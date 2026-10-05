# 작업지시서 [CC-1005-A] — 스케줄러 네트워크 안전장치 (v3.2.1)

- 작성: 2026-10-05 · Cowork
- 영역: **Node** (`scheduler.js`)
- 대상 파일: `scheduler.js`, `scripts/test_scheduler_guards.js`(신규), `README.md`, `CLAUDE.md`, `AGENTS.md`
- 요약: Notion 캐시를 다 읽지 못한 실행은 아무것도 저장하지 못하게 막고, YouTube 조회에 일시 오류 재시도를 넣고, 채널 구독자 수 조회를 채널당 1회·동시 호출에서 50개 배치 순차 호출로 바꾼다.

## 1. 배경

### 증상

`~/Library/Logs/irichgreen/ytsummarizer.log`(회전본 포함, 2026-08-12 ~ 10-05, 스케줄러 실행 219회)를 집계한 결과다.

| 구분 | 횟수 | 내용 |
|---|---|---|
| 실행 통째 실패 (`저장 0 · Skip 0 · 오류 1`) | 62회 (28%) | `ENOTFOUND` 41 · `ETIMEDOUT` 17 · 기타 4 |
| Notion 캐시 0건으로 진행 | 23회 | 그중 13회가 영상 15편씩 다시 저장 → **중복 저장 195건** |

중복 저장은 결과가 `저장 15 · Skip 0 · 오류 0` 이라 텔레그램에서 성공으로 보였다. Notion 실측으로 같은 영상의 페이지가 15개까지 확인됐고, 생성일이 빈 캐시 실행 13회의 날짜(08-25, 08-26, 08-31, 09-01, 09-03, 09-07, 09-10, 09-14, 09-15, 09-16, 09-18, 09-29, 10-01)와 일치한다. 한 번 터질 때마다 Gemini 호출 약 45회(15편 × 최소 3회)가 이미 저장된 영상에 쓰였다.

### 원인

1. **`loadNotionCache()` 가 빈 캐시를 정상값처럼 반환한다.** 루프가 `do { … } while (cursor)` 인데, 첫 페이지 조회가 네트워크 오류로 실패하면 `continue` 가 조건 검사로 넘어간다. 그 시점의 `cursor` 는 `undefined` 라 루프가 끝난다. 로그에는 `재시도 1/10` 만 찍히고 곧바로 `캐시 완료: 0개 페이지 로드` 가 나온다. 캐시가 비면 전 영상이 신규로 판정돼 `MAX_NEW_PER_RUN`(15)편을 다시 요약·저장한다. 같은 함수의 `status !== 200` 경로도 재시도 초과 시 `break` 로 **부분 캐시**를 반환한다(로그상 발생 0회, 같은 위험).
2. **`ytFetch()` 에 재시도가 없다.** YouTube 조회 한 번이 실패하면 `processMasterIngest` 가 던지고 `main` 의 catch 가 실행 전체를 `오류 1` 로 끝낸다.
3. **채널 구독자 수를 채널마다 따로·동시에 조회한다.** `Promise.all(uniqueChannels.map(getSubs))` — 2026-10-05 기준 고유 채널 450개. 실행마다 새 연결 약 450개가 한꺼번에 열리고 유닛도 450을 쓴다. `channels.list` 는 한 번에 50개를 받는다.

### 확인하지 못한 것

야간(00시·06시) `ENOTFOUND` 의 직접 원인은 밝히지 못했다. 데몬과 같은 node 로 동시 DNS 조회 449개 × 3회, 1,000개 × 1회를 시험했으나 전부 성공했다(주간). 이 지시서는 원인이 무엇이든 동작하는 방어(재시도, 연결 수 축소, fail-closed)만 넣는다.

### 사전 검증 (Cowork, 2026-10-05)

아래 TO-BE 를 적용한 사본으로 확인했다. 맥의 실제 `scheduler.js` 에 적용한 결과는 4절에서 다시 확인한다.

- `scripts/test_scheduler_guards.js` 12/12 PASS. 수정 전 코드에 같은 테스트를 돌리면 3/12(빈 캐시 재현 포함).
- 모의 실행 2종(네트워크 전면 실패, Notion 401) 기대대로 동작.
- 읽기 전용 실측(데몬과 같은 node): 캐시 3,041 페이지 · 영상 1,412 · 고유 채널 450 · 구독자 수 응답 450 · 신규 판정 23. 구독자 수 조회 1.1초.
- `channels.list` 에 채널 ID 50개를 넘기면 `maxResults` 유무와 관계없이 50개가 온다(실측).

