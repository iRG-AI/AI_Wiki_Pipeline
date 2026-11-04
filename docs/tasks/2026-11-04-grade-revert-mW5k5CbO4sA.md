# [CC-1104-C] 등급 되돌림 1건 — `mW5k5CbO4sA` keep → exclude (장부 값만)

- 작성: 2026-11-04 12:41 · pm-wiki (v4.17 관찰 판정 뒤속)
- 실행: `implementer`(Sonnet · medium) → 검수 `verifier`(Opus · high)
- 승인 범위: 장부 `data/library.db` 의 `videos` 1행 조건부 UPDATE(쓰기 전 백업) · 이 지시서 커밋 1건. push 는 PM 이 검수 뒤 한다(11-04~ 승인 없이).
- 코드·스키마·`.env`·launchd·Vault·시트 무변경 — 노트 프론트매터·시트·검색 인덱스는 다음 정시 실행이 `updated_at` 을 보고 맞춘다.
- 방식은 `[CC-1101-B]`(`docs/tasks/2026-11-01-grade-revert-3.md`)와 같고 방향만 반대다.

## 배경

- 11-03 18:02 재요약(3.5 Flash-Lite)에서 `mW5k5CbO4sA` 「AI 데이터 활용 {2-1}」이 `ai_related=false` 였지만, 장부 토픽(`AI 보안 · AI 트렌드 · AI 생산성 향상 · AI 자동화`)이 있어 v4.17 규칙대로 keep(`not_ai_minor`)이 됐다.
- 실제 내용은 파이썬 문자열 처리 기초 강의다(신호 reason). 장부 토픽은 예전에 제목·설명란으로 분류한 값이라 오해를 부르는 제목에 끌려갔다.
- 대표님 결정 11-04 12:4x: exclude 로 되돌린다. 규칙(v4.17)은 그대로 둔다.

## 범위

- 바꿀 것: `data/library.db` `videos` 의 위 1행(`grade`·`quality`·`updated_at`) · 이 지시서 커밋
- 바꾸면 안 되는 것: 코드 · 문서(README·CLAUDE.md·AGENTS.md) · 다른 장부 행 · `topics` · `wiki_extract` · Vault 파일 · 시트 · `sync_obsidian.py`·`sheet_mirror.py` 는 `--dry-run` 으로만

## 확인(먼저) — 하나라도 다르면 멈추고 보고

PM 이 11-04 12:40 에 실제 장부에서 본 값이다.

| # | 명령 | 기대값 |
|---|---|---|
| 0-1 | `git log --oneline -1` | `9af1514 [PM-1104] …` |
| 0-2 | `git status --porcelain -uall` | `?? docs/tasks/2026-11-04-grade-revert-mW5k5CbO4sA.md` 한 줄 |
| 0-3 | `sqlite3 "file:data/library.db?mode=ro" "select video_id, grade, summary_src, updated_at, json_extract(quality,'\$.manual_grade') is null, json_extract(quality,'\$.why') from videos where video_id='mW5k5CbO4sA'"` | `mW5k5CbO4sA\|keep\|video\|2026-11-03T09:02:24.354Z\|1\|[]` |
| 0-4 | `sqlite3 "file:data/library.db?mode=ro" "select count(*) from videos"` | `3243` (정시 실행이 끼면 늘 수 있다 — 값을 적어 보고하고 그 값을 기준으로) |
| 0-5 | `/opt/homebrew/bin/python3 sheet_mirror.py --dry-run \| tail -1` | `videos_sent: 0` · `tips_sent: 5` (12:33 꿀팁 보정분 — 다르면 숫자를 적어 보고하고 아래 기대값에 더한다) |
| 0-6 | `/opt/homebrew/bin/python3 sync_obsidian.py --dry-run \| grep RESULT_JSON` | `refreshed: 0` · `refresh_skipped: 0` · `tips_added: 1` (다르면 0-5 와 같이) |
| 0-7 | `ls data/library.db.bak.manual-20261104c` | 없음 |

## 단계

### 1. 시간 창·실행 중 확인

조건(둘 다): 분이 21~49 · `pgrep -f "scheduler.js|wiki_ingest.py|sync_obsidian.py"` 출력 없음. 아니면 멈추고 보고(PM 이 기다렸다가 이어 붙인다 — 워커는 foreground sleep 이 막힌다). 17:25~17:50 은 wiki-ingest 창이다.

### 2. 백업 (온라인 백업 API — `cp` 금지)

```bash
sqlite3 data/library.db ".backup data/library.db.bak.manual-20261104c"
sqlite3 "file:data/library.db.bak.manual-20261104c?mode=ro" "pragma integrity_check; select count(*) from videos"
```
→ `ok` · 0-4 값과 같음. 파일이 이미 있으면 덮지 말고 `…-20261104d` 로.

### 3. 조건부 UPDATE

