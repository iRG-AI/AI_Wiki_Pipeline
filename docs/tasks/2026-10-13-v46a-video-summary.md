# 작업지시서 — v4.6-a 실제 영상 요약 + 품질 필터 (신규 영상부터)

- 작성: 2026-10-13 (Cowork) · 실행: Claude Code (Sonnet 5.5) · 기준 커밋 `0e89773`(v4.5)
- 패치: `docs/tasks/2026-10-13-v46a-video-summary.patch` — sha256 `f8b37df3868e11be4986e17c464a60c8424e9338f793bf6ff246df0bc1813fd6`
- 보고는 한국어로. 기대값과 다르면 **그 단계에서 멈추고** 보고한다(다음 단계로 넘어가지 않는다).

## 1. 배경

`scheduler.js:geminiSummarize` 는 제목·채널·설명란·태그만 넣고 "정보가 부족해도 제목과 채널명으로 추론해 반드시 작성"을 시킨다. 영상을 보지 않으므로 설명란이 빈약하면 요약이 지어낸 내용이 된다.

- 10-12 시험(무료 키, 실제 영상 입력): `mW5k5CbO4sA` 「AI 데이터 활용」의 장부 요약(데이터 수집·정제·윤리)은 전부 지어낸 내용 — 실제는 VS Code 로 Python 문자열을 다루는 강의(AI 무관). 영상 입력 요약은 실제 내용을 맞혔다.
- 모델에게 A/B/C 등급을 매기게 하면 컨설팅 판매 영상에도 A 를 준다 → 모델은 사실 신호만, 등급은 코드 규칙.
- 10-13 시험: `endOffset` 600s → 마지막 장면 09:59(앞자르기 정상, 약 103토큰/초) · 일부공개 영상 403 PERMISSION_DENIED · **삭제된 영상은 200 + 영상 토큰 0 + 지어낸 답** · 20초 쇼츠·퍼가기 금지 영상 정상.
- 대표님 결정(10-12): 제외 = ① 제작자 자신의 강의·컨설팅·상품 판매가 주목적 ② 구체 정보 없는 일반론 ③ AI 무관. 유료 광고·제휴 자체는 제외 아님. 제외분은 노트를 두고 Wiki·검색에서만 뺀다.
- 사전 검증(맥 네이티브, 이 패치 그대로): 실제 영상 5건 — 강의(AI 무관) → `exclude [not_ai]`, 컨설팅 판매 → `exclude [promo_main]`, 협찬 도구 시연 → `keep`(sponsored true), 일부공개·삭제 → 영상 요청 없이 대체. 503 은 재시도로 통과.

## 2. AS-IS → TO-BE

| 항목 | AS-IS | TO-BE |
|---|---|---|
| 신규 영상 요약 | 설명란 추론(`geminiSummarize`) | 공개 영상은 Gemini 2.5 Flash 에 YouTube URL 을 영상으로(`MEDIA_RESOLUTION_LOW`, 30분 넘으면 `endOffset` 1800s), JSON `{summary_md, signals}`. 신규 모듈 `lib/video_summary.js`, 호출 자리 `processMasterIngest` 하나 |
| 등급 | 없음 | 코드 규칙 `computeGrade` — `promo_main`·`generic`·`!ai_related` 중 하나라도면 `exclude`, 아니면 `keep`. `sponsored`·`has_demo` 는 기록만 |
| 대체 | — | 비공개·일부공개·길이 모름 → 영상 요청 안 함. 영상 토큰 0 → 실패. 403 → 그 영상만(연속 2회면 그 실행 끔). 429·5xx·네트워크 → 키 돌려 재시도(최대 8회) 후. 400 등 → 바로. 하루 영상 분량 8시간(`.video_quota.json`) 초과 → 모두 기존 설명란 요약, `grade` NULL |
| 상세 조회 | `videos?part=statistics,snippet` | `part=statistics,snippet,contentDetails,status` (1유닛 그대로) → `durationSec`·`privacy` |
| 장부 | user_version 2 | **3** — `videos.grade`·`quality`·`summarized_at`. `scripts/migrate_library.py --apply` 가 `ALTER TABLE ADD COLUMN`(옛 행 NULL, `updated_at` 무변경 → 시트 재전송 없음). v1·v2 → v3 한 번에 |
| 장부 저장 | `summary_src` 항상 `app` | `video`(영상 요약) · `app`(설명란 요약) + `grade`·`quality`·`summarized_at` |
| 노트 | — | 새 노트 프론트매터 `grade:`(keep·exclude·null)·`summary_src:` (`notion_id` 바로 위) |
| Wiki·검색 | 모든 노트 | `grade: exclude` 노트는 `wiki_ingest.py:collect_sources`·`build_search_index.py:collect_notes` 에서 제외. 노트·MOC·시트는 그대로 |
| `.gitignore` | — | `.video_quota.json` |
| `.env` 스위치 | — | (선택, 없으면 기본) `VIDEO_SUMMARY`(false = 끔) · `VIDEO_MAX_SECONDS`(1800) · `VIDEO_DAILY_SECONDS`(28800) — **이번에 `.env` 는 고치지 않는다** |
| 테스트 | 9종 | 10종 — 신규 `scripts/test_video_summary.js` 17, `test_scheduler_guards.js` 31(+2), `test_wiki_ingest.py` 57(+6), `test_sync_obsidian.py` 24(+1), `test_build_wiki_index.py` 11(+1) |

