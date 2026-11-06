# [CC-1106-B] CLAUDE.md 다이어트 2단계 — 경위를 docs/claude_md_background.md 로 (v4.19.5)

- 발주: 대표님 11-06 — ERP `docs/pm_claude_md_diet_port_1106.md` 3절 2단계 · 4절 · 6절 (그 파일은 읽기만). 본보기 기준 ERP `docs/handoff_claude_md_diet.md` 1절, 형식 ERP `docs/claude_md_background.md`
- 설계: investigator 11-06 (HEAD 34fdfd3 기준 줄 단위 대조)
- 담당: implementer (기계적 줄 이동 — 줄 쪼개기·요약·다듬기 금지)
- 버전: **v4.19.5** (문서 = PATCH)

## 원칙

- **줄 단위로 통째로만 옮긴다.** 규칙과 경위가 한 줄에 섞인 줄은 루트에 남긴다(완료 기준 1 = 옛 줄이 어딘가에 줄 전체로 있어야 함).
- 아래 목록의 줄만 옮긴다. 목록의 행 번호는 **HEAD 34fdfd3 의 `CLAUDE.md`** 기준이다. 옮기기 전에 각 행이 아래 「앞 글자」 와 맞는지 스크립트로 확인하고, 하나라도 다르면 멈추고 보고한다.

## 범위 — 바꾸는 파일

- `CLAUDE.md` · 새 `docs/claude_md_background.md` · `AGENTS.md`(다시 만들기)
- 1단계 검수에서 남은 옛 문구 2곳: `.claude/agents/scribe.md` 3행 · `.claude/agents/verifier.md` 27행 (4절)
- 이번 버전 기록: `docs/claude_history.md` 맨 위 1줄 · README(머리 버전 · 요약표 맨 위 · 「🔍」 2026-11 범위) · `docs/changelog/2026-11.md` 맨 위 · `docs/changelog/README.md` 색인
- 그 밖 0. `.claude/hooks/`·`settings.json`·코드·장부 무변경.

## 0. 먼저 떠 두기

`$SCRATCH` = 세션 scratchpad 아래 `diet2/` (PM 이 프롬프트로 경로를 준다 — **지시서·커밋에 그 절대경로를 쓰지 않는다**). `CLAUDE.before.md` 사본 · `wc -c CLAUDE.md AGENTS.md`.

## 1. 옮길 줄

### 1-a. 머리 인용 블록 — 버전별 한 줄 요약 17줄 (5,114B)

행 **9~19 · 21 · 23~27** (각각 `> v4.0:` ~ `> v4.9:` · `> v4.11:` · `> v4.13:` ~ `> v4.17:` 로 시작).
남기는 머리 줄: 20(`> v4.10:`) · 22(`> v4.12:`) · 28(`> v4.18:`) · 29(`> v4.19:`) · 31~35(이관·개명) — 규칙 문장이나 루트에서 그 줄에만 있는 이름이 있다.

옛 9행 자리(남는 `> v4.10:` 줄 바로 위)에 포인터 1줄:
```
> (경위: [배경 §버전별 한 줄 요약](docs/claude_md_background.md#bg-versions)) — v4.0~v4.17 중 규칙 문장이 없는 줄 · 버전 상세는 `docs/changelog/`
```

### 1-b. `### 핵심 파일 역할` 표 — 32행 (7,875B)

옮길 행: **208–210, 213, 214, 216, 218–222, 224, 226–231, 233, 235–238, 242–250**.
남길 행 11개(행 안에 루트 다른 곳에 없는 경고·임계값·가드가 있다): **211**(`lib/classifier.js` 신뢰도 0.6) · **212**(`lib/youtube_oauth.js` 200ms) · **215**(`migrate_library.py`) · **217**(`build_obsidian_wiki.py`) · **223**(`telegram_tips_ingest.py`) · **225**(`lib/title_fetch.py`) · **232**(`lib/wiki_search.js`) · **234**(`build_search_index.py`) · **239**(`recategorize_tips.py`) · **240**(`retitle_tips.py`) · **241**(`lib/library_schema.sql`·`library_db.py`).

표 머리 2줄(206·207) 은 루트에 그대로 두고, 표 머리 **위**에 포인터 1줄 + 빈 줄:
```
→ README 「📁 파일 구조 및 역할」 이 파일 안내의 정본 · 아래는 경고·임계값·가드가 있는 행만 (경위: [배경 §핵심 파일 역할](docs/claude_md_background.md#bg-files))
```

(행 번호가 실제와 다르면 각 행 첫 칸의 파일 이름으로 맞추되, **남길 11행·옮길 32행의 파일 이름 집합**은 이 지시서와 같아야 한다.)

## 2. `docs/claude_md_background.md`

```
# CLAUDE.md 배경 — 규칙의 경위 · 실측 · 연혁

규칙의 정본은 `CLAUDE.md` 다. 이 파일은 왜 그 규칙이 생겼는지를 남긴다. 규칙과 이 파일이 다르면 `CLAUDE.md` 를 따른다.

<a id="bg-versions"></a>
## CLAUDE.md 머리 — 버전별 한 줄 요약

(1-a 17줄, 옛 순서 그대로)

<a id="bg-files"></a>
### 핵심 파일 역할

(표 머리 2줄 사본 + 1-b 32행, 옛 순서 그대로)
```
옮긴 줄은 바이트 그대로. 스크립트(`python3 -I`, `$SCRATCH`)로 한다.

