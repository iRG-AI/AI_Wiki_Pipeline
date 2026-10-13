# v4.11 — 재요약 5xx 조기 중단

> 지시 번호는 발행할 때 채팅으로 준다. 보고는 한국어로.
> 선행: `a237d2e`(v4.10, 원격 main 과 같음). 스케줄러는 내리지 않는다(5-0 의 시간 창만 피한다).
> 스키마·`.env` 변경 없음. **데몬 재기동 없음**(`scheduler.js` 는 실행마다 새로 뜬다). **장부·Vault 쓰기 없음**. push 는 이 지시서 범위 밖(다음 지시).

## 1. 배경

10-14 00:00 실행에서 재요약 1편(`RtGvzYeZ9gs` 「OpenAI의 준 리만 가설 증명, 해설과 그 의의」)이 Gemini 3.5 Flash-Lite **503 을 8회**(키 4개 × 2) 받고 실패했다.

```
[00:03:38]   🔁 재요약: OpenAI의 준 리만 가설 증명, 해설과 그 의의
[00:05:17]     ⏳ 영상 요약 503 — 6초 뒤 다음 키 (1/8)
...
[00:14:37]     ⏳ 영상 요약 503 — 20초 뒤 다음 키 (7/8)
[00:16:20]     ↩️  영상 요약 실패 (video_http_503)
[00:16:20]   🔁 재요약: 0편 (제외 등급 0) {"video_http_503":1} · 오늘 5/20 · 중단 video_http_503 · 남은 대상 2995
```

- 503 응답이 **1~2분 뒤에** 온다 → 1편에 약 12분 42초. 실행 16분 15초의 대부분이고, 20분 판정 시각에 가까워졌다.
- 신규 영상(2.5 Flash)의 503 은 약 20초 안에 오고 1~2회 재시도 뒤 성공한다(10-13 00시 3건 · 10-14 00시 1건 모두).
- 재요약은 신규보다 뒷순위이고, 실패하면 기존 요약을 그대로 둔다(다음 실행이 이어서). 오래 붙잡을 이유가 없다.
- 후보는 최신 업로드부터라 **같은 영상이 매 실행 후보 맨 앞**에 온다. 그 영상만 계속 5xx 면 재요약이 영원히 멈춘다 → 영상별로 세어 건너뛴다.

## 2. 설계 결정 (바꾸지 말 것)

| 항목 | 결정 |
|---|---|
| 요약기 인자 | `lib/video_summary.js:makeVideoSummarizer` 선택 인자 `maxServerErrors`(기본 0 = 상한 없음). 영상 1편의 재시도 고리에서 **5xx(status ≥ 500)만** 세어 그 횟수에 이르면 재시도를 그만두고 `video_http_<코드>` 로 실패. 로그 `⏹  영상 요약 503 — 재시도 그만 (5xx 1/1)` |
| 안 세는 것 | 429(키 회전 0.5초 — 키별 한도) · 네트워크 오류(status 0) — 지금처럼 키를 돌린다 |
| 신규 경로 | `scheduler.js:processMasterIngest` 는 `maxServerErrors` 를 넘기지 않는다 → 예전대로 키 4개 × 2회. **신규 쪽 상한을 줄이지 말 것** |
| 재요약 | `lib/resummarize.js` `settings().max5xx` = `RESUMMARY_MAX_5XX`(기본 **1**, 0 = 상한 없음)를 `makeSummarizer({…, maxServerErrors})` 로 넘긴다. `scheduler.js:runResummary` 가 그대로 전달 |
| 5xx 로 멈춤 | 분류는 예전과 같은 `stop`(그 실행 재요약 중단). 더해 그 영상 `quality.resummary_5xx` +1 · `resummary_last` — `lib/library.js:markResummary({server})`. **3회(`lib/library.js:RESUMMARY_MAX_5XX_STOPS`)면 `resummary_skip = '5xx:video_http_503'`** |
| `updated_at` | 안 건드린다(`quality` 만 — 기존 건너뜀·실패 표시와 같음, 시트 재전송 없음) |
| 성공하면 | `updateResummary` 가 quality 를 새로 쓰므로 `resummary_5xx` 는 사라진다(기존 동작 — `resummary_fail` 만 이어 붙임) |
| 무변경 | 장부 스키마(user_version 3) · 403 연속 2회 끔 · 하루 분량·예약 · 실행당·하루 상한 · `bad_*` 실패 2회 건너뜀 · 429·네트워크 처리 |

