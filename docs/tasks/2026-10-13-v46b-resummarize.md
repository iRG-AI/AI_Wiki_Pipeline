# 작업지시서 — v4.6-b 기존분 재요약 + 노트 요약 절 제자리 교체 + Wiki backfill 재개

- 작성: 2026-10-13 (Cowork) · 실행: Claude Code (Sonnet 5.5) · 기준 커밋 `d8635b2`(v4.6-a)
- 패치: `docs/tasks/2026-10-13-v46b-resummarize.patch` — sha256 `87920fb3e4ee5ef2b46b10b590118f0cbfc60bf7c63a7fbd4e531c990a996107`
- 보고는 한국어로. 기대값과 다르면 **그 단계에서 멈추고** 보고한다(다음 단계로 넘어가지 않는다).

## 1. 배경

- v4.6-a(10-13 `d8635b2`)부터 신규 영상은 실제 영상으로 요약한다. 장부의 옛 요약 약 3,000편(`summary_src != 'video'`)은 여전히 설명란만 보고 "추론해서라도" 쓴 것이라 일부는 지어낸 내용이다. 그래서 Wiki backfill(옛 소스 재추출)을 `.env WIKI_BACKFILL_DAILY_MAX=0` 으로 멈춰 두었다.
- 10-13 재요약 모델 비교(Cowork, 무료 키): `gemini-3.5-flash-lite` 5건이 2.5 Flash 와 **등급·신호 5/5 일치**(Python 강의 = not_ai, 컨설팅 모집 = promo_main 포함). 음성 토큰 항목은 따로 안 잡히지만 말 내용을 정확히 옮겼다. 요약은 약 65% 길이. **3.x 모델은 `thinkingBudget: 0` 을 400 INVALID_ARGUMENT 로 거절** → `thinkingLevel: 'minimal'`.
- 10-13 12:00 실행에서 무료 레퍼런스 키트를 나눠 주는 시연 영상(`-YySYOBbhD8`)이 `promo_main` 으로 제외됐다(오판). 사전 검증에서 끝에 자기 강의 모집을 잠깐 붙인 시연 영상도 같은 이유로 제외됐다 → 프롬프트를 좁혔다(넓히지 않음).
- 대표님 결정(10-13 01:20): 재요약 모델 3.5 Flash-Lite · 실행 자리 scheduler 매 실행 5편 · 항목 0 `_wiki` 페이지는 안내 문구로 · backfill 은 실제 영상 요약 소스만 재개. (13:10) promo_main 좁히기 + 오판 1건 keep 으로 되돌리기.

## 2. AS-IS → TO-BE

