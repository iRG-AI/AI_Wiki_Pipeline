// v4.6 실제 영상 요약 — Gemini 에 YouTube URL 을 영상으로 넣어 요약하고, 같은 호출에서 품질 신호를 받는다.
// 설명란만 보고 "추론해서라도 작성"하던 요약이 빈약한 설명란에서 지어낸 내용이 되던 문제(2026-10-12 시험)를 막는다.
//
// ★ 모델은 사실 신호만 낸다(promo_main·generic·ai_related·has_demo·sponsored). 등급(keep|exclude)은 computeGrade 의 코드 규칙이 정한다.
//   모델에게 A/B/C 를 매기게 했더니 컨설팅 판매 영상에도 A 를 줬다(10-12 시험).
// ★ 영상 입력이 안 되면 기존 설명란 요약(scheduler.js:geminiSummarize)으로 대체하고 등급은 미판정(null)으로 둔다.
//   - 공개(public)가 아닌 영상은 시도하지 않는다 — 일부공개는 403 PERMISSION_DENIED (10-13 시험)
//   - 200 이어도 영상 토큰이 0 이면 실패다 — 삭제된 영상은 200 + 영상 토큰 0 + 지어낸 답이 온다 (10-13 시험)
//   - 영상 입력 403 은 영상 단위 거부라 그 영상만 대체한다. 대체 요약(같은 키)이 403 이면 geminiSummarize 가 기존대로 종료한다.
//     연속 2회면 그 실행에서 영상 입력을 끈다(403 난사 방지 — 보안 원칙 1).
// ★ 무료 등급 영상 입력은 하루 8시간 분량 상한(미리보기 기능). .video_quota.json 에 태평양시 날짜로 초를 센다.
//   30분 넘는 영상은 videoMetadata.endOffset 으로 앞 30분만 넣는다(10-13 시험: endOffset 600s → 마지막 장면 09:59).
// ★ (v4.6-b) 같은 모듈을 기존분 재요약(lib/resummarize.js)이 모델·대체 없음·신규 몫 예약으로 다시 쓴다.
//   gemini-3.x 는 thinkingBudget 0 을 400 INVALID_ARGUMENT 로 거절한다(10-13 시험) → 모델별로 thinkingConfig 를 나눈다.
//   2.5 Flash 의 thinkingBudget 0(비용 85% 절감)은 그대로 둘 것.
'use strict';
const fs = require('fs');
const path = require('path');

const MODEL = 'gemini-2.5-flash';
const DEFAULT_MAX_SECONDS = 1800;          // 30분 — 이보다 길면 앞부분만
const DEFAULT_DAILY_SECONDS = 8 * 3600;    // 무료 등급 하루 영상 분량 상한
const MAX_403_IN_A_ROW = 2;

const PROMPT = `당신은 YouTube 영상 콘텐츠를 분석하는 전문 리서처입니다.
첨부한 영상을 실제로 보고 들은 내용만으로 경영진이 읽는 보고서를 한국어로 작성하고, 영상의 성격을 판정하세요.

[절대 규칙]
- 영상에서 확인되지 않는 내용은 쓰지 말 것 (제목·설명란만 보고 추측하지 말 것)
- summary_md 에는 아래 4개 섹션을 모두 작성할 것. 각 섹션 제목은 ## 로 시작
- 핵심 내용과 주요 인사이트는 * 로 시작하는 항목으로, 핵심 키워드는 **텍스트** 로 표시

[summary_md 형식]
## 영상 개요
(영상의 실제 주제, 대상 시청자, 주요 목적을 3문장으로)

## 핵심 내용
* **[핵심 키워드]**: (영상에서 실제로 보여 주거나 말한 구체적 내용 1~2문장)
(4개 이상)

## 주요 인사이트
* **[인사이트]**: (비즈니스/실무 관점의 시사점 1~2문장)
(3개)

## 활용 포인트
(실무나 의사결정에 어떻게 활용할지 2~3문장)

[signals — 영상 전체를 기준으로 사실만 판정]
- promo_main: 영상을 만든 채널(제작자) **자신의** 강의·컨설팅·코칭·유료 커뮤니티·자기 상품을 팔거나 모집하는 것이 영상의 주목적이면 true.
  다른 회사의 AI 도구·서비스를 소개·시연하는 영상은 협찬·유료 광고·제휴여도 사용법이나 결과를 실제로 보여 주면 false.
  무료 자료·템플릿·키트 배포, 구독·댓글·알림 설정·뉴스레터 유도는 판매가 아니므로 false.
  영상 내용 대부분이 실제 사용법·정보이고 끝이나 중간에 자기 강의·상품을 잠깐 알리는 정도도 false
  (영상의 주된 내용이 돈을 받는 강의·컨설팅·코칭·유료 커뮤니티·자기 상품을 팔거나 모집하는 것일 때만 true)
- sponsored: 협찬·유료 광고·제휴(어필리에이트) 표시나 언급이 있으면 true (이것만으로 영상을 낮게 보지 말 것)
- generic: 구체적인 도구·절차·수치·사례 없이 일반론·동기부여·소식 나열에 그치면 true
- ai_related: AI(생성형 AI·LLM·AI 도구·AI 개발·AI 산업)를 직접 다루면 true
- has_demo: 화면 시연이나 실제 작업 과정을 보여 주면 true
- reason: 위 판정의 근거 한 문장`;

