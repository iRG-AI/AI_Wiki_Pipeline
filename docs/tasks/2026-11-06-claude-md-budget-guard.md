# [CC-1106-C] CLAUDE.md 크기 가드 — scripts/test_claude_md_budget.py (v4.19.6)

- 발주: 대표님 11-06 — ERP `docs/pm_claude_md_diet_port_1106.md` 3절 「마지막 — 크기 가드」 (읽기만). 본보기 ERP `tests/test_claude_md_budget.py`
- 선행: [CC-1106-B] v4.19.5 push. 3단계(폴더별 분할)는 하지 않았다 — 한 폴더에만 걸리는 절 0개(investigator 11-06)
- 담당: implementer · 버전 **v4.19.6** (테스트 = PATCH)
- **실행 창**: `.py`·`.sh` 편집은 정시 실행·wiki-ingest 창(17:25~18:20 등)에 훅이 막는다. 막히면 우회하지 말고 멈춰서 보고.

## 범위

- 새 `scripts/test_claude_md_budget.py`
- `.claude/agents/scribe.md` 18행 (0절)
- `scripts/run_all_tests.sh` — `PY_TESTS` 끝에 1개 · 머리 주석 17종 → 18종
- 「17종」 표기 전부 → 18종(지난번 README 4곳이 남았던 일 — 이번에는 같은 커밋에서): `CLAUDE.md` 89·108행 근처 · `README.md` 18·297·299·470행 근처(요약표 v4.19.3 행 제목은 지난 기록이라 그대로) · `AGENTS.md`(다시 만들기)
- `CLAUDE.md` 명령 블록 회귀 목록 끝(`test_readme_changelog.py` 줄 다음)에 한 줄: `/opt/homebrew/bin/python3 scripts/test_claude_md_budget.py    # N/N    (v4.19.6) CLAUDE.md 크기·필수 제목·배경 앵커 (읽기만)` (앞 줄들과 정렬)
- 이번 버전 기록: `docs/claude_history.md` 맨 위 1줄 · README(머리 · 요약표 맨 위 · 「🔍」 범위) · `docs/changelog/2026-11.md` 맨 위 · 색인 2026-11 행(크기는 `wc -c` ÷ 1024 소수 1자리 — v4.19.5 때 「약 10 KB」 눈대중이었다)
- **[CC-1106-B] 검수 ⚠️ 반영 — 표 2행을 루트로 되돌린다**: 2단계에서 `docs/claude_md_background.md` 「핵심 파일 역할」 로 옮긴 행 중 루트에 같은 뜻이 없는 성질이 든 2행을 글자 그대로 루트 `### 핵심 파일 역할` 표로 되돌리고 background 에서 뺀다: `lib/kakao_parse.py` 행(「순수 함수, 네트워크 없음」) · `gas/sheet_mirror.gs` 행(「탭 화이트리스트(영상·꿀팁)」). 루트 표 안 위치는 옛 순서(34fdfd3 의 CLAUDE.md 표 순서)대로. **이 이동을 먼저 하고** 그 크기로 `ROOT_LIMIT` 을 정한다
- `.claude/hooks/`·`settings.json`·코드·장부 무변경

## 0. 버전 요약 인용 줄은 배경 파일로 (대표님 결정 11-06 「네, 배경 파일로」)

- `.claude/agents/scribe.md` 18행 `` `CLAUDE.md` — 머리 `**현재 버전:**` 줄과 버전 요약 인용 1줄, `` → `` `CLAUDE.md` — 머리 `**현재 버전:**` 줄. 버전 요약 인용 1줄(`> vX.Y: …`)은 `docs/claude_md_background.md` 「버전별 한 줄 요약」(`bg-versions`) 절 맨 아래(2026-11-06~ — CLAUDE.md 머리에 다시 쌓지 않는다). `` (나머지 글자 그대로)
- `CLAUDE.md` 머리의 버전 포인터 줄(`> (경위: [배경 §버전별 한 줄 요약](…#bg-versions)) — …`) 은 그대로 둔다. 머리에 남은 `> v4.10`·`> v4.12`·`> v4.18`·`> v4.19` 줄도 그대로(규칙·고유 이름이 있어 2단계에서 남긴 줄).
- 이 결정은 D4 와 같은 방식으로 D6 이 지킨다(1절).

## 1. 테스트 (표준 라이브러리만 · 읽기만 · 네트워크 0)

- 다른 `scripts/test_*.py` 처럼 검사마다 `✅`/`❌` 한 줄, 마지막 줄 `N/N`, 실패면 exit 1. 루트는 환경변수 `CLAUDE_MD_TEST_ROOT` 가 있으면 그 폴더(사본 시험용).
- 상수: `ROOT_LIMIT = <이 커밋의 CLAUDE.md 바이트> + 3000` (숫자를 코드에 박고 주석에 근거 날짜).

