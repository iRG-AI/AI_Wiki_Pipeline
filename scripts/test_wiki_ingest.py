#!/usr/bin/env python3
"""
wiki_ingest.py (v4.5 wiki_extract 누적·재렌더·backfill·씨앗) + scripts/migrate_library.py 회귀 테스트
— 네트워크 0회(Gemini 는 가짜), 실제 Vault·data/·상태 파일 무변경

  /opt/homebrew/bin/python3 scripts/test_wiki_ingest.py

끝에 'N/N PASS' 를 찍고 실패가 있으면 종료 코드 1.
"""
import contextlib, hashlib, io, json, os, re, shutil, sqlite3, sys, tempfile
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

import wiki_config as wc        # noqa: E402
wc.urlopen = _no_net
import wiki_ingest as wi        # noqa: E402
import migrate_library as mig   # noqa: E402
import library_db as ldb        # noqa: E402

REAL = {k: getattr(wi, k) for k in ('VAULT', 'WIKI_DIR', 'ENTITIES_DIR', 'CONCEPTS_DIR')}
REAL_STATE, REAL_DB, REAL_QUOTA = wc.STATE_FILE, ldb.DB_PATH, wc._QUOTA_FILE
for _k in ('WIKI_BACKFILL_DAILY_MAX', 'WIKI_BACKFILL_BATCH'):
    os.environ.pop(_k, None)   # 바깥 셸 값이 테스트를 흔들지 않게

results = []
def check(name, cond, detail=''):
    results.append((name, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}  {name}' + (f'  — {detail}' if detail and not cond else ''))


def tree_hash(root):
    h = hashlib.sha256()
    for d, _, fs in sorted(os.walk(root)):
        for f in sorted(fs):
            p = os.path.join(d, f)
            h.update(p.encode()); h.update(open(p, 'rb').read())
    return h.hexdigest()


# ── 가짜 Gemini ──
CALLS = []
SINGLE = {}      # 제목 → 응답 문자열
BATCH_DROP = set()   # backfill 응답에서 뺄 제목
def fake_gemini(prompt, temperature=0.2, max_tokens=4000):
    if '### S1' in prompt:
        CALLS.append(('batch', max_tokens))
        out = []
        for m in re.finditer(r'### S(\d+)\n- 제목: (.*)\n', prompt):
            sid, title = m.group(1), m.group(2)
            if title in BATCH_DROP: continue
            out.append({'id': f'S{sid}', 'entities': [{'name': 'Claude Code', 'insight': f'BF {title}', 'role': '도구'}],
                        'concepts': [{'name': '바이브코딩', 'insight': f'BF {title}'}], 'relations': []})
        return json.dumps({'results': out}, ensure_ascii=False)
    title = re.search(r'- 제목: (.*)\n', prompt).group(1)
    CALLS.append(('single', title))
    r = SINGLE.get(title)
    if isinstance(r, Exception):
        raise r
    return r if r is not None else json.dumps({'entities': [], 'concepts': [], 'relations': []})
wi.gemini_call = fake_gemini


def ok_json(ents=(), cons=(), rels=()):
    return json.dumps({'entities': [{'name': n, 'insight': f'{n} 요점', 'role': r} for n, r in ents],
                       'concepts': [{'name': n, 'insight': f'{n} 요점'} for n in cons],
                       'relations': [{'from': a, 'to': b, 'type': t} for a, b, t in rels]}, ensure_ascii=False)


def note(vault, folder, fname, title, rid, date='2026-10-01'):
    p = os.path.join(vault, folder, fname)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'w', encoding='utf-8').write(
        f'---\ntitle: "{title}"\nchannel: "채널"\nupload_date: {date}\nnotion_id: {rid}\n---\n\n## 영상 개요\n{title} 본문\n')
    return p


