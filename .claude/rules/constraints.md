---
paths:
  - "**/*.py"
  - "**/*.js"
  - "**/*.sh"
  - "**/*.plist"
  - "lib/**"
  - "scripts/**"
  - "gas/**"
  - "playlists.json"
---

# 중요한 제약사항 전문 (루트 CLAUDE.md 에서 이관 — 2026-11-11)

> 위 경로의 파일을 Read 하면 자동으로 읽힌다. 코드·plist·장부를 건드리기 전에는 직접 Read 해도 된다. 구현·검수 전에 반드시 읽는다. 루트 CLAUDE.md 와 어긋나면 **루트가 우선**한다. 아래는 옮기기 전 본문이다(글자 그대로).

**장부 캐시 — 전부 읽었거나, 던지거나 (v3.2.1 → v4.0) — 건드리지 말 것**

v4.0 2단계부터 `scheduler.js:loadLibraryCache()`(장부 `videos` 전량)가 중복 판정의 유일한 근거다. 아래 이력은 노션 캐시 시절 것이지만 원칙은 같다. `scheduler.js:loadNotionCache()` 는 중복 판정의 유일한 근거였다. 빈 캐시·부분 캐시가 한 번이라도 반환되면 전 영상이 신규로 보여 `MAX_NEW_PER_RUN`(15)편을 다시 요약·저장한다. 2026-08-12 ~ 10-01 사이 13회 발생해 Notion 중복 195건이 쌓였고, 결과가 "저장 15 · Skip 0 · 오류 0" 이라 성공으로 보였다.

- 장부 파일이 없으면 `lib/library.js:openLibrary()` 가 **만들지 않고 던진다.** 빈 장부를 새로 만들면 전 영상이 신규로 보인다. `user_version` 이 스키마와 다르면 던진다.
- 0건은 **던진다**. 빈 `Map` 반환으로 바꾸지 말 것. `main` 이 받아 영상 처리와 큐 재시도를 건너뛰고 텔레그램으로 알린다(fail-closed).
- 새로 만든 빈 장부로 처음 돌릴 때만 `.env` 에 `LIBRARY_ALLOW_EMPTY=true`. 평소에는 넣지 않는다. (`NOTION_CACHE_ALLOW_EMPTY` 는 더 이상 읽지 않는다)
- `insertVideo` 는 같은 video_id 를 덮어쓰지 않는다(UNIQUE 위반으로 던짐 → 오류 1건). `INSERT OR REPLACE` 로 바꾸지 말 것.
- **스케줄러 결과가 "저장 15 · Skip 0" 이면 성공이 아니라 캐시 이상을 의심한다.**

**YouTube 조회 재시도·배치 (v3.2.1)**

- `ytFetch()` 는 네트워크 오류·429·5xx 만 지수 백오프(2→16초, 최대 5회)로 재시도한다. 401/403 은 즉시 던진다 — 재시도 대상을 넓힐 때 이 구분을 지우지 말 것.
- 채널 구독자 수는 `getBatchSubs()` 로 50개씩 순차 조회한다. 채널마다 `Promise.all` 로 부르던 방식(실행당 새 연결·유닛 약 450)으로 되돌리지 말 것.
- `scheduler.js` 는 `require.main === module` 일 때만 `main` 을 돈다. 이 가드를 지우면 테스트가 실제 실행을 일으킨다.

**한글 NFC 정규화**: macOS는 파일명을 NFD로 저장함. 장부 topics·tags, 재생목록명, Obsidian 파일명은 모두 `.normalize('NFC')` 필수. `lib/library.js:addTopic()`(v4.0, 장부의 현재 topics 를 다시 읽어 NFC 합집합)이 중복 태그 방지의 핵심.

**YouTube Quota**: 일일 10,000 유닛, 태평양시 자정 리셋 = **KST 16:00**. `playlistItems.insert` 50유닛, 대부분의 읽기 1유닛, `search.list` 100유닛. 안전 버퍼 500을 뺀 임계 **9,500유닛**(`QUOTA_THRESHOLD`) 도달 시 `pending_playlist_adds.json`에 적재 후 다음 실행에서 처리.