| 검사 | 내용 |
|---|---|
| D1 | `CLAUDE.md` 바이트 ≤ `ROOT_LIMIT`. 실패 문구: 「루트가 커졌습니다 — 경위는 docs/claude_md_background.md, 운영 이력은 docs/claude_history.md 로 (<n> > <limit>)」 |
| D2 | 필수 제목이 루트 `CLAUDE.md` 에 줄 전체로 있다. 목록 = 다른 파일이 이름으로 가리키는 절: `## 🚨 보안 및 안전 최우선 개발 원칙 (Security & Safety Guidelines)` · `### 중요한 제약사항` · `### launchd 데몬` · `## 운영 체계 — pm-wiki · 워커 · Cowork (2026-10-31~)` · `## 산출물 규칙` · `## 변경 이력` · `### 핵심 파일 역할` + `grep -rhoE 'CLAUDE\.md[^「]{0,6}「[^」]+」' .claude README.md docs/changelog/README.md scripts install*.sh` 로 찾은 그 밖의 절(실제 제목 줄 글자 그대로). 목록에 넣은 근거(어느 파일이 가리키나)를 주석으로 |
| D3 | 루트(`CLAUDE.md`)의 `claude_md_background.md#bg-…` 링크마다 `docs/claude_md_background.md` 에 `<a id="bg-…"></a>` 가 있다 · 그 앵커 중복 0 |
| D4 | `docs/claude_history.md` 가 있고 첫 줄이 `# CLAUDE.md 운영 이력` · 루트 `## 변경 이력` 아래 비어 있지 않은 줄이 포인터 1줄뿐(이력 줄 `- **20` 이 루트에 다시 쌓이지 않게) |
| D6 | 루트 `CLAUDE.md` 머리(첫 `## ` 제목 앞)의 `> v` 로 시작하는 인용 줄 = 정확히 `> v4.10:` · `> v4.12:` · `> v4.18:` · `> v4.19:` 네 줄(새 버전 요약 줄이 머리에 다시 쌓이지 않게). 실패 문구: 「버전 요약 인용 줄은 docs/claude_md_background.md#bg-versions 맨 아래에」 |
| D5 | 하위 `CLAUDE.md`(`lib/`·`scripts/`·`gas/` 등 루트 밖 `**/CLAUDE.md`, `node_modules`·`.git` 제외)가 있으면 첫 줄이 `# <폴더> 지침 — 루트 CLAUDE.md 와 함께 읽힌다` (지금은 0개 — 통과) |

## 2. 이번 버전 기록 (v4.19.6)

- 머리 `v4.19.5` → `v4.19.6`(CLAUDE.md·README).
- 요약표 맨 위: `| **[v4.19.6](docs/changelog/2026-11.md#v4-19-6)** | 2026-11-06 | **🧪 CLAUDE.md 크기 가드 test_claude_md_budget.py · 회귀 18종 · CC-1106-C** |`
- `2026-11.md` 맨 위 항목(앵커 `v4-19-6`) · `claude_history.md` 맨 위 줄(D1~D5 · 상한 값 · 18종 · 3단계 안 한 이유 한 줄).

## 기준표 (ERP 이식 문서 5절 5·6 + 이 건)

| # | 확인 | 방법 |
|---|---|---|
| G1 | 새 테스트 · 회귀 18/18 | `python3 scripts/test_claude_md_budget.py` 마지막 줄 · `scripts/run_all_tests.sh` 마지막 줄 `RESULT: 18/18 통과` · `test_readme_changelog.py` 9/9 |
| G2 | 실패를 잡는다 (기준 5) | scratchpad 사본(`CLAUDE.md`·`docs/`)에 `CLAUDE_MD_TEST_ROOT` 로: ① `CLAUDE.md` 에 4,000B 덧붙이기 → D1 ❌ ② 필수 제목 1줄 지우기 → D2 ❌ ③ 포인터 앵커 이름 틀리게 → D3 ❌ ④ `## 변경 이력` 아래에 `- **2026-11-07 (x)** — y` 추가 → D4 ❌ ⑤ 머리 `> v4.19:` 줄 아래에 `> v4.20: x` 추가 → D6 ❌ — 각각 exit 1 + 걸린 검사 이름, 매번 사본 되돌림 |
| G3 | 「17종」 남은 곳 | `git grep -n -e '17종' -e '17/17' -- '*.md' '*.sh' ':!docs/tasks' ':!docs/changelog/20*' ':!docs/claude_history.md'` — 남은 줄은 README 요약표 v4.19.3 행(지난 기록)뿐 |
| G5 | 2행 되돌림 | 두 행이 루트 표에 `git show 34fdfd3:CLAUDE.md` 의 그 행과 글자 그대로 · background 에서 빠짐 · 옛 34fdfd3 CLAUDE.md 의 빈 줄 아닌 줄이 새 CLAUDE ∪ background ∪ history 에 모두 있음(사라진 줄 = 버전 줄·「17종」 줄뿐) |
| G4 | 범위 밖 0 · 공개 레포 | `git status --porcelain` · 훅·설정·코드·장부 diff 0 · 추가된 줄에 `/Users/`·`/private/tmp/`·맥 이름·이메일 0 · AGENTS diff 0 |

## 하지 말 것

- 테스트를 지금 데이터에 맞춰 느슨하게 만들기(예외 목록) · 상한 여유를 3,000B 보다 크게 · 훅·설정·코드·장부 · 지시서·커밋에 절대경로 · `git push`

## 커밋

`[CC-1106-C] v4.19.6 CLAUDE.md 크기 가드 test_claude_md_budget.py (상한 <값>B · 회귀 18/18 · G2 5종 잡음 · 버전 요약 줄은 배경 파일로)` + `Co-Authored-By:` 줄(실제 모델)

## 참고 (범위 밖 · 보고만)

- `.claude/hooks/guard_run_window.sh` 5·28행이 CLAUDE.md 「정시 실행 창」 을 가리키지만 그런 제목은 없다(investigator 11-06). D2 목록에 넣지 않는다 — 훅 문구 정정은 대표님 승인 사항.
