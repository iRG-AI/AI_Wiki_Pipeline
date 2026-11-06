# [CC-1106-A] CLAUDE.md 다이어트 1단계 — 「변경 이력」 을 docs/claude_history.md 로 (v4.19.4)

- 발주: 대표님 11-06 — ERP `docs/pm_claude_md_diet_port_1106.md` 3절 1단계 · 4절 pm-wiki 주의 (그 파일은 읽기만)
- 담당: implementer (기계적 이동 — 요약·다듬기 금지)
- 버전: **v4.19.4** (문서 = PATCH)
- 다음: 2단계 [CC-1106-B] 경위 이동 (이 건 push 뒤)

## 범위 — 바꾸는 파일

- `CLAUDE.md` · `AGENTS.md`(다시 만들기) · 새 `docs/claude_history.md`
- 규칙 문장 4곳: `CLAUDE.md` 2줄(아래 3절) · `.claude/pm/PM_ROLE.md` 13·69행 · `.claude/agents/scribe.md` 18행
- 이번 버전 기록: `README.md`(머리 버전 · 요약표 맨 위 1행 · 「🔍 상세 변경 내역」 2026-11 범위) · `docs/changelog/2026-11.md` 맨 위 · `docs/changelog/README.md` 색인 2026-11 행
- 그 밖 0. `.claude/hooks/`·`settings.json`·코드·장부 무변경.

## 0. 먼저 떠 두기 (레포 밖)

`S=/private/tmp/claude-501/-Users-tycoonan-Dev-AI-Wiki-Pipeline/d4e78755-5ee1-403d-9bbf-3c27b7ea90d2/scratchpad/diet1` — `cp CLAUDE.md $S/CLAUDE.before.md` · `wc -c CLAUDE.md AGENTS.md > $S/before_wc.txt`.

## 1. 옮기기

- `CLAUDE.md` 650행 `## 변경 이력` **다음 줄부터 파일 끝까지**(빈 줄 포함, 글자 그대로)를 새 파일 `docs/claude_history.md` 로 옮긴다. 파일 머리:
  ```
  # CLAUDE.md 운영 이력

  `CLAUDE.md` 에서 옮긴 운영 이력이다. 규칙은 `CLAUDE.md` 가 정본이다. 새 이력 줄은 이 파일 맨 위(이 머리 아래)에 쓴다(2026-11-06~). 버전별 상세는 `docs/changelog/`.

  ```
  그 아래에 옮긴 줄들(맨 위 = 가장 최근, 순서 그대로).
- `CLAUDE.md` 에는 `## 변경 이력` 제목과 그 아래 한 줄만 남긴다:
  ```
  ## 변경 이력

  → `docs/claude_history.md` (운영 이력 · 새 줄은 그 파일 맨 위) · 버전 이력은 `docs/changelog/`
  ```
- 스크립트(`python3 -I`, scratchpad)로 한다. 옮긴 덩어리는 바이트 단위로 같아야 한다.

## 2. 이번 이력 줄 (docs/claude_history.md 맨 위 — 새 규칙 첫 적용)

`- **2026-11-06 (v4.19.4 — CLAUDE.md 다이어트 1단계: 변경 이력 이동)** — CLAUDE.md 「변경 이력」 <N>바이트를 `docs/claude_history.md` 로 글자 그대로 옮기고 루트에는 포인터 1줄. 새 이력 줄은 그 파일 맨 위(CLAUDE.md 「운영 체계」·「산출물 규칙」, PM_ROLE, scribe 문구 교체). CLAUDE.md <전> → <후> 바이트. 코드·장부 무변경. 지시서 \`docs/tasks/2026-11-06-claude-md-diet-1-history.md\`. ERP 본보기 `docs/pm_claude_md_diet_port_1106.md`.`
(<…> 는 실제 값)

## 3. 규칙 문장 고치기 (이 4곳만 — 뜻은 「이력을 어디에 쓰나」 만 바뀐다)

| 파일 | 지금 | 바꾼 뒤 |
|---|---|---|
| `CLAUDE.md` 「운영 체계」 일의 흐름 줄 끝 | `(기록은 커밋 메시지 · 이 파일 「변경 이력」).` | `(기록은 커밋 메시지 · \`docs/claude_history.md\` 맨 위).` |
| `CLAUDE.md` 「산출물 규칙」 | `` - `CLAUDE.md`는 구조·제약이 바뀔 때 갱신하고 하단 이력에 날짜와 함께 남긴다. `` | `` - `CLAUDE.md`는 구조·제약이 바뀔 때 갱신하고, 이력은 `docs/claude_history.md` 맨 위에 날짜와 함께 남긴다(2026-11-06~, 그 전 이력도 그 파일에 있다). `` |
| `.claude/pm/PM_ROLE.md` 13행 | `· CLAUDE.md 이력 줄.` · `커밋 메시지와 CLAUDE.md 「변경 이력」이 그 변경의 기록이다.` | `· 이력 줄(\`docs/claude_history.md\`).` · `커밋 메시지와 \`docs/claude_history.md\` 맨 위 줄이 그 변경의 기록이다.` |
| `.claude/pm/PM_ROLE.md` 69행 | `CLAUDE.md 이력 1줄` | `\`docs/claude_history.md\` 이력 1줄` |
| `.claude/agents/scribe.md` 18행 | `하단 「변경 이력」 맨 위에 1줄.` | `이력 1줄은 \`docs/claude_history.md\` 맨 위(2026-11-06~).` |