## 2. 수정 — `scheduler.js`

위에서 아래 순서다. 각 AS-IS 는 파일에 정확히 한 번 나온다. 한 번이 아니면 멈추고 보고한다.

### 2-1. `ytFetch` — 일시 오류 재시도

네트워크 오류·429·5xx 만 지수 백오프(2 → 4 → 8 → 16초, 상한 30초)로 재시도하고 5회째에 던진다. 401/403 을 포함한 그 밖의 응답은 지금처럼 즉시 던진다.

**AS-IS**

```js
// ── YouTube API 호출 ──
async function ytFetch(path) {
  const res = await httpsRequest({
    hostname: 'www.googleapis.com',
    path: `/youtube/v3/${path}&key=${CONFIG.youtubeApiKey}`,
    method: 'GET',
  });
  if (res.status !== 200) throw new Error(`YouTube API 오류 ${res.status}: ${JSON.stringify(res.data)}`);
  return res.data;
}
```

**TO-BE**

```js
// ── YouTube API 호출 ──
// 일시 오류(네트워크·429·5xx)만 지수 백오프로 재시도한다.
// 401/403 을 포함한 그 밖의 응답은 재시도 없이 즉시 던진다(보안 원칙 1) — 재시도 대상을 넓힐 때 이 구분을 지우지 말 것.
const YT_MAX_ATTEMPTS    = 5;      // 최초 1회 + 재시도 4회
const YT_BACKOFF_BASE_MS = 2000;   // 2 → 4 → 8 → 16초
const YT_BACKOFF_MAX_MS  = 30000;
const YT_RETRY_NET_CODES = new Set([
  'ENOTFOUND', 'EAI_AGAIN', 'ETIMEDOUT', 'ECONNRESET', 'ECONNREFUSED',
  'EPIPE', 'ENETUNREACH', 'EHOSTUNREACH', 'ENETDOWN',
]);

async function ytFetch(path) {
  for (let attempt = 1; ; attempt++) {
    let res, netErr;
    try {
      res = await httpsRequest({
        hostname: 'www.googleapis.com',
        path: `/youtube/v3/${path}&key=${CONFIG.youtubeApiKey}`,
        method: 'GET',
      });
    } catch (e) {
      netErr = e;
    }

    if (res && res.status === 200) return res.data;

    const failure = netErr || new Error(`YouTube API 오류 ${res.status}: ${JSON.stringify(res.data)}`);
    const label = netErr ? (netErr.code || netErr.message) : `HTTP ${res.status}`;
    const retryable = netErr
      ? YT_RETRY_NET_CODES.has(netErr.code)
      : (res.status === 429 || res.status >= 500);

    if (!retryable || attempt >= YT_MAX_ATTEMPTS) throw failure;

    const waitMs = Math.min(YT_BACKOFF_BASE_MS * 2 ** (attempt - 1), YT_BACKOFF_MAX_MS);
    log(`  ⚠️ YouTube 일시 오류 (${label}), ${waitMs / 1000}초 후 재시도 ${attempt}/${YT_MAX_ATTEMPTS - 1}...`);
    await new Promise(r => setTimeout(r, waitMs));
  }
}
```

### 2-2. `getSubs` → `getBatchSubs`

**AS-IS**

```js
// ── 채널 구독자수 ──
async function getSubs(channelId) {
  const d = await ytFetch(`channels?part=statistics&id=${channelId}`);
  return parseInt(d.items?.[0]?.statistics?.subscriberCount || 0);

}
```

**TO-BE**

```js
// ── 채널 구독자수 (최대 50개 배치 조회) ──
// 채널마다 따로·동시에 부르지 말 것. 새 연결이 채널 수만큼 한꺼번에 열리고 유닛도 채널 수만큼 든다.
// 응답에 없는 채널(삭제·비공개)은 맵에 넣지 않는다 — 호출부가 `|| 0` 으로 받는다.
async function getBatchSubs(channelIds) {
  const map = {};
  for (let i = 0; i < channelIds.length; i += 50) {
    const batch = channelIds.slice(i, i + 50);
    const d = await ytFetch(`channels?part=statistics&maxResults=50&id=${batch.join(',')}`);
    for (const it of (d.items || [])) {
      map[it.id] = parseInt(it?.statistics?.subscriberCount || 0);
    }
  }
  return map;
}
```

