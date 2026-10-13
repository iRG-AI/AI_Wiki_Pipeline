#!/usr/bin/env node
// (v4.7) Wiki 검색 화면 API 회귀 테스트 — lib/wiki_search.js 의 listPayload·scoreAll·similar·noteById
// + wiki_lan_server.js 의 /api/wiki-search(all·similar)·/api/wiki-note 경로.
// 임시 인덱스·임시 Vault 만 쓴다(WIKI_SEARCH_DIR · WIKI_VAULT). Gemini 요청은 가짜로 바꿔 네트워크 0회.
//
//   /opt/homebrew/bin/node scripts/test_wiki_search.js
'use strict';
const fs = require('fs');
const os = require('os');
const path = require('path');
const zlib = require('zlib');
const http = require('http');
const https = require('https');
const { spawn } = require('child_process');
const { EventEmitter } = require('events');

const REPO = path.join(__dirname, '..');
const DIM = 768;
const results = [];
function check(name, cond, detail) {
  results.push(!!cond);
  console.log(`  ${cond ? 'PASS' : 'FAIL'}  ${name}${!cond && detail !== undefined ? '  — ' + JSON.stringify(detail).slice(0, 300) : ''}`);
}

// ── 임시 인덱스 · Vault ──
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'wiki-search-test-'));
const V = path.join(tmp, 'vault');
fs.mkdirSync(path.join(V, 'AI Claude'), { recursive: true });
fs.mkdirSync(path.join(V, 'AI 꿀팁'), { recursive: true });
const unit = k => { const v = new Float32Array(DIM); v[k] = 1; return v; };
const mix = (a, b, w) => { const v = new Float32Array(DIM); v[a] = Math.sqrt(1 - w * w); v[b] = w; return v; };
const NOTES = [
  { id: 'aaaaaaaa-0000-0000-0000-000000000001', path: 'AI Claude/채널가_클로드 코드 입문_20261001.md', title: '클로드 코드 입문', channel: '채널가', topic: 'AI Claude',
    tags: ['AI Claude', 'AI 바이브코딩'], upload_date: '2026-10-01', view_count: 1200, video_url: 'https://www.youtube.com/watch?v=AAAAAAAAAAA', hash: 'h1',
    snippet: '클로드 코드 기초', kind: 'video', subscriber_count: 5000, summary_src: 'video', link_url: '', category: '', importance: '', keywords: [] },
  { id: 'aaaaaaaa-0000-0000-0000-000000000002', path: 'AI Claude/채널나_클로드 코드 심화_20261002.md', title: '클로드 코드 심화', channel: '채널나', topic: 'AI Claude',
    tags: ['AI Claude'], upload_date: '2026-10-02', view_count: 300, video_url: 'https://www.youtube.com/watch?v=BBBBBBBBBBB', hash: 'h2',
    snippet: '스킬과 훅', kind: 'video', subscriber_count: 0, summary_src: '', link_url: '', category: '', importance: '', keywords: [] },
  { id: 'aaaaaaaa-0000-0000-0000-000000000003', path: 'AI Claude/채널다_제미나이 비교_20261003.md', title: '제미나이 비교', channel: '채널다', topic: 'AI Claude',
    tags: ['AI Gemini'], upload_date: '2026-10-03', view_count: 50, video_url: 'https://www.youtube.com/watch?v=CCCCCCCCCCC', hash: 'h3',
    snippet: '모델 비교', kind: 'video', subscriber_count: 10, summary_src: 'app', link_url: '', category: '', importance: '', keywords: [] },
  { id: 'tip-0001', path: 'AI 꿀팁/20261004_깃허브 자료.md', title: '깃허브 자료', channel: 'https://github.com', topic: 'AI 꿀팁',
    tags: [], upload_date: '2026-10-04', view_count: 0, video_url: '', hash: 'h4', snippet: '', kind: 'tip', subscriber_count: 0, summary_src: '',
    link_url: 'https://github.com/a/b', category: '개발툴', importance: '상', keywords: ['Claude'] },
  // Vault 밖을 가리키는 경로 — readNote 가 막아야 한다
  { id: 'evil-0001', path: '../밖.md', title: '밖', channel: 'x', topic: 'AI Claude', tags: [], upload_date: '2026-10-05', view_count: 0,
    video_url: '', hash: 'h5', snippet: '', kind: 'video', subscriber_count: 0, summary_src: '', link_url: '', category: '', importance: '', keywords: [] },
];
const VECS = [unit(0), mix(0, 1, 0.3), unit(2), mix(0, 3, 0.8), unit(4)];
function writeIndex(built) {
  fs.writeFileSync(path.join(tmp, 'wiki_index.json'), JSON.stringify({ version: 1, model: 'test', dim: DIM, built, notes: NOTES }));
  const buf = Buffer.alloc(NOTES.length * DIM * 4);
  VECS.forEach((v, i) => Buffer.from(v.buffer).copy(buf, i * DIM * 4));
  fs.writeFileSync(path.join(tmp, 'wiki_index.vec'), buf);
}
writeIndex('2026-10-13T10:00:00+0900');
fs.writeFileSync(path.join(V, NOTES[0].path), '---\ntitle: "클로드 코드 입문"\nnotion_id: aaaaaaaa-0000-0000-0000-000000000001\n---\n\n\n**▶ 영상 보기: **https://www.youtube.com/watch?v=AAAAAAAAAAA\n---\n## 영상 개요\n본문 첫 줄\n');
fs.writeFileSync(path.join(tmp, '밖.md'), '비밀\n');