> 두 상한: 영상 1편 안에서 재시도를 그만두는 5xx 횟수 = `.env RESUMMARY_MAX_5XX` → `settings().max5xx`(기본 1) · 같은 영상이 5xx 로 멈춘 실행 수 상한 = `lib/library.js:RESUMMARY_MAX_5XX_STOPS`(3, 상수).

## 3. 파일

| 파일 | 내용 |
|---|---|
| `docs/tasks/patches/2026-10-14-v411-resummary-5xx-stop.patch` | 기준 = `a237d2e`, 9개 파일, +96 −16 |
| `docs/tasks/2026-10-14-v411-resummary-5xx-stop.md` | 이 지시서 |

```
sha256  aa93e83aa8211c085963bd646fc1f5b59c6af3f12ecbe974e80427f9afca6922  docs/tasks/patches/2026-10-14-v411-resummary-5xx-stop.patch
```

| 패치 안 파일 | 변경 |
|---|---|
| `lib/video_summary.js` | 머리 설명 2줄 · `maxServerErrors` · 고리 안 5xx 세기 + `break` + 로그 1줄 (+8) |
| `lib/resummarize.js` | 머리 설명 3줄 · `DEFAULTS.max5xx` · `settings().max5xx` · `makeSummarizer` 인자 · 5xx 멈춤 때 `markResummary({server})` |
| `lib/library.js` | `RESUMMARY_MAX_5XX_STOPS = 3` · `markResummary` 의 `server`(`resummary_5xx` +1 · 3회면 skip) · export |
| `scheduler.js` | `runResummary` 의 `makeSummarizer` 가 `maxServerErrors` 전달 (2줄) |
| `scripts/test_video_summary.js` | +2건(상한 1 = 요청 1·회전 0·분량 1·로그 · 5xx 만 셈·429/네트워크는 회전·없으면 8회) → 25건 |
| `scripts/test_resummarize.js` | 중단 사례에 `resummary_5xx` 확인 + 2건(3회면 건너뜀·`updated_at` 그대로·다음 후보 · 설정 기본 1·0·전달) → 11건 |
| `CLAUDE.md` · `AGENTS.md` · `README.md` | 머리 버전 v4.11 · 요약 1줄 · 테스트 수 · 재요약 절 문구 · 이력 / README 요약 행 · `.env` 예시 1줄 · 상세 1절. AGENTS.md = 머리글 5줄 + CLAUDE.md 4행부터 |

### Cowork 사전 검증 (2026-10-14 00:55~01:00, 레포 무변경)

- 클라우드(Node 22.22): 새 테스트 4건이 옛 코드에서 실패(video_summary 2 · resummarize 3)하고 새 코드에서 통과.
- 맥 네이티브(홈 임시 폴더 `git archive a237d2e` + 이 패치 — 상수 이름 정리 뒤 최종본으로 다시 돌림): **회귀 14종 전부 통과** — scheduler_guards 33 · video_summary 25 · resummarize 11 · wiki_search 34 · verify_library 16 · retitle_tips 49 · wiki_ingest 64 · kakao_ingest 37 · title_fetch 43 · recategorize_tips 52 · sync_obsidian 32 · sheet_mirror 45 · build_wiki_index 15 · backup_library 50.
- 장부 사본(`.backup`)으로 모의 실행 3회(진짜 `makeVideoSummarizer` + 늘 503 을 주는 가짜 요청): 실행마다 **요청 1회** · `중단 video_http_503` · 후보 맨 앞 `RtGvzYeZ9gs` 의 `resummary_5xx` 1 → 2 → 3, 3회째 `resummary_skip = '5xx:video_http_503'` · 남은 대상 2995 → 2994 · `updated_at` 그대로 · integrity ok. 사본 삭제.

