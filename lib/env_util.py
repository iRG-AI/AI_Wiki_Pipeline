#!/usr/bin/env python3
"""
레포 루트 .env 읽기 — 네트워크 없음, 의존성 없음 (v4.0 3단계).

kakao_ingest.py 가 노션 래퍼(lib/tips_notion.py)를 .env 읽기용으로만 import 하던 것을 대신한다.
형식: KEY=VALUE 한 줄씩. '#' 주석·빈 줄 무시. 값 양끝의 따옴표(" ')는 벗긴다 (tips_notion.load_env 와 같은 규칙).
"""
import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(REPO_ROOT, '.env')


def load_env(path=None):
    env = {}
    p = path or ENV_PATH
    if not os.path.exists(p):
        return env
    with open(p, encoding='utf-8') as f:
        for line in f.read().split('\n'):
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, _, v = line.partition('=')
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env
