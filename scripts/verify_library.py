#!/usr/bin/env python3
"""
장부(data/library.db) ↔ Obsidian Vault 대조 — 읽기 전용 (v4.3)

  /opt/homebrew/bin/python3 scripts/verify_library.py        # 통과 0 · 실패 1 · 인자 오류 2

v4.3(노션 해지)에서 scripts/notion_to_sqlite.py --verify 를 노션 의존 없이 떼어 왔다. 검사 항목·RESULT_JSON 키는 그대로다.
  - 장부: user_version = lib/library_db.py:SCHEMA_VERSION · integrity_check ok · videos ≥ 1 · videos 안 video_id 중복 0
  - Vault 영상 노트의 notion_id(= 장부 record_id) 가 전부 videos 또는 videos_dup 에 있다 (vault_missing 0)
  - Vault 「AI 꿀팁」 노트의 notion_id 가 전부 tips 에 있다 (tips_missing 0)
장부는 mode=ro 로 열고, Vault 는 읽기만 한다. 네트워크 호출 없음.

notion_id 는 프론트매터 안의 것만 센다 — schema.md 처럼 본문 코드블록에 예시 'notion_id: xxxxxxxx-…' 를 담은 문서를
영상 노트로 오인하지 않기 위함 (2026-10-11 실측). 같은 규칙: sync_obsidian.py, build_search_index.py.
프론트매터 키 이름 notion_id 는 노션 시절 이름이지만 바꾸지 않는다(wiki_ingest·검색 인덱스 상태가 이 값에 묶여 있다).
"""
import json, os, re, sys, unicodedata

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, 'lib'))

import sync_obsidian as so                     # noqa: E402  VAULT 경로·Vault 스캔 재사용
import library_db as ldb                       # noqa: E402

FM_RE = re.compile(r'\A﻿?---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)', re.S)
VAULT_IGNORED = []           # 본문(프론트매터 밖)에만 notion_id 가 있어 Vault id 로 세지 않은 파일 (Vault 상대 경로)


def log(msg=''):
    print(msg, flush=True)


def nfc(s):
    return unicodedata.normalize('NFC', s or '')


def fm_notion_id(path):
    """맨 앞 YAML 프론트매터 안의 notion_id. 없으면 None."""
    try:
        text = nfc(open(path, encoding='utf-8', errors='ignore').read())
    except Exception:
        return None
    m = FM_RE.match(text)
    if not m:
        return None
    m2 = re.search(r'^notion_id:\s*(.+)$', m.group(1), re.MULTILINE)
    return m2.group(1).strip() if m2 else None


def vault_ids():
    """(영상 노트 notion_id 집합, 꿀팁 노트 notion_id 집합).
    폴더 스캔 규칙은 sync_obsidian.get_existing_vault_info 를 그대로 쓰되, notion_id 는 프론트매터 안의 것만 센다."""
    id_to_path, _, _ = so.get_existing_vault_info()
    VAULT_IGNORED.clear()
    video_ids = set()
    for i, path in id_to_path.items():
        if fm_notion_id(path) == i:
            video_ids.add(i)
        else:
            VAULT_IGNORED.append(nfc(os.path.relpath(path, so.VAULT)))
    tips_ids = set()
    tips_dir = os.path.join(so.VAULT, so.TIPS_FOLDER)
    if os.path.isdir(tips_dir):
        for f in os.listdir(tips_dir):
            if not f.endswith('.md'):
                continue
            i = fm_notion_id(os.path.join(tips_dir, f))
            if i:
                tips_ids.add(i)
    return video_ids, tips_ids


def verify():
    if not os.path.exists(ldb.DB_PATH):
        log(f'❌ {ldb.DB_PATH} 없음'); return 1
    conn = ldb.open_db(ldb.DB_PATH, readonly=True)
    q = lambda sql: conn.execute(sql).fetchall()
    uv = q('PRAGMA user_version')[0][0]
    ic = q('PRAGMA integrity_check')[0][0]
    n_v, n_d, n_t = (q(f'SELECT COUNT(*) FROM {t}')[0][0] for t in ('videos', 'videos_dup', 'tips'))
    live = {r[0] for r in q('SELECT record_id FROM videos')}
    dup = {r[0] for r in q('SELECT record_id FROM videos_dup')}
    tips = {r[0] for r in q('SELECT record_id FROM tips')}
    dup_vid = q('SELECT COUNT(*) FROM (SELECT video_id FROM videos WHERE video_id IS NOT NULL GROUP BY video_id HAVING COUNT(*) > 1)')[0][0]
    no_vid = q('SELECT COUNT(*) FROM videos WHERE video_id IS NULL')[0][0]
    src = dict(q('SELECT summary_src, COUNT(*) FROM videos GROUP BY summary_src'))
    meta = dict(q('SELECT key, value FROM meta'))
    conn.close()

    vv, tv = vault_ids()
    v_live, v_dup = vv & live, vv & dup
    v_missing = vv - live - dup
    t_missing = tv - tips
    log('🔎 data/library.db ↔ Obsidian Vault 대조')
    log(f'  user_version {uv} · integrity_check {ic}')
    log(f'  videos {n_v:,} · videos_dup {n_d:,} · tips {n_t:,}  (적재 시각 {meta.get("loaded_at", "?")} · 전환 {meta.get("switched_at", "전")})')
    log(f'  videos 안 video_id 중복 {dup_vid} · video_id 없음 {no_vid} · summary_src {src}')
    log(f'  Vault 영상 노트 notion_id {len(vv):,} → videos {len(v_live):,} · videos_dup {len(v_dup):,} · 어디에도 없음 {len(v_missing):,}')
    log(f'  Vault 꿀팁 노트 notion_id {len(tv):,} → tips {len(tv & tips):,} · 없음 {len(t_missing):,}')
    if VAULT_IGNORED:
        log(f'  Vault: 프론트매터 밖 notion_id 라 제외 {len(VAULT_IGNORED)} {sorted(VAULT_IGNORED)[:10]}')
    for x in sorted(v_missing)[:10]:
        log(f'    [영상 없음] {x}')
    for x in sorted(t_missing)[:10]:
        log(f'    [꿀팁 없음] {x}')
    ok = (uv == ldb.SCHEMA_VERSION and ic == 'ok' and dup_vid == 0 and not v_missing and not t_missing and n_v > 0)
    log('RESULT_JSON ' + json.dumps({
        'mode': 'verify', 'ok': ok, 'videos': n_v, 'videos_dup': n_d, 'tips': n_t,
        'vault_video_ids': len(vv), 'vault_in_videos': len(v_live), 'vault_in_dup': len(v_dup),
        'vault_missing': len(v_missing), 'vault_tip_ids': len(tv), 'tips_missing': len(t_missing), 'vault_ignored': len(VAULT_IGNORED),
        'summary_src': src, 'no_video_id': no_vid, 'switched_at': meta.get('switched_at')}, ensure_ascii=False))
    log('✅ 검증 통과' if ok else '❌ 검증 실패 — 위 항목 확인')
    return 0 if ok else 1


def main(argv):
    if argv:
        log(f'인자를 받지 않습니다: {argv}  (사용법: python3 scripts/verify_library.py)')
        return 2
    return verify()


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