- **실패 요청도 quota를 동일하게 소비한다.** v2.5에서 `addToPlaylist`의 실패 경로에도 `consumeQuota(50)`을 넣었다(`lib/youtube_oauth.js:217`). 이전에는 실패가 계상되지 않아 `.quota_state.json`이 0에 머무른 채 실제 한도를 넘겼다.
- 따라서 **하루 재생목록 추가 상한은 약 190건**이다(9,500 ÷ 50). 코드로 늘릴 수 없다.
- 무료 할당량이자 상한선이라 **초과해도 과금되지 않는다.** 403으로 거부될 뿐이다.
- **일 경계는 태평양시(PT) 기준이다** (v2.6). `todayKey()`가 `Intl.DateTimeFormat('en-CA', { timeZone: 'America/Los_Angeles' })`를 쓴다(`lib/youtube_oauth.js:45`). UTC를 쓰면 카운터만 KST 09:00에 리셋돼 **09:00~16:00 동안 스로틀이 무력화**된다. 실패도 50유닛을 먹으므로 소진된 quota에 계속 요청을 밀어넣게 된다. **날짜 키를 만드는 코드를 새로 쓸 때는 반드시 `todayKey()`를 재사용할 것** — `scheduler.js:1475`의 텔레그램 경고도 같은 키를 써야 오경보가 안 난다.
- `.quota_state.json` 스키마는 **`{date, used, ok, fail}`** 이다 (v2.7). `ok`/`fail`은 `playlistItems.insert`의 성공·실패 건수이고, 읽기(`list`)는 `used`에만 반영된다. `consumeQuota(units, outcome)`의 `outcome`은 `'ok' | 'fail' | undefined`. 기존 파일에 `ok`/`fail`이 없으면 `loadQuotaState()`가 0으로 채운다(하위호환).
- `.quota_state.json`의 `date`가 **PT 기준 오늘**이 아니면 그날 YouTube 쓰기가 한 건도 시도되지 않았다는 뜻이다. 최우선 이상 신호.
- **`date`가 오늘이라고 정상인 것은 아니다.** 실패도 `date`를 찍는다. `fail > 0 && ok === 0`이면 **인증은 되는데 쓰기만 전부 실패** — 계정 불일치를 의심할 자리다(v2.7이 이 분기를 텔레그램으로 경고한다).
- 상태 파일이 멈춰 있으면 "동작 안 함"과 "계측 안 됨"을 **둘 다** 의심할 것. (2026-08-17 오판 이력)

**대기 큐 안전장치 (v2.5) — 건드리지 말 것**

`scheduler.js:flushPendingQueue()`와 `processMasterIngest()` 내부 `appendPending`에 들어간 장치입니다. 큐에 쓰는 코드는 `scheduler.js` 한 곳이다(같은 큐 파일에 쓰던 `migrate_classify.js` 는 v4.0 에서 `legacy_scripts/` 로 은퇴).

- `appendPending`은 `(videoId, playlistId)` 중복을 적재하지 않는다(`scheduler.js:1124`). 없으면 큐가 며칠 만에 2배로 부푼다. 실제 46.7%까지 중복된 이력이 있다.
- `flushPendingQueue`는 **연속 실패 10회에서 큐 처리를 중단**한다(`scheduler.js:894`). 403을 수백 번 난사하면 구글이 어뷰징으로 판단해 계정을 정지시킨다. 보안 원칙 1의 구현체다.
- `invalid_grant` / `Token refresh failed` 감지 시 큐를 보존한 채 즉시 중단한다.
- 영구 실패 사유(`playlistItemsNotAccessible`, `playlistNotFound`, `videoNotFound`, `forbidden`)는 dead-letter로 격리한다.
- 그 외 실패는 `retryCount` 5회 초과 시 dead-letter로 보낸다. 무한 순환 금지.

**YouTube OAuth — 가장 자주 깨지는 지점**

```
필요 채널 : 타이쿤안 (UCGDu0ceSSUgzhrRHbW0pQ9w)
GCP       : youtube-data-api-487306, 게시 상태 = 프로덕션
```

- 토큰 재발급 시 **반드시 「타이쿤안」 채널을 선택**한다. 다른 계정/채널로 발급하면 33개 재생목록 전체에 `403 playlistItemsNotAccessible`이 난다.
- **이 에러를 "재생목록이 삭제됨"으로 단정하지 말 것. 계정 불일치를 먼저 의심한다.** 2026-08-17에 이 오판으로 복구 가능한 165건을 영구 폐기할 뻔했다.
- GCP 게시 상태가 「테스트」로 돌아가면 refresh token이 **7일마다 만료**된다. `invalid_grant`가 재발하면 게시 상태부터 확인한다.
- 재발급 중 `accounts.google.com/info/unknownerror`가 뜨면 다중 로그인 세션 충돌이다. 출력된 URL을 **시크릿 창**에 붙여넣는다.
- 발급 후 위 §"OAuth 계정 일치 검증"을 먼저 돌린다(1유닛).