## 3. AGENTS.md 다시 만들기

지금 `AGENTS.md` 1~5행 + 새 `CLAUDE.md` 4행부터 끝. `diff <(sed -n '4,$p' CLAUDE.md) <(sed -n '6,$p' AGENTS.md)` 빈 출력.

## 4. 옛 문구 2곳 (1단계 검수 ⚠️)

| 파일 | 지금 | 바꾼 뒤 |
|---|---|---|
| `.claude/agents/scribe.md` 3행 description | `CLAUDE.md 이력 1줄` | `` `docs/claude_history.md` 이력 1줄`` |
| `.claude/agents/verifier.md` 27행 | `` `CLAUDE.md` 머리 버전·이력 1줄`` | `` `CLAUDE.md` 머리 버전 · `docs/claude_history.md` 맨 위 이력 1줄`` |

글자가 다르면 멈추고 보고. 그 밖 글 무변경(scribe 18행의 「버전 요약 인용 1줄」 규칙은 대표님 결정 대기라 그대로).

## 5. 이번 버전 기록 (v4.19.5)

- `CLAUDE.md`·README 머리 `**현재 버전: v4.19.4** (2026-11-06)` → `v4.19.5`.
- README 요약표 맨 위: `| **[v4.19.5](docs/changelog/2026-11.md#v4-19-5)** | 2026-11-06 | **🪶 CLAUDE.md 다이어트 2단계 — 경위를 docs/claude_md_background.md 로 · CC-1106-B** |`
- `docs/changelog/2026-11.md` 맨 위: 앵커 `v4-19-5` + `#### [v4.19.5] - 2026-11-06 (🪶 CLAUDE.md 다이어트 2단계 — 경위를 docs/claude_md_background.md 로 · CC-1106-B)` + `- **요약**: …` + 불릿(옮긴 줄·바이트 · 전후 크기 · 남긴 표 행 11 · 3단계 안 함(한 폴더에만 걸리는 절 0) · 에이전트 문구 2곳).
- `docs/claude_history.md` 맨 위(머리 아래): `- **2026-11-06 (v4.19.5 — CLAUDE.md 다이어트 2단계: 경위 이동)** — …` (같은 내용, 실제 값, 지시서 경로).
- README 「🔍」 2026-11 줄 · `docs/changelog/README.md` 색인 2026-11 행 갱신.

## 기준표 (ERP 이식 문서 5절)

| # | 확인 | 방법 |
|---|---|---|
| 1 | 사라진 줄 0 | `git show 34fdfd3:CLAUDE.md` 의 빈 줄 아닌 모든 줄(코드 펜스 포함)이 새 `CLAUDE.md` ∪ `docs/claude_md_background.md` ∪ `docs/claude_history.md` 에 줄 전체로 있다. 허용: 머리 버전 줄 1개(바뀐 글 확인). 역방향: 새 `CLAUDE.md` 에서 옛 파일에 없는 줄 = 포인터 2줄 + 버전 줄뿐 |
| 1b | 옮긴 줄 바이트 그대로 | background 의 1-a·1-b 부분 = 옛 해당 행들을 순서대로 이은 것과 같음 |
| 2 | 규칙 문장은 루트에 | background 로 간 줄에서 `grep -E '않는다\|말 것\|금지\|반드시\|★\|⛔\|🚨\|한다\.'` — 걸린 줄마다 루트에 같은 뜻 문장이 있는 행 번호를 대응표로(설계안 근거: 209→260·579 · 213→456 · 218→87 · 220→113 · 221→484 · 222→279·295 · 229→329·332 · 237→117 · 242→474·477 · 243→388 · 248→89 — 실제 새 행 번호로) |
| 3 | 제목 그대로 | 옛 제목(`^#{1,4} `, 코드 펜스 밖) ⊆ 새 `CLAUDE.md` 제목 |
| 링크 | 앵커 연결 | 포인터 2줄의 `#bg-versions`·`#bg-files` 가 background 에 `<a id="…">` 각 1개 |
| 5 | 크기 | `wc -c CLAUDE.md AGENTS.md` 전후 (예상 약 91,970B ± 300) |
| 6 | 회귀 · 범위 밖 0 | `scripts/run_all_tests.sh` 17/17 · `test_readme_changelog.py` 9/9 · `git status --porcelain` 범위 안만 |
| 7 | AGENTS 동기 · 공개 레포 | 3절 diff 빈 출력 · 추가된 줄에 `/Users/`·`/private/tmp/`·맥 이름·이메일 0 |

(4번 「폴더별로 읽힌다」 는 3단계 항목 — 3단계는 하지 않는다: 한 폴더에만 걸리는 절 0개 · 0B, investigator 11-06 표.)

## 하지 말 것

- 목록 밖 줄 옮기기 · 줄 쪼개기 · 요약·다듬기 · 제목 바꾸기 · 4절 밖 규칙 문장 · `.claude/hooks/`·`settings.json`·코드·장부 · 다른 저장소 · rebase/amend/force-push · `git push` · 지시서·커밋 메시지에 절대경로

## 커밋

`[CC-1106-B] v4.19.5 CLAUDE.md 다이어트 2단계 — 경위를 docs/claude_md_background.md 로 (CLAUDE.md <전>→<후> 바이트 · 사라진 줄 0 · 회귀 17/17)` + `Co-Authored-By:` 줄(실제 모델)
