#!/usr/bin/env bash
# after_compact.sh — 자동·수동 압축 직후 PM 에게 지침과 인수인계를 다시 읽게 한다.
# 등록: .claude/settings.json → hooks.SessionStart(matcher: compact) · autoCompactWindow 20만과 짝.
# 2026-11-11 대표님 승인 — asset_manage(2026-11-10 시범) 방식 이식.
set -u
cat >/dev/null
D="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
echo "[압축 후 재개] 방금 문맥이 자동 압축됐다. 이어서 하기 전에:"
echo "1. .claude/pm/PM_ROLE.md 를 다시 읽는다."
echo "2. .claude/pm/local/HANDOFF.md 는 「현재 상태」 · 「다음 순서」 · 「알아 둔 것」 절만 읽는다. 전문을 읽지 않는다."
echo "3. 압축 요약과 인수인계가 다르면 요약(더 최신)을 따르고, 다른 점을 첫 보고에 적는다."
echo "4. 첫 보고 맨 앞에 「[압축 후 재개]」 를 적고, 압축 전 하던 일을 이어서 한다. 대표님께 새 세션을 요청하지 않는다."