const RESPONSE_SCHEMA = {
  type: 'OBJECT',
  properties: {
    summary_md: { type: 'STRING' },
    signals: {
      type: 'OBJECT',
      properties: {
        promo_main: { type: 'BOOLEAN' },
        generic:    { type: 'BOOLEAN' },
        ai_related: { type: 'BOOLEAN' },
        has_demo:   { type: 'BOOLEAN' },
        sponsored:  { type: 'BOOLEAN' },
        reason:     { type: 'STRING' },
      },
      required: ['promo_main', 'generic', 'ai_related', 'has_demo', 'sponsored', 'reason'],
    },
  },
  required: ['summary_md', 'signals'],
};

// ISO 8601 기간(PT1H2M3S, P1DT2H) → 초. 못 읽으면 null
function parseDuration(s) {
  const m = /^P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?$/.exec(String(s || ''));
  if (!m) return null;
  return (+(m[1] || 0)) * 86400 + (+(m[2] || 0)) * 3600 + (+(m[3] || 0)) * 60 + (+(m[4] || 0));
}

// (v4.6-b) 2.x 는 thinkingBudget 0(비용 절감), 3.x 는 thinkingBudget 을 거절하므로 thinkingLevel minimal
function thinkingConfigFor(model) {
  return /^gemini-2\./.test(String(model || MODEL)) ? { thinkingBudget: 0 } : { thinkingLevel: 'minimal' };
}

function buildBody(v, { maxSeconds = DEFAULT_MAX_SECONDS, model = MODEL } = {}) {
  const part = { fileData: { fileUri: `https://www.youtube.com/watch?v=${v.videoId}` } };
  if (v.durationSec && v.durationSec > maxSeconds) part.videoMetadata = { endOffset: `${maxSeconds}s` };
  const info = `[영상 정보 — 참고용]\n제목: ${v.title}\n채널: ${v.channelTitle}\n설명: ${(v.description || '(없음)').slice(0, 3000)}\n태그: ${v.tags?.join(', ') || '(없음)'}`;
  return {
    contents: [{ parts: [part, { text: `${PROMPT}\n\n${info}` }] }],
    generationConfig: {
      temperature: 0.3,
      maxOutputTokens: 4000,
      thinkingConfig: thinkingConfigFor(model),
      mediaResolution: 'MEDIA_RESOLUTION_LOW',
      responseMimeType: 'application/json',
      responseSchema: RESPONSE_SCHEMA,
    },
  };
}

function videoTokens(usage) {
  return (usage?.promptTokensDetails || [])
    .filter(d => d.modality === 'VIDEO')
    .reduce((a, d) => a + (d.tokenCount || 0), 0);
}

// (v4.6-b) 요약이 4절 형식 검사(scheduler.js:validateSummary)에 걸린 이유 — 로그 1줄용. 통과면 ''
const SECTIONS = ['## 영상 개요', '## 핵심 내용', '## 주요 인사이트', '## 활용 포인트'];
function summaryProblem(summary) {
  const s = String(summary || '');
  if (!s.trim() || s === '요약 불가') return 'empty';
  const missing = SECTIONS.filter(sec => !s.includes(sec));
  if (missing.length) return `missing:${missing.join('|')}`;
  const tail = s.slice(s.indexOf('## 활용 포인트') + '## 활용 포인트'.length).trim();
  if (tail.length < 10) return `short_tail:${tail.length}`;
  return '';
}