### 2-3. `loadNotionCache` — 루프 머리

**AS-IS**

```js
  let retryCount = 0;
  const MAX_RETRY = 10;          // 네트워크 복구 대기 포함해 여유 있게
  const NETWORK_WAIT_MS = 30000; // 네트워크 오류 시 30초 대기
  log('  📦 Notion DB 캐시 로딩 중...');
  do {
    const body = { page_size: 100 };
```

**TO-BE**

```js
  let retryCount = 0;
  let done = false;
  const MAX_RETRY = 10;          // 네트워크 복구 대기 포함해 여유 있게
  const NETWORK_WAIT_MS = 30000; // 네트워크 오류 시 30초 대기
  log('  📦 Notion DB 캐시 로딩 중...');
  // ★ `do { … } while (cursor)` 로 되돌리지 말 것. 첫 페이지에서 실패하면 `continue` 가 조건 검사로 넘어가는데
  //   cursor 가 아직 undefined 라 재시도 없이 빈 캐시로 끝난다. 빈 캐시는 전 영상을 신규로 보이게 해 중복 저장을 만든다.
  // ★ 이 함수는 "전부 읽었거나, 던지거나" 둘 중 하나다. 부분 캐시·빈 캐시를 반환하는 경로를 만들지 말 것.
  while (!done) {
    const body = { page_size: 100 };
```

### 2-4. `loadNotionCache` — 응답 상태 처리

401/403 은 재시도 없이 `fatalAuth` 로 던진다(지금은 10회 재시도한다). 재시도 초과는 `break` 대신 던진다. 200 인데 `results` 배열이 없는 응답도 오류로 본다.

**AS-IS**

```js
    if (res.status !== 200) {
      retryCount++;
      log(`  ⚠️ Notion API 오류 (status ${res.status}), 재시도 ${retryCount}/${MAX_RETRY}...`);
      if (retryCount >= MAX_RETRY) {
        log(`  ❌ Notion 캐시 로딩 실패 — 재시도 횟수 초과`);
        break;
      }
      await new Promise(r => setTimeout(r, 2000 * retryCount));
      continue;
    }
    retryCount = 0;
```

**TO-BE**

```js
    if (res.status === 401 || res.status === 403) {
      // 인증 만료·권한 거부는 재시도하지 않는다(보안 원칙 1). main 이 fatalAuth 를 보고 즉시 종료한다.
      const authErr = new Error(`Notion 인증·권한 오류 (status ${res.status})`);
      authErr.fatalAuth = true;
      throw authErr;
    }
    if (res.status !== 200 || !Array.isArray(res.data?.results)) {
      retryCount++;
      log(`  ⚠️ Notion API 오류 (status ${res.status}), 재시도 ${retryCount}/${MAX_RETRY}...`);
      if (retryCount >= MAX_RETRY) {
        throw new Error(`Notion 캐시 로딩 실패 — 재시도 횟수 초과 (status ${res.status}, ${total}개까지 로드)`);
      }
      await new Promise(r => setTimeout(r, 2000 * retryCount));
      continue;
    }
    retryCount = 0;
```

### 2-5. `loadNotionCache` — 루프 끝과 0건 가드

**AS-IS**

```js
    total += res.data?.results?.length || 0;
    cursor = res.data?.next_cursor;
    log(`  📦 캐시 진행: ${total}개 로드됨...`);
  } while (cursor);
  log(`  ✓ Notion DB 캐시 완료: ${total}개 페이지 로드`);
  return cache;
```

**TO-BE**

```js
    total += res.data.results.length;
    cursor = res.data.next_cursor;
    done = !cursor;
    log(`  📦 캐시 진행: ${total}개 로드됨...`);
  }
  if (total === 0 && process.env.NOTION_CACHE_ALLOW_EMPTY !== 'true') {
    throw new Error('Notion 캐시가 0건 — 새로 만든 빈 DB가 맞다면 .env 에 NOTION_CACHE_ALLOW_EMPTY=true 를 넣고 다시 실행');
  }
  log(`  ✓ Notion DB 캐시 완료: ${total}개 페이지 로드`);
  return cache;
```

