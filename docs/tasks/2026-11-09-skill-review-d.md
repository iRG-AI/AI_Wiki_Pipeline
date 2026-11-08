# [CC-1109-D] 매일 Wiki 검토 보완 — 투자 분야 · 하루 상한 5건 · 지난 자료 훑기(`--backfill`)

- 작성: pm-wiki · 2026-11-09 · 승인: 대표님 11-09 「투자 스킬도 포함 · 최근 1개월 · 매일 상한 5건」
- 실행: implementer · 검수: verifier · 실제 backfill 실행·커밋·push 는 PM
- 앞 단계: v4.20.0(`914d658`, push 전). 프로필 `data/review_profile.md` 에 5번 「투자·자산관리」는 PM 이 이미 넣었다.

## 원인 (왜 투자 제안이 빠졌나)
`SCHEMA` 의 `area` 가 `dev·work·knowledge·content` 4개뿐이고 프로필에도 투자가 없었다 → 시험 실행 note 「투자·주식 스킬(일반론이거나 판매)」.

## 범위

| 파일 | 할 일 |
|---|---|
| `skill_review.py` | 아래 1~3 |
| `scripts/test_skill_review.py` | 아래 4 (기존 33 유지 · 실제 `.env`·네트워크 0 그대로) |
| `wiki.html` | `P_AREA` 에 `invest: '투자·자산'` 한 항목만 (서버는 요청마다 파일을 읽으므로 재기동 불필요) |
| 문서 | README 요약표 v4.21.0 행 + 본문 「매일 Wiki 검토」 절에 2줄(투자 분야 · `--backfill`) · `docs/changelog/2026-11.md` 맨 위 v4.21.0(앵커) · 색인 행(13 · v4.17.0 ~ v4.21.0 · 크기) · CLAUDE.md·AGENTS.md 는 Commands 에 `--backfill=30` **한 줄**과 새 절에 **한 줄**만(상한 95,733B — 지금 약 773B 남음) · 머리 버전 v4.21.0 · `docs/claude_history.md` 1줄 |

바꾸면 안 되는 것: `lib/proposals.js`·`server.js` · 장부 · `.env` · launchd · `~/.claude/skills/` · 커밋·push.

## 1. 투자 분야 · 상한 5건
- `area` enum 에 `invest` 추가(SCHEMA·`validate` 둘 다). 프롬프트 규칙에 분야 설명 한 줄: `dev`=개발 자동화 · `work`=회사 업무 · `knowledge`=지식관리 · `content`=콘텐츠·영상 · `invest`=투자·자산관리.
- `MAX_PROPOSALS` 3 → 5, SCHEMA `maxItems` 3 → 5, 프롬프트 「0~3건」 → 「0~5건」.

## 2. `--backfill=DAYS` (지난 자료 훑기, 1회성)
- 시작 = 지금 − DAYS일. 대상 = 정식 실행과 같은 조건(영상 exclude 제외 · 꿀팁 전부)이되 **40편 자르기 없음**(`select_targets` 에 상한 인자).
- **묶음**: 최신순 영상을 40편씩, 꿀팁을 40건씩 나눠 i번째 묶음 = 영상 i번째 덩어리 + 꿀팁 i번째 덩어리. 묶음마다 `claude -p` 1회(인자·도구 0·MCP 0 그대로), 프롬프트는 정식과 같되 「후보 0~8건」, 그 호출만 SCHEMA `maxItems` 8. 검증은 **그 묶음의 record_id** 기준(`validate` 그대로).
- 묶음 호출 실패: 재시도 없음, `batch_errors` 에 사유 기록 후 다음 묶음. **연속 2회 실패면 거기서 멈춘다**.
- **순위 매기기**: 유효 후보가 15건 이하면 그대로. 넘으면 `claude -p` 1회 더 — 프롬프트 = 프로필 + 후보 목록(번호·kind·area·title·why·effort, skill_md 는 앞 600자) + 「겹치는 것은 하나만 남기고 대표님께 가장 쓸모 있는 순서로 최대 15개 번호를 고르라」, 스키마 `{"pick": [정수, maxItems 15], "note": 문자열}`. 범위 밖·중복 번호는 버리고, **후보 내용은 고쳐 쓰지 않는다**(고른 순서대로 원래 후보를 가져온다). 순위 호출이 실패하면 후보 앞 15건(묶음 순서 = 최신순).
- 저장: `--days` 와 같은 `trial/<YYYYMMDD-HHMMSS>.json`, id `trial-<stamp>-<n>`(n 1~15) — 기준점(`through`)을 움직이지 않고 화면은 지금 코드 그대로 보여 준다. 내용에 `mode: "backfill"`, `considered`(전체 영상·꿀팁 수), `batches`, `candidates`, `batch_errors`, `note`(순위 호출 note 또는 묶음 note 이어 붙임). 성공한 묶음이 0이면 파일 없이 `ok:false`.
- 알림 없음(정식 실행 아님). `--dry-run` 과 같이 쓰면 묶음 수·대상 수·묶음별 프롬프트 글자 수만, 호출 0·쓰기 0.
- `RESULT_JSON` 에 `batches`·`candidates`·`batch_errors` 수 추가(정식 실행엔 없어도 됨).