// ── Gemini 요청을 가짜로 — 임베딩 실패(키워드 폴백) 또는 고정 벡터 ──
let netCalls = 0, embedMode = 'fail';
https.request = (opts, cb) => {
  netCalls++;
  const req = new EventEmitter();
  req.write = () => {};
  req.destroy = () => {};
  req.end = () => setImmediate(() => {
    if (embedMode === 'fail') { req.emit('error', new Error('network blocked (test)')); return; }
    const res = new EventEmitter();
    res.statusCode = 200;
    cb(res);
    const values = Array.from(unit(0));
    res.emit('data', Buffer.from(JSON.stringify({ embedding: { values } })));
    res.emit('end');
  });
  return req;
};

process.env.WIKI_SEARCH_DIR = tmp;
process.env.GEMINI_API_KEYS = 'fake-key-for-test';   // 실제 .env 키를 쓰지 않는다 — 요청 자체가 가짜
process.env.WIKI_VAULT = V;
const ws = require(path.join(REPO, 'lib', 'wiki_search.js'));

(async () => {
  try {
    console.log('▶ 1. 전체 목록 (all=1 의 바탕)');
    const pl = ws.listPayload();
    const body = JSON.parse(pl.json);
    check('전체 건수 = 인덱스 노트 수', body.total === NOTES.length && body.notes.length === NOTES.length, body.total);
    const n0 = body.notes[0];
    check('화면용 메타가 담긴다 (kind·subscriber_count·summary_src)', n0.kind === 'video' && n0.subscriber_count === 5000 && n0.summary_src === 'video', n0);
    check('hash 는 보내지 않는다', !('hash' in n0), Object.keys(n0));
    check('빈 값·빈 배열은 뺀다', !('link_url' in n0) && !('keywords' in n0) && body.notes[3].keywords[0] === 'Claude', [n0, body.notes[3]]);
    check('gzip 본문을 풀면 원문과 같다', zlib.gunzipSync(pl.gz).equals(pl.json));
    check('같은 인덱스면 같은 묶음을 다시 쓴다(캐시)', ws.listPayload() === pl);
    await new Promise(r => setTimeout(r, 20));
    writeIndex('2026-10-13T11:00:00+0900');
    const pl2 = ws.listPayload();
    check('인덱스가 바뀌면 built·ETag 가 바뀐다', pl2.built === '2026-10-13T11:00:00+0900' && pl2.etag !== pl.etag, [pl.etag, pl2.etag]);

    console.log('▶ 2. 전체 점수 (scores=1)');
    embedMode = 'fail';
    const kw = await ws.scoreAll('클로드 코드');
    check('임베딩 실패 → 키워드 점수', kw.mode === 'keyword', kw.mode);
    check('키워드: 0점은 빼고 맞는 것만', Object.keys(kw.scores).sort().join() === 'aaaaaaaa-0000-0000-0000-000000000001,aaaaaaaa-0000-0000-0000-000000000002', kw.scores);
    embedMode = 'ok';
    const vec = await ws.scoreAll('클로드 코드');
    check('임베딩 성공 → 의미 점수, 모든 노트', vec.mode === 'vector' && Object.keys(vec.scores).length === NOTES.length, vec);
    check('의미 점수 순서 (1 > 2 > 3)', vec.scores[NOTES[0].id] > vec.scores[NOTES[1].id] && vec.scores[NOTES[1].id] > vec.scores[NOTES[2].id], vec.scores);
    check('built 가 함께 온다', vec.built === '2026-10-13T11:00:00+0900', vec.built);

    console.log('▶ 3. 비슷한 노트 (similar)');
    const sim = ws.similar(NOTES[0].id, 2);
    check('자기 자신은 빠진다', sim.every(x => x.id !== NOTES[0].id), sim);
    check('가까운 순 (심화 0.95 > 꿀팁 0.60)', sim.length === 2 && sim[0].id === NOTES[1].id && sim[1].id === NOTES[3].id, sim);
    check('없는 id → null', ws.similar('zzzz-0000') === null);
    const callsBefore = netCalls;
    ws.similar(NOTES[1].id, 5);
    check('similar 은 Gemini 를 부르지 않는다', netCalls === callsBefore, netCalls - callsBefore);

    console.log('▶ 4. 노트 본문 (noteById)');
    const nb = ws.noteById(NOTES[0].id);
    check('프론트매터는 떼고 본문만', nb && !nb.body.includes('notion_id') && nb.body.includes('본문 첫 줄'), nb);
    check('없는 id → null', ws.noteById('zzzz-0000') === null);
    let threw = false;
    try { ws.noteById('evil-0001'); } catch (e) { threw = /허용되지 않은 경로/.test(e.message); }
    check('Vault 밖 경로는 읽지 않는다', threw);
    check('id 형식 검사: ../ 거부 · uuid 허용', !ws.ID_RE.test('../../etc/passwd') && !ws.ID_RE.test('') && ws.ID_RE.test(NOTES[0].id));

    console.log('▶ 5. 집 안 전용 서버 경로 (127.0.0.1, 임시 포트)');
    const port = 31000 + Math.floor(Math.random() * 2000);
    // WIKI_LAN_ALLOW_CIDR 를 일부러 틀리게 → fail-closed 로 127.0.0.1 에만 묶인다(실제 .env 대역과 무관)
    const child = spawn(process.execPath, [path.join(REPO, 'wiki_lan_server.js')], {
      env: { ...process.env, GEMINI_API_KEYS: 'fake-key-for-test', WIKI_SEARCH_DIR: tmp, WIKI_VAULT: V, WIKI_LAN_PORT: String(port), WIKI_LAN_ALLOW_CIDR: 'invalid-for-test' },
      stdio: ['ignore', 'pipe', 'pipe'],
    });
    let out = '';
    child.stdout.on('data', d => { out += d; });
    child.stderr.on('data', d => { out += d; });
    await new Promise((resolve, reject) => {
      const t0 = Date.now();
      (function wait() { if (/바인딩/.test(out)) return resolve(); if (Date.now() - t0 > 8000) return reject(new Error('서버 기동 실패: ' + out)); setTimeout(wait, 100); })();
    });
    const get = (p, headers = {}) => new Promise((resolve, reject) => {
      http.get({ host: '127.0.0.1', port, path: encodeURI(p), headers: { Host: `127.0.0.1:${port}`, ...headers } }, res => {
        const chunks = [];
        res.on('data', c => chunks.push(c));
        res.on('end', () => resolve({ status: res.statusCode, headers: res.headers, body: Buffer.concat(chunks) }));
      }).on('error', reject);
    });
    try {
      check('fail-closed — 127.0.0.1 에만 묶였다', /바인딩: 127\.0\.0\.1:/.test(out), out.slice(0, 200));
      const a = await get('/api/wiki-search?all=1', { 'Accept-Encoding': 'gzip' });
      const al = JSON.parse(zlib.gunzipSync(a.body));
      check('all=1 → 200 · gzip · ETag', a.status === 200 && a.headers['content-encoding'] === 'gzip' && !!a.headers.etag && al.total === NOTES.length, [a.status, a.headers]);
      const a2 = await get('/api/wiki-search?all=1', { 'If-None-Match': a.headers.etag });
      check('같은 ETag → 304', a2.status === 304, a2.status);
      const s1 = await get(`/api/wiki-search?similar=${NOTES[0].id}`);
      check('similar → 200 · 5개 이하', s1.status === 200 && JSON.parse(s1.body).results.length === NOTES.length - 1, s1.body.toString());
      check('similar 잘못된 id → 400', (await get('/api/wiki-search?similar=../x')).status === 400);
      check('similar 없는 id → 404', (await get('/api/wiki-search?similar=zzzz-0000')).status === 404);
      const n1 = await get(`/api/wiki-note?id=${NOTES[0].id}`);
      check('wiki-note → 200 · 본문', n1.status === 200 && JSON.parse(n1.body).body.includes('본문 첫 줄'), n1.body.toString());
      check('wiki-note 잘못된 id → 400', (await get('/api/wiki-note?id=../../etc/passwd')).status === 400);
      check('wiki-note 없는 id → 404', (await get('/api/wiki-note?id=zzzz-0000')).status === 404);
      const ev = await get('/api/wiki-note?id=evil-0001');
      check('wiki-note Vault 밖 → 404 (내용 없음)', ev.status === 404 && !ev.body.toString().includes('비밀'), ev.body.toString());
      check('검색어 없는 search → 400 (기존 동작)', (await get('/api/wiki-search')).status === 400);
      check('목록에 없는 경로 → 404', (await get('/api/master-ingest')).status === 404);
      const pg = await get('/wiki');
      check('/wiki 화면 → 200', pg.status === 200 && pg.body.toString().includes('AI LLM Wiki'), pg.status);
    } finally {
      child.kill();
    }
    check('Gemini 요청은 가짜로만 2회(점수 2번) — 실제 네트워크 0', netCalls === 2, netCalls);
  } catch (e) {
    check('예외 없이 끝남', false, e.stack);
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
  const ok = results.filter(Boolean).length;
  console.log(`\n${ok}/${results.length} PASS`);
  process.exit(ok === results.length ? 0 : 1);
})();
