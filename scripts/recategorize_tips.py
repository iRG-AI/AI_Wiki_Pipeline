#!/usr/bin/env python3
"""
꿀팁 분류 보정 — 기존 장부 tips 의 카테고리·태그를 v4.9 규칙으로 다시 매기고, 옛 행의 출처를 호스트만으로 맞춘다 (v4.9)

  /opt/homebrew/bin/python3 scripts/recategorize_tips.py            # dry-run (기본) — 아무것도 쓰지 않는다
  /opt/homebrew/bin/python3 scripts/recategorize_tips.py --apply    # 실제 반영
      [--no-rebuild]   반영 뒤 build_obsidian_wiki.py · build_search_index.py 를 부르지 않는다 (테스트·사본 검증용)
      [--db PATH] [--vault PATH]   장부·Vault 경로 바꾸기 (사본 검증용, 기본 = data/library.db · sync_obsidian.VAULT)
  종료 코드: 0 성공 · 1 반영 중 실패 · 2 입력·검증 실패(아무것도 쓰지 않음)

대상 (한 행마다 판단):
  1. 카테고리·태그 — 지금 값이 「v4.8 규칙이 매긴 값」과 같을 때만 v4.9 규칙(lib/kakao_parse.classify)으로 다시 매긴다.
     v4.8 규칙 값 = (URL + 제목) 또는 (URL 만) 으로 매긴 결과. 둘 다 아니면 사람이 고른 값(노션 시절 등)으로 보고 그대로 둔다(manual_kept).
     제목이 URL 추정 제목(「노션 자료 (제목 미확인)」 등)이면 제목은 판정 글자에 넣지 않는다 — 추정 문구의 「노션」이 태그가 되지 않게.
  2. 출처 — 장부 source 가 'http://'·'https://' 로 시작하면(노션 이관 시절 행) 호스트만 남긴다(kakao_parse.host_of, www. 제거).
     그 호스트가 URL 의 호스트와 다르면 고치지 않고 보고만 한다(source_mismatch).
  바뀌는 행마다:
     장부 tips: category·tags·source, updated_at = 지금 (시트 미러가 이 워터마크로 변경분을 보낸다).
     「AI 꿀팁」 노트(프론트매터 notion_id = record_id)를 제자리에서 고친다 — 프론트매터 channel·category·keywords 줄,
     본문 '- 📂 카테고리:' · '- 🏷 태그:' · '- 🗓 저장일: … 출처:' 줄. 바뀌는 칸의 줄만, 지금 장부 값과 글자 그대로 같은 줄만.
     파일명·제목·나머지 내용(관련 링크 등)은 그대로. 노트가 없으면 장부만(다음 sync_obsidian 이 새 값으로 만든다).
  (--no-rebuild 가 아니면) build_obsidian_wiki.py → build_search_index.py — 출처는 「채널별 목차」 묶음, 태그·카테고리는 검색 필터에 쓰인다.

안전장치:
  - 노트에 고칠 줄이 정확히 1개씩 없으면(손으로 고친 노트) 그 행은 장부·노트 모두 건너뛰고 보고한다(skipped_note).
    같은 notion_id 노트가 2개 이상이어도 건너뛴다.
  - 쓰기 전에 data/recategorize_backup/<YYYYmmdd-HHMMSS>/ 에 장부 사본(온라인 백업 API)·바뀔 노트 원본·manifest.json.
    되돌리기: 장부는 사본으로 교체, 노트는 manifest 의 edited 를 사본에서 복사 → sheet_mirror.py --full.
  - 장부 UPDATE 는 한 트랜잭션, 조건은 record_id 와 옛 category·tags·source 셋 다. 행 수가 1이 아니면 전체 롤백.
  - 네트워크 호출 없음(rebuild 의 검색 인덱스만 Gemini 임베딩을 부른다 — 바뀐 노트 수만큼).
  - 다시 돌려도 안전하다 — 이미 고친 행은 v4.9 규칙 값과 같아 대상이 아니다(0건).
"""
import json, os, re, shutil, sqlite3, subprocess, sys, unicodedata
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, 'lib'))

