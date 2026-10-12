#!/usr/bin/env python3
"""
장부(data/library.db) 스키마 올리기 — v4.5 (1 → 2, wiki_extract 표) · v4.6 (2 → 3, videos.grade·quality·summarized_at 열)

  /opt/homebrew/bin/python3 scripts/migrate_library.py            # dry-run (기본): 현재·목표 버전, 새로 생길 표만 보고
  /opt/homebrew/bin/python3 scripts/migrate_library.py --apply    # 적용
  ... --db=<경로>                                                 # 다른 장부(복원본·테스트 사본)에 적용

--apply 순서:
  1) 장부가 없으면 만들지 않고 실패. user_version 이 목표면 "이미 최신"(exit 0). 1 미만이거나 목표보다 크면 거부(exit 1).
     v1 장부(10-12 이전 백업)도 한 번에 목표까지 올린다.
  2) SQLite 온라인 백업 API 로 <장부>.bak.v<현재>-<KST 시각> 사본 → integrity_check ok 확인 (이미 있으면 거부)
  3) 한 트랜잭션: 단계별 ALTER TABLE(ADD_COLUMNS) → lib/library_schema.sql 실행(CREATE ... IF NOT EXISTS 라 없는 표만 생기고
     user_version 이 오른다). 열 추가는 기존 행에 NULL 만 채운다 — updated_at 을 건드리지 않으므로 시트 미러가 다시 보내지 않는다
  4) 확인: user_version = 목표 · integrity_check ok · 기존 표 행 수 그대로 · 새 표·새 열 존재. 어긋나면 exit 1 (백업에서 되돌린다)
RESULT_JSON 한 줄. 옛 백업(v1)을 복원했을 때도 이것으로 올린다.
"""
import json, os, sqlite3, sys
from datetime import datetime, timezone, timedelta

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, 'lib'))
import library_db as ldb   # noqa: E402

KST = timezone(timedelta(hours=9))
OLD_TABLES = ('videos', 'videos_dup', 'tips', 'meta')
# 단계별 열 추가 — key 버전으로 올라갈 때 붙인다. lib/library_schema.sql 의 CREATE TABLE 과 같은 정의여야 한다.
ADD_COLUMNS = {
    3: [('videos', 'grade', 'TEXT'), ('videos', 'quality', 'TEXT'), ('videos', 'summarized_at', 'TEXT')],
}
NEW_TABLES = ('wiki_extract',)


def log(m=''):
    print(m, flush=True)


def emit(**kw):
    print('RESULT_JSON ' + json.dumps(kw, ensure_ascii=False), flush=True)


def tables(conn):
    return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def columns(conn, table):
    return {r[1] for r in conn.execute(f'PRAGMA table_info({table})')}


def missing_columns(conn, uv, target):
    out = []
    for ver in range(uv + 1, target + 1):
        for t, c, typ in ADD_COLUMNS.get(ver, []):
            if c not in columns(conn, t):
                out.append((t, c, typ))
    return out


def counts(conn):
    have = tables(conn)
    return {t: conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in OLD_TABLES if t in have}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    apply = '--apply' in argv
    db = ldb.DB_PATH
    for a in argv:
        if a.startswith('--db='):
            db = os.path.abspath(os.path.expanduser(a[5:]))
    target = ldb.SCHEMA_VERSION
    if not os.path.exists(db):
        log(f'❌ 장부 없음: {db} — 만들지 않는다')
        emit(ok=False, error='no_db', db=db)
        return 1
    conn = sqlite3.connect(f'file:{db}?mode=ro', uri=True)
    uv = conn.execute('PRAGMA user_version').fetchone()[0]
    before = counts(conn)
    missing = sorted(t for t in NEW_TABLES if t not in tables(conn))
    add_cols = missing_columns(conn, uv, target) if 1 <= uv < target else []
    conn.close()
    cols_s = [f'{t}.{c}' for t, c, _ in add_cols]
    log(f'장부 {db}\n  user_version {uv} → 목표 {target} · 새 표 {missing or "없음"} · 새 열 {cols_s or "없음"} · 행 수 {before}')
    if uv == target:
        log('✅ 이미 최신 — 할 일 없음')
        emit(ok=True, changed=False, user_version=uv, rows=before)
        return 0
    if not 1 <= uv < target:
        log(f'❌ user_version {uv} 은 이 스크립트가 올리는 범위(1~{target - 1} → {target})가 아니다')
        emit(ok=False, error=f'user_version:{uv}')
        return 1
    if not apply:
        log('  (dry-run — 쓰지 않음. 적용은 --apply)')
        emit(ok=True, changed=False, dry_run=True, user_version=uv, target=target, missing=missing, add_columns=cols_s, rows=before)
        return 0

    bak = f'{db}.bak.v{uv}-{datetime.now(KST):%Y%m%d-%H%M%S}'
    if os.path.exists(bak):
        log(f'❌ 백업 이름이 이미 있음: {bak}')
        emit(ok=False, error='backup_exists')
        return 1
    src = sqlite3.connect(f'file:{db}?mode=ro', uri=True)
    dst = sqlite3.connect(bak)
    src.backup(dst)
    src.close()
    ic = dst.execute('PRAGMA integrity_check').fetchone()[0]
    dst.close()
    if ic != 'ok':
        log(f'❌ 백업 사본 integrity_check {ic} — 적용 안 함')
        emit(ok=False, error='backup_integrity', backup=bak)
        return 1
    log(f'  백업 {bak} (integrity ok)')

    conn = ldb.open_db(db)
    try:
        # executescript 는 열린 트랜잭션을 먼저 커밋하므로, ALTER 와 스키마를 한 스크립트로 묶어 BEGIN … COMMIT 한다
        alters = ''.join(f'ALTER TABLE {t} ADD COLUMN {c} {typ};\n' for t, c, typ in add_cols)
        conn.executescript('BEGIN;\n' + alters + ldb.schema_sql() + '\nCOMMIT;')
    except Exception as e:
        try:
            conn.execute('ROLLBACK')
        except Exception:
            pass
        conn.close()
        log(f'❌ 적용 실패(되돌림): {e}')
        emit(ok=False, error=f'apply:{e}', backup=bak)
        return 1
    conn.close()

    conn = sqlite3.connect(f'file:{db}?mode=ro', uri=True)
    uv2 = conn.execute('PRAGMA user_version').fetchone()[0]
    ic2 = conn.execute('PRAGMA integrity_check').fetchone()[0]
    after = counts(conn)
    has_new = all(t in tables(conn) for t in NEW_TABLES)
    cols_ok = all(c in columns(conn, t) for ver in ADD_COLUMNS for t, c, _ in ADD_COLUMNS[ver] if ver <= target)
    conn.close()
    ok = (uv2 == target and ic2 == 'ok' and after == before and has_new and cols_ok)
    log(f'  결과 user_version {uv2} · integrity {ic2} · 행 수 {after} · 새 표 {"있음" if has_new else "없음"} · 새 열 {"있음" if cols_ok else "없음"}')
    log('✅ 적용 완료' if ok else f'❌ 확인 실패 — 백업 {bak} 에서 되돌릴 것')
    emit(ok=ok, changed=True, user_version=uv2, integrity=ic2, rows=after, rows_before=before, backup=bak)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
