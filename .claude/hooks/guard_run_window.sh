#!/usr/bin/env bash
# guard_run_window.sh — 정시 실행 창·실행 중에는 장부 쓰기·launchd 조작·코드 편집을 막는다.
# 등록: .claude/settings.json → hooks.PreToolUse (matcher Bash|Edit|Write|MultiEdit). 해당 없으면 즉시 통과(exit 0).
#   ① Bash: 장부·시트·Wiki 를 크게 쓰는 명령(--apply · --full 인자 · migrate_library · library.db 쓰기)·launchctl 조작
#           → 매시 분 50~59 · 00~20 이면 막음 (CLAUDE.md 「정시 실행 창」 매시 적용 규칙)
#   ② Edit/Write: 코드·plist(.js .py .sql .gs .sh .plist, .claude/·docs/ 제외)
#           → 정시 실행(00·06·12·18시) 전 10분 ~ 후 20분, wiki-ingest(17:25~17:50) 창이면 막음
#   ①② 공통: scheduler.js · wiki_ingest.py · sync_obsidian.py 가 돌고 있으면 막음
# 막을 때 exit 2 + stderr — Claude Code 가 그 문구를 워커에게 돌려준다.
set -u
input="$(cat)"
tool="$(printf '%s' "$input" | jq -r '.tool_name // ""' 2>/dev/null)"

now="${GUARD_NOW:-$(date +%H:%M)}"   # GUARD_NOW=HH:MM 은 시험용
H=$((10#${now%:*})); M=$((10#${now#*:}))

hourly_window() { [ "$M" -ge 50 ] || [ "$M" -le 20 ]; }
run_window() {
  case "$H" in 23|5|11|17) [ "$M" -ge 50 ] && return 0 ;; esac
  case "$H" in 0|6|12|18) [ "$M" -le 20 ] && return 0 ;; esac
  [ "$H" -eq 17 ] && [ "$M" -ge 25 ] && [ "$M" -le 50 ] && return 0
  return 1
}
# 실행 중 판정은 node·python 프로세스만 본다(명령 글자에 scheduler.js 가 든 셸·grep 을 실행으로 잘못 보지 않게)
running() {
  ps -axo ucomm=,args= 2>/dev/null | awk '{c=$1; sub(/.*\//,"",c)} (c=="node" || c ~ /^[Pp]ython/) && /scheduler\.js|wiki_ingest\.py|sync_obsidian\.py/ {f=1} END{exit !f}'
}
block() { echo "실행 창 보호: $1 — 지금 ${now}. $2 (guard_run_window.sh, CLAUDE.md 「정시 실행 창」)" >&2; exit 2; }

case "$tool" in
  Bash)
    cmd="$(printf '%s' "$input" | jq -r '.tool_input.command // ""' 2>/dev/null)"
    risky=0
    printf '%s' "$cmd" | grep -Eq -- 'launchctl[[:space:]]+(load|unload|bootstrap|bootout|kickstart|start|stop|enable|disable)' && risky=1
    # --apply·--full·migrate_library 는 실제 명령 글자일 때만 — heredoc 본문·따옴표 안 글자(문서 편집·커밋 메시지)는 빼고 본다 (11-04 오탐).
    # 셸로 넘기는 heredoc(bash <<…)은 실행되므로 본문을 남긴다.
    # ponytail: bash -c '… --apply' 처럼 따옴표 안에서 실행하는 꼴은 못 잡는다 — 이 레포 실행 관례(인터프리터 직접 호출)에 없음
    args="$cmd"
    printf '%s' "$cmd" | grep -Eq '(^|[^[:alnum:]_])(ba|z)?sh[[:space:]]+(-s[[:space:]]*)?<<' || \
      args="$(printf '%s' "$cmd" | perl -0pe 's/<<-?\s*([\x27"]?)(\w+)\1[^\n]*\n.*?\n[ \t]*\2[ \t]*(?=\n|\z)//sg')"
    args="$(printf '%s' "$args" | perl -0pe 's/"(?:\\.|[^"\\])*"|\x27[^\x27]*\x27//gs')"
    printf '%s' "$args" | grep -Eq -- '--apply|--full|migrate_library' && risky=1
    # sqlite3 로 장부를 여는데 읽기 전용(mode=ro)이 아니면 쓰기로 본다
    if printf '%s' "$cmd" | grep -Eq 'sqlite3[^|;&]*library\.db' && ! printf '%s' "$cmd" | grep -q 'mode=ro'; then risky=1; fi
    [ "$risky" -eq 1 ] || exit 0
    running && block "파이프라인 실행 중에 장부 쓰기·launchd 조작" "실행이 끝난 뒤(pgrep 로 확인) 다시 하십시오."
    hourly_window && block "매시 분 50~59 · 00~20 에는 장부 쓰기·launchd 조작을 하지 않습니다" "분 21 이후에 다시 하십시오."
    ;;
  Edit|Write|MultiEdit)
    path="$(printf '%s' "$input" | jq -r '.tool_input.file_path // .tool_input.path // ""' 2>/dev/null)"
    case "$path" in */.claude/*|*/docs/*) exit 0 ;; esac
    case "$path" in *.js|*.py|*.sql|*.gs|*.sh|*.plist) ;; *) exit 0 ;; esac
    running && block "파이프라인 실행 중에 코드·plist 편집" "실행이 끝난 뒤 다시 하십시오(실행 중 바뀐 코드를 하위 단계가 반쯤 읽을 수 있음)."
    run_window && block "정시 실행(00·06·12·18시 앞 10분·뒤 20분)·wiki-ingest(17:25~17:50) 창에는 코드·plist 를 고치지 않습니다" "창이 끝난 뒤 다시 하십시오."
    ;;
esac
exit 0
