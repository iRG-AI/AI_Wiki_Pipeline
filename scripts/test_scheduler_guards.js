#!/usr/bin/env node
// scheduler.js 의 네트워크·장부 안전장치 회귀 테스트 — 네트워크·YouTube 를 실제로 부르지 않고, 장부는 임시 파일로 만든다.
//   node scripts/test_scheduler_guards.js
// https.request 를 가짜로 바꾼 뒤 scheduler.js 를 require 한다. 대본(script)에 없는 요청이 나가면 그 자체로 실패다.
//
// 지키는 것:
//   1) 장부 캐시는 "전부 읽었거나, 던지거나" — 장부 파일이 없으면 만들지 않고 던지고, 0건이면 던진다
//      (2026-10-05 빈 캐시 중복 저장 195건의 원인. v4.0 에서 Notion 캐시 → 로컬 장부 data/library.db 로 바뀜)
//   2) YouTube 조회는 일시 오류만 재시도하고 401/403 은 즉시 던진다
//   3) 채널 구독자 수는 50개씩 묶어 순차 조회한다
//   4) 장부 쓰기(저장·주제 추가·통계 갱신)는 같은 video_id 를 덮어쓰지 않고, 네트워크 요청을 하나도 만들지 않는다
//   5) (v4.0 3단계) 시트 미러 훅은 실패해도 reject 하지 않는다 — 오류를 결과로 돌려줄 뿐 Obsidian 동기화를 막지 않는다
//   6) (v4.1) 장부 백업 훅도 같다 — 실패해도 reject 하지 않고, 네트워크 요청을 만들지 않는다(텔레그램은 main 이 보낸다)
//   7) (v4.2) 실행 실패 알림 — 통째 실패 판정, 직전 실행 점검 문구(끝나지 못한 실행·못 보낸 실패·빠진 정시 실행),
//      상태 파일 읽기·쓰기, sendTelegram 은 성공/실패를 true/false 로 돌려주고 JSON 아닌 응답에도 죽지 않는다
//   8) (v4.6) 상세 조회는 길이·공개 상태를 같은 1회 호출로 받고, 장부 저장은 요약 방식·등급·신호·요약 시각을 남긴다

const https = require('https');
const fs = require('fs');
const path = require('path');
const os = require('os');
const { EventEmitter } = require('events');

// ── 격리: 실제 로그 파일에 쓰지 않고, 백오프 대기를 건너뛰고, 화면 로그를 끈다 ──
fs.appendFileSync = () => {};
const realSetTimeout = global.setTimeout;
global.setTimeout = (fn, _ms, ...args) => realSetTimeout(fn, 0, ...args);
const out = (s) => process.stdout.write(s + '\n');
console.log = () => {};
delete process.env.LIBRARY_ALLOW_EMPTY;
// (v4.2) sendTelegram 테스트용 — scheduler.js 의 loadEnv 는 이미 있는 값을 덮지 않는다. 실제 봇 토큰·대화방은 쓰지 않는다
process.env.TELEGRAM_ENABLED = 'true';
process.env.TELEGRAM_BOT_TOKEN = 'TEST_TOKEN';
process.env.TELEGRAM_CHAT_ID = 'TEST_CHAT';