def setup(name, db_version=None):
    root = tempfile.mkdtemp(prefix=f'wiki_ingest_{name}_')
    vault = os.path.join(root, 'vault')
    os.makedirs(vault)
    wi.VAULT = vault
    wi.WIKI_DIR = os.path.join(vault, '_wiki')
    wi.ENTITIES_DIR = os.path.join(wi.WIKI_DIR, 'entities')
    wi.CONCEPTS_DIR = os.path.join(wi.WIKI_DIR, 'concepts')
    os.makedirs(wi.ENTITIES_DIR); os.makedirs(wi.CONCEPTS_DIR)
    wc.STATE_FILE = os.path.join(root, '.wiki_state.json')
    wc._QUOTA_FILE = os.path.join(root, '.wiki_quota.json')
    ldb.DB_PATH = os.path.join(root, 'data', 'library.db')
    c = ldb.open_db(ldb.DB_PATH); ldb.apply_schema(c)
    with c:
        c.execute("INSERT INTO videos (record_id, video_id, title, created_at, updated_at) VALUES ('v','VVVVVVVVVVV','t','x','x')")
    c.close()
    CALLS.clear(); SINGLE.clear(); BATCH_DROP.clear()
    wc.ENV.pop('WIKI_BACKFILL_DAILY_MAX', None)
    return root, vault


