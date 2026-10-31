#!/usr/bin/env bash
# run_all_tests.sh — 회귀 테스트 15종을 한 번에 돌린다 (2026-10-31~).
#   네트워크 0회 · 실제 장부·Vault·.env 무관 (각 테스트가 임시 폴더·가짜 요청을 쓴다). 데몬과 같은 인터프리터.
#   사용: scripts/run_all_tests.sh [all|js|py]    기본 all. 하나라도 실패하면 exit 1.
#   마지막 줄: RESULT: <통과>/<전체> 통과
set -u
cd "$(dirname "$0")/.." || exit 1
NODE=/opt/homebrew/bin/node
PY=/opt/homebrew/bin/python3
JS_TESTS="test_scheduler_guards test_video_summary test_classifier test_resummarize test_wiki_search"
PY_TESTS="test_verify_library test_retitle_tips test_wiki_ingest test_kakao_ingest test_title_fetch test_recategorize_tips test_sync_obsidian test_sheet_mirror test_build_wiki_index test_backup_library"

mode="${1:-all}"
case "$mode" in all|js|py) ;; *) echo "사용: $0 [all|js|py]" >&2; exit 2 ;; esac

n=0; ok=0
run_one() {  # $1 = 이름, 나머지 = 명령
  name="$1"; shift
  n=$((n + 1))
  out="$("$@" 2>&1)"; rc=$?
  last="$(printf '%s\n' "$out" | grep -v '^[[:space:]]*$' | tail -1)"
  if [ "$rc" -eq 0 ]; then
    ok=$((ok + 1)); printf '  ✅ %-24s %s\n' "$name" "$last"
  else
    printf '  ❌ %-24s rc=%s  %s\n' "$name" "$rc" "$last"
    printf '%s\n' "$out" | tail -15 | sed 's/^/        /'
  fi
}

echo "회귀 테스트 ($mode) — node $($NODE -v 2>/dev/null) · $($PY -V 2>&1)"
if [ "$mode" != "py" ]; then for t in $JS_TESTS; do run_one "$t" "$NODE" "scripts/$t.js"; done; fi
if [ "$mode" != "js" ]; then for t in $PY_TESTS; do run_one "$t" "$PY" "scripts/$t.py"; done; fi
echo "RESULT: ${ok}/${n} 통과"
[ "$ok" -eq "$n" ]
