#!/usr/bin/env bash
# gate_subagent_stop.sh — implementer(이름 모르는 워커 포함)가 멈추기 직전에 "커밋 전 체크리스트"를 기계적으로 검사한다.
# 미통과면 exit 2 → Claude Code 가 워커를 멈추지 못하게 하고 stderr 를 피드백으로 넘긴다.
# 차단 횟수는 워커(agent_id)별로 센다. 같은 워커를 3번 막으면 통과시키되(무한 루프 방지) 카운터를 지우고
# /tmp/cc-gate-AI_Wiki_Pipeline-<세션>.log 에 PASS-THROUGH 를 남긴다 — verifier 가 그 로그로 대조한다.
# 등록: .claude/settings.json → hooks.SubagentStop (timeout 900). 의존: git, jq, scripts/run_all_tests.sh
# 이력: 2026-10-31 v1 — iRichGreen_ERP gate v3 를 이 레포 규칙(공개 레포·회귀 15종·plist)으로 옮김
# 2026-11-04 — README·docs/changelog 변경이면 이력 구조 검사(v4.19.2)
# 2026-11-01 — 로그·기준점·카운터 경로에 프로젝트 이름(다른 프로젝트 세션 로그 오독 방지, pm-cnc 알림)

set -u
input="$(cat)"
agent="$(printf '%s' "$input" | jq -r '.agent_type // .agent_name // .subagent_type // ""' 2>/dev/null)"
aid="$(printf '%s' "$input" | jq -r '.agent_id // ""' 2>/dev/null)"
sid="$(printf '%s' "$input" | jq -r '.session_id // "nosid"' 2>/dev/null)"
aid="${aid:-main}"; sid="${sid:-nosid}"
now="$(date '+%Y-%m-%d %H:%M:%S')"
gate_log="/tmp/cc-gate-AI_Wiki_Pipeline-${sid}.log"

# 읽기 전용 워커는 통과. 이름을 모르면(빈 값) 보수적으로 검사한다.
case "$agent" in verifier|investigator|Explore|Plan) exit 0 ;; esac

root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$root" || exit 0

count_file="/tmp/cc-gate-AI_Wiki_Pipeline-${sid}-${aid}.count"
count="$(cat "$count_file" 2>/dev/null || echo 0)"
if [ "$count" -ge 3 ]; then
  rm -f "$count_file" 2>/dev/null
  echo "[$now] agent=$aid($agent) PASS-THROUGH: 3회 차단 뒤 강제 통과 (카운터 리셋). PM 이 verifier 로 직접 확인할 것" >> "$gate_log"
  echo "검증 게이트: 이 워커를 이미 3회 막았으므로 통과시킵니다. PM 이 verifier 로 직접 확인하십시오. (로그: $gate_log)" >&2
  exit 0
fi

# 바뀐 파일 = (워커 시작 시점 HEAD 이후 커밋된 파일) + (작업 트리의 미커밋·untracked 파일, gitignore 제외)
base="$(cat "/tmp/cc-gate-AI_Wiki_Pipeline-${sid}.base" 2>/dev/null || echo HEAD)"
changed="$( { git diff --name-only "$base" HEAD 2>/dev/null; git diff --name-only 2>/dev/null; git diff --name-only --cached 2>/dev/null; git ls-files --others --exclude-standard 2>/dev/null; } | sort -u )"
[ -z "$changed" ] && exit 0

# 추가된 줄 = 기준점 이후 diff 의 + 줄(plist 제외) + untracked 새 파일 전체(plist 제외)
added="$(git diff "$base" -- . ':(exclude)*.plist' 2>/dev/null | grep -E '^\+' | grep -vE '^\+\+\+ ' ;
         git ls-files --others --exclude-standard 2>/dev/null | grep -v '\.plist$' | while IFS= read -r f; do [ -f "$f" ] && sed 's/^/+/' "$f"; done)"

fail=""

# 1. 공개 레포: 개인 절대경로 (plist 원본은 설치본과 같아야 해서 제외)
if printf '%s\n' "$added" | grep -Eq '/Us''ers/[A-Za-z0-9._-]+'; then
  fail="${fail}- 추가된 줄에 개인 절대경로(/Us""ers/…)가 있습니다. <REPO_ROOT>/… 또는 ~/… 표기로 바꾸십시오.\n"
fi

# 2. 공개 레포: 맥 이름 (값을 하드코딩하지 않는다 — 실행 시점에 읽는다)
host="$(scutil --get LocalHostName 2>/dev/null || true)"
if [ -n "$host" ] && printf '%s\n' "$added" | grep -Fqi "$host"; then
  fail="${fail}- 추가된 줄에 이 맥의 이름(LocalHostName)이 있습니다. <맥이름> 으로 바꾸십시오.\n"
