#!/usr/bin/env bash
# record_base.sh — 서브에이전트가 시작될 때 HEAD 를 기록해 둔다(세션당 첫 워커 때 한 번).
# gate_subagent_stop.sh 가 "워커가 시작한 뒤 바뀐 파일"(커밋했든 안 했든)을 계산하는 기준점.
# 등록: .claude/settings.json → hooks.SubagentStart. (iRichGreen_ERP 의 같은 훅을 옮겨 왔다)
set -u
input="$(cat)"
sid="$(printf '%s' "$input" | jq -r '.session_id // "nosid"' 2>/dev/null)"
sid="${sid:-nosid}"
root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$root" || exit 0
base_file="/tmp/cc-gate-AI_Wiki_Pipeline-${sid}.base"
[ -f "$base_file" ] || git rev-parse HEAD > "$base_file" 2>/dev/null
exit 0
