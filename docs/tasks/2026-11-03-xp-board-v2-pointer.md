# [CC-1103-B] XP 보드 규칙 v2 포인터 (문서만, 버전 유지)

- 작성: 2026-11-03 12:55 KST (pm-wiki)
- 승인: 대표님 2026-11-03 12:57 「승인」
- 실행: scribe · 검수: verifier
- 버전: 유지(운영 체계 문서). README 무변경.

## 배경
XP 보드 규칙이 v2 로 바뀌었다(2026-11-03, 대표님 승인). 정본은 `~/Documents/Claude/XP/README.md`. 요점: 세션 시작 때 `open/` 확인 · 새 요청서는 `~/Documents/Claude/XP/new_xp.sh <발주코드>` 로만(코드 DS·ERP·AM·WIKI) · 번호 `XP-<발주코드>-<MMDD>-<순번>` · 파일명·번호 개명 금지, 상태는 본문 「상태」 줄에만 · 상대에게는 경로 대신 번호로. 11-03 이전 `XP-MMDD-A` 파일은 번호 그대로.
레포 문서에는 옛 형식 `[XP-MMDD-A]` 가 남아 있다(CLAUDE.md·AGENTS.md 「운영 체계」 절, `.claude/pm/PM_ROLE.md` §6).

## 수행 범위
- 바꿔도 되는 것: `CLAUDE.md`·`AGENTS.md`(두 파일 같은 내용)·`.claude/pm/PM_ROLE.md` 의 아래 지정 줄 · 이 지시서.
- 바꾸면 안 되는 것: 그 밖의 모든 파일. 특히 작업 트리에 있는 미커밋 파일 `docs/tasks/2026-11-03-v418-telegram-tips-bot.md` 는 커밋에 넣지 않는다.

## 단계
1. 사전 확인 — `git status --porcelain` 에 위 v418 지시서와 이 지시서 두 개(`??`)만 있어야 한다. 다르면 멈추고 보고.
2. `CLAUDE.md`·`AGENTS.md` 「운영 체계」 절 — 두 파일 모두 같은 치환:
   - 기존 줄
     ```
     - CW ↔ pm-wiki 는 XP 보드 `~/Documents/Claude/XP/`(`open/`·`done/`, `[XP-MMDD-A]`, `from: cw-wiki · to: pm-wiki` 또는 반대). CW 는 Claude Code 세션이 아니라 메시지를 받지 못한다 — 파일로만 주고받는다.
     ```
     을
     ```
     - CW ↔ pm-wiki 는 XP 보드 `~/Documents/Claude/XP/`(`open/`·`done/`, 번호 `XP-<발주코드>-<MMDD>-<순번>`, `from: cw-wiki · to: pm-wiki` 또는 반대). CW 는 Claude Code 세션이 아니라 메시지를 받지 못한다 — 파일로만 주고받는다.
     - (2026-11-03~) XP 보드 규칙 v2 의 정본은 `~/Documents/Claude/XP/README.md` — 세션 시작 때 `open/` 확인, 새 요청서는 `~/Documents/Claude/XP/new_xp.sh <발주코드>`(WIKI 등)로만 만들고, 파일명·번호는 바꾸지 않으며(상태는 본문 「상태」 줄에만), 상대에게는 경로 대신 번호로 말한다. 11-03 이전 `XP-MMDD-A` 파일은 번호 그대로.
     ```
     로 바꾼다(한 줄 → 두 줄).
   - 「변경 이력」 맨 위(현재 첫 항목 `**2026-11-01 (운영 체계, 버전 유지)**` 앞)에 한 줄:
     ```
     - **2026-11-03 (운영 체계, 버전 유지)** — XP 보드 규칙 v2(대표님 승인 11-03) 포인터: 정본 `~/Documents/Claude/XP/README.md`, 새 요청서는 `new_xp.sh <발주코드>` 로만, 번호 `XP-<발주코드>-<MMDD>-<순번>`, 상대에게는 번호로. 「운영 체계」 절 · `.claude/pm/PM_ROLE.md` §6 의 옛 `[XP-MMDD-A]` 표기 교체. 코드·장부 무변경. 지시서 `docs/tasks/2026-11-03-xp-board-v2-pointer.md`.
     ```
3. `.claude/pm/PM_ROLE.md` §6 — 기존 줄
   ```
   - 다른 프로젝트에 일을 시킬 때는 `[XP-MMDD-A]` 요청서로만, 완료 기준 없는 요청은 보내지 않는다. 상대 프로젝트 파일은 읽기만 한다.
   ```
   을
   ```
   - 다른 프로젝트·CW 에 일을 시킬 때는 `~/Documents/Claude/XP/new_xp.sh <발주코드>` 로 만든 요청서로만(번호 `XP-<발주코드>-<MMDD>-<순번>`, 규칙 정본 `~/Documents/Claude/XP/README.md` v2), 완료 기준 없는 요청은 보내지 않는다. 파일명·번호는 바꾸지 않고 상대에게는 번호로 말한다. 상대 프로젝트 파일은 읽기만 한다.
   ```
   로 바꾼다.
4. 확인 — `diff <(sed -n '/^## 운영 체계/,$p' CLAUDE.md) <(sed -n '/^## 운영 체계/,$p' AGENTS.md)` 출력 없음 · `grep -n "XP-MMDD-A" CLAUDE.md AGENTS.md .claude/pm/PM_ROLE.md` 는 새 문장 안의 "11-03 이전 `XP-MMDD-A` 파일" 과 변경 이력 줄의 "옛 `[XP-MMDD-A]` 표기"만.
5. 커밋 — `git add CLAUDE.md AGENTS.md .claude/pm/PM_ROLE.md docs/tasks/2026-11-03-xp-board-v2-pointer.md` → 메시지 `[CC-1103-B] XP 보드 규칙 v2 포인터 — 정본 XP/README.md · new_xp.sh · 번호로 말하기 (문서만, 코드·장부 무변경)`. push 하지 않는다.

## 완료 기준 (verifier)
| # | 기준 | 확인 방법 |
|---|---|---|
| 1 | 커밋 1개, 파일 4개(CLAUDE.md·AGENTS.md·PM_ROLE.md·이 지시서)만 | `git show --stat HEAD` |
| 2 | 두 문서의 해당 줄·이력 줄이 지시서 문구와 글자 그대로 | `git show HEAD` 읽기 |
| 3 | CLAUDE.md·AGENTS.md 「운영 체계」 절 이후 동일 | 단계 4 diff |
| 4 | 옛 형식이 단계 4 의 두 자리 말고 남지 않음 | 단계 4 grep |
| 5 | v418 지시서는 미커밋(`??`) 그대로 · 공개 레포 금지값(개인 절대경로·맥 이름·`.env` 값) 추가 없음 | `git status --porcelain` · diff 읽기 |

## 하지 말 것
- 다른 줄 손대기(서식 정리 포함) · README 수정 · `git push` · XP 폴더 파일 수정.

## 롤백
`git revert <커밋>`.
