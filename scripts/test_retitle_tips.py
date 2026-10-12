#!/usr/bin/env python3
"""
scripts/retitle_tips.py 회귀 테스트 — 네트워크 0회, 실제 Vault·data/ 무변경 (v4.4)

  /opt/homebrew/bin/python3 scripts/test_retitle_tips.py

임시 Vault·임시 장부·임시 백업 폴더로 돌린다. 끝에 'N/N PASS' 를 찍고 실패가 있으면 종료 코드 1.
"""
import contextlib, hashlib, io, json, os, shutil, sqlite3, sys, tempfile, unicodedata
import urllib.request

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, 'scripts'))
sys.path.insert(0, os.path.join(REPO_ROOT, 'lib'))
sys.path.insert(0, REPO_ROOT)

NET_CALLS = []
def _no_net(*a, **k):
    NET_CALLS.append(a)
    raise RuntimeError('네트워크 호출 금지')
urllib.request.urlopen = _no_net

import retitle_tips as m        # noqa: E402
import sync_obsidian as so      # noqa: E402
import library_db as ldb        # noqa: E402

TS = '2026-10-12T00:00:00.000Z'
TIPS = [
    # record_id, title, memo, saved_date
    ('tip-aaaaaa111111', '유튜브 영상 (제목 미확인)', '원문 확인 필요', '2026-10-11'),
    ('tip-bbbbbb222222', 'courses', '', '2026-10-10'),
    ('tip-cccccc333333', '노션 자료 (제목 미확인)', '슬러그에 한글 제목 없음 — 원문 확인 필요', '2026-10-12'),
    ('tip-dddddd444444', 'keep me', '사람이 쓴 메모', '2026-10-09'),
    ('tip-eeeeee555555', '다른 꿀팁', '', '2026-10-09'),
]

