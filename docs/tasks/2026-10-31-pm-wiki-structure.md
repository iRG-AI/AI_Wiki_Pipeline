# [CC-1031-A] 운영 체계 전환 — pm-wiki 실행 PM + 워커 서브에이전트 + 훅 (버전 유지)

- 작성: 2026-10-31 · Cowork(CW) → pm-wiki 첫 시운전 지시서
- 실행: `implementer`(Sonnet · medium) → 검수 `verifier`(Opus · high)
- 승인 범위: 이 지시서의 단계·기준표 안의 문서 수정과 커밋 1건. **`git push` 는 별도 승인.**

## 배경

지금까지 이 레포는 Cowork 가 지시서를 쓰고 대표님이 Claude Code 에 복붙해 실행했다. iRichGreen_ERP 의 `pm-erp` 처럼
Claude Code 세션 `pm-wiki` 가 실행 PM 이 되어 워커 서브에이전트에게 맡기고 검수하는 구조로 바꾼다. Cowork 는 정시 실행 판정·관찰·상담·설계 메모를 맡는다.
대표님이 터미널에서 돌린 설치 스크립트(`setup-pm-wiki.sh`)가 구조 파일을 이미 만들어 두었다 — 이 지시서는 그것을 확인하고 문서에 반영해 커밋한다. 코드·장부·데몬 무변경.

## 범위

- 바꿀 파일: `CLAUDE.md` · `AGENTS.md` · `README.md`
- 커밋에 넣을 파일(설치 스크립트가 만든 것): `.gitignore` · `pm-wiki.sh` · `.claude/pm/PM_ROLE.md` · `.claude/agents/{implementer,verifier,investigator,scribe}.md` · `.claude/hooks/{record_base,guard_run_window,gate_subagent_stop}.sh` · `.claude/settings.json` · `scripts/run_all_tests.sh` · 이 지시서
- 바꾸면 안 되는 것: 위 설치 파일의 내용(고칠 점이 보이면 보고만), 코드, `data/`, plist, `.env`, `docs/tasks/2026-10-31-v416-wiki-ingest-caffeinate.md`(다음 지시서 — 커밋에 넣지 않는다)

## 확인(먼저) — 하나라도 다르면 아무것도 바꾸지 말고 멈추고 보고

| # | 명령 | 기대값 |
|---|---|---|
| 0-1 | `git log --oneline -1` | `bddc01d v4.15 …` |
| 0-2 | `git status --porcelain -uall` | 정확히 아래 14줄 |
| 0-3 | `scripts/run_all_tests.sh` 마지막 줄 | `RESULT: 15/15 통과` |
| 0-4 | `jq -e . .claude/settings.json >/dev/null && echo ok` | `ok` |
| 0-5 | `for f in pm-wiki.sh .claude/hooks/*.sh scripts/run_all_tests.sh; do bash -n "$f" \|\| echo "FAIL $f"; done` | 출력 없음 |
| 0-6 | `git check-ignore -q .claude/agent-memory/x && git check-ignore -q .claude/pm/local/HANDOFF.md && echo ignored` | `ignored` |
| 0-7 | `git check-ignore -q .claude/agents/implementer.md; echo $?` | `1` (추적 대상) |

0-2 기대 14줄:
```
 M .gitignore
?? .claude/agents/implementer.md
?? .claude/agents/investigator.md
?? .claude/agents/scribe.md
?? .claude/agents/verifier.md
?? .claude/hooks/gate_subagent_stop.sh
?? .claude/hooks/guard_run_window.sh
?? .claude/hooks/record_base.sh
?? .claude/pm/PM_ROLE.md
?? .claude/settings.json
?? docs/tasks/2026-10-31-pm-wiki-structure.md
?? docs/tasks/2026-10-31-v416-wiki-ingest-caffeinate.md
?? pm-wiki.sh
?? scripts/run_all_tests.sh
```

## 단계

### 1. `CLAUDE.md` — 「운영 체계」 절 추가

`## 산출물 규칙` 줄 **바로 위**에 아래 블록을 그대로 넣는다(앞뒤 빈 줄 1개).

