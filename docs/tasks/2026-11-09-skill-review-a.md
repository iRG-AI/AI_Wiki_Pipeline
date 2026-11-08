# [CC-1109-A] 매일 Wiki 검토 1단계 — `skill_review.py` (제안 생성만, UI·예약 없음)

- 작성: pm-wiki · 2026-11-09 · 승인: 대표님 11-09 계획 승인(「매일 Wiki 검토 → 제안함 → 승인 → 스킬 설치」)
- 실행: implementer · 검수: verifier
- 이 단계 목적: 실제 데이터로 제안 품질을 대표님이 먼저 판정한다. 제안함 UI(B)·launchd(C)는 다음 지시서.

## 배경

장부에 매일 영상 4~19편·꿀팁이 들어온다. 그날 들어온 것만 Claude 가 읽고 "대표님께 실제로 쓸모 있는" 스킬·적용 아이디어를 하루 0~3건 제안한다.
Claude 에게 **도구를 주지 않는다** — 장부 읽기·파일 쓰기는 스크립트가 하고, Claude 는 프롬프트를 받아 JSON 만 돌려준다.

## 범위

- 만들 것: `<REPO_ROOT>/skill_review.py`, `<REPO_ROOT>/scripts/test_skill_review.py`
- 쓰는 곳: `<REPO_ROOT>/data/proposals/` (없으면 만든다 — `data/` 는 gitignore. `git check-ignore -q data/proposals/x.json` 확인)
- 읽기만: 장부 `data/library.db`(반드시 읽기 전용), `data/review_profile.md`(PM 이 만들어 둠), `~/.claude/skills/` 의 폴더 이름
- 바꾸면 안 되는 것: 다른 모든 파일 · 장부 · `.env` · launchd · `scripts/run_all_tests.sh`(C 단계에서 추가) · README/CLAUDE.md(C 단계) · 커밋·push

## 동작 (`skill_review.py`)

1. **장부 열기**: `lib/library_db.open_existing(readonly=True)`. 실패하면 RESULT_JSON `ok:false` 로 끝(exit 1).
2. **기준점(through)**: `data/proposals/` 의 `YYYYMMDD.json` 중 가장 최근 파일의 `through`(ISO UTC). 없으면 지금 − 1일.
   `--days=N` 이면 시작 = 지금 − N일이고 결과를 `data/proposals/trial/<YYYYMMDD-HHMMSS>.json` 에 쓴다(실제 기준점을 움직이지 않음).
3. **대상 선정** (`created_at > through` — `summarized_at` 은 재요약 때도 바뀌므로 쓰지 않는다):
   - videos: `grade` 가 `'exclude'` 가 아닌 행(NULL 포함). `record_id, title, channel, topics, video_url, summary_src, summary` — 요약은 2,500자로 자른다. 최대 40편(최신순), 넘으면 잘린 수를 결과에 기록.
   - tips: `record_id, title, url, category, tags, memo`. 최대 40건.
   - 둘 다 0건이면 Claude 호출 없이 `proposals: []` 로 정상 종료(파일은 쓴다 — 기준점 이동).
4. **맥락**: 프로필 전문, 설치된 스킬 이름 목록(`~/.claude/skills/` 1단계 폴더 이름 + `synced/*/` 아래 폴더 이름 — 이름만, 내용 읽지 않음), 최근 7일 `data/proposals/*.json` 의 제안 제목 + `data/proposals/decisions.json`(있으면)의 거절 사유. 환경변수 `SKILL_REVIEW_SKILLS_DIR` 로 스킬 폴더를 바꿀 수 있게(테스트용).
5. **프롬프트**(한국어): 역할 · 프로필 · 대상 목록(각 항목에 `record_id`) · 규칙:
   - 제안 0~3건. 억지로 채우지 말 것("오늘은 없음" 정상). 판매·일반론·뉴스 제외. 설치된 스킬·최근 제안/거절과 겹치면 제외.
   - `evidence` 는 위 목록의 `record_id` 만, 1개 이상.
   - `kind: "skill"` 이면 `skill.slug`(`^[a-z0-9-]{3,40}$`, 접두 없이)와 `skill.skill_md`(완전한 SKILL.md — 프론트매터 `name: wiki-<slug>` · `description:`(언제 쓰는지 · 호출 문구 포함), 본문 한국어 절차). 비밀값·개인 경로 넣지 말 것.
   - `kind: "action"` 이면 `action_prompt`(대표님이 Claude Code 에 그대로 붙여 넣을 지시 한 단락).
6. **호출**: `subprocess.run([CLAUDE_BIN, '-p', '--model', 'opus', '--output-format', 'json', '--json-schema', <스키마 JSON>, '--tools', '', '--strict-mcp-config', '--no-session-persistence'], input=prompt, cwd=<빈 임시 폴더>, timeout=900)`.
   - `CLAUDE_BIN` = 환경변수 `CLAUDE_BIN` 또는 `~/.local/bin/claude`(launchd PATH 에 없음).
   - **재시도하지 않는다**(하루 1회 호출. 실패는 기록하고 끝 — 다음 날 같은 기준점에서 다시 본다).
   - `--bare` 는 쓰지 않는다(OAuth 구독 인증을 읽지 않는다).
   - 먼저 짧은 프롬프트로 1회 실호출해 출력 JSON 의 모양(구조화 결과가 `structured_output` 인지 `result` 문자열인지)을 확인하고 그대로 파싱한다. 확인 결과를 보고에 적는다.
