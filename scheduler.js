// ===== YouTube AI 요약기 자동 스케줄러 (v4.0: 저장 = 로컬 장부 data/library.db · v4.2: 실행 실패 알림) =====
// Mac launchd에 의해 6시간 간격으로 자동 실행됩니다.
// 직접 실행: node scheduler.js

const https = require('https');
const fs = require('fs');
const path = require('path');
const library = require('./lib/library');   // v4.0 로컬 장부 (node:sqlite)

// ══════════════════════════════════
// ★ .env 파일에서 환경변수 로드 ★
// ══════════════════════════════════
function loadEnv() {
  const envPath = path.join(__dirname, '.env');
  if (!fs.existsSync(envPath)) return;
  const lines = fs.readFileSync(envPath, 'utf8').split('\n');
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const eqIdx = trimmed.indexOf('=');
    if (eqIdx < 0) continue;
    const key = trimmed.slice(0, eqIdx).trim();
    const val = trimmed.slice(eqIdx + 1).trim();
    if (key && !process.env[key]) process.env[key] = val;
  }
}
loadEnv();

// ── Gemini 다중 API Key 로더 및 상태 관리 ──
const getGeminiKeys = () => {
  const keysStr = process.env.GEMINI_API_KEYS || '';
  if (keysStr) {
    return keysStr.split(',').map(k => k.trim()).filter(Boolean);
  }
  return [process.env.GEMINI_API_KEY || ''].filter(Boolean);
};

let currentGeminiKeyIdx = 0;

function getActiveGeminiKey() {
  const keys = CONFIG.geminiApiKeys;
  if (!keys || keys.length === 0) return '';
  return keys[currentGeminiKeyIdx % keys.length];
}

function rotateGeminiKey() {
  const keys = CONFIG.geminiApiKeys;
  if (!keys || keys.length <= 1) return false;
  const oldKeyIdx = currentGeminiKeyIdx;
  currentGeminiKeyIdx = (currentGeminiKeyIdx + 1) % keys.length;
  log(`      🔄 [API Key Rotation] API 키 교체 ➔ (Key #${oldKeyIdx + 1} ➔ Key #${currentGeminiKeyIdx + 1})`);
  return true;
}

const CONFIG = {
  youtubeApiKey:        process.env.YOUTUBE_API_KEY             || '',
  geminiApiKey:         process.env.GEMINI_API_KEY              || '', // 하위 호환성용
  geminiApiKeys:        getGeminiKeys(),                        // 다중 키 배열
  masterPlaylistId:     process.env.YOUTUBE_MASTER_PLAYLIST_ID  || '',

  // 토픽별 YouTube 재생목록 자동 추가 (2026-09-09 신설 스위치).
  // 'false' 로 두면 재생목록 추가와 pending 큐 재시도를 모두 건너뛴다.
  // ★ 요약·장부 저장·Obsidian 동기화·토픽 분류는 이 값과 무관하게 그대로 동작한다.
  //   playlists.json 은 분류기의 후보 토픽 목록이므로 비우면 안 된다(주제 분류가 죽는다).
  playlistSync:         process.env.YOUTUBE_PLAYLIST_SYNC !== 'false',

  telegram: {
    enabled:  process.env.TELEGRAM_ENABLED === 'true',
    botToken: process.env.TELEGRAM_BOT_TOKEN || '',
    chatId:   process.env.TELEGRAM_CHAT_ID   || '',
  },
  email: {
    enabled:  process.env.EMAIL_ENABLED === 'true',
    from:     process.env.EMAIL_FROM     || '',
    to:       process.env.EMAIL_TO       || '',
    appPass:  process.env.EMAIL_APP_PASS || '',
  },
};
// ══════════════════════════════════

// ══════════════════════════════════
// 텔레그램 알림 전송
// ══════════════════════════════════
// (v4.2) 보냈으면 true, 꺼져 있거나 실패하면 false 로 끝난다(reject 없음).
//   실행 상태 파일(.run_state.json)이 "실패 알림이 실제로 나갔는지" 를 이 값으로 기록한다.
function sendTelegram(message) {
  return new Promise((resolve) => {
    if (!CONFIG.telegram.enabled) return resolve(false);
    const text = encodeURIComponent(message);
    const url = `/bot${CONFIG.telegram.botToken}/sendMessage?chat_id=${CONFIG.telegram.chatId}&text=${text}&parse_mode=HTML`;
    const req = https.request(
      { hostname: 'api.telegram.org', path: url, method: 'GET' },
      (res) => {
        let data = [];
        res.on('data', c => data.push(c));
        res.on('end', () => {
          // JSON 이 아닌 응답(게이트웨이 502 HTML 등)에 JSON.parse 가 던지면 이벤트 핸들러 밖으로 새 프로세스가 죽었다(v4.2 에서 막음)
          let body = null;
          try { body = JSON.parse(Buffer.concat(data).toString('utf8')); } catch {}
          if (body && body.ok) { log('📱 텔레그램 알림 전송 완료'); return resolve(true); }
          log('⚠️  텔레그램 전송 실패: ' + (body ? body.description : `HTTP ${res.statusCode} (JSON 아닌 응답)`));
          resolve(false);
        });
      }
    );
    // 응답이 없으면 20초에 끊는다 — 알림이 실행 종료를 붙잡지 않게
    req.setTimeout(20000, () => req.destroy(new Error('timeout 20s')));
    req.on('error', (e) => { log('⚠️  텔레그램 오류: ' + e.message); resolve(false); });
    req.end();
  });
}

// ── (v3.0) 카카오톡 → 장부 tips (v4.0 부터 노션 대신 data/library.db) ──
// kakao_ingest.py --apply --if-new 실행. 새 CSV 가 없으면 Python 쪽이 즉시 종료한다.
// 실패해도 reject 하지 않는다 — 카톡 단계가 Obsidian 동기화를 막으면 안 된다.
function runKakaoIngest(python3) {
  return new Promise((resolve) => {
    const { execFile } = require('child_process');
    const script = path.join(__dirname, 'kakao_ingest.py');
    if (!fs.existsSync(script)) { log('ℹ️  kakao_ingest.py 없음 — 건너뜀'); return resolve(null); }
    execFile(python3, [script, '--apply', '--if-new'], { cwd: __dirname, timeout: 10 * 60 * 1000 },
      (err, stdout, stderr) => {
        let r = null;
        const line = String(stdout || '').split('\n').find(l => l.startsWith('RESULT_JSON:'));
        if (line) { try { r = JSON.parse(line.slice('RESULT_JSON:'.length)); } catch (e) { log(`⚠️ 카톡 결과 파싱 오류: ${e.message}`); } }
        if (err) {
          log(`⚠️ 카톡 인제스트 오류 (exit ${err.code}): ${String(stderr || '').slice(-300)}`);
        } else if (r && r.skipped) {
          log(`ℹ️  카톡 인제스트 건너뜀: ${r.skipped}${r.csv ? ` (${r.csv})` : ''}`);
        } else if (r) {
          log(`📎 카톡 인제스트: 신규 ${r.created}건 / 후보 ${r.candidates}건 · DB 총 ${r.db_total}건`);
        }
        resolve(r);
      });
  });
}

// ── (v4.0 3단계) 장부 → 구글 시트 미러 (보기 전용, 변경분만) ──
// sheet_mirror.py 실행. .env 에 SHEET_MIRROR_URL 이 없으면 Python 쪽이 skipped 로 즉시 끝난다.
// 실패해도 reject 하지 않는다 — 시트는 보기용 사본이라 Obsidian 동기화를 막으면 안 된다. 실패분은 다음 실행이 다시 보낸다.
function runSheetMirror(python3) {
  return new Promise((resolve) => {
    const { execFile } = require('child_process');
    const script = path.join(__dirname, 'sheet_mirror.py');
    if (!fs.existsSync(script)) { log('ℹ️  sheet_mirror.py 없음 — 건너뜀'); return resolve(null); }
    execFile(python3, [script], { cwd: __dirname, timeout: 10 * 60 * 1000 },
      (err, stdout, stderr) => {
        let r = null;
        const line = String(stdout || '').split('\n').find(l => l.startsWith('RESULT_JSON:'));
        if (line) { try { r = JSON.parse(line.slice('RESULT_JSON:'.length)); } catch (e) { log(`⚠️ 시트 미러 결과 파싱 오류: ${e.message}`); } }
        if (err) {
          log(`⚠️ 시트 미러 오류 (exit ${err.code}${r && r.error ? `, ${r.error}` : ''}): ${String(stderr || '').slice(-300)}`);
          if (!r) r = { error: 'exit_' + err.code, videos_sent: 0, tips_sent: 0 };
        } else if (r && r.skipped) {
          log(`ℹ️  시트 미러 건너뜀: ${r.skipped}`);
        } else if (r) {
          log(`📗 시트 미러: 영상 ${r.videos_sent}건 · 꿀팁 ${r.tips_sent}건${r.full ? ' (전체 다시 쓰기)' : ''}`);
        }
        resolve(r);
      });
  });
}

