#!/usr/bin/env python3
"""
v4.0 1단계 — 노션 → SQLite 적재 (노션 읽기 전용)

  /opt/homebrew/bin/python3 scripts/notion_to_sqlite.py                    # dry-run: 노션을 읽고 보고만 한다. 파일을 쓰지 않는다
  /opt/homebrew/bin/python3 scripts/notion_to_sqlite.py --apply            # data/library.db 생성 (이미 있으면 거부)
  /opt/homebrew/bin/python3 scripts/notion_to_sqlite.py --apply --replace  # 기존 파일을 data/library.db.bak.<시각> 으로 옮기고 새로 만든다
  /opt/homebrew/bin/python3 scripts/notion_to_sqlite.py --verify           # 노션 호출 없이 data/library.db ↔ Obsidian Vault 대조

  --summary-check=N   무작위 N개 영상의 노션 본문 블록과 '요약 내용' 속성을 비교해 보고만 한다 (기본 20, 0 = 끔)
  --summary-check=all 전량 비교하고, 다르면 본문 블록 쪽을 summary 로 쓴다 (페이지당 1회 호출, 3천 건이면 약 30분)

안전 (CLAUDE.md 보안 원칙):
  - 노션에는 GET 과 databases/query(POST, 읽기)만 보낸다. 쓰기·수정·삭제 요청은 이 파일에 없다.
  - HTTP 는 lib/tips_notion.py:notion_call 하나로 나간다 — 401/403 즉시 NotionAuthError(종료 코드 2),
    429/5xx 지수 백오프(2·4·8·16초) 후 실패, 호출 간 0.35초 대기.
  - 전부 읽었거나 아무것도 쓰지 않거나: 임시 파일(library.db.tmp)에 쓰고 검사가 통과해야만 rename 한다.
    중간에 실패하면 기존 data/library.db 는 그대로다.

중복(같은 video_id):
  Obsidian 노트(notion_id)가 가리키는 page 를 남긴다. 여럿이면 그중 가장 오래된 것, 없으면 전체에서 가장 오래된 것.
  나머지는 videos_dup 에 보관한다(삭제 아님). 남긴 행의 topics 는 그룹 전체 topics 의 합집합이다.
"""
import json, os, random, re, sys, time, unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, 'lib'))

import tips_notion as tn                       # noqa: E402  HTTP·인증 오류 처리 원본
import sync_obsidian as so                     # noqa: E402  VAULT 경로·block_to_md·Vault 스캔 재사용
from kakao_parse import url_key                # noqa: E402
import library_db as ldb                       # noqa: E402

NOTION_DB_ID   = tn.ENV.get('NOTION_DB_ID', '')
TIPS_DB_ID     = tn.TIPS_DB_ID
RATE_SLEEP     = tn.RATE_SLEEP
SUMMARY_PROP   = '요약 내용'
RT_REFETCH_AT  = 25          # 속성 rich_text 가 이 개수 이상이면 잘렸을 수 있으므로 속성 단독 조회로 다시 받는다
VID_RE = re.compile(r'(?:[?&]v=|youtu\.be/|/shorts/|/embed/)([A-Za-z0-9_-]{11})')


def log(msg=''):
    print(msg, flush=True)


def nfc(s):
    return unicodedata.normalize('NFC', s or '')


def plain(rt):
    return nfc(''.join((t.get('plain_text') if t.get('plain_text') is not None
                        else t.get('text', {}).get('content', '')) for t in (rt or [])))


# ─────────────────────────── 노션 읽기 ───────────────────────────
def query_all(db_id, label):
    """DB 전체 조회. 전부 읽었거나 던지거나. 0건이면 던진다."""
    if not db_id:
        raise RuntimeError(f'{label}: DB id 가 .env 에 없습니다')
    pages, cursor, n = [], None, 0
    while True:
        body = {'page_size': 100}
        if cursor:
            body['start_cursor'] = cursor
        res = tn.notion_call('POST', f'/v1/databases/{db_id}/query', body)
        if not isinstance(res, dict) or not isinstance(res.get('results'), list):
            raise RuntimeError(f'{label}: 응답 형식 이상 (results 없음) — {str(res)[:200]}')
        pages.extend(res['results'])
        n += 1
        cursor = res.get('next_cursor')
        if not res.get('has_more') or not cursor:
            break
        time.sleep(RATE_SLEEP)
    if not pages:
        raise RuntimeError(f'{label}: 0건 — API 오류 의심, 중단')
    log(f'  {label}: {len(pages):,}건 ({n}회 조회)')
    return pages