// 200 응답 → { ok:true, summary, signals, videoTokens, promptTokens } | { ok:false, reason[, detail] }
function parseResponse(data, validateSummary) {
  const vt = videoTokens(data?.usageMetadata);
  if (vt <= 0) return { ok: false, reason: 'no_video_tokens' };
  const text = data?.candidates?.[0]?.content?.parts?.[0]?.text || '';
  let j;
  try { j = JSON.parse(text); } catch { return { ok: false, reason: 'bad_json' }; }
  const summary = String(j?.summary_md || '').trim();
  const s = j?.signals || {};
  const bools = ['promo_main', 'generic', 'ai_related', 'has_demo', 'sponsored'];
  if (!bools.every(k => typeof s[k] === 'boolean')) return { ok: false, reason: 'bad_signals' };
  if (validateSummary && !validateSummary(summary)) return { ok: false, reason: 'bad_summary', detail: summaryProblem(summary) || `len:${summary.length}` };
  const signals = { promo_main: s.promo_main, generic: s.generic, ai_related: s.ai_related, has_demo: s.has_demo,
                    sponsored: s.sponsored, reason: String(s.reason || '').slice(0, 300) };
  return { ok: true, summary, signals, videoTokens: vt, promptTokens: data?.usageMetadata?.promptTokenCount || 0 };
}

// 등급 규칙 (대표님 결정 10-12): ① 판매가 주목적 ② 구체 정보 없는 일반론 ③ AI 무관 → exclude.
// 유료 광고·협찬(sponsored)·시연 여부(has_demo)는 기록만 하고 등급에 쓰지 않는다 — 10-13 시험에서 정의가 넓으면
// 다른 회사 도구 시연(협찬)까지 promo_main 으로 잡혀, promo_main 을 "제작자 자신의 판매"로 좁혔다.
function computeGrade(signals) {
  if (!signals) return { grade: null, why: [] };
  const why = [];
  if (signals.promo_main) why.push('promo_main');
  if (signals.generic) why.push('generic');
  if (!signals.ai_related) why.push('not_ai');
  return { grade: why.length ? 'exclude' : 'keep', why };
}

// ── 하루 영상 분량 누계 (.video_quota.json {date(PT), seconds, calls}) ──
function readQuota(file, todayKey) {
  try {
    const j = JSON.parse(fs.readFileSync(file, 'utf8'));
    if (j.date === todayKey()) return { date: j.date, seconds: +j.seconds || 0, calls: +j.calls || 0 };
  } catch {}
  return { date: todayKey(), seconds: 0, calls: 0 };
}
function writeQuota(file, q) {
  try { fs.writeFileSync(file, JSON.stringify(q, null, 2)); return true; } catch { return false; }
}

