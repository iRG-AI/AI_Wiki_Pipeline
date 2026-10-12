#!/usr/bin/env python3
"""
v4.0 로컬 원본 장부(data/library.db) 공용 헬퍼 — Python 쪽.
스키마 원본은 lib/library_schema.sql 하나다. Node 쪽(2단계)도 같은 파일을 node:sqlite 로 실행한다.
"""
import os, sqlite3

REPO_ROOT   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR    = os.path.join(REPO_ROOT, 'data')
DB_PATH     = os.path.join(DATA_DIR, 'library.db')
SCHEMA_PATH = os.path.join(REPO_ROOT, 'lib', 'library_schema.sql')
SCHEMA_VERSION = 3   # v4.6 videos.grade·quality·summarized_at (v4.5 = 2 wiki_extract) — lib/library_schema.sql 의 PRAGMA user_version 과 같이 올린다


def schema_sql():
    with open(SCHEMA_PATH, encoding='utf-8') as f:
        return f.read()


def open_db(path=DB_PATH, readonly=False):
    if readonly:
        conn = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
    else:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        conn = sqlite3.connect(path)
        # journal_mode 는 기본(DELETE) 그대로 둔다 (2단계 결정: 접근이 순차라 WAL 불필요, 겹치면 timeout 5초 대기).
    conn.row_factory = sqlite3.Row
    return conn


def apply_schema(conn):
    conn.executescript(schema_sql())


def open_existing(path=None, readonly=False):
    """v4.0 2단계 — 이미 있는 장부만 연다. 파일이 없으면 만들지 않고 FileNotFoundError, user_version 이 다르면 RuntimeError.
    빈 장부를 새로 만들면 모든 링크·영상이 신규로 보여 중복이 쌓인다(scheduler.js·lib/library.js 와 같은 원칙).
    sqlite3.connect 의 기본 timeout 5초 = busy_timeout 5초 (Node 쪽 lib/library.js 와 같은 값)."""
    path = path or DB_PATH
    if not os.path.exists(path):
        raise FileNotFoundError(f'장부 파일 없음: {path} — 원본 장부다. 새로 만들지 말고 백업(data/library.db.bak.*)에서 복원할 것')
    conn = open_db(path, readonly=readonly)
    uv = conn.execute('PRAGMA user_version').fetchone()[0]
    if uv != SCHEMA_VERSION:
        conn.close()
        raise RuntimeError(f'장부 user_version {uv} ≠ 스키마 {SCHEMA_VERSION}')
    return conn