def fetch_property_text(page_id, prop_id):
    """속성 단독 조회(페이지네이션) — 잘린 rich_text 를 끝까지 받는다."""
    parts, cursor = [], None
    while True:
        path = f'/v1/pages/{page_id}/properties/{prop_id}?page_size=100'
        if cursor:
            path += f'&start_cursor={cursor}'
        res = tn.notion_call('GET', path)
        time.sleep(RATE_SLEEP)
        items = res.get('results') if res.get('object') == 'list' else [res]
        for it in items or []:
            parts.append(plain([it.get('rich_text')] if isinstance(it.get('rich_text'), dict) else it.get('rich_text')))
        cursor = res.get('next_cursor')
        if not res.get('has_more') or not cursor:
            break
    return ''.join(parts)


def blocks_body_md(page_id):
    """영상 페이지 본문 → 마크다운. 썸네일·'▶ 영상 보기'·구분선 다음부터가 요약 본문이다."""
    blocks = tn.get_blocks(page_id)
    time.sleep(RATE_SLEEP)
    idx = next((i for i, b in enumerate(blocks) if b.get('type') == 'divider'), None)
    body = blocks[idx + 1:] if idx is not None else [b for b in blocks if b.get('type') != 'image']
    return nfc('\n'.join(so.block_to_md(b) for b in body)).strip()


def video_row(page, stats):
    pr = page.get('properties', {})
    url = (pr.get('영상 URL', {}) or {}).get('url') or ''
    m = VID_RE.search(url)
    topics, seen = [], set()
    for t in (pr.get('주제', {}) or {}).get('multi_select') or []:
        name = nfc(t.get('name', ''))
        if name and name not in seen:
            seen.add(name); topics.append(name)
    sp = pr.get(SUMMARY_PROP, {}) or {}
    rt = sp.get('rich_text') or []
    if len(rt) >= RT_REFETCH_AT and sp.get('id'):
        summary = fetch_property_text(page['id'], sp['id'])
        stats['summary_refetch'] += 1
    else:
        summary = plain(rt)
    src = 'property'
    if not summary.strip():
        summary = blocks_body_md(page['id'])
        src = 'blocks' if summary else 'empty'
    return {
        'record_id': page['id'],
        'video_id': m.group(1) if m else None,
        'title': plain((pr.get('영상 제목', {}) or {}).get('title')),
        'channel': plain((pr.get('유튜브 채널', {}) or {}).get('rich_text')),
        'topics': topics,
        'upload_date': (((pr.get('업로드 일자', {}) or {}).get('date') or {}).get('start') or '')[:10] or None,
        'view_count': (pr.get('조회수', {}) or {}).get('number'),
        'subscriber_count': (pr.get('구독자수', {}) or {}).get('number'),
        'video_url': url or None,
        'thumbnail_url': (pr.get('썸네일 URL', {}) or {}).get('url') or None,
        'status': (((pr.get('처리 상태', {}) or {}).get('select')) or {}).get('name') or None,
        'summary': summary,
        'summary_src': src,
        'created_at': page.get('created_time', ''),
        'updated_at': page.get('last_edited_time', '') or page.get('created_time', ''),
    }


def tip_row(page):
    r = tn.page_to_row(page)
    try:
        body = nfc('\n'.join(so.block_to_md(b) for b in tn.get_blocks(page['id']))).strip()
    finally:
        time.sleep(RATE_SLEEP)
    return {
        'record_id': page['id'],
        'title': nfc(r['title']), 'url': r['url'], 'url_key': url_key(r['url']) if r['url'] else '',
        'source': r['source'], 'tags': [nfc(t) for t in r['tags']],
        'category': nfc(r['category']), 'status': nfc(r['status']), 'importance': nfc(r['importance']),
        'saved_date': (r['saved_date'] or '')[:10] or None, 'memo': nfc(r['memo']), 'body_md': body,
        'created_at': r['created_time'], 'updated_at': r['last_edited_time'] or r['created_time'],
    }


