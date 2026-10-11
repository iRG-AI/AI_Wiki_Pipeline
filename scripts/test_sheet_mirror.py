#!/usr/bin/env python3
"""sheet_mirror.py + gas/sheet_mirror.gs 회귀 테스트 (v4.0 3단계). 실제 구글·실제 장부·.env 를 건드리지 않는다.

    /opt/homebrew/bin/python3 scripts/test_sheet_mirror.py

받는 쪽은 scripts/fake_gas_server.js — gas/sheet_mirror.gs 원본을 그대로 node vm 에 올리고 시트를 흉내 낸다(127.0.0.1).
node 는 FAKE_GAS_NODE 환경변수 → /opt/homebrew/bin/node → PATH 의 node 순으로 찾는다.

지키는 것:
  1) URL 미설정이면 아무 요청 없이 skipped (설치 전 스케줄러 안전)
  2) 처음엔 두 탭을 비우고 전부 보낸다. 두 번째 실행은 요청 0
  3) 장부에서 바뀐 행만 보내고, 시트에서는 제자리 덮어쓰기(중복 행 없음)
  4) 401/403·토큰 불일치·HTML 응답은 재시도 없이 즉시 중단 (exit 2)
  5) 5xx·busy 는 2·4·8초 지수 백오프, 4회 초과면 exit 1 — 워터마크는 그대로(다음 실행에 다시 보냄)
  6) 중간 실패 후 다시 돌리면 빠짐·중복 없이 맞춰진다
  7) '='로 시작하는 글자는 수식이 되지 않는다
  8) 장부는 meta 의 sheet_* 키 말고는 바뀌지 않는다. 토큰은 출력에 나오지 않는다
"""
import hashlib, io, json, os, shutil, sqlite3, subprocess, sys, tempfile, time
from contextlib import redirect_stdout
from urllib.request import urlopen, Request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, 'lib'))
import library_db as ldb   # noqa: E402
import sheet_mirror as sm  # noqa: E402

TOKEN = 'tok-' + 'x' * 20
results = []


def check(name, cond, detail=''):
    results.append(bool(cond))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f'  — {detail}' if detail and not cond else ''), flush=True)


def find_node():
    for c in (os.environ.get('FAKE_GAS_NODE'), '/opt/homebrew/bin/node', shutil.which('node')):
        if c and os.path.exists(c):
            return c
    raise SystemExit('node 를 찾지 못했습니다')


tmp = tempfile.mkdtemp(prefix='sheet-mirror-test-')
DB = os.path.join(tmp, 'data', 'library.db')
ldb.DB_PATH = DB
proc = subprocess.Popen([find_node(), os.path.join(REPO, 'scripts', 'fake_gas_server.js')],
                        stdout=subprocess.PIPE, text=True, env={**os.environ, 'FAKE_GAS_TOKEN': TOKEN, 'FAKE_GAS_MAXROWS': '120'})   # 120행 탭 — 넘치면 행을 늘리는지
port = int(proc.stdout.readline().split()[1])
BASE = f'http://127.0.0.1:{port}'
sm.ALLOWED_URL_PREFIXES = (BASE + '/exec',)
ENV = {'SHEET_MIRROR_URL': BASE + '/exec', 'SHEET_MIRROR_TOKEN': TOKEN}
sm.load_env = lambda: dict(ENV)
sleeps = []
sm.time.sleep = lambda s: sleeps.append(s)


def ctl(**kw):
    urlopen(Request(BASE + '/__ctl', data=json.dumps(kw).encode(), method='POST',
                    headers={'Content-Type': 'application/json'})).read()


def state():
    return json.loads(urlopen(BASE + '/__state').read())


def run(*argv):
    sleeps.clear()
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = sm.main(list(argv))
    out = buf.getvalue()
    rj = next((json.loads(l[len('RESULT_JSON:'):]) for l in out.splitlines() if l.startswith('RESULT_JSON:')), None)
    return code, out, rj


def ts(n):
    return f'2026-10-{n:02d}T00:00:00.000Z'