## 3. 정식·`--days` 동작은 1·5의 변경 말고 그대로.

## 5. 꿀팁 우선 (대표님 11-09 추가 — 「텔레그램에 남긴 것은 내가 중요하다고 생각한 것」)
꿀팁(카톡 「나와의 채팅」·텔레그램 봇 방)은 대표님이 **직접 골라 남긴 것**이다. 영상(재생목록 자동 수집)보다 신호가 강한데, 제목·URL 만 있어 정보가 얇다는 이유로 버려졌다.
- 프롬프트(정식·`--days`·backfill 묶음 공통) 규칙에 추가: 「꿀팁은 대표님이 직접 골라 남긴 자료라 영상보다 우선한다. 정보가 얇아도 제목·메모·URL 로 무엇인지 알 수 있으면 후보로 본다. 내용을 알 수 없으면(예: 「(제목 미확인)」 인스타 릴스) 버리지 말고 kind=action 「원문 확인 후 스킬화」 제안이 맞는지 판단한다. 영상 요약과 같은 주제면 둘 다 evidence 로 묶는다.」 프롬프트의 꿀팁 절 제목도 「## 대표님이 직접 남긴 꿀팁 (우선)」 으로.
- SCHEMA 에 선택 필드 `tip_review`: 배열, 항목 `{id: 문자열, verdict: "proposed"|"skipped", reason: 문자열}`. 프롬프트: 「대상 꿀팁마다 하나씩 — 제안에 썼으면 proposed, 아니면 skipped 와 이유 한 줄」. 저장 파일에 `tip_review` 그대로 남긴다(대상 밖 id 항목만 버림, 없거나 모양이 틀려도 실패 아님 — 빈 배열).
- backfill 순위 프롬프트에 「꿀팁이 evidence 에 들어간 후보를 우선한다」 한 줄, 후보 목록에 `꿀팁근거: 예/아니오` 표시.
- 테스트 추가: ㉖ 프롬프트에 우선 문구·꿀팁 절 제목이 있음 ㉗ `tip_review` 저장 · 대상 밖 id 버림 · 모양 틀림은 빈 배열(실패 아님) ㉘ 순위 프롬프트에 꿀팁근거 표시.

## 4. 테스트 (최소 추가)
⑱ `invest` 분야 제안 통과 · 모르는 분야 버림 ⑲ 정식 실행 6건 응답 → 5건 저장 · 1건 `over_limit` ⑳ backfill 영상 85편 → 묶음 3 · 호출 3(후보 ≤15) · 묶음 밖 evidence 버림 ㉑ 후보 > 15 → 순위 호출 1회 · 고른 순서대로 · 범위 밖·중복 번호 무시 · 내용 무변경 ㉒ 순위 호출 실패 → 앞 15건 ㉓ 묶음 연속 2회 실패 → 멈춤 · 1회 실패는 계속 ㉔ backfill 은 trial 폴더 · 다음 정식 실행 기준점 불변 · 알림 0 ㉕ `--backfill --dry-run` 호출 0 · 쓰기 0.
가짜 claude 는 표준입력에 순위 프롬프트 표식이 있으면 다른 응답 파일을 내게 하는 식으로(실행 파일 하나).

## 확인
1. `test_skill_review.py` 전부 통과 2. `scripts/run_all_tests.sh` → 20/20 3. 실데이터 `skill_review.py --backfill=30 --dry-run` 결과(묶음 수·대상 수) 보고 — **실제 backfill 실행은 하지 않는다**(PM 이 한다).

## 기준표
| # | 기준 | 근거 |
|---|---|---|
| 1 | ⑱~㉕ 포함 전부 통과 · 네트워크·실제 `.env` 0 | 출력·코드 |
| 2 | 묶음·순위 호출도 도구 0·MCP 0·재시도 0 · 연속 2회 실패 멈춤 | 코드(호출 1곳 재사용) |
| 3 | 순위 호출이 후보 내용을 바꾸지 못함(번호만 받음) | 코드·㉑ |
| 4 | backfill 이 기준점·정식 날짜 파일·알림을 건드리지 않음 | ㉔ |
| 5 | 회귀 20/20 · `test_claude_md_budget`·`test_readme_changelog` 통과 | 출력 |
| 6 | 범위 밖 변경 0 (`lib/proposals.js`·`server.js` 무변경) · 커밋 0 | `git status`·`git diff --stat` |
| 7 | 실데이터 backfill dry-run 결과 보고 | 보고 |
