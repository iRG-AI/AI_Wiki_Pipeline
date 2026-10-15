#!/usr/bin/env node
// lib/classifier.js (v4.14 분류 모델 전환) 회귀 테스트 — 네트워크 0회(https.request 를 가짜로 바꾼다).
//   node scripts/test_classifier.js
//
// 지키는 것:
//   1) 모델 기본값은 gemini-3.5-flash-lite, .env CLASSIFY_MODEL 로 바꾼다(앞뒤 공백 무시, 빈 값이면 기본값)
//   2) 2.x 는 thinkingBudget 0, 3.x 는 thinkingLevel minimal — 3.x 에 thinkingBudget 을 보내면 400 이다(둘을 같이 보내지 않는다)
//   3) 요청 주소의 모델 = opts.model 또는 기본 모델, 키는 opts.geminiApiKey. temperature 0.2 · JSON 응답은 그대로
//   4) 응답 한글이 청크 경계에서 잘려도 토픽이 깨지지 않는다(Buffer.concat) — 깨지면 allowedSet 에서 떨어져 토픽이 사라진다
//   5) 결과에 model 이 붙는다. allowedSet 필터·5개 상한·confidence 0~1 은 그대로
//   6) 200 이 아니면 "Gemini <상태>" 로 던진다 — scheduler 의 429·5xx·401/403 판정이 이 문구를 본다
'use strict';
const https = require('https');
const { EventEmitter } = require('events');
const path = require('path');

const out = (s) => process.stdout.write(s + '\n');
const assert = (c, m) => { if (!c) throw new Error(m || '조건 불일치'); };
const cls = require(path.join(__dirname, '..', 'lib', 'classifier'));

const TOPICS = ['AI Claude', 'AI 생산성 향상', 'AI 바이브코딩', 'AI Gemini', 'AI 자동화', 'AI 트렌드'];

// 가짜 https.request — 요청을 기록하고, 응답 본문을 정해진 바이트 조각으로 나눠 보낸다
let calls = [];
function fake({ status = 200, json, raw, split } = {}) {
  https.request = (opts, cb) => {
    const req = new EventEmitter();
    let body = '';
    req.write = (b) => { body += b; };
    req.end = () => {
      calls.push({ opts, body: JSON.parse(body) });
      const res = new EventEmitter();
      res.statusCode = status;
      cb(res);
      const buf = Buffer.from(raw !== undefined ? raw : JSON.stringify(json), 'utf8');
      const parts = split ? split(buf) : [buf];
      setImmediate(() => { for (const p of parts) res.emit('data', p); res.emit('end'); });
    };
    return req;
  };
}
const answer = (obj) => ({ candidates: [{ content: { parts: [{ text: JSON.stringify(obj) }] } }] });
const run = (opts = {}) => cls.classifyTopics({ summary: '요약', title: '제목', channel: '채널' }, TOPICS,
                                              { geminiApiKey: 'TESTKEY', maxRetries: 0, ...opts });