// ── (v4.1) 장부 하루 1회 백업 — 로컬 data/backups/ + 구글 드라이브 폴더(.env LIBRARY_BACKUP_DIR) ──
// backup_library.py 실행. 오늘(KST) 백업이 이미 있으면 Python 쪽이 skipped 로 즉시 끝난다 → 00시 실행이 만들고 나머지는 건너뜀.
// 실패해도 reject 하지 않는다(시트 미러 훅과 같은 원칙). 텔레그램은 main 이 보낸다 — 이 함수는 네트워크를 쓰지 않는다.
function runLibraryBackup(python3) {
  return new Promise((resolve) => {
    const { execFile } = require('child_process');
    const script = path.join(__dirname, 'backup_library.py');
    if (!fs.existsSync(script)) { log('ℹ️  backup_library.py 없음 — 건너뜀'); return resolve(null); }
    execFile(python3, [script], { cwd: __dirname, timeout: 10 * 60 * 1000 },
      (err, stdout, stderr) => {
        let r = null;
        const line = String(stdout || '').split('\n').find(l => l.startsWith('RESULT_JSON:'));
        if (line) { try { r = JSON.parse(line.slice('RESULT_JSON:'.length)); } catch (e) { log(`⚠️ 장부 백업 결과 파싱 오류: ${e.message}`); } }
        if (err) {
          log(`⚠️ 장부 백업 오류 (exit ${err.code}${r && r.error ? `, ${r.error}` : ''}): ${String(stderr || '').slice(-300)}`);
          if (!r) r = { error: 'exit_' + err.code };
          if (!r.error) r.error = 'exit_' + err.code;
        } else if (r && r.skipped) {
          log(`ℹ️  장부 백업 건너뜀: ${r.skipped} (${r.file})`);
        } else if (r) {
          const d = r.dests || {};
          log(`🗄  장부 백업: ${r.file} ${((r.bytes || 0) / 1048576).toFixed(1)}MB · 로컬 ${d.local} · 드라이브 ${d.drive}`);
        }
        resolve(r);
      });
  });
}

// ── (v4.2) 실행 상태 파일 — 통째 실패·끝나지 못한 실행·빠진 정시 실행을 알린다 ──
// 네트워크가 죽은 실행은 그 자리에서 텔레그램도 못 보낸다. 그래서 실행마다 "어떻게 끝났는지" 를 파일에 남기고,
// 다음 실행이 시작할 때 읽어 못 보낸 실패 알림·끝을 기록하지 못한 실행·간격이 너무 긴 실행을 한 번에 알린다.
// 파일: .run_state.json (gitignore). 기록 실패는 실행을 막지 않는다(로그만 남긴다).
//   { v, started_at, finished_at, outcome: 'running'|'ok'|'fail', reason, notified, pending: [못 보낸 점검 문구] }
const RUN_STATE_FILE  = path.join(__dirname, '.run_state.json');
const RUN_STALE_H     = 3;    // 'running' 으로 남은 직전 실행이 이보다 오래면 도중에 죽은 것. 짧으면 겹친 실행일 수 있어 알리지 않는다
const RUN_GAP_ALERT_H = 9;    // 정시 간격 6시간 + 지연 3시간까지 허용. 넘으면 정시 실행이 하나 이상 빠진 것
const RUN_PENDING_MAX = 10;   // 못 보낸 점검 문구 보관 상한 (텔레그램이 계속 꺼져 있어도 파일이 자라지 않게)
let runState = null;          // main 이 시작할 때 만든다. main().catch 도 쓴다

function escapeHtml(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
function fmtKst(ms) {
  return new Date(ms).toLocaleString('ko-KR', { timeZone: 'Asia/Seoul' });
}
// 오류 메시지 첫 줄만, 300자까지 (스택·긴 본문이 상태 파일과 텔레그램을 채우지 않게)
function shortReason(e) {
  return String(e && e.message !== undefined ? e.message : e).split('\n')[0].slice(0, 300);
}
function readRunState(file = RUN_STATE_FILE) {
  try {
    const st = JSON.parse(fs.readFileSync(file, 'utf8'));
    return st && typeof st === 'object' && !Array.isArray(st) ? st : null;
  } catch (e) {
    if (e.code !== 'ENOENT') log(`⚠️ 실행 상태 파일을 읽지 못함 (${e.message}) — 직전 실행 점검 없이 진행`);
    return null;
  }
}
function writeRunState(st, file = RUN_STATE_FILE) {
  try {
    const tmp = file + '.tmp';
    fs.writeFileSync(tmp, JSON.stringify(st, null, 2) + '\n', 'utf8');
    fs.renameSync(tmp, file);
    return true;
  } catch (e) {
    log(`⚠️ 실행 상태 파일 쓰기 실패: ${e.message}`);
    return false;
  }
}
// 영상을 하나도 확인하지 못한 실행 = 저장 0 · Skip 0 · 오류 ≥ 1 (10-04 06:00, 10-05 00:00 ENOTFOUND 가 이 모양이었다)
function isWholeRunFailure({ saved, skip, error }) {
  return saved === 0 && skip === 0 && error > 0;
}
// 직전 실행 기록 → 이번 실행이 알릴 문구 (순수 함수, 텔레그램 HTML)
function runNotices(prev, nowMs) {
  if (!prev || !prev.started_at) return [];
  const startedMs = Date.parse(prev.started_at);
  if (!Number.isFinite(startedMs)) return [];
  const gapH = (nowMs - startedMs) / 3600000;
  const out = [];
  if (prev.outcome === 'running') {
    if (gapH >= RUN_STALE_H) out.push(`🛑 ${fmtKst(startedMs)} 실행이 끝을 기록하지 못했습니다 — 도중에 멈췄거나 강제 종료됨 (scheduler.log 확인)`);
  } else if (prev.outcome === 'fail' && !prev.notified) {
    out.push(`🚨 ${fmtKst(startedMs)} 실행 실패 — 그때 알림을 보내지 못했습니다\n   원인: ${escapeHtml(prev.reason || '기록 없음')}`);
  }
  if (gapH >= RUN_GAP_ALERT_H) {
    out.push(`⏰ 직전 실행 ${fmtKst(startedMs)} → 이번 실행까지 ${gapH.toFixed(1)}시간 — 그 사이 정시 실행이 빠졌습니다 (맥 잠자기·전원·launchd 확인)`);
  }
  return out;
}

// ══════════════════════════════════
// 이메일 알림 전송 (Gmail SMTP over TLS)
// ══════════════════════════════════
function sendEmail(subject, body) {
  return new Promise((resolve) => {
    if (!CONFIG.email.enabled) return resolve();
    const tls = require('tls');
    const { from, to, appPass } = CONFIG.email;
    const auth = Buffer.from(`\0${from}\0${appPass}`).toString('base64');
    const boundary = 'boundary_yt_notify';
    const msg = [
      `From: YouTube 요약기 <${from}>`,
      `To: ${to}`,
      `Subject: =?UTF-8?B?${Buffer.from(subject).toString('base64')}?=`,
      'MIME-Version: 1.0',
      `Content-Type: text/plain; charset=UTF-8`,
      'Content-Transfer-Encoding: base64',
      '',
      Buffer.from(body).toString('base64'),
    ].join('\r\n');

    const socket = tls.connect(465, 'smtp.gmail.com', {}, () => {
      let step = 0;
      const cmds = [
        `EHLO localhost\r\n`,
        `AUTH PLAIN ${auth}\r\n`,
        `MAIL FROM:<${from}>\r\n`,
        `RCPT TO:<${to}>\r\n`,
        `DATA\r\n`,
        `${msg}\r\n.\r\n`,
        `QUIT\r\n`,
      ];
      socket.on('data', (d) => {
        const res = d.toString();
        if (res.startsWith('220') && step === 0) { socket.write(cmds[step++]); return; }
        if ((res.includes('250') || res.includes('235')) && step <= 5) { socket.write(cmds[step++]); return; }
        if (res.startsWith('354') && step === 5) { socket.write(cmds[step++]); return; }
        if (res.startsWith('221')) { log('📧 이메일 알림 전송 완료'); socket.destroy(); resolve(); }
      });
      socket.on('error', (e) => { log('⚠️  이메일 오류: ' + e.message); resolve(); });
    });
    socket.on('error', (e) => { log('⚠️  이메일 연결 오류: ' + e.message); resolve(); });
  });
}

// ── 로그 파일 경로 (scheduler.log 로 기록됨) ──
const LOG_FILE = path.join(__dirname, 'scheduler.log');

// ── 로그 기록 함수 (터미널 + 파일) ──
function log(msg) {
  const t = new Date().toLocaleString('ko-KR', { timeZone: 'Asia/Seoul' });
  const line = `[${t}] ${msg}`;
  console.log(line);
  fs.appendFileSync(LOG_FILE, line + '\n', 'utf8');
}

// ── playlists.json 에서 재생목록 목록 읽기 ──
function loadPlaylists() {
  const filePath = path.join(__dirname, 'playlists.json');
  if (!fs.existsSync(filePath)) {
    log('⚠️  playlists.json 파일이 없습니다. 브라우저에서 재생목록을 먼저 등록하세요.');
    return [];
  }
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
  } catch (e) {
    log(`❌ playlists.json 파싱 오류: ${e.message}`);
    return [];
  }
}

// ── HTTPS GET/POST 래퍼 ──
// Buffer 배열로 수집 후 utf8 디코딩 → 이모지 등 멀티바이트 문자 깨짐 방지
function httpsRequest(options, body) {
  return new Promise((resolve, reject) => {
    const req = https.request(options, (res) => {
      const chunks = [];
      res.on('data', chunk => chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk)));
      res.on('end', () => {
        const raw = Buffer.concat(chunks).toString('utf8');
        try { resolve({ status: res.statusCode, data: JSON.parse(raw) }); }
        catch(e) { resolve({ status: res.statusCode, data: raw }); }
      });
    });
    req.on('error', reject);
    if (body) {
      // body를 utf8 Buffer로 변환하여 전송 (이모지 포함 제목 처리)
      const bodyStr = typeof body === 'string' ? body : JSON.stringify(body);
      const bodyBuf = Buffer.from(bodyStr, 'utf8');
      req.write(bodyBuf);
    }
    req.end();
  });
}

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

// ── 재생목록 이름 가져오기 ──
async function getPlaylistTitle(listId) {
  const d = await ytFetch(`playlists?part=snippet&id=${listId}`);
  return d.items?.[0]?.snippet?.title || '';
}

