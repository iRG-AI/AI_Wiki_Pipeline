# [CC-1101-A] 등급 되돌림 2건 — `3729clHFDjU` · `VoqXu3oFsk4` exclude → keep (장부 값만)

- 작성: 2026-11-01 · pm-wiki
- 실행: `implementer`(Sonnet · medium) → 검수 `verifier`(Opus · high)
- 승인 범위: 장부 `data/library.db` 의 `videos` 2행 조건부 UPDATE(쓰기 전 백업) · 이 지시서 커밋 1건. **`git push` 는 별도 승인.**
- 코드·스키마·`.env`·launchd·Vault·시트 무변경 — 노트 프론트매터와 시트는 다음 정시 실행(`sync_obsidian`·`sheet_mirror`)이 `updated_at` 을 보고 맞춘다.

## 배경

- 10-31 CW 가 새 exclude 4건을 물었고, 대표님이 11-01 CW 의견대로 결정했다: `TzDlXg8Cg8o`·`Hkpy69D1m-8` 은 제외 유지, 아래 2건은 keep.
  - `3729clHFDjU` 「매일 사용하는 5가지 오픈소스 (feat. 에이전트)」 — promo_main · share 0.08 · subject 로 제외됐으나 본론은 오픈소스 도구 정보, 자기 강의 쿠폰은 곁다리(`vPzM2ix4ApM` 유형). promo 오판.
  - `VoqXu3oFsk4` 「바이브코딩 하다 AWS 요금 폭탄 맞으신 분?」 — not_ai 로 제외됐으나 바이브코더 대상 개발 운영 정보. not_ai 경계선(앞 `r98qvQYlrMc`·`5k0tCrXdIIM` 에 이어 3건째).
- 방식은 지난 수동 되돌림(`5k0tCrXdIIM`·`wgrpasYyiIQ` 등)과 같다: `grade='keep'` + `quality.manual_grade` 에 사유 + `updated_at` 새로 찍기. v4.6-b 부터 장부 `grade` 만 고치면 노트가 따라온다.

## 범위

- 바꿀 것: `data/library.db` `videos` 의 위 2행(`grade`·`quality`·`updated_at`) · 이 지시서 커밋
- 바꾸면 안 되는 것: 코드 · 문서(README·CLAUDE.md·AGENTS.md — 데이터 값만 바뀌므로 갱신 대상 아님) · 다른 장부 행 · `wiki_extract` · Vault 파일 · 시트(`sheet_mirror.py` 를 dry-run 없이 돌리지 말 것) · `sync_obsidian.py` 를 dry-run 없이 돌리지 말 것

## 확인(먼저) — 하나라도 다르면 멈추고 보고

PM 이 11-01 00:48 에 실제 장부에서 본 값이다.

| # | 명령 | 기대값 |
|---|---|---|
| 0-1 | `git log --oneline -1` | `c40374e [CC-1031-B] …` |
| 0-2 | `git status --porcelain -uall` | `?? docs/tasks/2026-11-01-grade-revert-2.md` 한 줄 |
| 0-3 | `sqlite3 "file:data/library.db?mode=ro" "select video_id, grade, summary_src, updated_at, json_extract(quality,'\$.manual_grade') is null from videos where video_id in ('3729clHFDjU','VoqXu3oFsk4') order by 1"` | `3729clHFDjU\|exclude\|video\|2026-10-27T03:03:09.832Z\|1` · `VoqXu3oFsk4\|exclude\|video\|2026-10-20T09:05:04.851Z\|1` |
| 0-4 | `/opt/homebrew/bin/python3 sheet_mirror.py --dry-run \| tail -1` | `videos_sent: 0` · `tips_sent: 0` (다르면 숫자를 적어 보고 — 다른 변경분이 있으면 아래 기대값에 더한다) |
| 0-5 | `/opt/homebrew/bin/python3 sync_obsidian.py --dry-run \| grep RESULT_JSON` | `refreshed: 0` · `refresh_skipped: 0` · `added: 0` (다르면 0-4 와 같이) |

## 단계

### 1. 시간 창·실행 중 확인

조건(둘 다): 분이 21~49 · `pgrep -f "scheduler.js|wiki_ingest.py|sync_obsidian.py"` 출력 없음. 아니면 멈추고 보고(PM 이 기다렸다가 이어 붙인다 — 워커는 foreground sleep 이 막힌다).

### 2. 백업 (온라인 백업 API — `cp` 금지)

```bash
sqlite3 data/library.db ".backup data/library.db.bak.manual-20261101"
sqlite3 "file:data/library.db.bak.manual-20261101?mode=ro" "pragma integrity_check; select count(*) from videos"
```
→ `ok` · 0-3 시점 videos 행 수와 같음. 파일이 이미 있으면 덮지 말고 `…-20261101b` 로.

### 3. 조건부 UPDATE (한 번에 한 행, 행마다 `changes()` = 1)

