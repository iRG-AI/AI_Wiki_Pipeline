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
    IN, RANK_OUT, RANKFAIL, FAILONCE, DYN, ARGS = (os.path.join(tmp, n) for n in ('in.txt', 'rank_out.json', 'rankfail', 'failonce', 'dyn', 'args'))
    DYNPY = os.path.join(tmp, 'dyn.py')
    open(DYNPY, 'w').write("import json,re,sys\ns=open(sys.argv[1]).read()\nm=re.search(r'### \\[(\\w+)\\]|- \\[(\\w+)\\]',s)\nr=m.group(1) or m.group(2)\n"
        "P=[{'kind':'action','area':'invest','title':f'T-{r}-{i}','why':'w','evidence':[r],'effort':'낮음','action_prompt':'p'} for i in range(1,9)]\n"
        "print(json.dumps({'is_error':False,'result':'{}','structured_output':{'proposals':P,'note':'n-'+r}}))\n")
    open(FAKE, 'w').write(f'#!/bin/sh\necho x >> "{MARK}"\nprintf "%s|" "$@" >> "{ARGS}"\necho >> "{ARGS}"\ncat > "{IN}"\n'
        f'if [ -f "{SLOW}" ]; then echo partial-err >&2; exec sleep 5; fi\nif [ -f "{FAIL}" ]; then printf "boom\\nline2" >&2; exit 3; fi\n'
        f'if [ -f "{FAILONCE}" ]; then rm "{FAILONCE}"; echo once >&2; exit 3; fi\n'
        f'if grep -q "순위 매기기" "{IN}"; then if [ -f "{RANKFAIL}" ]; then exit 3; fi; cat "{RANK_OUT}"; exit 0; fi\n'
        f'if [ -f "{DYN}" ]; then {sys.executable} "{DYNPY}" "{IN}"; exit 0; fi\ncat "{FAKE_OUT}"\n')
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
    os.makedirs(os.path.join(rc, 'trial'))
    for fn, ti in (('20261108-071502', 'trial6'), ('20261102-071502', 'trial7'), ('20261109-010101', 'today')):
        open(os.path.join(rc, 'trial', fn + '.json'), 'w').write(json.dumps({'proposals': [{'title': ti}]}))
    dec = {f'd{i}': {'title': f'T{i}', 'decision': 'rejected', 'reason': f'r{i}', 'at': f'2026-11-{i + 1:02d}T00:00:00Z'} for i in range(32)}
    dec['x'] = {'title': 'noreason', 'decision': 'rejected', 'reason': '', 'at': '2026-12-01T00:00:00Z'}
    dec['y'] = {'title': 'appr', 'decision': 'approved', 'reason': 'ok', 'at': '2026-12-02T00:00:00Z'}
    open(os.path.join(rc, 'decisions.json'), 'w').write(json.dumps({'version': 1, 'decisions': dec}))
    titles, rej = sr.recent_context(rc, datetime(2026, 11, 8, 23, 30, tzinfo=timezone.utc))
    check('7일 = KST 오늘 기준 0~6일 전만 · ㉡ trial 포함 · 같은 제목 한 번', sorted(titles) == ['six', 'today', 'trial6'], titles)
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


    print('--- ⑱⑲ 투자 분야 · 상한 5')
    inv = dict(ok_skill('inv-skill'), area='invest')
    check('⑱ invest 통과 · 모르는 분야 버림', sr.validate(inv, {'v1'}) is None and sr.validate(dict(inv, area='art'), {'v1'}) == 'enum')
    reset_today(); fake([ok_skill(f'sk-{i}') for i in range(6)])
    code, r, _ = run()
    check('⑲ 6건 응답 → 5건 저장 · 1건 over_limit', r['proposals'] == 5 and r['dropped'] == 1
          and json.load(open(r['file']))['dropped'][0]['reason'] == 'over_limit', r)
    reset_today(); SENT.clear()

    print('--- ⑳~㉕ backfill')
    check('⑨ 장부 sha256 전후 동일(backfill 행 추가 전)', sha(DB) == db_sha)
    conn = sqlite3.connect(DB)
    for i in range(1, 86):
        tt = iso(now - timedelta(minutes=i * 10))
        conn.execute("INSERT INTO videos(record_id,video_id,title,summary,created_at,updated_at) VALUES(?,?,?,?,?,?)", (f'b{i}', f'bid{i}', f'bt{i}', 'S', tt, tt))
    conn.commit(); conn.close()
    db_sha = sha(DB)
    open(FAKE_OUT, 'w').write(json.dumps({'is_error': False, 'result': '{}', 'structured_output': {'proposals': [dict(ok_skill('bf-one', ('b1',)), area='invest')], 'note': 'N'}}))
    n0 = calls(); open(ARGS, 'w').close()
    code, r, _ = run('--backfill=30')
    d = json.load(open(r['file'])) if r['file'] else {}
    check('⑳ 영상 88(85+v1·v2·v4) → 묶음 3 · 호출 3 · 후보 1(묶음 밖 evidence 버림)', r['batches'] == 3 and calls() - n0 == 3 and r['candidates'] == 1
          and d.get('mode') == 'backfill' and d.get('considered', {}).get('videos') == 88 and d.get('considered', {}).get('tips') == 1, r)
    args = open(ARGS).read().splitlines()
    check('호출마다 도구 0 · MCP 엄격 · 재시도 0', len(args) == 3 and all('--tools||' in x and '--strict-mcp-config' in x for x in args), args)
    check('㉔ trial 폴더 · 정식 파일 없음 · 알림 0', os.sep + 'trial' + os.sep in r['file'] and not os.path.exists(today) and not SENT and r['notified'] is None, r)
    open(os.path.join(OUT, '20990101.json'), 'w').write(json.dumps({'through': 'X', 'proposals': []}))
    run('--backfill=30')
    check('㉔ 기준점 파일 불변', json.load(open(os.path.join(OUT, '20990101.json')))['through'] == 'X')
    os.remove(os.path.join(OUT, '20990101.json'))

    open(DYN, 'w').write('')
    n0 = calls()
    open(RANK_OUT, 'w').write(json.dumps({'is_error': False, 'result': '{}', 'structured_output': {'pick': [5, 2, 2, 99, 0, -1, 'x', 24], 'note': 'RK'}}))
    code, r, _ = run('--backfill=30')
    d = json.load(open(r['file']))
    check('㉑ 후보 24 → 순위 호출 1회(총 4) · 고른 순서 · 범위 밖·중복 무시 · 내용 무변경',
          calls() - n0 == 4 and [p['title'] for p in d['proposals']][:2] == ['T-b1-5', 'T-b1-2'] and len(d['proposals']) == 3 and d['proposals'][2]['title'].endswith('-8') and not d['proposals'][2]['title'].startswith('T-b1-')
          and d['proposals'][0]['action_prompt'] == 'p' and d['proposals'][0]['id'].endswith('-1') and d['note'] == 'RK', (calls() - n0, d.get('proposals')))
    open(RANKFAIL, 'w').write('')
    code, r, _ = run('--backfill=30')
    d = json.load(open(r['file']))
    check('㉒ 순위 호출 실패 → 앞 15건 · batch_errors 기록', code == 0 and len(d['proposals']) == 15 and d['proposals'][0]['title'] == 'T-b1-1'
          and any(x.startswith('순위') for x in d['batch_errors']), d.get('batch_errors'))
    os.remove(RANKFAIL); os.remove(DYN)

    open(FAKE_OUT, 'w').write(json.dumps({'is_error': False, 'result': '{}', 'structured_output': {'proposals': [], 'note': ''}}))
    open(FAILONCE, 'w').write(''); n0 = calls()
    code, r, _ = run('--backfill=30')
    check('㉓ 1회 실패는 계속(호출 3 · 성공 묶음 2)', code == 0 and calls() - n0 == 3 and r['batches'] == 2 and r['batch_errors'] == 1, r)
    open(FAIL, 'w').write(''); n0 = calls()
    before_files = sorted(os.listdir(os.path.join(OUT, 'trial')))
    code, r, _ = run('--backfill=30')
    check('㉓ 연속 2회 실패 → 호출 2에서 멈춤 · ok:false · 파일 없음', code == 1 and not r['ok'] and calls() - n0 == 2
          and sorted(os.listdir(os.path.join(OUT, 'trial'))) == before_files, r)
    os.remove(FAIL)

    n0 = calls(); before_files = sorted(os.listdir(os.path.join(OUT, 'trial')))
    code, r, out = run('--backfill=30', '--dry-run')
    check('㉕ --backfill --dry-run → 호출 0 · 쓰기 0 · 묶음 3 표시', code == 0 and calls() == n0 and 'batches=3' in out
          and sorted(os.listdir(os.path.join(OUT, 'trial'))) == before_files, out)
    check('backfill 도 장부 불변', sha(DB) == db_sha)

    print('--- 꿀팁 분산 · no_targets · tip_review 제한')
    conn = sqlite3.connect(DB)
    for i in range(2, 51):
        tt = iso(now - timedelta(minutes=60 + i))
        conn.execute("INSERT INTO tips(record_id,title,created_at,updated_at) VALUES(?,?,?,?)", (f'tp{i}', 'x', tt, tt))
    conn.commit(); conn.close(); db_sha = sha(DB)
    seen_prompts = []
    real_cc = sr.call_claude
    sr.call_claude = lambda prompt, schema=sr.SCHEMA, key='proposals': (seen_prompts.append(prompt), {'proposals': []})[1]
    code, r, _ = run('--backfill=30')
    sr.call_claude = real_cc
    per = [sum(1 for l in x.splitlines() if l.startswith('- [tp') or l.startswith('- [tip1]')) for x in seen_prompts]
    check('꿀팁 50건 → 묶음 3에 돌아가며 (17·17·16)', per == [17, 17, 16] and r['batches'] == 3, per)
    n0 = calls()
    code, r, _ = run('--backfill=0')
    check('대상 0 → 호출 0 · no_targets', code == 1 and r['error'] == 'no_targets' and calls() == n0, r)
    code, r, out = run('--backfill=30', '--dry-run')
    check('dry-run RESULT 의 batches = 실제 묶음 수', r['batches'] == 3 and r['batch_errors'] == 0, r)
    big = [{'id': 'tip1', 'verdict': 'skipped', 'reason': 'r' * 500}, {'id': 'tp2', 'verdict': 'proposed', 'reason': 'ok'}]
    cl = sr.clean_tip_review(big, {'tip1'})
    check('tip_review: id 중복 1개 · reason 200자 · 대상 수 이하', len(cl) == 1 and len(cl[0]['reason']) == 200)
    open(FAKE_OUT, 'w').write(json.dumps({'is_error': False, 'result': '{}', 'structured_output': {'proposals': [], 'note': ''}}))
    code, r, _ = run('--backfill=30')
    check('RESULT: candidates_total 키 · batch_errors 건수', code == 0 and r['candidates_total'] == 0 and r['batch_errors'] == 0, r)

    print('--- ㉖~㉘ 꿀팁 우선')
    reset_today()
    out_tr = {'proposals': [ok_skill()], 'tip_review': [{'id': 'tip1', 'verdict': 'proposed', 'reason': 'r'}, {'id': 'zzz', 'verdict': 'skipped', 'reason': 'x'},
              {'id': 'tip1', 'verdict': 'maybe', 'reason': 'x'}, 'bad', {'id': ['tip1'], 'verdict': 'proposed', 'reason': 'x'},
              {'id': {'a': 1}, 'verdict': 'skipped', 'reason': 'x'}, {'id': 'tip1', 'verdict': 'skipped', 'reason': 'dup'}]}
    open(FAKE_OUT, 'w').write(json.dumps({'is_error': False, 'result': '{}', 'structured_output': out_tr}))
    code, r, _ = run('--days=1')
    pr = open(IN, encoding='utf-8').read()
    check('㉖ 프롬프트에 우선 문구 · 꿀팁 절 제목', '영상보다 우선한다' in pr and '## 대표님이 직접 남긴 꿀팁 (우선)' in pr and 'tip_review' in pr)
    check('㉗ tip_review 저장 · 대상 밖 id·틀린 항목 버림', json.load(open(r['file']))['tip_review'] == [{'id': 'tip1', 'verdict': 'proposed', 'reason': 'r'}], r)
    fake([ok_skill()])
    code, r, _ = run('--days=1')
    check('㉗ tip_review 없음 → 빈 배열 · 실패 아님', code == 0 and json.load(open(r['file']))['tip_review'] == [], r)
    rp = sr.rank_prompt('p', [ok_skill('a-x', ('tip1',)), ok_skill('b-x', ('v1',))], {'tip1'})
    check('㉘ 순위 프롬프트: 꿀팁근거 예/아니오 · 우선 문구', '꿀팁근거: 예' in rp and '꿀팁근거: 아니오' in rp and '우선합니다' in rp)

    print('--- ⑨ 장부 불변')
    check('장부 sha256 전후 동일(backfill 이후 기준)', sha(DB) == db_sha)

finally:
    shutil.rmtree(tmp, ignore_errors=True)
p = sum(results)
print(f'RESULT: {p}/{len(results)} 통과')
sys.exit(0 if p == len(results) else 1)
