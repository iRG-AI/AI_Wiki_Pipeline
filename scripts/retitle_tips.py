#!/usr/bin/env python3
"""
꿀팁 제목 보완 — 장부 tips 의 제목을 고치고 Obsidian 노트·링크까지 맞춘다 (v4.4)

  /opt/homebrew/bin/python3 scripts/retitle_tips.py <CSV>              # dry-run (기본) — 아무것도 쓰지 않는다
  /opt/homebrew/bin/python3 scripts/retitle_tips.py <CSV> --apply      # 실제 반영
      [--no-rebuild]   반영 뒤 build_obsidian_wiki.py · build_search_index.py 를 부르지 않는다 (테스트·사본 검증용)
      [--db PATH] [--vault PATH]   장부·Vault 경로 바꾸기 (사본 검증용, 기본 = data/library.db · sync_obsidian.VAULT)
  종료 코드: 0 성공 · 1 반영 중 실패 · 2 입력·검증 실패(아무것도 쓰지 않음)

CSV (UTF-8, 머리글 필수): record_id,old_title,new_title
  - old_title 은 지금 장부의 제목과 글자 그대로 같아야 한다(다르면 그 행이 이미 바뀐 것 — 전체 중단).

하는 일 (한 행마다):
  1. 장부 tips: title = new_title, updated_at = 지금 (시트 미러가 이 워터마크로 변경분을 보낸다).
     memo 가 카톡 인제스트의 자동 메모(lib/kakao_parse.py 의 '원문 확인 필요' 류)면 비운다. 사람이 쓴 메모는 그대로 둔다.
  2. 「AI 꿀팁」 노트(프론트매터 notion_id = record_id)를 제자리에서 고친다 — title·memo 줄, 첫 H1, '- 📝 메모:' 줄.
     다시 생성하지 않는다(build_obsidian_wiki 가 붙인 관련 링크 등 나머지 내용 보존).
     파일명을 '<저장일>_<새 제목>.md' 로 바꾼다(sync_obsidian.sync_tips 와 같은 규칙, 이미 있으면 record_id 끝 6자리).
  3. Vault 의 [[옛 파일명]] 링크를 새 파일명으로 바꾼다. 별칭이 옛 제목이면 별칭도 새 제목으로.
     _trash/ 와 숨김 폴더는 건드리지 않는다.
  4. (--no-rebuild 가 아니면) build_obsidian_wiki.py → build_search_index.py — sync_obsidian 이 변경 뒤 부르는 것과 같다.

안전장치:
  - 검증(행 존재·옛 제목 일치·노트 1개·편집 지점 1곳씩·새 파일명 충돌)을 전부 통과해야 쓰기 시작한다.
  - 쓰기 전에 data/retitle_backup/<YYYYmmdd-HHMMSS>/ 에 장부 사본(온라인 백업 API)과 바뀔 Vault 파일 원본, manifest.json 을 남긴다.
    되돌리기: 장부는 사본으로 교체, Vault 는 manifest 의 renamed 를 거꾸로 + 원본 복사 → sheet_mirror.py --full.
  - 장부 UPDATE 는 한 트랜잭션, 조건은 record_id 와 옛 제목 둘 다. 행 수가 1이 아니면 전체 롤백.
  - 네트워크 호출 없음(4단계의 검색 인덱스만 Gemini 임베딩을 부른다 — 바뀐 노트 수만큼).
"""
import csv, json, os, re, shutil, sqlite3, subprocess, sys, time, unicodedata
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, 'lib'))

import sync_obsidian as so                     # noqa: E402  VAULT·TIPS_FOLDER·safe_filename·_q·fm 규칙 재사용
import library_db as ldb                       # noqa: E402

# lib/kakao_parse.py:guess_meta 가 붙이는 자동 메모 — 제목을 확인했으니 지운다
AUTO_MEMOS = {'원문 확인 필요', '슬러그에 한글 제목 없음 — 원문 확인 필요'}
BACKUP_ROOT = os.path.join(ldb.DATA_DIR, 'retitle_backup')


def log(msg=''):
    print(msg, flush=True)


def nfc(s):
    return unicodedata.normalize('NFC', s or '')


def nfd(s):
    return unicodedata.normalize('NFD', s or '')


def now_iso():
    dt = datetime.now(timezone.utc)
    return dt.strftime('%Y-%m-%dT%H:%M:%S.') + f'{dt.microsecond // 1000:03d}Z'   # kakao_ingest·scheduler 와 같은 형식


def emit(code, **kw):
    print('RESULT_JSON:' + json.dumps(kw, ensure_ascii=False), flush=True)
    return code


