# [CC-1109-C] 매일 Wiki 검토 3단계 — 매일 08:30 자동 실행 · 텔레그램 알림 · 회귀 20종 · 문서 v4.20.0

- 작성: pm-wiki · 2026-11-09 · 승인: 대표님 11-09 「3단계 진행」(계획 `mellow-mixing-scott.md` 3단계)
- 실행: implementer · 검수: verifier · 설치(`launchctl`)·커밋·push 는 PM 이 한다(이 지시서 범위 밖)
- 앞 단계: [CC-1109-A] `skill_review.py` · [CC-1109-B] 제안함 화면 — 둘 다 검수 통과, 아직 커밋 전

## 범위

| 파일 | 할 일 |
|---|---|
| `skill_review.py` | 텔레그램 알림 + `--no-notify` (아래) |
| `scripts/test_skill_review.py` | 알림 테스트 추가 · **모든 기존 호출이 실제 텔레그램에 닿지 않게** |
| `com.irichgreen.skill-review.plist` (신규, 레포 루트) | 아래 모양 |
| `install-skill-review.sh` (신규) | `install-wiki-ingest.sh` 와 같은 꼴(치환 없이 복사 → unload/load) — **만들기만, 실행 금지** |
| `scripts/run_all_tests.sh` | `JS_TESTS` 에 `test_proposals`, `PY_TESTS` 에 `test_skill_review` · 머리 주석 18 → 20종 |
| `README.md` | 요약표 맨 위 v4.20.0 행 · 본문(핵심 기능 1줄 · 파이프라인/모듈 상세에 「매일 Wiki 검토」 절 · 파일 구조 표 5행(`skill_review.py`·`lib/proposals.js`·plist·install 스크립트·테스트 2) · 회귀 18 → 20종 · 설치 가이드에 `install-skill-review.sh` 한 줄) |
| `docs/changelog/2026-11.md` | 맨 위 `<a id="v4-20-0"></a>` + `#### [v4.20.0] - 2026-11-09 (🧭 매일 Wiki 검토 → 제안함 → 승인 → 스킬 설치)` |
| `CLAUDE.md` | 아래 「CLAUDE.md 새 절」 + Commands 블록 3줄 + launchd 표 1행 + 회귀 줄 2개(18 → 20종) + 머리 `현재 버전` v4.20.0. **`scripts/test_claude_md_budget.py` 상한 95,733B 안** (지금 92,780B — 남은 약 2,900B) |
| `AGENTS.md` | CLAUDE.md 와 같은 변경을 같은 자리에 |
| `docs/claude_history.md` | 맨 위 1줄 |

바꾸면 안 되는 것: `lib/proposals.js`·`server.js`·`wiki.html`(B 단계 검수 통과본) · 장부 · `.env` · 설치된 launchd(`~/Library/LaunchAgents`) · `~/.claude/skills/` · 다른 테스트 · 커밋·push.

## 1. 알림 (`skill_review.py`)

- `.env` 의 `TELEGRAM_BOT_TOKEN`·`TELEGRAM_CHAT_ID`(실행 알림 봇 — 꿀팁 봇 `TIPS_BOT_*` 아님)를 `lib/env_util.load_env()` 로 읽는다. 없으면 `notified: "not_configured"`, 요청 0.
- 발송 함수는 모듈 수준 하나(`send_telegram(token, chat, text) -> bool`): `urllib.request` POST `sendMessage`, 20초, **재시도 없음**, 예외를 던지지 않고 True/False. 토큰·chat id·URL 을 출력·로그에 쓰지 않는다(`telegram_tips_ingest.tg` 와 같은 원칙).
- **보내는 경우만**: 정식 실행(`--days` 없음 · `--dry-run` 아님 · `--no-notify` 아님) 이고
  - 제안 ≥ 1 → `🧭 [매일 Wiki 검토] 제안 N건 (영상 V · 꿀팁 T 검토)` + 제안마다 `N. [스킬|적용] 제목` 한 줄 + 마지막 줄 `http://localhost:3000/wiki#tab=proposals`
  - 실패(`ok:false`, 단 `error == "exists"` 는 제외 — 같은 날 두 번째 실행은 조용히 끝) → `⚠️ [매일 Wiki 검토 실패] <error 앞 150자>`
  - 제안 0건 · 대상 0건 → 보내지 않는다(소음 줄이기).
- 결과: `RESULT_JSON` 에 `notified`(`true`·`false`·`"not_configured"`·`null`=보낼 경우 아님) 추가. 발송 실패는 `ok`·종료 코드를 바꾸지 않는다.
- 제목은 텔레그램 일반 글자로(파싱 모드 없음). 한 메시지 4,000자 넘으면 자른다.

## 2. 테스트 (`scripts/test_skill_review.py`)

- 파일 머리에서 `sr.send_telegram` 을 기록용 가짜로 바꾸고, `lib/env_util.load_env` 가 실제 `.env` 를 읽지 않게(가짜 env 를 돌려주게) 한다. **기존 25개 포함 어떤 경로도 실제 네트워크·실제 `.env` 에 닿지 않는다.**
- 추가 확인(최소): ⑩ 제안 ≥1 정식 실행 → 1회 발송, 본문에 건수·제목·`#tab=proposals` ⑪ 깨진 JSON 실패 → 실패 문구 1회 ⑫ `exists` → 0회 ⑬ 제안 0건 → 0회 ⑭ `--days`·`--dry-run`·`--no-notify` → 0회 ⑮ 토큰 없음 → `not_configured`, 0회 ⑯ 발송 False → `notified:false`, `ok` 그대로 ⑰ 출력(stdout·stderr)에 가짜 토큰 문자열 없음.

## 3. plist (`com.irichgreen.skill-review.plist`)