패치가 바꾸는 파일 18개(M 16 · 신규 2): `.gitignore` `AGENTS.md` `CLAUDE.md` `README.md` `build_search_index.py` `lib/library.js` `lib/library_db.py` `lib/library_schema.sql` `lib/video_summary.js`(신규) `scheduler.js` `scripts/migrate_library.py` `scripts/test_build_wiki_index.py` `scripts/test_scheduler_guards.js` `scripts/test_sync_obsidian.py` `scripts/test_video_summary.js`(신규) `scripts/test_wiki_ingest.py` `sync_obsidian.py` `wiki_ingest.py`

파일 sha256(적용 후):

```
e964d3efc90d83b207d7272b4256fa737030786ff8ee455a75c8bdd0f07315f3  lib/video_summary.js
1da5de9541560f29b54a4f5abe33484609c00504b211ad6c5847f12d19c55c20  scheduler.js
9d75486e32e07b65c7cf5107454aaa4778c72473bc462d3eee55c3b73d5fcb1a  scripts/migrate_library.py
b473c365a1470bea06b8e0f3652e8e3af15bb227ab5299ab236f373a9588fb9c  lib/library_schema.sql
1155a200106e7c1cf9b7dbf0a7929a4c4a685c455ec19478e65c6314d7991a35  lib/library.js
cd34a5924dfd7ca57942203b127718ee9c8b752dca2e1af763e4456ff669d349  wiki_ingest.py
152dc81c67d2969fc7fd71ca8b0762a5799717c6a123005efa127909f02a8cae  build_search_index.py
98d1de67e97c1795054871beddb947069b7157568f57432b6db4a08765860e39  sync_obsidian.py
```

> ⚠️ 패치를 적용한 순간부터 장부를 이전(3-3)하기 전까지 **모든 실행(스케줄러·카톡·시트 미러·백업·wiki_ingest)이 user_version 불일치로 던진다.** 3-1 ~ 3-3 을 끊지 말고 이어서 한다.

## 3. 실행 순서 (`cd <REPO_ROOT>`, 파이썬은 `/opt/homebrew/bin/python3`, 노드는 `/opt/homebrew/bin/node`)

### 3-0. 시간 창·사전 확인

- 지금 시각이 **정시 실행 창(00·06·12·18시 −10분 ~ +25분)과 17:25~17:55 밖**인지 확인. 안이면 창이 끝날 때까지 기다린다.
- `pgrep -fl "scheduler.js|wiki_ingest.py|sync_obsidian.py|kakao_ingest.py|backup_library.py"` → 빈 출력.
- `git rev-parse --short HEAD` → `0e89773`
- `git --no-optional-locks status --porcelain` → 아래 두 줄만:
  ```
  ?? docs/tasks/2026-10-13-v46a-video-summary.md
  ?? docs/tasks/2026-10-13-v46a-video-summary.patch
  ```
- `shasum -a 256 docs/tasks/2026-10-13-v46a-video-summary.patch` → 위 sha256
- `sqlite3 "file:data/library.db?mode=ro" "pragma user_version;"` → `2`

### 3-1. 패치 적용

```bash
git apply --check docs/tasks/2026-10-13-v46a-video-summary.patch && git apply docs/tasks/2026-10-13-v46a-video-summary.patch
shasum -a 256 lib/video_summary.js scheduler.js scripts/migrate_library.py lib/library_schema.sql lib/library.js wiki_ingest.py build_search_index.py sync_obsidian.py   # 2절과 같아야 함
git --no-optional-locks status --porcelain | awk '{print $1}' | sort | uniq -c    # M 16 · ?? 4 (신규 2 + 지시서·패치)
```

### 3-2. 회귀 테스트 10종 (네트워크 0)

```bash
for t in scheduler_guards video_summary; do printf "%s " $t; /opt/homebrew/bin/node scripts/test_$t.js | tail -1; done
for t in verify_library retitle_tips wiki_ingest kakao_ingest sync_obsidian sheet_mirror build_wiki_index backup_library; do
  printf "%s " $t; /opt/homebrew/bin/python3 scripts/test_$t.py 2>&1 | tail -1; done
```
기대: **31/31 · 17/17** · 16/16 · 49/49 · **57/57** · 18/18 · **24/24** · 45/45 · **11/11** · 50/50 — 전부 PASS.

### 3-3. 장부 이전 (user_version 2 → 3) — 원본 장부에 쓰는 단계(대표님 승인)