# ─────────────────────────── Vault ───────────────────────────
FM_RE = re.compile(r'\A\ufeff?---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)', re.S)
VAULT_IGNORED = []           # 본문(프론트매터 밖)에만 notion_id 가 있어 Vault id 로 세지 않은 파일 (Vault 상대 경로)


def fm_notion_id(path):
    """맨 앞 YAML 프론트매터 안의 notion_id. 없으면 None.
    schema.md 처럼 본문 코드블록에 예시 'notion_id: xxxxxxxx-…' 를 담은 문서를 영상 노트로 오인하지 않기 위함 (10-11 dry-run)."""
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


# ─────────────────────────── 중복 정리 ───────────────────────────
def dedupe(rows, vids_in_vault):
    groups = defaultdict(list)
    for r in rows:
        groups[r['video_id'] or ('__noid__', r['record_id'])].append(r)
    keepers, dups = [], []
    st = Counter()
    for key, g in groups.items():
        if len(g) == 1:
            keepers.append(g[0]); continue
        st['dup_groups'] += 1
        g.sort(key=lambda r: (r['created_at'], r['record_id']))
        noted = [r for r in g if r['record_id'] in vids_in_vault]
        keep = noted[0] if noted else g[0]
        st['keeper_by_vault' if noted else 'keeper_by_oldest'] += 1
        if len(noted) > 1:
            st['groups_multi_notes'] += 1
        merged = list(keep['topics'])
        for r in g:
            for t in r['topics']:
                if t not in merged:
                    merged.append(t)
        if merged != keep['topics']:
            st['keeper_topics_grew'] += 1
        keep = dict(keep, topics=merged)
        if not keep['summary'].strip():
            donor = next((r for r in g if r['summary'].strip()), None)
            if donor:
                keep.update(summary=donor['summary'], summary_src=donor['summary_src'])
                st['keeper_summary_from_dup'] += 1
        keepers.append(keep)
        for r in g:
            if r is not keep and r['record_id'] != keep['record_id']:
                dups.append(dict(r, keeper_record_id=keep['record_id'],
                                 has_vault_note=1 if r['record_id'] in vids_in_vault else 0))
    return keepers, dups, st


# ─────────────────────────── 요약 대조 (보고용) ───────────────────────────
def _norm(s):
    s = re.sub(r'\*\*|^#+\s*|^[-*]\s+|^1\.\s+', '', s or '', flags=re.MULTILINE)
    return re.sub(r'\s+', '', nfc(s))


def summary_check(rows, n):
    """n: 정수 = 무작위 n개 대조(보고만), 'all' = 전량 대조하고 불일치는 본문 블록 쪽으로 교체."""
    cand = [r for r in rows if r['summary_src'] == 'property']
    if n == 'all':
        sample, fix = cand, True
    else:
        if n <= 0 or not cand:
            return None
        sample, fix = random.Random(20261011).sample(cand, min(n, len(cand))), False
    bad = []
    for i, r in enumerate(sample, 1):
        body = blocks_body_md(r['record_id'])
        if _norm(r['summary']) != _norm(body):
            bad.append(r['record_id'])
            if fix and body:
                r['summary'], r['summary_src'] = body, 'blocks'
        if fix and i % 250 == 0:
            log(f'  요약 전량 대조 {i:,}/{len(sample):,} (불일치 {len(bad)})')
    return {'checked': len(sample), 'match': len(sample) - len(bad), 'mismatch_ids': bad[:10],
            'replaced_by_blocks': len(bad) if fix else 0}


# ─────────────────────────── 쓰기 ───────────────────────────
V_COLS = ['record_id', 'video_id', 'title', 'channel', 'topics', 'upload_date', 'view_count', 'subscriber_count',
          'video_url', 'thumbnail_url', 'status', 'summary', 'summary_src', 'created_at', 'updated_at']
D_COLS = V_COLS + ['keeper_record_id', 'has_vault_note']
T_COLS = ['record_id', 'title', 'url', 'url_key', 'source', 'tags', 'category', 'status', 'importance',
          'saved_date', 'memo', 'body_md', 'created_at', 'updated_at']


def _vals(r, cols):
    out = []
    for c in cols:
        v = r.get(c)
        if c in ('topics', 'tags'):
            v = json.dumps(v or [], ensure_ascii=False)
        out.append(v)
    return out