import sync_obsidian as so                     # noqa: E402  VAULT·TIPS_FOLDER·_q·fm_notion_id 재사용
import library_db as ldb                       # noqa: E402
import kakao_parse as kp                       # noqa: E402

BACKUP_ROOT = os.path.join(ldb.DATA_DIR, 'recategorize_backup')


def log(msg=''):
    print(msg, flush=True)


def nfc(s):
    return unicodedata.normalize('NFC', s or '')


def now_iso():
    dt = datetime.now(timezone.utc)
    return dt.strftime('%Y-%m-%dT%H:%M:%S.') + f'{dt.microsecond // 1000:03d}Z'   # kakao_ingest·scheduler 와 같은 형식


def emit(code, **kw):
    print('RESULT_JSON:' + json.dumps(kw, ensure_ascii=False), flush=True)
    return code


class Invalid(Exception):
    pass


# ── v4.8 규칙 (얼린 사본) — 「규칙이 매긴 값인가」 판정에만 쓴다. 고치지 말 것 ──
_V48_TAGS = [
    (r'claude[-_ ]?code', 'ClaudeCode'), (r'claude', 'Claude'), (r'antigravity', 'Antigravity'),
    (r'gemini', 'Gemini'), (r'gpt|openai|chatgpt', 'GPT'), (r'ollama', 'Ollama'),
    (r'notion', 'Notion'), (r'obsidian', 'Obsidian'), (r'prompt|프롬프트', '프롬프트'),
    (r'mcp', 'MCP'), (r'agent|에이전트', 'Agent'), (r'cursor', 'Cursor'), (r'github\.com', 'GitHub'),
    (r'youtube\.com|youtu\.be', 'YouTube'), (r'huggingface', 'HuggingFace'),
]


def classify_v48(url, *texts):
    text = ' '.join([url or ''] + [t or '' for t in texts]).lower()
    tags = []
    for pat, tag in _V48_TAGS:
        if re.search(pat, text) and tag not in tags:
            tags.append(tag)
    category = '개발툴' if 'github.com' in kp.host_of(url or '') else '기타'
    if '프롬프트' in tags:
        category = '프롬프트'
    elif any(t in tags for t in ('ClaudeCode', 'Antigravity', 'Cursor', 'MCP', 'Ollama')) and category == '기타':
        category = '개발툴'
    elif any(t in tags for t in ('Notion', 'Obsidian')) and category == '기타':
        category = '지식관리'
    elif any(t in tags for t in ('GPT', 'Gemini', 'Claude')) and category == '기타':
        category = '모델/LLM'
    return category, tags


# ── 행 판단 ──
def title_text(url, title):
    """판정 글자로 쓸 제목. URL 추정 제목(guess_meta 가 메시지 없이 만든 제목)이면 ''."""
    return '' if nfc(title) == kp.guess_meta(url, '')['title'] else nfc(title)


def decide(row):
    """장부 행 → {'category','tags','source','rule_made','source_mismatch'} (새 값)."""
    url, cat, tags, src = row['url'], nfc(row['category']), [nfc(t) for t in row['tags']], nfc(row['source'])
    t = title_text(url, row['title'])
    rule_made = (cat, tags) in (classify_v48(url, t), classify_v48(url))
    new_cat, new_tags = kp.classify(url, t) if rule_made else (cat, tags)
    new_src, mismatch = src, False
    if re.match(r'https?://', src, re.I):
        h = kp.host_of(src)
        if h and h == kp.host_of(url):
            new_src = h
        else:
            mismatch = True
    return {'category': new_cat, 'tags': new_tags, 'source': new_src, 'rule_made': rule_made, 'source_mismatch': mismatch}


# ── 노트 편집 ──
def tag_str(tags):
    return ', '.join(tags) if tags else '(없음)'


def kw_line(tags):
    return f'keywords: [{", ".join(chr(34) + so._q(t) + chr(34) for t in tags)}]'


def _replace_one(lines, lo, hi, match, new, what):
    """lines[lo:hi] 에서 match(line) 이 참인 줄이 정확히 1개여야 한다 → new(line) 으로 바꾼다."""
    idx = [i for i in range(lo, hi) if match(lines[i])]
    if len(idx) != 1:
        raise Invalid(f'{what} 줄이 1개가 아니다({len(idx)}개) — 손으로 고친 노트일 수 있다')
    lines[idx[0]] = new(lines[idx[0]])


