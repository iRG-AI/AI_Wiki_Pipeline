#!/usr/bin/env python3
"""backup_library.py 회귀 테스트 (v4.1). 실제 장부·.env·드라이브를 건드리지 않는다 — 전부 임시 폴더.

    /opt/homebrew/bin/python3 scripts/test_backup_library.py

지키는 것:
  1) 하루 1회 — 오늘(KST) 이름이 있는 폴더는 건너뛴다. 드라이브만 빠졌으면 드라이브에만 다시 쓴다
  2) 백업 = 장부와 같은 내용(압축 풀어 sha256·integrity_check·행 수), 장부 파일은 한 바이트도 안 바뀐다
  3) 드라이브 폴더의 부모가 없으면(앱 꺼짐) 만들지 않고 실패 — 로컬은 그대로 만든다
  4) 사본 검사(빈 장부·user_version·장부 없음)에 걸리면 아무것도 만들지 않고 기존 백업도 지우지 않는다
  5) 보관: 최신 7개 + 주별 4개 = 최대 11개. 이름 형식이 다른 파일은 절대 지우지 않는다
  6) --dry-run 은 아무것도 쓰지 않는다. 임시 파일이 남지 않는다
"""
import gzip, hashlib, io, json, os, sqlite3, sys, tempfile
from contextlib import redirect_stdout
from datetime import date, timedelta

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, 'lib'))
import library_db as ldb      # noqa: E402
import backup_library as bl   # noqa: E402

results = []


def check(name, cond, detail=''):
    results.append(bool(cond))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f'  — {detail}' if detail and not cond else ''), flush=True)


TMP = tempfile.mkdtemp(prefix='backup-lib-test-')
ENV = {}
TODAY = [date(2026, 10, 12)]
bl.load_env = lambda: dict(ENV)
bl.today_kst = lambda: TODAY[0]