def write_db(keepers, dups, tips, meta, replace):
    final = ldb.DB_PATH
    tmp = final + '.tmp'
    for p in (tmp, tmp + '-journal'):
        if os.path.exists(p):
            os.remove(p)
    conn = ldb.open_db(tmp)
    try:
        ldb.apply_schema(conn)
        with conn:
            conn.executemany(f'INSERT INTO videos ({",".join(V_COLS)}) VALUES ({",".join("?" * len(V_COLS))})',
                             [_vals(r, V_COLS) for r in keepers])
            conn.executemany(f'INSERT INTO videos_dup ({",".join(D_COLS)}) VALUES ({",".join("?" * len(D_COLS))})',
                             [_vals(r, D_COLS) for r in dups])
            conn.executemany(f'INSERT INTO tips ({",".join(T_COLS)}) VALUES ({",".join("?" * len(T_COLS))})',
                             [_vals(r, T_COLS) for r in tips])
            conn.executemany('INSERT INTO meta (key, value) VALUES (?, ?)',
                             [(k, str(v)) for k, v in meta.items()])
        got = {t: conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in ('videos', 'videos_dup', 'tips')}
        want = {'videos': len(keepers), 'videos_dup': len(dups), 'tips': len(tips)}
        ic = conn.execute('PRAGMA integrity_check').fetchone()[0]
        if got != want or ic != 'ok':
            raise RuntimeError(f'쓰기 검사 실패 — 건수 {got} ≠ {want} 또는 integrity_check={ic}')
    finally:
        conn.close()
    backup = None
    if os.path.exists(final):
        if not replace:   # main 에서 이미 막지만 한 번 더
            raise RuntimeError(f'{final} 가 이미 있습니다 (--replace 필요)')
        backup = f'{final}.bak.{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        os.replace(final, backup)
    os.replace(tmp, final)
    return got, backup


# ─────────────────────────── --verify ───────────────────────────
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
    log('🔎 data/library.db 검증')
    log(f'  user_version {uv} · integrity_check {ic}')
    log(f'  videos {n_v:,} · videos_dup {n_d:,} · tips {n_t:,}  (적재 시각 {meta.get("loaded_at", "?")})')
    log(f'  videos 안 video_id 중복 {dup_vid} · video_id 없음 {no_vid} · summary_src {src}')
    log(f'  Vault 영상 노트 notion_id {len(vv):,} → videos {len(v_live):,} · videos_dup {len(v_dup):,}(2단계 고아 격리 예정) · 어디에도 없음 {len(v_missing):,}')
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
        'summary_src': src, 'no_video_id': no_vid}, ensure_ascii=False))
    log('✅ 검증 통과' if ok else '❌ 검증 실패 — 위 항목 확인')
    return 0 if ok else 1


