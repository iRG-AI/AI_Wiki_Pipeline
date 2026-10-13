// v4.6-b 기존분 재요약 — 설명란만 보고 만든 옛 요약(summary_src != 'video')을 실제 영상 요약으로 천천히 바꾼다.
// scheduler.js 가 매 실행 신규 영상 처리 뒤에 부른다(실패해도 실행 결과에 영향 없음 — 호출부가 try/catch).
//
// ★ 신규 영상이 먼저다. 재요약은
//   - 실행당 RESUMMARY_PER_RUN(기본 5)편 · 태평양시 하루 RESUMMARY_DAILY_MAX(기본 20)편
//   - 하루 영상 분량 상한(8시간)에서 RESUMMARY_RESERVE_SECONDS(기본 3시간)를 신규 몫으로 남기고 그 안에서만
//     (PT 하루 안의 실행 순서가 18→00→06→12시라 앞 실행이 다 쓰면 12시 신규가 설명란 요약으로 밀린다)
// ★ 모델은 RESUMMARY_MODEL(기본 gemini-3.5-flash-lite). 신규 요약(2.5 Flash)과 무료 한도가 모델별로 따로라
//   본 파이프라인(요약·분류·Wiki·LAN 답변)의 2.5 Flash 하루 한도를 먹지 않는다. 10-13 비교 5건: 등급·신호 5/5 일치.
// ★ 실패하면 설명란 요약으로 대체하지 않는다 — 기존 요약을 그대로 둔다(대체하면 지어낸 요약을 다시 쓰는 셈).
//   - 삭제(목록에 없음)·공개 아님·길이 모름·영상 토큰 0 → 건너뜀 표시(다시 시도 안 함)
//   - 응답 형식 실패(bad_json·bad_signals·bad_summary)·그 밖의 HTTP → 실패 1회, 2회면 건너뜀
//   - 429·5xx 소진·네트워크·하루 분량·영상 입력 꺼짐(403 연속 2회 포함) → 이번 실행 재요약 중단(다음 실행이 이어서)
// ★ 하루 횟수는 상태 파일 없이 장부 quality.resummary_day(태평양시 날짜)로 센다.
'use strict';
const library = require('./library');

const DEFAULTS = { model: 'gemini-3.5-flash-lite', perRun: 5, dailyMax: 20, reserveSeconds: 3 * 3600 };

function intEnv(env, key, def) {
  const n = parseInt(env[key], 10);
  return Number.isFinite(n) && n >= 0 ? n : def;
}
function settings(env = {}) {
  return {
    enabled: env.RESUMMARY !== 'false' && env.VIDEO_SUMMARY !== 'false',
    model: (env.RESUMMARY_MODEL || '').trim() || DEFAULTS.model,
    perRun: intEnv(env, 'RESUMMARY_PER_RUN', DEFAULTS.perRun),
    dailyMax: intEnv(env, 'RESUMMARY_DAILY_MAX', DEFAULTS.dailyMax),
    reserveSeconds: intEnv(env, 'RESUMMARY_RESERVE_SECONDS', DEFAULTS.reserveSeconds),
  };
}

// 요약 실패 사유 → 'skip'(다시 시도 안 함) | 'fail'(1회 세고 2회면 건너뜀) | 'stop'(이번 실행 중단)
const SKIP = new Set(['no_video_tokens', 'no_duration', 'gone']);
const FAIL = new Set(['bad_json', 'bad_signals', 'bad_summary', 'video_403']);
function classify(reason) {
  const r = String(reason || '');
  if (SKIP.has(r) || r.startsWith('privacy:')) return 'skip';
  if (FAIL.has(r)) return 'fail';
  const m = /^video_http_(\d+)$/.exec(r);
  if (m) {
    const code = +m[1];
    return code === 0 || code === 429 || code >= 500 ? 'stop' : 'fail';
  }
  return 'stop';   // daily_video_cap · VIDEO_SUMMARY=false · video_403_repeated · 모르는 사유
}