| 항목 | AS-IS (v4.6-a) | TO-BE (v4.6-b) |
|---|---|---|
| 옛 요약 | 그대로 | 신규 `lib/resummarize.js` — `scheduler.js` 가 신규 처리 뒤 매 실행 호출(`runResummary`, 던지지 않음, 저장·Skip·오류 집계 밖). 후보 `summary_src != 'video'` · `quality.resummary_skip` 없음 · 최신 업로드부터. 실행당 `RESUMMARY_PER_RUN` 5 · 하루(PT) `RESUMMARY_DAILY_MAX` 20(장부 `quality.resummary_day` 로 셈 — 상태 파일 없음) · 하루 영상 분량 8시간 중 `RESUMMARY_RESERVE_SECONDS` 10800 은 신규 몫. 모델 `RESUMMARY_MODEL` 기본 `gemini-3.5-flash-lite` |
| 재요약 실패 | — | 대체 요약 없이 기존 요약 유지. 삭제·공개 아님·길이 모름·영상 토큰 0 → `quality.resummary_skip`. 형식 실패·그 밖 4xx → `resummary_fail` +1, 2회면 건너뜀. 429·5xx·네트워크·하루 분량·403 연속·`VIDEO_SUMMARY=false` → 그 실행 재요약 중단. 표시만 할 때는 `updated_at` 안 건드림 |
| 장부 | — | 성공 시 한 트랜잭션: `summary`·`summary_src='video'`·`grade`·`quality`(+`resummary`·`resummary_day`)·`summarized_at`·`updated_at` + 그 소스 `wiki_extract` → `status='stale'`, `attempts=0`(`updated_at` 그대로). **스키마 무변경(user_version 3)** |
| `lib/video_summary.js` | 모델 2.5 Flash 고정, 실패 시 항상 설명란 요약 | 모델 인자 + `thinkingConfigFor`(2.x = `thinkingBudget: 0` 그대로 · 3.x = `thinkingLevel: 'minimal'`), `fallback:false`(실패면 `{ok:false, reason}`), `reserveSeconds`. `summaryProblem` — bad_summary 사유 로그 1줄(`missing:<절>`·`short_tail:N`·`empty`). `promo_main` 프롬프트 좁힘: 무료 자료·키트 배포, 구독·댓글 유도, 끝·중간에 자기 강의를 잠깐 알리는 정도는 false |
| 노트 | 새 노트만 | `sync_obsidian.py:refresh_changed_notes` — 장부 `summary_src='video'` 인데 노트 프론트매터와 다르면 요약 절(`**▶ 영상 보기: **` 줄 다음 `---` 뒤부터 `🔗 관련 항목` 앞까지)만 교체 + `grade`·`summary_src` 맞춤(없으면 `notion_id` 앞에 삽입). `video` 인데 `grade` 만 다르면 그 줄만. 경계를 못 찾으면 파일 그대로 + `RESULT_JSON.refresh_skipped`. 바뀐 노트가 있으면 검색 인덱스 갱신 |
| Wiki backfill | 정지(`.env` 0) · 대상 = ingested + wiki_extract 없음/seed | 대상 = **노트 `summary_src: video` 인 소스만**(`backfill_source`). `stale` 행은 다시 추출될 때까지 페이지에 그대로. `.env` 정지 줄 제거 → 기본 30(실사용은 재요약 속도 = 하루 1~2회) |
| 항목 0 페이지 | 옛 내용 그대로 남음 | 이름이 `ENTITIES`·`CONCEPTS` 목록 안이면 안내 문구 페이지(`source_count: 0`, 시각 없음 — 결정적), index 에서 빠짐. 목록 밖 파일은 건드리지 않음. `WIKI_RESULT.empty_pages` |
| 테스트 | 10종 | **11종** — 신규 `scripts/test_resummarize.js` 9, `test_video_summary.js` 23(+6), `test_scheduler_guards.js` 33(+2), `test_sync_obsidian.py` 32(+8), `test_wiki_ingest.py` 64(+7) |

패치가 바꾸는 파일 14개(M 12 · 신규 2): `AGENTS.md` `CLAUDE.md` `README.md` `lib/library.js` `lib/resummarize.js`(신규) `lib/video_summary.js` `scheduler.js` `scripts/test_resummarize.js`(신규) `scripts/test_scheduler_guards.js` `scripts/test_sync_obsidian.py` `scripts/test_video_summary.js` `scripts/test_wiki_ingest.py` `sync_obsidian.py` `wiki_ingest.py`

파일 sha256(적용 후):

```
b383e765b9d36a07838603c879d04a1a7cb3c167be9fb715dd05d72e192415e2  lib/resummarize.js
59829adf82168a3dff4cdc9d58d34978bf4fcefc700be371718a3734e11f5d83  lib/video_summary.js
a7d4fc7d375e508db57c1b6c764e7ce80d9e97ec45693b702429347a922c3234  lib/library.js
32e563333f10aa6025377179325f0baa8a63ef3b84ec9edc1185b55eed16cf9d  scheduler.js
626eb434c67b7289c91cf5daf9592927927a11c02288ac01e041c37d210225a5  sync_obsidian.py
e166cd5768b38bf5e4ab2c08a394e592e65e10110a4f18d92cf7caaffca96ecd  wiki_ingest.py
```

### 사전 검증 (Cowork, 맥 네이티브 — `git archive d8635b2` + 이 패치의 코드, 실데이터는 사본)

- 회귀 11종 전부 PASS(33 · 23 · 9 · 16 · 49 · 64 · 18 · 32 · 45 · 11 · 50).
- 장부 사본 실제 재요약 2건(3.5 Flash-Lite, 29.9초): 후보 순서 = 최신 업로드부터, 성공 2 · `updated_at`·`summarized_at` 갱신 · `wiki_extract` 2행 `stale` · 남은 대상 2,998.
- Vault 사본(3,015 노트): **요약 절 경계 3,015/3,015 찾음 · 관련 항목 절 3,015/3,015 보존**. 재요약 2건 맞춤 → 두 번째 실행 0.
- Wiki(사본): backfill 대상 옛 규칙 3,117 → 새 규칙 1(stale 1). `--render-only` 항목 0 안내 페이지 1(`Replit`), 두 번째 렌더 쓰기 0.
- 좁힌 promo_main 프롬프트(3.5 Flash-Lite): 무료 키트 시연 `-YySYOBbhD8` keep · 끝에 강의 모집을 붙인 시연 `CDSrRCbdG4o` keep · 컨설팅 모집 `2cX3_vi2y3I` exclude [promo_main] 유지.

