#!/usr/bin/env python3
"""
v4.1 — 장부(data/library.db) 하루 1회 백업. 로컬 data/backups/ + 구글 드라이브 폴더(선택)

    /opt/homebrew/bin/python3 backup_library.py            # 오늘(KST) 백업이 없는 곳에만 만든다 (스케줄러가 매 실행 끝에 부른다 → 실제로는 하루 1회)
    /opt/homebrew/bin/python3 backup_library.py --dry-run  # 만들 곳·지울 파일만 출력. 장부·백업 폴더 쓰기 0
    /opt/homebrew/bin/python3 backup_library.py --status   # 두 곳의 백업 목록·가장 최근 백업 날짜 (읽기만)
    /opt/homebrew/bin/python3 backup_library.py --force    # 오늘 백업이 있어도 다시 만든다 (같은 이름 덮어쓰기)

.env: LIBRARY_BACKUP_DIR = 드라이브 쪽 백업 폴더 (구글 드라이브 데스크톱 앱이 동기화하는 폴더 안).
      없으면 로컬에만 만든다. 이 폴더의 **부모가 없으면**(드라이브 앱 꺼짐·로그아웃) 만들지 않고 drive: unavailable 로 실패 처리한다
      — 드라이브 경로 아래에 엉뚱한 로컬 폴더를 새로 만들지 않기 위해서다.

만드는 법:
  1) SQLite 온라인 백업 API 로 임시 사본을 뜬다 (장부는 journal_mode=DELETE 라 파일을 그냥 복사하면 쓰는 도중의 상태가 찍힐 수 있다).
     장부는 읽기 전용(mode=ro)으로만 연다 — 이 스크립트는 장부에 아무것도 쓰지 않는다.
  2) 사본 검사: PRAGMA integrity_check = ok · user_version = 스키마 버전 · videos 1건 이상. 하나라도 어긋나면 만들지 않는다(기존 백업도 지우지 않는다).
  3) gzip(약 16MB → 4MB) → 압축을 다시 풀어 sha256 이 사본과 같은지 확인 → 각 폴더에 .tmp 로 쓰고 이름 바꾸기(반쯤 쓴 파일이 백업 이름을 갖지 않게).
  4) 쓴 폴더에서만 보관 규칙 적용: 최신 7개(일별) + 일별이 대표하지 않는 옛 ISO 주마다 가장 최근 1개(보통 일요일)씩 4주(주별) = 최대 11개.
     이름이 정확히 library-YYYYMMDD.db.gz 인 파일만 센다·지운다. 그 밖의 파일(손으로 둔 .bak 등)은 건드리지 않는다.

파일 이름의 날짜 = KST 오늘. 오늘 이름이 이미 있으면 그 폴더는 건너뛴다 → 00시 실행이 만들고 06·12·18시는 skipped.
드라이브만 실패했으면 다음 실행이 드라이브에만 다시 시도한다.

마지막 줄은 RESULT_JSON:{...} (scheduler.js:runLibraryBackup 이 파싱). exit 0 = 성공 또는 skipped, exit 1 = 실패(어느 한 곳이라도).
"""
import gzip, hashlib, json, os, re, shutil, sqlite3, sys
from datetime import date, datetime, timedelta, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR, 'lib'))
import library_db as ldb          # noqa: E402
from env_util import load_env     # noqa: E402

KST = timezone(timedelta(hours=9))
DB_PATH = ldb.DB_PATH
LOCAL_DIR = os.path.join(ldb.DATA_DIR, 'backups')
NAME_RE = re.compile(r'^library-(\d{8})\.db\.gz$')
KEEP_DAILY = 7
KEEP_WEEKLY = 4
TABLES = ('videos', 'videos_dup', 'tips', 'meta')


def log(m=''):
    print(m, flush=True)


def emit(**kw):
    print('RESULT_JSON:' + json.dumps(kw, ensure_ascii=False), flush=True)


def today_kst():
    return datetime.now(KST).date()