fi

# 3. 공개 레포: .env 의 비밀·개인 값 (키 이름만 알린다 — 값은 출력하지 않는다)
if [ -f .env ]; then
  while IFS= read -r line; do
    case "$line" in ''|\#*) continue ;; esac
    key="${line%%=*}"; val="${line#*=}"
    printf '%s' "$key" | grep -Eq '(KEY|KEYS|TOKEN|SECRET|PASS|CIDR|_ID|_URL|EMAIL)' || continue
    val="${val%\"}"; val="${val#\"}"; val="${val%\'}"; val="${val#\'}"
    old_ifs="$IFS"; IFS=','
    for v in $val; do
      v="$(printf '%s' "$v" | tr -d '[:space:]')"
      [ "${#v}" -ge 8 ] || continue
      if printf '%s\n' "$added" | grep -Fq -- "$v"; then fail="${fail}- 추가된 줄에 .env 의 ${key} 값이 있습니다. 지우십시오(지시서·문서에는 키 이름만).\n"; break; fi
    done
    IFS="$old_ifs"
  done < .env
fi

# 4. 장부·상태 파일이 git 에 들어가면 안 된다
for f in data/library.db .env .run_state.json .video_quota.json .quota_state.json .wiki_state.json; do
  git check-ignore -q "$f" 2>/dev/null || fail="${fail}- ${f} 가 gitignore 대상이 아닙니다. .gitignore 를 되돌리십시오.\n"
done
if [ -n "$(git ls-files data/ 2>/dev/null)" ]; then fail="${fail}- data/ 아래 파일이 git 에 추적되고 있습니다(장부·백업). git rm --cached 하십시오.\n"; fi

# 5. README.html 금지 (v3.0 폐지)
[ -f README.html ] && fail="${fail}- README.html 이 생겼습니다. 삭제하십시오(문서는 README.md 하나).\n"

# 6. plist 를 건드렸으면 문법 검사
for f in $(printf '%s\n' "$changed" | grep '\.plist$'); do
  [ -f "$f" ] && ! plutil -lint "$f" >/dev/null 2>&1 && fail="${fail}- ${f} plutil -lint 실패.\n"
done

# 7. 셸 스크립트를 건드렸으면 문법 검사
for f in $(printf '%s\n' "$changed" | grep '\.sh$'); do
  [ -f "$f" ] && ! bash -n "$f" 2>/dev/null && fail="${fail}- ${f} bash -n 실패(문법 오류).\n"
done

# 8. 코드를 건드렸으면 회귀 테스트 15종 (1분 안쪽 — 네트워크 0, 실제 장부·Vault 무관)
if printf '%s\n' "$changed" | grep -Eq '\.(js|py|sql|gs)$' && [ -x scripts/run_all_tests.sh ]; then
  tlog="/tmp/cc-gate-AI_Wiki_Pipeline-${sid}-tests.log"
  if ! scripts/run_all_tests.sh all >"$tlog" 2>&1; then
    fail="${fail}- scripts/run_all_tests.sh 실패. 끝부분:\n$(tail -n 25 "$tlog" 2>/dev/null)\n(전체: ${tlog})\n"
  fi
elif printf '%s\n' "$changed" | grep -Eq '^README\.md$|^docs/changelog/'; then
  # 8-b. README·docs/changelog 만 바꿨으면 이력 구조 검사만 (1초 안쪽, v4.19.2)
  dlog="/tmp/cc-gate-AI_Wiki_Pipeline-${sid}-docs.log"
  if ! /opt/homebrew/bin/python3 scripts/test_readme_changelog.py >"$dlog" 2>&1; then
    fail="${fail}- scripts/test_readme_changelog.py 실패(README 요약표·docs/changelog 구조). 끝부분:\n$(tail -n 15 "$dlog" 2>/dev/null)\n"
  fi
fi

if [ -n "$fail" ]; then
  next=$((count + 1)); echo "$next" > "$count_file"
  { echo "[$now] agent=$aid($agent) BLOCK $next/3"; printf '%b' "$fail" | sed 's/^/    /'; } >> "$gate_log"
  printf '검증 게이트 미통과 — 아래를 고친 뒤 다시 끝내십시오 (차단 %d/3, 로그 %s):\n%b' "$next" "$gate_log" "$fail" >&2
  exit 2
fi
rm -f "$count_file" 2>/dev/null
exit 0