```markdown
## 운영 체계 — pm-wiki · 워커 · Cowork (2026-10-31~)

| 주체 | 어디서 | 하는 일 | 하지 않는 일 |
|---|---|---|---|
| **pm-wiki** (실행 PM) | Claude Code 세션 `./pm-wiki.sh` (Opus, 지침 `.claude/pm/PM_ROLE.md`) | 지시서 작성 → 대표님 승인 → 워커 호출 → 검수 판정 → (대표님 승인 뒤) `git push` · 인수인계 `.claude/pm/local/HANDOFF.md` | 코드·문서 직접 수정 |
| **워커** | pm-wiki 의 서브에이전트 `.claude/agents/` | `implementer`(Sonnet) 실행 · `verifier`(Opus, 읽기 전용) 검수 · `investigator`(Opus, 읽기 전용) 조사·설계 · `scribe`(Haiku) 문서 기록 | 지시서 범위 밖 변경 · `git push` |
| **Cowork(CW)** | claude.ai 프로젝트 「AI Wiki Pipeline」 | 정시 실행 판정·관찰, 대표님 상담(등급 오판 등 결정 자료), 조사·설계 메모, 다른 프로젝트 연계 | 레포·장부·데몬 쓰기 |

- 일의 흐름: 대표님 지시 또는 XP 요청서 → pm-wiki 가 `docs/tasks/` 지시서 → 승인 → implementer → verifier(기준표 ✅/❌) → 미달이면 같은 implementer 에 재지시(지시서당 3회까지) → 통과 보고 → push 승인.
- 승인 단위는 **지시서 1건**이다 — 대표님이 승인한 지시서의 범위·기준표 안이면 워커가 추가 승인 없이 수행한다. 범위 밖 변경·지시서에 없는 장부 쓰기·외부 발송·launchd/`.env`/OAuth·운영 상태 파일 손수정·`git push` 는 멈추고 묻는다.
- CW ↔ pm-wiki 는 XP 보드 `~/Documents/Claude/XP/`(`open/`·`done/`, `[XP-MMDD-A]`, `from: cw-wiki · to: pm-wiki` 또는 반대). CW 는 Claude Code 세션이 아니라 메시지를 받지 못한다 — 파일로만 주고받는다.
- 훅(`.claude/settings.json`): `guard_run_window.sh`(PreToolUse) — 장부 쓰기·launchd 조작은 매시 분 50~59·00~20, 코드·plist 편집은 정시 실행·wiki-ingest 창과 실행 중에 막는다. `record_base.sh`(SubagentStart) + `gate_subagent_stop.sh`(SubagentStop) — 워커가 끝나기 전에 공개 레포 규칙(개인 절대경로·맥 이름·`.env` 값)·gitignore·`README.html`·plist/셸 문법·회귀 15종을 검사하고, 미통과면 3회까지 돌려보낸다(`/tmp/cc-gate-<세션>.log`).
- `.claude/agents/`·`.claude/pm/PM_ROLE.md`·`.claude/hooks/`·`.claude/settings.json`·`pm-wiki.sh` 는 git 추적. `.claude/agent-memory/`(워커 메모리)·`.claude/pm/local/`(인수인계)·`.claude/settings.local.json` 은 gitignore.
```

### 2. `CLAUDE.md` — Commands 에 두 명령

`# 대기 큐 정리 (중복 제거 + dead-letter 격리) — 기본 dry-run` 줄 **바로 위**에 아래 4줄과 빈 줄 1개를 넣는다.

```bash
# (2026-10-31) 회귀 테스트 15종 한 번에 — 마지막 줄 RESULT: 15/15 통과, 실패하면 exit 1
scripts/run_all_tests.sh             # all | js | py
# (2026-10-31) 실행 PM 세션 띄우기 (Opus + 워커 서브에이전트, 「운영 체계」 절)
./pm-wiki.sh                         # --rc 면 Remote Control
```

### 3. `CLAUDE.md` — 산출물 규칙 한 줄 교체

AS-IS
```
- Cowork → Claude Code 핸드오프는 `docs/tasks/YYYY-MM-DD-<슬러그>.md` 작업지시서로 한다.
```
TO-BE
```
- 작업지시서는 `docs/tasks/YYYY-MM-DD-<슬러그>.md`(번호 `[CC-MMDD-X]`) — pm-wiki 가 쓰고 워커가 실행한다(「운영 체계」 절). Cowork 는 XP 요청서로 pm-wiki 에 발주한다.
```

### 4. `CLAUDE.md` — 변경 이력 맨 위 1줄

`## 변경 이력` 바로 아래 첫 항목으로:

```markdown
- **2026-10-31 (운영 체계 전환, 버전 유지)** — 실행 PM 을 Claude Code 세션 `pm-wiki`(`./pm-wiki.sh`, Opus) + 워커 서브에이전트 4종(`.claude/agents/` implementer·verifier·investigator·scribe) + 훅(`.claude/hooks/` 실행 창 보호·워커 종료 게이트)으로 옮겼다(iRichGreen_ERP `pm-erp` 구조). Cowork 는 정시 실행 판정·관찰·상담·설계 메모를 맡고 pm-wiki 에는 XP 요청서로 발주한다. `scripts/run_all_tests.sh`(회귀 15종 한 번에) 신설. `.gitignore` 에 `.claude/agent-memory/`·`.claude/pm/local/`. 코드·장부·데몬 무변경. 지시서 `docs/tasks/2026-10-31-pm-wiki-structure.md`.
```

### 5. `AGENTS.md` — 1~4 와 같은 변경

같은 기준 줄(`## 산출물 규칙` · `# 대기 큐 정리 …` · 산출물 규칙의 핸드오프 줄 · `## 변경 이력`)에 같은 문구. **기준 줄이 AGENTS.md 에 없으면 그 단계만 하지 말고 보고한다**(어긋나면 CLAUDE.md 가 이긴다).