def edit_note(text, old, new):
    """old/new = {'category','tags','source'}. 바뀌는 칸의 줄만 고친다. 편집 지점이 정확히 1곳씩이 아니면 Invalid."""
    text = nfc(text)
    m = so.FM_RE.match(text)
    if not m:
        raise Invalid('프론트매터 없음')
    lines = text.split('\n')
    fm_end = text[:m.end()].count('\n')          # 프론트매터(닫는 --- 포함) 다음 줄 번호
    n = len(lines)
    q = so._q
    if old['source'] != new['source']:
        a, b = f'channel: "{q(old["source"])}"', f'channel: "{q(new["source"])}"'
        _replace_one(lines, 0, fm_end, lambda l: l == a, lambda l: b, 'channel')
        tail = f'  ·  출처: {old["source"]}'
        _replace_one(lines, fm_end, n, lambda l: l.startswith('- 🗓 저장일: ') and l.endswith(tail),
                     lambda l: l[:-len(tail)] + f'  ·  출처: {new["source"]}', '출처')
    if old['category'] != new['category']:
        a, b = f'category: "{q(old["category"])}"', f'category: "{q(new["category"])}"'
        _replace_one(lines, 0, fm_end, lambda l: l == a, lambda l: b, 'category')
        head = f'- 📂 카테고리: {old["category"]}  ·  '
        _replace_one(lines, fm_end, n, lambda l: l.startswith(head),
                     lambda l: f'- 📂 카테고리: {new["category"]}  ·  ' + l[len(head):], '카테고리')
    if old['tags'] != new['tags']:
        a, b = kw_line(old['tags']), kw_line(new['tags'])
        _replace_one(lines, 0, fm_end, lambda l: l == a, lambda l: b, 'keywords')
        a2, b2 = f'- 🏷 태그: {tag_str(old["tags"])}', f'- 🏷 태그: {tag_str(new["tags"])}'
        _replace_one(lines, fm_end, n, lambda l: l == a2, lambda l: b2, '태그')
    return '\n'.join(lines)


def tip_notes(tips_dir):
    """notion_id -> [파일명(NFC)]"""
    found = {}
    if os.path.isdir(tips_dir):
        for f in os.listdir(tips_dir):
            if f.endswith('.md'):
                nid = so.fm_notion_id(os.path.join(tips_dir, f))
                if nid:
                    found.setdefault(nid, []).append(nfc(f))
    return found


# ── 계획 ──
def build_plan(conn, vault):
    tips_dir = os.path.join(vault, so.TIPS_FOLDER)
    notes = tip_notes(tips_dir)
    plan, skipped, mismatch, manual = [], [], [], 0
    rows = conn.execute('SELECT record_id, title, url, source, tags, category FROM tips ORDER BY created_at, record_id').fetchall()
    for r in rows:
        row = dict(r)
        try:
            row['tags'] = json.loads(row['tags'] or '[]')
        except ValueError:
            skipped.append({'record_id': row['record_id'], 'reason': 'tags JSON 아님'})
            continue
        old = {'category': nfc(row['category']), 'tags': [nfc(t) for t in row['tags']], 'source': nfc(row['source'])}
        d = decide(row)
        new = {k: d[k] for k in ('category', 'tags', 'source')}
        if d['source_mismatch']:
            mismatch.append({'record_id': row['record_id'], 'source': old['source'], 'url_host': kp.host_of(row['url'])})
        if not d['rule_made'] and (old['category'], old['tags']) != kp.classify(row['url'], title_text(row['url'], row['title'])):
            manual += 1
        if new == old:
            continue
        item = {'record_id': row['record_id'], 'title': nfc(row['title']), 'old': old, 'new': new,
                'raw': {'category': r['category'], 'tags': r['tags'], 'source': r['source']}, 'file': None, 'note_text': None}
        files = notes.get(row['record_id'], [])
        try:
            if len(files) > 1:
                raise Invalid(f'같은 notion_id 꿀팁 노트가 {len(files)}개 {files}')
            if files:
                text = open(os.path.join(tips_dir, files[0]), encoding='utf-8').read()
                item['note_text'] = edit_note(text, old, new)
                item['file'] = files[0]
        except (Invalid, OSError, UnicodeDecodeError) as e:
            skipped.append({'record_id': row['record_id'], 'title': item['title'][:40], 'reason': str(e)[:120]})
            continue
        plan.append(item)
    return plan, skipped, mismatch, manual, len(rows)