class Invalid(Exception):
    pass


# ── 입력 ──
def read_csv(path):
    with open(path, encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    need = {'record_id', 'old_title', 'new_title'}
    if not rows or not need.issubset(rows[0].keys()):
        raise Invalid(f'CSV 머리글은 {sorted(need)} 이어야 하고 행이 1개 이상이어야 한다')
    out, seen = [], set()
    for i, r in enumerate(rows, 2):
        rid, old, new = (r['record_id'] or '').strip(), nfc(r['old_title'] or ''), nfc((r['new_title'] or '').strip())
        if not rid or not new:
            raise Invalid(f'CSV {i}행: record_id·new_title 이 비었다')
        if rid in seen:
            raise Invalid(f'CSV {i}행: record_id 중복 {rid}')
        if new == old:
            raise Invalid(f'CSV {i}행: 새 제목이 옛 제목과 같다')
        if len(new) > 200:
            raise Invalid(f'CSV {i}행: 새 제목 200자 초과')   # kakao_ingest 와 같은 상한
        if '|' in new or '[[' in new or ']]' in new:
            raise Invalid(f'CSV {i}행: 새 제목에 | · [[ · ]] 금지 — Obsidian 링크 [[파일|별칭]] 을 깨뜨린다')
        seen.add(rid)
        out.append({'record_id': rid, 'old_title': old, 'new_title': new})
    return out


# ── 노트 편집 계획 ──
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


def _sub_once(pattern, repl, text, what, flags=0):
    new, n = re.subn(pattern, lambda m: repl, text, count=0, flags=flags)
    if n != 1:
        raise Invalid(f'{what} 편집 지점이 1곳이 아니다({n}곳) — 손으로 고친 노트일 수 있다')
    return new


def edit_note(text, old_title, new_title, old_memo, new_memo):
    """노트 본문 문자열 → 고친 문자열. 편집 지점이 정확히 1곳씩이 아니면 Invalid."""
    text = nfc(text)
    m = so.FM_RE.match(text)
    if not m:
        raise Invalid('프론트매터 없음')
    fm, body = text[:m.end()], text[m.end():]
    fm = _sub_once(r'^title: .*$', f'title: "{so._q(new_title)}"', fm, 'title', re.M)
    if old_memo != new_memo:
        fm = _sub_once(r'^memo: .*$', f'memo: "{so._q(new_memo)}"', fm, 'memo', re.M)
    body = _sub_once(r'^# ' + re.escape(old_title) + r'[ \t]*$', f'# {new_title}', body, 'H1', re.M)
    if old_memo != new_memo and old_memo:
        pat = r'^- 📝 메모: ' + re.escape(old_memo) + r'[ \t]*\n'
        body = _sub_once(pat, f'- 📝 메모: {new_memo}\n' if new_memo else '', body, '메모 줄', re.M)
    return fm + body


# ── 링크 치환 ──
def link_pattern(old_stem):
    alts = sorted({re.escape(old_stem), re.escape(nfd(old_stem))}, key=len, reverse=True)
    folder = '|'.join(sorted({re.escape(so.TIPS_FOLDER + '/'), re.escape(nfd(so.TIPS_FOLDER) + '/')}))
    # 별칭에는 홑 ']' 가 올 수 있다(예: '[시크아] 디자인 …') — ']]' 앞까지
    return re.compile(r'\[\[(' + folder + r')?(?:' + '|'.join(alts) + r')(#[^\]|]*)?(?:\|((?:[^\]]|\](?!\]))*))?\]\]')


def rewrite_links(text, pat, new_stem, old_title, new_title):
    def repl(m):
        prefix, anchor, alias = m.group(1) or '', m.group(2) or '', m.group(3)
        out = '[[' + nfc(prefix) + new_stem + anchor
        if alias is not None:
            out += '|' + (new_title if nfc(alias) == old_title else alias)
        return out + ']]'
    return pat.subn(repl, text)


def vault_md_files(vault):
    for root, dirs, files in os.walk(vault):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '_trash']
        for f in files:
            if f.endswith('.md'):
                yield os.path.join(root, f)