// deps: db(node:sqlite) · fetchDetails(videoIds) → {id: {privacy, durationSec, description, tags, realChannelTitle}}
//       makeSummarizer({model, reserveSeconds}) → {summarize, stats} (lib/video_summary.makeVideoSummarizer, fallback:false)
//       todayKey() → 태평양시 날짜 · env · log · sleep
// 반환: { enabled, done, exclude, skipped, failed, reasons, today, dailyMax, remaining, stopped, model }
async function run(deps) {
  const cfg = settings(deps.env || {});
  const log = deps.log || (() => {});
  const sleep = deps.sleep || (ms => new Promise(r => setTimeout(r, ms)));
  const res = { enabled: cfg.enabled, model: cfg.model, done: 0, exclude: 0, skipped: 0, failed: 0, reasons: {},
                today: 0, dailyMax: cfg.dailyMax, remaining: null, stopped: '' };
  if (!cfg.enabled) { res.stopped = 'disabled'; return res; }

  const db = deps.db;
  const day = deps.todayKey();
  res.today = library.resummaryDoneOn(db, day);
  const budget = Math.min(cfg.perRun, Math.max(0, cfg.dailyMax - res.today));
  if (budget <= 0) {
    res.stopped = res.today >= cfg.dailyMax ? 'daily_max' : 'per_run_0';
    res.remaining = library.resummaryRemaining(db);
    return res;
  }

  // 건너뜀으로 빠질 행을 감안해 넉넉히 뽑는다(그래도 videos.list 1회 = 1유닛)
  const cands = library.resummaryCandidates(db, Math.min(50, budget * 4));
  const details = cands.length ? await deps.fetchDetails(cands.map(c => c.video_id)) : {};
  const summarizer = deps.makeSummarizer({ model: cfg.model, reserveSeconds: cfg.reserveSeconds });
  const note = (reason) => { res.reasons[reason] = (res.reasons[reason] || 0) + 1; };

  for (const c of cands) {
    if (res.done >= budget) break;
    const d = details[c.video_id];
    if (!d) {   // 목록에 없음 = 삭제·비공개 전환
      library.markResummary(db, c.record_id, { skip: 'gone' });
      res.skipped++; note('gone');
      continue;
    }
    const v = { videoId: c.video_id, title: c.title, channelTitle: d.realChannelTitle || c.channel,
                description: d.description, tags: d.tags, privacy: d.privacy, durationSec: d.durationSec };
    log(`  🔁 재요약: ${String(c.title || '').slice(0, 50)}`);
    const r = await summarizer.summarize(v);
    if (r && r.ok) {
      const q = library.parseQuality(r.quality);
      const prev = library.parseQuality(c.quality);
      const quality = JSON.stringify({ ...q, resummary: true, resummary_day: day,
        ...(prev.resummary_fail ? { resummary_fail: prev.resummary_fail } : {}) });
      if (library.updateResummary(db, c.record_id, { summary: r.summary, grade: r.grade, quality })) {
        res.done++;
        if (r.grade === 'exclude') res.exclude++;
      }
      await sleep(2000);
      continue;
    }
    const reason = (r && r.reason) || 'unknown';
    note(reason);
    const kind = classify(reason);
    if (kind === 'skip') {
      library.markResummary(db, c.record_id, { skip: reason });
      res.skipped++;
    } else if (kind === 'fail') {
      library.markResummary(db, c.record_id, { fail: reason });
      res.failed++;
    } else {
      res.stopped = reason;
      break;
    }
  }
  res.today = library.resummaryDoneOn(db, day);
  res.remaining = library.resummaryRemaining(db);
  return res;
}

function summaryLine(r) {
  if (!r) return '';
  if (!r.enabled) return '🔁 재요약: 꺼짐 (RESUMMARY=false 또는 VIDEO_SUMMARY=false)';
  const extra = [];
  if (r.skipped) extra.push(`건너뜀 ${r.skipped}`);
  if (r.failed) extra.push(`실패 ${r.failed}`);
  const reasons = Object.keys(r.reasons).length ? ` ${JSON.stringify(r.reasons)}` : '';
  const stop = r.stopped && r.stopped !== 'daily_max' ? ` · 중단 ${r.stopped}` : '';
  return `🔁 재요약: ${r.done}편 (제외 등급 ${r.exclude})${extra.length ? ' · ' + extra.join(' · ') : ''}${reasons}` +
         ` · 오늘 ${r.today}/${r.dailyMax}${stop} · 남은 대상 ${r.remaining ?? '?'}`;
}

module.exports = { run, settings, classify, summaryLine, DEFAULTS };
