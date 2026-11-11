# 외부 도구 — agy-run · Codex 리뷰 · 실패 대응 (asset_manage 에서 이식 — 2026-11-11)

> agy-run 이나 Codex 리뷰를 부르기 전, 외부 도구가 실패했을 때 읽는다.
> asset_manage `.claude/pm/ref/tools.md`(2026-11-10 대표님 승인 규칙)를 이 저장소에 맞춰 옮겼다. PM_ROLE 본문과 어긋나면 **PM_ROLE 이 우선**한다.

- **넓은 읽기는 Antigravity 먼저**: 구조 파악 · 파일 여러 개 훑기 · 외부 문서 조사는 `~/Documents/mac-health/agy-run "<질문>. 파일은 읽기만 하고 수정 · 생성하지 말 것. 40줄 이내."` 로 맡긴다(Gemini · Claude 토큰 0 · 1회 약 1분). agy-run 은 `agy -p --mode plan --sandbox --model gemini-4-argon-medium` 을 감싸 실패 시 gemini-3.8-flash-medium 으로 1회 재시도하고 호출마다 사용량을 기록한다. 원인 해석 · 판정 · 계획서 초안처럼 판단이 필요한 일만 investigator(Opus)에게 준다. agy 요약을 사실로 쓰기 전에 파일:줄 1 ~ 2곳을 직접 대조한다.
- **Codex 리뷰 먼저**: verifier 를 부르기 전에 `node ~/.claude/plugins/cache/openai-codex/codex/1.0.6/scripts/codex-companion.mjs review --wait --base <작업 전 HEAD> --scope branch > /tmp/codex-review-<지시서번호>.txt 2>&1` 를 직접 실행한다(Claude 토큰 0 · 약 2분 · Bash 시간 제한 5분). 출력은 파일로 받고 결론만 읽어 3줄로 verifier 호출 메시지에 붙인다. 코드 결함은 Codex, 범위 · 기준표 · 게이트는 verifier 가 본다.
  - verifier 는 **Opus 를 유지한다**. 이 저장소에서 Codex 와 verifier 판정을 3건 나란히 비교한 뒤 Sonnet 전환을 대표님께 다시 묻는다(asset_manage 는 3건 비교 뒤 Sonnet 으로 내렸다).
- **외부 도구 실패 · 한도 대응**: 성공 · 실패는 오류 문구가 아니라 **종료 코드와 빈 결과**로 판단한다. 처음 보는 오류 문구는 이 문서가 정한 인수인계 파일에 한 줄 남긴다.
  - Codex 리뷰 실패(종료 코드 ≠ 0 · 결론 없음) → 다시 돌리지 않고 verifier 단독 검수로 간다. verifier 가 Sonnet 으로 내려가 있으면 그 건만 Opus 로 부른다.
  - agy-run 최종 실패(종료 코드 1 = flash 재시도까지 실패) → investigator 에 맡기거나, 파일 1 ~ 2개만 좁게 직접 읽는다. 넓게 직접 읽지 않는다.
  - Codex 출력이나 `/status` 에 한도 80% 이상 · 한도 경고가 보이면 큰 리뷰(파일 10개 이상 · 여러 커밋)는 미루고 verifier 로 검수한다. 작은 리뷰는 계속 Codex 로 한다.
