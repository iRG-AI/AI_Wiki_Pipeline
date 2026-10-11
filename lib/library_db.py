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
SCHEMA_VERSION = 1


def schema_sql():
    with open(SCHEMA_PATH, encoding='utf-8') as f:
        return f.read()


def open_db(path=DB_PATH, readonly=False):
    if readonly:
        conn = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
    else:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        conn = sqlite3.connect(path)
        # journal_mode 는 기본(DELETE) 그대로 둔다. WAL 전환 여부는 동시 쓰기가 생기는 2단계에서 정한다.
    conn.row_factory = sqlite3.Row
    return conn


def apply_schema(conn):
    conn.executescript(schema_sql())
