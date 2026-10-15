# v4.13 — 영상 하루 분량을 모델별·키별로 (재요약 처리량 회복)

> 지시 번호는 발행할 때 채팅으로 준다. 보고는 한국어로.
> 선행: `a78da1e`(원격 main 과 같음). 스케줄러는 내리지 않는다(5-0 의 시간 창만 피한다).
> 스키마·`.env` 변경 없음. **데몬 재기동 없음**(`scheduler.js`·`lib/*.js` 는 실행마다 새로 읽힌다). **장부·Vault 쓰기 없음**. push 는 이 지시서 범위 밖(다음 지시).

## 1. 배경

10-15 06시 실행의 재요약이 0편이었다 — `🔁 재요약: 0편 … 중단 daily_video_cap`.

| PT 10-14 | 편수 | 초 |
|---|---|---|
| 신규 영상 (2.5 Flash) | 14 | 10,590 |
| 재요약 (3.5 Flash-Lite) | 9 | 5,593 |
| `.video_quota.json` 합계 (실패 요청 포함) | | **17,524** |

재요약 한도는 하루 8시간에서 신규 몫 3시간을 뺀 18,000초인데, 합계 하나로 세므로 신규가 먼저 쓴 만큼 재요약 몫이 줄어든다. 476초만 남아 다음 후보(945초)를 보내지 못했다. 이 속도(하루 약 9편)면 남은 2,981편에 약 10개월이 걸린다(설계 5개월).

### 근거 — 한도는 "모든 키·모델 합계 8시간"이 아니다 (Cowork, 10-15 10:48~10:52, 읽기만)

같은 PT 10-14 하루에 v4.12 시험(맥 `~/v412probe`, 10-14 18:33~18:53 KST = PT 02:33~02:53)도 같은 키 4개로 실호출했다.

| 출처 | 2.5 Flash | 3.5 Flash-Lite | 합계 |
|---|---|---|---|
| 파이프라인 (`.video_quota.json`) | 신규 10,590 | 재요약 5,593 | 17,524 |
| v4.12 시험 (`results.jsonl` 16건 · `results2.jsonl` 10건 · `live.js` 6건) | 9,905 | 9,905 | 19,810 |
| **합계** | 약 20,500 | 약 15,500 | **약 37,300초 = 10.4시간** |