**wiki-ingest 의 Gemini 무료 할당량 — 3중 함정 (2026-09-10)**

`wiki_config.py:gemini_call`. 로그 근거: `~/Library/Logs/irichgreen/wiki-ingest.log` WIKI_RESULT 29회 = processed 212 / errors 165(44%).
오류 내역은 **429 125건(RPD 108 + RPM 17) · 503 39건 · 타임아웃 1건**. 파싱 실패는 0건이다.

- **429 는 두 종류다. `quotaId` 로만 구분된다.** 응답 `error.details[].QuotaFailure.violations[].quotaId` 가
  `GenerateRequestsPerDayPerProjectPerModel-FreeTier`(quotaValue 20)면 RPD,
  `GenerateRequestsPerMinutePerProjectPerModel-FreeTier`(quotaValue 5)면 RPM이다.
  `RetryInfo.retryDelay` 에 권장 대기시간이 같이 온다. **추측으로 분기하지 말 것 — 근거는 응답 안에 있다.**
  예전 코드는 둘을 구분하지 않고 전부 `dead` 처리해서 분당 한도 한 번에 키 하나를 하루치 통째로 버렸다.
  지금은 RPM이면 `retryDelay+2`초(상한 65) 대기 후 **같은 키로** 재시도하고, RPD일 때만 dead 처리한다.
  `quotaId` 가 없으면 `unknown` — 본문 전체를 로그에 남기고 보수적으로 RPD 취급한다.
- **5xx 는 재시도 대상이다.** 오류 165건 중 39건(24%)이 503인데 예전에는 그대로 올려서 소스가 떨어졌다.
  지금은 지수 백오프(2→15초 상한, 3회)로 같은 키에 재시도한다. `<urlopen error timed out>` 도 같은 취급.
  **`scheduler.js` v2.7.1 이 JS 쪽에서 고친 것과 같은 결함이었다. 한쪽만 고치면 다른 쪽이 남는다.**
- **일 경계는 태평양시다.** `_today()` 가 `time.gmtime(now - 8h)` 를 쓴다. KST 자정 기준으로 세면
  로컬 카운터만 리셋되고 구글 RPD 는 그대로라, **00시 실행이 매번 '깨끗한 장부'로 시작해 즉시 429 를 맞는다.**
  `lib/youtube_oauth.js:todayKey()` 와 같은 취지의 교정이다.

**wiki_ingest 실행 경로는 두 개다 (2026-09-10)**

```
① launchd  com.irichgreen.wiki-ingest         매일 17:30 (= PT 01:30, RPD 리셋 직후)
② scheduler.js:1525  totalSaved === 0  →  sync_obsidian.py --rebuild
     └ sync_obsidian.py:516  --rebuild → force=True
       └ sync_obsidian.py:538  subprocess.run([sys.executable, 'wiki_ingest.py', '--no-backfill'], capture_output=True)
```

②는 **저장 0건인 스케줄러 실행마다(00/06/12/18시)** 돈다. 증분 모드라 할 일이 없으면 즉시 끝나고,
KST 00/06/12 시는 PT 기준 전날 장부·17:30 은 PT 당일 리셋 직후라 서로 할당량을 뺏지 않는다.
**②를 끄지 말 것 — 의도된 동작이다.**

- ②의 stdout 은 `capture_output=True` 라 예전에는 `ytsummarizer.log` 로 흡수돼
  `wiki-ingest.log` 에 아무것도 안 남았다. `.wiki_state.json` 의 `last_run` 만 갱신되고 로그는 그대로여서
  "안 도는 줄" 오판하기 좋았다(2026-09-10 06:01:11 사건).
  지금은 `sync_obsidian.py:_tee_wiki_log()` 가 캡처한 출력을 `wiki-ingest.log` 에 append 한다.
  `───── via sync_obsidian.py (subprocess) <ISO시각> ─────` 헤더가 붙고 **`WIKI_RESULT` 줄이 그대로 남는다.**
  `WIKI_RESULT` 가 유일한 판정 지표이므로 이 tee 를 지우면 ②는 다시 안 보이게 된다.
- **두 경로의 인터프리터는 같다: `/opt/homebrew/bin/python3`.**
  plist 의 `ProgramArguments`, `scheduler.js:1514`, `server.js:232` 가 모두 이 경로를 하드코딩하고,
  `sync_obsidian.py` 는 `sys.executable` 을 물려주므로 ②도 같은 파이썬을 탄다.
  **셋 중 하나만 바꾸면 라이브러리가 갈린다 — 바꿀 때는 3곳을 함께 고칠 것.**