def run(*args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = wi.main(list(args))
    out = buf.getvalue()
    m = re.search(r'WIKI_RESULT:(\{.*\})', out)
    return code, out, (json.loads(m.group(1)) if m else None)


def page(vault, kind, name):
    p = os.path.join(vault, '_wiki', kind, f'{name}.md')
    return open(p, encoding='utf-8').read() if os.path.exists(p) else ''


def rows():
    c = sqlite3.connect(ldb.DB_PATH); c.row_factory = sqlite3.Row
    r = {x['record_id']: dict(x) for x in c.execute('SELECT * FROM wiki_extract')}
    c.close()
    return r


def state():
    return json.load(open(wc.STATE_FILE, encoding='utf-8'))


# ═══ 1. 핵심 회귀 — 두 번째 실행이 첫 실행분을 지우지 않는다 ═══
root, vault = setup('accum')
note(vault, 'AI Claude', 'a1.md', '영상A', 'rid-a')
note(vault, 'AI Claude', 'b1.md', '영상B', 'rid-b')
SINGLE['영상A'] = ok_json([('Claude Code', '도구')], ['바이브코딩'], [('Claude Code', '바이브코딩', '사용')])
SINGLE['영상B'] = ok_json([('Claude Code', '주제')], ['바이브코딩', 'MCP'])
code, out, r1 = run()
check('1차: 2건 처리 · 개념 2 · 엔티티 1', code == 0 and r1['processed'] == 2 and r1['concepts'] == 2 and r1['entities'] == 1, str(r1))
note(vault, 'AI Gemini', 'c1.md', '영상C', 'rid-c', date='2026-10-05')
SINGLE['영상C'] = ok_json([('Gemini', '주제')], ['바이브코딩'])
code, out, r2 = run()
p = page(vault, 'concepts', '바이브코딩')
check('2차: 신규 1건만 Gemini 호출', len(CALLS) == 3 and CALLS[-1] == ('single', '영상C') and sorted(CALLS[:2]) == [('single', '영상A'), ('single', '영상B')], CALLS)
check('2차 뒤 바이브코딩 페이지 = 3건 누적 (1차분 유지)', 'source_count: 3' in p and '[[a1|영상A]]' in p and '[[b1|영상B]]' in p and '[[c1|영상C]]' in p, p[:400])
check('MCP 페이지는 2차에 안 건드렸어도 그대로 1건', 'source_count: 1' in page(vault, 'concepts', 'MCP'))
idx = open(os.path.join(vault, '_wiki', 'index.md'), encoding='utf-8').read()
check('index = 전체 (엔티티 2 · 개념 2)', '— 2개' in idx and '[[Claude Code]] | 2개' in idx and '[[바이브코딩]] | 3개' in idx and '[[Gemini]] | 1개' in idx, idx)
e = page(vault, 'entities', 'Claude Code')
check('엔티티 페이지: 역할별 절 + 관계', '## 🎯 주제로 다룬 영상 (1개)' in e and '## 🔧 도구로 다룬 영상 (1개)' in e and '- [[바이브코딩]] — 사용' in e, e)
check('최신 업로드가 위', p.index('[[c1|') < p.index('[[a1|'))
check('state concepts = 전체 카운트', state()['concepts'] == {'MCP': 1, '바이브코딩': 3}, state().get('concepts'))
check('wiki_extract 3행 ok · source single', {k: (v['status'], v['source']) for k, v in rows().items()} == {k: ('ok', 'single') for k in ('rid-a', 'rid-b', 'rid-c')})
h = tree_hash(os.path.join(vault, '_wiki'))
code, out, r3 = run('--render-only')
check('--render-only: Gemini 0회 · 파일 무변경(결정적 렌더)', len(CALLS) == 3 and tree_hash(os.path.join(vault, '_wiki')) == h and r3['entities_updated'] == 0 and r3['concepts_updated'] == 0, str(r3))
log_md = open(os.path.join(vault, '_wiki', 'log.md'), encoding='utf-8').read()
check('변화 없는 실행은 log.md 에 안 남김', log_md.count('## [') == 2, log_md.count('## ['))

# 제목·파일명 변경(retitle)과 고아
os.rename(os.path.join(vault, 'AI Claude', 'a1.md'), os.path.join(vault, 'AI Claude', 'a2.md'))
note(vault, 'AI Claude', 'a2.md', '영상A 새 제목', 'rid-a')
os.remove(os.path.join(vault, 'AI Claude', 'b1.md'))
code, out, r4 = run('--render-only')
p = page(vault, 'concepts', '바이브코딩')
check('제목·파일명 변경이 페이지에 반영', '[[a2|영상A 새 제목]]' in p and '[[a1|' not in p, p)
check('Vault 에서 빠진 소스는 페이지에서 빠짐 · 장부 행은 보존', '[[b1|' not in p and 'source_count: 2' in p and 'rid-b' in rows())
check('항목 0개가 된 MCP 기존 페이지는 지우지 않음', os.path.exists(os.path.join(vault, '_wiki', 'concepts', 'MCP.md')))
check('네트워크 0회', NET_CALLS == [])

# ═══ 2. 응답 해석 실패 — ingested 에 넣지 않고 3회에서 포기 ═══
root, vault = setup('fail')
note(vault, 'AI Claude', 'x.md', '깨진응답', 'rid-x')
SINGLE['깨진응답'] = '이건 JSON 이 아님'
wc.ENV['WIKI_BACKFILL_DAILY_MAX'] = '0'
code, out, r = run()
check('실패 1회: ingested 에 없음 · failed 행 attempts 1', 'rid-x' not in state()['ingested'] and rows()['rid-x']['status'] == 'failed' and rows()['rid-x']['attempts'] == 1 and r['failed'] == 1, str(r))
run(); code, out, r = run()
check('실패 3회: 포기(ingested 표시) · attempts 3', 'rid-x' in state()['ingested'] and rows()['rid-x']['attempts'] == 3, rows().get('rid-x'))
n = len(CALLS); run()
check('포기 뒤엔 다시 태우지 않음', len(CALLS) == n)
SINGLE['빈결과'] = json.dumps({'entities': [], 'concepts': []})
note(vault, 'AI Claude', 'y.md', '빈결과', 'rid-y')
run()
check('정상 JSON 의 빈 결과는 ok (실패 아님)', rows()['rid-y']['status'] == 'ok' and 'rid-y' in state()['ingested'])
SINGLE['목록밖'] = ok_json([('없는도구', '도구'), ('Claude', '이상한역할')], ['없는개념'])
note(vault, 'AI Claude', 'z.md', '목록밖', 'rid-z')
run()
z = rows()['rid-z']
check('목록 밖 이름은 버리고 역할은 관련으로', json.loads(z['entities']) == [{'name': 'Claude', 'insight': 'Claude 요점', 'role': '관련'}] and json.loads(z['concepts']) == [], z)

# ═══ 3. 할당량 소진 — 남은 건 다음에, 렌더는 한다 ═══
root, vault = setup('quota')
note(vault, 'AI Claude', 'q1.md', 'Q1', 'rid-q1'); note(vault, 'AI Claude', 'q2.md', 'Q2', 'rid-q2')
SINGLE['Q1'] = SINGLE['Q2'] = ok_json([], ['MCP'])
_orig = wi.gemini_call
def _quota_second(prompt, **k):
    if len(CALLS) >= 1:
        CALLS.append(('quota',)); raise wc.DailyQuotaExhausted('소진')
    return fake_gemini(prompt, **k)
wi.gemini_call = _quota_second
json.dump({'ingested': {'rid-old': 'x'}}, open(wc.STATE_FILE, 'w', encoding='utf-8'))
note(vault, 'AI Claude', 'old.md', '옛것', 'rid-old')
code, out, r = run()
wi.gemini_call = _orig
done = [k for k in ('rid-q1', 'rid-q2') if k in state()['ingested']]
check('소진: 1건만 기록 · 나머지 미처리 · 렌더 됨 · backfill 안 함', len(done) == 1 and set(rows()) == set(done) and 'source_count: 1' in page(vault, 'concepts', 'MCP') and r['backfill_calls'] == 0 and r['backfill_left'] is None and r['processed'] == 1, str(r))

# ═══ 4. 씨앗 — 옛 페이지 항목을 wiki_extract 로 ═══
root, vault = setup('seed')
note(vault, 'AI Claude', 's1.md', 'S원1', 'rid-s1'); note(vault, 'AI Claude', 's2.md', 'S원2', 'rid-s2')
note(vault, 'AI Claude', '채널 [Tech]_[한영자막] 제목_20260914.md', '[한영자막] 제목', 'rid-s3')
open(os.path.join(vault, '_wiki', 'entities', 'Claude.md'), 'w', encoding='utf-8').write(
    '---\ntype: entity\nname: "Claude"\nsource_count: 2\nlast_updated: 2026-10-01 00:00\n---\n\n# Claude\n\n> 총 **2개** 영상에서 언급됨\n\n'
    '## 🎯 주제로 다룬 영상 (1개)\n\n- [[s1|S원1]] `채널` 2026-10-01\n  > 옛 인사이트1\n\n'
    '## 🔧 도구로 다룬 영상 (1개)\n\n- [[없는파일|유령]] `채널` 2026-09-01\n  > 유령\n\n## 🔗 관련 엔티티/개념\n\n- [[MCP]] — 사용\n')
open(os.path.join(vault, '_wiki', 'concepts', 'MCP.md'), 'w', encoding='utf-8').write(
    '---\ntype: concept\nname: "MCP"\nsource_count: 2\n---\n\n# MCP\n\n## 📚 관련 영상\n\n'
    '- [[s1|S원1]] `채널` 2026-10-01\n  > MCP 인사이트1\n- [[s2|S원2]] `채널` 2026-10-01\n  > MCP 인사이트2\n'
    '- [[채널 [Tech]_[한영자막] 제목_20260914|[한영자막] 제목]] `채널 [Tech]` 2026-09-14\n  > 대괄호 파일명\n')
open(os.path.join(vault, '_wiki', 'concepts', '없는개념.md'), 'w', encoding='utf-8').write('- [[s1|S원1]] `x` 1\n')
db0 = open(ldb.DB_PATH, 'rb').read()
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    wi.main(['--seed-from-pages'])
sr = json.loads(re.search(r'SEED_RESULT:(\{.*\})', buf.getvalue()).group(1))
check('씨앗 dry-run: 장부 무변경 · 페이지 2 · 항목 5 · 소스 3(파일명 대괄호 포함) · 매칭 실패 1', open(ldb.DB_PATH, 'rb').read() == db0 and (sr['pages'], sr['items'], sr['records'], sr['unmatched'], sr['written']) == (2, 5, 3, 1, 0), str(sr))
with contextlib.redirect_stdout(io.StringIO()):
    wi.main(['--seed-from-pages', '--apply'])
rs = rows()
check('씨앗 적용: seed 3행 · 역할·인사이트 보존', {k: v['status'] for k, v in rs.items()} == {'rid-s1': 'seed', 'rid-s2': 'seed', 'rid-s3': 'seed'}
      and json.loads(rs['rid-s1']['entities']) == [{'name': 'Claude', 'insight': '옛 인사이트1', 'role': '주제'}]
      and json.loads(rs['rid-s2']['concepts']) == [{'name': 'MCP', 'insight': 'MCP 인사이트2'}], rs)
code, out, r = run('--render-only')
mp = page(vault, 'concepts', 'MCP')
check('씨앗 렌더: 옛 항목 그대로 다시 그림', '[[s1|S원1]]' in mp and '> MCP 인사이트2' in mp and '> 대괄호 파일명' in mp and 'source_count: 3' in mp, mp)
check('씨앗 렌더: 매칭 안 된 항목은 빠짐', '유령' not in page(vault, 'entities', 'Claude'))
with contextlib.redirect_stdout(io.StringIO()):
    wi.main(['--seed-from-pages', '--apply'])
check('씨앗 재적용: 그대로 3행 (멱등)', len(rows()) == 3)

# ═══ 5. backfill — 처리됐지만 wiki_extract 에 없는/seed 뿐인 소스를 묶어서 ═══
#   (위 seed 환경 이어서) s1·s2 = seed, 여기에 옛 ingested 45건 추가
for i in range(45):
    note(vault, 'AI Claude', f'old{i:02d}.md', f'옛영상{i:02d}', f'rid-old{i:02d}')
st = {'ingested': {f'rid-old{i:02d}': 'x' for i in range(45)}}
st['ingested'].update({'rid-s1': 'x', 'rid-s2': 'x', 'rid-s3': 'x'})
json.dump(st, open(wc.STATE_FILE, 'w', encoding='utf-8'))
wc.ENV['WIKI_BACKFILL_DAILY_MAX'] = '2'
BATCH_DROP.add('옛영상03')
CALLS.clear()
code, out, r = run()
check('backfill: 하루 상한 2회만 · 묶음 20건 · max_tokens 16000', [c for c in CALLS if c[0] == 'batch'] == [('batch', 16000), ('batch', 16000)] and r['backfill_calls'] == 2, CALLS)
rs = rows()
check('backfill: 39건 ok(batch) · 응답 빠진 1건 failed · 남은 대상 9', r['backfill_done'] == 39 and rs['rid-old03']['status'] == 'failed' and rs['rid-old03']['attempts'] == 1 and r['backfill_left'] == 9, str(r))
check('backfill: 오늘 사용 2회 기록(태평양시 날짜)', state()['backfill'] == {'date': wc._today(), 'calls': 2}, state().get('backfill'))
check('backfill 결과가 페이지에 들어감', 'BF 옛영상00' in page(vault, 'entities', 'Claude Code') and 'source_count: 39' in page(vault, 'concepts', '바이브코딩'))
CALLS.clear(); run()
check('같은 날 다시 실행: backfill 0회', CALLS == [])
st = state(); st['backfill'] = {'date': '2000-01-01', 'calls': 9}; json.dump(st, open(wc.STATE_FILE, 'w', encoding='utf-8'))
BATCH_DROP.clear(); CALLS.clear()
code, out, r = run()
rs = rows()
check('다음 날: 남은 9건(seed 3 · 실패 1 포함) 1회로 끝', r['backfill_calls'] == 1 and r['backfill_left'] == 0 and rs['rid-s1']['status'] == 'ok' and rs['rid-old03']['status'] == 'ok', str(r))
check('seed 가 batch 결과로 교체됨', json.loads(rs['rid-s1']['concepts']) == [{'name': '바이브코딩', 'insight': 'BF S원1'}])
CALLS.clear(); run()
check('대상 0이면 호출 0', CALLS == [])

# --no-backfill · 신규 소스는 backfill 대상 아님
root, vault = setup('nobf')
note(vault, 'AI Claude', 'n1.md', 'N1', 'rid-n1')
json.dump({'ingested': {'rid-n1': 'x'}}, open(wc.STATE_FILE, 'w', encoding='utf-8'))
code, out, r = run('--no-backfill')
check('--no-backfill: 호출 0 · 대상은 남음', CALLS == [] and r['backfill_calls'] == 0 and r['backfill_left'] is None, str(r))
wc.ENV['WIKI_BACKFILL_DAILY_MAX'] = '0'
code, out, r = run()
check('WIKI_BACKFILL_DAILY_MAX=0: 호출 0', CALLS == [] and r['backfill_left'] == 1, str(r))
wc.ENV['WIKI_BACKFILL_DAILY_MAX'] = '숫자아님'
check('상한 값이 이상하면 기본 30', wi.backfill_max() == 30)
wc.ENV['WIKI_BACKFILL_BATCH'] = '500'
check('묶음 크기 상한 40 · 이상값은 기본 20', wi.batch_size() == 40 and (wc.ENV.update({'WIKI_BACKFILL_BATCH': 'x'}) or wi.batch_size() == 20))
wc.ENV.pop('WIKI_BACKFILL_BATCH', None)
wc.ENV['WIKI_BACKFILL_DAILY_MAX'] = '0'; os.environ['WIKI_BACKFILL_DAILY_MAX'] = '1'
check('프로세스 환경변수가 .env 보다 먼저', wi.backfill_max() == 1)
del os.environ['WIKI_BACKFILL_DAILY_MAX']

# ═══ 6. 장부 없음·버전 다름 — Vault 를 건드리지 않는다 ═══
root, vault = setup('nodb')
note(vault, 'AI Claude', 'k.md', 'K', 'rid-k')
os.remove(ldb.DB_PATH)
h = tree_hash(vault)
try:
    run(); raised = False
except FileNotFoundError:
    raised = True
check('장부 없음: 던짐 · 장부 안 만듦 · Vault 무변경', raised and not os.path.exists(ldb.DB_PATH) and tree_hash(vault) == h)

# ═══ 7. migrate_library ═══
root, vault = setup('mig')
c = sqlite3.connect(ldb.DB_PATH)
c.execute('DROP TABLE wiki_extract'); c.execute('PRAGMA user_version = 1'); c.commit(); c.close()
try:
    run(); raised = ''
except RuntimeError as e:
    raised = str(e)
check('v1 장부를 v2 코드가 열면 던짐', 'user_version 1' in raised, raised)
b0 = open(ldb.DB_PATH, 'rb').read()
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    code = mig.main([])
rj = json.loads(buf.getvalue().split('RESULT_JSON ')[1])
check('migrate dry-run: 무변경 · missing [wiki_extract]', code == 0 and open(ldb.DB_PATH, 'rb').read() == b0 and rj['missing'] == ['wiki_extract'] and rj['dry_run'], str(rj))
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    code = mig.main(['--apply'])
rj = json.loads(buf.getvalue().split('RESULT_JSON ')[1])
check('migrate --apply: user_version 2 · 행 수 그대로 · 백업 생김', code == 0 and rj['ok'] and rj['user_version'] == 2 and rj['rows'] == {'videos': 1, 'videos_dup': 0, 'tips': 0, 'meta': 0} and os.path.exists(rj['backup']), str(rj))
bk = sqlite3.connect(rj['backup'])
check('백업 사본은 v1 그대로', bk.execute('PRAGMA user_version').fetchone()[0] == 1); bk.close()
code, out, r = run()
check('이전 뒤 wiki_ingest 정상', code == 0 and r is not None)
with contextlib.redirect_stdout(io.StringIO()):
    code = mig.main(['--apply'])
check('migrate 재실행: 이미 최신 exit 0', code == 0)
c = sqlite3.connect(ldb.DB_PATH); c.execute('PRAGMA user_version = 7'); c.commit(); c.close()
with contextlib.redirect_stdout(io.StringIO()):
    code = mig.main(['--apply'])
check('migrate: 범위 밖 버전은 거부 exit 1', code == 1)
with contextlib.redirect_stdout(io.StringIO()):
    code = mig.main(['--apply', '--db=' + os.path.join(root, '없음.db')])
check('migrate: 장부 없으면 exit 1 · 안 만듦', code == 1 and not os.path.exists(os.path.join(root, '없음.db')))
c = sqlite3.connect(':memory:'); c.executescript(ldb.schema_sql())
check('스키마 파일 user_version = SCHEMA_VERSION', c.execute('PRAGMA user_version').fetchone()[0] == ldb.SCHEMA_VERSION == 2); c.close()

# ═══ 마무리 ═══
check('전체 네트워크 0회', NET_CALLS == [])
check('실제 상태 파일·장부 경로는 건드리지 않음(경로 복원 전 확인)', REAL_STATE != wc.STATE_FILE and REAL_DB != ldb.DB_PATH)
for k, v in REAL.items():
    setattr(wi, k, v)
wc.STATE_FILE, ldb.DB_PATH, wc._QUOTA_FILE = REAL_STATE, REAL_DB, REAL_QUOTA

passed = sum(1 for _, ok in results if ok)
print(f'\n{passed}/{len(results)} PASS')
sys.exit(0 if passed == len(results) else 1)
