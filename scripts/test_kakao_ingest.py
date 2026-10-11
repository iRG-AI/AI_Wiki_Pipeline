#!/usr/bin/env python3
"""kakao_ingest.py 회귀 테스트 (v4.0 — 장부 tips). 네트워크 0회, 임시 장부·임시 CSV·임시 상태 파일만 쓴다.

    /opt/homebrew/bin/python3 scripts/test_kakao_ingest.py

지키는 것:
  1) 장부가 없으면 만들지 않고 실패한다 (빈 장부 = 전부 신규 = 중복)
  2) 중복 판정은 장부 tips 의 url_key — 같은 CSV 를 두 번 돌리면 두 번째는 0건 (2026-09-06 중복 15건 재발 방지)
  3) dry-run 은 장부·상태 파일을 쓰지 않는다
  4) 신규 행은 노션 시절과 같은 기본값·형식으로 들어간다
  5) 노션·외부 HTTP 요청을 하나도 만들지 않는다 (v4.0 3단계: 노션 래퍼 lib/tips_notion.py 를 import 하지도 않는다)
"""
import io, json, os, sqlite3, sys, tempfile
from contextlib import redirect_stdout

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, 'lib'))
import urllib.request
calls = []
def _no_net(*a, **k):
    calls.append(a[0] if a else k)
    raise RuntimeError('네트워크 요청 금지 (테스트)')
urllib.request.urlopen = _no_net
import library_db as ldb
import kakao_ingest as ki

results = []
def check(name, cond, detail=''):
    results.append(bool(cond))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f'  — {detail}' if detail and not cond else ''), flush=True)

def run(argv):
    sys.argv = ['kakao_ingest.py'] + argv
    buf = io.StringIO()
    code = 0
    with redirect_stdout(buf):
        try:
            ki.main()
        except SystemExit as e:
            code = e.code or 0
    out = buf.getvalue()
    rj = next((json.loads(l[len('RESULT_JSON:'):]) for l in out.splitlines() if l.startswith('RESULT_JSON:')), None)
    return code, out, rj