// ── 재생목록 전체 동영상 가져오기 ──
async function getVideos(listId) {
  const videos = [];
  let token = '';
  do {
    const d = await ytFetch(`playlistItems?part=snippet&playlistId=${listId}&maxResults=50&pageToken=${token}`);
    for (const it of d.items) {
      const s = it.snippet;
      if (s.resourceId?.videoId) {
        videos.push({
          videoId: s.resourceId.videoId,
          title: s.title,
          channelId: s.channelId,
          channelTitle: s.channelTitle,
          publishedAt: s.publishedAt,
          thumbnail: s.thumbnails?.medium?.url || '',
        });
      }
    }
    token = d.nextPageToken || '';
  } while (token);
  return videos;
}

// ── 동영상 상세 정보 (최대 50개 배치 조회) ──
async function getBatchDetails(videoIds) {
  if (!videoIds.length) return {};
  const map = {};
  // 50개씩 나눠서 배치 조회
  for (let i = 0; i < videoIds.length; i += 50) {
    const batch = videoIds.slice(i, i + 50);
    const d = await ytFetch(`videos?part=statistics,snippet&id=${batch.join(',')}`);
    for (const it of (d.items || [])) {
      map[it.id] = {
        viewCount:       parseInt(it?.statistics?.viewCount || 0),
        description:     it?.snippet?.description || '',
        tags:            it?.snippet?.tags || [],
        realChannelTitle: it?.snippet?.channelTitle || '',
        realChannelId:   it?.snippet?.channelId || '',
        realPublishedAt: it?.snippet?.publishedAt || '',
      };
    }
  }
  return map;
}

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
// ── 요약 무결성 검증 함수 ──
function validateSummary(summary) {
  if (!summary || summary === '요약 불가') return false;
  const requiredSections = [
    '## 영상 개요',
    '## 핵심 내용',
    '## 주요 인사이트',
    '## 활용 포인트'
  ];
  // 4가지 섹션 헤더가 모두 포함되어 있는지 검증
  const hasAllHeaders = requiredSections.every(sec => summary.includes(sec));
  if (!hasAllHeaders) return false;

  // 마지막 섹션인 '## 활용 포인트' 밑에 내용이 충분히 채워졌는지 검증 (10자 이상)
  const partIndex = summary.indexOf('## 활용 포인트');
  const partContent = summary.slice(partIndex + '## 활용 포인트'.length).trim();
  if (partContent.length < 10) return false;

  return true;
}

// ── 제목 정규화 헬퍼 (중복 감지 신뢰도 향상) ──
function normalizeTitle(t) {
  if (!t) return '';
  return t
    .normalize('NFC')
    .toLowerCase()
    .replace(/[\s\p{P}\p{S}]/gu, '') // 공백, 기호, 이모지 등 모두 제거해 매칭률 극대화
    .trim();
}

// ── Gemini 요약 ──
async function geminiSummarize(v) {
  const basePrompt = `당신은 YouTube 영상 콘텐츠를 분석하는 전문 리서처입니다.
아래 영상 정보를 바탕으로 경영진이 읽는 보고서를 한국어로 작성해주세요.

[절대 규칙]
- 반드시 아래 4개 섹션을 모두 작성할 것 (하나라도 빠지면 안 됨)
- 각 섹션 제목은 반드시 ## 로 시작할 것
- 핵심 내용과 주요 인사이트는 반드시 * 로 시작하는 항목으로 작성할 것
- **굵게** 표시가 필요한 핵심 키워드는 **텍스트** 형식으로 표시
- 영상 정보가 부족해도 제목과 채널명을 바탕으로 반드시 추론하여 작성할 것
- 절대로 중간에 끊지 말고 4개 섹션을 모두 완성할 것

[작성 형식]
## 영상 개요
(이 영상이 다루는 주제와 목적을 정확히 3문장으로 서술. 영상의 핵심 주제, 대상 시청자, 주요 목적을 포함)

## 핵심 내용
* **[핵심 키워드1]**: (구체적인 설명 1~2문장)
* **[핵심 키워드2]**: (구체적인 설명 1~2문장)
* **[핵심 키워드3]**: (구체적인 설명 1~2문장)
* **[핵심 키워드4]**: (구체적인 설명 1~2문장)
(반드시 4개 이상 항목 작성)

## 주요 인사이트
* **[인사이트1]**: (비즈니스/실무 관점의 핵심 시사점 1~2문장)
* **[인사이트2]**: (비즈니스/실무 관점의 핵심 시사점 1~2문장)
* **[인사이트3]**: (비즈니스/실무 관점의 핵심 시사점 1~2문장)
(반드시 3개 항목 작성)

## 활용 포인트
(이 영상의 내용을 실무나 의사결정에 어떻게 활용할 수 있는지 구체적으로 2~3문장 작성)

[영상 정보]
제목: ${v.title}
채널: ${v.channelTitle}
설명: ${v.description || '(없음)'}
태그: ${v.tags?.join(', ') || '(없음)'}

보고서:`;

  const fallbackPrompt = `당신은 YouTube 영상 콘텐츠를 분석하는 전문 리서처입니다.
[🚨 중요: 이번에는 텍스트가 절대 짤리지 않도록 각 섹션을 중언부언하지 말고 매우 간결하고 밀도 높은 한국어 문장(핵심당 1문장 내외)으로 짧게 완성해 주세요.]

[절대 규칙]
- 반드시 아래 4개 섹션을 모두 작성할 것 (하나라도 빠지면 안 됨)
- 각 섹션 제목은 반드시 ## 로 시작할 것
- 핵심 내용과 주요 인사이트는 반드시 * 로 시작하는 항목으로 작성할 것
- 절대로 중간에 끊지 말고 4개 섹션을 모두 완벽히 완성할 것

[작성 형식]
## 영상 개요
(이 영상이 다루는 주제와 목적을 핵심 위주로 정확히 2문장으로 요약)

## 핵심 내용
* **[핵심 키워드1]**: (구체적인 설명 1문장)
* **[핵심 키워드2]**: (구체적인 설명 1문장)
* **[핵심 키워드3]**: (구체적인 설명 1문장)
(반드시 3개 이상 항목 작성)

## 주요 인사이트
* **[인사이트1]**: (비즈니스/실무 관점의 핵심 시사점 1문장)
* **[인사이트2]**: (비즈니스/실무 관점의 핵심 시사점 1문장)
(반드시 2개 이상 항목 작성)

## 활용 포인트
(이 영상의 내용을 실무나 의사결정에 어떻게 활용할 수 있는지 구체적으로 1~2문장 작성)

[영상 정보]
제목: ${v.title}
채널: ${v.channelTitle}
설명: ${v.description || '(없음)'}
태그: ${v.tags?.join(', ') || '(없음)'}

보고서:`;

  let finalSummary = '요약 불가';
  let qualityAttempt = 0;
  const maxQualityAttempts = 3;

  while (qualityAttempt < maxQualityAttempts) {
    const isFallback = qualityAttempt > 0;
    const prompt = isFallback ? fallbackPrompt : basePrompt;
    
    if (isFallback) {
      log(`    ⚠️ [요약 무결성 검증 실패] 주요 섹션 유실 감지 ➔ 간결한 Fallback 프롬프트로 재시도 (${qualityAttempt}/${maxQualityAttempts - 1})`);
    }

    let res;
    const keysCount = CONFIG.geminiApiKeys.length;
    const maxAttempts = Math.max(3, keysCount * 2);
    let attempt = 0;

    while (attempt < maxAttempts) {
      const currentKey = getActiveGeminiKey();
      const maskedKey = currentKey ? `${currentKey.slice(0, 8)}...${currentKey.slice(-6)}` : '없음';

      res = await httpsRequest({
        hostname: 'generativelanguage.googleapis.com',
        path: `/v1beta/models/gemini-2.5-flash:generateContent?key=${currentKey}`,
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      }, {
        contents: [{ parts: [{ text: prompt }] }],
        generationConfig: { 
          temperature: 0.3, 
          maxOutputTokens: 4000, // 한글 출력 짤림 방지를 위해 2000 ➔ 4000 상향
          thinkingConfig: { thinkingBudget: 0 }
        },
      });

      if (res.status === 429) {
        attempt++;
        if (keysCount > 1 && attempt < keysCount) {
          log(`    ⏳ [Rate Limit] 429 에러 발생 (Key: ${maskedKey}). 대기 없이 다음 API Key로 즉시 교체 시도... (시도: ${attempt}/${maxAttempts})`);
          rotateGeminiKey();
          await new Promise(r => setTimeout(r, 500));
          continue;
        } else {
          log(`    ⏳ [Rate Limit] 429 에러 지속 발생 (Key: ${maskedKey}). 20초 대기 후 순환 재시도... (시도: ${attempt}/${maxAttempts})`);
          rotateGeminiKey();
          await new Promise(r => setTimeout(r, 20000));
          continue;
        }
      }

      if (res.status === 403) {
        const errorMsg = typeof res.data === 'object' ? JSON.stringify(res.data) : String(res.data);
        log(`\n🚨🚨🚨 [치명적 권한 에러] Gemini API 403 Forbidden 감지! (Key: ${maskedKey})`);
        log(`상세 내용: ${errorMsg}`);
        
        if (errorMsg.includes('suspended') || errorMsg.includes('CONSUMER_SUSPENDED')) {
          log(`⚠️  경고: 구글에 의해 해당 API Key 또는 프로젝트가 정지(Suspended)되었습니다.`);
          log(`계정 보호 및 추가 연쇄 정지 방지를 위해 즉시 작업을 전면 중단하고 프로세스를 종료합니다.`);
          await sendTelegram(`🚨 <b>[치명적 보안 경고]</b>\nGemini API 키 정지(Suspended) 감지!\n추가 차단 방지를 위해 요약 작업을 긴급 중단하고 프로세스를 강제 종료했습니다.\n계정 및 API 상태를 즉시 확인하세요.`);
          process.exit(1);
        } else {
          log(`⚠️  권한 부족 오류입니다. 추가 에러 방지를 위해 작업을 중단합니다.`);
          await sendTelegram(`🚨 <b>[작업 중단 알림]</b>\nGemini API 403 Forbidden 권한 에러 감지.\n작업을 긴급 중단했습니다.`);
          process.exit(1);
        }
      }

      if (res.status === 400 || res.status === 401) {
        log(`🚨 [치명적 설정 에러] Gemini API ${res.status} 감지! (Key: ${maskedKey})`);
        log(`잘못된 요청이거나 잘못된 API 키 설정입니다. 추가적인 무의미한 API 호출 방지를 위해 프로세스를 종료합니다.`);
        await sendTelegram(`🚨 <b>[설정 오류 알림]</b>\nGemini API ${res.status} 오류 감지.\n프로세스를 중단했습니다.`);
        process.exit(1);
      }
      
      if (res.status !== 200) {
        attempt++;
        const waitTime = Math.min(20000, 3000 * Math.pow(2, attempt)); // 지수 백오프 적용
        log(`    ⚠️  Gemini API 에러 ${res.status} (Key: ${maskedKey}). ${waitTime / 1000}초 대기 후 다음 키로 교체 시도... (시도: ${attempt}/${maxAttempts})`);
        rotateGeminiKey();
        await new Promise(r => setTimeout(r, waitTime));
        continue;
      }
      break;
    }
    
    if (res.status !== 200) throw new Error(`Gemini 재시도 초과 오류 ${res.status}: ${JSON.stringify(res.data)}`);
    
    const candidateText = res.data.candidates?.[0]?.content?.parts?.[0]?.text?.trim() || '요약 불가';
    
    if (validateSummary(candidateText)) {
      finalSummary = candidateText;
      log(`    ✓ 요약 무결성 검증 통과!`);
      break;
    } else {
      finalSummary = candidateText;
      qualityAttempt++;
    }
  }

  return finalSummary;
}