// deps: request(options, body) → {status, data} · getKey() · rotateKey() · keysCount
//       describe(v) → 설명란 요약 문자열(scheduler.js:geminiSummarize) · validateSummary · todayKey · log · sleep
//       quotaFile · env(process.env 형태)
//       (v4.6-b, 선택) model(기본 MODEL) · fallback(기본 true — false 면 실패 시 설명란 요약을 부르지 않고 {ok:false, reason} 반환)
//                      · reserveSeconds(기본 0 — 하루 분량 상한에서 이만큼을 남겨 둔다. 재요약이 신규 영상 몫을 먹지 않게)
//       (v4.11, 선택) maxServerErrors(기본 0 = 상한 없음) — 영상 1편에서 5xx 응답이 이 횟수에 이르면 재시도를 그만둔다.
//                      재요약이 1 을 넘긴다(3.5 Flash-Lite 503 은 1~2분 뒤에 와서 8회면 약 13분). 429·네트워크 오류는 따로 — 그대로 키를 돌린다
function makeVideoSummarizer(deps) {
  const env = deps.env || {};
  const enabled = env.VIDEO_SUMMARY !== 'false';
  const maxSeconds = +env.VIDEO_MAX_SECONDS || DEFAULT_MAX_SECONDS;
  const dailySeconds = (+env.VIDEO_DAILY_SECONDS || DEFAULT_DAILY_SECONDS) - Math.max(0, +deps.reserveSeconds || 0);
  const model = deps.model || MODEL;
  const useFallback = deps.fallback !== false;
  const maxServerErrors = Math.max(0, Math.floor(+deps.maxServerErrors || 0));
  const log = deps.log || (() => {});
  const sleep = deps.sleep || (ms => new Promise(r => setTimeout(r, ms)));
  const stats = { video: 0, fallback: 0, exclude: 0, reasons: {} };
  let forbiddenInARow = 0;
  let disabledReason = enabled ? '' : 'VIDEO_SUMMARY=false';

  async function fallback(v, reason, detail) {
    stats.fallback++;
    stats.reasons[reason] = (stats.reasons[reason] || 0) + 1;
    if (!useFallback) {
      log(`    ↩️  영상 요약 실패 (${reason}${detail ? `: ${detail}` : ''})`);
      return { ok: false, reason, detail: detail || '' };
    }
    log(`    ↩️  영상 입력 대신 설명란 요약 (${reason}${detail ? `: ${detail}` : ''})`);
    const summary = await deps.describe(v);
    return { summary, src: 'app', grade: null, quality: JSON.stringify({ fallback: reason }) };
  }

  // 반환: { summary, src: 'video'|'app', grade: 'keep'|'exclude'|null, quality: JSON 문자열 }
  async function summarize(v) {
    if (disabledReason) return fallback(v, disabledReason);
    if (v.privacy !== 'public') return fallback(v, `privacy:${v.privacy || 'unknown'}`);
    if (!v.durationSec) return fallback(v, 'no_duration');
    const sec = Math.min(v.durationSec, maxSeconds);
    const q = readQuota(deps.quotaFile, deps.todayKey);
    if (q.seconds + sec > dailySeconds) return fallback(v, 'daily_video_cap');

    const body = buildBody(v, { maxSeconds, model });
    const maxAttempts = Math.max(3, deps.keysCount * 2);
    let res;
    let serverErrors = 0;
    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        res = await deps.request({
          hostname: 'generativelanguage.googleapis.com',
          path: `/v1beta/models/${model}:generateContent?key=${deps.getKey()}`,
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        }, body);
      } catch (e) {
        res = { status: 0, data: String(e && e.code || e) };   // 네트워크 오류 — 5xx 처럼 백오프
      }
      if (res.status === 429 || res.status >= 500 || res.status === 0) {
        if (attempt >= maxAttempts) break;
        if (res.status >= 500 && maxServerErrors && ++serverErrors >= maxServerErrors) {
          log(`    ⏹  영상 요약 ${res.status} — 재시도 그만 (5xx ${serverErrors}/${maxServerErrors})`);
          break;
        }
        const wait = res.status === 429 ? (attempt < deps.keysCount ? 500 : 20000) : Math.min(3000 * 2 ** attempt, 20000);
        log(`    ⏳ 영상 요약 ${res.status} — ${wait / 1000}초 뒤 다음 키 (${attempt}/${maxAttempts})`);
        deps.rotateKey();
        await sleep(wait);
        continue;
      }
      break;
    }
    // 시도 자체는 분량을 쓴다(실패 요청도 한도를 쓴다는 가정 — 보수적으로)
    const used = readQuota(deps.quotaFile, deps.todayKey);
    writeQuota(deps.quotaFile, { date: used.date, seconds: used.seconds + sec, calls: used.calls + 1 });

    if (res.status === 403) {
      forbiddenInARow++;
      if (forbiddenInARow >= MAX_403_IN_A_ROW) {
        disabledReason = 'video_403_repeated';
        log(`    ⚠️  영상 입력 403 ${forbiddenInARow}회 연속 — 이번 실행은 영상 입력을 끈다`);
      }
      return fallback(v, 'video_403');
    }
    if (res.status !== 200) return fallback(v, `video_http_${res.status}`);
    forbiddenInARow = 0;

    const p = parseResponse(res.data, deps.validateSummary);
    if (!p.ok) return fallback(v, p.reason, p.detail);
    const g = computeGrade(p.signals);
    stats.video++;
    if (g.grade === 'exclude') stats.exclude++;
    log(`    🎬 영상 요약 (${Math.round(sec / 60)}분${v.durationSec > maxSeconds ? ' · 앞부분만' : ''}, 영상 토큰 ${p.videoTokens}) → ${g.grade}${g.why.length ? ` [${g.why.join(',')}]` : ''}`);
    return {
      ok: true, summary: p.summary, src: 'video', grade: g.grade,
      quality: JSON.stringify({ ...p.signals, why: g.why, model, sec, clipped: v.durationSec > maxSeconds, video_tokens: p.videoTokens }),
    };
  }

  return { summarize, stats };
}

module.exports = { MODEL, PROMPT, parseDuration, buildBody, parseResponse, computeGrade, videoTokens, summaryProblem, thinkingConfigFor,
                   readQuota, writeQuota, makeVideoSummarizer, MAX_403_IN_A_ROW };