# ── 반영 ──
def backup(db_path, vault, plan):
    base = os.path.join(BACKUP_ROOT, datetime.now().strftime('%Y%m%d-%H%M%S'))
    d, k = base, 1
    while os.path.exists(d):   # 같은 초에 두 번 돌린 경우
        k += 1
        d = f'{base}-{k}'
    os.makedirs(d)
    src = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)
    dst = sqlite3.connect(os.path.join(d, 'library.db'))
    with dst:
        src.backup(dst)
    src.close(); dst.close()
    edited = []
    for p in plan:
        if not p['file']:
            continue
        rel = os.path.join(so.TIPS_FOLDER, p['file'])
        os.makedirs(os.path.join(d, 'vault', so.TIPS_FOLDER), exist_ok=True)
        shutil.copy2(os.path.join(vault, rel), os.path.join(d, 'vault', rel))
        edited.append(rel)
    manifest = {
        'created_at': now_iso(), 'db': os.path.abspath(db_path), 'vault': os.path.abspath(vault),
        'rows': [{'record_id': p['record_id'], 'old': p['old'], 'new': p['new']} for p in plan],
        'edited': edited,
    }
    open(os.path.join(d, 'manifest.json'), 'w', encoding='utf-8').write(json.dumps(manifest, ensure_ascii=False, indent=2))
    return d


def apply_db(conn, plan):
    ts = now_iso()
    with conn:   # 한 트랜잭션 — 예외면 전부 롤백
        for p in plan:
            n = p['new']
            cur = conn.execute(
                'UPDATE tips SET category = ?, tags = ?, source = ?, updated_at = ? '
                'WHERE record_id = ? AND category = ? AND tags = ? AND source = ?',
                (n['category'], json.dumps(n['tags'], ensure_ascii=False), n['source'], ts,
                 p['record_id'], p['raw']['category'], p['raw']['tags'], p['raw']['source']))
            if cur.rowcount != 1:
                raise RuntimeError(f'{p["record_id"]}: UPDATE 행 수 {cur.rowcount} ≠ 1 — 롤백')
    return ts


def apply_vault(vault, plan):
    tips_dir = os.path.join(vault, so.TIPS_FOLDER)
    for p in plan:
        if p['file']:
            open(os.path.join(tips_dir, p['file']), 'w', encoding='utf-8').write(p['note_text'])


def rebuild():
    out = {}
    for name in ('build_obsidian_wiki.py', 'build_search_index.py'):
        r = subprocess.run([sys.executable, os.path.join(REPO_ROOT, name)], capture_output=True, text=True)
        out[name] = r.returncode
        log(f'  {"✅" if r.returncode == 0 else "❌"} {name} (종료 {r.returncode})')
        if r.returncode != 0:
            log((r.stderr or '')[-400:])
    return out