// ══════════════════════════════════
// ── v4.0 로컬 장부 (data/library.db) ──
// ══════════════════════════════════
// 노션 대신 맥 로컬 SQLite 1파일이 원본이다. 스키마는 lib/library_schema.sql, 접근 함수는 lib/library.js.
let libDb = null;   // main 에서 연다. 못 열면 null 그대로 두고 영상 처리를 건너뛴다(fail-closed)

// ── 장부 전체 캐시 (재생목록 처리 전 1회) ──
// ★ "전부 읽었거나, 던지거나" 둘 중 하나다. 빈 캐시는 전 영상을 신규로 보이게 해 중복 저장을 만든다(2026-10-05 사고).
//   0건이면 던진다. 새로 만든 빈 장부가 맞을 때만 .env 에 LIBRARY_ALLOW_EMPTY=true.
function loadLibraryCache(db) {
  log('  📦 장부 캐시 로딩 중...');
  const rows = library.allVideos(db);
  if (rows.length === 0 && process.env.LIBRARY_ALLOW_EMPTY !== 'true') {
    throw new Error('장부(videos)가 0건 — 새로 만든 빈 장부가 맞다면 .env 에 LIBRARY_ALLOW_EMPTY=true 를 넣고 다시 실행');
  }
  const cache = new Map();
  for (const r of rows) {
    const title = r.title || '';
    const videoId = r.video_id || '';
    if (!videoId && !title) continue;
    const entry = {
      pageId:           r.record_id,          // 이름은 노션 시절 그대로 둔다 (= 장부 record_id)
      title,
      topics:           r.topics,
      savedViewCount:   r.view_count ?? null,
      savedSubscribers: r.subscriber_count ?? null,
      savedDate:        r.upload_date ?? null,
    };
    if (videoId) cache.set(videoId, entry);
    if (title) cache.set(title, entry);
    // 정규화된 제목 보조 키 등록 (공백/이모지 방지)
    const normTitle = normalizeTitle(title);
    if (normTitle) cache.set(normTitle, entry);
  }
  log(`  ✓ 장부 캐시 완료: ${rows.length}개 영상`);
  return cache;
}

// ── 중복 체크 (videoId 우선, 없으면 정규화된 title로 fallback) ──
function findDuplicate(video, cache) {
  if (video.videoId && cache.has(video.videoId)) return cache.get(video.videoId);
  if (video.title) {
    if (cache.has(video.title)) return cache.get(video.title);
    const normTitle = normalizeTitle(video.title);
    if (cache.has(normTitle)) return cache.get(normTitle);
  }
  return null;
}

// ── 기존 영상에 주제(재생목록) 추가 ── 장부의 현재 topics 를 다시 읽어 합집합으로 쓴다. NFC 는 lib/library.js 가 맞춘다.
function addTopicToRecord(recordId, newTopic) {
  try { return library.addTopic(libDb, recordId, newTopic); }
  catch (e) { log(`    ⚠️ 주제 추가 실패: ${e.message}`); return false; }
}

// ── 중복 영상 조회수·구독자수(·업로드일) 업데이트 ──
function updateStatsInLibrary(recordId, viewCount, subscriberCount, uploadDate) {
  try { return library.updateStats(libDb, recordId, viewCount, subscriberCount, uploadDate); }
  catch (e) { log(`    ⚠️ 통계 갱신 실패: ${e.message}`); return false; }
}

// ── 신규 영상 저장 → record_id ── 같은 video_id 가 이미 있으면 던진다(덮어쓰지 않는다). 호출자가 오류 1건으로 센다.
function saveToLibrary(v, summary, topics) {
  return library.insertVideo(libDb, {
    videoId:         v.videoId,
    title:           v.title,
    channelTitle:    v.channelTitle,
    topics:          topics || [],
    uploadDate:      v.publishedAt?.split('T')[0] || null,
    viewCount:       v.viewCount || 0,
    subscriberCount: v.subscriberCount || 0,
    thumbnail:       v.thumbnail || `https://img.youtube.com/vi/${v.videoId}/hqdefault.jpg`,
    summary,
  });
}

// ── pending_playlist_adds.json 큐 소진 ──
// 매 실행 시 quota 여유분 내에서 미처리 YouTube 재생목록 추가를 처리합니다.
async function flushPendingQueue() {
  if (!CONFIG.playlistSync) {
    log('⏭  재생목록 동기화 꺼짐(YOUTUBE_PLAYLIST_SYNC=false) — pending 큐 재시도 건너뜀');
    return;
  }
  const PENDING_PATH = path.join(__dirname, 'pending_playlist_adds.json');
  let queue = [];
  try { queue = JSON.parse(fs.readFileSync(PENDING_PATH, 'utf-8')); } catch { return; }
  if (!queue.length) return;

  let yt;
  try { yt = require('./lib/youtube_oauth'); } catch (e) {
    log(`⚠️  flushPendingQueue: youtube_oauth 로드 실패 — ${e.message}`); return;
  }

  log(`⏳ pending 큐 처리 시작 — ${queue.length}건`);
  const remaining = [];
  const deadLetters = [];
  let done = 0;
  let consecutiveFail = 0;   // 연속 실패 차단기 (CLAUDE.md 보안 원칙 1 — 403 연쇄 요청 금지)

  for (let i = 0; i < queue.length; i++) {
    const item = queue[i];
    if (!yt.checkQuotaAvailable(50)) {
      log(`  ⏸  quota 한도 — ${queue.length - i}건 다음 실행으로 연기`);
      remaining.push(...queue.slice(i));
      break;
    }
    try {
      await yt.addToPlaylist(item.playlistId, item.videoId);
      done++;
      consecutiveFail = 0;
    } catch (e) {
      if (e.code === 'QUOTA_EXHAUSTED') {
        log(`  ⏸  quota 소진 — ${queue.length - i}건 연기`);
        remaining.push(...queue.slice(i));
        break;
      }
      // OAuth 토큰 만료 → 전체 중단, 큐 보존
      if (e.message?.includes('invalid_grant') || e.message?.includes('Token refresh failed')) {
        log(`  ❌ OAuth 오류 — 큐 처리 중단 (node oauth_setup.js 로 토큰 재발급 필요): ${e.message.slice(0, 80)}`);
        remaining.push(...queue.slice(i));
        break;
      }
      // 연속 실패가 이어지면 계정/권한 문제다. 403을 수백 번 난사하면
      // 실제 quota만 태우고 구글 어뷰징 탐지 대상이 되므로 즉시 중단한다.
      if (++consecutiveFail >= 10) {
        log(`  🛑 연속 실패 ${consecutiveFail}회 — 큐 처리 중단 (OAuth 계정/재생목록 권한 확인 필요): ${e.message.slice(0, 80)}`);
        remaining.push(...queue.slice(i));
        break;
      }
      // 영구 실패는 재시도해도 성공하지 않는다 → dead-letter로 격리
      const PERMANENT = ['playlistItemsNotAccessible', 'playlistNotFound', 'videoNotFound', 'forbidden'];
      const isPermanent = PERMANENT.some(k => (e.message || '').includes(k));

      if (isPermanent) {
        deadLetters.push({ ...item, deadReason: e.message.slice(0, 200), deadAt: new Date().toISOString() });
        log(`  ⛔ 영구 실패 격리 [${item.videoId}] ${item.topic || ''}: ${e.message.slice(0, 60)}`);
      } else {
        item.retryCount = (item.retryCount || 0) + 1;
        if (item.retryCount >= 5) {
          deadLetters.push({ ...item, deadReason: `재시도 5회 초과: ${e.message.slice(0, 150)}`, deadAt: new Date().toISOString() });
          log(`  ⛔ 재시도 한도 초과 격리 [${item.videoId}]`);
        } else {
          log(`  ⚠️  실패(${item.retryCount}/5) [${item.videoId}]: ${e.message.slice(0, 60)}`);
          remaining.push(item);
        }
      }
    }
  }

  if (deadLetters.length) {
    const DEAD_PATH = path.join(__dirname, 'pending_playlist_adds.dead.json');
    let dead = [];
    try { dead = JSON.parse(fs.readFileSync(DEAD_PATH, 'utf-8')); } catch {}
    fs.writeFileSync(DEAD_PATH, JSON.stringify([...dead, ...deadLetters], null, 2));
    log(`  ⛔ dead-letter ${deadLetters.length}건 격리 (누적 ${dead.length + deadLetters.length}건)`);
  }

  fs.writeFileSync(PENDING_PATH, JSON.stringify(remaining, null, 2));
  log(`  ✓ pending 처리: ${done}건 추가 완료, ${remaining.length}건 잔여`);
}

