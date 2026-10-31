#!/usr/bin/env bash
# pm-wiki.sh — AI_Wiki_Pipeline 의 실행 PM 세션(pm-wiki)을 띄운다. (2026-10-31~)
#   사용:  ./pm-wiki.sh          터미널에서
#          ./pm-wiki.sh --rc     Remote Control 켬 — 폰·데스크톱 앱에서도 이어서
# 하는 일: 레포로 이동 → XP 보드 폴더를 작업 폴더로 추가 → PM 역할 지침(.claude/pm/PM_ROLE.md)을
#          시스템 프롬프트에 덧붙여 Opus 로 시작. 워커는 .claude/agents/ 의 서브에이전트.
# 경로는 스크립트 위치와 $HOME 기준이다(공개 레포 — 개인 절대경로를 쓰지 않는다). macOS bash 3.2 호환.
set -euo pipefail
REPO="$(cd "$(dirname "$0")" && pwd -P)"
XP="$HOME/Documents/Claude/XP"
cd "$REPO"
mkdir -p "$XP/open" "$XP/done"

ARGS=(--name pm-wiki --model opus --append-system-prompt-file .claude/pm/PM_ROLE.md --add-dir "$XP")
if [ "${1:-}" = "--rc" ]; then
  exec claude "${ARGS[@]}" --remote-control pm-wiki
else
  exec claude "${ARGS[@]}"
fi
