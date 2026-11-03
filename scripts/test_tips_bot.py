#!/usr/bin/env python3
"""telegram_tips_ingest.py 회귀 테스트 (v4.18). 네트워크 0회 — 가짜 urlopen·가짜 sleep·임시 장부·가짜 env.

    /opt/homebrew/bin/python3 scripts/test_tips_bot.py

값은 가짜 토큰 TEST:TOKEN · 허용 chat 1 · 허용 밖 chat 987654 만 쓴다.
"""
import io, json, os, sqlite3, sys, tempfile, urllib.error, urllib.request
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timezone, timedelta

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, 'lib'))
import library_db as ldb
import kakao_ingest as ki
import telegram_tips_ingest as tb

TOKEN, OTHER = 'TEST:TOKEN', 987654
ENV = {}
ki.load_env = lambda: dict(ENV)
queue, calls, sleeps = [], [], []


class Resp(io.BytesIO):
    def __init__(self, code, body):
        super().__init__(json.dumps(body).encode())
        self.status = code
    def __enter__(self): return self
    def __exit__(self, *a): return False


def fake_urlopen(req, timeout=None):
    method = req.full_url.rsplit('/', 1)[1]
    calls.append((method, json.loads(req.data)))
    code, body = queue.pop(0) if queue else (200, {'ok': True, 'result': []})
    if code == 'net':
        raise urllib.error.URLError('down')
    if code == 200:
        return Resp(200, body)
    raise urllib.error.HTTPError(req.full_url, code, 'x', {}, Resp(code, body))


urllib.request.urlopen = fake_urlopen
tb.time.sleep = lambda s: sleeps.append(s)

results = []
def check(name, cond, detail=''):
    results.append(bool(cond))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f'  — {detail}' if detail and not cond else ''), flush=True)


def msg(uid, mid, text=None, chat=1, **extra):
    m = {'message_id': mid, 'date': 1793600000, 'chat': {'id': chat, 'type': 'private', 'first_name': 'T'}}
    if text is not None:
        m['text'] = text
    m.update(extra)
    return {'update_id': uid, 'message': m}


def ok(updates):
    return (200, {'ok': True, 'result': updates})


alltext = []
def run(argv=('--apply', '--no-lookup')):
    sys.argv = ['telegram_tips_ingest.py'] + list(argv)
    calls.clear(); sleeps.clear()
    o, e = io.StringIO(), io.StringIO()
    with redirect_stdout(o), redirect_stderr(e):
        code = tb.main()
    out = o.getvalue() + e.getvalue()
    alltext.append(out)
    rj = next((json.loads(l[len('RESULT_JSON:'):]) for l in out.splitlines() if l.startswith('RESULT_JSON:')), None)
    return code, out, rj


def fresh(tmp, name):
    p = os.path.join(tmp, name + '.db')
    c = ldb.open_db(p); ldb.apply_schema(c)
    with c:
        c.execute("INSERT INTO tips (record_id,title,url,url_key,source,tags,category,status,importance,saved_date,memo,created_at,updated_at) "
                  "VALUES ('old','기존','https://github.com/a/b','https://github.com/a/b','github.com','[]','개발툴','미확인','중','2026-09-01','',"
                  "'2026-09-01T00:00:00.000Z','2026-09-01T00:00:00.000Z')")
    c.close()
    ldb.DB_PATH = p
    return p


def q(p, sql):
    c = sqlite3.connect(p); c.row_factory = sqlite3.Row
    r = [dict(x) for x in c.execute(sql)]; c.close(); return r


def offset(p):
    r = q(p, "select value from meta where key='tips_bot_offset'")
    return r[0]['value'] if r else None


def sent(): return [c[1]['text'] for c in calls if c[0] == 'sendMessage']