## 3. 실행 순서 (`cd <REPO_ROOT>`, 파이썬은 `/opt/homebrew/bin/python3`, 노드는 `/opt/homebrew/bin/node`)

### 3-0. 시간 창·사전 확인

- 지금 시각이 **정시 실행 창(00·06·12·18시 −10분 ~ +25분)과 17:25~17:55 밖**인지 확인. 안이면 창이 끝날 때까지 기다린다.
- `pgrep -fl "scheduler.js|wiki_ingest.py|sync_obsidian.py|kakao_ingest.py|backup_library.py"` → 빈 출력.
- `git rev-parse --short HEAD` → `d8635b2`
- `git --no-optional-locks status --porcelain` → 아래 두 줄만:
  ```
  ?? docs/tasks/2026-10-13-v46b-resummarize.md
  ?? docs/tasks/2026-10-13-v46b-resummarize.patch
  ```
- `shasum -a 256 docs/tasks/2026-10-13-v46b-resummarize.patch` → 위 sha256

### 3-1. 패치 적용

```bash
git apply --check docs/tasks/2026-10-13-v46b-resummarize.patch && git apply docs/tasks/2026-10-13-v46b-resummarize.patch
shasum -a 256 lib/resummarize.js lib/video_summary.js lib/library.js scheduler.js sync_obsidian.py wiki_ingest.py   # 2절과 같아야 함
git --no-optional-locks status --porcelain | awk '{print $1}' | sort | uniq -c    # M 12 · ?? 4 (신규 2 + 지시서·패치)
```

### 3-2. 회귀 테스트 11종 (네트워크 0)

```bash
for t in scheduler_guards video_summary resummarize; do printf "%s " $t; /opt/homebrew/bin/node scripts/test_$t.js | tail -1; done
for t in verify_library retitle_tips wiki_ingest kakao_ingest sync_obsidian sheet_mirror build_wiki_index backup_library; do
  printf "%s " $t; /opt/homebrew/bin/python3 scripts/test_$t.py 2>&1 | tail -1; done
```
기대: **33/33 · 23/23 · 9/9** · 16/16 · 49/49 · **64/64** · 18/18 · **32/32** · 45/45 · 11/11 · 50/50 — 전부 PASS.

### 3-3. 로드·읽기 전용 확인 (장부·Vault 쓰기 없음)

```bash
/opt/homebrew/bin/node -e "const s=require('./scheduler.js'); console.log(typeof s.runResummary, JSON.stringify(require('./lib/resummarize').settings({})))"
# → function {"enabled":true,"model":"gemini-3.5-flash-lite","perRun":5,"dailyMax":20,"reserveSeconds":10800}
/opt/homebrew/bin/node -e "const l=require('./lib/library'); const db=l.openLibrary(); console.log(l.resummaryRemaining(db), l.resummaryDoneOn(db, require('./lib/youtube_oauth').todayKey())); db.close()"
# → 3000 안팎(설명란 요약 행 수) 0
/opt/homebrew/bin/python3 sync_obsidian.py --dry-run | grep RESULT_JSON     # "refreshed": 0 · "refresh_skipped": 0
PYTHONPATH=. /opt/homebrew/bin/python3 -c "
import io, contextlib, wiki_ingest as w, wiki_config as c, library_db as l
with contextlib.redirect_stdout(io.StringIO()): s = w.collect_sources()
st = c.load_state()['ingested']; db = l.open_existing(readonly=True); store = w.load_store(db); db.close()
print('backfill 대상', sum(1 for x in s if w.backfill_source(x, st, store)))"
# → backfill 대상 0 (0~2 정상 — 아직 stale 이 없다)
```

### 3-4. 오판 1건 등급 되돌리기 — 원본 장부에 쓰는 단계(대표님 승인)

`-YySYOBbhD8`(무료 레퍼런스 키트 시연)을 `keep` 으로. `updated_at` 을 새로 찍는다(장부 규칙). 노트 프론트매터는 다음 `sync_obsidian` 이 맞춘다(이번 패치의 `refresh_changed_notes`).