// ── AI 영상목록 → 자동 분류 + 장부 저장 + 토픽 재생목록 추가 ──
async function processMasterIngest(libCache) {
  const masterId = CONFIG.masterPlaylistId;
  if (!masterId) {
    log('⚠️  YOUTUBE_MASTER_PLAYLIST_ID 미설정 — 마스터 인제스트 건너뜀');
    return { saved: 0, skip: 0, error: 0 };
  }

  // lib 모듈 lazy-load (선택적 기능, 없어도 레거시 동작)
  let yt, classifier;
  try {
    yt = require('./lib/youtube_oauth');
    classifier = require('./lib/classifier');
  } catch (e) {
    log('⚠️  lib/youtube_oauth 또는 lib/classifier 로드 실패 — 마스터 인제스트 건너뜀: ' + e.message);
    return { saved: 0, skip: 0, error: 0 };
  }

  // playlists.json에서 토픽 → playlistId 매핑 구성
  const playlists = loadPlaylists();
  const topicToPlaylistId = {};
  for (const pl of playlists) {
    const m = pl.url.match(/[?&]list=([a-zA-Z0-9_-]+)/);
    if (m && pl.name) topicToPlaylistId[(pl.name || '').normalize('NFC')] = m[1];
  }
  const availableTopics = Object.keys(topicToPlaylistId);

  log(`\n▶ [AI 영상목록] 마스터 인제스트 시작...`);
  log(`  📚 분류 가능 토픽: ${availableTopics.length}개`);

  const videos = await getVideos(masterId);
  log(`  총 ${fmtNum(videos.length)}개 동영상`);
  if (!videos.length) return { saved: 0, skip: 0, error: 0 };

  log(`  🔄 YouTube 상세 정보 조회 중...`);
  const detailMap = await getBatchDetails(videos.map(v => v.videoId));

  const uniqueChannels = [...new Set(videos.map(v => detailMap[v.videoId]?.realChannelId || v.channelId).filter(Boolean))];
  const chCache = await getBatchSubs(uniqueChannels);

  let saved = 0, skip = 0, error = 0;
  const savedList  = [];   // [{title, topics, confidence}] — 저장된 영상 목록
  const topicStats = {};   // {topicName: count} — 주제별 저장 건수
  const skipList   = [];   // 스킵된 영상 제목 (최대 5개, 디버그용)
  const newVideos  = [];

  // ── 1단계: 중복 체크 ──
  for (const v of videos) {
    const det = detailMap[v.videoId];
    if (det) {
      v.viewCount = det.viewCount; v.description = det.description; v.tags = det.tags;
      if (det.realChannelTitle) v.channelTitle = det.realChannelTitle;
      if (det.realChannelId)    v.channelId    = det.realChannelId;
      if (det.realPublishedAt)  v.publishedAt  = det.realPublishedAt;
    }
    v.subscriberCount = chCache[v.channelId] || 0;

    const dup = findDuplicate(v, libCache);
    if (dup) {
      if (skipList.length < 5) skipList.push(v.title || '(제목 없음)');
      skip++;
      log(`  ⏭ Skip (이미 저장됨): ${v.title?.slice(0, 50)}`);
      // 결과 테이블용 구조화 데이터 (server.js → index.html 전달)
      console.log('RESULT_ROW:' + JSON.stringify({
        videoId: v.videoId, title: v.title, channelTitle: v.channelTitle,
        publishedAt: v.publishedAt, viewCount: v.viewCount, subscriberCount: v.subscriberCount,
        summary: null, topics: [], status: 'skip',
      }));
    } else {
      newVideos.push(v);
    }
  }

  if (!newVideos.length) {
    log('  ✓ 신규 영상 없음');
    return { saved, skip, error, savedList, topicStats, skipList, totalInPlaylist: videos.length };
  }

  // ── 2단계: 신규 영상 — 요약 + 분류 + 저장 + YouTube 추가 ──
  const MAX_NEW_PER_RUN = 15;
  const processList = newVideos.slice(0, MAX_NEW_PER_RUN);
  if (newVideos.length > MAX_NEW_PER_RUN) {
    log(`\n  ⚠️ 신규 영상이 너무 많습니다 (${newVideos.length}개). 할당량 보호를 위해 상위 ${MAX_NEW_PER_RUN}개만 먼저 처리합니다.`);
  }

  log(`\n  ⚡ 신규 ${processList.length}개 처리 시작...`);
  const PARALLEL = 1;

  for (let i = 0; i < processList.length; i += PARALLEL) {
    const batch = processList.slice(i, i + PARALLEL);
    log(`  ⚡ [${i+1}~${Math.min(i+PARALLEL, processList.length)}/${processList.length}] 병렬 요약 중...`);

    const summaryResults = await Promise.allSettled(batch.map(v => geminiSummarize(v)));
    
    // API 호출 간격 확보 (2초 대기)
    await new Promise(r => setTimeout(r, 2000));

    for (let j = 0; j < batch.length; j++) {
      const v = batch[j];
      const sRes = summaryResults[j];
      try {
        if (sRes.status === 'rejected') throw new Error(sRes.reason?.message || '요약 실패');
        const summary = sRes.value;

        // 분류 (현재 활성화된 로테이션된 API Key 주입)
        let cls;
        const keysCount = CONFIG.geminiApiKeys.length;
        const maxClsAttempts = Math.max(3, keysCount * 2);
        let clsAttempt = 0;

        while (clsAttempt < maxClsAttempts) {
          try {
            cls = await classifier.classifyTopics(
              { summary, title: v.title, channel: v.channelTitle },
              availableTopics,
              { geminiApiKey: getActiveGeminiKey(), maxRetries: 0 }
            );
            break;
          } catch (clsErr) {
            clsAttempt++;
            const msg = clsErr.message || '';
            const currentKey = getActiveGeminiKey();
            const maskedKey = currentKey ? `${currentKey.slice(0, 8)}...${currentKey.slice(-6)}` : '없음';

            // 인증·권한 오류는 재시도하지 않는다 (CLAUDE.md 보안 원칙 1).
            // 실패를 루프로 난사하면 구글이 어뷰징으로 판단한다.
            if (/\b(401|403)\b/.test(msg)) throw clsErr;

            // 429/quota — 키를 바꾸면 대개 즉시 통과하므로 짧게 대기
            const isRateLimit = msg.includes('429') || /quota/i.test(msg);
            // 5xx·UNAVAILABLE — 모델 과부하 등 일시적 서버 오류.
            // 요약 경로는 이미 이걸 재시도하는데 분류만 빠져 있었다.
            const isTransient = /\b(500|502|503|504)\b/.test(msg)
              || /UNAVAILABLE|overloaded|high demand/i.test(msg);

            if ((isRateLimit || isTransient) && clsAttempt < maxClsAttempts) {
              // 일시 오류는 지수 백오프 (보안 원칙 2). 상한 15초.
              const waitMs = isRateLimit ? 1000 : Math.min(2000 * 2 ** (clsAttempt - 1), 15000);
              log(`    ⏳ [분류 ${isRateLimit ? 'Rate Limit' : '일시 오류'}] ${msg.slice(0, 60)} (Key: ${maskedKey}). ${waitMs / 1000}초 대기 후 재시도... (시도: ${clsAttempt}/${maxClsAttempts})`);
              if (keysCount > 1) rotateGeminiKey();
              await new Promise(r => setTimeout(r, waitMs));
              continue;
            }
            throw clsErr;
          }
        }
        // 재시도를 모두 소진하면 cls 가 undefined 인 채로 루프를 빠져나온다.
        // 아래 cls.topics 에서 TypeError 로 죽는 것을 막는다.
        if (!cls) throw new Error(`classifyTopics: 재시도 ${maxClsAttempts}회 소진`);
        const topics = cls.topics;  // 분류된 토픽들
        const allTopics = [...topics];  // 분류 토픽만 (AI 영상목록은 재생목록이지 주제 태그 아님)

        const confStr = `conf=${cls.confidence.toFixed(2)}`;
        log(`    🏷  분류: [${topics.join(', ')}] (${confStr})`);
        if (cls.droppedTopics?.length) {
          log(`    ⚠️  droppedTopics (allowedSet 불일치): [${cls.droppedTopics.join(', ')}]`);
        }
        if (cls.confidence < 0.6) {
          log(`    ⚠️  신뢰도 낮음 — 주제 저장은 하되 수동 검토 권장`);
        }

        // 장부 저장
        const pageId = saveToLibrary(v, summary, allTopics);
        log(`    ✓ 장부 저장 완료 (주제: ${allTopics.join(', ') || '(분류 없음)'})`);
        // 결과 테이블용 구조화 데이터 (server.js → index.html 전달)
        console.log('RESULT_ROW:' + JSON.stringify({
          videoId: v.videoId, title: v.title, channelTitle: v.channelTitle,
          publishedAt: v.publishedAt, viewCount: v.viewCount, subscriberCount: v.subscriberCount,
          summary: summary?.slice(0, 200) || '', topics: allTopics, status: 'ok',
        }));

        // 캐시 갱신
        libCache.set(v.videoId || v.title, {
          pageId, title: v.title, topics: allTopics,
          savedViewCount: v.viewCount, savedSubscribers: v.subscriberCount,
          savedDate: v.publishedAt?.split('T')[0] || null,
        });

        // 저장 통계 수집
        savedList.push({ title: v.title, topics: allTopics, confidence: cls.confidence });
        for (const t of topics) {
          topicStats[t] = (topicStats[t] || 0) + 1;
        }

        // YouTube 토픽 재생목록에 추가 (신뢰도 0.6+, playlistSync 켜진 경우만)
        if (CONFIG.playlistSync && cls.confidence >= 0.6 && topics.length > 0) {
          // pending 큐 헬퍼 (legacy_scripts/migrate_classify.js 와 같은 파일 형식 — 그 스크립트는 v4.0 에서 은퇴)
          const PENDING_PATH = path.join(__dirname, 'pending_playlist_adds.json');
          const appendPending = (entry) => {
            let q = [];
            try { q = JSON.parse(fs.readFileSync(PENDING_PATH, 'utf-8')); } catch {}
            // 이미 대기 중인 (videoId, playlistId) 조합이면 적재하지 않음
            if (q.some(x => x.videoId === entry.videoId && x.playlistId === entry.playlistId)) return;
            q.push({ ...entry, ts: new Date().toISOString() });
            fs.writeFileSync(PENDING_PATH, JSON.stringify(q, null, 2));
          };

          for (const topic of topics) {
            const pid = topicToPlaylistId[topic];
            if (!pid) continue;
            try {
              if (!yt.checkQuotaAvailable(50)) {
                log(`    ⏸  YouTube quota 한도 — [${topic}] 보류 (pending 큐 적재)`);
                appendPending({ playlistId: pid, topic, videoId: v.videoId, title: v.title });
                continue;
              }
              await yt.addToPlaylist(pid, v.videoId);
              log(`    ✓ YouTube [${topic}] 재생목록 추가`);
            } catch (ytErr) {
              log(`    ⚠️  YouTube [${topic}] 추가 실패: ${ytErr.message?.slice(0, 80)}`);
              appendPending({ playlistId: pid, topic, videoId: v.videoId, title: v.title, reason: ytErr.message });
            }
          }
        }

        saved++;
      } catch (e) {
        log(`    ❌ 오류 (${v.title?.slice(0, 30)}): ${e.message}`);
        error++;
        // 결과 테이블용 구조화 데이터 (오류)
        console.log('RESULT_ROW:' + JSON.stringify({
          videoId: v.videoId, title: v.title, channelTitle: v.channelTitle,
          publishedAt: v.publishedAt, viewCount: v.viewCount, subscriberCount: v.subscriberCount,
          summary: `오류: ${e.message}`, topics: [], status: 'error',
        }));
      }
    }
    if (i + PARALLEL < newVideos.length) await new Promise(r => setTimeout(r, 300));
  }

  return { saved, skip, error, savedList, topicStats, skipList, totalInPlaylist: videos.length };
}