### 2-6. 마스터 모드 호출부 (`processMasterIngest`)

**AS-IS**

```js
  const chCache = {};
  const uniqueChannels = [...new Set(videos.map(v => detailMap[v.videoId]?.realChannelId || v.channelId).filter(Boolean))];
  await Promise.all(uniqueChannels.map(async (chId) => { chCache[chId] = await getSubs(chId); }));
```

**TO-BE**

```js
  const uniqueChannels = [...new Set(videos.map(v => detailMap[v.videoId]?.realChannelId || v.channelId).filter(Boolean))];
  const chCache = await getBatchSubs(uniqueChannels);
```

### 2-7. 레거시 모드 호출부 (`processPlaylist`)

**AS-IS**

```js
  // ── 채널 구독자수 병렬 조회 (채널별 1회만) ──
  const chCache = {};
  const uniqueChannels = [...new Set(
    videos.map(v => detailMap[v.videoId]?.realChannelId || v.channelId).filter(Boolean)
  )];
  log(`  🔄 채널 구독자수 조회 중... (${uniqueChannels.length}개 채널)`);
  await Promise.all(uniqueChannels.map(async (chId) => {
    chCache[chId] = await getSubs(chId);
  }));
```

**TO-BE**

```js
  // ── 채널 구독자수 배치 조회 (50개씩 순차) ──
  const uniqueChannels = [...new Set(
    videos.map(v => detailMap[v.videoId]?.realChannelId || v.channelId).filter(Boolean)
  )];
  log(`  🔄 채널 구독자수 조회 중... (${uniqueChannels.length}개 채널)`);
  const chCache = await getBatchSubs(uniqueChannels);
```

### 2-8. `main` — 캐시 실패 시 영상 처리 건너뜀

캐시 로드가 던지면 `flushPendingQueue` 와 영상 처리를 건너뛰고 `오류 1` 로 집계한다. 결과 객체 모양은 기존 catch 경로와 같아서 뒤의 알림·카톡·Obsidian 단계는 손대지 않는다. `fatalAuth` 면 텔레그램 경고 후 즉시 종료한다(Gemini 403 처리와 같은 방식).

**AS-IS**

```js
  // ── Notion DB 전체 캐시 로드 ──
  const notionCache = await loadNotionCache();

  // ── pending 큐 소진 (quota 여유분 내에서) ──
  await flushPendingQueue();

  let totalSaved = 0, totalSkip = 0, totalError = 0;
  const results = [];

  if (useMasterMode) {
```

**TO-BE**

```js
  // ── Notion DB 전체 캐시 로드 ──
  // 캐시가 없으면 중복 판정을 못 한다. 로드에 실패하면 이번 실행은 영상 처리·큐 재시도를 건너뛴다(fail-closed).
  let notionCache = null;
  try {
    notionCache = await loadNotionCache();
  } catch (e) {
    if (e && e.fatalAuth) {
      log(`❌ ${e.message} — 추가 요청 없이 종료합니다.`);
      await sendTelegram(`🚨 <b>[작업 중단 알림]</b>\n${e.message}\nNotion 토큰·DB 공유 상태를 확인하세요. 프로세스를 중단했습니다.`);
      process.exit(1);
    }
    log(`❌ Notion 캐시 로드 실패 — 중복 저장을 막기 위해 이번 실행은 영상 처리를 건너뜁니다: ${e.message}`);
  }

  // ── pending 큐 소진 (quota 여유분 내에서) ──
  if (notionCache) await flushPendingQueue();

  let totalSaved = 0, totalSkip = 0, totalError = 0;
  const results = [];

  if (!notionCache) {
    totalError += 1;
    results.push({ name: useMasterMode ? 'AI 영상목록 (마스터)' : 'Notion 캐시', saved: 0, skip: 0, error: 1 });
  } else if (useMasterMode) {
```

### 2-9. 진입점 — `require` 가능하게

launchd 와 `server.js` 는 `scheduler.js` 를 직접 실행하므로 동작은 같다. `require` 했을 때만 함수를 내보낸다.

**AS-IS**

```js
main().catch(e => {
  log(`❌ 치명적 오류: ${e.message}`);
  process.exit(1);
});
```

**TO-BE**