def make_db():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    c = ldb.open_db(DB); ldb.apply_schema(c)
    with c:
        for i in range(450):
            c.execute('INSERT INTO videos (record_id, video_id, title, channel, topics, upload_date, view_count, subscriber_count, '
                      'video_url, thumbnail_url, status, summary, summary_src, created_at, updated_at) '
                      "VALUES (?,?,?,?,?,?,?,?,?,?,'완료',?,'property',?,?)",
                      (f'rec-{i:04d}', f'vid{i:08d}', '=1+1' if i == 7 else f'영상 {i}', '채널가', json.dumps(['AI 자동화', 'AI Claude'], ensure_ascii=False),
                       '2026-09-01', 1000 + i, 5000, f'https://www.youtube.com/watch?v=vid{i:08d}', None,
                       f'## 영상 개요\n요약 {i}', ts(1), ts(1)))
        for i in range(3):
            c.execute('INSERT INTO tips (record_id, title, url, url_key, source, tags, category, status, importance, saved_date, memo, created_at, updated_at) '
                      "VALUES (?,?,?,?,?,?,'개발툴','미확인','중','2026-09-02','',?,?)",
                      (f'tip-{i}', f'팁 {i}', f'https://github.com/a/{i}', f'https://github.com/a/{i}', 'github.com', '["Claude"]', ts(2), ts(2)))
    c.close()


def db_conn():
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row; return c


def content_hash():
    c = db_conn()
    h = hashlib.sha256()
    for t in ('videos', 'tips', 'videos_dup'):
        for r in c.execute(f'SELECT * FROM {t} ORDER BY record_id'):
            h.update(repr(tuple(r)).encode())
    for r in c.execute("SELECT * FROM meta WHERE key NOT LIKE 'sheet\\_%' ESCAPE '\\' ORDER BY key"):
        h.update(repr(tuple(r)).encode())
    c.close()
    return h.hexdigest()


def meta(key):
    c = db_conn(); r = c.execute('SELECT value FROM meta WHERE key=?', (key,)).fetchone(); c.close()
    return r[0] if r else None


