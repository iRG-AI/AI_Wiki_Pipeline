#!/usr/bin/env node
// scheduler.js 의 네트워크 안전장치 회귀 테스트 — 네트워크·Notion·YouTube 를 실제로 부르지 않는다.
//   node scripts/test_scheduler_guards.js
// https.request 를 가짜로 바꾼 뒤 scheduler.js 를 require 한다. 대본(script)에 없는 요청이 나가면 그 자체로 실패다.
//
// 지키는 것:
//   1) Notion 캐시는 "전부 읽었거나, 던지거나" — 빈 캐시·부분 캐시를 돌려주지 않는다 (2026-10-05 중복 저장 195건의 원인)
//   2) YouTube 조회는 일시 오류만 재시도하고 401/403 은 즉시 던진다
//   3) 채널 구독자 수는 50개씩 묶어 순차 조회한다

const https = require('https');
const fs = require('fs');
const path = require('path');
const { EventEmitter } = require('events');

// ── 격리: 실제 로그 파일에 쓰지 않고, 백오프 대기를 건너뛰고, 화면 로그를 끈다 ──
fs.appendFileSync = () => {};
const realSetTimeout = global.setTimeout;
global.setTimeout = (fn, _ms, ...args) => realSetTimeout(fn, 0, ...args);
const out = (s) => process.stdout.write(s + '\n');
console.log = () => {};
delete process.env.NOTION_CACHE_ALLOW_EMPTY;