## 4. 기대 효과

| | 지금 | v4.11 |
|---|---|---|
| 재요약 503 1편 | 8회 · 약 13분 | 1회 · 1~2분 |
| 같은 영상이 계속 503 | 매 실행 13분 · 재요약 영영 정지 | 3번째 실행에 건너뜀 → 다음 후보 |
| 신규 영상 503 | 키 4개 × 2회 | 그대로 |

## 5. 실행 — 적용·테스트·커밋

### 5-0. 시간

스케줄러가 00·06·12·18시, wiki-ingest 가 17:30 에 돈다. **매시 50분 ~ 다음 시 20분, 17:25~17:45 에는 5-2 이후를 시작하지 않는다.**
판정은 시각의 **분**으로 한다 — `date '+%H:%M'` 의 분이 50~59 또는 00~20 이면(어느 시든) 창 **안**이다. 예: 00:15 는 창 안, 00:25 는 창 밖.
(이 지시서는 장부를 쓰지 않지만, 스케줄러가 패치 도중의 `lib/*.js` 를 읽지 않게 창을 피한다.)

### 5-1. 시작 상태 (읽기만)

```bash
cd <REPO_ROOT>
date '+%H:%M'                                            # 창 밖이어야 한다
git --no-optional-locks rev-parse --short HEAD          # a237d2e
git --no-optional-locks status --porcelain
#   기대: 아래 두 줄만
#   ?? docs/tasks/2026-10-14-v411-resummary-5xx-stop.md
#   ?? docs/tasks/patches/2026-10-14-v411-resummary-5xx-stop.patch
shasum -a 256 docs/tasks/patches/2026-10-14-v411-resummary-5xx-stop.patch   # 3절 값과 같아야 한다
grep -o '"outcome": "[a-z]*"' .run_state.json            # "ok" (running 이면 멈춤 — 스케줄러 실행 중)
pgrep -fl scheduler.js || echo "scheduler 미실행"         # 미실행이어야 한다
```

어긋나면 **멈추고 보고**한다.

### 5-2. 패치 적용

```bash
git apply --check docs/tasks/patches/2026-10-14-v411-resummary-5xx-stop.patch && git apply docs/tasks/patches/2026-10-14-v411-resummary-5xx-stop.patch
git --no-optional-locks status --porcelain
#   기대: M AGENTS.md · M CLAUDE.md · M README.md · M lib/library.js · M lib/resummarize.js · M lib/video_summary.js
#        M scheduler.js · M scripts/test_resummarize.js · M scripts/test_video_summary.js · ?? 지시서 · ?? 패치
git --no-optional-locks diff --stat | tail -1            # 9 files changed, 96 insertions(+), 16 deletions(-)
{ head -5 AGENTS.md; tail -n +4 CLAUDE.md; } | cmp - AGENTS.md && echo AGENTS_OK
for f in lib/library.js lib/resummarize.js lib/video_summary.js scheduler.js; do /opt/homebrew/bin/node --check $f || echo "SYNTAX_FAIL $f"; done; echo SYNTAX_DONE
```

### 5-3. 회귀 테스트 14종 (네트워크 0회, 실제 장부·Vault·.env 무관)

```bash
/opt/homebrew/bin/node scripts/test_scheduler_guards.js      # 33/33 PASS
/opt/homebrew/bin/node scripts/test_video_summary.js         # 25/25  (+2)
/opt/homebrew/bin/node scripts/test_resummarize.js           # 11/11  (+2)
/opt/homebrew/bin/node scripts/test_wiki_search.js           # 34/34
/opt/homebrew/bin/python3 scripts/test_recategorize_tips.py  # 52/52
/opt/homebrew/bin/python3 scripts/test_title_fetch.py        # 43/43
/opt/homebrew/bin/python3 scripts/test_kakao_ingest.py       # 37/37
/opt/homebrew/bin/python3 scripts/test_verify_library.py     # 16/16
/opt/homebrew/bin/python3 scripts/test_retitle_tips.py       # 49/49
/opt/homebrew/bin/python3 scripts/test_wiki_ingest.py        # 64/64
/opt/homebrew/bin/python3 scripts/test_sync_obsidian.py      # 32/32
/opt/homebrew/bin/python3 scripts/test_sheet_mirror.py       # 45/45
/opt/homebrew/bin/python3 scripts/test_build_wiki_index.py   # 15/15
/opt/homebrew/bin/python3 scripts/test_backup_library.py     # 50/50
```