**Gemini 분류 경로 — 요약 경로와 대응이 달랐던 자리 (v2.7.1)**

- `scheduler.js`의 분류 재시도 catch는 원래 **429/quota만** 재시도했다. 요약 경로(`:459`)는 503에 키 로테이션 + 재시도로 대응하는데 분류만 빠져 있어 **503 한 번에 영상이 떨어졌다**(2026-08-28 06:00 실제 발생). 지금은 `5xx`·`UNAVAILABLE`·`overloaded`·`high demand`도 지수 백오프(2→15초 상한)로 재시도한다. **분류 쪽 재시도 조건을 손댈 때 요약 경로와 대칭인지 먼저 확인할 것.**
- `401`/`403`은 **명시적으로 즉시 중단**한다(보안 원칙 1). 재시도 조건을 넓힐 때 이 가드를 지우지 말 것.
- 재시도 소진 시 `cls`가 `undefined`인 채 `cls.topics`로 진입하던 잠복 TypeError 경로가 있었다. `clsAttempt < maxClsAttempts` 가드와 루프 직후 `if (!cls) throw` **가드 2개가 짝**이다. 한쪽만 지우면 되살아난다.
- `classifyTopics`를 `maxRetries: 0`으로 호출하는 것은 **의도된 설계**다. 재시도는 키 교체를 하는 바깥 루프가 담당한다.
- (v4.14) 분류 모델은 `gemini-3.5-flash-lite`(2.5 Flash 하루 요청 한도를 영상 요약에 남긴다). 같은 프롬프트로 2.5 Flash 보다 토픽을 적게(비교 20편 4.4 → 2.5개) 붙인다 — 프롬프트의 「추상 토픽 남발 금지」를 지킨 결과라 의도된 변화다(대표님 결정 10-15). 예전 분류로 되돌릴 때는 코드가 아니라 `.env CLASSIFY_MODEL=gemini-2.5-flash`. 응답은 `Buffer.concat` 으로 모은다 — `chunks += c` 로 되돌리지 말 것(한글 토픽이 청크 경계에서 깨져 allowedSet 에서 떨어진다).

**Gemini API 최적화 (중요)**: Gemini 2.5 Flash 모델 사용 시 내부 추론 과정에서 과다한 "Thinking 토큰" 과금을 방지하기 위해 반드시 API 호출 옵션에 `generationConfig: { thinkingConfig: { thinkingBudget: 0 } }`를 적용해야 합니다 (비용 85% 절감 효과). (v4.6-b) 3.x 모델(`gemini-3.5-flash-lite` 등)은 `thinkingBudget` 을 400 INVALID_ARGUMENT 로 거절한다 — `thinkingConfig: { thinkingLevel: 'minimal' }`(`lib/video_summary.js:thinkingConfigFor`).

**토픽 추가 시**: `playlists.json`에 새 항목 추가 + `build_obsidian_wiki.py`의 `VALID_NOTION_TAGS` 동기화 필수.

**Vault 경로 중첩 (2026-09-19)**: 실제 Vault는 `~/Documents/Obsidian/AI LLM Wiki/AI LLM Wiki` (바깥 `AI LLM Wiki/`는 빈 껍데기, `README-여기가-아님.txt` 있음). 동작에 문제 없음. 이 경로는 `sync_obsidian.py`·`build_obsidian_wiki.py`·`wiki_config.py`·`lib/wiki_search.js`·`cleanup_duplicates.py`·`notion_to_obsidian.js` 6곳 + `legacy_scripts/` 2곳 + Obsidian 앱 등록에 박혀 있다. **v3.3(2nd_Brain 2단계 — `build_search_index.py`에 `_Brain/` 포함)과 같은 작업지시서로 한 단계 승격한다. 그 전에 옮기지 말 것.** 절차: 데몬 전부 stop(`wiki-lan` 포함 — 같은 Vault 경로를 읽는다) → `mv` → 8파일 치환 → Obsidian 재등록 → `--orphans-dry-run --no-tips`로 "notion_id 2,542·고아 0" 확인 → 인덱스 재빌드 → 재기동.

**server.js 보안**: `127.0.0.1` 전용 바인딩. CORS는 `localhost:3000`만 허용. IP당 분당 120요청 rate limit. 노션 프록시(v4.0 2-b)·`/api/sync-obsidian`(v4.0 3단계)은 제거됐다 — 다시 만들지 말 것.