// ── 재생목록 하나 처리 ──
async function processPlaylist(pl, libCache) {
  const m = pl.url.match(/[?&]list=([a-zA-Z0-9_-]+)/);
  if (!m) { log(`⚠️  URL 형식 오류: ${pl.url}`); return { saved: 0, skip: 0, error: 0 }; }
  const listId = m[1];

  log(`\n▶ [${pl.name}] 재생목록 조회 중...`);
  // YouTube API 제목 대신 playlists.json의 name 사용 (이모지 깨짐 방지)
  const playlistTitle = (pl.name || '').normalize('NFC');
  log(`  재생목록명: "${playlistTitle}"`);

  const videos = await getVideos(listId);
  log(`  총 ${fmtNum(videos.length)}개 동영상`);

  // ── ① YouTube 상세 정보 배치 조회 (50개씩, API 호출 대폭 감소) ──
  log(`  🔄 YouTube 상세 정보 배치 조회 중...`);
  const detailMap = await getBatchDetails(videos.map(v => v.videoId));

  // ── 채널 구독자수 배치 조회 (50개씩 순차) ──
  const uniqueChannels = [...new Set(
    videos.map(v => detailMap[v.videoId]?.realChannelId || v.channelId).filter(Boolean)
  )];
  log(`  🔄 채널 구독자수 조회 중... (${uniqueChannels.length}개 채널)`);
  const chCache = await getBatchSubs(uniqueChannels);

  let saved = 0, skip = 0, error = 0;

  // ── 1단계: 모든 영상 순회 → Skip/업데이트 처리 + 신규 영상 수집 ──
  const newVideos = [];
  for (let i = 0; i < videos.length; i++) {
    const v = videos[i];
    const det = detailMap[v.videoId];
    if (det) {
      v.viewCount = det.viewCount; v.description = det.description; v.tags = det.tags;
      if (det.realChannelTitle) v.channelTitle = det.realChannelTitle;
      if (det.realChannelId)    v.channelId    = det.realChannelId;
      if (det.realPublishedAt)  v.publishedAt  = det.realPublishedAt;
    }
    v.subscriberCount = chCache[v.channelId] || 0;

    log(`  [${i+1}/${videos.length}] ${v.title}`);
    const dup = findDuplicate(v, libCache);
    if (dup) {
      // 이미 같은 주제가 있으면 장부를 건드리지 않는다
      const needTopicAdd = !dup.topics.includes(playlistTitle);
      const topicAdded = needTopicAdd
        ? addTopicToRecord(dup.pageId, playlistTitle)
        : false;
      if (topicAdded) dup.topics.push(playlistTitle);
      const newViewCount = v.viewCount || 0;
      const newSubscribers = v.subscriberCount || 0;  // 숫자로 통일
      const newDate = v.publishedAt?.split('T')[0] || null;
      // 조회수: savedView가 null/0이면 최초 채움, 그 외 15% 이상 변화 시만 업데이트
      const savedView = dup.savedViewCount ?? null;
      const viewChanged = newViewCount > 0 && (
        savedView === null || savedView === 0
          ? true
          : Math.abs(newViewCount - savedView) / savedView >= 0.15
      );
      // 구독자수: 동일 로직
      const savedSubs = dup.savedSubscribers ?? null;
      const subsChanged = newSubscribers > 0 && (
        savedSubs === null || savedSubs === 0
          ? true
          : Math.abs(newSubscribers - savedSubs) / savedSubs >= 0.15
      );
      const dateChanged = newDate && dup.savedDate && dup.savedDate !== newDate;
      if (viewChanged || subsChanged || dateChanged) {
        updateStatsInLibrary(dup.pageId, newViewCount, newSubscribers, dateChanged ? newDate : null);
        dup.savedViewCount = newViewCount;
        dup.savedSubscribers = newSubscribers;
        if (dateChanged) dup.savedDate = newDate;
        const ch = [];
        if (viewChanged) ch.push('조회수 ' + (savedView||0).toLocaleString() + '->' + newViewCount.toLocaleString());
        if (subsChanged) ch.push('구독자 ' + savedSubs.toLocaleString() + '->' + newSubscribers.toLocaleString());
        if (dateChanged) ch.push('업로드일 ->' + newDate);
        log('    🔄 통계 업데이트: ' + ch.join(' / '));
      } else if (topicAdded) {
        log('    ⏭ 중복 — 주제 "' + playlistTitle + '" 추가 후 Skip');
      } else {
        log('    ⏭ Skip (변경사항 없음)');
      }
      skip++;
    } else {
      log('    → 신규 영상');
      newVideos.push(v);
    }
  }

  // ── 2단계: 신규 영상 순차 Gemini 요약 → 장부 저장 ──
  const PARALLEL = 1; // 순차 처리로 변경
  if (newVideos.length > 0) {
    log('\n  ⚡ 신규 ' + newVideos.length + '개 Gemini 병렬 요약 시작 (3개씩 동시)...');
  }
  for (let i = 0; i < newVideos.length; i += PARALLEL) {
    const batch = newVideos.slice(i, i + PARALLEL);
    log('  ⚡ [' + (i+1) + '~' + Math.min(i+PARALLEL, newVideos.length) + '/' + newVideos.length + '] 병렬 요약 중...');
    const results = await Promise.allSettled(batch.map(v => geminiSummarize(v)));
    
    // API 호출 간격 확보 (2초 대기)
    await new Promise(r => setTimeout(r, 2000));
    for (let j = 0; j < batch.length; j++) {
      const v = batch[j];
      const res = results[j];
      try {
        if (res.status === 'rejected') throw new Error(res.reason?.message || '요약 실패');
        const summary = res.value;
        log('    ✓ 요약 완료 (' + summary.length + '자): ' + v.title.slice(0,30));
        const recordId = saveToLibrary(v, summary, [playlistTitle]);
        const cacheKey = v.videoId || v.title;
        libCache.set(cacheKey, {
          pageId: recordId, title: v.title, topics: [playlistTitle],
          savedViewCount: v.viewCount, savedSubscribers: v.subscriberCount,
          savedDate: v.publishedAt?.split('T')[0] || null,
        });
        log('    ✓ 장부 저장 완료');
        saved++;
      } catch(e) {
        log('    ❌ 오류: ' + e.message);
        error++;
      }
    }
    if (i + PARALLEL < newVideos.length) await new Promise(r => setTimeout(r, 300));
  }
  return { saved, skip, error };
}

// ══════════════════════════════════
// ── 메인 실행 ──
// ══════════════════════════════════
// ── 유동적 구분선 생성 (내용 길이 기준) ──
// ═ 는 터미널에서 2칸 폭 전각문자, 타임스탬프는 약 14칸
// 가장 긴 내용 줄 길이에 맞춰 구분선 자동 계산
function makeLine(...texts) {
  // 각 텍스트의 시각적 너비 계산 (한글/CJK=2칸, 나머지=1칸)
  const visualLen = (str) => {
    let w = 0;
    for (const ch of str) {
      const code = ch.codePointAt(0);
      w += (code > 0x2E00) ? 2 : 1;
    }
    return w;
  };
  // ─ 는 1칸짜리 문자 → 가장 긴 텍스트 너비만큼 생성
  const maxLen = Math.max(...texts.map(t => visualLen(t)));
  return '─'.repeat(maxLen + 2); // 터미널 폰트 렌더링 여백 보정 +2
}