(실제 글자는 파일을 보고 맞춘다. 글자가 다르면 멈추고 보고.)

## 4. AGENTS.md 다시 만들기

`AGENTS.md` 머리글 규칙대로: 지금 `AGENTS.md` 1~5행(머리글) + 새 `CLAUDE.md` 4행부터 끝까지. 확인 `diff <(sed -n '4,$p' CLAUDE.md) <(sed -n '6,$p' AGENTS.md)` 빈 출력.

## 5. 이번 버전 기록 (v4.19.4)

- `CLAUDE.md`·README 머리 `**현재 버전: v4.19.3**` → `v4.19.4`.
- README 요약표 맨 위: `| **[v4.19.4](docs/changelog/2026-11.md#v4-19-4)** | 2026-11-06 | **🪶 CLAUDE.md 다이어트 1단계 — 변경 이력을 docs/claude_history.md 로 · CC-1106-A** |`
- `docs/changelog/2026-11.md` 맨 위: 앵커 `v4-19-4` + `#### [v4.19.4] - 2026-11-06 (🪶 CLAUDE.md 다이어트 1단계 — 변경 이력을 docs/claude_history.md 로 · CC-1106-A)` + `- **요약**: …` + 불릿(옮긴 바이트 · 전후 크기 · 규칙 문장 4곳 · AGENTS 다시 만듦).
- README 「🔍 상세 변경 내역」 2026-11 줄 · `docs/changelog/README.md` 색인 2026-11 행(항목 수 · 범위 · 크기, 1024 기준 소수 1자리) 갱신.

## 기준표 (ERP 이식 문서 5절)

| # | 확인 | 방법 |
|---|---|---|
| 1 | 규칙이 사라지지 않았다 | 옛 `CLAUDE.md`(0단계 사본)의 빈 줄 아닌 모든 줄이 새 `CLAUDE.md` 또는 `docs/claude_history.md` 에 **줄 전체로** 있다 — 스크립트로 「사라진 줄」 목록. 허용되는 것은 3절에서 일부러 바꾼 CLAUDE.md 2줄·머리 버전 줄뿐(그 줄의 옛/새 글을 보고) |
| 1b | 옮긴 덩어리 바이트 동일 | 옛 650행 다음 ~ 끝 vs `docs/claude_history.md` 에서 머리(4줄)와 v4.19.4 줄을 뺀 글 — `cmp` 같음 |
| 2 | 규칙 문장은 루트에 | `docs/claude_history.md` 로 간 줄은 모두 `- **YYYY-MM-DD (…)**` 로 시작하는 이력 줄(또는 빈 줄) — 그 밖 줄 0 |
| 3 | 제목 그대로 | 옛 `^#{1,4} ` 제목 목록 ⊆ 새 `CLAUDE.md` 제목 목록 (`## 변경 이력` 포함) |
| 5 | 크기 | `wc -c CLAUDE.md AGENTS.md` 전후 |
| 6 | 회귀 · 범위 밖 0 | `scripts/run_all_tests.sh` 마지막 줄 17/17 · `python3 scripts/test_readme_changelog.py` 9/9 · `git status --porcelain` 범위 안 파일만 |
| 7 | AGENTS 동기 · 공개 레포 | 4절 diff 빈 출력 · 추가된 줄에 개인 절대경로·맥 이름·이메일 0 |
| 8 | 남은 참조 | `grep -rn '「변경 이력」\|하단 이력' CLAUDE.md .claude/agents .claude/pm/PM_ROLE.md` — 남은 줄을 그대로 보고(규칙으로 이력 위치를 말하는 문장이 남았으면 ❌) |

(4번 「폴더별로 읽힌다」 는 3단계 항목이라 이 건에는 없음.)

## 하지 말 것

- 이력 줄 요약·다듬기·순서 바꾸기 · 제목 바꾸기 · 3절 밖 규칙 문장 고치기 · `.claude/hooks/`·`settings.json`·코드·장부 · ERP 등 다른 저장소 · rebase/amend/force-push · `git push`

## 커밋

`[CC-1106-A] v4.19.4 CLAUDE.md 다이어트 1단계 — 변경 이력을 docs/claude_history.md 로 (CLAUDE.md <전>→<후> 바이트 · 사라진 줄 0 · 회귀 17/17)` + `Co-Authored-By:` 줄(실제 모델)
