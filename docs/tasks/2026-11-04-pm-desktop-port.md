# [CC-1104-A] PM 진행 방식 11-04 개정 이식 — 메인 세션 = PM · 작은 수정 · 요청 = 승인 (문서·설정만, 버전 유지)

- 작성: 2026-11-04 11:36 KST (pm-wiki)
- 승인: 대표님 2026-11-04 「ERP pm_desktop_port_1104.md 를 읽고 오늘 개정된 PM 진행 방식을 이 저장소에 적용해 줘」 — 요청 메시지 자체가 이 범위의 승인. push 는 따로.
- 실행: implementer · 검수: verifier
- 버전: 유지(운영 체계 문서). README 무변경(CC-1103-B 와 같은 취급).

## 배경
ERP 가 11-04 에 PM 세션 진행 방식을 바꿨고(본보기 `~/Dev/iRichGreen_ERP/.claude/pm/PM_ROLE.md`, 공통 지시서 `~/Dev/iRichGreen_ERP/docs/pm_desktop_port_1104.md` — 둘 다 읽기만), 각 저장소에 옮긴다. 바뀐 점:
1. Claude Desktop(Code 탭)에서 이 저장소로 연 **메인 세션이 PM** 이다. `CLAUDE.md` 머리 포인터 한 줄이 `PM_ROLE.md` 를 가리킨다. `pm-wiki.sh` 는 그대로(터미널로 띄워도 같다).
2. 목적 = 대표님 손이 가는 일을 최소로. 질문은 예/아니요·하나 고르기로, 응답 맨 끝에 하나로.
3. 작은 수정(한 파일 20줄 안팎 + 확인 방법이 뻔한 것)은 PM 이 직접 고치고 테스트를 직접 돌린다. 워커가 돌 때는 PM 이 파일을 고치지 않는다.
4. 대표님의 작업 요청 메시지 자체가 그 범위의 승인. 지시서가 범위를 넘거나 안이 갈릴 때만 묻는다. 멈춤 목록·push 승인은 그대로.
5. 지시서는 워커 한 번에 끝나는 크기로(고칠 파일 10개 초과·화면 확인 여럿이면 2~3개로).
6. 진행 상황은 Pinboard 로 보인다 — 응답 본문에 작업 보드 표를 그리지 않고 결론부터.
7. Desktop 에는 `--add-dir` 이 없다 → `.claude/settings.json` `permissions.additionalDirectories` 에 XP 폴더.

**이 저장소에서 그대로 두는 것(대표님 지시):** HANDOFF.md 인수인계 절차, Cowork(cw-wiki) 발주 흐름(XP 요청서 · 정시 실행 판정은 CW 몫 · 역할 표의 Cowork 행).

## 범위
- 바꿔도 되는 것: `CLAUDE.md` · `AGENTS.md`(재생성) · `.claude/pm/PM_ROLE.md` · `.claude/settings.json` · 이 지시서.
- 바꾸면 안 되는 것: 그 밖의 모든 파일. 특히 `pm-wiki.sh` · README · `.claude/agents/` · `.claude/hooks/` · `.claude/pm/local/` · XP 폴더.
- **공개 레포** — 개인 절대경로(`/Us` + `ers/…`)를 쓰지 않는다. XP 폴더는 `~/Documents/Claude/XP` 표기.

## 확인(먼저)
| 확인 | 기대 | 다르면 |
|---|---|---|
| `git status --porcelain` | 이 지시서 한 줄(`??`)만 | 멈추고 보고 |
| `git log --oneline -1` | `39cf803` | 멈추고 보고 |
| `diff <( { head -5 AGENTS.md; tail -n +4 CLAUDE.md; } ) AGENTS.md` | 출력 없음 | 멈추고 보고 |

## 단계

### 1. `CLAUDE.md`