- 영상 요청에 429 는 0건이었다. 합계 8시간을 넘긴 뒤의 10-15 00시 실행(신규 11 · 재요약 4)도 200 이었다. 그 실행의 503 은 과부하이고(8시간 전인 10-14 00시에도 같은 503), 한도 거절이 아니다.
- 모델별로는 둘 다 8시간 미만이라, 한도 단위가 **모델**인지 **프로젝트(키 — 키마다 GCP 프로젝트가 다르다)**인지는 이 데이터로 가를 수 없다. Google 문서(영상 이해 · 제한)도 "무료는 하루 YouTube 영상 8시간"만 적고 단위가 없다.
- 그래서 **두 누계를 다 센다** — 어느 쪽이 맞아도 넘지 않는다. 틀렸을 때도 Google 이 429 로 거절할 뿐이고(재요약은 그 실행 중단, 신규는 키를 돌린 뒤 설명란 대체 — 기존 경로), 403 난사와는 무관하다.
- 참고: 파이프라인은 오류가 날 때만 키를 바꾸므로 하루 사용량이 키 1~2개에 몰린다(10-15 00시: 키 #1 → #2 → #3 → #4).

## 2. 설계 결정 (대표님 결정 10-15 10:52 — 바꾸지 말 것)

| 항목 | 결정 |
|---|---|
| 누계 | `.video_quota.json` = `{date(PT), seconds, calls, models{모델: 초}, keys{키 id: 초}, legacy}`. 키 id = 키의 sha256 앞 8자리 — **키 원문을 파일에 쓰지 않는다**. `seconds`·`calls` 는 전체 합계(표시·하위호환) |
| 판단 | 요청 전 **그 모델 누계 + 영상 초** 와 **지금 키 누계 + 영상 초** 가 둘 다 `VIDEO_DAILY_SECONDS`(기본 28800) − `reserveSeconds` 이하일 때만. 모델이 찼으면 `daily_video_cap`. 키가 찼으면 로그 `⏭ 이 키의 오늘 영상 분량이 찼다 — 다음 키` 후 `rotateKey`, 키 수 − 1 번 돌아도 차 있으면 `daily_video_cap`(detail `keys`) — 요청 0 |
| 세는 법 | 실패 요청도 센다(그대로). 모델·합계·calls 는 영상 1편에 1회. 키는 **재시도로 요청을 받은 키마다** 센다(429·5xx 로 키를 돌렸으면 그 키들 모두) |
| 첫날 | `models` 가 없는 파일(v4.13 전)의 그날 `seconds` 는 `legacy` 로 옮겨 모든 모델·키 누계에 더한다 — 보수적, 그 PT 하루만. 날짜가 바뀌면 0 |
| 재요약 예약 | `lib/resummarize.js` `RESUMMARY_RESERVE_SECONDS` 기본 10800 → **0**(`.env` 에 이 키 없음 — 맥 확인 10-15). 값을 주면 재요약은 모델·키 누계 둘 다에서 그만큼 남긴다 |
| 무변경 | 장부·스키마(user_version 3)·`.env` · 재요약 실행당 5편·하루 20편 · 신규 경로 재시도(키 4개 × 2회) · 5xx 상한(v4.11) · 실패 사유 분류 |
| 범위 밖 | `RESUMMARY_DAILY_MAX` 올리기(3.5 Flash-Lite 무료 하루 요청 한도 미확인) · 재요약 전용 키 지정 · 키를 오류 없이도 돌려 고르게 쓰기 |
| 함께 | v4.12 지시서 시각 표기 2곳 정정(시험 18:33~18:45 · 사전 검증 18:47~18:56 — 동작 무관) |

## 3. 파일

| 파일 | 내용 |
|---|---|
| `docs/tasks/patches/2026-10-15-v413-video-quota-per-model-key.patch` | 기준 = `a78da1e`, 8개 파일, +132 −29 |
| `docs/tasks/2026-10-15-v413-video-quota-per-model-key.md` | 이 지시서 |

```
sha256  1580c147a42c6b487ca61ad29d7cc7285e0d933042e2c11a0f785e1547f4ae0e  docs/tasks/patches/2026-10-15-v413-video-quota-per-model-key.patch
```

| 패치 안 파일 | 변경 |
|---|---|
| `lib/video_summary.js` | 머리 설명 5줄 · `crypto` · `readQuota`(models·keys·legacy) · `modelUsed`·`keyUsed`·`keyId` · 요청 전 모델·키 검사 · 요청 키 기록 · 누계 쓰기 · export |
| `lib/resummarize.js` | 머리 설명 3줄 · `DEFAULTS.reserveSeconds` 0 |
| `scripts/test_video_summary.js` | 머리 1항목 · +4건(모델별 · 키별 넘기기·모두 참 · 재시도 키 · legacy) → 32건 |
| `scripts/test_resummarize.js` | 예약 기본값 기대 10800 → 0 (1곳) |
| `CLAUDE.md` · `AGENTS.md` · `README.md` | 머리 버전 v4.13 · 요약 1줄 · 테스트 수 · 실제 영상 요약·재요약 절 · 이력 / README 요약 1줄 · `.env` 예시 · 구조 주석 · 요약 행 · 상세 1절 · 재요약 표. AGENTS.md = 머리글 5줄 + CLAUDE.md 4행부터 |
| `docs/tasks/2026-10-14-v412-promo-share.md` | 시각 표기 2곳 |

### Cowork 사전 검증 (2026-10-15 10:55~10:58, 레포 무변경 — 패치 파일만 놓음)

- 클라우드(Node 22): 새 테스트 4건이 옛 코드에서 실패(`test_video_summary.js` FAIL 4 · `test_resummarize.js` FAIL 1)하고 새 코드에서 통과(32/32 · 11/11).
- 맥 네이티브(홈 임시 폴더 `git archive a78da1e` + 이 패치): **회귀 14종 전부 통과** — scheduler_guards 33 · video_summary 32 · resummarize 11 · wiki_search 34 · recategorize_tips 52 · title_fetch 43 · kakao_ingest 37 · verify_library 16 · retitle_tips 49 · wiki_ingest 64 · sync_obsidian 32 · sheet_mirror 45 · build_wiki_index 15 · backup_library 50.
- 맥 모의(실제 `.video_quota.json` 사본, 요청은 가짜 400 — 네트워크 0): 오늘(PT 10-14) 파일 `{seconds 17524, calls 24}` → legacy 17524. 945초 재요약 후보가 예약 10800 이면 `daily_video_cap`(지금과 같음), v4.13(예약 0)이면 요청함. 쓴 뒤 `{seconds 18469, calls 25, models{3.5 Flash-Lite 945}, keys{<8자리> 945}, legacy 17524}` — 키 원문 없음.

## 4. 기대 효과

| | v4.12 | v4.13 |
|---|---|---|
| 재요약 한도 | 합계 18,000초에서 신규가 쓴 만큼 줄어듦 | 3.5 Flash-Lite 누계 28,800초 · 키별 28,800초 |
| 신규가 많은 날 재요약 | 약 9편에서 `daily_video_cap` | 하루 20편 상한까지(20편 ≈ 12,000초) |
| 남은 2,981편 | 약 10개월 | 약 5개월 |
| 배포 당일(PT 10-14 계속, 합계 17,524 = legacy) | 재요약 0편 | 재요약 여유 11,276초 |

## 5. 실행 — 적용·테스트·커밋

### 5-0. 시간

스케줄러가 00·06·12·18시, wiki-ingest 가 17:30 에 돈다. **매시 50분 ~ 다음 시 20분, 17:25~17:45 에는 5-2 이후를 시작하지 않는다.**
판정은 시각의 **분**으로 한다 — `date '+%H:%M'` 의 분이 50~59 또는 00~20 이면(어느 시든) 창 **안**이다. 예: 12:15 는 창 안, 12:25 는 창 밖.
(이 지시서는 장부를 쓰지 않지만, 스케줄러가 패치 도중의 `lib/*.js` 를 읽지 않게 창을 피한다.)

### 5-1. 시작 상태 (읽기만)

```bash
cd <REPO_ROOT>
date '+%H:%M'                                            # 창 밖이어야 한다
git --no-optional-locks rev-parse --short HEAD          # a78da1e
git --no-optional-locks status --porcelain
#   기대: 아래 두 줄만
#   ?? docs/tasks/2026-10-15-v413-video-quota-per-model-key.md
#   ?? docs/tasks/patches/2026-10-15-v413-video-quota-per-model-key.patch
shasum -a 256 docs/tasks/patches/2026-10-15-v413-video-quota-per-model-key.patch   # 3절 값과 같아야 한다
grep -o '"outcome": "[a-z]*"' .run_state.json            # "ok" (running 이면 멈춤 — 스케줄러 실행 중)
pgrep -fl scheduler.js || echo "scheduler 미실행"         # 미실행이어야 한다
grep -c '^RESUMMARY_RESERVE_SECONDS=' .env               # 0 (값은 출력하지 않는다)
```

어긋나면 **멈추고 보고**한다.

### 5-2. 패치 적용

```bash
git apply --check docs/tasks/patches/2026-10-15-v413-video-quota-per-model-key.patch && git apply docs/tasks/patches/2026-10-15-v413-video-quota-per-model-key.patch
git --no-optional-locks status --porcelain
#   기대: M AGENTS.md · M CLAUDE.md · M README.md · M docs/tasks/2026-10-14-v412-promo-share.md · M lib/resummarize.js
#         M lib/video_summary.js · M scripts/test_resummarize.js · M scripts/test_video_summary.js · ?? 지시서 · ?? 패치
git --no-optional-locks diff --stat | tail -1            # 8 files changed, 132 insertions(+), 29 deletions(-)
{ head -5 AGENTS.md; tail -n +4 CLAUDE.md; } | cmp - AGENTS.md && echo AGENTS_OK
/opt/homebrew/bin/node --check lib/video_summary.js && /opt/homebrew/bin/node --check lib/resummarize.js && echo SYNTAX_OK
```

### 5-3. 회귀 테스트 14종 (네트워크 0회, 실제 장부·Vault·.env 무관)

```bash
/opt/homebrew/bin/node scripts/test_scheduler_guards.js      # 33/33 PASS
/opt/homebrew/bin/node scripts/test_video_summary.js         # 32/32  (+4)
/opt/homebrew/bin/node scripts/test_resummarize.js           # 11/11
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

### 5-4. 지금 분량 파일 읽기 확인 (읽기만 — 쓰기·네트워크 0)

```bash
/opt/homebrew/bin/node -e "
const vs=require('./lib/video_summary'); const rs=require('./lib/resummarize');
const t=()=>new Intl.DateTimeFormat('en-CA',{timeZone:'America/Los_Angeles'}).format(new Date());
const q=vs.readQuota('.video_quota.json',t);
console.log(q.date, q.seconds, q.legacy, vs.modelUsed(q,'gemini-3.5-flash-lite'), rs.settings({}).reserveSeconds, vs.keyId('x').length);"
#   기대: <PT 날짜> <seconds> <legacy> <3.5 Flash-Lite 누계> 0 8
#   PT 10-14 이면(KST 16:00 전) "2026-10-14 17524 17524 17524 0 8" — 그 뒤 정시 실행이 돌았으면 출력 그대로 보고
```


## 6. 커밋 (push 하지 않음)

```bash
git add AGENTS.md CLAUDE.md README.md lib/video_summary.js lib/resummarize.js scripts/test_video_summary.js scripts/test_resummarize.js \
        docs/tasks/2026-10-14-v412-promo-share.md \
        docs/tasks/2026-10-15-v413-video-quota-per-model-key.md docs/tasks/patches/2026-10-15-v413-video-quota-per-model-key.patch
git commit -m "v4.13 영상 하루 분량을 모델별·키별로 — 재요약이 신규 몫에 막히지 않게 (예약 기본 0)"
git --no-optional-locks status --porcelain       # 커밋 뒤 기대: 빈 출력
git --no-optional-locks log --oneline -2
git --no-optional-locks show --stat HEAD | tail -11   # 10개 파일
```

## 7. 데몬

재기동 없음. `lib/video_summary.js`·`lib/resummarize.js` 는 정시 실행(`scheduler.js`)마다 새로 읽힌다 — 커밋 뒤 첫 정시 실행부터 적용. 상주 데몬(`server`·`wiki-lan`)은 이 파일을 쓰지 않는다.

## 8. 롤백

- 커밋 전: `git checkout -- AGENTS.md CLAUDE.md README.md docs/tasks/2026-10-14-v412-promo-share.md lib/video_summary.js lib/resummarize.js scripts/test_video_summary.js scripts/test_resummarize.js` (지시서·패치는 untracked 로 남김).
- 커밋 뒤(push 전): `git reset --hard a78da1e` 는 지시서·패치까지 지우므로 쓰지 않는다 → `git revert --no-edit HEAD`.
- 되돌려도 `.video_quota.json` 의 `models`·`keys`·`legacy` 는 무해하다(옛 코드는 `seconds`·`calls` 만 읽는다).
- 급히 예전 동작(재요약 신규 몫 3시간)만 되살리려면 코드 대신 `.env RESUMMARY_RESERVE_SECONDS=10800`.
- 첫 실행들에서 영상 요청 429(`⏳ 영상 요약 429`)가 잦으면 한도 단위 추정이 틀린 것 — Cowork 판단 후 되돌림 또는 예약 복구.

## 9. 보고

5-1 ~ 6 의 각 명령 출력(기대값과 다르면 그 줄을 먼저), 커밋 해시, `show --stat` 마지막 11줄.

## 10. 범위 밖

- push(다음 지시).
- `RESUMMARY_DAILY_MAX`·`RESUMMARY_PER_RUN` 조정 · 재요약 전용 키 · 키 고르게 쓰기.
- 첫 정시 실행 판정(Cowork) — `🔁 재요약: N편`(5 기대) · `.video_quota.json` 의 `models`·`keys`·`legacy` · 영상 429 유무 · 신규 영상이 설명란으로 밀리지 않는지.