// ── 가짜 https.request ──
let script = [];   // [{ netErr: 'ENOTFOUND' } | { status: 200, body: {...} }]
let calls = [];    // [{ host, path }]
let unscripted = 0;
https.request = (options, onResponse) => {
  const req = new EventEmitter();
  req.write = () => {};
  req.setTimeout = () => req;   // (v4.2) sendTelegram 이 부른다
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
      res.emit('data', Buffer.from(step.raw !== undefined ? step.raw : JSON.stringify(step.body || {}), 'utf8'));
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
const sched = require(SCHEDULER);
const { ytFetch, getBatchSubs, getBatchDetails, loadLibraryCache, findDuplicate, saveToLibrary, _setLibDb } = sched;
const { sendTelegram, readRunState, writeRunState, runNotices, isWholeRunFailure } = sched;
const library = require(path.join(__dirname, '..', 'lib', 'library'));
const { DatabaseSync } = library.loadSqlite();   // ExperimentalWarning 한 줄을 삼키는 로더

const net = (code) => ({ netErr: code });
const http = (status, body) => ({ status, body });
// ── 임시 장부: lib/library_schema.sql 을 그대로 실행해 만든다 ──
const TMP = fs.mkdtempSync(path.join(os.tmpdir(), 'sched-lib-'));
let dbSeq = 0;
function makeLibrary(rows = [], { userVersion } = {}) {
  const p = path.join(TMP, `library-${++dbSeq}.db`);
  const db = new DatabaseSync(p);
  db.exec(fs.readFileSync(path.join(__dirname, '..', 'lib', 'library_schema.sql'), 'utf8'));
  if (userVersion !== undefined) db.exec(`PRAGMA user_version = ${userVersion}`);
  const ins = db.prepare(`INSERT INTO videos (record_id, video_id, title, channel, topics, upload_date, view_count,
    subscriber_count, video_url, summary, summary_src, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)`);
  for (const r of rows) {
    ins.run(r.id, r.vid ?? null, r.title || '', 'ch', JSON.stringify(r.topics || []), r.date ?? null, r.views ?? null,
      null, r.vid ? `https://www.youtube.com/watch?v=${r.vid}` : null, '요약', 'property',
      '2026-10-01T00:00:00.000Z', '2026-10-01T00:00:00.000Z');
  }
  db.close();
  return p;
}
const SEED = [
  { id: 'aaaa-1', vid: 'AAAAAAAAAA1', title: 'Claude Code 완벽 가이드!', topics: ['AI Claude'], date: '2026-09-01', views: 100 },
  { id: 'aaaa-2', vid: 'AAAAAAAAAA2', title: '두 번째 영상', topics: [] },
  { id: 'aaaa-3', vid: null, title: 'video_id 없는 영상' },
];
// 가짜 인터프리터: 인자를 무시하고 주어진 셸 명령만 실행 (runSheetMirror 가 python3 대신 부른다)
function fakeInterpreter(body) {
  const p = path.join(TMP, `fake-py-${++dbSeq}.sh`);
  fs.writeFileSync(p, `#!/bin/sh\n${body}\n`, { mode: 0o755 });
  return p;
}
const count = (p) => { const d = new DatabaseSync(p); const n = d.prepare('SELECT COUNT(*) n FROM videos').get().n; d.close(); return n; };

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
  ['openLibrary: 장부 파일이 없으면 새로 만들지 않고 던진다', async () => {
    const p = path.join(TMP, 'none', 'library.db');
    const e = await expectThrow(() => library.openLibrary(p));
    assert(/장부 파일 없음/.test(e.message), '파일 없음 오류가 아니다: ' + e.message);
    assert(!fs.existsSync(p), '빈 장부 파일을 만들었다');
  }],
  ['openLibrary: user_version 이 스키마와 다르면 던진다', async () => {
    const p = makeLibrary(SEED, { userVersion: 0 });
    const e = await expectThrow(() => library.openLibrary(p));
    assert(/user_version/.test(e.message), 'user_version 오류가 아니다: ' + e.message);
  }],
  ['loadLibraryCache: video_id·제목·정규화 제목 키로 전부 들어간다', async () => {
    const db = library.openLibrary(makeLibrary(SEED));
    try {
      const cache = loadLibraryCache(db);
      assert(cache.get('AAAAAAAAAA1')?.pageId === 'aaaa-1', 'video_id 키가 없다');
      assert(cache.get('두 번째 영상')?.pageId === 'aaaa-2', '제목 키가 없다');
      assert(findDuplicate({ title: 'video_id 없는 영상' }, cache)?.pageId === 'aaaa-3', 'video_id 없는 행을 제목으로 못 찾는다');
      assert(findDuplicate({ videoId: 'ZZZZZZZZZZZ', title: 'claude code 완벽 가이드' }, cache)?.pageId === 'aaaa-1', '정규화 제목으로 못 찾는다');
      const e = cache.get('AAAAAAAAAA1');
      assert(e.topics[0] === 'AI Claude' && e.savedViewCount === 100 && e.savedDate === '2026-09-01', '캐시 항목 값이 다르다');
    } finally { db.close(); }
  }],
  ['loadLibraryCache: 0건이면 던진다', async () => {
    const db = library.openLibrary(makeLibrary([]));
    try {
      const e = await expectThrow(() => loadLibraryCache(db));
      assert(/0건/.test(e.message), '0건 오류가 아니다');
    } finally { db.close(); }
  }],
  ['loadLibraryCache: LIBRARY_ALLOW_EMPTY=true 면 빈 장부를 허용한다', async () => {
    process.env.LIBRARY_ALLOW_EMPTY = 'true';
    const db = library.openLibrary(makeLibrary([]));
    try {
      assert(loadLibraryCache(db).size === 0, '빈 캐시가 아니다');
    } finally { db.close(); delete process.env.LIBRARY_ALLOW_EMPTY; }
  }],
  ['saveToLibrary: 신규 영상을 장부 형식대로 저장하고, 다시 읽은 캐시가 중복으로 잡는다', async () => {
    const db = library.openLibrary(makeLibrary(SEED));
    _setLibDb(db);
    try {
      const nfd = 'AI 클로드'.normalize('NFD');
      const id = saveToLibrary({ videoId: 'NEWNEWNEW01', title: '새 영상', channelTitle: '채널', publishedAt: '2026-10-10T01:02:03Z',
        viewCount: 5, subscriberCount: 7, thumbnail: 'https://i.ytimg.com/vi/NEWNEWNEW01/mq.jpg' }, '## 요약\n- 내용', [nfd, 'AI 클로드', 'AI 에이전트']);
      assert(/^[0-9a-f-]{36}$/.test(id), 'record_id 가 uuid 가 아니다: ' + id);
      const r = db.prepare('SELECT * FROM videos WHERE record_id = ?').get(id);
      assert(r.video_id === 'NEWNEWNEW01' && r.video_url === 'https://www.youtube.com/watch?v=NEWNEWNEW01', 'video_id·url 이 다르다');
      assert(r.topics === JSON.stringify(['AI 클로드', 'AI 에이전트']), 'topics 가 NFC·중복 제거되지 않았다: ' + r.topics);
      assert(r.upload_date === '2026-10-10' && r.view_count === 5 && r.subscriber_count === 7, '날짜·통계가 다르다');
      assert(r.thumbnail_url === 'https://i.ytimg.com/vi/NEWNEWNEW01/mq.jpg', '썸네일이 다르다');
      assert(r.summary === '## 요약\n- 내용' && r.summary_src === 'app' && r.status === '완료', 'summary·summary_src·status 가 다르다');
      assert(/^\d{4}-\d\d-\d\dT.*Z$/.test(r.created_at) && r.created_at === r.updated_at, '시각 형식이 다르다');
      assert(findDuplicate({ videoId: 'NEWNEWNEW01' }, loadLibraryCache(db)), '저장한 영상을 캐시가 못 찾는다');
    } finally { _setLibDb(null); db.close(); }
  }],
  ['getBatchDetails: (v4.6) contentDetails·status 를 같은 호출로 받아 길이(초)·공개 상태를 채운다', async () => {
    script = [http(200, { items: [
      { id: 'V1', statistics: { viewCount: '9' }, snippet: { title: 't' }, contentDetails: { duration: 'PT45M31S' }, status: { privacyStatus: 'public' } },
      { id: 'V2', statistics: {}, snippet: {}, contentDetails: { duration: 'P0D' }, status: { privacyStatus: 'unlisted' } },
      { id: 'V3', statistics: {}, snippet: {} },
    ] })];
    const m = await getBatchDetails(['V1', 'V2', 'V3', 'V4']);
    assert(calls.length === 1 && /^\/youtube\/v3\/videos\?part=statistics,snippet,contentDetails,status&id=V1,V2,V3,V4&key=/.test(calls[0].path), '요청 경로가 다르다');
    assert(m.V1.durationSec === 2731 && m.V1.privacy === 'public' && m.V1.viewCount === 9, 'V1');
    assert(m.V2.durationSec === 0 && m.V2.privacy === 'unlisted', 'V2');
    assert(m.V3.durationSec === null && m.V3.privacy === '' && !m.V4, 'V3·V4');
  }],
  ['saveToLibrary: (v4.6) 요약 방식·등급·신호·요약 시각 저장, 등급 값은 keep|exclude 만', async () => {
    const db = library.openLibrary(makeLibrary(SEED));
    _setLibDb(db);
    try {
      const id1 = saveToLibrary({ videoId: 'NEWVID00001', title: '영상 요약' }, '요약', [], { src: 'video', grade: 'exclude', quality: '{"promo_main":true}' });
      const id2 = saveToLibrary({ videoId: 'NEWVID00002', title: '대체 요약' }, '요약', []);
      const id3 = saveToLibrary({ videoId: 'NEWVID00003', title: '이상한 등급' }, '요약', [], { src: 'video', grade: 'A' });
      const g = (id) => db.prepare('SELECT summary_src, grade, quality, summarized_at, created_at FROM videos WHERE record_id = ?').get(id);
      const a = g(id1), b = g(id2), c = g(id3);
      assert(a.summary_src === 'video' && a.grade === 'exclude' && a.quality === '{"promo_main":true}' && a.summarized_at === a.created_at, JSON.stringify(a));
      assert(b.summary_src === 'app' && b.grade === null && b.quality === null && b.summarized_at === b.created_at, JSON.stringify(b));
      assert(c.grade === null, '허용 밖 등급이 저장됐다: ' + c.grade);
    } finally { _setLibDb(null); db.close(); }
  }],
  ['saveToLibrary: 이미 있는 video_id 는 덮어쓰지 않고 던진다', async () => {
    const p = makeLibrary(SEED);
    const db = library.openLibrary(p);
    _setLibDb(db);
    try {
      const e = await expectThrow(() => saveToLibrary({ videoId: 'AAAAAAAAAA1', title: '같은 영상' }, '요약', []));
      assert(/UNIQUE/i.test(e.message), 'UNIQUE 위반이 아니다: ' + e.message);
      assert(db.prepare("SELECT title FROM videos WHERE video_id = 'AAAAAAAAAA1'").get().title === 'Claude Code 완벽 가이드!', '기존 행이 바뀌었다');
    } finally { _setLibDb(null); db.close(); }
    assert(count(p) === 3, '행 수가 바뀌었다');
  }],
  ['addTopic: 장부의 현재 값과 합집합, 이미 있으면(NFD 포함) false', async () => {
    const db = library.openLibrary(makeLibrary(SEED));
    try {
      assert(library.addTopic(db, 'aaaa-1', 'AI 에이전트') === true, '추가를 못 했다');
      assert(library.addTopic(db, 'aaaa-1', 'AI 에이전트'.normalize('NFD')) === false, 'NFD 같은 주제를 또 넣었다');
      assert(library.addTopic(db, 'aaaa-1', 'AI Claude') === false, '기존 주제를 또 넣었다');
      const t = db.prepare("SELECT topics FROM videos WHERE record_id = 'aaaa-1'").get().topics;
      assert(t === JSON.stringify(['AI Claude', 'AI 에이전트']), 'topics 가 다르다: ' + t);
      await expectThrow(() => library.addTopic(db, 'no-such-id', 'AI Claude'));
    } finally { db.close(); }
  }],
  ['runSheetMirror: 미러가 exit 2(auth) 여도 reject 없이 결과를 돌려준다', async () => {
    const fake = fakeInterpreter('echo \'RESULT_JSON:{"error":"auth","videos_sent":0,"tips_sent":0}\'; exit 2');
    const r = await sched.runSheetMirror(fake);
    assert(r && r.error === 'auth', '결과가 다르다: ' + JSON.stringify(r));
  }],
  ['runSheetMirror: 출력 없이 죽어도 reject 없이 exit 코드를 오류로 돌려준다', async () => {
    const fake = fakeInterpreter('exit 3');
    const r = await sched.runSheetMirror(fake);
    assert(r && r.error === 'exit_3', '결과가 다르다: ' + JSON.stringify(r));
  }],
  ['runSheetMirror: skipped(설정 전)는 오류가 아니다', async () => {
    const fake = fakeInterpreter('echo \'RESULT_JSON:{"skipped":"not_configured","videos_sent":0,"tips_sent":0,"error":""}\'');
    const r = await sched.runSheetMirror(fake);
    assert(r && r.skipped === 'not_configured' && !r.error, '결과가 다르다: ' + JSON.stringify(r));
  }],
  ['runLibraryBackup: 드라이브 실패(exit 1)여도 reject 없이 결과를 돌려준다', async () => {
    const fake = fakeInterpreter('echo \'RESULT_JSON:{"file":"library-20261012.db.gz","dests":{"local":"ok","drive":"unavailable"},"error":"drive_unavailable"}\'; exit 1');
    const r = await sched.runLibraryBackup(fake);
    assert(r && r.error === 'drive_unavailable' && r.dests.local === 'ok', '결과가 다르다: ' + JSON.stringify(r));
  }],
  ['runLibraryBackup: 출력 없이 죽어도 reject 없이 exit 코드를 오류로 돌려준다', async () => {
    const fake = fakeInterpreter('exit 4');
    const r = await sched.runLibraryBackup(fake);
    assert(r && r.error === 'exit_4', '결과가 다르다: ' + JSON.stringify(r));
  }],
  ['runLibraryBackup: skipped(오늘 것 있음)는 오류가 아니다', async () => {
    const fake = fakeInterpreter('echo \'RESULT_JSON:{"skipped":"already_done","file":"library-20261012.db.gz","error":""}\'');
    const r = await sched.runLibraryBackup(fake);
    assert(r && r.skipped === 'already_done' && !r.error, '결과가 다르다: ' + JSON.stringify(r));
  }],
  // ── (v4.2) 실행 실패 알림 ──
  ['isWholeRunFailure: 저장 0 · Skip 0 · 오류 ≥1 만 통째 실패', async () => {
    assert(isWholeRunFailure({ saved: 0, skip: 0, error: 1 }) === true, '0/0/1 을 못 잡았다');
    assert(isWholeRunFailure({ saved: 0, skip: 1539, error: 0 }) === false, '평소 실행(0/1539/0)을 실패로 봤다');
    assert(isWholeRunFailure({ saved: 0, skip: 1537, error: 2 }) === false, '일부 오류(0/1537/2)를 통째 실패로 봤다');
    assert(isWholeRunFailure({ saved: 3, skip: 0, error: 1 }) === false, '저장이 있는데 실패로 봤다');
    assert(isWholeRunFailure({ saved: 0, skip: 0, error: 0 }) === false, '빈 목록(0/0/0)을 실패로 봤다');
  }],
  ['runNotices: 기록 없음·깨진 시각이면 알리지 않는다', async () => {
    const now = Date.parse('2026-10-12T03:00:00Z');
    assert(runNotices(null, now).length === 0, 'null');
    assert(runNotices({}, now).length === 0, '빈 객체');
    assert(runNotices({ started_at: 'garbage', outcome: 'running' }, now).length === 0, '깨진 시각');
  }],
  ['runNotices: 정상 실행 6시간 뒤 → 없음, 12시간 뒤 → 빠진 실행 1줄', async () => {
    const prev = { started_at: '2026-10-09T21:00:00.000Z', outcome: 'ok', notified: false };   // KST 10-10 06:00
    assert(runNotices(prev, Date.parse('2026-10-10T03:00:30Z')).length === 0, '6시간 간격을 알렸다');
    assert(runNotices(prev, Date.parse('2026-10-10T05:59:00Z')).length === 0, '9시간 미만(지연)을 알렸다');
    const n = runNotices(prev, Date.parse('2026-10-10T09:00:00Z'));
    assert(n.length === 1 && n[0].includes('12.0시간') && n[0].includes('빠졌습니다'), '빠진 실행 문구가 다르다: ' + JSON.stringify(n));
  }],
  ['runNotices: 못 보낸 실패만 알리고, 원인의 < > & 는 이스케이프한다', async () => {
    const at = '2026-10-04T21:00:00.000Z', now = Date.parse('2026-10-05T03:00:00Z');
    const n = runNotices({ started_at: at, outcome: 'fail', notified: false, reason: '마스터 인제스트 오류: getaddrinfo ENOTFOUND <x&y>' }, now);
    assert(n.length === 1 && n[0].includes('ENOTFOUND') && n[0].includes('&lt;x&amp;y&gt;') && !n[0].includes('<x'), '실패 문구가 다르다: ' + JSON.stringify(n));
    assert(runNotices({ started_at: at, outcome: 'fail', notified: true, reason: 'x' }, now).length === 0, '이미 알린 실패를 또 알렸다');
  }],
  ['runNotices: running 으로 남은 실행 — 3시간 이상이면 알리고, 짧으면(겹친 실행) 알리지 않는다', async () => {
    const prev = { started_at: '2026-10-12T03:00:00.000Z', outcome: 'running' };
    assert(runNotices(prev, Date.parse('2026-10-12T04:00:00Z')).length === 0, '1시간 전 running 을 알렸다');
    const n = runNotices(prev, Date.parse('2026-10-12T09:00:00Z'));
    assert(n.length === 1 && n[0].includes('끝을 기록하지 못했습니다'), 'running 문구가 다르다: ' + JSON.stringify(n));
    const both = runNotices(prev, Date.parse('2026-10-12T15:00:00Z'));
    assert(both.length === 2, '끝나지 못함 + 12시간 간격 2줄이어야 한다: ' + both.length);
  }],
  ['readRunState/writeRunState: 쓰고 다시 읽는다 · 없거나 깨지면 null · .tmp 를 남기지 않는다', async () => {
    const f = path.join(TMP, 'run_state.json');
    assert(readRunState(f) === null, '없는 파일이 null 이 아니다');
    const st = { v: 1, started_at: '2026-10-12T03:00:00.000Z', outcome: 'ok', pending: ['a'] };
    assert(writeRunState(st, f) === true, '쓰기 실패');
    const back = readRunState(f);
    assert(back && back.outcome === 'ok' && back.pending[0] === 'a', '다시 읽은 값이 다르다');
    assert(!fs.existsSync(f + '.tmp'), '.tmp 가 남았다');
    fs.writeFileSync(f, '{ 깨진', 'utf8');
    assert(readRunState(f) === null, '깨진 파일이 null 이 아니다');
    fs.writeFileSync(f, '[1,2]', 'utf8');
    assert(readRunState(f) === null, '배열을 상태로 받았다');
    assert(writeRunState(st, path.join(TMP, 'no-such-dir', 'x.json')) === false, '못 쓰는 경로에서 true');
  }],
  ['sendTelegram: ok 면 true · 실패 응답·JSON 아닌 응답·네트워크 오류는 false (던지지 않는다)', async () => {
    script = [http(200, { ok: true }), http(400, { ok: false, description: 'Bad Request' }), { status: 502, raw: '<html>Bad Gateway</html>' }, net('ENOTFOUND')];
    assert(await sendTelegram('a') === true, 'ok 응답이 true 가 아니다');
    assert(await sendTelegram('b') === false, '실패 응답이 false 가 아니다');
    assert(await sendTelegram('c') === false, 'JSON 아닌 응답이 false 가 아니다');
    assert(await sendTelegram('d') === false, '네트워크 오류가 false 가 아니다');
    assert(calls.length === 4 && calls.every(c => c.host === 'api.telegram.org'), '요청 수·호스트가 다르다');
  }],
  ['updateStats: 업로드일을 안 주면 기존 날짜를 지킨다', async () => {
    const db = library.openLibrary(makeLibrary(SEED));
    try {
      assert(library.updateStats(db, 'aaaa-1', 300, 40, null) === true, '갱신 실패');
      let r = db.prepare("SELECT view_count, subscriber_count, upload_date FROM videos WHERE record_id = 'aaaa-1'").get();
      assert(r.view_count === 300 && r.subscriber_count === 40 && r.upload_date === '2026-09-01', '값이 다르다');
      library.updateStats(db, 'aaaa-1', 301, 41, '2026-09-02');
      r = db.prepare("SELECT upload_date FROM videos WHERE record_id = 'aaaa-1'").get();
      assert(r.upload_date === '2026-09-02', '업로드일이 안 바뀌었다');
    } finally { db.close(); }
  }],
];

(async () => {
  let pass = 0;
  for (const [name, fn] of cases) {
    script = []; calls = []; unscripted = 0;
    try {
      await fn();
      assert(calls.length === 0 || /^(ytFetch|getBatchSubs|getBatchDetails|sendTelegram)/.test(name), `장부 테스트가 네트워크 요청 ${calls.length}회를 만들었다`);
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