def backup_name(d):
    return f'library-{d:%Y%m%d}.db.gz'


def _date_of(name):
    m = NAME_RE.match(name)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1), '%Y%m%d').date()
    except ValueError:
        return None


def plan_prune(names, keep_daily=KEEP_DAILY, keep_weekly=KEEP_WEEKLY):
    """지울 이름 목록. 백업 이름 형식이 아닌 것은 절대 고르지 않는다."""
    dated = sorted(((d, n) for n in names if (d := _date_of(n))), reverse=True)
    keep = {n for _, n in dated[:keep_daily]}
    seen = {tuple(d.isocalendar())[:2] for d, _ in dated[:keep_daily]}   # 일별이 이미 대표하는 주는 주별로 또 세지 않는다
    weekly = 0
    for d, n in dated[keep_daily:]:
        wk = tuple(d.isocalendar())[:2]
        if wk in seen:
            continue
        if weekly >= keep_weekly:
            break
        seen.add(wk)
        weekly += 1
        keep.add(n)          # 내림차순이라 그 주에서 처음 만나는 것 = 가장 최근(보통 일요일)
    return [n for _, n in dated if n not in keep]


def list_backups(folder):
    try:
        return sorted(n for n in os.listdir(folder) if _date_of(n))
    except FileNotFoundError:
        return []


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def sha256_gz(path):
    h = hashlib.sha256()
    with gzip.open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def destinations(env):
    """[(라벨, 폴더 | None, 상태 | None)] — 상태가 있으면 쓸 수 없는 곳"""
    dests = [('local', LOCAL_DIR, None)]
    drive = os.path.expanduser((env.get('LIBRARY_BACKUP_DIR') or '').strip())
    if not drive:
        dests.append(('drive', None, 'not_configured'))
    elif not os.path.isdir(os.path.dirname(os.path.normpath(drive))):
        dests.append(('drive', drive, 'unavailable'))
    else:
        dests.append(('drive', drive, None))
    return dests


def snapshot(db_path, out_path):
    """온라인 백업 API 로 사본을 뜨고 검사한다. 행 수 dict 를 돌려준다. 어긋나면 RuntimeError."""
    if not os.path.exists(db_path):
        raise RuntimeError('no_db')
    src = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True, timeout=5)
    try:
        dst = sqlite3.connect(out_path)
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()
    conn = sqlite3.connect(f'file:{out_path}?mode=ro', uri=True)
    try:
        ic = conn.execute('PRAGMA integrity_check').fetchone()[0]
        if ic != 'ok':
            raise RuntimeError('integrity:' + str(ic)[:80])
        uv = conn.execute('PRAGMA user_version').fetchone()[0]
        if uv != ldb.SCHEMA_VERSION:
            raise RuntimeError(f'user_version:{uv}')
        rows = {t: conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in TABLES}
    finally:
        conn.close()
    if rows['videos'] < 1:
        raise RuntimeError('empty_ledger')
    return rows


def write_into(folder, name, gz_path, expect_size):
    os.makedirs(folder, exist_ok=True)
    final = os.path.join(folder, name)
    tmp = final + '.tmp'
    shutil.copyfile(gz_path, tmp)
    if os.path.getsize(tmp) != expect_size:
        os.remove(tmp)
        raise RuntimeError('size_mismatch')
    os.replace(tmp, final)


def prune(folder, dry_run=False):
    victims = plan_prune(list_backups(folder))
    for n in victims:
        if not dry_run:
            os.remove(os.path.join(folder, n))
    return victims