1-a. 머리 포인터 — 5행 `**현재 버전: v4.18** …` **앞에** 아래 한 줄 + 빈 줄을 넣는다(3행 안내문 · 4행 빈 줄은 그대로, AGENTS 재생성이 4행부터 복사하므로 포인터가 AGENTS 에도 들어간다):
```
- **대표님과 직접 대화하는 메인 세션은 PM(pm-wiki) 이다 — 세션을 시작하면 `.claude/pm/PM_ROLE.md` 를 읽고 따른다** (2026-11-04 대표님 결정 · Claude Desktop(Code 탭)에서 이 저장소로 연 세션 · `./pm-wiki.sh` 로 띄워도 같다). 워커 서브에이전트(`implementer` · `verifier` · `investigator` · `scribe`)는 이 줄을 따르지 않는다.
```

1-b. 「운영 체계」 표의 pm-wiki 행 전체를 아래로 바꾼다(워커 행·Cowork 행은 그대로):
```
| **pm-wiki** (실행 PM) | Claude Code 메인 세션 — Claude Desktop(Code 탭)에서 이 저장소로 연 세션 또는 `./pm-wiki.sh` (Opus, 지침 `.claude/pm/PM_ROLE.md`) | 지시서 작성 → 워커 호출 → 검수 판정 → (대표님 승인 뒤) `git push` · 작은 수정(한 파일 20줄 안팎, 확인 방법이 뻔한 것)은 직접 고치고 테스트를 직접 돌림 · 인수인계 `.claude/pm/local/HANDOFF.md` | 작은 수정 밖의 코드·문서 직접 수정 · 워커가 도는 동안 파일 수정 |
```

1-c. 같은 절의 두 줄을 바꾼다.
- 기존 `- 일의 흐름: 대표님 지시 또는 XP 요청서 → pm-wiki 가 `docs/tasks/` 지시서 → 승인 → implementer → verifier(기준표 ✅/❌) → 미달이면 같은 implementer 에 재지시(지시서당 3회까지) → 통과 보고 → push 승인.`
  → `- 일의 흐름: 대표님 지시 또는 XP 요청서 → pm-wiki 가 `docs/tasks/` 지시서(워커 한 번에 끝나는 크기 — 고칠 파일 10개 초과면 2~3개로) → implementer → verifier(기준표 ✅/❌) → 미달이면 같은 implementer 에 재지시(지시서당 3회까지) → 통과 보고 → push 승인. 작은 수정은 pm-wiki 가 직접 고치고 `scripts/run_all_tests.sh` 를 직접 돌린다(기록은 커밋 메시지 · 이 파일 「변경 이력」).`
- 기존 `- 승인 단위는 **지시서 1건**이다 — 대표님이 승인한 지시서의 범위·기준표 안이면 워커가 추가 승인 없이 수행한다. 범위 밖 변경·지시서에 없는 장부 쓰기·외부 발송·launchd/`.env`/OAuth·운영 상태 파일 손수정·`git push` 는 멈추고 묻는다.`
  → `- (2026-11-04~) 승인은 **대표님의 작업 요청 메시지 자체**다 — 그 요청 범위 안의 지시서·워커 실행은 따로 승인받지 않는다(XP 요청서는 대표님이 진행하라고 한 메시지부터). 지시서가 요청 범위를 넘거나 고를 안이 갈리면 그 점만 묻는다. 범위 밖 변경·지시서에 없는 장부 쓰기·외부 발송·launchd/`.env`/OAuth·운영 상태 파일 손수정·`git push` 는 멈추고 묻는다.`