# ── 계획 ──
def build_plan(rows, conn, vault):
    tips_dir = os.path.join(vault, so.TIPS_FOLDER)
    notes = tip_notes(tips_dir)
    plan, taken = [], set()
    for r in rows:
        rec = conn.execute('SELECT record_id, title, memo, saved_date FROM tips WHERE record_id = ?', (r['record_id'],)).fetchone()
        if not rec:
            raise Invalid(f'장부에 없는 record_id {r["record_id"]}')
        cur = nfc(rec['title'])
        if cur != r['old_title']:
            raise Invalid(f'{r["record_id"]}: 장부 제목이 옛 제목과 다르다 (장부 "{cur}" / CSV "{r["old_title"]}")')
        old_memo = nfc(rec['memo'])
        new_memo = '' if old_memo in AUTO_MEMOS else old_memo
        files = notes.get(r['record_id'], [])
        if len(files) > 1:
            raise Invalid(f'{r["record_id"]}: 같은 notion_id 꿀팁 노트가 {len(files)}개 {files}')
        item = {**r, 'old_memo': old_memo, 'new_memo': new_memo, 'old_file': None, 'new_file': None, 'note_text': None, 'links': {}}
        if files:
            old_file = files[0]
            text = open(os.path.join(tips_dir, old_file), encoding='utf-8').read()
            item['note_text'] = edit_note(text, r['old_title'], r['new_title'], old_memo, new_memo)
            saved = rec['saved_date'] or ''
            date_part = saved[:10].replace('-', '') if saved else '00000000'
            new_file = nfc(so.safe_filename(f"{date_part}_{r['new_title']}") + '.md')
            if new_file != old_file and (os.path.exists(os.path.join(tips_dir, new_file)) or new_file in taken):
                new_file = nfc(so.safe_filename(f"{date_part}_{r['new_title']}_{r['record_id'][-6:]}") + '.md')
                if os.path.exists(os.path.join(tips_dir, new_file)) or new_file in taken:
                    raise Invalid(f'{r["record_id"]}: 새 파일명 충돌 {new_file}')
            taken.add(new_file)
            item['old_file'], item['new_file'] = old_file, new_file
        plan.append(item)

    # 링크: 파일명이 바뀌는 행만. 여러 행이 같은 파일을 건드릴 수 있어 파일 단위로 누적한다.
    renames = [p for p in plan if p['old_file'] and p['old_file'] != p['new_file']]
    link_edits = {}   # 절대경로 -> (새 본문, 치환 수)
    if renames:
        pats = [(link_pattern(p['old_file'][:-3]), p) for p in renames]
        tip_paths = {os.path.join(tips_dir, p['old_file']) for p in plan if p['old_file']}
        for path in vault_md_files(vault):
            if path in tip_paths:
                continue   # 대상 노트 자체는 노트 편집에서 처리
            try:
                text = open(path, encoding='utf-8').read()
            except (OSError, UnicodeDecodeError):
                continue
            total, new = 0, text
            for pat, p in pats:
                new, n = rewrite_links(new, pat, p['new_file'][:-3], p['old_title'], p['new_title'])
                if n:
                    p['links'][os.path.relpath(path, vault)] = n
                total += n
            if total:
                link_edits[path] = (new, total)
        # 대상 노트끼리 서로 링크하는 경우
        for p in plan:
            if p['note_text'] is None:
                continue
            for pat, q in pats:
                if q is not p:
                    p['note_text'], _ = rewrite_links(p['note_text'], pat, q['new_file'][:-3], q['old_title'], q['new_title'])
    return plan, link_edits


# ── 반영 ──
def backup(db_path, vault, plan, link_edits):
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
    tips_dir = os.path.join(vault, so.TIPS_FOLDER)
    files = [os.path.join(tips_dir, p['old_file']) for p in plan if p['old_file']] + list(link_edits)
    for f in files:
        rel = os.path.relpath(f, vault)
        os.makedirs(os.path.join(d, 'vault', os.path.dirname(rel)), exist_ok=True)
        shutil.copy2(f, os.path.join(d, 'vault', rel))
    manifest = {
        'created_at': now_iso(), 'db': os.path.abspath(db_path), 'vault': os.path.abspath(vault),
        'rows': [{k: p[k] for k in ('record_id', 'old_title', 'new_title', 'old_memo', 'new_memo')} for p in plan],
        'renamed': [{'from': os.path.join(so.TIPS_FOLDER, p['old_file']), 'to': os.path.join(so.TIPS_FOLDER, p['new_file'])}
                    for p in plan if p['old_file'] and p['old_file'] != p['new_file']],
        'edited': [os.path.relpath(f, vault) for f in files],
    }
    open(os.path.join(d, 'manifest.json'), 'w', encoding='utf-8').write(json.dumps(manifest, ensure_ascii=False, indent=2))
    return d