```bash
sqlite3 data/library.db "
UPDATE videos SET grade='keep',
  quality=json_set(quality,'\$.manual_grade','keep: 본론은 오픈소스 도구 정보, 자기 강의 쿠폰은 곁다리 — promo_main 오판 (대표님 결정 11-01)'),
  updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')
WHERE video_id='3729clHFDjU' AND grade='exclude' AND summary_src='video';
SELECT changes();"
sqlite3 data/library.db "
UPDATE videos SET grade='keep',
  quality=json_set(quality,'\$.manual_grade','keep: 바이브코더 대상 클라우드 비용·운영 정보, not_ai 경계선 (대표님 결정 11-01)'),
  updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')
WHERE video_id='VoqXu3oFsk4' AND grade='exclude' AND summary_src='video';
SELECT changes();"
```
→ 각각 `1`. `0` 이면 멈추고 보고(되돌릴 것 없음 — 조건이 안 맞은 것). `quality` 의 다른 키(signals·model 등)는 그대로 남아야 한다.

### 4. 사후 확인 (전부 읽기만)

| # | 명령 | 기대값 |
|---|---|---|
| 4-1 | 0-3 명령에서 `is null` 을 빼고 `json_extract(quality,'$.manual_grade')` 로 | 두 행 `keep` · `video` · `updated_at` 이 11-01(UTC 10-31T15~ 또는 11-01) 지금 시각 · manual_grade 위 문구 |
| 4-2 | `sqlite3 "file:data/library.db?mode=ro" "pragma integrity_check"` | `ok` |
| 4-3 | `sqlite3 "file:data/library.db?mode=ro" "select count(*) from videos"` | 2단계 백업 행 수와 같음 |
| 4-4 | `sqlite3 "file:data/library.db?mode=ro" "select count(*) from videos where json_extract(quality,'\$.signals') is null and video_id in ('3729clHFDjU','VoqXu3oFsk4')"` | `0` (신호 보존) |
| 4-5 | `/opt/homebrew/bin/python3 scripts/verify_library.py \| tail -1` | `ok: true` · `vault_missing 0` · `tips_missing 0` |
| 4-6 | `/opt/homebrew/bin/python3 sync_obsidian.py --dry-run \| grep RESULT_JSON` | `refreshed: 2` (0-5 값 + 2) · `refresh_skipped: 0` |
| 4-7 | `/opt/homebrew/bin/python3 sheet_mirror.py --dry-run \| tail -1` | `videos_sent: 2` (0-4 값 + 2) · `tips_sent: 0` |

### 5. 커밋

```bash
git add docs/tasks/2026-11-01-grade-revert-2.md
git commit -m "[CC-1101-A] 등급 되돌림 2건 3729clHFDjU·VoqXu3oFsk4 exclude → keep (장부 값만, 코드 무변경)"
```
`data/` 는 gitignore — `git status --porcelain` 에 `data/` 가 보이면 멈추고 보고.

## 기준표

| # | 기준 |
|---|---|
| 1 | 0-1~0-5 기대값 일치(또는 다른 값을 보고하고 기대값을 그만큼 옮김) |
| 2 | 장부 쓰기가 분 21~49 · 파이프라인 실행 없음에서 이루어짐(시각 보고) |
| 3 | 백업 `data/library.db.bak.manual-20261101` 존재 · integrity ok · 행 수 같음 |
| 4 | UPDATE 2건 각각 `changes()` = 1 |
| 5 | 4-1~4-7 기대값 일치 |
| 6 | 이 두 행 밖의 장부 변경 없음(videos 행 수 같음 · 0-4/4-7 차이 = 2) |
| 7 | 커밋 1건, 변경 파일은 이 지시서 하나 · `data/` 미포함 · push 안 함 |
| 8 | `sync_obsidian.py`·`sheet_mirror.py` 는 `--dry-run` 으로만 실행 |

## 하지 말 것

- 위 두 `video_id` 밖의 행 수정, `wiki_extract` 수정, 등급 규칙 코드·프롬프트 수정
- `cp` 로 장부 백업, 장부 새로 만들기·삭제
- `sync_obsidian.py`·`sheet_mirror.py` 를 dry-run 없이 실행, 시트 `--full`
- `git push`

## 롤백

```bash
# 시간 창 밖·파이프라인 실행 없음에서
sqlite3 data/library.db "UPDATE videos SET grade='exclude', quality=json_remove(quality,'\$.manual_grade'), updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE video_id IN ('3729clHFDjU','VoqXu3oFsk4') AND grade='keep'; SELECT changes();"
```
→ `2`. 다음 정시 실행이 노트·시트를 다시 맞춘다. 통째 복원이 필요하면 README 「장부 백업」 절차로 `data/library.db.bak.manual-20261101`.

## 범위 밖

- 다음 정시 실행(06시) 뒤 확인: 두 노트 프론트매터 `grade: keep` · 시트 영상 2행 갱신 · 검색 인덱스에 두 노트 포함 — CW 판정.
- 17:30 wiki-ingest 가 두 소스를 Wiki 합성 대상으로 다시 넣는지 — 관찰만.
- not_ai 경계선 3건째 → `lib/video_summary.js` 의 `ai_related` 프롬프트 문구 개선은 별도 지시서(대표님 결정 뒤).
