# [CC-1101-B] 등급 되돌림 1건 — `0Ef6MaFg6b0` exclude → keep (장부 값만)

- 작성: 2026-11-01 · pm-wiki (XP-1101-B 작업 1)
- 실행: `implementer`(Sonnet · medium) → 검수 `verifier`(Opus · high)
- 승인 범위: 장부 `data/library.db` 의 `videos` 1행 조건부 UPDATE(쓰기 전 백업) · 이 지시서 커밋 1건. **`git push` 는 별도 승인.**
- 코드·스키마·`.env`·launchd·Vault·시트 무변경 — 노트 프론트매터·시트·검색 인덱스는 다음 정시 실행이 `updated_at` 을 보고 맞춘다.
- 방식은 `[CC-1101-A]`(`docs/tasks/2026-11-01-grade-revert-2.md`)와 같다. 그 지시서의 4-4 쿼리(`$.signals`)는 틀렸다 — `quality` 신호는 최상위 키다. 이 지시서는 고친 꼴을 쓴다.

## 배경

- 11-01 00:08 재요약(3.5 Flash-Lite)에서 `0Ef6MaFg6b0` 「대한항공 마일리지 빈좌석 찾기 프로그램 무료 공유」(바이브코더 채널)가 `ai_related=false` → exclude(`why ["not_ai"]`). 본론은 직접 만든 조회 툴(GitHub·Playwright) 시연·무료 공유와 "AI 에이전트나 Codex 로 클론·실행" 안내, 토픽 분류 `AI 바이브코딩 · AI 여행계획`.
- 대표님 결정 11-01 08:49(XP-1101-B): keep. not_ai 경계선 4건째 — 규칙 개선(v4.17)은 별도 지시서.

## 범위

- 바꿀 것: `data/library.db` `videos` 의 위 1행(`grade`·`quality`·`updated_at`) · 이 지시서 커밋
- 바꾸면 안 되는 것: 코드 · 문서(README·CLAUDE.md·AGENTS.md — 데이터 값만 바뀌므로 갱신 대상 아님) · 다른 장부 행 · `wiki_extract` · Vault 파일 · 시트 · `sync_obsidian.py`·`sheet_mirror.py` 는 `--dry-run` 으로만

## 확인(먼저) — 하나라도 다르면 멈추고 보고

PM 이 11-01 08:52 에 실제 장부에서 본 값이다.

| # | 명령 | 기대값 |
|---|---|---|
| 0-1 | `git log --oneline -1` | `12eb52a [CC-1101-A] …` |
| 0-2 | `git status --porcelain -uall` | `?? docs/tasks/2026-11-01-grade-revert-3.md` 한 줄 (v4.17 지시서가 함께 있으면 그 줄도 — 건드리지 말 것) |
| 0-3 | `sqlite3 "file:data/library.db?mode=ro" "select video_id, grade, summary_src, updated_at, json_extract(quality,'\$.manual_grade') is null, json_extract(quality,'\$.why') from videos where video_id='0Ef6MaFg6b0'"` | `0Ef6MaFg6b0\|exclude\|video\|2026-10-31T15:08:36.716Z\|1\|["not_ai"]` |
| 0-4 | `sqlite3 "file:data/library.db?mode=ro" "select count(*) from videos"` | `3200` (정시 실행이 끼면 늘 수 있다 — 값을 적어 보고하고 그 값을 기준으로) |
| 0-5 | `/opt/homebrew/bin/python3 sheet_mirror.py --dry-run \| tail -1` | `videos_sent: 0` · `tips_sent: 0` (다르면 숫자를 적어 보고 — 아래 기대값에 더한다) |
| 0-6 | `/opt/homebrew/bin/python3 sync_obsidian.py --dry-run \| grep RESULT_JSON` | `refreshed: 0` · `refresh_skipped: 0` · `added: 0` (다르면 0-5 와 같이) |
| 0-7 | `ls data/library.db.bak.manual-20261101b` | 없음 |

## 단계

### 1. 시간 창·실행 중 확인

조건(둘 다): 분이 21~49 · `pgrep -f "scheduler.js|wiki_ingest.py|sync_obsidian.py"` 출력 없음. 11:50~12:20 은 정시 실행 창이다. 아니면 멈추고 보고(PM 이 기다렸다가 이어 붙인다 — 워커는 foreground sleep 이 막힌다).

### 2. 백업 (온라인 백업 API — `cp` 금지)

```bash
sqlite3 data/library.db ".backup data/library.db.bak.manual-20261101b"
sqlite3 "file:data/library.db.bak.manual-20261101b?mode=ro" "pragma integrity_check; select count(*) from videos"
```
→ `ok` · 0-4 값과 같음. 파일이 이미 있으면 덮지 말고 `…-20261101c` 로.

### 3. 조건부 UPDATE