# ─────────────────────────── main ───────────────────────────
def main(argv):
    if '--verify' in argv:
        return verify()
    apply_ = '--apply' in argv
    replace = '--replace' in argv
    n_check = 20
    for a in argv:
        if a.startswith('--summary-check='):
            v = a.split('=', 1)[1]
            n_check = 'all' if v == 'all' else int(v)
    if apply_ and os.path.exists(ldb.DB_PATH) and not replace:
        log(f'❌ {ldb.DB_PATH} 가 이미 있습니다. 다시 만들려면 --apply --replace'); return 1

    t0 = time.time()
    log(f'🚚 노션 → SQLite 적재 ({"APPLY" if apply_ else "DRY-RUN"})')
    vv, tv = vault_ids()
    log(f'  Vault: 영상 노트 notion_id {len(vv):,} · 꿀팁 노트 notion_id {len(tv):,}')
    if VAULT_IGNORED:
        log(f'  Vault: 프론트매터 밖 notion_id 라 제외 {len(VAULT_IGNORED)} {sorted(VAULT_IGNORED)[:10]}')
    if not vv:
        log(f'❌ Vault 에서 영상 노트 notion_id 를 하나도 못 찾았습니다 ({so.VAULT}) — 중복 판정 근거가 없어 중단'); return 1

    log('🔄 노션 조회 (읽기 전용)')
    vpages = query_all(NOTION_DB_ID, '「AI YouTube 요약 자료」')
    tpages = query_all(TIPS_DB_ID, '「AI 꿀팁」')

    stats = Counter()
    rows = []
    for i, p in enumerate(vpages, 1):
        rows.append(video_row(p, stats))
        if i % 500 == 0:
            log(f'  영상 변환 {i:,}/{len(vpages):,}')
    keepers, dups, dst = dedupe(rows, vv)
    tips = [tip_row(p) for p in tpages]

    no_vid = sum(1 for r in keepers if not r['video_id'])
    ids_all = {r['record_id'] for r in rows}
    v_missing = vv - ids_all
    t_missing = tv - {t['record_id'] for t in tips}
    tip_key_dup = sum(c - 1 for c in Counter(t['url_key'] for t in tips if t['url_key']).values() if c > 1)
    sc = summary_check(keepers, n_check)
    src = Counter(r['summary_src'] for r in keepers)   # 'all' 이면 교체분 반영

    log('')
    log('📊 결과')
    log(f'  영상 페이지 {len(rows):,} → videos {len(keepers):,} · videos_dup {len(dups):,}  (중복 그룹 {dst["dup_groups"]})')
    log(f'    남길 행 선택: Vault 노트 기준 {dst["keeper_by_vault"]} · 가장 오래된 것 {dst["keeper_by_oldest"]} · '
        f'노트 2개 이상 그룹 {dst["groups_multi_notes"]} · topics 합쳐짐 {dst["keeper_topics_grew"]} · 요약 dup 에서 보충 {dst["keeper_summary_from_dup"]}')
    log(f'    videos_dup 중 Vault 노트 있음 {sum(d["has_vault_note"] for d in dups)} (2단계에서 고아 격리 대상)')
    log(f'    summary_src {dict(src)} · rich_text 재조회 {stats["summary_refetch"]} · video_id 없음 {no_vid}')
    log(f'  꿀팁 {len(tips):,} · url_key 중복 {tip_key_dup} · 본문 블록 있음 {sum(1 for t in tips if t["body_md"])}')
    log(f'  Vault 대조: 영상 노트 중 노션에 없는 id {len(v_missing)} · 꿀팁 노트 중 없는 id {len(t_missing)}')
    for x in sorted(v_missing)[:10]:
        log(f'    [영상 없음] {x}')
    for x in sorted(t_missing)[:10]:
        log(f'    [꿀팁 없음] {x}')
    if sc:
        log(f'  요약 대조({"전량" if n_check == "all" else "무작위"} {sc["checked"]}): 일치 {sc["match"]} · '
            f'불일치 {sc["checked"] - sc["match"]} {sc["mismatch_ids"]}'
            + (f' → 블록 본문으로 교체 {sc["replaced_by_blocks"]}' if n_check == 'all' else ''))

    result = {'mode': 'apply' if apply_ else 'dry-run', 'video_pages': len(rows), 'videos': len(keepers),
              'videos_dup': len(dups), 'dup_groups': dst['dup_groups'], 'tips': len(tips),
              'summary_src': dict(src), 'summary_refetch': stats['summary_refetch'], 'no_video_id': no_vid,
              'vault_missing': len(v_missing), 'tips_missing': len(t_missing), 'vault_ignored': len(VAULT_IGNORED),
              'tip_url_key_dup': tip_key_dup,
              'summary_check': sc, 'elapsed_s': round(time.time() - t0, 1)}

    if apply_:
        meta = {'loaded_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), 'source': 'notion',
                'notion_video_pages': len(rows), 'notion_tip_pages': len(tips), 'schema_version': ldb.SCHEMA_VERSION}
        got, backup = write_db(keepers, dups, tips, meta, replace)
        log(f'💾 {ldb.DB_PATH} 작성 {got}' + (f' · 이전 파일 → {os.path.basename(backup)}' if backup else ''))
        result['written'] = got
        result['backup'] = os.path.basename(backup) if backup else None
    else:
        log('ℹ️  dry-run — 파일을 쓰지 않았습니다. 적재하려면 --apply')
    log('RESULT_JSON ' + json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv[1:]))
    except tn.NotionAuthError as e:
        log(f'🛑 {e} — 즉시 종료 (보안 원칙 1). 아무것도 쓰지 않았습니다')
        sys.exit(2)