```js
// 직접 실행할 때만 main 을 돈다. require 하면 아래 함수만 내보낸다(scripts/test_scheduler_guards.js·읽기 전용 점검용).
if (require.main === module) {
  main().catch(e => {
    log(`❌ 치명적 오류: ${e.message}`);
    process.exit(1);
  });
} else {
  module.exports = { ytFetch, getVideos, getBatchDetails, getBatchSubs, loadNotionCache, findDuplicate };
}
```

## 3. 신규 — `scripts/test_scheduler_guards.js`

**Cowork 가 레포에 미리 넣어 두었다(미추적 상태).** 내용을 고치지 말고 그대로 커밋에 포함한다. 파일이 없으면 멈추고 보고한다.

- `https.request` 를 가짜로 바꾼 뒤 `scheduler.js` 를 `require` 한다. 실제 네트워크 요청은 0회다.
- `scheduler.log` 에 쓰지 않고, 백오프 대기는 건너뛴다.
- `scheduler.js` 에 `require.main === module` 가드가 없으면 실행을 거부한다(exit 2). **2-9 를 적용하기 전에는 돌리지 않는다.**

## 4. 검증

레포 루트에서 순서대로 실행한다. 하나라도 기대와 다르면 커밋하지 말고 멈춘다. **이 지시서에서는 `node scheduler.js` 를 직접 실행하지 않는다** — 실제 실행 검증은 다음 정기 실행(launchd)을 Cowork 가 확인한다.

### 4-1. 문법·잔존 확인

```bash
/opt/homebrew/bin/node --check scheduler.js && echo SYNTAX_OK
grep -c 'getSubs(' scheduler.js
grep -c 'Promise.all(uniqueChannels' scheduler.js
grep -c '} while (cursor);' scheduler.js
grep -c 'require.main === module' scheduler.js
```

기대 출력: `SYNTAX_OK`, `0`, `0`, `0`, `1`

### 4-2. 회귀 테스트

```bash
B=$(stat -f %m scheduler.log)
/opt/homebrew/bin/node scripts/test_scheduler_guards.js; echo "exit=$?"
[ "$B" = "$(stat -f %m scheduler.log)" ] && echo LOG_UNTOUCHED
```

기대 출력: `PASS` 12줄, `12/12 PASS`, `exit=0`, `LOG_UNTOUCHED`. (`LOG_UNTOUCHED` 는 테스트가 실제 로그 파일에 쓰지 않았다는 확인이다. 정기 실행이 도는 중이면 로그가 따로 갱신되니 그때는 피해서 돌린다.)

### 4-3. 모의 실행 — 네트워크 전면 실패

네트워크·자식 프로세스·로그 파일을 가짜로 바꾸는 preload 를 임시 폴더에 만들어 `main` 전체 흐름을 돌린다. preload 는 커밋하지 않는다.

```bash
SIM_DIR="$(mktemp -d)"; SIM="$SIM_DIR/sim_preload.js"
cat > "$SIM" <<'EOF'
// 모의 실행용 preload — 네트워크·자식 프로세스·로그 파일을 모두 가짜로 바꾼다. 커밋하지 않는다.
const https = require('https'), fs = require('fs'), cp = require('child_process'), path = require('path');
const { EventEmitter } = require('events');
const MODE = process.env.SIM_MODE || 'enotfound';
fs.appendFileSync = () => {};
const realSetTimeout = global.setTimeout;
global.setTimeout = (fn, _ms, ...a) => realSetTimeout(fn, 0, ...a);
https.request = (o, cb) => {
  const req = new EventEmitter();
  req.write = () => {};
  req.end = () => realSetTimeout(() => {
    console.log(`[SIM] 요청 가로챔: ${o.hostname}`);
    if (MODE === '401' && o.hostname === 'api.notion.com') {
      const res = new EventEmitter(); res.statusCode = 401; cb(res);
      res.emit('data', Buffer.from('{"code":"unauthorized"}')); res.emit('end'); return;
    }
    const e = new Error('getaddrinfo ENOTFOUND ' + o.hostname); e.code = 'ENOTFOUND'; req.emit('error', e);
  }, 0);
  return req;
};
cp.execFile = (file, args, opts, cb) => {
  console.log(`[SIM] 자식 프로세스 생략: ${path.basename(args[0])} ${args.slice(1).join(' ')}`.trim());
  cb(null, 'RESULT_JSON:{"skipped":"sim"}\n', '');
};
EOF
TELEGRAM_ENABLED=false EMAIL_ENABLED=false /opt/homebrew/bin/node -r "$SIM" scheduler.js > "$SIM_DIR/net.log" 2>&1; echo "exit=$?"
grep -E '\[SIM\]|캐시 로드 실패|완료! 저장|Notion 저장 완료' "$SIM_DIR/net.log" | sed -E 's/^\[2026[^]]*\] //' | sort | uniq -c
```