1-d. 「변경 이력」 맨 위(현재 첫 항목 `**2026-11-03 (운영 체계, 버전 유지)**` 앞)에 한 줄:
```
- **2026-11-04 (운영 체계, 버전 유지)** — PM 진행 방식 개정 이식(ERP 11-04 본보기): Claude Desktop 에서 이 저장소로 연 메인 세션이 PM(머리 포인터 1줄 → `.claude/pm/PM_ROLE.md`, `./pm-wiki.sh` 는 그대로) · 작은 수정(한 파일 20줄 안팎)은 PM 이 직접 · 대표님의 작업 요청 메시지가 그 범위의 승인 · 지시서는 워커 한 번에 끝나는 크기로 · 진행은 Pinboard(응답에 작업 보드 표 없음) · `.claude/settings.json` `permissions.additionalDirectories` 에 XP 폴더(Desktop 에는 `--add-dir` 이 없다). HANDOFF 인수인계 · Cowork 발주 흐름은 그대로. 코드·장부 무변경. 지시서 `docs/tasks/2026-11-04-pm-desktop-port.md`.
```

### 2. `AGENTS.md` — 재생성
`{ head -5 AGENTS.md; tail -n +4 CLAUDE.md; } > /tmp/agents.new && mv /tmp/agents.new AGENTS.md` (머리글 5줄 + CLAUDE.md 4행부터, CLAUDE.md 「산출물 규칙」의 갱신 방법). 손으로 고치지 않는다.

### 3. `.claude/pm/PM_ROLE.md`

3-a. 1~4행(제목 ~ 「…어긋나면 `CLAUDE.md` 가 이긴다.」)을 아래로 바꾼다:
```
# PM 역할 지침 — AI_Wiki_Pipeline (메인 세션 전용)

이 저장소에서 대표님과 직접 대화하는 **메인 세션은 PM(pm-wiki)** 이다(2026-11-04 대표님 결정 · Claude Desktop(Code 탭)에서 이 저장소로 연 세션).
`CLAUDE.md` 머리 포인터가 이 파일을 가리킨다. `./pm-wiki.sh`(`--append-system-prompt-file`)로 띄워도 같다.
워커 서브에이전트(`implementer` · `verifier` · `investigator` · `scribe`)는 이 파일을 따르지 않는다. 레포의 `CLAUDE.md`·`AGENTS.md` 는 PM 과 워커가 함께 따르고, 어긋나면 `CLAUDE.md` 가 이긴다.

**목적: 대표님 손이 가는 일을 최소로.** 대표님께 올라가는 것은 결정과 승인뿐이다. 나머지(지시서 · 워커 선택 · 검수 · 재지시)는 PM 이 끝까지 돌린다.
대표님은 휴대폰(Remote Control · Claude 앱 Code 탭)으로도 답한다 — 묻는 말은 「예/아니요」나 고르기 한 번으로 끝나게 쓰고, 응답 맨 끝에 하나로 모은다.
```

3-b. §0 의 두 줄(8·9행)을 바꾼다.
- `대표님 지시(또는 Cowork 의 XP 요청서)를 **지시서로 바꾸고, 워커에게 맡기고, 결과를 기준표로 검수해서, 작업 보드로 보고**한다.`
  → `대표님 지시(또는 Cowork 의 XP 요청서)를 **지시서로 바꾸고, 워커에게 맡기고, 결과를 기준표로 검수해서, 결론부터 보고**한다.`
- `나는 코드·문서를 직접 고치지 않는다 — 수정은 전부 `implementer`·`scribe` 서브에이전트가 한다. 예외: `docs/tasks/` 에 지시서를 쓰는 것, `.claude/pm/local/HANDOFF.md` 를 갱신하는 것.`
  → 아래 세 줄:
```
- **내가 직접 고쳐도 되는 것(작은 수정, 2026-11-04~)**: 한 파일 20줄 안팎이고 확인 방법이 뻔한 것 — 문구 · 설정값 한 줄 · verifier 지적 반영 · 지시서 · CLAUDE.md 이력 줄. 고친 뒤 `scripts/run_all_tests.sh` 를 직접 돌린다(코드를 건드렸으면 반드시). 커밋 메시지와 CLAUDE.md 「변경 이력」이 그 변경의 기록이다. 장부·launchd·`.env`·Vault 를 바꾸는 일은 크기와 상관없이 작은 수정이 아니다. `docs/tasks/` 지시서 · `.claude/pm/local/HANDOFF.md` 는 늘 내가 쓴다.
- 그보다 크거나 여러 파일 · 설계 판단이 섞이면 `implementer` 에게 맡기고, implementer 결과는 **반드시** `verifier` 가 본다.
- 워커가 돌고 있는 동안에는 내가 파일을 고치지 않는다(같은 파일 동시 수정 방지).
```

