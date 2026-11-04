# [CC-1104-G] 이력 구조 감지 장치 + 규칙 문서 (v4.19.2)

- 발주: 대표님 11-04 — ERP `docs/pm_docs_versioning_port_1104.md` 3~4절 「[CC-B]」 + 7절 위키 훅 연결·PM_ROLE 한 줄(대표님 승인 11-04) (그 파일은 읽기만)
- 담당: implementer
- 선행: [CC-1104-F] v4.19.1 커밋(월별 파일·3칸 요약표)
- 버전: **v4.19.2** (테스트·문서 = PATCH)

## 범위 — 바꾸는 파일

- 새 파일: `scripts/test_readme_changelog.py`
- `scripts/run_all_tests.sh` (`PY_TESTS` 끝에 1개 · 머리 주석 16종 → 17종)
- `CLAUDE.md` · `AGENTS.md` (아래 3절 줄만 · 두 파일 같은 글)
- `.claude/agents/scribe.md` · `.claude/agents/verifier.md` · `.claude/pm/PM_ROLE.md` (README 요약표·상세 위치를 말하는 줄만 — 4절)
- `README.md` 요약표 맨 위 1행 · `docs/changelog/2026-11.md` 맨 위 1항목 · `docs/changelog/README.md` 색인 2026-11 행
- `.claude/hooks/gate_subagent_stop.sh` — **8번 검사에 `elif` 하나만**(6절, 대표님 승인 11-04 · ERP 이식 문서 7절). 다른 검사 절·면제 목록·주석의 「15종」 무변경
- **`.claude/settings.json` · 그 밖 `.claude/hooks/` 변경 0**

## 1. `scripts/test_readme_changelog.py`

본보기: `~/Dev/iRichGreen_ERP/tests/test_readme_changelog.py` (C-1~C-8) · `~/Dev/CNC_REA/tools/check_docs.py` — 읽기만. 표준 라이브러리만 · 네트워크 0 · 파일 읽기만.

- 루트: 기본은 저장소 루트. 환경변수 `CHANGELOG_TEST_ROOT` 가 있으면 그 폴더를 루트로 본다(B2 시험용 — 사본에서 돌리기 위해).
- 다른 `scripts/test_*.py` 처럼 항목마다 `✅`/`❌` 한 줄, **마지막 줄 `N/N`** (통과/전체), 하나라도 실패면 exit 1. 실패 줄에는 어느 버전·파일·행인지 적는다.
- 버전 정규식은 접미사를 받는다: `v\d+\.\d+\.\d+(?:-[a-z])?`. 정렬 키 = (major, minor, patch, 접미사) — 같은 숫자면 `-b` > `-a`.
- 앵커 규칙: 버전의 `.` → `-` (`v4.6.0-a` → `v4-6-0-a`). 같은 버전이 두 번이면 두 번째(뒤 날짜)에 `-2`.

| 검사 | 내용 |
|---|---|
| C1 | README 에 상세 블록(`^#### \[v`) 0 |
| C2 | README `### 🕒 요약 이력 (Summary Table)` 표(다음 `###` 앞까지)의 모든 데이터 행이 한 줄 · 이스케이프 안 된 `\|` 로 나눴을 때 정확히 3칸 · 제목 칸 120자 이하 |
| C3 | 요약표 버전 엄격 내림차순 |
| C4 | 요약표 각 행 링크 `docs/changelog/YYYY-MM.md#<앵커>` — 파일이 있고 그 파일에 `<a id="<앵커>"></a>` 가 있으며 앵커가 그 행 버전에서 만든 값 · 링크 파일의 달 = 행 날짜의 달 |
| C5 | `docs/changelog/` 의 `README.md` 밖 파일은 모두 `YYYY-MM.md` · 모든 `#### [v` 헤딩 바로 윗줄이 그 버전의 앵커 |
| C6 | 앵커 전체 중복 0 (모든 월 파일 합쳐) |
| C7 | 헤딩 날짜의 달 = 파일 이름의 달 · 파일 안 버전 엄격 내림차순 |
| C8 | 요약표 버전 집합 = 월 파일 헤딩 버전 집합 (빠짐·남음 0) · 요약표 맨 위 행 = 가장 최근 달 파일 맨 위 항목 |
| C9 | `README.html` 없음 |