```bash
sqlite3 "file:data/library.db?mode=ro" "select grade, json_extract(quality,'$.why') from videos where video_id='-YySYOBbhD8';"     # exclude|["promo_main"]
sqlite3 data/library.db "UPDATE videos SET grade='keep', quality=json_set(quality,'$.manual_grade','keep: 무료 키트 시연 promo_main 오판 (10-13)'), updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE video_id='-YySYOBbhD8' AND grade='exclude'; SELECT changes();"   # 1
sqlite3 "file:data/library.db?mode=ro" "select grade, updated_at, json_extract(quality,'$.manual_grade') from videos where video_id='-YySYOBbhD8'; pragma integrity_check;"   # keep|2026-10-13T…Z|keep: … / ok
/opt/homebrew/bin/python3 sync_obsidian.py --dry-run | grep -E "dry-run\] grade|RESULT_JSON"   # [dry-run] grade → keep … · "refreshed": 1
```
- 자동 모드가 이 단계를 막으면 멈추고 보고한다(대표님이 터미널에서 같은 명령을 직접 실행).

### 3-5. Wiki backfill 정지 줄 제거 (`.env` — 레포 밖 비밀 파일, 커밋 대상 아님)

```bash
cp .env ~/rename_backup_20261013/env.pre_v46b
grep -n '^WIKI_BACKFILL_DAILY_MAX=' .env          # 한 줄, 값 0
sed -i '' '/^WIKI_BACKFILL_DAILY_MAX=0$/d' .env
grep -c '^WIKI_BACKFILL_DAILY_MAX=' .env           # 0
PYTHONPATH=. /opt/homebrew/bin/python3 -c "import wiki_ingest as w; print(w.backfill_max())"   # 30
```
- `.env` 의 다른 줄은 건드리지 않는다. 값·키를 출력하지 않는다(위 명령 외).

### 3-6. 커밋 (push 는 별도 지시)

```bash
git add AGENTS.md CLAUDE.md README.md lib/library.js lib/resummarize.js lib/video_summary.js scheduler.js \
  scripts/test_resummarize.js scripts/test_scheduler_guards.js scripts/test_sync_obsidian.py scripts/test_video_summary.js \
  scripts/test_wiki_ingest.py sync_obsidian.py wiki_ingest.py \
  docs/tasks/2026-10-13-v46b-resummarize.md docs/tasks/2026-10-13-v46b-resummarize.patch
git commit -m "v4.6-b 기존분 재요약 — 3.5 Flash-Lite 실행당 5편·하루 20 · 노트 요약 절 제자리 교체 · backfill 은 영상 요약 소스만 · 항목 0 안내 페이지 · promo_main 좁힘"
git --no-optional-locks status --porcelain    # 빈 출력 (커밋 뒤)
git log --oneline -1
```

## 4. 데몬 재기동

없음. `ytsummarizer`·`wiki-ingest` 는 실행마다 새 프로세스라 다음 실행부터 반영된다(18:00 실행이 첫 재요약). 상주 데몬(`server`·`wiki-lan`)은 바뀐 모듈을 불러오지 않는다. plist 무변경.

## 5. 롤백

- 재요약만 끄기(코드 유지): `.env` 끝에 `RESUMMARY=false` 한 줄 → 다음 실행부터 재요약 0(장부·네트워크 0).
- backfill 다시 멈추기: `.env` 에 `WIKI_BACKFILL_DAILY_MAX=0` 한 줄(또는 `cp ~/rename_backup_20261013/env.pre_v46b .env`).
- 등급 되돌리기 취소: 3-4 의 UPDATE 를 `grade='exclude'` 로(같은 조건 반대로).
- 커밋 전: `git checkout -- . && rm lib/resummarize.js scripts/test_resummarize.js`. 커밋 뒤: `git revert <커밋>`. 스키마 무변경이라 장부 버전 조작 없음. 이미 재요약된 행은 `summary_src='video'` 로 남는다(옛 코드도 정상으로 읽는다).

## 6. 범위 밖

- `git push`(검증 뒤 별도 지시), plist 변경, 지금 `sync_obsidian.py` 실제 실행(다음 정시 실행이 한다).
- 토픽 재분류·노트 폴더 이동, 시트에 등급 보이기, MOC 에서 exclude 노트 빼기, 꿀팁 재요약, 재요약 프롬프트 분량 보강.
- 실제 동작 판정은 Cowork 가 18:00 실행의 `scheduler.log` `🔁 재요약` 줄·장부 `quality.model` 집계·노트 요약 절·`--check`, 다음 날 17:30 `WIKI_RESULT.backfill_calls` 로 한다.