results = []
def check(name, cond, detail=''):
    results.append((name, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}  {name}' + (f'  — {detail}' if detail and not cond else ''))


def make_env():
    root = tempfile.mkdtemp(prefix='retitle_test_')
    vault, db, bk = os.path.join(root, 'vault'), os.path.join(root, 'library.db'), os.path.join(root, 'bk')
    tips_dir = os.path.join(vault, so.TIPS_FOLDER)
    os.makedirs(tips_dir)
    conn = ldb.open_db(db)
    ldb.apply_schema(conn)
    with conn:
        conn.execute('INSERT INTO videos (record_id, video_id, title, created_at, updated_at) VALUES (?,?,?,?,?)',
                     ('vid-1', 'VVVVVVVVVVV', '영상', TS, TS))
        for rid, title, memo, saved in TIPS:
            conn.execute('INSERT INTO tips (record_id, title, url, url_key, source, saved_date, memo, created_at, updated_at) '
                         'VALUES (?,?,?,?,?,?,?,?,?)', (rid, title, f'https://x/{rid}', rid, 'x', saved, memo, TS, TS))
    rows = {r['record_id']: dict(r) for r in conn.execute('SELECT * FROM tips')}
    conn.close()
    for rid, r in rows.items():
        r['tags'] = []
        fname = so.safe_filename(f"{r['saved_date'].replace('-', '')}_{r['title']}") + '.md'
        body = so.tip_note_md(r)
        if rid == 'tip-aaaaaa111111':
            body += '\n## 관련\n\n- [[Claude Code]]\n'     # build_obsidian_wiki 가 붙인 내용 — 보존돼야 한다
        open(os.path.join(tips_dir, fname), 'w', encoding='utf-8').write(body)
    os.makedirs(os.path.join(vault, '_wiki', 'concepts'))
    open(os.path.join(vault, '_wiki', 'concepts', 'AI 생산성.md'), 'w', encoding='utf-8').write(
        '# AI 생산성\n\n'
        '- [[20261011_유튜브 영상 (제목 미확인)|유튜브 영상 (제목 미확인)]] `youtube.com` 2026-10-11\n'
        '  > 유튜브 영상 (제목 미확인) 은 본문 글자라 그대로\n'
        '- [[20261010_courses|courses]] `x` 2026-10-10\n'
        '- [[20261010_coursesX]] 비슷한 이름은 그대로\n'
        '- [[AI 꿀팁/20261010_courses#요약|내 별칭]] 폴더·앵커·사용자 별칭\n'
        '- [[20261009_다른 꿀팁]] 무관\n')
    os.makedirs(os.path.join(vault, '_MOC'))
    # 디스크에 NFD 로 남은 링크 글자도 잡아야 한다
    open(os.path.join(vault, '_MOC', 'AI 꿀팁 MOC.md'), 'w', encoding='utf-8').write(
        unicodedata.normalize('NFD', '- [[20261012_노션 자료 (제목 미확인)]]\n- [[20261011_유튜브 영상 (제목 미확인)]]\n'))
    os.makedirs(os.path.join(vault, '_trash', 'x'))
    open(os.path.join(vault, '_trash', 'x', 'old.md'), 'w', encoding='utf-8').write('[[20261010_courses]]\n')
    os.makedirs(os.path.join(vault, '.obsidian'))
    open(os.path.join(vault, '.obsidian', 'w.md'), 'w', encoding='utf-8').write('[[20261010_courses]]\n')
    return root, vault, db, bk


def write_csv(root, rows, name='in.csv'):
    p = os.path.join(root, name)
    with open(p, 'w', encoding='utf-8') as f:
        f.write('record_id,old_title,new_title\n')
        for r in rows:
            f.write(','.join('"' + c.replace('"', '""') + '"' for c in r) + '\n')
    return p


def run(args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = m.main(args)
    out = buf.getvalue()
    res = {}
    for line in out.splitlines():
        if line.startswith('RESULT_JSON:'):
            res = json.loads(line[len('RESULT_JSON:'):])
    return code, res, out


def snapshot(root):
    h = {}
    for d, _, fs in os.walk(root):
        for f in fs:
            p = os.path.join(d, f)
            h[os.path.relpath(p, root)] = hashlib.sha1(open(p, 'rb').read()).hexdigest()
    return h


def tip(db, rid):
    c = sqlite3.connect(db); c.row_factory = sqlite3.Row
    r = dict(c.execute('SELECT * FROM tips WHERE record_id = ?', (rid,)).fetchone()); c.close()
    return r


GOOD = [
    ('tip-aaaaaa111111', '유튜브 영상 (제목 미확인)', '클로드 코드 TOP 5 — 일주일 순위'),
    ('tip-bbbbbb222222', 'courses', '강의: 메이크패밀리 라운지'),
    ('tip-cccccc333333', '노션 자료 (제목 미확인)', '[시크아] 디자인 리소스 리스트'),
    ('tip-dddddd444444', 'keep me', 'Keep "me"'),
]

# 1. dry-run — 무변경
root, vault, db, bk = make_env(); m.BACKUP_ROOT = bk
csvp = write_csv(root, GOOD)
before = snapshot(root)
code, res, out = run([csvp, '--db', db, '--vault', vault])
check('dry-run 종료 0 · ok', code == 0 and res.get('ok') and res.get('dry_run'), res)
check('dry-run 무변경(장부·Vault·백업 폴더)', snapshot(root) == before)
check('dry-run 집계 rows 4 · renamed 4 · memo_cleared 2', (res.get('rows'), res.get('renamed'), res.get('memo_cleared')) == (4, 4, 2), res)
check('dry-run 링크 파일 2 (_trash·.obsidian 제외)', res.get('link_files') == 2, res)

# 2. apply
code, res, out = run([csvp, '--apply', '--no-rebuild', '--db', db, '--vault', vault])
check('apply 종료 0 · ok', code == 0 and res.get('ok'), out[-500:])
a = tip(db, 'tip-aaaaaa111111')
check('장부 제목 변경', a['title'] == '클로드 코드 TOP 5 — 일주일 순위')
check('자동 메모 비움', a['memo'] == '')
check('updated_at 새로 찍힘(형식 유지)', a['updated_at'] != TS and a['updated_at'].endswith('Z') and len(a['updated_at']) == 24, a['updated_at'])
check('사람 메모 보존', tip(db, 'tip-dddddd444444')['memo'] == '사람이 쓴 메모')
e = tip(db, 'tip-eeeeee555555')
check('대상 밖 행 무변경(updated_at 포함)', e['title'] == '다른 꿀팁' and e['updated_at'] == TS)
check('created_at 무변경', a['created_at'] == TS)

td = os.path.join(vault, so.TIPS_FOLDER)
names = set(os.listdir(td))
check('노트 파일명 변경', '20261011_클로드 코드 TOP 5 — 일주일 순위.md' in names and '20261011_유튜브 영상 (제목 미확인).md' not in names, names)
check('파일명 안전 변환(: → _)', '20261010_강의_ 메이크패밀리 라운지.md' in names, names)
note = open(os.path.join(td, '20261011_클로드 코드 TOP 5 — 일주일 순위.md'), encoding='utf-8').read()
check('노트 title·H1 변경', 'title: "클로드 코드 TOP 5 — 일주일 순위"' in note and '\n# 클로드 코드 TOP 5 — 일주일 순위\n' in note)
check('노트 memo 비움 · 메모 줄 삭제', 'memo: ""' in note and '📝 메모' not in note)
check('노트 나머지 내용 보존(관련 링크·notion_id·link_url)', '- [[Claude Code]]' in note and 'notion_id: tip-aaaaaa111111' in note
      and 'link_url: https://x/tip-aaaaaa111111' in note)
nd = open(os.path.join(td, '20261009_Keep _me_.md'), encoding='utf-8').read()
check('제목 따옴표는 _q 규칙(프론트매터)·원문(H1)', "title: \"Keep 'me'\"" in nd and '\n# Keep "me"\n' in nd)
check('사람 메모 줄 보존', '- 📝 메모: 사람이 쓴 메모' in nd)
check('노트 notion_id 로 장부와 대응 유지', so.fm_notion_id(os.path.join(td, '20261010_강의_ 메이크패밀리 라운지.md')) == 'tip-bbbbbb222222')

con = open(os.path.join(vault, '_wiki', 'concepts', 'AI 생산성.md'), encoding='utf-8').read()
check('링크+별칭(옛 제목) 치환', '[[20261011_클로드 코드 TOP 5 — 일주일 순위|클로드 코드 TOP 5 — 일주일 순위]]' in con, con)
check('본문 글자는 그대로', '> 유튜브 영상 (제목 미확인) 은 본문 글자라 그대로' in con)
check('폴더·앵커·사용자 별칭 유지', '[[AI 꿀팁/20261010_강의_ 메이크패밀리 라운지#요약|내 별칭]]' in con, con)
check('비슷한 이름·무관 링크 그대로', '[[20261010_coursesX]]' in con and '[[20261009_다른 꿀팁]]' in con)
moc = open(os.path.join(vault, '_MOC', 'AI 꿀팁 MOC.md'), encoding='utf-8').read()
check('NFD 링크 글자도 치환', '[[20261012_[시크아] 디자인 리소스 리스트]]' in moc and '[[20261011_클로드 코드 TOP 5 — 일주일 순위]]' in moc, moc)
check('_trash·숨김 폴더 무변경', open(os.path.join(vault, '_trash', 'x', 'old.md'), encoding='utf-8').read() == '[[20261010_courses]]\n'
      and open(os.path.join(vault, '.obsidian', 'w.md'), encoding='utf-8').read() == '[[20261010_courses]]\n')

bdirs = os.listdir(bk)
check('백업 폴더 1개', len(bdirs) == 1, bdirs)
bd = os.path.join(bk, bdirs[0])
man = json.load(open(os.path.join(bd, 'manifest.json'), encoding='utf-8'))
check('manifest renamed 4 · edited 6', len(man['renamed']) == 4 and len(man['edited']) == 6, man)
bc = sqlite3.connect(os.path.join(bd, 'library.db'))
check('백업 장부 = 반영 전 제목', bc.execute("SELECT title FROM tips WHERE record_id='tip-aaaaaa111111'").fetchone()[0] == '유튜브 영상 (제목 미확인)')
bc.close()
check('백업 Vault 원본 보존', os.path.exists(os.path.join(bd, 'vault', so.TIPS_FOLDER, '20261011_유튜브 영상 (제목 미확인).md')))

# 3. 같은 CSV 다시 — 옛 제목 불일치로 중단, 무변경
before = snapshot(root)
code, res, out = run([csvp, '--apply', '--no-rebuild', '--db', db, '--vault', vault])
check('재실행 = 옛 제목 불일치 → 종료 2', code == 2 and not res.get('ok'), res)
check('재실행 무변경(백업도 안 만듦)', snapshot(root) == before)

# 4. 검증 실패는 아무것도 쓰지 않는다 — 한 행이라도 틀리면 전체 중단
root, vault, db, bk = make_env(); m.BACKUP_ROOT = bk
before = snapshot(root)
for label, rows in (
    ('없는 record_id', [GOOD[1], ('tip-zzzz', 'x', 'y')]),
    ('record_id 중복', [GOOD[1], GOOD[1]]),
    ('새 제목 빈칸', [('tip-bbbbbb222222', 'courses', '  ')]),
    ('새 제목 = 옛 제목', [('tip-bbbbbb222222', 'courses', 'courses')]),
    ('옛 제목 불일치', [GOOD[1], ('tip-aaaaaa111111', '다른 제목', 'y')]),
    ('새 제목에 |', [('tip-bbbbbb222222', 'courses', '강의 | 라운지')]),
    ('새 제목에 ]]', [('tip-bbbbbb222222', 'courses', 'a]] b')]),
):
    code, res, _ = run([write_csv(root, rows, 'bad.csv'), '--apply', '--no-rebuild', '--db', db, '--vault', vault])
    os.remove(os.path.join(root, 'bad.csv'))
    check(f'검증 실패({label}) → 종료 2', code == 2 and not res.get('ok'), res)
check('검증 실패들 뒤 무변경', snapshot(root) == before)

# 5. 손으로 고친 노트(H1 없음) → 중단
td = os.path.join(vault, so.TIPS_FOLDER)
p = os.path.join(td, '20261010_courses.md')
txt = open(p, encoding='utf-8').read()
open(p, 'w', encoding='utf-8').write(txt.replace('\n# courses\n', '\n# 손으로 바꾼 제목\n'))
before = snapshot(root)
code, res, _ = run([write_csv(root, [GOOD[1]], 'h1.csv'), '--apply', '--no-rebuild', '--db', db, '--vault', vault])
check('H1 불일치 노트 → 종료 2', code == 2 and 'H1' in res.get('error', ''), res)
os.remove(os.path.join(root, 'h1.csv'))
check('H1 불일치 뒤 무변경', snapshot(root) == before)

# 6. 새 파일명 충돌 → record_id 끝 6자리
root, vault, db, bk = make_env(); m.BACKUP_ROOT = bk
td = os.path.join(vault, so.TIPS_FOLDER)
open(os.path.join(td, '20261010_다른 꿀팁.md'), 'w', encoding='utf-8').write('---\nnotion_id: other\n---\n')
code, res, out = run([write_csv(root, [('tip-bbbbbb222222', 'courses', '다른 꿀팁')]), '--apply', '--no-rebuild', '--db', db, '--vault', vault])
check('충돌 시 접미사 파일명', code == 0 and os.path.exists(os.path.join(td, '20261010_다른 꿀팁_222222.md'))
      and open(os.path.join(td, '20261010_다른 꿀팁.md'), encoding='utf-8').read() == '---\nnotion_id: other\n---\n', out[-400:])

# 7. 노트가 없는 행 — 장부만 고친다
root, vault, db, bk = make_env(); m.BACKUP_ROOT = bk
os.remove(os.path.join(vault, so.TIPS_FOLDER, '20261009_다른 꿀팁.md'))
code, res, out = run([write_csv(root, [('tip-eeeeee555555', '다른 꿀팁', '새 제목')]), '--apply', '--no-rebuild', '--db', db, '--vault', vault])
check('노트 없음 → 장부만 갱신 · notes 0', code == 0 and res.get('notes') == 0 and tip(db, 'tip-eeeeee555555')['title'] == '새 제목', res)

# 8. 별칭에 홑 ']' 가 든 링크도 치환 (예: 첫 보완으로 '[시크아] …' 가 된 노트를 다시 고칠 때)
root, vault, db, bk = make_env(); m.BACKUP_ROOT = bk
code, res, _ = run([write_csv(root, [GOOD[2]], 'c1.csv'), '--apply', '--no-rebuild', '--db', db, '--vault', vault])
cp = os.path.join(vault, '_wiki', 'concepts', 'AI 생산성.md')
open(cp, 'a', encoding='utf-8').write('- [[20261012_[시크아] 디자인 리소스 리스트|[시크아] 디자인 리소스 리스트]] 별칭에 괄호\n')
code, res, _ = run([write_csv(root, [('tip-cccccc333333', '[시크아] 디자인 리소스 리스트', '시크아 디자인 리소스')], 'c2.csv'),
                    '--apply', '--no-rebuild', '--db', db, '--vault', vault])
txt = open(cp, encoding='utf-8').read()
check('별칭에 ] 가 든 링크 치환', code == 0 and '[[20261012_시크아 디자인 리소스|시크아 디자인 리소스]] 별칭에 괄호' in txt
      and '[시크아] 디자인 리소스 리스트]]' not in txt, txt[-300:])
man = json.load(open(os.path.join(bk, sorted(os.listdir(bk))[-1], 'manifest.json'), encoding='utf-8'))
check('manifest 경로는 절대경로', os.path.isabs(man['db']) and os.path.isabs(man['vault']), man['db'])

# 9. 인자 오류
code, res, _ = run(['--apply'])
check('CSV 없음 → 종료 2', code == 2)
code, res, _ = run([csvp, '--bogus'])
check('모르는 옵션 → 종료 2', code == 2)
code, res, _ = run([csvp, '--db', db, '--vault', os.path.join(root, 'nope')])
check('Vault 없음 → 종료 2', code == 2)

check('네트워크 호출 0회', not NET_CALLS, NET_CALLS)

passed = sum(1 for _, ok in results if ok)
print(f'\n{passed}/{len(results)} PASS')
sys.exit(0 if passed == len(results) else 1)
