#!/usr/bin/env python3
"""skill_review.py 회귀 테스트 [CC-1109-A]. 네트워크 0회 — 임시 장부·임시 출력 폴더·임시 스킬 폴더·가짜 claude 실행 파일.

    /opt/homebrew/bin/python3 scripts/test_skill_review.py
"""
import hashlib, io, json, os, shutil, sqlite3, stat, sys, tempfile
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timedelta, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, 'lib'))
import library_db as ldb
import skill_review as sr
import env_util

SENT = []
FAKE_ENV = {'TELEGRAM_BOT_TOKEN': 'TOK-SECRET-123', 'TELEGRAM_CHAT_ID': '987654'}
SEND_RESULT = [True]
env_util.load_env = lambda path=None: dict(FAKE_ENV)  # 실제 .env 를 읽지 않는다
def _fake_send(token, chat, text):
    SENT.append(text)
    return SEND_RESULT[0]
sr.send_telegram = _fake_send  # 실제 네트워크 0

tmp = tempfile.mkdtemp()
try:
    DB, OUT, PROF, SKILLS = (os.path.join(tmp, n) for n in ('lib.db', 'proposals', 'profile.md', 'skills'))
    FAKE, FAKE_OUT, MARK = (os.path.join(tmp, n) for n in ('claude', 'fake_out.json', 'called'))
    os.makedirs(os.path.join(SKILLS, 'abc-skill'))
    open(PROF, 'w').write('프로필')
    FAIL, SLOW = os.path.join(tmp, 'fail'), os.path.join(tmp, 'slow')
    open(FAKE, 'w').write(f'#!/bin/sh\necho x >> "{MARK}"\ncat >/dev/null\nif [ -f "{SLOW}" ]; then echo partial-err >&2; exec sleep 5; fi\nif [ -f "{FAIL}" ]; then printf "boom\\nline2" >&2; exit 3; fi\ncat "{FAKE_OUT}"\n')
    os.chmod(FAKE, os.stat(FAKE).st_mode | stat.S_IEXEC)
    os.environ['CLAUDE_BIN'], os.environ['SKILL_REVIEW_SKILLS_DIR'] = FAKE, SKILLS

    now = datetime.now(timezone.utc)
    iso = sr.iso
    conn = sqlite3.connect(DB)
    conn.executescript(ldb.schema_sql())
    def vid(i, ago_h, grade=None):
        t = iso(now - timedelta(hours=ago_h))
        conn.execute("INSERT INTO videos(record_id,video_id,title,summary,created_at,updated_at,grade) VALUES(?,?,?,?,?,?,?)",
                     (f'v{i}', f'id{i}', f't{i}', 'S' * 3000, t, t, grade))
    vid(1, 2); vid(2, 5); vid(3, 3, 'exclude'); vid(4, 100)
    t = iso(now - timedelta(hours=1))
    conn.execute("INSERT INTO tips(record_id,title,created_at,updated_at) VALUES('tip1','x',?,?)", (t, t))
    conn.commit(); conn.close()

    results = []
    def check(name, cond, detail=''):
        results.append(bool(cond))
        print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f'  — {detail}' if detail and not cond else ''), flush=True)

    def sha(p):
        return hashlib.sha256(open(p, 'rb').read()).hexdigest()

    def run(*args):
        buf = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(io.StringIO()):
            code = sr.main(['--db=' + DB, '--out-dir=' + OUT, '--profile=' + PROF, *args])
        out = buf.getvalue()
        return code, json.loads(out.strip().splitlines()[-1].split(' ', 1)[1]), out

    def calls():
        return len(open(MARK).read().split()) if os.path.exists(MARK) else 0

    def fake(proposals, note=''):
        open(FAKE_OUT, 'w').write(json.dumps({'is_error': False, 'result': '{}', 'structured_output': {'proposals': proposals, 'note': note}}))

    def ok_skill(slug='good-skill', ev=('v1',)):
        return {'kind': 'skill', 'area': 'dev', 'title': slug, 'why': 'w', 'evidence': list(ev), 'effort': '낮음',
                'skill': {'slug': slug, 'skill_md': f'---\nname: wiki-{slug}\ndescription: d\n---\n본문'}}

    _tick = [0]
    def _clock():  # 같은 초에 trial 파일 이름이 겹치지 않게 호출마다 1초씩 앞으로
        _tick[0] += 1
        return datetime.now(timezone.utc) + timedelta(seconds=_tick[0])
    sr.utcnow = _clock

    db_sha = sha(DB)
    today = os.path.join(OUT, now.astimezone(sr.KST).strftime('%Y%m%d') + '.json')

    print('--- ⑥ dry-run')
    code, r, out = run('--dry-run')
    check('dry-run 호출 0 · 파일 0', code == 0 and calls() == 0 and not os.path.exists(OUT), out)
    check('dry-run 건수(기준점 없음 = 24h): videos 2 · tips 1', (r['considered_videos'], r['considered_tips']) == (2, 1), r)

    print('--- ② 대상 0')
    code, r, _ = run('--days=0')
    check('대상 0 → 호출 0 · trial 파일 씀', code == 0 and calls() == 0 and r['file'] and os.path.exists(r['file']), r)
    os.remove(r['file'])

    print('--- ③ 깨진 JSON')
    open(FAKE_OUT, 'w').write('not json')
    code, r, _ = run()
    check('깨진 JSON → ok:false · 파일 없음', code == 1 and not r['ok'] and not os.path.exists(today), r)

    print('--- ①④⑤ 정상 + 검증')
    bad = [dict(ok_skill('no-ev'), evidence=[]), ok_skill('outside', ('zzz',)), ok_skill('Bad_Slug'),
           dict(ok_skill('name-mis'), skill={'slug': 'name-mis', 'skill_md': '---\nname: wiki-other\n---\n'})]
    fake([ok_skill()] + bad)
    code, r, _ = run()
    d = json.load(open(today)) if os.path.exists(today) else {}
    check('① videos 2(exclude·옛 것 제외) · tips 1', d.get('considered') == {'videos': 2, 'tips': 1, 'truncated': 0}, d.get('considered'))
    check('④ 불량 4건만 버림 · 1건 통과', r['proposals'] == 1 and r['dropped'] == 4 and d['proposals'][0]['id'].endswith('-1'), r)
    check('⑤ through = 대상 created_at 최댓값(tip1)', d.get('through') == t, d.get('through'))
    check('요약 2,500자 절단', len(sr.select_targets(ldb.open_existing(DB, readonly=True), '0')[0][0]['summary']) == 2500)

    print('--- ⑧ 같은 날 두 번')
    n = calls()
    code, r, _ = run()
    check('exists · 호출 증가 0', code == 1 and r['error'] == 'exists' and calls() == n, r)

    print('--- ⑦ --days → trial · 기준점 불변')
    before = json.load(open(today))['through']
    code, r, _ = run('--days=7')
    check('trial 폴더에 씀', code == 0 and os.sep + 'trial' + os.sep in r['file'] and os.path.exists(r['file']), r)
    check('실제 파일 불변(through 동일)', json.load(open(today))['through'] == before)
    check('trial 제안 id 접두', json.load(open(r['file']))['proposals'][0]['id'].startswith('trial-'))

    print('--- 다음 실행 기준점')
    os.remove(today)
    open(os.path.join(OUT, '20990101.json'), 'w').write(json.dumps({'through': iso(now), 'proposals': []}))
    code, r, _ = run('--dry-run')
    check('기준점 = 최근 파일 through → 대상 0', r['considered_videos'] == 0 and r['considered_tips'] == 0, r)

    print('--- KST 날짜')
    fixed = datetime(2026, 11, 8, 23, 30, tzinfo=timezone.utc)  # KST 11-09 08:30
    real_now = _clock
    sr.utcnow = lambda: fixed
    fake([])
    code, r, _ = run('--days=1')
    check('KST 08:30(UTC 전날 23:30) → trial 파일명이 KST 날짜', os.path.basename(r['file'] or '') == '20261109-083000.json', r)
    os.remove(r['file'])
    fake([ok_skill()])
    code, r, _ = run()
    check('일반 파일명 = KST 날짜 · created_at 은 UTC', os.path.basename(r['file'] or '') == '20261109.json'
          and json.load(open(r['file']))['created_at'].startswith('2026-11-08T23:30'), r)
    os.remove(r['file'])
    sr.utcnow = real_now

    print('--- recent_context')
    rc = os.path.join(tmp, 'rc'); os.makedirs(rc)
    for ymd, ti in (('20261109', 'today'), ('20261103', 'six'), ('20261102', 'seven')):
        open(os.path.join(rc, ymd + '.json'), 'w').write(json.dumps({'proposals': [{'title': ti}]}))
    dec = {f'd{i}': {'title': f'T{i}', 'decision': 'rejected', 'reason': f'r{i}', 'at': f'2026-11-{i + 1:02d}T00:00:00Z'} for i in range(32)}
    dec['x'] = {'title': 'noreason', 'decision': 'rejected', 'reason': '', 'at': '2026-12-01T00:00:00Z'}
    dec['y'] = {'title': 'appr', 'decision': 'approved', 'reason': 'ok', 'at': '2026-12-02T00:00:00Z'}
    open(os.path.join(rc, 'decisions.json'), 'w').write(json.dumps({'version': 1, 'decisions': dec}))
    titles, rej = sr.recent_context(rc, datetime(2026, 11, 8, 23, 30, tzinfo=timezone.utc))
    check('7일 = KST 오늘 기준 0~6일 전만', sorted(titles) == ['six', 'today'], titles)
    check('거절만 · 최신순 30개 · 사유 없음 표기', len(rej) == 30 and rej[0] == 'noreason: (사유 없음)' and not any('appr' in x for x in rej), rej[:2])

    print('--- 접두 wiki- 버림')
    fake([ok_skill('wiki-abc')])
    code, r, _ = run('--days=1')
    check('slug 가 wiki- 로 시작 → dropped', r['proposals'] == 0 and r['dropped'] == 1, r)
    os.remove(r['file'])

    print('--- claude 실패 사유')
    open(FAIL, 'w').write('')
    code, r, _ = run('--days=1')
    check('종료 코드 ≠ 0 → error 에 stderr 포함(줄바꿈 → 공백)', code == 1 and 'boom line2' in (r['error'] or ''), r)
    os.remove(FAIL)

    print('--- 시간 초과')
    open(SLOW, 'w').write('')
    sr.CLAUDE_TIMEOUT = 1
    code, r, _ = run('--days=1')
    check('시간 초과 → error 에 claude timeout + stderr', code == 1 and 'claude timeout: partial-err' in (r['error'] or ''), r)
    sr.CLAUDE_TIMEOUT = 900
    os.remove(SLOW)

    print('--- name 줄 정규식')
    def md_with(name_line, nl='\n'):
        return {'kind': 'skill', 'area': 'dev', 'title': 'x', 'why': 'w', 'evidence': ['v1'], 'effort': '낮음',
                'skill': {'slug': 'xyz', 'skill_md': nl.join(['---', name_line, 'description: d', '---', 'b'])}}
    check('name:\\nwiki-x → 거부', sr.validate(md_with('name:\nwiki-xyz'), {'v1'}) == 'skill_md')
    check('정상 name 통과 · CRLF 거부', sr.validate(md_with('name: wiki-xyz'), {'v1'}) is None and sr.validate(md_with('name: wiki-xyz', '\r\n'), {'v1'}) == 'skill_md')

    print('--- 프로필 없음')
    buf_err = io.StringIO()
    with redirect_stderr(buf_err), redirect_stdout(io.StringIO()):
        code, r, _ = sr.main(['--db=' + DB, '--out-dir=' + OUT, '--days=1', '--profile=' + os.path.join(tmp, 'nope.md')]), None, None
    check('프로필 없음 → stderr 경고 한 줄', '프로필 파일 없음' in buf_err.getvalue(), buf_err.getvalue())
    code, r, _ = run('--days=1', '--profile=' + os.path.join(tmp, 'nope.md'))
    check('프로필 없음 → note 에 표시', json.load(open(r['file']))['note'].endswith('프로필 없음'), r)
    os.remove(r['file'])

    print('--- ⑩~⑰ 알림')
    def reset_today():
        if os.path.exists(today):
            os.remove(today)
    reset_today()
    # 이전 단계가 남긴 기준점 파일 제거(20990101)
    for f in os.listdir(OUT):
        if f == '20990101.json':
            os.remove(os.path.join(OUT, f))
    SENT.clear(); fake([ok_skill()])
    code, r, out = run()
    check('⑩ 제안 ≥1 → 1회 발송 · 건수·제목·#tab=proposals', len(SENT) == 1 and '제안 1건' in SENT[0] and '[스킬] good-skill' in SENT[0]
          and '#tab=proposals' in SENT[0] and r['notified'] is True, (SENT, r))
    check('⑰ 출력에 토큰·chat id 없음', 'TOK-SECRET' not in out and '987654' not in out)
    reset_today(); SENT.clear()
    open(FAKE_OUT, 'w').write('not json')
    code, r, _ = run()
    check('⑪ 실패 → 실패 문구 1회', len(SENT) == 1 and SENT[0].startswith('⚠️ [매일 Wiki 검토 실패]'), SENT)
    SENT.clear(); fake([ok_skill()])
    run(); SENT.clear()
    code, r, _ = run()
    check('⑫ exists → 0회', r['error'] == 'exists' and not SENT and r['notified'] is None, (SENT, r))
    reset_today(); SENT.clear(); fake([])
    code, r, _ = run()
    check('⑬ 제안 0건 → 0회', r['ok'] and r['proposals'] == 0 and not SENT, (SENT, r))
    reset_today(); fake([ok_skill()])
    run('--days=1'); run('--dry-run'); run('--no-notify')
    check('⑭ --days·--dry-run·--no-notify → 0회', not SENT, SENT)
    reset_today()
    FAKE_ENV.pop('TELEGRAM_BOT_TOKEN')
    code, r, _ = run()
    check('⑮ 토큰 없음 → not_configured · 0회', r['notified'] == 'not_configured' and not SENT, (SENT, r))
    FAKE_ENV['TELEGRAM_BOT_TOKEN'] = 'TOK-SECRET-123'
    reset_today(); SEND_RESULT[0] = False
    code, r, _ = run()
    check('⑯ 발송 False → notified:false · ok 그대로', code == 0 and r['ok'] and r['notified'] is False, r)
    SEND_RESULT[0] = True
    reset_today()

    print('--- ⑨ 장부 불변')
    check('장부 sha256 전후 동일', sha(DB) == db_sha)

finally:
    shutil.rmtree(tmp, ignore_errors=True)
p = sum(results)
print(f'RESULT: {p}/{len(results)} 통과')
sys.exit(0 if p == len(results) else 1)
