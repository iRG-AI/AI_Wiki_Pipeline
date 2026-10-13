#!/usr/bin/env python3
"""
scripts/recategorize_tips.py + lib/kakao_parse.classify 회귀 테스트 — 네트워크 0회, 실제 Vault·data/ 무변경 (v4.9)

  /opt/homebrew/bin/python3 scripts/test_recategorize_tips.py

임시 Vault·임시 장부·임시 백업 폴더로 돌린다. 끝에 'N/N PASS' 를 찍고 실패가 있으면 종료 코드 1.
"""
import contextlib, io, json, os, shutil, sqlite3, sys, tempfile
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

import recategorize_tips as m   # noqa: E402
import sync_obsidian as so      # noqa: E402
import library_db as ldb        # noqa: E402
import kakao_parse as kp        # noqa: E402

TS = '2026-10-12T00:00:00.000Z'
HEX = '3cff67ccdbf881b2b0123456789abcde'

results = []
def check(name, cond, detail=''):
    results.append((name, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}  {name}' + (f'  — {detail}' if detail and not cond else ''))


# ── 1. classify 규칙 ──
print('▶ classify (v4.9 규칙)')
check('노션 페이지 주소는 Notion 태그 아님', kp.classify(f'https://grand-count-2aa.notion.site/x-{HEX}') == ('기타', []))
check('app.notion.com·notion.so 도 같음',
      kp.classify('https://app.notion.com/p/abc') == ('기타', []) and kp.classify('https://notion.so/abc') == ('기타', []))
check('notion.com(노션 회사 사이트)은 Notion', kp.classify('https://notion.com/templates/x') == ('지식관리', ['Notion']))
check('글자에 「노션」 → Notion·지식관리', kp.classify('https://a.notion.site/x', 'AI로 노션 대시보드 만들기') == ('지식관리', ['Notion']))
check('「클로드코드」 → ClaudeCode·Claude·개발툴',
      kp.classify('https://a.notion.site/x', '클로드코드로 광고 영상 만들기') == ('개발툴', ['ClaudeCode', 'Claude']))
check('「클로드 코드」(띄어쓰기) 도 같음', kp.classify('https://youtu.be/x', '클로드 코드 TOP 5')[1] == ['ClaudeCode', 'Claude', 'YouTube'])
check('「클로드」 → Claude·모델/LLM', kp.classify('https://a.notion.site/x', '클로드 확장팩 35개') == ('모델/LLM', ['Claude']))
check('「제미나이」·「챗지피티」 → Gemini·GPT', kp.classify('https://x.com/a', '제미나이와 챗지피티 비교') == ('모델/LLM', ['Gemini', 'GPT']))
check('「옵시디언」 → Obsidian', kp.classify('https://x.com/a', '옵시디언 플러그인')[1] == ['Obsidian'])
check('「프롬프트」 우선 → 프롬프트', kp.classify('https://a.notion.site/x', '클로드 프롬프트 모음') == ('프롬프트', ['Claude', '프롬프트']))
check('GitHub 은 개발툴', kp.classify('https://github.com/a/b') == ('개발툴', ['GitHub']))
check('「커서」는 태그 아님(일반 명사)', kp.classify('https://x.com/a', '마우스 커서 바꾸기') == ('기타', []))
check('영문 규칙 그대로', kp.classify('https://x.com/claude-code-tips') == ('개발툴', ['ClaudeCode', 'Claude']))
g = kp.guess_meta(f'https://a.notion.site/{HEX}', '')
check('guess_meta: 추정 제목 「노션 자료」 가 Notion 태그를 만들지 않음', g['tags'] == [] and g['category'] == '기타', str(g))
g = kp.guess_meta(f'https://a.notion.site/x-{HEX}', '', '클로드코드 필수 플러그인')
check('guess_meta: 조회 제목으로 분류', (g['category'], g['tags']) == ('개발툴', ['ClaudeCode', 'Claude']), str(g))

# ── 2. decide ──
print('▶ decide')
def row(url, title, cat, tags, src='x'):
    return {'url': url, 'title': title, 'category': cat, 'tags': tags, 'source': src}
d = m.decide(row(f'https://a.notion.site/x-{HEX}', '클로드코드로 광고 영상 만들기', '지식관리', ['Notion'], 'a.notion.site'))
check('v4.8 규칙 값(URL 만) → 다시 매김', d['rule_made'] and (d['category'], d['tags']) == ('개발툴', ['ClaudeCode', 'Claude']))
d = m.decide(row(f'https://a.notion.site/x-{HEX}', 'Higgsfield에서 GPT API 연결', '지식관리', ['GPT', 'Notion']))
check('v4.8 규칙 값(URL + 제목) → 다시 매김', d['rule_made'] and (d['category'], d['tags']) == ('모델/LLM', ['GPT']))
d = m.decide(row(f'https://a.notion.site/x-{HEX}', 'MarkItDown 변환', '개발툴', ['MarkItDown']))
check('사람이 고른 값 → 그대로', not d['rule_made'] and (d['category'], d['tags']) == ('개발툴', ['MarkItDown']))
d = m.decide(row(f'https://a.notion.site/{HEX}', '노션 자료 (제목 미확인)', '지식관리', ['Notion']))
check('추정 제목은 판정 글자에서 뺌 → 기타·태그 없음', d['rule_made'] and (d['category'], d['tags']) == ('기타', []))
d = m.decide(row('https://www.sume.so/a', 'x', '뉴스/트렌드', ['AI'], 'https://www.sume.so'))
check('출처 https:// → 호스트(www 제거)', d['source'] == 'sume.so' and not d['source_mismatch'])
d = m.decide(row('https://b.com/a', 'x', '기타', [], 'https://c.com'))
check('출처 호스트가 URL 과 다르면 그대로 + 보고', d['source'] == 'https://c.com' and d['source_mismatch'])
d = m.decide(row('https://b.com/a', 'x', '기타', [], 'b.com'))
check('이미 호스트면 그대로', d['source'] == 'b.com' and not d['source_mismatch'])

# ── 3. 임시 장부·Vault 로 전체 흐름 ──
TIPS = [
    # record_id, url, title, source, tags, category, extra_note
    ('tip-a1', f'https://a.notion.site/x-{HEX}', '클로드코드로 광고 영상 만들기', 'a.notion.site', ['Notion'], '지식관리', '\n## 관련\n\n- [[Claude Code]]\n'),
    ('tip-b2', 'https://oavoir.notion.site/y', 'Obsidian 활용 정리', 'https://oavoir.notion.site', ['Obsidian'], '지식관리', ''),
    ('tip-c3', f'https://c.notion.site/z-{HEX}', 'MarkItDown 변환', 'c.notion.site', ['MarkItDown'], '개발툴', ''),
    ('tip-d4', f'https://d.notion.site/w-{HEX}', '클로드 확장팩 35개', 'd.notion.site', ['Notion'], '지식관리', 'HANDEDIT'),
    ('tip-e5', 'https://youtu.be/abc', '클로드 코드 TOP 5', 'youtu.be', ['YouTube'], '기타', None),   # 노트 없음
    ('tip-f6', 'https://x.com/a', '그대로', 'x.com', [], '기타', ''),
]


def make_env():
    root = tempfile.mkdtemp(prefix='recat_test_')
    vault, db, bk = os.path.join(root, 'vault'), os.path.join(root, 'library.db'), os.path.join(root, 'bk')
    tips_dir = os.path.join(vault, so.TIPS_FOLDER)
    os.makedirs(tips_dir)
    conn = ldb.open_db(db)
    ldb.apply_schema(conn)
    with conn:
        conn.execute('INSERT INTO videos (record_id, video_id, title, created_at, updated_at) VALUES (?,?,?,?,?)',
                     ('vid-1', 'VVVVVVVVVVV', '영상', TS, TS))
        for rid, url, title, src, tags, cat, _ in TIPS:
            conn.execute('INSERT INTO tips (record_id, title, url, url_key, source, tags, category, status, importance, saved_date, '
                         'created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                         (rid, title, url, rid, src, json.dumps(tags, ensure_ascii=False), cat, '미확인', '중', '2026-10-05', TS, TS))
    rows = {r['record_id']: dict(r) for r in conn.execute('SELECT * FROM tips')}
    conn.close()
    for rid, url, title, src, tags, cat, extra in TIPS:
        if extra is None:
            continue
        r = rows[rid]
        r['tags'] = tags
        body = so.tip_note_md(r)
        if extra == 'HANDEDIT':
            body = body.replace('- 🏷 태그: Notion', '- 🏷 태그: Notion, 내가 붙인 태그')
        else:
            body += extra
        open(os.path.join(tips_dir, so.safe_filename(f'20261005_{title}') + '.md'), 'w', encoding='utf-8').write(body)
    m.BACKUP_ROOT = bk
    return root, vault, db, bk


def run(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = m.main(argv)
    out = buf.getvalue()
    res = json.loads([l for l in out.splitlines() if l.startswith('RESULT_JSON:')][-1][len('RESULT_JSON:'):])
    return code, res, out


def db_rows(db):
    c = sqlite3.connect(db); c.row_factory = sqlite3.Row
    out = {r['record_id']: dict(r) for r in c.execute('SELECT * FROM tips')}
    c.close()
    return out


def note(vault, title):
    return open(os.path.join(vault, so.TIPS_FOLDER, so.safe_filename(f'20261005_{title}') + '.md'), encoding='utf-8').read()


print('▶ dry-run')
root, vault, db, bk = make_env()
try:
    before_db = open(db, 'rb').read()
    before_note = note(vault, '클로드코드로 광고 영상 만들기')
    code, res, out = run(['--db', db, '--vault', vault])
    check('dry-run 종료 0', code == 0, out[-300:])
    check('대상 3행(a1 분류 · b2 출처 · e5 분류)', res['rows'] == 3, str(res))
    check('손으로 고친 노트 1건 건너뜀', res['skipped_note'] == 1 and '건너뜀 tip-d4' in out, out[-500:])
    check('사람이 고른 값 유지 1건(c3)', res['manual_kept'] == 1, str(res))
    check('dry-run: 장부·노트 무변경 · 백업 없음',
          open(db, 'rb').read() == before_db and note(vault, '클로드코드로 광고 영상 만들기') == before_note and not os.path.exists(bk))

    print('▶ apply')
    code, res, out = run(['--apply', '--no-rebuild', '--db', db, '--vault', vault])
    check('apply 종료 0', code == 0, out[-400:])
    r = db_rows(db)
    check('a1: 장부 개발툴 · ClaudeCode,Claude · updated_at 갱신',
          r['tip-a1']['category'] == '개발툴' and json.loads(r['tip-a1']['tags']) == ['ClaudeCode', 'Claude']
          and r['tip-a1']['updated_at'] != TS, str(r['tip-a1']))
    check('b2: 출처 호스트만 · 분류 그대로', r['tip-b2']['source'] == 'oavoir.notion.site' and r['tip-b2']['category'] == '지식관리')
    check('e5: 노트 없어도 장부는 고침', r['tip-e5']['category'] == '개발툴' and json.loads(r['tip-e5']['tags']) == ['ClaudeCode', 'Claude', 'YouTube'])
    check('c3·d4·f6: 장부 그대로(updated_at 포함)',
          all(r[k]['updated_at'] == TS for k in ('tip-c3', 'tip-d4', 'tip-f6')) and r['tip-d4']['category'] == '지식관리')
    t = note(vault, '클로드코드로 광고 영상 만들기')
    check('a1 노트: 프론트매터 category·keywords', 'category: "개발툴"' in t and 'keywords: ["ClaudeCode", "Claude"]' in t)
    check('a1 노트: 본문 카테고리·태그 줄',
          '- 📂 카테고리: 개발툴  ·  중요도: 중  ·  상태: 미확인' in t and '- 🏷 태그: ClaudeCode, Claude' in t)
    check('a1 노트: 붙어 있던 관련 링크 보존 · 제목 그대로', t.endswith('- [[Claude Code]]\n') and '# 클로드코드로 광고 영상 만들기' in t)
    t = note(vault, 'Obsidian 활용 정리')
    check('b2 노트: channel·출처 줄만 바뀜',
          'channel: "oavoir.notion.site"' in t and '  ·  출처: oavoir.notion.site\n' in t
          and 'link_url: https://oavoir.notion.site/y' in t and 'category: "지식관리"' in t)
    check('d4 노트(손으로 고침) 그대로', '내가 붙인 태그' in note(vault, '클로드 확장팩 35개'))
    man = json.load(open(os.path.join(res['backup'], 'manifest.json'), encoding='utf-8'))
    check('백업: 장부 사본 · 노트 원본 2개 · manifest 3행',
          os.path.exists(os.path.join(res['backup'], 'library.db')) and len(man['edited']) == 2 and len(man['rows']) == 3, str(man['edited']))
    bk_note = open(os.path.join(res['backup'], 'vault', so.TIPS_FOLDER, so.safe_filename('20261005_클로드코드로 광고 영상 만들기') + '.md'),
                   encoding='utf-8').read()
    check('백업 노트 = 고치기 전 원본', bk_note == before_note)

    print('▶ 다시 돌리기')
    code, res, out = run(['--apply', '--no-rebuild', '--db', db, '--vault', vault])
    check('두 번째 apply: 0행 · 백업 안 만듦', code == 0 and res['rows'] == 0 and 'backup' not in res, str(res))

finally:
    shutil.rmtree(root, ignore_errors=True)

print('▶ 계획 뒤 장부가 바뀌면 전체 롤백')
root, vault, db, bk = make_env()
try:
    conn = ldb.open_existing(db)
    plan, *_ = m.build_plan(conn, vault)
    c = sqlite3.connect(db)
    with c:
        c.execute("UPDATE tips SET tags='[\"Notion\", \"사람\"]' WHERE record_id='tip-e5'")   # 계획 뒤 다른 곳에서 고침
    c.close()
    try:
        m.apply_db(conn, plan)
        check('조건 불일치 → RuntimeError', False)
    except RuntimeError as e:
        check('조건 불일치 → RuntimeError', '롤백' in str(e), str(e))
    conn.close()
    r = db_rows(db)
    check('앞선 행(a1·b2)도 롤백 — 장부 그대로',
          r['tip-a1']['category'] == '지식관리' and r['tip-b2']['source'] == 'https://oavoir.notion.site' and r['tip-a1']['updated_at'] == TS)
finally:
    shutil.rmtree(root, ignore_errors=True)

print('▶ 입력 오류')
code, res, _ = run(['--bogus'])
check('모르는 인자 → 종료 2', code == 2 and not res['ok'])
code, res, _ = run(['--vault', '/nonexistent/vault'])
check('Vault 꿀팁 폴더 없음 → 종료 2', code == 2 and not res['ok'])

check('네트워크 호출 0회', not NET_CALLS, str(NET_CALLS[:1]))
n_ok = sum(1 for _, ok in results if ok)
print(f'\n{n_ok}/{len(results)} PASS')
sys.exit(0 if n_ok == len(results) else 1)