7. **검증**: 스키마 밖 · `evidence` 가 비었거나 대상 밖 id · slug 정규식 위반 · `skill_md` 가 `---` 프론트매터로 시작하지 않거나 `name: wiki-<slug>` 불일치 · `kind` 별 필수 필드 없음 → 그 제안만 버리고 `dropped` 에 사유. 3건 초과분 버림.
   각 제안에 `id` = `<YYYYMMDD>-<n>`(trial 은 `trial-<YYYYMMDD-HHMMSS>-<n>`), `status: "new"`.
8. **저장**: tmp 파일 → `os.replace`. 내용 `{version:1, created_at, through(대상 중 created_at 최댓값, 대상 0이면 지금), window:{from,to}, considered:{videos,tips,truncated}, model, proposals:[…], dropped:[…], note}`.
   같은 날 파일이 이미 있으면 덮지 않고 `ok:false, error:"exists"`(같은 날 두 번 돌리면 멈춤).
9. **출력**: 마지막 줄 `RESULT_JSON {ok, considered_videos, considered_tips, proposals, dropped, file, error}`. 종료 0 · 1.
10. `--dry-run`: 1~5 까지 하고 대상 건수·프롬프트 글자 수를 찍는다. **Claude 호출 0 · 파일 쓰기 0.**

스키마 JSON(`--json-schema` 로 넘김):
`{"type":"object","required":["proposals"],"properties":{"proposals":{"type":"array","maxItems":3,"items":{"type":"object","required":["kind","area","title","why","evidence","effort"],"properties":{"kind":{"enum":["skill","action"]},"area":{"enum":["dev","work","knowledge","content"]},"title":{"type":"string"},"why":{"type":"string"},"evidence":{"type":"array","items":{"type":"string"},"minItems":1},"effort":{"enum":["낮음","중간","높음"]},"skill":{"type":"object","properties":{"slug":{"type":"string"},"skill_md":{"type":"string"}}},"action_prompt":{"type":"string"}}}},"note":{"type":"string"}}}`

## 테스트 `scripts/test_skill_review.py` (네트워크 0 · 실제 장부·스킬 폴더 무관)

임시 장부(`lib/library_schema.sql` 로 생성) · 임시 `data/proposals` · 임시 스킬 폴더 · 가짜 `claude` 실행 파일(`CLAUDE_BIN`, 미리 정한 JSON 을 출력하고 호출 표시 파일을 남김). 경로는 환경변수나 인자로 주입한다(필요하면 `--db=`·`--out-dir=`·`--profile=` 옵션을 테스트 전용으로 둔다).
최소 확인: ① `created_at > through` 만·`exclude` 제외 ② 대상 0 → 호출 0 · 파일 씀 ③ 깨진 JSON → `ok:false` · 파일 없음 ④ evidence 없음/대상 밖/slug 위반/name 불일치 제안만 버림 ⑤ through 가 대상 created_at 최댓값 ⑥ `--dry-run` 호출 0 · 파일 0 ⑦ `--days` 는 trial 폴더 · 다음 실행 기준점 불변 ⑧ 같은 날 두 번 → exists ⑨ 장부 파일 sha256 실행 전후 동일.

## 실데이터 시험 (테스트 통과 뒤)

1. `/opt/homebrew/bin/python3 skill_review.py --dry-run --days=7` → 대상 건수가 `sqlite3 "file:data/library.db?mode=ro" "select count(*) from videos where created_at > strftime('%Y-%m-%dT%H:%M:%fZ','now','-7 days') and coalesce(grade,'')<>'exclude'"` 와 같은지(최대 40 상한 고려).
2. `/opt/homebrew/bin/python3 skill_review.py --days=7` 1회 → trial 파일 경로와 RESULT_JSON 을 보고. 제안 본문은 PM 이 파일에서 읽는다(보고에 전문을 옮기지 않아도 됨).

## 기준표

| # | 기준 | 판정 근거 |
|---|---|---|
| 1 | 테스트 ①~⑨ 통과 | `test_skill_review.py` 출력 N/N |
| 2 | 장부는 읽기 전용으로만 연다 | 코드 `readonly=True` · 테스트 ⑨ |
| 3 | Claude 호출에 도구 0 · MCP 0 · 재시도 0 | 코드의 인자 목록 · 호출 1곳 |
| 4 | dry-run 호출 0 · 쓰기 0 | 테스트 ⑥ |
| 5 | 출력 JSON 모양 실측 결과 보고 | implementer 보고 |
| 6 | 실데이터 dry-run 건수 = sqlite 집계 | 시험 1 |
| 7 | 실데이터 1회 → trial 파일 생성, RESULT_JSON `ok:true` | 시험 2 |
| 8 | 범위 밖 변경 0 · 커밋 0 | `git status --porcelain` = 새 파일 2개 + 이 지시서 + 기존 `?? docs/tasks/2026-11-08-video-daily-seconds-trial.md` |
| 9 | 보고·로그에 `.env` 값·토큰 노출 없음 | implementer 보고 |

## 하지 말 것
- 장부 쓰기 · `~/.claude/skills/` 쓰기 · 텔레그램 발송 · launchd · 커밋·push · Claude 호출 반복(실데이터 시험은 짧은 모양 확인 1회 + 본 시험 1회까지).
