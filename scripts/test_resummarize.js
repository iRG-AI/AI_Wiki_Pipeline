#!/usr/bin/env node
// lib/resummarize.js (v4.6-b 기존분 재요약) + lib/library.js 재요약 헬퍼 회귀 테스트
// — 네트워크 0회(영상 조회·요약기는 가짜), 임시 장부(lib/library_schema.sql 그대로).
//   node scripts/test_resummarize.js
//
// 지키는 것:
//   1) 후보 = summary_src != 'video' · 건너뜀 표시 없음 · 최신 업로드부터. 'video' 행은 다시 건드리지 않는다
//   2) 성공 → summary·summary_src video·grade·quality(+resummary_day)·summarized_at·updated_at, wiki_extract → stale(attempts 0, updated_at 그대로)
//   3) 실패는 대체 요약 없이 기존 요약 그대로 — 삭제·공개 아님·영상 토큰 0 은 건너뜀 표시, 형식 실패는 2회에 건너뜀(updated_at 안 건드림)
//   4) 429·5xx·하루 분량·영상 입력 꺼짐은 그 실행 중단
//   5) 실행당 상한 · 태평양시 하루 상한(장부 quality.resummary_day 로 셈) · RESUMMARY=false·VIDEO_SUMMARY=false 면 아무것도 안 함
//   6) 모델·신규 몫 예약을 요약기에 넘긴다
'use strict';
const fs = require('fs');
const os = require('os');
const path = require('path');

const out = (s) => process.stdout.write(s + '\n');
const ROOT = path.join(__dirname, '..');
const library = require(path.join(ROOT, 'lib', 'library'));
const rs = require(path.join(ROOT, 'lib', 'resummarize'));

const TMP = fs.mkdtempSync(path.join(os.tmpdir(), 'resummarize-'));
let seq = 0;
const OLD_TS = '2026-05-01T00:00:00.000Z';

function makeDb(rows, extract = []) {
  const p = path.join(TMP, `lib-${++seq}.db`);
  const { DatabaseSync } = library.loadSqlite();
  const raw = new DatabaseSync(p);
  raw.exec(fs.readFileSync(path.join(ROOT, 'lib', 'library_schema.sql'), 'utf8'));
  const ins = raw.prepare(`INSERT INTO videos (record_id, video_id, title, channel, upload_date, summary, summary_src, grade, quality, created_at, updated_at)
    VALUES (?, ?, ?, 'ch', ?, ?, ?, ?, ?, ?, ?)`);
  for (const r of rows) ins.run(r.id, r.vid, r.title || r.id, r.date, r.summary || '옛 요약', r.src || 'property', r.grade || null, r.quality || null, OLD_TS, OLD_TS);
  for (const id of extract) {
    raw.prepare(`INSERT INTO wiki_extract (record_id, status, source, entities, concepts, attempts, created_at, updated_at)
      VALUES (?, 'ok', 'single', '[]', '[]', 1, 'x', ?)`).run(id, OLD_TS);
  }
  raw.close();
  return library.openLibrary(p);
}
const row = (db, id) => db.prepare('SELECT * FROM videos WHERE record_id = ?').get(id);
const Q = (db, id) => library.parseQuality(row(db, id).quality);

const DET = (o = {}) => ({ privacy: 'public', durationSec: 600, description: '설명', tags: [], realChannelTitle: '채널', ...o });
const GOOD = (grade = 'keep') => ({ ok: true, summary: '## 영상 개요\n새 요약', src: 'video', grade,
  quality: JSON.stringify({ promo_main: grade === 'exclude', why: grade === 'exclude' ? ['promo_main'] : [], model: 'gemini-3.5-flash-lite', sec: 600 }) });
const FAIL = (reason) => ({ ok: false, reason });

function harness({ db, details = {}, script = [], env = {}, today = '2026-10-13' }) {
  const h = { fetched: [], summarized: [], made: [], logs: [] };
  h.run = () => rs.run({
    db, env, todayKey: () => today, log: (m) => h.logs.push(m), sleep: async () => {},
    fetchDetails: async (ids) => { h.fetched.push(ids); const m = {}; for (const id of ids) if (details[id]) m[id] = details[id]; return m; },
    makeSummarizer: (opts) => { h.made.push(opts); return { summarize: async (v) => { h.summarized.push(v.videoId); const s = script.shift(); if (!s) throw new Error('대본 없음'); return s; } }; },
  });
  return h;
}
function assert(c, m) { if (!c) throw new Error(m); }