`com.irichgreen.wiki-ingest.plist` 를 그대로 본뜬다(같은 키·같은 PATH·LANG):
- `Label` `com.irichgreen.skill-review`
- `ProgramArguments` `/usr/bin/caffeinate` `-i` `/opt/homebrew/bin/python3` `<레포 절대경로>/skill_review.py`
- `StartCalendarInterval` Hour 8 · Minute 30 · `RunAtLoad` false · `WorkingDirectory` 레포 절대경로
- 로그 `~/Library/Logs/irichgreen/skill-review.log` · `skill-review-err.log` (절대경로로)
- `EnvironmentVariables` 에 `HOME` 은 넣지 않는다(launchd 가 준다). `CLAUDE_BIN` 도 넣지 않는다(코드 기본값 `~/.local/bin/claude`).
- `plutil -lint` 통과.

## 4. CLAUDE.md 새 절 (「기존분 재요약」 절 다음, 짧게 — 2,900B 안)

제목 `### 매일 Wiki 검토 → 제안함 (v4.20)` 아래 다음 규칙만(문장은 다듬어도 됨, 규칙은 빼지 말 것):
- 흐름 1줄: launchd 08:30 `skill_review.py` → 장부(읽기 전용) `created_at > 지난 through` 영상(exclude 제외)·꿀팁 → `claude -p`(도구 0 · MCP 0 · 재시도 0) → `data/proposals/YYYYMMDD.json`(KST) → 텔레그램(제안 ≥1·실패만) → `localhost:3000/wiki#tab=proposals` 에서 승인·보류·거절.
- 쓰는 주체 분리: 날짜 파일은 `skill_review.py` 만, `decisions.json` 은 `lib/proposals.js`(server.js) 만. 기준점은 마지막 날짜 파일의 `through` — 상태 파일 없음. `--days` 시험은 `trial/` 이라 기준점을 안 움직인다.
- **Claude 호출에 도구·MCP 를 주지 말 것**(`--tools ''`·`--strict-mcp-config`). 같은 날 파일이 있으면 멈춘다(`exists`, 알림 없음).
- 승인 = `~/.claude/skills/wiki-<slug>/SKILL.md` 설치. 내용은 저장된 제안에서만, 요청 본문 값은 쓰지 않는다. **이미 있으면 덮어쓰지 않는다(409)**. 되돌리기는 `data/proposals/_trash/` 로 이동(삭제 아님).
- POST `/api/proposals/decide` 는 Host·Origin 이 `localhost:3000`/`127.0.0.1:3000` 이고 JSON 일 때만. **`wiki_lan_server.js` 에 제안함 라우트를 넣지 말 것.**
- 프로필 `data/review_profile.md`(gitignore, 대표님이 고침). 구독 사용량을 쓴다 — 하루 1회.
- 판정: `~/Library/Logs/irichgreen/skill-review.log` 의 `RESULT_JSON`.

Commands 블록: `skill_review.py --dry-run` · `skill_review.py --days=7`(시험, trial) · `launchctl start com.irichgreen.skill-review`. launchd 표: `com.irichgreen.skill-review` | `skill_review.py` (v4.20 `caffeinate -i`) | 매일 08:30 | `/opt/homebrew/bin/python3`. 회귀 줄: `test_proposals.js 31/31` · `test_skill_review.py N/N`.
「launchd 데몬」 절 아래 문장의 「4개」(plist 4개 · 8군데)는 5개 · 10군데로.

## 확인

1. `/opt/homebrew/bin/python3 scripts/test_skill_review.py` 전부 통과
2. `scripts/run_all_tests.sh` → `RESULT: 20/20 통과`
3. `plutil -lint com.irichgreen.skill-review.plist` · `bash -n install-skill-review.sh`
4. `/opt/homebrew/bin/python3 skill_review.py --dry-run` (실데이터, 호출 0 · 쓰기 0 · 발송 0) 결과 보고
5. `/opt/homebrew/bin/python3 scripts/test_claude_md_budget.py` · `scripts/test_readme_changelog.py` 통과

## 기준표

| # | 기준 | 판정 근거 |
|---|---|---|
| 1 | 테스트 ⑩~⑰ 포함 전부 통과 · 테스트가 실제 `.env`·네트워크에 안 닿음 | 출력 · 코드(가짜 교체가 import 직후) |
| 2 | 알림은 정식 실행의 제안 ≥1·실패(exists 제외)만 · 발송 실패가 ok 를 안 바꿈 | 코드 · 테스트 |
| 3 | 토큰·chat id·URL 이 출력·로그에 안 나옴 | 코드 · ⑰ |
| 4 | plist = wiki-ingest 꼴 · 08:30 · caffeinate · Homebrew python3 · lint 통과 | `plutil -lint` · diff 대조 |
| 5 | install 스크립트 문법 통과 · 실행 안 함 | `bash -n` · `launchctl list` 에 skill-review 없음 |
| 6 | 회귀 20/20 | `run_all_tests.sh` |
| 7 | 문서: README 요약표·본문 · changelog 앵커 · CLAUDE.md 새 절(규칙 7개 다 있음)·크기 상한 안 · AGENTS.md 같은 변경 · history 1줄 | `test_readme_changelog` · `test_claude_md_budget` · grep |
| 8 | 범위 밖 변경 0 (B 단계 3파일 무변경 — 이번 작업 전후 sha256 같음) · 커밋 0 · 설치 0 | `git status` · sha256 |
| 9 | 새 문서 줄에 개인 절대경로·맥 이름·`.env` 값 없음(plist 제외) | 게이트 · grep |

## 하지 말 것
- `launchctl load/start` · `install-skill-review.sh` 실행 · 실제 텔레그램 발송 · `skill_review.py` 정식 실행(dry-run 만) · 장부 쓰기 · 커밋·push.