// ── 숫자 천단위 콤마 포맷 ──
function fmtNum(n) {
  return Number(n).toLocaleString('ko-KR');
}

// ── 소요시간 포맷 (분 단위, 60분 이상이면 시간+분) ──
function formatElapsed(ms) {
  const totalMin = Math.floor(ms / 60000);
  const sec = Math.floor((ms % 60000) / 1000);
  if (totalMin < 60) {
    return totalMin > 0 ? `${String(totalMin).padStart(2,'0')}분 ${String(sec).padStart(2,'0')}초` : `${String(sec).padStart(2,'0')}초`;
  }
  const h = Math.floor(totalMin / 60);
  const m = totalMin % 60;
  return `${String(h).padStart(2,'0')}시간 ${String(m).padStart(2,'0')}분`;
}

async function main() {
  log('');
  const startTime = Date.now();
  const titleLine = makeLine('  YouTube 자동 요약 스케줄러 시작 (v4.0 로컬 장부)');
  log(titleLine);
  log('  YouTube 자동 요약 스케줄러 시작 (v4.0 로컬 장부)');
  log(titleLine);

  // 설정값 검증
  if (CONFIG.youtubeApiKey === 'YOUR_YOUTUBE_API_KEY') {
    log('❌ scheduler.js 의 CONFIG 설정값을 채워주세요!'); process.exit(1);
  }

  const playlists = loadPlaylists();
  const LEGACY_MODE = process.argv.includes('--legacy');
  const useMasterMode = CONFIG.masterPlaylistId && !LEGACY_MODE;

  if (!playlists.length && !useMasterMode) {
    log('⚠️  처리할 재생목록이 없습니다. 브라우저에서 먼저 등록하세요.');
    process.exit(0);
  }

  if (useMasterMode) {
    log(`🆕 마스터 인제스트 모드 — "AI 영상목록" 기반 자동 분류`);
    log(`   (레거시 33개 재생목록 모드: node scheduler.js --legacy)`);
  } else {
    log(`📋 레거시 모드 — 총 ${playlists.length}개 재생목록 처리`);
  }

  // ── (v4.2) 직전 실행 점검 + 이번 실행 시작 기록 ──
  // 시작 기록을 먼저 쓴다 — 점검 문구를 보내다 죽어도 pending 에 남아 다음 실행이 다시 보낸다.
  const prevRun = readRunState();
  const notices = [
    ...(prevRun && Array.isArray(prevRun.pending) ? prevRun.pending : []),
    ...runNotices(prevRun, Date.now()),
  ].slice(-RUN_PENDING_MAX);
  runState = { v: 1, started_at: new Date().toISOString(), finished_at: null, outcome: 'running', reason: '', notified: false, pending: notices };
  writeRunState(runState);
  if (notices.length) {
    for (const n of notices) log(`⚠️ 직전 실행 점검: ${n.replace(/\n\s*/g, ' ')}`);
    if (await sendTelegram(`⚠️ <b>[직전 실행 점검]</b>\n${notices.join('\n')}`)) {
      runState.pending = [];
      writeRunState(runState);
    }
  }

  // ── 장부(data/library.db) 열기 + 전체 캐시 ──
  // 장부가 없거나·버전이 다르거나·0건이면 중복 판정을 못 한다. 이번 실행은 영상 처리·큐 재시도를 건너뛴다(fail-closed).
  let libCache = null;
  let libLoadError = '', libAlertSent = false;   // (v4.2) 실행 상태 기록용
  try {
    libDb = library.openLibrary();
    libCache = loadLibraryCache(libDb);
  } catch (e) {
    log(`❌ 장부 로드 실패 — 중복 저장을 막기 위해 이번 실행은 영상 처리를 건너뜁니다: ${e.message}`);
    libLoadError = shortReason(e);
    libAlertSent = await sendTelegram(`🚨 <b>[장부 로드 실패]</b>\n${e.message}\n이번 실행은 영상 처리를 건너뛰었습니다.`);
  }

  // ── pending 큐 소진 (quota 여유분 내에서) ──
  if (libCache) await flushPendingQueue();

  let totalSaved = 0, totalSkip = 0, totalError = 0;
  let runFailReason = '';   // (v4.2) 통째 실패 알림에 넣을 마지막 오류 (첫 줄)
  const results = [];

  if (!libCache) {
    totalError += 1;
    results.push({ name: useMasterMode ? 'AI 영상목록 (마스터)' : '장부', saved: 0, skip: 0, error: 1 });
  } else if (useMasterMode) {
    // ── 신규 워크플로: AI 영상목록 → 자동 분류 ──
    try {
      const result = await processMasterIngest(libCache);
      totalSaved += result.saved;
      totalSkip += result.skip;
      totalError += result.error;
      results.push({ name: 'AI 영상목록 (마스터)', ...result });
    } catch (e) {
      const errMsg = e instanceof Error ? (e.stack || e.message) : String(e);
      log(`❌ 마스터 인제스트 오류:\n${errMsg}`);
      runFailReason = `마스터 인제스트 오류: ${shortReason(e)}`;
      totalError += 1;
      results.push({ name: 'AI 영상목록 (마스터)', saved: 0, skip: 0, error: 1 });
    }
  } else {
    // ── 레거시 워크플로: 33개 토픽 재생목록 순회 ──
    for (let i = 0; i < playlists.length; i++) {
      const pl = playlists[i];
      log(`\n━━━ [${i+1}/${playlists.length}] ${pl.name} ━━━`);
      try {
        const result = await processPlaylist(pl, libCache);
        totalSaved += result.saved;
        totalSkip += result.skip;
        totalError += result.error;
        results.push({ name: pl.name, ...result });
      } catch (e) {
        const errMsg = e instanceof Error ? (e.stack || e.message) : String(e);
        log(`❌ 재생목록 처리 중 오류:\n${errMsg}`);
        runFailReason = `재생목록 처리 오류 (${pl.name}): ${shortReason(e)}`;
        totalError += 1;
        results.push({ name: pl.name, saved: 0, skip: 0, error: 1 });
      }
    }
  }

  // 장부 연결은 여기서 닫는다 (뒤이은 kakao_ingest·sync_obsidian 은 각자 연다)
  if (libDb) { try { libDb.close(); } catch {} libDb = null; }

  log('');
  const line1 = `  완료! 저장: ${fmtNum(totalSaved)}개 / Skip: ${fmtNum(totalSkip)}개 / 오류: ${fmtNum(totalError)}개`;
  const line2 = `  소요시간: ${formatElapsed(Date.now() - startTime)}`;
  const finishLine = makeLine(line1, line2);
  log(finishLine);
  log(line1);
  log(line2);
  log(finishLine);

  // ── (v4.2) 통째 실패 알림 + 실행 결과 기록 ──
  // 저장 0 · Skip 0 · 오류 ≥1 은 예전에 아래 hasNewOrUpdated 에 걸리지 않아 텔레그램 없이 지나갔다.
  if (isWholeRunFailure({ saved: totalSaved, skip: totalSkip, error: totalError })) {
    runState.outcome = 'fail';
    if (!libCache) {
      // 장부 로드 실패는 위에서 이미 [장부 로드 실패] 로 알렸다 — 두 번 보내지 않는다
      runState.reason = `장부 로드 실패: ${libLoadError}`;
      runState.notified = libAlertSent;
    } else {
      runState.reason = runFailReason || `오류 ${totalError}건`;
      runState.notified = await sendTelegram(
        `🚨 <b>[실행 실패]</b>\n저장 0 · Skip 0 · 오류 ${fmtNum(totalError)} — 이번 실행은 영상을 하나도 확인하지 못했습니다.\n` +
        `원인: ${escapeHtml(runState.reason)}\n다음 정시 실행이 다시 시도합니다.`);
    }
  } else {
    runState.outcome = 'ok';
  }
  runState.finished_at = new Date().toISOString();
  writeRunState(runState);

  // ── 전체 완료 알림 전송 ──
  const now = new Date().toLocaleString('ko-KR', { timeZone: 'Asia/Seoul' });

  // 마스터 모드: 주제별 분류 / 저장 영상 목록 포함한 상세 메시지
  let summaryLines;
  if (useMasterMode && results.length > 0) {
    const r = results[0];
    const inPlaylist = r.totalInPlaylist ?? (r.saved + r.skip + r.error);
    const lines = [];

    if (r.saved > 0) {
      lines.push(`• AI 영상목록 (마스터): 재생목록 ${fmtNum(inPlaylist)}개 | 신규 저장 ${fmtNum(r.saved)}개 | 스킵 ${fmtNum(r.skip)}개`);

      // 주제별 저장 건수
      const topicEntries = Object.entries(r.topicStats || {}).sort((a, b) => b[1] - a[1]);
      if (topicEntries.length) {
        lines.push(`  🏷 주제별: ${topicEntries.map(([t, c]) => `${t}(${c})`).join(', ')}`);
      }
    } else {
      lines.push(`• AI 영상목록 (마스터): 재생목록 ${fmtNum(inPlaylist)}개 | 신규 없음`);
      lines.push(`  ℹ️ ${fmtNum(r.skip)}개 모두 이미 장부에 저장된 영상`);
      // 스킵 예시 (최대 2개 — 실제로 어떤 영상인지 파악용)
      const samples = (r.skipList || []).slice(0, 2).map(t => t.slice(0, 25));
      if (samples.length) {
        lines.push(`  예) ${samples.map(t => `"${t}"`).join(', ')} …`);
      }
    }
    if (r.error > 0) lines.push(`  ❌ 오류 ${fmtNum(r.error)}개`);
    summaryLines = lines.join('\n');
  } else {
    // 레거시 모드: 기존 형식
    summaryLines = results.map(r =>
      `• ${r.name}: 저장 ${fmtNum(r.saved)}/ 스킵 ${fmtNum(r.skip)}/ 오류 ${fmtNum(r.error)}`
    ).join('\n');
  }
  const elapsed = formatElapsed(Date.now() - startTime);
  const totalLine = useMasterMode
    ? `📊 합계: 신규 저장 ${fmtNum(totalSaved)}개 | 스킵 ${fmtNum(totalSkip)}개 | 오류 ${fmtNum(totalError)}개`
    : `📊 합계: 저장 ${fmtNum(totalSaved)}/ 스킵 ${fmtNum(totalSkip)}/ 오류 ${fmtNum(totalError)}`;

  // ── pending 큐 적체 경고 (3개월간 아무도 모르고 5,392건까지 쌓인 사고 재발 방지) ──
  const queueLines = [];
  // 큐 파일을 한 번만 읽어 잔량과 오늘 유입을 함께 구한다.
  const queueSnapshot = (() => {
    try { return JSON.parse(fs.readFileSync(path.join(__dirname, 'pending_playlist_adds.json'), 'utf-8')); } catch { return []; }
  })();
  const pendingCount = queueSnapshot.length;

  if (pendingCount > 0) {
    const yt = require('./lib/youtube_oauth');
    const today = yt.todayKey();
    const qs = yt.loadQuotaState();          // ok/fail 이 없으면 0으로 채워져 온다
    const ok = qs.ok || 0, fail = qs.fail || 0;

    // ── 오늘 쓰기 결과 ──
    if (ok > 0) {
      queueLines.push(`✅ 재생목록 추가: ${fmtNum(ok)}건${fail ? ` (실패 ${fmtNum(fail)}건)` : ''}`);
    } else if (fail > 0) {
      // 인증은 되는데 쓰기만 전부 실패 — 계정 불일치·권한 문제의 신호
      queueLines.push(`🛑 오늘 재생목록 추가 전부 실패 (${fmtNum(fail)}건) — OAuth 계정 일치 확인 필요`);
    } else if (qs.date !== today) {
      queueLines.push(`🛑 오늘 YouTube 쓰기 시도 없음 — quota_state 마지막 갱신 ${qs.date}`);
    }

    // ── 잔량 + 오늘 유입 ──
    //   ts 는 appendPending 이 찍는 UTC ISO 문자열이므로 UTC 날짜로 맞춰 센다.
    const utcToday = new Date().toISOString().slice(0, 10);
    const inflow = queueSnapshot.filter(x => String(x.ts || '').slice(0, 10) === utcToday).length;
    const net = ok - inflow;
    const eta = net > 0 ? ` · 순감 ${fmtNum(net)}/일 → 약 ${(pendingCount / net).toFixed(1)}일` : '';
    queueLines.push(`⏳ 재생목록 대기: ${fmtNum(pendingCount)}건 (오늘 유입 +${fmtNum(inflow)}${eta})`);
    if (net <= 0 && ok > 0) queueLines.push(`⚠️ 유입이 배수보다 많음 — 큐가 줄지 않습니다`);

    if (pendingCount >= 1000) queueLines.push(`⚠️ 큐 적체 — 원인 확인 필요`);
  }

  const msg = [
    `🎬 YouTube 요약 완료`,
    `📅 ${now}`,
    `⏱ 소요시간: ${elapsed}`,
    ``,
    summaryLines,
    ``,
    totalLine,
    ...queueLines,
  ].join('\n');

  await sendEmail(`[YouTube 요약] 완료 - 저장 ${totalSaved}개`, msg);

  const python3 = '/opt/homebrew/bin/python3';

  // ── (v3.0) 카카오톡 → 장부 tips (새 CSV 있을 때만 실제 동작) ──
  log('\n📎 카톡 → AI 꿀팁 인제스트...');
  const kakao = await runKakaoIngest(python3);
  const kakaoCreated = (kakao && kakao.created) || 0;

  // ── (v4.0 3단계) 장부 → 구글 시트 미러 (설정 전이면 skipped) ──
  log('\n📗 구글 시트 미러...');
  const mirror = await runSheetMirror(python3);
  const mirrorSent = mirror && !mirror.skipped ? (mirror.videos_sent || 0) + (mirror.tips_sent || 0) : 0;
  const mirrorFailed = !!(mirror && mirror.error);

  // ── (v4.1) 장부 하루 1회 백업 (오늘 것 있으면 skipped). 실패는 텔레그램 별도 한 줄 — 저장 0건 실행에도 알린다 ──
  log('\n🗄  장부 백업...');
  const backup = await runLibraryBackup(python3);
  if (backup && backup.error) {
    const d = backup.dests || {};
    await sendTelegram(`⚠️ <b>[장부 백업 실패]</b>\n${backup.error}\n로컬: ${d.local || '-'} · 드라이브: ${d.drive || '-'}\n` +
      (String(backup.error).includes('drive') ? '구글 드라이브 앱 실행·로그인 확인' : 'backup_library.py --status 로 확인'));
  }

  // ── Obsidian 동기화 (항상 실행 - 장부·카톡·시트·Obsidian 결과 합쳐서 1개 메시지 전송) ──
  log('\n🔄 Obsidian 동기화 시작...');
  const { execFile } = require('child_process');
  const syncScript = path.join(__dirname, 'sync_obsidian.py');
  const syncArgs = totalSaved > 0 ? [syncScript] : [syncScript, '--rebuild'];
  execFile(python3, syncArgs, { cwd: __dirname }, async (err, stdout, stderr) => {
    if (err) {
      log(`❌ Obsidian 동기화 오류: ${err.message}`);
      if (totalSaved > 0) {
        await sendTelegram(msg + `\n\n⚠️ Obsidian 동기화 실패`);
      }
      return;
    }
    const jsonLine = stdout.split('\n').find(l => l.startsWith('RESULT_JSON:'));
    if (jsonLine) {
      try {
        const r = JSON.parse(jsonLine.replace('RESULT_JSON:', ''));
        const tipsAdded = r.tips_added || 0;
        const kakaoSection = kakaoCreated > 0 ? [
          ``,
          `━━━━━━━━━━━━━━━━━━━━━━`,
          `📎 카톡 → AI 꿀팁`,
          `  • 장부 신규: ${kakaoCreated}건 (총 ${kakao.db_total}건)`,
          ...(Array.isArray(kakao.titles) ? kakao.titles.slice(0, 5).map(t => `    - ${t}`) : []),
        ] : [];
        const mirrorSection = (mirrorSent > 0 || mirrorFailed) ? [
          ``,
          `━━━━━━━━━━━━━━━━━━━━━━`,
          `📗 구글 시트 미러`,
          ...(mirrorSent > 0 ? [`  • 보냄: 영상 ${mirror.videos_sent || 0}건 · 꿀팁 ${mirror.tips_sent || 0}건${mirror.full ? ' (전체)' : ''}`] : []),
          ...(mirrorFailed ? [`  • ⚠️ 실패 (${mirror.error}) — ${mirror.error === 'auth' ? '토큰·웹앱 배포 확인 필요' : '다음 실행에 다시 보냄'}`] : []),
        ] : [];
        const obsSection = [
          ...kakaoSection,
          ...mirrorSection,
          ``,
          `━━━━━━━━━━━━━━━━━━━━━━`,
          `📓 Obsidian AI LLM Wiki`,
          `  • 신규 영상 노트: ${r.added - tipsAdded}개`,
          ...(tipsAdded > 0 ? [`  • 신규 꿀팁 노트: ${tipsAdded}개`] : []),
          ...(r.tags_updated > 0 ? [`  • tags 갱신: ${r.tags_updated}개`] : []),
          `  • Wiki 재구성: ${r.rebuilt ? '✅ 완료' : '⏭ 생략'}`,
          `  • 소요시간: ${r.elapsed}초`,
        ].join('\n');
        log(`✅ Obsidian 동기화 완료! 추가: ${r.added}개 (꿀팁 ${tipsAdded})`);

        const hasNewOrUpdated = totalSaved > 0 || kakaoCreated > 0 || (r.added && r.added > 0) || (r.tags_updated && r.tags_updated > 0) || mirrorFailed;
        if (hasNewOrUpdated) {
          await sendTelegram(msg + obsSection);
        } else {
          log(`ℹ️  신규 저장/업데이트된 동영상이 없으므로 텔레그램 메시지 발송 생략`);
        }
      } catch(e) {
        log(`⚠️ Obsidian 결과 파싱 오류: ${e.message}`);
        if (totalSaved > 0) {
          await sendTelegram(msg);
        }
      }
    } else {
      if (totalSaved > 0) {
        await sendTelegram(msg);
      }
    }
  });
}