def main():
    tmp = tempfile.mkdtemp(prefix='tipsbot-test-')

    print('▶ 1·2 설정 없음')
    p = fresh(tmp, 't1')
    code, out, rj = run()
    check('1 토큰 없음 → skipped not_configured · 요청 0', code == 0 and rj['skipped'] == 'not_configured' and not calls, rj)
    ENV.update(TIPS_BOT_TOKEN=TOKEN)
    code, out, rj = run()
    check('2 chat id 없음 → no_chat_id · 요청 0 · 출력에 id 없음', code == 0 and rj['skipped'] == 'no_chat_id' and not calls, rj)
    ENV['TIPS_BOT_CHAT_ID'] = '1'

    print('▶ 3~6 저장·dup·링크 없음·허용 밖·offset')
    p = fresh(tmp, 't3')
    queue[:] = [ok([msg(10, 100, 'https://github.com/zz/newrepo-xyz 메모'), msg(11, 101, 'https://www.github.com/a/b/?utm_source=x'),
                    msg(12, 102, '그냥 글'), msg(13, 103, 'https://github.com/zz/other', chat=OTHER)])]
    code, out, rj = run()
    new = q(p, "select * from tips where record_id != 'old'")
    r = new[0] if new else {}
    check('3 링크 1건 저장 — 카톡과 같은 행 꼴(uuid·url_key·기본값·KST 날짜)', code == 0 and len(new) == 1 and len(r['record_id']) == 36
          and r['url_key'] == ki.url_key(r['url']) and r['status'] == '미확인' and r['importance'] == '중' and r['category'] == '개발툴'
          and r['source'] == 'github.com' and r['saved_date'] == '2026-11-02' and r['body_md'] == '' and r['created_at'].endswith('Z'), (code, r))
    check('4 허용 밖 chat → 적재 0 · dropped 만 · id 미출력', rj['dropped'] == 1 and len(new) == 1 and str(OTHER) not in out and rj['created'] == 1, rj)
    s = sent()
    check('5 답장 문구 3종 (저장 · 이미 있음 · 링크 없음)', len(s) == 3 and s[0].startswith('저장: ') and s[0].endswith(' · 개발툴') and s[1:] == ['이미 있음', '링크 없음'], s)
    check('5 dup 1 · no_link 1', rj['dup'] == 1 and rj['no_link'] == 1, rj)
    check('6 offset = 받은 최대 update_id(허용 밖 포함) · last_ok 기록', offset(p) == '13' and q(p, "select 1 from meta where key='tips_bot_last_ok'"))
    queue[:] = [ok([])]
    run()
    check('6 다음 getUpdates 인자 offset=14', calls[0][1].get('offset') == 14, calls)

    print('▶ 7 INSERT 실패')
    p = fresh(tmp, 't7')
    c = sqlite3.connect(p)
    c.execute("CREATE TRIGGER boom BEFORE INSERT ON tips WHEN NEW.url LIKE '%newrepo%' BEGIN SELECT RAISE(ABORT,'boom'); END"); c.commit(); c.close()
    queue[:] = [ok([msg(20, 200, 'https://github.com/zz/newrepo-xyz')])]
    code, out, rj = run()
    check('7 행 0 · offset 그대로 · 답장 0 · exit 1', code == 1 and len(q(p, 'select 1 from tips')) == 1 and offset(p) is None and not sent(), (code, rj))

    print('▶ 8 치명 응답')
    for st in (401, 403, 404, 409):
        p = fresh(tmp, f't8{st}')
        queue[:] = [(st, {'ok': False, 'error_code': st, 'description': 'x'})]
        code, out, rj = run()
        check(f'8 {st} → 요청 1회 · exit 2 · 장부·offset 그대로', code == 2 and len(calls) == 1 and offset(p) is None
              and len(q(p, 'select 1 from tips')) == 1 and rj['error'] in ('auth', 'conflict'), (code, len(calls), rj))

    print('▶ 9 429')
    p = fresh(tmp, 't9')
    queue[:] = [(429, {'ok': False, 'parameters': {'retry_after': 7}}), ok([msg(30, 300, 'https://github.com/zz/r9')])]
    code, out, rj = run()
    check('9 retry_after 대기 뒤 성공', code == 0 and 7 in sleeps and rj['created'] == 1, (code, sleeps, rj))

    print('▶ 10 5xx')
    p = fresh(tmp, 't10')
    queue[:] = [(503, {'ok': False})] * 3
    code, out, rj = run()
    check('10 5xx 3회 → exit 1 transient · 2·4초 · 장부·offset 그대로', code == 1 and rj['error'] == 'transient' and len(calls) == 3
          and sleeps == [2, 4] and offset(p) is None, (code, rj, sleeps))
    queue[:] = [('net', None)] * 3
    code, out, rj = run()
    check('10 네트워크 오류도 transient', code == 1 and rj['error'] == 'transient', rj)

    print('▶ 11 답장 실패')
    for st in (403, 503):
        p = fresh(tmp, f't11{st}')
        queue[:] = [ok([msg(40, 400, 'https://github.com/zz/r11a'), msg(41, 401, 'https://github.com/zz/r11b')]), (st, {'ok': False})]
        code, out, rj = run()
        check(f'11 답장 {st} 실패에도 적재 유지 · exit 0 · 남은 답장 포기', code == 0 and rj['created'] == 2 and offset(p) == '41'
              and len(sent()) == 1, (code, rj, sent()))

    print('▶ 12 caption·text_link')
    p = fresh(tmp, 't12')
    queue[:] = [ok([msg(50, 500, None, caption='https://github.com/zz/cap1 설명'),
                    msg(51, 501, '이거 보세요', entities=[{'type': 'text_link', 'offset': 0, 'length': 2, 'url': 'https://github.com/zz/hid1'}])])]
    code, out, rj = run()
    urls = {r['url'] for r in q(p, "select url from tips where record_id != 'old'")}
    check('12 caption · text_link URL 저장', urls == {'https://github.com/zz/cap1', 'https://github.com/zz/hid1'}, urls)

    print('▶ 13 stale_h')
    p = fresh(tmp, 't13')
    queue[:] = [ok([])]
    code, out, rj = run()
    check('13 last_ok 없으면 null', rj['stale_h'] is None, rj)
    c = sqlite3.connect(p)
    old = (datetime.now(timezone.utc) - timedelta(hours=20)).strftime('%Y-%m-%dT%H:%M:%S.000Z')
    c.execute("INSERT OR REPLACE INTO meta VALUES ('tips_bot_last_ok', ?)", (old,)); c.commit(); c.close()
    queue[:] = [ok([])]
    code, out, rj = run()
    check('13 20시간 전 → stale_h 20.0', rj['stale_h'] == 20.0, rj)

    print('▶ 15 dry-run')
    p = fresh(tmp, 't15')
    queue[:] = [ok([msg(60, 600, 'https://github.com/zz/r15')])]
    code, out, rj = run(('--no-lookup',))
    check('15 dry-run → 장부·meta 쓰기 0 · sendMessage 0 · 후보 1', code == 0 and rj['candidates'] == 1 and len(q(p, 'select 1 from tips')) == 1
          and not q(p, "select 1 from meta where key like 'tips_bot%'") and not sent(), (code, rj))

    print('▶ whoami')
    queue[:] = [ok([msg(70, 700, 'x')])]
    code, out, rj = run(('--whoami',))
    check('whoami → 터미널에 chat id · RESULT_JSON 없음 · offset 인자 없음', code == 0 and 'chat id: 1' in out and rj is None
          and 'offset' not in calls[0][1], out)

    print('▶ 14 토큰 노출')
    check('14 모든 경로 출력에 토큰·요청 주소 0회', all(TOKEN not in t and 'api.telegram.org' not in t for t in alltext))
    print(f'\n{sum(results)}/{len(results)} PASS')
    return 0 if all(results) else 1


if __name__ == '__main__':
    sys.exit(main())