def cmd_status(dests, today):
    out = {}
    for label, folder, state in dests:
        if state == 'not_configured':
            log(f'  {label}: 설정 없음 (.env LIBRARY_BACKUP_DIR)')
            out[label] = {'state': state}
            continue
        names = list_backups(folder) if folder else []
        latest = names[-1] if names else None
        age = (today - _date_of(latest)).days if latest else None
        size = sum(os.path.getsize(os.path.join(folder, n)) for n in names) if names else 0
        flag = '' if state is None else f' ⚠️ {state}'
        log(f'  {label}: {len(names)}개 · {size / 1048576:.1f}MB · 최근 {latest or "없음"}'
            + (f' ({age}일 전)' if age is not None else '') + flag)
        out[label] = {'state': state or 'ok', 'count': len(names), 'latest': latest, 'age_days': age, 'bytes': size}
    emit(status=True, dests=out, error='')
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    dry_run, force, status = '--dry-run' in argv, '--force' in argv, '--status' in argv
    env = load_env()
    today = today_kst()
    name = backup_name(today)
    dests = destinations(env)

    if status:
        return cmd_status(dests, today)

    result = {d[0]: (d[2] or ('exists' if os.path.exists(os.path.join(d[1], name)) and not force else 'todo'))
              for d in dests}
    todo = [(label, folder) for label, folder, _ in dests if result[label] == 'todo']
    if not todo:
        failed = [k for k, v in result.items() if v == 'unavailable']
        log(f'ℹ️  오늘 백업 있음 ({name})' + (f' · 쓸 수 없는 곳: {", ".join(failed)}' if failed else ''))
        if failed:
            emit(file=name, dests=result, pruned={}, error='drive_unavailable')
            return 1
        emit(skipped='already_done', file=name, dests=result, error='')
        return 0

    if dry_run:
        for label, folder in todo:
            victims = plan_prune(list_backups(folder) + [name])
            log(f'  [dry-run] {label}: {os.path.join(folder, name)} 만들 예정 · 지울 것 {len(victims)}개 {victims}')
        emit(dry_run=True, file=name, dests=result, error='')
        return 0

    os.makedirs(LOCAL_DIR, exist_ok=True)
    raw = os.path.join(LOCAL_DIR, f'.snap-{os.getpid()}.db')
    gz = os.path.join(LOCAL_DIR, f'.snap-{os.getpid()}.db.gz')
    pruned = {}
    try:
        try:
            rows = snapshot(DB_PATH, raw)
        except (RuntimeError, sqlite3.Error) as e:
            log(f'❌ 사본 검사 실패: {e} — 백업을 만들지 않고 기존 백업도 지우지 않는다')
            emit(file=name, dests=result, pruned={}, error=f'snapshot:{e}')
            return 1
        digest = sha256_file(raw)
        with open(raw, 'rb') as fi, gzip.open(gz, 'wb', compresslevel=6) as fo:
            shutil.copyfileobj(fi, fo, 1 << 20)
        if sha256_gz(gz) != digest:
            log('❌ 압축 검증 실패 (sha256 불일치)')
            emit(file=name, dests=result, pruned={}, error='gzip_verify')
            return 1
        size = os.path.getsize(gz)

        for label, folder in todo:
            try:
                write_into(folder, name, gz, size)
                result[label] = 'ok'
                pruned[label] = len(prune(folder))
            except (OSError, RuntimeError) as e:     # 드라이브 앱이 중간에 빠지는 경우 등. 다른 곳은 계속 쓴다
                result[label] = 'error'
                log(f'⚠️ {label} 쓰기 실패: {e}')

        bad = [k for k, v in result.items() if v in ('error', 'unavailable')]
        log(f'🗄  {name} {size / 1048576:.1f}MB · 영상 {rows["videos"]:,} · 꿀팁 {rows["tips"]:,} · '
            + ' · '.join(f'{k} {v}' for k, v in result.items())
            + (' · 정리 ' + ', '.join(f'{k} {v}개' for k, v in pruned.items()) if pruned else ''))
        emit(file=name, bytes=size, sha256=digest, rows=rows, dests=result, pruned=pruned,
             error=(','.join(f'{k}_{result[k]}' for k in bad) if bad else ''))
        return 1 if bad else 0
    finally:
        for p in (raw, gz):
            try:
                os.remove(p)
            except FileNotFoundError:
                pass


if __name__ == '__main__':
    sys.exit(main())