```bash
sqlite3 data/library.db "
UPDATE videos SET grade='exclude',
  quality=json_set(quality,'\$.manual_grade','exclude: 파이썬 문자열 기초 강의, AI 무관 — 장부 토픽은 옛 제목 기반 분류 (v4.17 not_ai_minor 오판, 대표님 결정 11-04)'),
  updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')
WHERE video_id='mW5k5CbO4sA' AND grade='keep' AND summary_src='video';
SELECT changes();"
```
→ `1`. `0` 이면 멈추고 보고. `quality` 의 다른 키는 그대로 남아야 한다.

### 4. 사후 확인 (전부 읽기만)

| # | 명령 | 기대값 |
|---|---|---|
| 4-1 | `sqlite3 "file:data/library.db?mode=ro" "select grade, summary_src, updated_at, json_extract(quality,'\$.manual_grade') from videos where video_id='mW5k5CbO4sA'"` | `exclude` · `video` · `updated_at` 이 지금 시각(UTC) · manual_grade 위 문구 |
| 4-2 | `sqlite3 "file:data/library.db?mode=ro" "pragma integrity_check"` | `ok` |
| 4-3 | `sqlite3 "file:data/library.db?mode=ro" "select count(*) from videos"` | 백업 행 수와 같음 |
| 4-4 | `sqlite3 "file:data/library.db?mode=ro" "select (json_type(quality,'\$.promo_main') is null) + (json_type(quality,'\$.ai_related') is null) + (json_type(quality,'\$.model') is null) from videos where video_id='mW5k5CbO4sA'"` | `0` (신호 보존) |
| 4-5 | 백업과 현재의 `quality` 키 비교: `for d in data/library.db.bak.manual-20261104c data/library.db; do sqlite3 "file:$d?mode=ro" "select group_concat(key) from (select key from json_each((select quality from videos where video_id='mW5k5CbO4sA')) order by key)"; done` | 두 줄 차이는 `manual_grade` 하나 |
| 4-6 | `/opt/homebrew/bin/python3 scripts/verify_library.py \| grep RESULT_JSON` | `ok: true` · `vault_missing 0` · `tips_missing 0` |
| 4-7 | `/opt/homebrew/bin/python3 sync_obsidian.py --dry-run \| grep RESULT_JSON` | `refreshed: 1` (0-6 값 + 1) · `refresh_skipped: 0` |
| 4-8 | `/opt/homebrew/bin/python3 sheet_mirror.py --dry-run \| tail -1` | `videos_sent: 1` (0-5 값 + 1) · `tips_sent` 는 0-5 그대로 |

### 5. 커밋

```bash
git add docs/tasks/2026-11-04-grade-revert-mW5k5CbO4sA.md
git commit -m "[CC-1104-C] 등급 되돌림 1건 mW5k5CbO4sA keep → exclude (장부 값만, 코드 무변경)"
```
이 지시서 파일만 add 한다. `data/` 가 보이면 멈추고 보고.

## 기준표

| # | 기준 |
|---|---|
| 1 | 0-1~0-7 기대값 일치(또는 다른 값을 보고하고 기대값을 그만큼 옮김) |
| 2 | 장부 쓰기가 분 21~49 · 파이프라인 실행 없음에서 이루어짐(시각 보고) |
| 3 | 백업 `data/library.db.bak.manual-20261104c` 존재 · integrity ok · 행 수 같음 |
| 4 | UPDATE `changes()` = 1 |
| 5 | 4-1~4-8 기대값 일치 |
| 6 | 이 행 밖의 장부 변경 없음(행 수 같음 · 0-5/4-8 영상 차이 = 1) |
| 7 | 커밋 1건, 변경 파일은 이 지시서 하나 · `data/` 미포함 · push 안 함 |
| 8 | `sync_obsidian.py`·`sheet_mirror.py` 는 `--dry-run` 으로만 실행 |

## 하지 말 것

- 이 `video_id` 밖의 행 수정, `topics`·`wiki_extract` 수정, 등급 규칙 코드·프롬프트 수정
- `cp` 로 장부 백업, 장부 새로 만들기·삭제
- `sync_obsidian.py`·`sheet_mirror.py` 를 dry-run 없이 실행, 시트 `--full`
- `git push`

## 롤백

```bash
# 시간 창 밖·파이프라인 실행 없음에서
sqlite3 data/library.db "UPDATE videos SET grade='keep', quality=json_remove(quality,'\$.manual_grade'), updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE video_id='mW5k5CbO4sA' AND grade='exclude'; SELECT changes();"
```
→ `1`. 통째 복원이 필요하면 README 「장부 백업」 절차로 `data/library.db.bak.manual-20261104c`.

## 범위 밖

- 다음 정시 실행 뒤 노트 `grade: exclude` · 시트 영상 1행 · 검색 인덱스에서 빠짐 — 18:20 이후 PM 확인.
- 재요약이 장부 토픽(옛 분류) 대신 새로 분류하게 하는 규칙 변경 — 같은 오판이 반복되면 별도 지시서.