// ── 가짜 https.request ──
let script = [];   // [{ netErr: 'ENOTFOUND' } | { status: 200, body: {...} }]
let calls = [];    // [{ host, path }]
let unscripted = 0;
https.request = (options, onResponse) => {
  const req = new EventEmitter();
  req.write = () => {};
  req.end = () => {
    calls.push({ host: options.hostname, path: options.path });
    const step = script.shift();
    realSetTimeout(() => {
      if (!step) {
        unscripted++;
        // 경로에는 API 키(?key=)·봇 토큰(/bot…/)이 들어 있으므로 물음표 앞까지만, 토큰은 가려서 찍는다
        const safePath = String(options.path || '').split('?')[0].replace(/\/bot[^/]+\//, '/bot<redacted>/');
        const e = new Error('대본에 없는 요청: ' + options.hostname + safePath);
        e.code = 'UNSCRIPTED';
        return req.emit('error', e);
      }
      if (step.netErr) {
        const e = new Error(step.netErr);
        e.code = step.netErr;
        return req.emit('error', e);
      }
      const res = new EventEmitter();
      res.statusCode = step.status;
      onResponse(res);
      res.emit('data', Buffer.from(JSON.stringify(step.body || {}), 'utf8'));
      res.emit('end');
    }, 0);
  };
  return req;
};

// scheduler.js 에 require.main 가드가 없으면 require 하는 순간 실제 실행(main)이 돈다. 먼저 확인한다.
const SCHEDULER = path.join(__dirname, '..', 'scheduler.js');
if (!fs.readFileSync(SCHEDULER, 'utf8').includes('require.main === module')) {
  out('중단: scheduler.js 에 `require.main === module` 가드가 없다. 가드를 먼저 넣어야 이 테스트를 돌릴 수 있다.');
  process.exit(2);
}
const { ytFetch, getBatchSubs, loadNotionCache } = require(SCHEDULER);

const net = (code) => ({ netErr: code });
const http = (status, body) => ({ status, body });
const notionPage = (n, nextCursor) => http(200, {
  results: Array.from({ length: n }, (_, i) => ({
    id: `page-${nextCursor || 'last'}-${i}`,
    properties: {
      '영상 제목': { title: [{ text: { content: `제목 ${nextCursor || 'last'} ${i}` } }] },
      '영상 URL': { url: `https://www.youtube.com/watch?v=${String(i).padStart(4, '0')}${(nextCursor || 'last').padEnd(7, 'x').slice(0, 7)}` },
    },
  })),
  next_cursor: nextCursor || null,
});

async function expectThrow(fn) {
  try { await fn(); } catch (e) { return e; }
  throw new Error('던져야 하는데 정상 반환했다');
}
function assert(cond, msg) { if (!cond) throw new Error(msg); }

const cases = [
  ['ytFetch: 네트워크 오류 2회 뒤 성공하면 결과를 돌려준다', async () => {
    script = [net('ENOTFOUND'), net('ETIMEDOUT'), http(200, { items: [1] })];
    const d = await ytFetch('videos?part=snippet&id=x');
    assert(d.items.length === 1, '응답 본문이 다르다');
    assert(calls.length === 3, `요청 ${calls.length}회 (기대 3)`);
  }],
  ['ytFetch: 503 은 재시도한다', async () => {
    script = [http(503, {}), http(200, { ok: true })];
    const d = await ytFetch('videos?part=snippet&id=x');
    assert(d.ok === true && calls.length === 2, `요청 ${calls.length}회 (기대 2)`);
  }],
  ['ytFetch: 403 은 재시도 없이 즉시 던진다', async () => {
    script = [http(403, { error: { code: 403 } }), http(200, {})];
    const e = await expectThrow(() => ytFetch('videos?part=snippet&id=x'));
    assert(/403/.test(e.message), '오류 메시지에 403 이 없다');
    assert(calls.length === 1, `요청 ${calls.length}회 (기대 1)`);
  }],
  ['ytFetch: 401 은 재시도 없이 즉시 던진다', async () => {
    script = [http(401, {}), http(200, {})];
    await expectThrow(() => ytFetch('videos?part=snippet&id=x'));
    assert(calls.length === 1, `요청 ${calls.length}회 (기대 1)`);
  }],
  ['ytFetch: 네트워크 오류가 계속되면 5회에서 멈추고 던진다', async () => {
    script = Array.from({ length: 9 }, () => net('ENOTFOUND'));
    const e = await expectThrow(() => ytFetch('videos?part=snippet&id=x'));
    assert(e.code === 'ENOTFOUND', '원래 오류가 아니다');
    assert(calls.length === 5, `요청 ${calls.length}회 (기대 5)`);
  }],
  ['getBatchSubs: 120개 채널을 50개씩 3회로 조회한다', async () => {
    const ids = Array.from({ length: 120 }, (_, i) => `UC${String(i).padStart(22, '0')}`);
    const page = (from, to) => http(200, { items: ids.slice(from, to).map((id, k) => ({ id, statistics: { subscriberCount: String(1000 + from + k) } })) });
    script = [page(0, 50), page(50, 100), page(100, 120)];
    const map = await getBatchSubs(ids);
    assert(calls.length === 3, `요청 ${calls.length}회 (기대 3)`);
    assert(calls.every(c => c.host === 'www.googleapis.com' && c.path.includes('/youtube/v3/channels?')), '채널 조회가 아닌 요청이 섞였다');
    const perCall = calls.map(c => decodeURIComponent(c.path.match(/[?&]id=([^&]+)/)[1]).split(',').length);
    assert(perCall.join(',') === '50,50,20', `호출별 채널 수 ${perCall.join(',')} (기대 50,50,20)`);
    assert(Object.keys(map).length === 120 && map[ids[119]] === 1119, '구독자 수 맵이 다르다');
  }],
  ['getBatchSubs: 응답에 없는 채널은 맵에서 빠진다', async () => {
    script = [http(200, { items: [{ id: 'UCa', statistics: { subscriberCount: '7' } }] })];
    const map = await getBatchSubs(['UCa', 'UCgone']);
    assert(map.UCa === 7 && !('UCgone' in map), '맵이 다르다');
  }],
  ['loadNotionCache: 첫 페이지 네트워크 오류 뒤에도 전부 읽는다 (빈 캐시 금지)', async () => {
    script = [net('ENOTFOUND'), notionPage(100, 'cur1'), notionPage(30)];
    const cache = await loadNotionCache();
    assert(calls.length === 3, `요청 ${calls.length}회 (기대 3)`);
    assert(cache.size > 0, '캐시가 비었다');
    assert(cache.has('0000cur1xxx') && cache.has('0029lastxxx'), '두 페이지의 영상이 모두 들어 있지 않다');
  }],
  ['loadNotionCache: 0건이면 던진다', async () => {
    script = [http(200, { results: [], next_cursor: null })];
    const e = await expectThrow(() => loadNotionCache());
    assert(/0건/.test(e.message), '0건 오류가 아니다');
  }],
  ['loadNotionCache: 401 은 재시도 없이 fatalAuth 로 던진다', async () => {
    script = [http(401, { code: 'unauthorized' }), notionPage(10)];
    const e = await expectThrow(() => loadNotionCache());
    assert(e.fatalAuth === true, 'fatalAuth 가 아니다');
    assert(calls.length === 1, `요청 ${calls.length}회 (기대 1)`);
  }],
  ['loadNotionCache: 중간에 오류가 계속되면 부분 캐시 대신 던진다', async () => {
    script = [notionPage(100, 'cur1'), ...Array.from({ length: 12 }, () => http(500, {}))];
    const e = await expectThrow(() => loadNotionCache());
    assert(/재시도 횟수 초과/.test(e.message), '재시도 초과 오류가 아니다');
    assert(calls.length === 11, `요청 ${calls.length}회 (기대 11)`);
  }],
  ['loadNotionCache: NOTION_CACHE_ALLOW_EMPTY=true 면 빈 DB 를 허용한다', async () => {
    process.env.NOTION_CACHE_ALLOW_EMPTY = 'true';
    try {
      script = [http(200, { results: [], next_cursor: null })];
      const cache = await loadNotionCache();
      assert(cache.size === 0, '빈 캐시가 아니다');
    } finally {
      delete process.env.NOTION_CACHE_ALLOW_EMPTY;
    }
  }],
];

(async () => {
  let pass = 0;
  for (const [name, fn] of cases) {
    script = []; calls = []; unscripted = 0;
    try {
      await fn();
      assert(unscripted === 0, `대본에 없는 요청 ${unscripted}회`);
      pass++;
      out(`PASS  ${name}`);
    } catch (e) {
      out(`FAIL  ${name}\n      → ${e.message}`);
    }
  }
  out(`\n${pass}/${cases.length} PASS`);
  process.exit(pass === cases.length ? 0 : 1);
})();