def summarize(plan, skipped, mismatch, manual, total):
    moves = {}
    for p in plan:
        if p['old']['category'] != p['new']['category']:
            k = f'{p["old"]["category"]}→{p["new"]["category"]}'
            moves[k] = moves.get(k, 0) + 1
    return dict(
        tips=total, rows=len(plan),
        category_changed=sum(1 for p in plan if p['old']['category'] != p['new']['category']),
        tags_changed=sum(1 for p in plan if p['old']['tags'] != p['new']['tags']),
        source_changed=sum(1 for p in plan if p['old']['source'] != p['new']['source']),
        notes=sum(1 for p in plan if p['file']), skipped_note=len(skipped), source_mismatch=len(mismatch),
        manual_kept=manual, moves=dict(sorted(moves.items(), key=lambda x: -x[1])))


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    apply_ = '--apply' in argv
    no_rebuild = '--no-rebuild' in argv
    db_path, vault = ldb.DB_PATH, so.VAULT
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ('--db', '--vault'):
            if i + 1 >= len(argv):
                return emit(2, ok=False, error=f'{a} 값 없음')
            if a == '--db':
                db_path = argv[i + 1]
            else:
                vault = argv[i + 1]
            i += 2
            continue
        if a not in ('--apply', '--no-rebuild'):
            return emit(2, ok=False, error=f'모르는 인자 {a}')
        i += 1
    if not os.path.isdir(os.path.join(vault, so.TIPS_FOLDER)):
        return emit(2, ok=False, error=f'Vault 꿀팁 폴더 없음: {vault}')

    try:
        conn = ldb.open_existing(db_path, readonly=not apply_)
    except (OSError, RuntimeError, sqlite3.Error) as e:
        log(f'❌ {e}')
        return emit(2, ok=False, error=str(e)[:300])
    try:
        try:
            plan, skipped, mismatch, manual, total = build_plan(conn, vault)
        except (Invalid, OSError) as e:
            log(f'❌ 검증 실패 — 아무것도 쓰지 않았습니다: {e}')
            return emit(2, ok=False, error=str(e)[:300])

        log(f'🏷  꿀팁 분류 보정 {len(plan)}건 / 장부 {total}건 {"(apply)" if apply_ else "(dry-run)"}\n')
        for p in plan:
            o, n = p['old'], p['new']
            log(f'  {p["record_id"][:8]} | {p["title"][:44]}')
            if o['category'] != n['category']:
                log(f'           카테고리 {o["category"]} → {n["category"]}')
            if o['tags'] != n['tags']:
                log(f'           태그 {tag_str(o["tags"])} → {tag_str(n["tags"])}')
            if o['source'] != n['source']:
                log(f'           출처 {o["source"]} → {n["source"]}')
            log(f'           노트 {p["file"]}' if p['file'] else '           노트 없음 — 다음 sync_obsidian 이 새 값으로 만든다')
        for s in skipped:
            log(f'  ⏭  건너뜀 {s["record_id"][:8]} {s.get("title", "")} — {s["reason"]}')
        for s in mismatch:
            log(f'  ⚠️  출처·URL 호스트 다름(그대로 둠) {s["record_id"][:8]} source={s["source"]} url={s["url_host"]}')
        summary = summarize(plan, skipped, mismatch, manual, total)
        log(f'\n  카테고리 이동: {summary["moves"] or "없음"} · 사람이 고른 값 유지 {manual}건')
        if not apply_:
            log('\n👀 dry-run — 장부·Vault 무변경. 반영은 --apply')
            return emit(0, ok=True, dry_run=True, **summary)
        if not plan:
            log('\n✅ 고칠 행 없음')
            return emit(0, ok=True, dry_run=False, **summary)

        try:
            bdir = backup(db_path, vault, plan)
        except Exception as e:
            log(f'❌ 백업 실패 — 장부·Vault 무변경: {e}')
            return emit(1, ok=False, error=f'백업 실패: {e}'[:300], **summary)
        log(f'\n💾 백업: {bdir}')
        try:
            ts = apply_db(conn, plan)
        except Exception as e:
            log(f'❌ 장부 반영 실패(롤백, Vault 무변경): {e}')
            return emit(1, ok=False, error=str(e)[:300], backup=bdir, **summary)
        log(f'🗄  장부 tips {len(plan)}행 갱신 (updated_at {ts})')
        try:
            apply_vault(vault, plan)
        except Exception as e:
            log(f'❌ Vault 반영 중 실패 — 장부는 이미 바뀜. 백업 manifest 로 되돌릴 것: {e}')
            return emit(1, ok=False, error=str(e)[:300], backup=bdir, updated_at=ts, **summary)
        log(f'📂 노트 {summary["notes"]}개 수정')
        rb = {}
        if not no_rebuild:
            log('\n🔧 Wiki 재구성 · 검색 인덱스')
            rb = rebuild()
        ok = all(v == 0 for v in rb.values())
        return emit(0 if ok else 1, ok=ok, dry_run=False, backup=bdir, updated_at=ts, rebuild=rb, **summary)
    finally:
        conn.close()


if __name__ == '__main__':
    sys.exit(main())