하나라도 FAIL 이면 멈추고 보고(8절 롤백).

### 5-4. 설정 확인 (읽기만 — 장부·네트워크 0)

```bash
/opt/homebrew/bin/node -e "const rs=require('./lib/resummarize'); const lib=require('./lib/library'); console.log(JSON.stringify(rs.settings(process.env)), lib.RESUMMARY_MAX_5XX_STOPS)"
#   기대: {"enabled":true,"model":"gemini-3.5-flash-lite","perRun":5,"dailyMax":20,"reserveSeconds":10800,"max5xx":1} 3
#   (`.env` 를 읽지 않는 셸이라 기본값이 나온다 — 스케줄러는 .env 를 읽는다. .env 에 RESUMMARY_MAX_5XX 줄은 없다)
grep -c '^RESUMMARY_MAX_5XX=' .env                        # 0 (넣지 않는다 — 기본 1)
```

## 6. 커밋 (push 하지 않음)

```bash
git add AGENTS.md CLAUDE.md README.md lib/library.js lib/resummarize.js lib/video_summary.js scheduler.js \
        scripts/test_resummarize.js scripts/test_video_summary.js \
        docs/tasks/2026-10-14-v411-resummary-5xx-stop.md docs/tasks/patches/2026-10-14-v411-resummary-5xx-stop.patch
git commit -m "v4.11 재요약 5xx 조기 중단 (RESUMMARY_MAX_5XX 기본 1 · 영상별 3회면 건너뜀)"
git --no-optional-locks status --porcelain       # 커밋 뒤 기대: 빈 출력
git --no-optional-locks log --oneline -2
git --no-optional-locks show --stat HEAD | tail -13   # 11개 파일
```

## 7. 데몬

재기동 없음. `scheduler.js`·`lib/*.js` 는 정시 실행마다 새로 읽힌다 — 커밋 뒤 첫 정시 실행부터 적용. 상주 데몬(`server`·`wiki-lan`)은 바뀐 파일을 쓰지 않는다(`lib/wiki_search.js` 무변경).

## 8. 롤백

- 커밋 전: `git checkout -- AGENTS.md CLAUDE.md README.md lib/library.js lib/resummarize.js lib/video_summary.js scheduler.js scripts/test_resummarize.js scripts/test_video_summary.js` (지시서·패치는 untracked 로 남김).
- 커밋 뒤(push 전): `git reset --hard a237d2e` 는 지시서·패치까지 지우므로 쓰지 않는다 → `git revert --no-edit HEAD`.
- 급히 예전 동작으로: `.env` 에 `RESUMMARY_MAX_5XX=0` (영상 1편 상한 없음 = 8회. 영상별 3회 건너뜀은 그대로 남는다). 재요약 전체를 끄려면 `RESUMMARY=false`.
- 장부에 남는 `quality.resummary_5xx`·`resummary_skip = '5xx:…'` 는 무해하다. 건너뜀을 풀려면 Cowork 판단 후 장부 1행 수정(이 지시서 범위 밖).

## 9. 보고

5-1 ~ 6 의 각 명령 출력(기대값과 다르면 그 줄을 먼저), 커밋 해시, `show --stat` 마지막 13줄.

## 10. 범위 밖

- push(다음 지시).
- 신규 영상 경로의 503 재시도(그대로 둔다).
- 503 이 영상 탓인지 모델 탓인지 가리기 — 10-14 06시 이후 실행 로그로 Cowork 가 본다.
- 429·네트워크 오류 재시도 정책, `RESUMMARY_PER_RUN`·`RESUMMARY_DAILY_MAX` 값.