```bash
Q="select count(*), max(updated_at), sum(length(summary)) from videos; select count(*) from tips; select count(*) from wiki_extract;"
sqlite3 "file:data/library.db?mode=ro" "$Q" > /tmp/v46a_before.txt; cat /tmp/v46a_before.txt
/opt/homebrew/bin/python3 scripts/migrate_library.py            # dry-run
/opt/homebrew/bin/python3 scripts/migrate_library.py --apply
sqlite3 "file:data/library.db?mode=ro" "$Q" > /tmp/v46a_after.txt; diff /tmp/v46a_before.txt /tmp/v46a_after.txt && echo 같음
sqlite3 "file:data/library.db?mode=ro" "pragma user_version; pragma integrity_check; select count(*) from videos where grade is not null or quality is not null or summarized_at is not null;"
```
- dry-run 기대: `"user_version": 2, "target": 3, "missing": [], "add_columns": ["videos.grade", "videos.quality", "videos.summarized_at"]`, 장부 무변경.
- apply 기대: `"ok": true, "user_version": 3, "integrity": "ok"`, `rows == rows_before`, `backup` = `data/library.db.bak.v2-<시각>` 존재.
- 전후 `diff` → `같음`(행 수·최대 `updated_at`·요약 길이 합·tips·wiki_extract). 마지막 줄 기대: `3` / `ok` / `0`.
- 자동 모드가 이 단계를 막으면 멈추고 보고한다(대표님이 터미널에서 같은 명령을 직접 실행).

### 3-4. 연계·로드 확인

```bash
/opt/homebrew/bin/python3 scripts/verify_library.py | grep RESULT_JSON        # "ok": true · vault_missing 0 · tips_missing 0
/opt/homebrew/bin/python3 sheet_mirror.py --check                              # match true (시트 열 무변경)
/opt/homebrew/bin/python3 backup_library.py --status                           # 오류 없이 출력
/opt/homebrew/bin/node -e "const s=require('./scheduler.js'); console.log(typeof s.getBatchDetails, typeof s.validateSummary)"   # function function
/opt/homebrew/bin/python3 -c "import build_search_index as b; print(len(b.collect_notes()))"     # 직전 인덱스 노트 수와 같음 (아직 exclude 노트 없음)
/opt/homebrew/bin/python3 -c "import json; print(len(json.load(open('wiki_index.json'))['notes']))"
touch .video_quota.json && git check-ignore -q .video_quota.json && echo ignored; rm -f .video_quota.json
git check-ignore -q data/library.db && echo ignored
```
- `collect_notes` 수 = `wiki_index.json` 노트 수(같지 않으면 두 값을 보고 — 오늘 새 노트가 아직 인덱스에 없을 수 있다, 차이 0~수 건은 정상).

### 3-5. 커밋 (push 는 별도 지시)

```bash
git add .gitignore AGENTS.md CLAUDE.md README.md build_search_index.py lib/library.js lib/library_db.py lib/library_schema.sql \
  lib/video_summary.js scheduler.js scripts/migrate_library.py scripts/test_build_wiki_index.py scripts/test_scheduler_guards.js \
  scripts/test_sync_obsidian.py scripts/test_video_summary.js scripts/test_wiki_ingest.py sync_obsidian.py wiki_ingest.py \
  docs/tasks/2026-10-13-v46a-video-summary.md docs/tasks/2026-10-13-v46a-video-summary.patch
git commit -m "v4.6-a 실제 영상 요약 + 품질 필터 — 신규 영상 영상 입력 · 코드 등급(keep/exclude) · 장부 user_version 3 · exclude 는 Wiki·검색 제외"
git --no-optional-locks status --porcelain    # 빈 출력 (커밋 뒤)
git log --oneline -1
```

## 4. 데몬 재기동

없음. `ytsummarizer`·`wiki-ingest` 는 실행마다 새 프로세스라 다음 실행부터 반영된다. 상주 데몬(`server`·`wiki-lan`)은 장부·요약 코드를 불러오지 않는다(`server.js` 는 `scheduler.js` 를 자식 프로세스로 띄운다). plist·`.env` 무변경.

## 5. 롤백

- 영상 요약만 끄기(코드 유지): `.env` 끝에 `VIDEO_SUMMARY=false` 한 줄 → 다음 실행부터 전부 설명란 요약.
- 커밋 전: `git checkout -- . && rm lib/video_summary.js scripts/test_video_summary.js` → 장부 `sqlite3 data/library.db "pragma user_version = 2"`(새 열은 남아도 옛 코드가 이름으로 읽어 무해 — 그 사이 새로 쌓인 행을 지키려고 백업 복원 대신 버전만 내린다).
- 커밋 뒤: `git revert <커밋>` + 위 버전 내리기. 정시 실행 창 밖에서.

## 6. 범위 밖

- `git push`(검증 뒤 별도 지시), `.env`·plist 변경, Wiki backfill 재개(`.env WIKI_BACKFILL_DAILY_MAX=0` 유지).
- v4.6-b: 기존 약 3,000편 재요약 · 노트 요약 절 제자리 교체 · backfill 결합 · 항목 0이 된 `_wiki` 페이지 처리 · 재요약 모델(`gemini-2.5-flash-lite` 는 신규 프로젝트에 404).
- 실제 동작 판정은 Cowork 가 다음 정시 실행의 `scheduler.log` `🎬 요약 방식` 줄과 장부 `summary_src`·`grade` 집계로 한다.