const cases = [
  ['모델 기본값 3.5 Flash-Lite · CLASSIFY_MODEL 로 바꿈(공백 무시, 빈 값이면 기본값)', async () => {
    assert(cls.DEFAULT_MODEL === 'gemini-3.5-flash-lite', cls.DEFAULT_MODEL);
    assert(cls.resolveModel({}) === 'gemini-3.5-flash-lite');
    assert(cls.resolveModel({ CLASSIFY_MODEL: '  gemini-2.5-flash ' }) === 'gemini-2.5-flash');
    assert(cls.resolveModel({ CLASSIFY_MODEL: '   ' }) === 'gemini-3.5-flash-lite');
    assert(cls.resolveModel() === 'gemini-3.5-flash-lite');
  }],
  ['thinking 설정 — 2.x 는 thinkingBudget 0, 3.x 는 thinkingLevel minimal (같이 보내지 않음)', async () => {
    const a = cls.thinkingConfigFor('gemini-2.5-flash');
    const b = cls.thinkingConfigFor('gemini-3.5-flash-lite');
    assert(JSON.stringify(a) === '{"thinkingBudget":0}', JSON.stringify(a));
    assert(JSON.stringify(b) === '{"thinkingLevel":"minimal"}', JSON.stringify(b));
  }],
  ['3.5 Flash-Lite 요청 — 주소의 모델·키, thinkingLevel minimal, temperature 0.2, JSON 응답', async () => {
    calls = [];
    fake({ json: answer({ topics: ['AI Claude'], confidence: 0.9, reasoning: 'r' }) });
    const r = await run({ model: 'gemini-3.5-flash-lite' });
    const c = calls[0];
    assert(calls.length === 1, `요청 ${calls.length}회`);
    assert(c.opts.path === '/v1beta/models/gemini-3.5-flash-lite:generateContent?key=TESTKEY', c.opts.path);
    const g = c.body.generationConfig;
    assert(JSON.stringify(g.thinkingConfig) === '{"thinkingLevel":"minimal"}', JSON.stringify(g.thinkingConfig));
    assert(g.temperature === 0.2 && g.responseMimeType === 'application/json', JSON.stringify(g));
    assert(r.model === 'gemini-3.5-flash-lite' && r.topics.join() === 'AI Claude', JSON.stringify(r));
  }],
  ['2.5 Flash 로 되돌린 요청 — thinkingBudget 0 그대로', async () => {
    calls = [];
    fake({ json: answer({ topics: ['AI Gemini'], confidence: 0.8 }) });
    const r = await run({ model: 'gemini-2.5-flash' });
    assert(calls[0].opts.path.startsWith('/v1beta/models/gemini-2.5-flash:generateContent?'), calls[0].opts.path);
    assert(JSON.stringify(calls[0].body.generationConfig.thinkingConfig) === '{"thinkingBudget":0}');
    assert(r.model === 'gemini-2.5-flash');
  }],
  ['opts.model 없으면 모듈 모델(MODEL) — 결과 model 도 같다', async () => {
    calls = [];
    fake({ json: answer({ topics: [], confidence: 0.5 }) });
    const r = await run();
    assert(calls[0].opts.path.startsWith(`/v1beta/models/${cls.MODEL}:generateContent?`), calls[0].opts.path);
    assert(r.model === cls.MODEL, r.model);
  }],
  ['응답 한글이 청크 경계에서 잘려도 토픽이 깨지지 않는다 (Buffer.concat)', async () => {
    calls = [];
    // 「생산성」 글자 한가운데(UTF-8 3바이트 중 1바이트 뒤)에서 자른다
    fake({
      json: answer({ topics: ['AI 생산성 향상', 'AI 바이브코딩'], confidence: 0.9 }),
      split: (buf) => {
        const at = buf.indexOf(Buffer.from('생', 'utf8')) + 1;
        const at2 = buf.indexOf(Buffer.from('브', 'utf8')) + 2;
        return [buf.subarray(0, at), buf.subarray(at, at2), buf.subarray(at2)];
      },
    });
    const r = await run();
    assert(r.topics.join('|') === 'AI 생산성 향상|AI 바이브코딩', `토픽 ${JSON.stringify(r.topics)}`);
    assert(r.droppedTopics.length === 0, `dropped ${JSON.stringify(r.droppedTopics)}`);
  }],
  ['allowedSet 필터·5개 상한·confidence 0~1 은 그대로', async () => {
    calls = [];
    fake({ json: answer({ topics: ['AI Claude', '없는 토픽', 'AI Gemini', 'AI 자동화', 'AI 트렌드', 'AI 바이브코딩', 'AI 생산성 향상'], confidence: 1.7 }) });
    const r = await run();
    assert(r.topics.length === 5 && !r.topics.includes('없는 토픽'), JSON.stringify(r.topics));
    assert(r.droppedTopics.join() === '없는 토픽', JSON.stringify(r.droppedTopics));
    assert(r.confidence === 1, String(r.confidence));
  }],
  ['200 이 아니면 "Gemini <상태>" 로 던진다 (scheduler 429·5xx·401/403 판정용)', async () => {
    for (const status of [429, 503, 400]) {
      calls = [];
      fake({ status, json: { error: { code: status, message: 'x' } } });
      let msg = '';
      try { await run(); } catch (e) { msg = e.message; }
      assert(new RegExp(`Gemini ${status}\\b`).test(msg), `${status}: ${msg}`);
      assert(calls.length === 1, `maxRetries 0 인데 요청 ${calls.length}회`);
    }
  }],
];

(async () => {
  const orig = https.request;
  let pass = 0;
  for (const [name, fn] of cases) {
    try { await fn(); pass++; out(`PASS  ${name}`); }
    catch (e) { out(`FAIL  ${name}\n      → ${e.message}`); }
  }
  https.request = orig;
  out(`\n${pass}/${cases.length} PASS`);
  process.exit(pass === cases.length ? 0 : 1);
})();
