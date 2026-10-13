#!/usr/bin/env node
// lib/video_summary.js (v4.6 실제 영상 요약 + 품질 신호) 회귀 테스트 — 네트워크 0회(요청 함수는 가짜), 상태 파일은 임시 폴더.
//   node scripts/test_video_summary.js
//
// 지키는 것:
//   1) 요청 모양 — YouTube URL 을 fileData 로, 30분 넘으면 endOffset 1800s, MEDIA_RESOLUTION_LOW, thinkingBudget 0, JSON 응답
//   2) 200 이어도 영상 토큰 0 이면 실패(삭제된 영상이 지어낸 답을 돌려준다 — 10-13 시험) → 설명란 요약으로 대체
//   3) 공개가 아닌 영상·길이 모름·하루 분량 상한·VIDEO_SUMMARY=false 는 영상 요청을 아예 만들지 않는다
//   4) 영상 입력 403 은 그 영상만 대체, 연속 2회면 그 실행에서 영상 입력을 끈다(403 난사 방지). 중간에 성공하면 다시 센다
//   5) 등급은 코드 규칙 — promo_main·generic·AI 무관 중 하나라도면 exclude, 신호가 없으면(대체 요약) null
//   6) 하루 분량 누계는 .video_quota.json 에 태평양시 날짜로 — 날짜가 바뀌면 0부터
//   7) (v4.6-b) 모델 인자 — 2.x 는 thinkingBudget 0, 3.x 는 thinkingLevel minimal(thinkingBudget 은 400). 대체 없음(fallback:false)·신규 몫 예약.
//      bad_summary 는 어느 검사에 걸렸는지 로그 1줄. promo_main 은 무료 자료 배포·구독 유도를 판매로 보지 않는다
//   8) (v4.11) maxServerErrors — 5xx 만 세어 그 횟수면 재시도 그만(재요약용). 주지 않으면 예전대로 키 4개 × 2회
'use strict';
const fs = require('fs');
const os = require('os');
const path = require('path');

const out = (s) => process.stdout.write(s + '\n');
const vs = require(path.join(__dirname, '..', 'lib', 'video_summary'));
const { validateSummary } = require(path.join(__dirname, '..', 'scheduler.js'));

const TMP = fs.mkdtempSync(path.join(os.tmpdir(), 'video-summary-'));
let seq = 0;
const GOOD_MD = '## 영상 개요\n개요 문장.\n\n## 핵심 내용\n* **A**: 설명\n\n## 주요 인사이트\n* **B**: 설명\n\n## 활용 포인트\n실무에 이렇게 활용할 수 있다.';
const SIG = (o = {}) => ({ promo_main: false, generic: false, ai_related: true, has_demo: true, sponsored: false, reason: '근거', ...o });
const ok200 = (sig = SIG(), md = GOOD_MD, videoTok = 42600) => ({
  status: 200,
  data: {
    candidates: [{ content: { parts: [{ text: JSON.stringify({ summary_md: md, signals: sig }) }] } }],
    usageMetadata: { promptTokenCount: videoTok + 19230,
      promptTokensDetails: [{ modality: 'TEXT', tokenCount: 30 }, { modality: 'VIDEO', tokenCount: videoTok }, { modality: 'AUDIO', tokenCount: 19200 }] },
  },
});
const V = (o = {}) => ({ videoId: 'VVVVVVVVVV1', title: '제목', channelTitle: '채널', description: '설명', tags: ['t'],
                          privacy: 'public', durationSec: 600, ...o });

function harness({ script = [], env = {}, today = '2026-10-12', quota, extra = {} } = {}) {
  const quotaFile = path.join(TMP, `q-${++seq}.json`);
  if (quota) fs.writeFileSync(quotaFile, JSON.stringify(quota));
  const h = { requests: [], described: [], rotations: 0, logs: [], quotaFile };
  h.s = vs.makeVideoSummarizer({
    request: async (opts, body) => {
      h.requests.push({ opts, body });
      const step = script.shift();
      if (!step) throw new Error('대본에 없는 요청');
      if (step.netErr) { const e = new Error(step.netErr); e.code = step.netErr; throw e; }
      return step;
    },
    getKey: () => 'TESTKEY', rotateKey: () => { h.rotations++; return true; }, keysCount: 4,
    describe: async (v) => { h.described.push(v.videoId); return '설명란 요약'; },
    validateSummary, todayKey: () => today, log: (m) => h.logs.push(m), sleep: async () => {},
    quotaFile, env, ...extra,
  });
  h.quota = () => JSON.parse(fs.readFileSync(quotaFile, 'utf8'));
  return h;
}
function assert(c, m) { if (!c) throw new Error(m); }