기대 출력(순서는 다를 수 있다):

```
exit=0
   1   완료! 저장: 0개 / Skip: 0개 / 오류: 1개
  10 [SIM] 요청 가로챔: api.notion.com
   1 [SIM] 자식 프로세스 생략: kakao_ingest.py --apply --if-new
   1 [SIM] 자식 프로세스 생략: sync_obsidian.py --rebuild
   1 ❌ Notion 캐시 로드 실패 — 중복 저장을 막기 위해 이번 실행은 영상 처리를 건너뜁니다: getaddrinfo ENOTFOUND api.notion.com
```

판정 기준: `www.googleapis.com` 요청이 **한 줄도 없고**, `Notion 저장 완료` 가 **없어야** 한다.

### 4-4. 모의 실행 — Notion 401

4-3 과 같은 셸에서 이어서 실행한다.

```bash
SIM_MODE=401 TELEGRAM_ENABLED=false EMAIL_ENABLED=false /opt/homebrew/bin/node -r "$SIM" scheduler.js > "$SIM_DIR/401.log" 2>&1; echo "exit=$?"
grep -E '\[SIM\]|종료합니다|완료! 저장' "$SIM_DIR/401.log" | sed -E 's/^\[2026[^]]*\] //'
rm -rf "$SIM_DIR"
```

기대 출력:

```
exit=1
[SIM] 요청 가로챔: api.notion.com
❌ Notion 인증·권한 오류 (status 401) — 추가 요청 없이 종료합니다.
```

판정 기준: Notion 요청이 **1회**뿐이고 `자식 프로세스 생략` 줄이 없어야 한다.

### 4-5. 읽기 전용 실측

실제 Notion·YouTube 를 읽기만 한다(Notion 조회 약 31회, YouTube 약 70유닛). Gemini 호출·쓰기는 없다.

```bash
/opt/homebrew/bin/node -e "
require('fs').appendFileSync = () => {};   // scheduler.log 에 쓰지 않는다
const s = require('./scheduler.js');
(async () => {
  const cache = await s.loadNotionCache();
  const videos = await s.getVideos(process.env.YOUTUBE_MASTER_PLAYLIST_ID);
  const det = await s.getBatchDetails(videos.map(v => v.videoId));
  const ch = [...new Set(videos.map(v => det[v.videoId]?.realChannelId || v.channelId).filter(Boolean))];
  const subs = await s.getBatchSubs(ch);
  const fresh = videos.filter(v => !s.findDuplicate(v, cache)).length;
  console.log('RESULT 영상', videos.length, '| 고유채널', ch.length, '| 구독자수 응답', Object.keys(subs).length, '| 신규 판정', fresh);
})().catch(e => { console.log('RESULT 실패', e.code || e.message); process.exit(1); });
" | grep -E 'RESULT|캐시 완료|재시도'
```

기대 출력(숫자는 그날 값):

```
[시각]   ✓ Notion DB 캐시 완료: 30xx개 페이지 로드
RESULT 영상 141x | 고유채널 45x | 구독자수 응답 45x | 신규 판정 NN
```

판정 기준:

- `구독자수 응답` 이 `고유채널` 과 같거나 몇 개 적다(삭제·비공개 채널).
- `신규 판정` 이 수십 이하이고 `영상` 수와 같지 않다. 2026-10-05 12:09 실측은 23(Gemini 한도 때문에 밀린 영상).
- `RESULT 실패` 가 나오면 멈추고 메시지를 그대로 보고한다.

## 5. 문서 갱신

문서에 개인 절대경로·맥 이름·집 네트워크 값을 쓰지 않는다.

### `README.md`

1. 요약 이력 표 맨 위에 한 행 추가:

```
| **v3.2.1** | 2026-10-05 | **스케줄러 네트워크 안전장치 — 빈 캐시 중복 저장 차단**: Notion 캐시 첫 조회가 네트워크 오류로 실패하면 재시도 없이 빈 캐시로 진행해 재생목록 앞 15편을 다시 저장하던 결함 수정(08-12 이후 13회·중복 195건). 캐시는 "전부 읽었거나, 던지거나"로 바꾸고 실패한 실행은 영상 처리를 건너뜀(fail-closed), Notion 401/403 은 즉시 종료. YouTube 조회에 일시 오류 지수 백오프 재시도 추가(오류 한 번에 실행이 통째 실패하던 비율 28%). 채널 구독자 수 조회를 채널당 1회·동시 호출(약 450회)에서 50개 배치 순차(9회)로 교체. 회귀 테스트 `scripts/test_scheduler_guards.js` 신설 |
```

2. 상세 변경 내역 맨 위에 `#### [v3.2.1] — 2026-10-05 (🛡️ 스케줄러 네트워크 안전장치)` 절 추가. 기존 절과 같은 구성(**배경.** / **수정.** / **검증.**)으로, 이 지시서 1절의 숫자와 2절의 변경, 4절의 실제 검증 결과를 요약한다. "확인하지 못한 것"(야간 DNS 실패의 직접 원인)도 한 줄 남긴다.
3. 환경 변수 절(`.env` 예시)에 한 줄 추가:

```
# (v3.2.1) 새로 만든 빈 Notion DB 로 처음 돌릴 때만 true. 평소에는 넣지 않는다 — 캐시 0건이면 저장 없이 중단하는 안전장치를 끈다
# NOTION_CACHE_ALLOW_EMPTY=true
```

4. 프로젝트 구조 절에 `scripts/test_scheduler_guards.js` 를 추가한다.

### `CLAUDE.md`

1. 머리의 현재 버전을 `v3.2.1` (2026-10-05) 로.
2. Commands 블록에 추가:

```bash
# 스케줄러 네트워크 안전장치 회귀 테스트 (v3.2.1) — 네트워크 0회, scheduler.log 무변경
node scripts/test_scheduler_guards.js
```

3. 핵심 파일 역할 표에 한 행: `scripts/test_scheduler_guards.js` — (v3.2.1) `scheduler.js` 의 캐시·재시도·배치 조회 회귀 테스트. `https.request` 를 가짜로 바꾸고 `require` 한다.
4. "중요한 제약사항"에 아래 절을 추가한다.

```markdown
**Notion 캐시 — 전부 읽었거나, 던지거나 (v3.2.1) — 건드리지 말 것**

`scheduler.js:loadNotionCache()` 는 중복 판정의 유일한 근거다. 빈 캐시·부분 캐시가 한 번이라도 반환되면 전 영상이 신규로 보여 `MAX_NEW_PER_RUN`(15)편을 다시 요약·저장한다. 2026-08-12 ~ 10-01 사이 13회 발생해 Notion 중복 195건이 쌓였고, 결과가 "저장 15 · Skip 0 · 오류 0" 이라 성공으로 보였다.

- 루프를 `do { … } while (cursor)` 로 되돌리지 말 것. 첫 페이지 실패 시 `continue` 가 조건 검사로 넘어가 재시도 없이 끝난다.
- 재시도 초과·0건은 **던진다**. `break` 나 빈 `Map` 반환으로 바꾸지 말 것. `main` 이 받아 영상 처리와 큐 재시도를 건너뛴다(fail-closed).
- Notion 401/403 은 재시도 없이 `fatalAuth` 로 던지고 `main` 이 즉시 종료한다(보안 원칙 1).
- 새로 만든 빈 DB 로 처음 돌릴 때만 `.env` 에 `NOTION_CACHE_ALLOW_EMPTY=true`. 평소에는 넣지 않는다.
- **스케줄러 결과가 "저장 15 · Skip 0" 이면 성공이 아니라 캐시 이상을 의심한다.**

**YouTube 조회 재시도·배치 (v3.2.1)**

- `ytFetch()` 는 네트워크 오류·429·5xx 만 지수 백오프(2→16초, 최대 5회)로 재시도한다. 401/403 은 즉시 던진다 — 재시도 대상을 넓힐 때 이 구분을 지우지 말 것.
- 채널 구독자 수는 `getBatchSubs()` 로 50개씩 순차 조회한다. 채널마다 `Promise.all` 로 부르던 방식(실행당 새 연결·유닛 약 450)으로 되돌리지 말 것.
- `scheduler.js` 는 `require.main === module` 일 때만 `main` 을 돈다. 이 가드를 지우면 테스트가 실제 실행을 일으킨다.
```