def make_db(path, videos=3, tips=2, user_version=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = ldb.open_db(path)
    ldb.apply_schema(conn)
    ts = '2026-10-11T00:00:00.000Z'
    for i in range(videos):
        conn.execute('INSERT INTO videos (record_id, video_id, title, summary, created_at, updated_at) VALUES (?,?,?,?,?,?)',
                     (f'rec-{i}', f'VID{i:08d}', f'영상 {i}', '요약 ' * 50, ts, ts))
    for i in range(tips):
        conn.execute('INSERT INTO tips (record_id, title, url, created_at, updated_at) VALUES (?,?,?,?,?)',
                     (f'tip-{i}', f'꿀팁 {i}', f'https://ex.com/{i}', ts, ts))
    conn.execute("INSERT INTO meta (key, value) VALUES ('switched_at', ?)", (ts,))
    if user_version is not None:
        conn.execute(f'PRAGMA user_version = {user_version}')
    conn.commit()
    conn.close()


def setup(name, **kw):
    """케이스마다 새 장부·새 로컬 폴더"""
    root = os.path.join(TMP, name)
    db = os.path.join(root, 'data', 'library.db')
    if kw.pop('no_db', False):
        os.makedirs(os.path.dirname(db), exist_ok=True)
    else:
        make_db(db, **kw)
    bl.DB_PATH = db
    bl.LOCAL_DIR = os.path.join(root, 'data', 'backups')
    ENV.clear()
    TODAY[0] = date(2026, 10, 12)
    return root, db


def run(*argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = bl.main(list(argv))
    out = buf.getvalue()
    rj = next((json.loads(l[len('RESULT_JSON:'):]) for l in out.splitlines() if l.startswith('RESULT_JSON:')), None)
    return code, out, rj


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def unpack(gz_path, out_path):
    with gzip.open(gz_path, 'rb') as fi, open(out_path, 'wb') as fo:
        fo.write(fi.read())
    return out_path


def leftovers(folder):
    return [n for n in (os.listdir(folder) if os.path.isdir(folder) else []) if n.startswith('.snap-') or n.endswith('.tmp')]


NAME = 'library-20261012.db.gz'

print('[1] 드라이브 미설정 → 로컬만')
root, db = setup('local_only')
before = sha(db)
code, out, rj = run()
f = os.path.join(bl.LOCAL_DIR, NAME)
check('exit 0', code == 0, out)
check('로컬 파일 생성', os.path.exists(f))
check('drive = not_configured', rj and rj['dests'].get('drive') == 'not_configured', str(rj))
check('행 수 보고 (영상 3 · 꿀팁 2)', rj and rj['rows']['videos'] == 3 and rj['rows']['tips'] == 2, str(rj))
raw = unpack(f, os.path.join(root, 'restored.db'))
check('압축 해제본 sha256 = 보고값', rj and sha(raw) == rj['sha256'])
c = sqlite3.connect(raw)
check('해제본 integrity_check ok', c.execute('PRAGMA integrity_check').fetchone()[0] == 'ok')
check(f'해제본 user_version = {ldb.SCHEMA_VERSION}', c.execute('PRAGMA user_version').fetchone()[0] == ldb.SCHEMA_VERSION)
check('해제본 meta 보존', c.execute("SELECT value FROM meta WHERE key='switched_at'").fetchone() is not None)
c.close()
check('장부 파일 무변경 (sha256)', sha(db) == before)
check('임시 파일 없음', leftovers(bl.LOCAL_DIR) == [], str(leftovers(bl.LOCAL_DIR)))

print('[2] 같은 날 다시 → skipped')
mt = os.path.getmtime(f)
code, out, rj = run()
check('exit 0 · skipped already_done', code == 0 and rj and rj.get('skipped') == 'already_done', str(rj))
check('파일 다시 안 씀 (mtime 같음)', os.path.getmtime(f) == mt)

print('[3] --force → 같은 이름 다시 만듦')
os.utime(f, (1, 1))
code, out, rj = run('--force')
check('exit 0', code == 0, out)
check('다시 씀 (mtime 바뀜)', os.path.getmtime(f) != 1)

print('[4] 드라이브 설정 → 두 곳 모두, 내용 동일')
root, db = setup('both')
drive_parent = os.path.join(root, 'GoogleDrive', '내 드라이브')
os.makedirs(drive_parent)
ENV['LIBRARY_BACKUP_DIR'] = os.path.join(drive_parent, 'YouTube_Ledger_Backup')
code, out, rj = run()
fl, fd = os.path.join(bl.LOCAL_DIR, NAME), os.path.join(ENV['LIBRARY_BACKUP_DIR'], NAME)
check('exit 0 · local ok · drive ok', code == 0 and rj['dests'] == {'local': 'ok', 'drive': 'ok'}, str(rj))
check('드라이브 하위 폴더 자동 생성 + 파일', os.path.exists(fd))
check('두 파일 바이트 동일', os.path.exists(fl) and sha(fl) == sha(fd))
check('드라이브 쪽 임시 파일 없음', leftovers(ENV['LIBRARY_BACKUP_DIR']) == [])

print('[5] 로컬만 있고 드라이브에 없음 → 드라이브에만 씀')
os.remove(fd)
mt = os.path.getmtime(fl)
code, out, rj = run()
check('exit 0 · local exists · drive ok', code == 0 and rj['dests'] == {'local': 'exists', 'drive': 'ok'}, str(rj))
check('로컬 다시 안 씀', os.path.getmtime(fl) == mt)
check('드라이브 파일 생김', os.path.exists(fd))

print('[6] 드라이브 부모 없음(앱 꺼짐) → 로컬은 만들고 실패 보고')
root, db = setup('drive_gone')
gone = os.path.join(root, 'GoogleDrive-없음', '내 드라이브', 'YouTube_Ledger_Backup')
ENV['LIBRARY_BACKUP_DIR'] = gone
code, out, rj = run()
check('exit 1', code == 1, out)
check('drive = unavailable · local = ok', rj and rj['dests'] == {'local': 'ok', 'drive': 'unavailable'}, str(rj))
check('error = drive_unavailable', rj and rj['error'] == 'drive_unavailable', str(rj))
check('없는 드라이브 경로를 만들지 않음', not os.path.exists(os.path.dirname(os.path.dirname(gone))))
check('로컬 파일 생성', os.path.exists(os.path.join(bl.LOCAL_DIR, NAME)))
code, out, rj = run()
check('다음 실행: 로컬 있음 + 드라이브 없음 → exit 1 (계속 알림)', code == 1 and rj['error'] == 'drive_unavailable', str(rj))

print('[7] 사본 검사 실패 → 만들지 않고 기존 백업 유지')
root, db = setup('empty', videos=0)
os.makedirs(bl.LOCAL_DIR)
old = [f'library-202609{d:02d}.db.gz' for d in range(1, 21)]
for n in old:
    open(os.path.join(bl.LOCAL_DIR, n), 'wb').write(b'x')
code, out, rj = run()
check('빈 장부 → exit 1 · snapshot:empty_ledger', code == 1 and rj['error'] == 'snapshot:empty_ledger', str(rj))
check('오늘 파일 안 만듦', not os.path.exists(os.path.join(bl.LOCAL_DIR, NAME)))
check('기존 백업 20개 그대로 (정리 안 함)', sorted(bl.list_backups(bl.LOCAL_DIR)) == sorted(old))
check('임시 파일 없음', leftovers(bl.LOCAL_DIR) == [], str(leftovers(bl.LOCAL_DIR)))
root, db = setup('uv', user_version=9)
code, out, rj = run()
check('user_version 다름 → exit 1 · snapshot:user_version:9', code == 1 and rj['error'] == 'snapshot:user_version:9', str(rj))
root, db = setup('nodb', no_db=True)
code, out, rj = run()
check('장부 없음 → exit 1 · snapshot:no_db', code == 1 and rj['error'] == 'snapshot:no_db', str(rj))
check('장부 없을 때 장부를 만들지 않음', not os.path.exists(db))

print('[8] 보관 규칙 (순수 함수)')
days = [date(2026, 10, 12) - timedelta(days=i) for i in range(60)]
names = [bl.backup_name(d) for d in days]
victims = set(bl.plan_prune(names))
kept = sorted(set(names) - victims, reverse=True)
want = [bl.backup_name(date(2026, 10, d)) for d in (12, 11, 10, 9, 8, 7, 6)] + \
       [bl.backup_name(date(2026, 10, 4)), bl.backup_name(date(2026, 9, 27)),
        bl.backup_name(date(2026, 9, 20)), bl.backup_name(date(2026, 9, 13))]   # 일요일. 10-05(월)은 10-06 과 같은 주라 일별이 대표
check('60일 연속 → 11개 (최신 7 + 일요일 4)', kept == want, str(kept))
sparse = [bl.backup_name(date(2026, 10, d)) for d in (12, 1)] + [bl.backup_name(date(2026, 9, d)) for d in (30, 29, 24, 23, 3, 2, 1)] + \
         [bl.backup_name(date(2026, 8, 20))]
kept = sorted(set(sparse) - set(bl.plan_prune(sparse)), reverse=True)
want = [bl.backup_name(date(2026, 10, 12)), bl.backup_name(date(2026, 10, 1)), bl.backup_name(date(2026, 9, 30)),
        bl.backup_name(date(2026, 9, 29)), bl.backup_name(date(2026, 9, 24)), bl.backup_name(date(2026, 9, 23)),
        bl.backup_name(date(2026, 9, 3)),                                      # 최신 7개
        bl.backup_name(date(2026, 8, 20))]   # 9-02·9-01 은 9-03(일별)과 같은 주 → 지움
check('결번 있음 → 일별이 대표한 주는 건너뛰고 더 옛 주를 남김', kept == want, str(kept))
check('7개 이하면 아무것도 안 지움', bl.plan_prune(names[:7]) == [])
others = ['library.db.bak.20261011_231534', 'notes.txt', 'library-2026.db.gz', 'library-20261399.db.gz',
          'library-20260101.db', 'xlibrary-20260101.db.gz', 'library-20260101.db.gz.tmp']
check('형식 다른 이름은 절대 고르지 않음', set(bl.plan_prune(names + others)) & set(others) == set())

print('[9] 실제 정리 — 쓴 폴더에서만, 다른 파일 보존')
root, db = setup('prune')
os.makedirs(bl.LOCAL_DIR)
for n in names[1:30] + others:            # 어제부터 29일치 + 기타
    open(os.path.join(bl.LOCAL_DIR, n), 'wb').write(b'x')
code, out, rj = run()
left = sorted(os.listdir(bl.LOCAL_DIR))
check('exit 0', code == 0, out)
check('백업 11개만 남음', len(bl.list_backups(bl.LOCAL_DIR)) == 11, str(bl.list_backups(bl.LOCAL_DIR)))
check('오늘 파일 남음', NAME in left)
check('기타 파일 7개 그대로', all(o in left for o in others))
check('pruned.local = 19', rj and rj['pruned'].get('local') == 19, str(rj))

print('[10] --dry-run · --status')
root, db = setup('dry')
drive_parent = os.path.join(root, 'GoogleDrive', '내 드라이브')
os.makedirs(drive_parent)
ENV['LIBRARY_BACKUP_DIR'] = os.path.join(drive_parent, 'YouTube_Ledger_Backup')
code, out, rj = run('--dry-run')
check('dry-run exit 0', code == 0 and rj and rj.get('dry_run') is True, str(rj))
check('dry-run: 로컬 폴더도 안 만듦', not os.path.exists(bl.LOCAL_DIR))
check('dry-run: 드라이브 폴더도 안 만듦', not os.path.exists(ENV['LIBRARY_BACKUP_DIR']))
run()
TODAY[0] = date(2026, 10, 14)
code, out, rj = run('--status')
check('status: local 1개 · 2일 전', rj and rj['dests']['local']['count'] == 1 and rj['dests']['local']['age_days'] == 2, str(rj))
check('status: drive 1개', rj and rj['dests']['drive']['count'] == 1, str(rj))
check('status 는 아무것도 안 만듦', bl.list_backups(bl.LOCAL_DIR) == [NAME])

print('[11] 읽기 연결이 열려 있어도 백업된다 (스케줄러와 겹칠 때)')
root, db = setup('concurrent')
reader = sqlite3.connect(db)
reader.execute('BEGIN')
reader.execute('SELECT COUNT(*) FROM videos').fetchone()
code, out, rj = run()
reader.close()
check('exit 0', code == 0, out)

print()
n_pass = sum(results)
print(f'{n_pass}/{len(results)} PASS')
sys.exit(0 if n_pass == len(results) else 1)