const cases = [
  ['parseDuration: ISO 8601 기간 → 초', async () => {
    assert(vs.parseDuration('PT1H2M3S') === 3723 && vs.parseDuration('PT45S') === 45 && vs.parseDuration('PT12M') === 720, '기본 형식');
    assert(vs.parseDuration('P1DT1S') === 86401 && vs.parseDuration('P0D') === 0, '일 단위·0');
    assert(vs.parseDuration('') === null && vs.parseDuration(undefined) === null && vs.parseDuration('1:02') === null, '못 읽으면 null');
  }],
  ['buildBody: URL·LOW·thinkingBudget 0·JSON 스키마 · 30분 이하는 endOffset 없음', async () => {
    const b = vs.buildBody(V({ durationSec: 1800 }));
    const p = b.contents[0].parts;
    assert(p[0].fileData.fileUri === 'https://www.youtube.com/watch?v=VVVVVVVVVV1' && !p[0].videoMetadata, '영상 파트');
    assert(/영상에서 확인되지 않는 내용은 쓰지 말 것/.test(p[1].text) && /제목: 제목/.test(p[1].text) && /자신의/.test(p[1].text), '프롬프트');
    assert(b.generationConfig.responseSchema.properties.signals.required.includes('sponsored'), 'sponsored 필수');
    const g = b.generationConfig;
    assert(g.mediaResolution === 'MEDIA_RESOLUTION_LOW' && g.thinkingConfig.thinkingBudget === 0 && g.responseMimeType === 'application/json'
           && g.responseSchema.required.includes('signals'), 'generationConfig');
  }],
  ['buildBody: 30분 넘으면 endOffset 1800s (VIDEO_MAX_SECONDS 로 조정)', async () => {
    assert(vs.buildBody(V({ durationSec: 2731 })).contents[0].parts[0].videoMetadata.endOffset === '1800s', '기본 1800s');
    assert(vs.buildBody(V({ durationSec: 2731 }), { maxSeconds: 600 }).contents[0].parts[0].videoMetadata.endOffset === '600s', '조정');
  }],
  ['parseResponse: 영상 토큰 0 = 실패 (삭제 영상이 200 + 지어낸 답)', async () => {
    assert(vs.parseResponse(ok200(SIG(), GOOD_MD, 0).data, validateSummary).reason === 'no_video_tokens', '영상 토큰 0 통과');
    const noDetails = ok200().data; delete noDetails.usageMetadata.promptTokensDetails;
    assert(vs.parseResponse(noDetails, validateSummary).reason === 'no_video_tokens', '세부 토큰 없음 통과');
  }],
  ['parseResponse: 깨진 JSON·신호 누락·요약 4절 미달은 실패, 정상은 신호·토큰 반환', async () => {
    const bad = ok200().data; bad.candidates[0].content.parts[0].text = '{"summary_md": "끊김';
    assert(vs.parseResponse(bad, validateSummary).reason === 'bad_json', 'bad_json');
    assert(vs.parseResponse(ok200({ promo_main: 'yes' }).data, validateSummary).reason === 'bad_signals', 'bad_signals');
    assert(vs.parseResponse(ok200({ sponsored: undefined }).data, validateSummary).reason === 'bad_signals', 'sponsored 누락');
    assert(vs.parseResponse(ok200(SIG(), '## 영상 개요\n짧음').data, validateSummary).reason === 'bad_summary', 'bad_summary');
    const r = vs.parseResponse(ok200().data, validateSummary);
    assert(r.ok && r.summary === GOOD_MD && r.videoTokens === 42600 && r.signals.has_demo === true, '정상');
  }],
  ['computeGrade: 판매 주목적·일반론·AI 무관 → exclude, 모두 아니면 keep, 신호 없으면 null · 유료 광고는 제외 사유 아님', async () => {
    const g = (o) => vs.computeGrade(SIG(o));
    assert(g({}).grade === 'keep' && g({}).why.length === 0, 'keep');
    assert(g({ promo_main: true }).grade === 'exclude' && g({ promo_main: true }).why[0] === 'promo_main', 'promo');
    assert(g({ generic: true }).why[0] === 'generic' && g({ ai_related: false }).why[0] === 'not_ai', 'generic·not_ai');
    assert(g({ promo_main: true, ai_related: false }).why.join() === 'promo_main,not_ai', '복수 사유');
    assert(vs.computeGrade(null).grade === null, '신호 없음');
    assert(g({ has_demo: false }).grade === 'keep' && g({ sponsored: true }).grade === 'keep', 'has_demo·sponsored(유료 광고) 는 등급에 안 쓴다');
  }],
  ['summarize: 공개 영상 → src video · 등급 · quality JSON · 분량 누계(앞 30분만 셈)', async () => {
    const h = harness({ script: [ok200(SIG({ promo_main: true }))] });
    const r = await h.s.summarize(V({ durationSec: 2731 }));
    const q = JSON.parse(r.quality);
    assert(r.src === 'video' && r.grade === 'exclude' && r.summary === GOOD_MD, JSON.stringify(r).slice(0, 200));
    assert(q.why.join() === 'promo_main' && q.sec === 1800 && q.clipped === true && q.model === 'gemini-2.5-flash' && q.video_tokens === 42600, r.quality);
    assert(h.requests.length === 1 && /gemini-2\.5-flash:generateContent\?key=TESTKEY$/.test(h.requests[0].opts.path), '요청');
    assert(h.described.length === 0, '설명란 요약을 불렀다');
    const qt = h.quota();
    assert(qt.date === '2026-10-12' && qt.seconds === 1800 && qt.calls === 1, JSON.stringify(qt));
    assert(h.s.stats.video === 1 && h.s.stats.exclude === 1, JSON.stringify(h.s.stats));
  }],
  ['summarize: 일부공개·비공개·길이 모름은 영상 요청 없이 설명란 요약 (src app · grade null)', async () => {
    const h = harness();
    for (const v of [V({ privacy: 'unlisted' }), V({ privacy: 'private' }), V({ privacy: '' }), V({ durationSec: null }), V({ durationSec: 0 })]) {
      const r = await h.s.summarize(v);
      assert(r.src === 'app' && r.grade === null && r.summary === '설명란 요약', JSON.stringify(r));
    }
    assert(h.requests.length === 0 && h.described.length === 5, `요청 ${h.requests.length}`);
    assert(h.s.stats.reasons['privacy:unlisted'] === 1 && h.s.stats.reasons.no_duration === 2, JSON.stringify(h.s.stats.reasons));
  }],
  ['summarize: 삭제 영상(200 + 영상 토큰 0)은 설명란 요약으로 대체', async () => {
    const h = harness({ script: [ok200(SIG(), GOOD_MD, 0)] });
    const r = await h.s.summarize(V());
    assert(r.src === 'app' && r.grade === null && JSON.parse(r.quality).fallback === 'no_video_tokens', JSON.stringify(r));
    assert(h.requests.length === 1 && h.described.length === 1, '호출 수');
  }],
  ['summarize: 403 연속 2회 → 그 실행에서 영상 입력 끔 (3번째는 요청 없음)', async () => {
    const h = harness({ script: [{ status: 403, data: {} }, { status: 403, data: {} }] });
    const r1 = await h.s.summarize(V()); const r2 = await h.s.summarize(V()); const r3 = await h.s.summarize(V());
    assert([r1, r2, r3].every(r => r.src === 'app'), '대체 아님');
    assert(h.requests.length === 2 && h.described.length === 3, `요청 ${h.requests.length}`);
    assert(JSON.parse(r3.quality).fallback === 'video_403_repeated', r3.quality);
    assert(h.rotations === 0, '403 에 키를 돌렸다(재시도 금지)');
  }],
  ['summarize: 403 다음 성공이면 연속 횟수를 다시 센다', async () => {
    const h = harness({ script: [{ status: 403, data: {} }, ok200(), { status: 403, data: {} }, ok200()] });
    const srcs = [];
    for (let i = 0; i < 4; i++) srcs.push((await h.s.summarize(V())).src);
    assert(srcs.join() === 'app,video,app,video' && h.requests.length === 4, srcs.join());
  }],
  ['summarize: 429 → 다음 키로 바로 재시도 후 성공 · 네트워크 오류도 재시도', async () => {
    const h = harness({ script: [{ status: 429, data: {} }, { netErr: 'ECONNRESET' }, ok200()] });
    const r = await h.s.summarize(V());
    assert(r.src === 'video' && h.requests.length === 3 && h.rotations === 2, `요청 ${h.requests.length} · 회전 ${h.rotations}`);
  }],
  ['summarize: 429 가 끝까지 이어지면 설명란 요약 (시도 상한 = 키 4개 × 2)', async () => {
    const h = harness({ script: Array.from({ length: 8 }, () => ({ status: 429, data: {} })) });
    const r = await h.s.summarize(V());
    assert(r.src === 'app' && h.requests.length === 8 && JSON.parse(r.quality).fallback === 'video_http_429', r.quality);
  }],
  ['(v4.11) maxServerErrors 1: 5xx 1회면 재시도 없이 실패 · 키 회전 0 · 분량 1회 · 로그 1줄', async () => {
    const h = harness({ script: [{ status: 503, data: {} }], extra: { fallback: false, maxServerErrors: 1 } });
    const r = await h.s.summarize(V());
    assert(!r.ok && r.reason === 'video_http_503' && h.requests.length === 1 && h.rotations === 0 && h.described.length === 0, JSON.stringify(r));
    assert(h.quota().calls === 1 && h.logs.some(l => /재시도 그만 \(5xx 1\/1\)/.test(l)), h.logs.join('|'));
  }],
  ['(v4.11) maxServerErrors 는 5xx 만 센다 — 429·네트워크 오류는 그대로 키를 돌림 · 없으면 예전대로 8회', async () => {
    const h = harness({ script: [{ status: 503, data: {} }, { status: 429, data: {} }, { netErr: 'ECONNRESET' }, { status: 500, data: {} }],
                        extra: { fallback: false, maxServerErrors: 2 } });
    const r = await h.s.summarize(V());
    assert(r.reason === 'video_http_500' && h.requests.length === 4 && h.rotations === 3, `요청 ${h.requests.length} · 회전 ${h.rotations}`);
    const h2 = harness({ script: Array.from({ length: 8 }, () => ({ status: 503, data: {} })) });
    const r2 = await h2.s.summarize(V());
    assert(r2.src === 'app' && h2.requests.length === 8 && JSON.parse(r2.quality).fallback === 'video_http_503', `기본 ${h2.requests.length}`);
  }],
  ['summarize: 400 등 그 밖의 오류는 재시도 없이 대체', async () => {
    const h = harness({ script: [{ status: 400, data: {} }] });
    const r = await h.s.summarize(V());
    assert(r.src === 'app' && h.requests.length === 1 && h.rotations === 0, '재시도했다');
  }],
  ['summarize: 하루 분량 상한을 넘을 영상은 요청하지 않는다 · 실패 요청도 분량을 센다', async () => {
    const h = harness({ quota: { date: '2026-10-12', seconds: 8 * 3600 - 300, calls: 30 } });
    const r = await h.s.summarize(V({ durationSec: 600 }));
    assert(r.src === 'app' && h.requests.length === 0 && JSON.parse(r.quality).fallback === 'daily_video_cap', r.quality);
    const h2 = harness({ script: [{ status: 403, data: {} }], quota: { date: '2026-10-12', seconds: 100, calls: 1 } });
    await h2.s.summarize(V({ durationSec: 200 }));
    assert(h2.quota().seconds === 300 && h2.quota().calls === 2, JSON.stringify(h2.quota()));
  }],
  ['summarize: 누계 날짜(PT)가 바뀌면 0부터 · VIDEO_DAILY_SECONDS 로 상한 조정', async () => {
    const h = harness({ script: [ok200()], quota: { date: '2026-10-11', seconds: 8 * 3600, calls: 99 } });
    const r = await h.s.summarize(V());
    assert(r.src === 'video' && h.quota().date === '2026-10-12' && h.quota().seconds === 600 && h.quota().calls === 1, JSON.stringify(h.quota()));
    const h2 = harness({ env: { VIDEO_DAILY_SECONDS: '500' } });
    assert((await h2.s.summarize(V({ durationSec: 600 }))).src === 'app' && h2.requests.length === 0, '상한 조정 무시');
  }],
  ['summarize: VIDEO_SUMMARY=false 면 영상 요청 0 · 전부 설명란 요약', async () => {
    const h = harness({ env: { VIDEO_SUMMARY: 'false' } });
    const r = await h.s.summarize(V());
    assert(r.src === 'app' && h.requests.length === 0 && JSON.parse(r.quality).fallback === 'VIDEO_SUMMARY=false', r.quality);
  }],
  ['(v4.6-b) thinkingConfig: 2.x = thinkingBudget 0 · 3.x = thinkingLevel minimal (thinkingBudget 없음)', async () => {
    assert(vs.thinkingConfigFor('gemini-2.5-flash').thinkingBudget === 0, '2.5');
    const t = vs.thinkingConfigFor('gemini-3.5-flash-lite');
    assert(t.thinkingLevel === 'minimal' && !('thinkingBudget' in t), JSON.stringify(t));
    const g = vs.buildBody(V(), { model: 'gemini-3.5-flash-lite' }).generationConfig;
    assert(g.thinkingConfig.thinkingLevel === 'minimal' && g.mediaResolution === 'MEDIA_RESOLUTION_LOW', JSON.stringify(g.thinkingConfig));
    assert(vs.buildBody(V()).generationConfig.thinkingConfig.thinkingBudget === 0, '기본 모델은 2.5');
  }],
  ['(v4.6-b) 모델 인자: 요청 경로·quality.model 이 그 모델', async () => {
    const h = harness({ script: [ok200()], extra: { model: 'gemini-3.5-flash-lite' } });
    const r = await h.s.summarize(V());
    assert(r.ok && /gemini-3\.5-flash-lite:generateContent/.test(h.requests[0].opts.path) && JSON.parse(r.quality).model === 'gemini-3.5-flash-lite', r.quality);
    assert(h.requests[0].body.generationConfig.thinkingConfig.thinkingLevel === 'minimal', '본문 thinking');
  }],
  ['(v4.6-b) fallback:false — 실패하면 설명란 요약을 부르지 않고 {ok:false, reason}', async () => {
    const h = harness({ script: [ok200(SIG(), GOOD_MD, 0), { status: 400, data: {} }], extra: { fallback: false } });
    const r1 = await h.s.summarize(V()); const r2 = await h.s.summarize(V({ privacy: 'unlisted' })); const r3 = await h.s.summarize(V());
    assert(r1.ok === false && r1.reason === 'no_video_tokens' && r2.reason === 'privacy:unlisted' && r3.reason === 'video_http_400', JSON.stringify([r1, r2, r3]));
    assert(h.described.length === 0 && h.logs.some(l => /영상 요약 실패 \(no_video_tokens\)/.test(l)), h.logs.join('|'));
  }],
  ['(v4.6-b) reserveSeconds: 하루 상한에서 예약분을 빼고 판단 (신규 몫 보호)', async () => {
    const h = harness({ quota: { date: '2026-10-12', seconds: 5 * 3600, calls: 9 }, extra: { reserveSeconds: 3 * 3600, fallback: false } });
    const r = await h.s.summarize(V({ durationSec: 600 }));
    assert(r.ok === false && r.reason === 'daily_video_cap' && h.requests.length === 0, JSON.stringify(r));
    const h2 = harness({ script: [ok200()], quota: { date: '2026-10-12', seconds: 5 * 3600, calls: 9 } });
    assert((await h2.s.summarize(V({ durationSec: 600 }))).src === 'video', '예약 없으면 통과해야');
  }],
  ['(v4.6-b) bad_summary 사유: summaryProblem · 로그 1줄', async () => {
    assert(vs.summaryProblem(GOOD_MD) === '' && vs.summaryProblem('') === 'empty' && vs.summaryProblem('요약 불가') === 'empty', '기본');
    assert(vs.summaryProblem('## 영상 개요\n짧음') === 'missing:## 핵심 내용|## 주요 인사이트|## 활용 포인트', vs.summaryProblem('## 영상 개요\n짧음'));
    assert(vs.summaryProblem(GOOD_MD.replace('실무에 이렇게 활용할 수 있다.', '짧다')) === 'short_tail:2', '활용 포인트 짧음');
    const h = harness({ script: [ok200(SIG(), '## 영상 개요\n## 핵심 내용\n## 주요 인사이트\n본문')] });
    const r = await h.s.summarize(V());
    assert(r.src === 'app' && h.logs.some(l => l.includes('(bad_summary: missing:## 활용 포인트)')) && h.s.stats.reasons.bad_summary === 1, h.logs.join('|'));
  }],
  ['(v4.6-b) promo_main 프롬프트: 무료 자료 배포·구독 유도·끝에 잠깐 알리는 자기 홍보는 판매 아님', async () => {
    assert(/무료 자료·템플릿·키트 배포/.test(vs.PROMPT) && /돈을 받는/.test(vs.PROMPT) && /자신의/.test(vs.PROMPT) && /잠깐 알리는 정도도 false/.test(vs.PROMPT), '프롬프트 문구');
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