5. 변경 이력 맨 위에 `2026-10-05 (v3.2.1)` 항목을 추가한다(배경 숫자, 수정 3건, 검증 결과, 지시서 경로 `docs/tasks/2026-10-05-scheduler-network-guards.md`).
6. `scheduler.js` 줄 번호 참조를 교정한다. 이번 수정으로 줄이 밀렸다.

```bash
grep -n -o 'scheduler\.js:[0-9~]*' CLAUDE.md AGENTS.md
```

나온 참조마다 수정 후 `scheduler.js` 에서 실제 줄을 확인해 고친다. 어느 코드를 가리키는지 문맥으로 판단할 수 없는 참조는 고치지 말고 보고한다.

### `AGENTS.md`

`CLAUDE.md` 4번 절과 5번 이력을 같은 내용으로 넣고, 6번 줄 번호 교정을 한다. 그 밖의 낡은 내용(머리의 버전·경로 등)은 이번 범위가 아니다 — 발견한 것만 보고한다.

## 6. 데몬 재기동

**필요 없다.** `scheduler.js` 는 launchd 가 정시에 새 프로세스로 띄우고 `server.js` 도 요청마다 자식 프로세스로 띄운다. 다음 실행부터 새 코드가 돈다. `server.js`·`wiki_lan_server.js` 는 건드리지 않는다.

작업 중 정기 실행(00·06·12·18시)이 겹쳐도 해당 실행은 시작 시점의 파일로 돈다. 다만 파일을 반쯤 고친 상태로 정시를 넘기지 않도록, **정시 10분 전 ~ 정시 후 15분 사이에는 `scheduler.js` 편집을 시작하지 않는다.**

## 7. 커밋

```bash
git status --short
git add scheduler.js scripts/test_scheduler_guards.js README.md CLAUDE.md AGENTS.md docs/tasks/2026-10-05-scheduler-network-guards.md
git diff --cached --stat
git commit -m "fix(scheduler): 빈 Notion 캐시 중복 저장 차단 + YouTube 조회 재시도·구독자 수 배치 조회 (v3.2.1)"
```

- `git status --short` 에 위 6개 외의 파일이 보이면 추가하지 말고 보고한다.
- **`git push` 는 하지 않는다.** 대표님 확인 후 별도 지시로 한다.

## 8. 롤백

```bash
git revert --no-edit <이 커밋 해시>
```

커밋 전이라면 `git checkout -- scheduler.js README.md CLAUDE.md AGENTS.md`. 상태 파일·큐 파일·Notion 데이터는 이 지시서가 건드리지 않으므로 되돌릴 것이 없다. 롤백하면 빈 캐시 중복 저장이 다시 가능해진다.

## 9. 범위 밖

- **Notion 중복 약 195건 정리.** 페이지를 지우는 작업이라 dry-run 부터 하는 별도 지시서([CC-1005-B])로 한다. 이번에는 Notion 데이터를 건드리지 않는다.
- 야간 DNS 실패의 원인 조사.
- 실행 통째 실패 시 알림(지금은 저장 0건이면 텔레그램을 보내지 않는다).
- Gemini 무료 한도 소진(유입량 문제) 대응.
- `flushPendingQueue`·`appendPending`·dead-letter 로직, `migrate_classify.js`, `lib/youtube_oauth.js`.
- `sync_obsidian.py`·`wiki_ingest.py`·`kakao_ingest.py` 등 Python 쪽.
- `node scheduler.js` 실제 실행.

## 10. 보고 형식

한국어로, 아래 순서로 보고한다.

1. 2절 9곳의 적용 여부(AS-IS 가 한 번이 아니었던 곳이 있으면 그 내용)
2. 4-1 ~ 4-5 의 실제 출력
3. 줄 번호 참조 교정 목록(이전 → 이후), 판단을 보류한 참조
4. `git diff --cached --stat` 과 커밋 해시
5. `AGENTS.md` 등에서 발견했지만 손대지 않은 낡은 내용