const BASE = [
  { id: 'r-old', vid: 'VID_OLD____', date: '2026-01-01' },
  { id: 'r-new', vid: 'VID_NEW____', date: '2026-10-01' },
  { id: 'r-mid', vid: 'VID_MID____', date: '2026-06-01', src: 'app', quality: '{"fallback":"bad_summary"}' },
  { id: 'r-vid', vid: 'VID_DONE___', date: '2026-10-10', src: 'video', grade: 'keep' },
  { id: 'r-bad', vid: 'VID_BADQ___', date: '2026-02-01', quality: '깨진 JSON' },
];
const allDetails = Object.fromEntries(BASE.map(r => [r.vid, DET()]));

const cases = [
  ['후보: video 아닌 행만 · 최신 업로드부터 · 깨진 quality 도 후보(던지지 않음)', async () => {
    const db = makeDb(BASE);
    const c = library.resummaryCandidates(db, 10).map(r => r.record_id);
    assert(c.join() === 'r-new,r-mid,r-bad,r-old', c.join());
    assert(library.resummaryRemaining(db) === 4, String(library.resummaryRemaining(db)));
  }],
  ['성공: 장부 갱신 · updated_at 새로 · wiki_extract stale(attempts 0 · updated_at 그대로) · 모델·예약 전달', async () => {
    const db = makeDb(BASE, ['r-new']);
    const h = harness({ db, details: allDetails, script: [GOOD('exclude'), GOOD()], env: { RESUMMARY_PER_RUN: '2' } });
    const r = await h.run();
    const n = row(db, 'r-new'); const q = Q(db, 'r-new');
    assert(r.done === 2 && r.exclude === 1 && h.summarized.join() === 'VID_NEW____,VID_MID____', JSON.stringify(r));
    assert(n.summary_src === 'video' && n.grade === 'exclude' && n.summary.includes('새 요약') && n.updated_at !== OLD_TS && n.summarized_at === n.updated_at, JSON.stringify(n));
    assert(q.resummary === true && q.resummary_day === '2026-10-13' && q.model === 'gemini-3.5-flash-lite', JSON.stringify(q));
    const w = db.prepare("SELECT * FROM wiki_extract WHERE record_id='r-new'").get();
    assert(w.status === 'stale' && w.attempts === 0 && w.updated_at === OLD_TS, JSON.stringify(w));
    assert(h.made.length === 1 && h.made[0].model === 'gemini-3.5-flash-lite' && h.made[0].reserveSeconds === 10800, JSON.stringify(h.made));
    assert(h.fetched.length === 1, '영상 조회는 실행당 1회');
    assert(r.today === 2 && r.remaining === 2, JSON.stringify(r));
    assert(rs.summaryLine(r).startsWith('🔁 재요약: 2편 (제외 등급 1)') && rs.summaryLine(r).includes('오늘 2/20 · 남은 대상 2'), rs.summaryLine(r));
  }],
  ['이미 video 인 행은 updateResummary 가 건드리지 않는다', async () => {
    const db = makeDb(BASE);
    assert(library.updateResummary(db, 'r-vid', { summary: 'x', grade: 'exclude', quality: '{}' }) === false && row(db, 'r-vid').grade === 'keep', '덮어씀');
  }],
  ['건너뜀: 목록에 없음(gone)·일부공개·영상 토큰 0 → 표시 · 요약·updated_at 그대로 · 다음 실행 후보에서 빠짐', async () => {
    const db = makeDb(BASE);
    const det = { ...allDetails }; delete det.VID_NEW____;
    const h = harness({ db, details: det, script: [FAIL('privacy:unlisted'), FAIL('no_video_tokens'), GOOD()] });
    const r = await h.run();
    assert(Q(db, 'r-new').resummary_skip === 'gone' && Q(db, 'r-mid').resummary_skip === 'privacy:unlisted' && Q(db, 'r-bad').resummary_skip === 'no_video_tokens', JSON.stringify([Q(db, 'r-new'), Q(db, 'r-mid'), Q(db, 'r-bad')]));
    assert(Q(db, 'r-mid').fallback === 'bad_summary', '기존 quality 를 덮었다');
    assert(row(db, 'r-new').summary === '옛 요약' && row(db, 'r-new').updated_at === OLD_TS && row(db, 'r-mid').updated_at === OLD_TS, 'updated_at 건드림');
    assert(r.skipped === 3 && r.done === 1 && row(db, 'r-old').summary_src === 'video', JSON.stringify(r));
    assert(library.resummaryCandidates(db, 10).length === 0, '건너뜀 표시가 후보에 남음');
  }],
  ['형식 실패: 1회는 다음에 다시 · 2회면 건너뜀 · 대체 요약 없음', async () => {
    const db = makeDb([{ id: 'r1', vid: 'V1_________', date: '2026-10-01' }]);
    const d = { V1_________: DET() };
    await harness({ db, details: d, script: [FAIL('bad_summary')] }).run();
    assert(Q(db, 'r1').resummary_fail === 1 && !Q(db, 'r1').resummary_skip && library.resummaryCandidates(db, 5).length === 1, JSON.stringify(Q(db, 'r1')));
    await harness({ db, details: d, script: [FAIL('bad_json')] }).run();
    assert(Q(db, 'r1').resummary_fail === 2 && Q(db, 'r1').resummary_skip === 'fail:bad_json' && row(db, 'r1').summary === '옛 요약', JSON.stringify(Q(db, 'r1')));
  }],
  ['중단: 429·5xx·하루 분량·영상 입력 꺼짐 → 그 실행 멈춤 · 표시 안 함', async () => {
    for (const reason of ['video_http_429', 'video_http_503', 'video_http_0', 'daily_video_cap', 'video_403_repeated', 'VIDEO_SUMMARY=false']) {
      const db = makeDb(BASE);
      const h = harness({ db, details: allDetails, script: [FAIL(reason), GOOD()] });
      const r = await h.run();
      assert(r.stopped === reason && h.summarized.length === 1 && !Q(db, 'r-new').resummary_skip && !Q(db, 'r-new').resummary_fail, `${reason}: ${JSON.stringify(r)}`);
    }
    assert(rs.classify('video_http_400') === 'fail' && rs.classify('video_403') === 'fail' && rs.classify('privacy:private') === 'skip', '분류');
  }],
  ['하루 상한: 장부 resummary_day 로 센다 · 다 찼으면 요약기 안 만듦 · 날짜 바뀌면 다시', async () => {
    const rows = BASE.concat([{ id: 'r-today', vid: 'VID_T______', date: '2026-03-01', src: 'video', quality: '{"resummary":true,"resummary_day":"2026-10-13"}' }]);
    const db = makeDb(rows);
    const h = harness({ db, details: allDetails, env: { RESUMMARY_DAILY_MAX: '1' } });
    const r = await h.run();
    assert(r.stopped === 'daily_max' && h.made.length === 0 && h.fetched.length === 0 && r.today === 1 && r.remaining === 4, JSON.stringify(r));
    const h2 = harness({ db, details: allDetails, env: { RESUMMARY_DAILY_MAX: '1' }, script: [GOOD()], today: '2026-10-14' });
    assert((await h2.run()).done === 1, '다음 날 다시');
  }],
  ['실행당 상한(기본 5) · 하루 남은 몫이 더 작으면 그만큼', async () => {
    const many = Array.from({ length: 9 }, (_, i) => ({ id: `m${i}`, vid: `VM${i}_________`.slice(0, 11), date: `2026-09-0${i + 1}` }));
    const det = Object.fromEntries(many.map(r => [r.vid, DET()]));
    const db = makeDb(many);
    const h = harness({ db, details: det, script: Array.from({ length: 9 }, () => GOOD()) });
    assert((await h.run()).done === 5 && h.summarized.length === 5, '기본 5');
    const h2 = harness({ db, details: det, script: Array.from({ length: 9 }, () => GOOD()), env: { RESUMMARY_DAILY_MAX: '7' } });
    assert((await h2.run()).done === 2, '하루 7 - 오늘 5 = 2');
  }],
  ['RESUMMARY=false · VIDEO_SUMMARY=false 면 장부·조회·요약 0', async () => {
    for (const env of [{ RESUMMARY: 'false' }, { VIDEO_SUMMARY: 'false' }]) {
      const db = makeDb(BASE);
      const h = harness({ db, details: allDetails, env });
      const r = await h.run();
      assert(!r.enabled && r.done === 0 && h.fetched.length === 0 && h.made.length === 0 && row(db, 'r-new').quality === null, JSON.stringify(env));
      assert(rs.summaryLine(r).includes('꺼짐'), rs.summaryLine(r));
    }
    assert(rs.settings({ RESUMMARY_PER_RUN: 'x', RESUMMARY_MODEL: ' ' }).perRun === 5 && rs.settings({}).model === 'gemini-3.5-flash-lite', '기본값');
  }],
];

(async () => {
  let pass = 0;
  for (const [name, fn] of cases) {
    try { await fn(); pass++; out(`PASS  ${name}`); }
    catch (e) { out(`FAIL  ${name}\n      → ${e.message}`); }
  }
  fs.rmSync(TMP, { recursive: true, force: true });
  out(`\n${pass}/${cases.length} PASS`);
  process.exit(pass === cases.length ? 0 : 1);
})();