def make_db(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    c = ldb.open_db(path); ldb.apply_schema(c)
    with c:
        c.execute("INSERT INTO tips (record_id,title,url,url_key,source,tags,category,status,importance,saved_date,memo,created_at,updated_at) "
                  "VALUES ('tip-old-1','기존 팁','https://github.com/a/b','https://github.com/a/b','github.com','[]','개발툴','미확인','중','2026-09-01','',"
                  "'2026-09-01T00:00:00.000Z','2026-09-01T00:00:00.000Z')")
    c.close()

def tips(path):
    c = sqlite3.connect(path); c.row_factory = sqlite3.Row
    rows = [dict(r) for r in c.execute('SELECT * FROM tips ORDER BY created_at, record_id')]
    c.close(); return rows

def main():
    tmp = tempfile.mkdtemp(prefix='kakao-test-')
    ldb.DB_PATH = os.path.join(tmp, 'data', 'library.db')
    ki.STATE_FILE = os.path.join(tmp, '.kakao_state.json')
    csv_path = os.path.join(tmp, 'KakaoTalk_Chat_안진훈_2026-10-11.csv')
    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        f.write('Date,User,Message\n'
                '2026-02-01 10:00:00,"안진훈","https://old.example.com/x 기간 밖"\n'
                '2026-10-01 09:00:00,"안진훈","https://www.github.com/a/b/?utm_source=x 이미 있는 레포"\n'
                '2026-10-02 09:00:00,"안진훈","https://github.com/claude/skills 새 레포"\n'
                '2026-10-03 09:00:00,"안진훈","https://example.com/prompt-guide 프롬프트 정리"\n'
                '2026-10-03 09:05:00,"안진훈","https://example.com/prompt-guide/ 같은 링크 다시"\n')

    print('▶ 장부 없음')
    code, out, rj = run([f'--csv={csv_path}', '--apply'])
    check('장부가 없으면 exit 1', code == 1, out[-300:])
    check('장부 파일을 만들지 않는다', not os.path.exists(ldb.DB_PATH))
    check('상태 파일을 쓰지 않는다', not os.path.exists(ki.STATE_FILE))

    make_db(ldb.DB_PATH)
    print('▶ dry-run')
    code, out, rj = run([f'--csv={csv_path}'])
    check('dry-run 종료 0 · 후보 2건 (기간 밖·기존·CSV 내부 중복 제외)', code == 0 and rj and rj['candidates'] == 2, rj)
    check('dry-run 은 장부를 쓰지 않는다', len(tips(ldb.DB_PATH)) == 1)
    check('dry-run 은 상태 파일을 쓰지 않는다', not os.path.exists(ki.STATE_FILE))

    print('▶ apply')
    code, out, rj = run([f'--csv={csv_path}', '--apply', '--if-new'])
    rows = tips(ldb.DB_PATH)
    check('apply 종료 0 · 신규 2 · 총 3', code == 0 and rj and rj['created'] == 2 and rj['db_total'] == 3 and len(rows) == 3, rj)
    new = [r for r in rows if r['record_id'] != 'tip-old-1']
    gh = next((r for r in new if 'github.com/claude/skills' in r['url']), {})
    check('record_id 는 uuid4', all(len(r['record_id']) == 36 for r in new))
    check('url_key 는 kakao_parse.url_key 와 같다', gh.get('url_key') == ki.url_key(gh.get('url', '')), gh)
    check('기본값: 상태 미확인 · 중요도 중 · 카테고리 개발툴 · 출처 호스트', gh.get('status') == '미확인' and gh.get('importance') == '중'
          and gh.get('category') == '개발툴' and gh.get('source') == 'github.com', gh)
    check('tags 는 JSON 배열 · saved_date YYYY-MM-DD · body_md 빈 값', isinstance(json.loads(gh.get('tags', 'x')), list)
          and gh.get('saved_date') == '2026-10-02' and gh.get('body_md') == '', gh)
    check('created_at 은 ISO UTC(밀리초 Z)', all(len(r['created_at']) == 24 and r['created_at'].endswith('Z') for r in new), [r['created_at'] for r in new])
    st = json.load(open(ki.STATE_FILE, encoding='utf-8'))
    check('상태 파일 기록 (created 2 · db_total 3)', st.get('created') == 2 and st.get('db_total') == 3, st)

    print('▶ 멱등성')
    code, out, rj = run([f'--csv={csv_path}', '--apply', '--if-new'])
    check('--if-new 같은 CSV 는 건너뜀', rj and rj.get('skipped') == 'already_processed', rj)
    code, out, rj = run([f'--csv={csv_path}', '--apply', '--force'])
    check('--force 로 다시 돌려도 신규 0 · 총 3', code == 0 and rj and rj['created'] == 0 and len(tips(ldb.DB_PATH)) == 3, rj)

    print('▶ 쓰기 실패는 전부 아니면 전무')
    c = sqlite3.connect(ldb.DB_PATH)
    c.execute("CREATE TRIGGER boom BEFORE INSERT ON tips WHEN NEW.url LIKE '%prompt-guide%' BEGIN SELECT RAISE(ABORT, 'boom'); END")
    c.execute("DELETE FROM tips WHERE record_id != 'tip-old-1'"); c.commit(); c.close()
    code, out, rj = run([f'--csv={csv_path}', '--apply', '--force'])
    check('중간 실패 시 exit 1 · 남은 행 0 (총 1 그대로)', code == 1 and len(tips(ldb.DB_PATH)) == 1, (code, rj))

    check('네트워크 요청 0건', not calls, calls[:3])
    check('노션 래퍼(tips_notion)를 import 하지 않음', 'tips_notion' not in sys.modules)
    ok = all(results)
    print(f'\n{sum(results)}/{len(results)} PASS')
    return 0 if ok else 1

if __name__ == '__main__':
    sys.exit(main())