3-c. 역할 분담 표의 pm-wiki 행을 아래로 바꾼다(워커 행·Cowork 행은 그대로):
```
| **pm-wiki (나)** | 지시서 작성 → 워커 호출 → 검수 → 커밋 확인 → (대표님 승인 뒤) `git push` · 작은 수정 직접 · HANDOFF 갱신 |
```

3-d. §1 의 「여러 단계·여러 주체가 얽힌 작업은 **매 응답을 작업 보드로 시작**한다 …」 줄부터 「…끝난 항목은 지운다. 날짜가 정해진 관찰 항목은 순서 칸 "—".」 줄까지(24~30행: 안내 줄 · 빈 줄 · 표 머리 2줄 · 빈 줄 · 「누가」 줄 · 「기한」 줄)를 아래 두 줄로 바꾼다:
```
- 진행 상황은 **Pinboard**(Desktop 이 보여 주는 할 일 · 열린 결정)로 보인다. 응답 본문에 작업 보드 표를 따로 그리지 않고 결론부터 쓴다. 할 일·관찰 항목(날짜가 정해진 판정 포함)은 Pinboard 와 work_state 에 둔다.
- 대표님이 답해야 하는 질문은 응답 맨 끝에 하나로 모은다.
```
이어지는 「- 보드 끝에 **세션 상태** 한 줄(교체 필요 여부 + 근거: …).」 줄은 앞머리만 `- 큰 작업이 끝났을 때 **세션 상태** 한 줄(교체 필요 여부 + 근거: …).` 으로 바꾸고 나머지 글자·다음 두 줄(교체 기준 · HANDOFF 갱신·시작 지시문)은 그대로 둔다.

3-e. §2 수명주기 블록의 ② 줄
`  → ② 대표님 승인   (승인 전에는 지시서 말고 아무 파일도 바꾸지 않는다)`
→ 두 줄:
```
  → ② 승인 확인     대표님의 작업 요청 메시지 자체가 그 요청 범위의 승인이다(XP 요청서는 대표님이 진행하라고 한 메시지부터).
                    지시서가 요청에 없는 범위를 더하거나 고를 안이 갈리면 그 점만 묻고 기다린다
```

3-f. §2 의 「- 지시서 한 번에 하나. 대표님 할 일과 워커 할 일은 섞지 않는다.」 줄 **바로 다음**에 한 줄:
```
- **지시서 하나는 워커 한 번에 끝나는 크기로** 자른다. 고칠 파일이 10개를 넘거나 화면 확인이 여럿이면 2~3개로 나눈다(ERP 2026-11-04 CC-1104-A: implementer 80턴 · verifier 40턴 한도에 걸려 보고 직전에 멈췄다).
```

3-g. §6 의 「있으면 보드 맨 위에 올리고 대표님께 알린 뒤(승인 필요 여부 포함) 처리한다.」 → 「있으면 Pinboard 에 올리고 대표님께 알린 뒤(진행 지시가 필요한지 포함) 처리한다.」 (그 줄의 나머지 글자 그대로).

3-h. §7 첫 줄 `- 대표님 승인 없는 파일 변경(지시서·HANDOFF 작성은 예외)` → `- 대표님이 요청하지 않은 범위의 파일 변경(지시서·HANDOFF 작성은 예외)`.

그 밖의 줄(HANDOFF 읽기 · §2 의 CW 정시 판정 줄 · §3 · §4 · §5 · 시간 창)은 손대지 않는다.