예외 목록을 두지 않는다(지금 데이터로 전부 통과해야 한다). 통과 안 되는 데이터가 있으면 고치지 말고 보고하라.

## 2. `scripts/run_all_tests.sh`

`PY_TESTS` 끝에 `test_readme_changelog` · 1행 주석 「회귀 테스트 16종」 → 「17종」. 다른 줄 무변경.

## 3. `CLAUDE.md` · `AGENTS.md` (두 파일 같은 글로)

1. 머리 `**현재 버전: v4.19** (2026-11-04)` → `**현재 버전: v4.19.2** (2026-11-04)`.
2. 명령 블록 `# 회귀 테스트 16종 …` → `17종`, 그 아래 목록 끝(`test_tips_bot.py` 줄 다음)에 한 줄:
   `/opt/homebrew/bin/python3 scripts/test_readme_changelog.py # N/N  (v4.19.2) README 요약표 ↔ docs/changelog 월별 파일 구조 (읽기만)` — N 은 실제 값, 앞 줄들과 같은 정렬.
   `# (2026-10-31) 회귀 테스트 16종 한 번에 — 마지막 줄 RESULT: 16/16` → `17종` · `17/17`.
3. 「산출물 규칙」 의 `- \`README.md\` 버전 이력은 요약 표 1행 + 상세 변경 내역 1절을 함께 쓴다. 메이저는 …, 마이너는 기능·안정성.` 한 줄을 아래로 바꾼다:
   ```
   - 버전 이력 (v4.19.1~, ERP·asset_manage 방식): README 「📝 버전 히스토리」 = 요약 이력 표(3칸 `| **[vX.Y.Z](docs/changelog/YYYY-MM.md#vX-Y-Z)** | 날짜 | **제목** |`, 버전 내림차순) + 월별 파일 링크뿐. 상세는 `docs/changelog/YYYY-MM.md` 맨 위에 헤딩 바로 윗줄 앵커 `<a id="vX-Y-Z"></a>` 와 함께. 규칙 정본 `docs/changelog/README.md`, 감지 `scripts/test_readme_changelog.py`.
   - 버전 부여: 단일 줄 · HEAD 기준(`git log --oneline -1`) · 새 행이 요약표 맨 위가 아니면 번호가 틀린 것 · push 한 번호는 고쳐 쓰지 않는다. 메이저 = 아키텍처 확장(소스·저장소·합성 엔진 추가), 마이너 = 기능·동작·안정성, **패치 = 수정·문서·테스트 — 문서만 고친 커밋도 PATCH 를 올린다(2026-11-04~, 그 전 「버전 유지」 이력 줄은 그대로 둔다).** `-a`·`-b` 접미사는 새로 만들지 않는다. MAJOR, 또는 소스·저장소·실행 경로·예약 작업을 바꾸는 MINOR 는 같은 커밋에서 README 본문도 맞춘다.
   ```
4. 「변경 이력」 맨 위에 2줄 (새 형식 — 「버전 유지」 를 쓰지 않는다):
   - `- **2026-11-04 (v4.19.2 — 이력 구조 감지 장치 + 규칙 문서)** — …` (이번 건: 테스트 C1~C9 · 회귀 17종 · 위 규칙 줄 · 에이전트·PM 문서 줄. 지시서 `docs/tasks/2026-11-04-changelog-guard-rules.md`.)
   - `- **2026-11-04 (v4.19.1 — 상세 이력을 월별 파일로 · 요약표 3칸)** — …` ([CC-1104-F] 커밋 내용: README <전>→<후> 바이트, 월별 8파일, 앵커 38, 「버전별 한 줄 요약」 이동. 지시서 `docs/tasks/2026-11-04-changelog-monthly-split.md`.)

## 4. 에이전트·PM 문서 (README 위치를 말하는 줄만)

- `.claude/agents/scribe.md` 3·17·23행 근처: 「README 요약표 1행 + 상세 1절」·「`### 📌 요약 이력` 맨 위 1행, `### 📝 상세 변경 내역` 맨 위 1절」·「머리 현재 버전」 → 「README `### 🕒 요약 이력` 맨 위 3칸 1행 + `docs/changelog/YYYY-MM.md` 맨 위 1항목(앵커 포함, 규칙 `docs/changelog/README.md`)」. README 머리에 버전 표기가 없으면 그 말은 뺀다(실제 README 를 보고).
- `.claude/agents/verifier.md` 27행 근처: 같은 뜻으로 + 「`scripts/test_readme_changelog.py` 통과」.
- `.claude/pm/PM_ROLE.md` 69·81행: 「README 요약표 1행 + 상세 1절」 → 「README 요약표 1행 + `docs/changelog` 월 파일 1항목」.
- `.claude/pm/PM_ROLE.md` 13행 「내가 직접 고쳐도 되는 것(작은 수정 …)」 줄 끝에 한 문장 덧붙임(대표님 승인 11-04): 「README · `docs/changelog/` 를 직접 고쳤으면 커밋 전 `python3 scripts/test_readme_changelog.py` 를 돌리고 통과 줄을 커밋 메시지에 남긴다(훅은 워커가 끝날 때만 돈다).」
- 그 밖 글 무변경.

## 6. 훅 연결 — 문서만 바꾼 변경도 검사 (대표님 승인 11-04)

본보기: `~/Dev/asset_manage/.claude/hooks/gate_subagent_stop.sh` 88~97행 (읽기만).

`.claude/hooks/gate_subagent_stop.sh` 8번 `if … fi` 의 `fi` 앞에 아래를 넣는다(코드 변경이면 회귀 17종이 이 테스트를 이미 포함하므로 `elif`):

```bash
elif printf '%s\n' "$changed" | grep -Eq '^README\.md$|^docs/changelog/'; then
  # 8-b. README·docs/changelog 만 바꿨으면 이력 구조 검사만 (1초 안쪽, v4.19.2)
  dlog="/tmp/cc-gate-AI_Wiki_Pipeline-${sid}-docs.log"
  if ! /opt/homebrew/bin/python3 scripts/test_readme_changelog.py >"$dlog" 2>&1; then
    fail="${fail}- scripts/test_readme_changelog.py 실패(README 요약표·docs/changelog 구조). 끝부분:\n$(tail -n 15 "$dlog" 2>/dev/null)\n"
  fi
```
그 밖 줄 무변경(이력 주석에 `# 2026-11-04 — README·docs/changelog 변경이면 이력 구조 검사(v4.19.2)` 한 줄 추가는 허용).

**훅 확인은 커밋한 뒤** 임시 worktree 에서 한다(저장소 작업 트리는 깨끗하게):
```bash
W=<scratchpad>/hookwt; git worktree add --detach "$W" HEAD
J='{"agent_type":"implementer","agent_id":"hooktest","session_id":"hooktest-1104"}'
# 깨끗한 상태 + 문서만 무해 변경(docs/changelog/README.md 끝에 빈 줄) → 0
(cd "$W" && printf '\n' >> docs/changelog/README.md && printf '%s' "$J" | bash .claude/hooks/gate_subagent_stop.sh; echo rc=$?)
# 요약표 두 행 순서 바꿈 → 2 + 「test_readme_changelog.py 실패」 문구
(cd "$W" && git checkout -- . && <요약표 2·3번째 데이터 행 맞바꿈> && printf '%s' "$J" | bash .claude/hooks/gate_subagent_stop.sh; echo rc=$?)
git worktree remove --force "$W"; rm -f /tmp/cc-gate-AI_Wiki_Pipeline-hooktest-1104*
```
(이 기준점 파일이 없으면 훅은 `HEAD` 를 기준으로 본다 — 미커밋 변경만 `changed` 에 든다. 의도대로다.)

## 5. 이번 항목 v4.19.2

- `docs/changelog/2026-11.md` 맨 위: 앵커 `v4-19-2` + `#### [v4.19.2] - 2026-11-04 (🧪 이력 구조 감지 장치 + 규칙 문서 · CC-1104-G)` + `- **요약**: …` + 불릿 몇 줄(테스트 C1~C9, 회귀 17종, 규칙 줄, 에이전트 문서, B2 결과).
- README 요약표 맨 위 1행(3칸) · README 3행 머리 `**현재 버전: v4.19** (2026-11-04)` → `**현재 버전: v4.19.2** (2026-11-04)` · `docs/changelog/README.md` 색인 2026-11 행(항목 수·범위·크기) 갱신. README 「🔍 상세 변경 내역」 2026-11 줄의 범위도 `v4.17.0 ~ v4.19.2`.

## 기준표

| # | 확인 | 방법 |
|---|---|---|
| B1 | 새 테스트 통과 · 회귀 17/17 | `python3 scripts/test_readme_changelog.py` 마지막 줄 · `scripts/run_all_tests.sh` 마지막 줄 `RESULT: 17/17 통과` |
| B2 | 테스트가 실제로 잡는다 | 저장소를 scratchpad 로 복사(`README.md`·`docs/changelog/`)한 사본에서 `CHANGELOG_TEST_ROOT=<사본>` 로: ① 월 파일 앵커 1줄 삭제 ② 요약표 두 행 순서 바꾸기 ③ README 에 `#### [v9.9.9] - 2026-11-04 (x)` 블록 추가 — 각각 따로 해서 exit 1 + 걸린 검사 이름을 보이고, 매번 사본을 되돌린다. 저장소 파일은 손대지 않는다 |
| B3 | 「버전 유지」 규칙이 새 규칙으로 | `grep -n "버전을 올리지 않는다\|버전 유지" CLAUDE.md AGENTS.md README.md docs/changelog/README.md` — 남은 것은 지난 이력 줄(11-04 이전·이번 전 날짜 줄)과 새 규칙 문장 속 인용뿐 · 그 목록을 그대로 보고 |
| B4 | 설정·코드·장부 무변경 · 훅은 8-b 만 | `git diff --stat HEAD~1` 에 `settings.json`·`*.js`·`lib/`·`data/` 없음 · `git diff HEAD~1 -- .claude/hooks/` 가 `gate_subagent_stop.sh` 의 8-b `elif` 블록(+ 이력 주석 1줄)뿐 |
| B7 | 훅 문법 · 잡는다 | `bash -n .claude/hooks/gate_subagent_stop.sh` · 6절 worktree 시험: 무해 문서 변경 rc=0 · 요약표 두 행 바꿈 rc=2 + 「test_readme_changelog.py 실패」 · 시험 뒤 `git worktree list` 1줄 · `git status --porcelain` 빈 출력 |
| B8 | PM_ROLE 한 줄 | `grep -n 'test_readme_changelog' .claude/pm/PM_ROLE.md` — 13행 작은 수정 줄 |
| B5 | CLAUDE.md = AGENTS.md (바꾼 줄) | 바꾼 줄 각각 두 파일에 같은 글 — `grep -c` 로 대조 |
| B6 | 공개 레포 | 새·바꾼 줄에 개인 절대경로·맥 이름·이메일 없음 (본보기 경로는 `~/Dev/...` 표기) |

## 하지 말 것

- 훅의 8-b 밖 줄 · `settings.json`(훅 등록 포함) · 코드(`*.js`·`lib/`) · 장부 · 지난 버전 번호 · 지난 이력 줄 · ERP·다른 저장소 파일 · rebase/amend/force-push · `git push`(PM 이 한다)

## 커밋

`[CC-1104-G] v4.19.2 이력 구조 감지 장치 test_readme_changelog.py + 규칙 문서 (회귀 17/17 · B2 3종 잡음)` + `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`