try:
    print('▶ 1. 설정 전·잘못된 설정')
    ENV['SHEET_MIRROR_URL'] = ''
    code, out, rj = run()
    check('URL 없음 → exit 0 · skipped', code == 0 and rj and rj['skipped'] == 'not_configured')
    check('URL 없음 → 장부를 열지도 않음(파일 없어도 됨)', not os.path.exists(DB))
    code, out, rj = run('--dry-run')
    check('URL 없음 + --dry-run → 장부가 없으면 exit 1 (만들지 않음)', code == 1 and rj['error'] == 'library' and not os.path.exists(DB))
    ENV['SHEET_MIRROR_URL'] = 'https://evil.example.com/exec'
    code, out, rj = run()
    check('script.google.com 아닌 URL → exit 2 · 보내지 않음', code == 2 and rj['error'] == 'bad_url' and state()['posts'] == 0)
    ENV['SHEET_MIRROR_URL'] = BASE + '/exec'
    code, out, rj = run()
    check('장부 없음 → exit 1 · 만들지 않음', code == 1 and rj['error'] == 'library' and not os.path.exists(DB))

    make_db()

    print('▶ 2. dry-run')
    ENV['SHEET_MIRROR_URL'] = ''; ENV['SHEET_MIRROR_TOKEN'] = ''
    code, out, rj = run('--dry-run')
    check('URL·토큰 설정 전에도 --dry-run 은 건수를 센다 (전체 · 요청 0)', code == 0 and rj['videos_sent'] == 450 and rj['tips_sent'] == 3 and rj['full'] is True and state()['posts'] == 0, rj)
    ENV['SHEET_MIRROR_URL'] = BASE + '/exec'; ENV['SHEET_MIRROR_TOKEN'] = TOKEN
    code, out, rj = run('--dry-run')
    check('dry-run → 영상 450 · 꿀팁 3 · full', code == 0 and rj['videos_sent'] == 450 and rj['tips_sent'] == 3 and rj['full'] is True)
    check('dry-run → 요청 0 · meta 무변경', state()['posts'] == 0 and meta('sheet_target') is None)

    print('▶ 3. 첫 실행 (전체)')
    code, out, rj = run()
    st = state()
    check('exit 0 · 영상 450 · 꿀팁 3', code == 0 and rj['videos_sent'] == 450 and rj['tips_sent'] == 3, json.dumps(rj, ensure_ascii=False))
    check('요청 = reset 2 + upsert 3(200·200·50) + 1', st['log'] == ['reset:영상', 'upsert:영상:200', 'upsert:영상:200', 'upsert:영상:50', 'reset:꿀팁', 'upsert:꿀팁:3'], st['log'])
    check('시트 행 수 = 머리글 + 450 / + 3', len(st['sheets']['영상']) == 451 and len(st['sheets']['꿀팁']) == 4)
    check('머리글 = VIDEO_HEADERS', st['sheets']['영상'][0] == sm.VIDEO_HEADERS)
    row = next((r for r in st['sheets']['영상'] if r[0] == 'rec-0003'), [None] * 11)
    check('행 내용: 주제 쉼표 결합 · 숫자 · KST 시각', row[4] == 'AI 자동화, AI Claude' and row[5] == 1003 and row[9] == '2026-10-01 09:00', row)
    check("'=1+1' 제목은 글자로 들어감(수식 0)", st['formulas'] == [] and next((r for r in st['sheets']['영상'] if r[0] == 'rec-0007'), [None] * 11)[3] == '=1+1')
    check('워터마크·대상 기록', meta('sheet_wm_videos') == ts(1) and meta('sheet_wm_tips') == ts(2) and meta('sheet_target') == sm.url_hash(BASE + '/exec'))
    check('토큰이 출력에 없음', TOKEN not in out)

    print('▶ 4. 변경 없음')
    p0 = state()['posts']
    code, out, rj = run()
    check('두 번째 실행 → 0 · 0 · 요청 0', code == 0 and rj['videos_sent'] == 0 and rj['tips_sent'] == 0 and state()['posts'] == p0)

    print('▶ 5. 변경분만')
    c = db_conn()
    with c:
        c.execute("UPDATE videos SET topics=?, view_count=99999, updated_at=? WHERE record_id='rec-0010'", (json.dumps(['AI 자동화', 'AI 에이전트'], ensure_ascii=False), ts(5)))
        c.execute("INSERT INTO tips (record_id,title,url,url_key,source,tags,category,status,importance,saved_date,memo,created_at,updated_at) "
                  "VALUES ('tip-new','새 팁','https://x.com/1','https://x.com/1','x.com','[]','기타','미확인','중','2026-10-05','메모',?,?)", (ts(5), ts(5)))
    c.close()
    code, out, rj = run()
    st = state()
    r10 = [r for r in st['sheets']['영상'] if r[0] == 'rec-0010']
    check('영상 1 · 꿀팁 1 만 보냄', code == 0 and rj['videos_sent'] == 1 and rj['tips_sent'] == 1 and rj['full'] is False)
    check('바뀐 영상은 제자리 덮어쓰기 (행 수 그대로, 중복 없음)', len(st['sheets']['영상']) == 451 and len(r10) == 1 and r10[0][5] == 99999 and r10[0][4] == 'AI 자동화, AI 에이전트')
    check('새 꿀팁은 아래에 추가', len(st['sheets']['꿀팁']) == 5 and st['sheets']['꿀팁'][-1][0] == 'tip-new')
    check('워터마크 올라감', meta('sheet_wm_videos') == ts(5) and meta('sheet_wm_tips') == ts(5))

    print('▶ 6. 일시 오류 — 지수 백오프')
    c = db_conn()
    with c: c.execute("UPDATE videos SET view_count=1, updated_at=? WHERE record_id='rec-0011'", (ts(6),))
    c.close()
    ctl(queue=[{'status': 500}, {'busy': True}])
    code, out, rj = run()
    check('500 → busy → 성공: exit 0 · 대기 [2, 4]', code == 0 and sleeps == [2, 4] and rj['videos_sent'] == 1, (code, sleeps))
    c = db_conn()
    with c: c.execute("UPDATE videos SET view_count=2, updated_at=? WHERE record_id='rec-0012'", (ts(7),))
    c.close()
    ctl(queue=[{'status': 503}] * 4)
    p0 = state()['posts']
    code, out, rj = run()
    check('503 ×4 → exit 1 · transient · 대기 [2, 4, 8] · 시도 4', code == 1 and rj['error'] == 'transient' and sleeps == [2, 4, 8] and state()['posts'] - p0 == 4, (code, sleeps))
    check('실패 → 워터마크 그대로', meta('sheet_wm_videos') == ts(6))
    code, out, rj = run()
    check('다음 실행이 다시 보냄', code == 0 and rj['videos_sent'] == 1 and meta('sheet_wm_videos') == ts(7))

    print('▶ 7. 인증 오류 — 재시도 없음')
    c = db_conn()
    with c: c.execute("UPDATE videos SET view_count=3, updated_at=? WHERE record_id='rec-0013'", (ts(8),))
    c.close()
    for label, inj in (('HTTP 403', {'status': 403}), ('HTTP 401', {'status': 401}), ('HTML(로그인 화면)', {'html': True}), ('HTTP 404', {'status': 404})):
        ctl(queue=[inj])
        p0 = state()['posts']
        code, out, rj = run()
        check(f'{label} → exit 2 · auth · 시도 1 · 대기 없음', code == 2 and rj['error'] == 'auth' and state()['posts'] - p0 == 1 and sleeps == [], (code, rj, sleeps))
    ctl(token='other-token')
    p0 = state()['posts']
    code, out, rj = run()
    check('토큰 불일치 → exit 2 · 시도 1', code == 2 and rj['error'] == 'auth' and state()['posts'] - p0 == 1)
    check('인증 오류 내내 워터마크 그대로', meta('sheet_wm_videos') == ts(7))
    ctl(token=TOKEN)
    code, out, rj = run()
    check('토큰 복구 후 다시 보냄', code == 0 and rj['videos_sent'] == 1)

    print('▶ 8. 전체 다시 쓰기 중 실패 → 복구')
    ctl(queue=[{}, {}, {'status': 403}])   # reset·첫 묶음 성공, 둘째 묶음 403
    code, out, rj = run('--full')
    st = state()
    check('--full 도중 403 → exit 2 · 영상 200 만 보냄', code == 2 and rj['videos_sent'] == 200, rj)
    check('이 시점 시트는 반쪽(200행)', len(st['sheets']['영상']) == 201)
    check('끊긴 전체 쓰기 → 대상 표시 지워짐(다음 실행 전체)', meta('sheet_target') is None)
    code, out, rj = run()
    st = state()
    check('다음 실행이 다시 전체(reset 포함)로 맞춤 — 영상 450 · 중복 0',
          code == 0 and rj['full'] is True and len(st['sheets']['영상']) == 451 and len({r[0] for r in st['sheets']['영상'][1:]}) == 450, rj)
    check('꿀팁도 4행으로 맞춤', len(st['sheets']['꿀팁']) == 5)

    print('▶ 9. 대조 (--check) · 머리글 어긋남 · 주소 변경')
    code, out, rj = run('--check')
    check('--check → match true', code == 0 and rj['match'] is True and rj['db'] == {'영상': 450, '꿀팁': 4}, rj)
    ctl(deleteRow={'sheet': '영상', 'row': 10})
    code, out, rj = run('--check')
    check('시트 행을 지우면 match false', code == 0 and rj['match'] is False and rj['sheet']['영상'] == 449)
    ctl(setCell={'sheet': '꿀팁', 'row': 1, 'col': 3, 'value': '이름바꿈'})
    c = db_conn()
    with c: c.execute("UPDATE tips SET memo='m', updated_at=? WHERE record_id='tip-0'", (ts(9),))
    c.close()
    code, out, rj = run()
    check('머리글이 다르면 쓰지 않음 → exit 1 · other', code == 1 and rj['error'] == 'other', rj)
    check('그때 꿀팁 워터마크 그대로', meta('sheet_wm_tips') == ts(5))
    ENV['SHEET_MIRROR_URL'] = BASE + '/exec?v=2'
    sm.ALLOWED_URL_PREFIXES = (BASE + '/exec',)
    code, out, rj = run()
    st = state()
    check('주소가 바뀌면 자동 전체 → 머리글·행 수 복구', code == 0 and rj['full'] is True and st['sheets']['꿀팁'][0] == sm.TIP_HEADERS
          and len(st['sheets']['영상']) == 451 and len(st['sheets']['꿀팁']) == 5, rj)
    code, out, rj = run('--check')
    check('복구 후 --check match true', rj['match'] is True)

    print('▶ 10. 장부 보존')
    c = db_conn()
    keys = sorted(r[0] for r in c.execute('SELECT key FROM meta'))
    c.close()
    check('meta 키 = sheet_* 만', keys == ['sheet_last_ok', 'sheet_target', 'sheet_wm_tips', 'sheet_wm_videos'], keys)

    print('▶ 11. 미러만 돌렸을 때 장부 해시')
    shutil.copy(DB, DB + '.before')
    h1 = content_hash()
    c = db_conn()
    with c: c.execute("UPDATE videos SET view_count=4, updated_at=? WHERE record_id='rec-0020'", (ts(10),))
    c.close()
    h2 = content_hash()
    run(); run('--check'); run('--dry-run')
    check('미러 실행 3종 뒤 장부 내용 해시 그대로', content_hash() == h2 and h1 != h2)
finally:
    proc.kill()
    shutil.rmtree(tmp, ignore_errors=True)

ok = sum(results)
print(f'\n{ok}/{len(results)} PASS')
sys.exit(0 if ok == len(results) else 1)