// 직접 실행할 때만 main 을 돈다. require 하면 아래 함수만 내보낸다(scripts/test_scheduler_guards.js·읽기 전용 점검용).
if (require.main === module) {
  main().catch(async e => {
    log(`❌ 치명적 오류: ${e.message}`);
    // (v4.2) 끝을 먼저 기록하고 알린다. 알림이 실패하면(네트워크 다운) notified=false 로 남아 다음 실행이 다시 알린다.
    const reason = `치명적 오류: ${shortReason(e)}`;
    const st = { ...(runState || { v: 1, started_at: new Date().toISOString(), pending: [] }),
      outcome: 'fail', reason, notified: false, finished_at: new Date().toISOString() };
    writeRunState(st);
    st.notified = await sendTelegram(`🚨 <b>[실행 실패]</b>\n${escapeHtml(reason)}\n실행이 중간에 멈췄습니다. 다음 정시 실행이 다시 시도합니다.`);
    if (st.notified) writeRunState(st);
    process.exit(1);
  });
} else {
  module.exports = {
    ytFetch, getVideos, getBatchDetails, getBatchSubs, loadLibraryCache, findDuplicate, saveToLibrary, runSheetMirror, runLibraryBackup,
    sendTelegram, readRunState, writeRunState, runNotices, isWholeRunFailure, escapeHtml,   // (v4.2) 실행 실패 알림
    _setLibDb: (db) => { libDb = db; },   // 테스트 전용 (scripts/test_scheduler_guards.js)
  };
}
