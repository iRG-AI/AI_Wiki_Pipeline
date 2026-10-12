#!/usr/bin/env python3
"""
장부(data/library.db) 스키마 올리기 — v4.5 (user_version 1 → 2, wiki_extract 표 추가)

  /opt/homebrew/bin/python3 scripts/migrate_library.py            # dry-run (기본): 현재·목표 버전, 새로 생길 표만 보고
  /opt/homebrew/bin/python3 scripts/migrate_library.py --apply    # 적용
  ... --db=<경로>                                                 # 다른 장부(복원본·테스트 사본)에 적용

--apply 순서:
  1) 장부가 없으면 만들지 않고 실패. user_version 이 목표면 "이미 최신"(exit 0). 목표-1 이 아니면 거부(exit 1).
  2) SQLite 온라인 백업 API 로 <장부>.bak.v<현재>-<KST 시각> 사본 → integrity_check ok 확인 (이미 있으면 거부)
  3) lib/library_schema.sql 실행 — 전부 CREATE ... IF NOT EXISTS 라 기존 표·행은 그대로, 없는 표만 생기고 user_version 이 오른다
  4) 확인: user_version = 목표 · integrity_check ok · 기존 표 행 수 그대로 · 새 표 존재. 어긋나면 exit 1 (백업에서 되돌린다)
RESULT_JSON 한 줄. 옛 백업(v1)을 복원했을 때도 이것으로 올린다.
"""
import json, os, sqlite3, sys
from datetime import datetime, timezone, timedelta

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, 'lib'))
import library_db as ldb   # noqa: E402

KST = timezone(timedelta(hours=9))
OLD_TABLES = ('videos', 'videos_dup', 'tips', 'meta')


def log(m=''):
    print(m, flush=True)


def emit(**kw):
    print('RESULT_JSON ' + json.dumps(kw, ensure_ascii=False), flush=True)


def tables(conn):
    return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}


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
    missing = sorted(t for t in ('wiki_extract',) if t not in tables(conn))
    conn.close()
    log(f'장부 {db}\n  user_version {uv} → 목표 {target} · 새 표 {missing or "없음"} · 행 수 {before}')
    if uv == target:
        log('✅ 이미 최신 — 할 일 없음')
        emit(ok=True, changed=False, user_version=uv, rows=before)
        return 0
    if uv != target - 1:
        log(f'❌ user_version {uv} 은 이 스크립트가 올리는 범위({target - 1} → {target})가 아니다')
        emit(ok=False, error=f'user_version:{uv}')
        return 1
    if not apply:
        log('  (dry-run — 쓰지 않음. 적용은 --apply)')
        emit(ok=True, changed=False, dry_run=True, user_version=uv, target=target, missing=missing, rows=before)
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
    ldb.apply_schema(conn)
    conn.close()

    conn = sqlite3.connect(f'file:{db}?mode=ro', uri=True)
    uv2 = conn.execute('PRAGMA user_version').fetchone()[0]
    ic2 = conn.execute('PRAGMA integrity_check').fetchone()[0]
    after = counts(conn)
    has_new = 'wiki_extract' in tables(conn)
    conn.close()
    ok = (uv2 == target and ic2 == 'ok' and after == before and has_new)
    log(f'  결과 user_version {uv2} · integrity {ic2} · 행 수 {after} · wiki_extract {"있음" if has_new else "없음"}')
    log('✅ 적용 완료' if ok else f'❌ 확인 실패 — 백업 {bak} 에서 되돌릴 것')
    emit(ok=ok, changed=True, user_version=uv2, integrity=ic2, rows=after, rows_before=before, backup=bak)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