def apply_db(conn, plan):
    ts = now_iso()
    with conn:   # 한 트랜잭션 — 예외면 전부 롤백
        for p in plan:
            cur = conn.execute('UPDATE tips SET title = ?, memo = ?, updated_at = ? WHERE record_id = ? AND title = ?',
                               (p['new_title'], p['new_memo'], ts, p['record_id'], p['old_title']))
            if cur.rowcount != 1:
                raise RuntimeError(f'{p["record_id"]}: UPDATE 행 수 {cur.rowcount} ≠ 1 — 롤백')
    return ts


def apply_vault(vault, plan, link_edits):
    tips_dir = os.path.join(vault, so.TIPS_FOLDER)
    for p in plan:
        if not p['old_file']:
            continue
        old_path, new_path = os.path.join(tips_dir, p['old_file']), os.path.join(tips_dir, p['new_file'])
        open(old_path, 'w', encoding='utf-8').write(p['note_text'])
        if new_path != old_path:
            os.rename(old_path, new_path)
    for path, (text, _) in link_edits.items():
        open(path, 'w', encoding='utf-8').write(text)


def rebuild():
    out = {}
    for name in ('build_obsidian_wiki.py', 'build_search_index.py'):
        r = subprocess.run([sys.executable, os.path.join(REPO_ROOT, name)], capture_output=True, text=True)
        out[name] = r.returncode
        log(f'  {"✅" if r.returncode == 0 else "❌"} {name} (종료 {r.returncode})')
        if r.returncode != 0:
            log((r.stderr or '')[-400:])
    return out


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    apply_ = '--apply' in argv
    no_rebuild = '--no-rebuild' in argv
    db_path, vault, csv_path = ldb.DB_PATH, so.VAULT, None
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
        if a.startswith('--'):
            if a not in ('--apply', '--no-rebuild'):
                return emit(2, ok=False, error=f'모르는 옵션 {a}')
        elif csv_path is None:
            csv_path = a
        else:
            return emit(2, ok=False, error='CSV 는 하나만')
        i += 1
    if not csv_path:
        log(__doc__)
        return emit(2, ok=False, error='CSV 경로 필요')
    if not os.path.isdir(os.path.join(vault, so.TIPS_FOLDER)):
        return emit(2, ok=False, error=f'Vault 꿀팁 폴더 없음: {vault}')

    try:
        rows = read_csv(csv_path)
        conn = ldb.open_existing(db_path, readonly=not apply_)
    except (Invalid, OSError, RuntimeError) as e:
        log(f'❌ {e}')
        return emit(2, ok=False, error=str(e)[:300])
    try:
        try:
            plan, link_edits = build_plan(rows, conn, vault)
        except (Invalid, OSError) as e:
            log(f'❌ 검증 실패 — 아무것도 쓰지 않았습니다: {e}')
            return emit(2, ok=False, error=str(e)[:300])

        log(f'📝 꿀팁 제목 보완 {len(plan)}건 {"(apply)" if apply_ else "(dry-run)"}\n')
        for p in plan:
            log(f'  {p["record_id"][:8]} | "{p["old_title"]}" → "{p["new_title"]}"')
            if p['old_memo'] != p['new_memo']:
                log(f'           메모 "{p["old_memo"]}" → "{p["new_memo"]}"')
            if p['old_file']:
                log(f'           노트 {p["old_file"]}' + (f' → {p["new_file"]}' if p['old_file'] != p['new_file'] else ' (파일명 그대로)'))
            else:
                log('           노트 없음 — 다음 sync_obsidian 이 새 제목으로 만든다')
            for rel, n in sorted(p['links'].items()):
                log(f'           링크 {n}곳 · {rel}')
        summary = dict(rows=len(plan), notes=sum(1 for p in plan if p['old_file']),
                       renamed=sum(1 for p in plan if p['old_file'] and p['old_file'] != p['new_file']),
                       memo_cleared=sum(1 for p in plan if p['old_memo'] != p['new_memo']),
                       link_files=len(link_edits), links=sum(n for _, n in link_edits.values()))
        if not apply_:
            log('\n👀 dry-run — 장부·Vault 무변경. 반영은 --apply')
            return emit(0, ok=True, dry_run=True, **summary)

        try:
            bdir = backup(db_path, vault, plan, link_edits)
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
            apply_vault(vault, plan, link_edits)
        except Exception as e:
            log(f'❌ Vault 반영 중 실패 — 장부는 이미 바뀜. 백업 manifest 로 되돌릴 것: {e}')
            return emit(1, ok=False, error=str(e)[:300], backup=bdir, updated_at=ts, **summary)
        log(f'📂 노트 {summary["notes"]}개 수정 · 이름 변경 {summary["renamed"]}개 · 링크 {summary["links"]}곳({summary["link_files"]}개 파일)')
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