### 4. `.claude/settings.json`
`permissions` 객체 안, `"deny": [...]` 배열 뒤에 키 하나를 더한다(쉼표 주의):
```
    "additionalDirectories": [
      "~/Documents/Claude/XP"
    ]
```
`allow` 의 `Read(~/Documents/Claude/XP/**)` · `Write(~/Documents/Claude/XP/**)` · `Edit(~/Documents/Claude/XP/**)` 는 그대로 둔다(Edit 규칙은 이미 있다). 그 밖의 키·훅은 손대지 않는다.

### 5. 확인
- `python3 -m json.tool .claude/settings.json > /dev/null && echo json-ok`
- `grep -n "PM_ROLE" CLAUDE.md | head -3` — 5행에 포인터
- `diff <( { head -5 AGENTS.md; tail -n +4 CLAUDE.md; } ) AGENTS.md` — 출력 없음
- `grep -n "작업 보드\|대표님 승인   " .claude/pm/PM_ROLE.md` — 출력 없음
- `git diff --stat` — 파일 4개
- `git diff | grep '^+' | grep -c '/Us''ers/'` — 0
- 코드는 안 건드렸으므로 회귀 테스트는 게이트가 돌리는 것으로 충분하다.

### 6. 커밋
`git add CLAUDE.md AGENTS.md .claude/pm/PM_ROLE.md .claude/settings.json docs/tasks/2026-11-04-pm-desktop-port.md` → 메시지
`[CC-1104-A] PM 진행 방식 11-04 개정 이식 — 메인 세션 = PM · 작은 수정 직접 · 요청 = 승인 · Pinboard · XP additionalDirectories (문서·설정만, 코드·장부 무변경)`. push 하지 않는다.

## 기준표 (verifier)
| # | 기준 | 확인 방법 |
|---|---|---|
| 1 | 커밋 1개, 파일 5개(CLAUDE.md · AGENTS.md · PM_ROLE.md · settings.json · 이 지시서)만 | `git show --stat HEAD` |
| 2 | CLAUDE.md 머리 포인터 · pm-wiki 행 · 두 줄 · 이력 줄이 지시서 문구와 글자 그대로, Cowork 행·XP 줄·훅 줄은 그대로 | `git show HEAD -- CLAUDE.md` |
| 3 | AGENTS.md = 머리글 5줄 + CLAUDE.md 4행부터 | 단계 5 diff |
| 4 | PM_ROLE.md 3-a ~ 3-h 가 문구 그대로, HANDOFF 읽기·교체 기준·§2 CW 정시 판정 줄·§3·§4·§5·시간 창은 그대로 | `git show HEAD -- .claude/pm/PM_ROLE.md` (삭제 줄이 3-a~3-h 대상뿐인지) |
| 5 | settings.json JSON 유효 · `permissions.additionalDirectories` = `["~/Documents/Claude/XP"]` · Edit(XP) 규칙 유지 · 훅 무변경 | `python3 -m json.tool` · `git show HEAD -- .claude/settings.json` |
| 6 | 공개 레포 금지값(개인 절대경로·맥 이름·`.env` 값) 추가 없음 · `pm-wiki.sh`·README 무변경 · 범위 밖 파일 변경 없음 | diff 읽기 · `git status --porcelain` · 작업 시작 시각 이후 수정 파일 |

## 하지 말 것
- 지정 줄 밖 손대기(서식 정리 포함) · README · `pm-wiki.sh` · 훅 · 에이전트 정의 수정 · `git push` · XP 폴더 파일 수정.
- AGENTS.md 를 손으로 고치기(재생성만).

## 롤백
`git revert <커밋>`.

## 범위 밖
- 실제 새 세션이 지침을 읽는지(`claude -p`) 확인은 PM 이 커밋 뒤에 직접 한다.
- CLAUDE.md 훅 줄의 「회귀 15종」(v4.18 뒤 16종) 표기는 이번에 고치지 않는다.