### 6. `README.md` — 「📂 프로젝트 구조」에 3항목

기존 트리·표 모양 그대로 아래 3항목을 알맞은 자리에 넣는다(루트 파일 쪽에 `pm-wiki.sh`, `scripts/` 쪽에 `run_all_tests.sh`, 숨김 폴더 `.claude/`).
- `pm-wiki.sh` — 실행 PM 세션(Claude Code) 띄우기
- `.claude/` — pm-wiki 지침(`pm/PM_ROLE.md`)·워커 서브에이전트(`agents/`)·훅(`hooks/`)·`settings.json`
- `scripts/run_all_tests.sh` — 회귀 테스트 15종 한 번에

버전 번호·요약표는 바꾸지 않는다(버전 유지).

### 7. 커밋

```bash
git add .gitignore pm-wiki.sh .claude/pm/PM_ROLE.md .claude/agents/implementer.md .claude/agents/verifier.md \
  .claude/agents/investigator.md .claude/agents/scribe.md .claude/hooks/record_base.sh .claude/hooks/guard_run_window.sh \
  .claude/hooks/gate_subagent_stop.sh .claude/settings.json scripts/run_all_tests.sh \
  docs/tasks/2026-10-31-pm-wiki-structure.md CLAUDE.md AGENTS.md README.md
git commit -m "[CC-1031-A] 운영 체계 전환 — pm-wiki 실행 PM + 워커 서브에이전트 4종 + 훅 · scripts/run_all_tests.sh (코드·장부 무변경)"
```
(커밋 메시지 끝에 레포 관례의 Co-Authored-By 줄.) `git push` 는 하지 않는다.

## 기준표

| # | 기준 | 확인 방법 |
|---|---|---|
| 1 | 확인(먼저) 0-1 ~ 0-7 전부 기대값 | 출력 |
| 2 | CLAUDE.md 「운영 체계」 절 1개, `## 산출물 규칙` 바로 위 | `grep -n "^## 운영 체계\|^## 산출물 규칙" CLAUDE.md` — 운영 체계가 앞, 각 1줄 |
| 3 | CLAUDE.md Commands 에 `scripts/run_all_tests.sh`·`./pm-wiki.sh` | `grep -n "run_all_tests.sh\|./pm-wiki.sh" CLAUDE.md` |
| 4 | 산출물 규칙의 옛 핸드오프 줄이 없고 새 줄이 있다 | `grep -c "Cowork → Claude Code 핸드오프" CLAUDE.md` = 0 |
| 5 | 변경 이력 첫 항목이 2026-10-31 운영 체계 전환 | `grep -n -A1 "^## 변경 이력" CLAUDE.md` |
| 6 | AGENTS.md 에 2~5 같은 변경(또는 기준 줄 없음 보고) | grep 같은 4개 |
| 7 | README 프로젝트 구조에 3항목, 머리 버전 `v4.15` 그대로 | `grep -n "pm-wiki.sh\|run_all_tests.sh\|\.claude/" README.md` · `grep -n "현재 버전" README.md` |
| 8 | 커밋 1건, 메시지 `[CC-1031-A]` 로 시작, 파일 16개 | `git log --oneline -1` · `git show --stat HEAD \| tail -1` |
| 9 | 커밋 뒤 남은 변경은 다음 지시서 1줄뿐 | `git status --porcelain -uall` = `?? docs/tasks/2026-10-31-v416-wiki-ingest-caffeinate.md` |
| 10 | 공개 레포 규칙 — 커밋에 개인 절대경로·맥 이름·`.env` 값 없음 | 게이트 통과 + verifier 재확인 |
| 11 | 회귀 15종 | `scripts/run_all_tests.sh` → `RESULT: 15/15 통과` |
| 12 | push 안 함 | `git status -sb` 첫 줄에 `ahead 1` |

## 하지 말 것

- 설치 스크립트가 만든 파일의 내용 수정(이상하면 보고)
- `docs/tasks/2026-10-31-v416-wiki-ingest-caffeinate.md` 를 커밋에 넣기
- 버전 번호·README 요약표 변경, `README.html` 생성
- `git add -A`·`git add .`, `git push`

## 롤백

커밋 전: `git checkout -- CLAUDE.md AGENTS.md README.md`. 커밋 뒤(push 전): `git reset --soft HEAD~1` 후 위와 같이.
구조 자체를 걷어 낼 때: `.claude/settings.json` 을 지우면 훅이 꺼진다(워커 정의는 남아도 무해).

## 범위 밖

- v4.16(wiki-ingest caffeinate · brew 점검 순서) — 다음 지시서 `[CC-1031-B]`
- 레포 밖 설정(`rotate_extra_logs.sh`·MCP 등록) — 설치 스크립트가 대표님 터미널에서 처리