```bash
sqlite3 data/library.db "
UPDATE videos SET grade='keep',
  quality=json_set(quality,'\$.manual_grade','keep: 바이브코더가 AI 에이전트·Codex 로 만든 툴의 시연·공유, not_ai 경계선 (대표님 결정 11-01)'),
  updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')
WHERE video_id='0Ef6MaFg6b0' AND grade='exclude' AND summary_src='video';
SELECT changes();"
```
→ `1`. `0` 이면 멈추고 보고. `quality` 의 다른 키는 그대로 남아야 한다.

### 4. 사후 확인 (전부 읽기만)

| # | 명령 | 기대값 |
|---|---|---|
| 4-1 | `sqlite3 "file:data/library.db?mode=ro" "select grade, summary_src, updated_at, json_extract(quality,'\$.manual_grade') from videos where video_id='0Ef6MaFg6b0'"` | `keep` · `video` · `updated_at` 이 지금 시각(UTC) · manual_grade 위 문구 |
| 4-2 | `sqlite3 "file:data/library.db?mode=ro" "pragma integrity_check"` | `ok` |
| 4-3 | `sqlite3 "file:data/library.db?mode=ro" "select count(*) from videos"` | 백업 행 수와 같음 |
| 4-4 | `sqlite3 "file:data/library.db?mode=ro" "select (json_type(quality,'\$.promo_main') is null) + (json_type(quality,'\$.ai_related') is null) + (json_type(quality,'\$.model') is null) from videos where video_id='0Ef6MaFg6b0'"` | `0` (신호 보존) |
| 4-5 | 백업과 현재의 `quality` 키 비교: `for d in data/library.db.bak.manual-20261101b data/library.db; do sqlite3 "file:$d?mode=ro" "select group_concat(key) from (select key from json_each((select quality from videos where video_id='0Ef6MaFg6b0')) order by key)"; done` | 두 줄 차이는 `manual_grade` 하나 |
| 4-6 | `/opt/homebrew/bin/python3 scripts/verify_library.py \| grep RESULT_JSON` | `ok: true` · `vault_missing 0` · `tips_missing 0` |
| 4-7 | `/opt/homebrew/bin/python3 sync_obsidian.py --dry-run \| grep RESULT_JSON` | `refreshed: 1` (0-6 값 + 1) · `refresh_skipped: 0` |
| 4-8 | `/opt/homebrew/bin/python3 sheet_mirror.py --dry-run \| tail -1` | `videos_sent: 1` (0-5 값 + 1) · `tips_sent: 0` |

### 5. 커밋

```bash
git add docs/tasks/2026-11-01-grade-revert-3.md
git commit -m "[CC-1101-B] 등급 되돌림 1건 0Ef6MaFg6b0 exclude → keep (장부 값만, 코드 무변경)"
```
이 지시서 파일만 add 한다(다른 untracked 지시서가 있어도 넣지 않는다). `data/` 가 보이면 멈추고 보고.

## 기준표

| # | 기준 |
|---|---|
| 1 | 0-1~0-7 기대값 일치(또는 다른 값을 보고하고 기대값을 그만큼 옮김) |
| 2 | 장부 쓰기가 분 21~49 · 파이프라인 실행 없음에서 이루어짐(시각 보고) |
| 3 | 백업 `data/library.db.bak.manual-20261101b` 존재 · integrity ok · 행 수 같음 |
| 4 | UPDATE `changes()` = 1 |
| 5 | 4-1~4-8 기대값 일치 |
| 6 | 이 행 밖의 장부 변경 없음(행 수 같음 · 0-5/4-8 차이 = 1) |
| 7 | 커밋 1건, 변경 파일은 이 지시서 하나 · `data/` 미포함 · push 안 함 |
| 8 | `sync_obsidian.py`·`sheet_mirror.py` 는 `--dry-run` 으로만 실행 |

## 하지 말 것

- 이 `video_id` 밖의 행 수정, `wiki_extract` 수정, 등급 규칙 코드·프롬프트 수정
- `cp` 로 장부 백업, 장부 새로 만들기·삭제
- `sync_obsidian.py`·`sheet_mirror.py` 를 dry-run 없이 실행, 시트 `--full`
- `git push`

## 롤백

```bash
# 시간 창 밖·파이프라인 실행 없음에서
sqlite3 data/library.db "UPDATE videos SET grade='exclude', quality=json_remove(quality,'\$.manual_grade'), updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE video_id='0Ef6MaFg6b0' AND grade='keep'; SELECT changes();"
```
→ `1`. 통째 복원이 필요하면 README 「장부 백업」 절차로 `data/library.db.bak.manual-20261101b`.

## 범위 밖

- 다음 정시 실행 뒤 노트 `grade: keep` · 시트 영상 1행 · 검색 인덱스 포함 — CW 판정.
- not_ai 규칙 좁히기(v4.17) — 별도 지시서.
