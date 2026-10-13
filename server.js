// ===== YouTube AI 요약기 백엔드 서버 (보안 강화판, v4.0: 노션 프록시·Obsidian 동기화 트리거 제거) =====
// 실행 방법: node server.js

const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');

const PORT = 3000;

// ── .env 파일 로드 ──
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

// ── 허용할 출처 (localhost만 허용) ──
const ALLOWED_ORIGINS = [
  'http://localhost:3000',
  'http://127.0.0.1:3000',
];

// ── 요청 크기 제한 (5MB) ──
const MAX_BODY_SIZE = 5 * 1024 * 1024;

// ── Rate Limiting (IP당 분당 최대 요청 수) ──
const rateLimitMap = new Map();
const RATE_LIMIT = 120;     // 분당 최대 요청 수
const RATE_WINDOW = 60000;  // 1분

function checkRateLimit(ip) {
  const now = Date.now();
  const entry = rateLimitMap.get(ip) || { count: 0, start: now };
  if (now - entry.start > RATE_WINDOW) {
    rateLimitMap.set(ip, { count: 1, start: now });
    return true;
  }
  if (entry.count >= RATE_LIMIT) return false;
  entry.count++;
  rateLimitMap.set(ip, entry);
  return true;
}

// ── 오래된 Rate Limit 항목 주기적 정리 (메모리 누수 방지) ──
setInterval(() => {
  const now = Date.now();
  for (const [ip, entry] of rateLimitMap.entries()) {
    if (now - entry.start > RATE_WINDOW * 2) rateLimitMap.delete(ip);
  }
}, 60000);

// ── playlists.json 입력값 검증 ──
function validatePlaylists(data) {
  let parsed;
  try { parsed = JSON.parse(data); } catch(e) { return false; }
  if (!Array.isArray(parsed)) return false;
  if (parsed.length > 100) return false; // 최대 100개
  for (const item of parsed) {
    if (typeof item !== 'object' || !item.url || !item.name) return false;
    if (typeof item.url !== 'string' || typeof item.name !== 'string') return false;
    if (item.url.length > 500 || item.name.length > 200) return false;
    // YouTube 재생목록 URL 형식만 허용
    if (!/^https:\/\/(www\.)?youtube\.com\/playlist\?/.test(item.url) &&
        !/^https:\/\/youtube\.com\/playlist\?/.test(item.url)) return false;
  }
  return true;
}

// ── CORS 헤더 생성 (출처 검증) ──
function getCorsHeaders(origin) {
  const allowed = ALLOWED_ORIGINS.includes(origin) ? origin : ALLOWED_ORIGINS[0];
  return {
    'Content-Type': 'application/json; charset=utf-8',
    'Access-Control-Allow-Origin': allowed,
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
  };
}

// ── 요청 본문 수집 (크기 제한 적용) ──
function collectBody(req, callback) {
  let body = '';
  let size = 0;
  req.on('data', chunk => {
    size += chunk.length;
    if (size > MAX_BODY_SIZE) {
      callback(new Error('요청 크기 초과'), null);
      req.destroy();
      return;
    }
    body += chunk;
  });
  req.on('end', () => callback(null, body));
  req.on('error', err => callback(err, null));
}

// ── HTTP 서버 ──
const server = http.createServer((req, res) => {
  // WHATWG URL API 사용 (url.parse() 보안 경고 제거)
  const parsedUrl = new URL(req.url, 'http://localhost');
  const origin = req.headers.origin || '';
  const CORS = getCorsHeaders(origin);
  const clientIp = req.headers['x-forwarded-for'] || req.socket.remoteAddress || '';

  // Rate Limit 검사
  if (!checkRateLimit(clientIp)) {
    res.writeHead(429, { ...CORS, 'Retry-After': '60' });
    res.end(JSON.stringify({ error: '요청이 너무 많습니다. 잠시 후 다시 시도하세요.' }));
    return;
  }

  // CORS Preflight
  if (req.method === 'OPTIONS') {
    res.writeHead(204, CORS);
    res.end();
    return;
  }

  // ── API 설정값 제공 (웹앱 자동 로드용) ──
  if (parsedUrl.pathname === '/api/config' && req.method === 'GET') {
    res.writeHead(200, CORS);
    res.end(JSON.stringify({
      ytKey:   process.env.YOUTUBE_API_KEY  || '',
      gmKey:   process.env.GEMINI_API_KEY   || '',
      telegram: {
        enabled:  process.env.TELEGRAM_ENABLED === 'true',
        botToken: process.env.TELEGRAM_BOT_TOKEN || '',
        chatId:   process.env.TELEGRAM_CHAT_ID   || '',
      },
    }));
    return;
  }

  // ── AI 영상목록 마스터 인제스트 (SSE 스트리밍) ──
  if (parsedUrl.pathname === '/api/master-ingest' && req.method === 'POST') {
    res.writeHead(200, {
      ...CORS,
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'X-Accel-Buffering': 'no',
    });

    const send = (msg) => {
      try { res.write(`data: ${JSON.stringify({ msg })}\n\n`); } catch {}
    };
    const done = (stats) => {
      try { res.write(`data: ${JSON.stringify({ done: true, stats })}\n\n`); res.end(); } catch {}
    };

    send('🚀 AI 영상목록 마스터 인제스트 시작...');

    const { spawn } = require('child_process');
    const child = spawn(process.execPath, [require('path').join(__dirname, 'scheduler.js')], {
      cwd: __dirname,
      env: { ...process.env },
    });

    let output = '';
    child.stdout.on('data', (d) => {
      const text = d.toString();
      output += text;
      for (const line of text.split('\n')) {
        // RESULT_ROW: 접두사 → 구조화 데이터(결과 테이블용)로 별도 전송
        if (line.startsWith('RESULT_ROW:')) {
          try {
            const row = JSON.parse(line.slice('RESULT_ROW:'.length).trim());
            try { res.write(`data: ${JSON.stringify({ row })}\n\n`); } catch {}
          } catch {}
          continue;
        }
        const clean = line.replace(/^\[.*?\]\s*/, '').trim();
        if (clean) send(clean);
      }
    });
    child.stderr.on('data', (d) => send('⚠️ ' + d.toString().trim()));

    child.on('close', (code) => {
      // 통계 파싱
      const savedM  = output.match(/저장:\s*([\d,]+)개/);
      const skipM   = output.match(/Skip:\s*([\d,]+)개/);
      const errorM  = output.match(/오류:\s*([\d,]+)개/);
      done({
        saved: parseInt((savedM?.[1] || '0').replace(/,/g, ''), 10),
        skip:  parseInt((skipM?.[1]  || '0').replace(/,/g, ''), 10),
        error: parseInt((errorM?.[1] || '0').replace(/,/g, ''), 10),
        code,
      });
    });

    req.on('close', () => { try { child.kill(); } catch {} });
    return;
  }

  // ── LLM Wiki 검색 페이지 ──
  if (parsedUrl.pathname === '/wiki' && req.method === 'GET') {
    fs.readFile(path.join(__dirname, 'wiki.html'), (err, data) => {
      if (err) { res.writeHead(404); res.end('Not Found'); return; }
      res.writeHead(200, {
        'Content-Type': 'text/html; charset=utf-8',
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'Cache-Control': 'no-store',
      });
      res.end(data);
    });
    return;
  }

  // ── LLM Wiki 토픽 목록 (필터 드롭다운용) ──
  if (parsedUrl.pathname === '/api/wiki-topics' && req.method === 'GET') {
    try {
      const topics = require('./lib/wiki_search').listTopics();
      res.writeHead(200, CORS);
      res.end(JSON.stringify({ topics }));
    } catch (e) {
      res.writeHead(500, CORS);
      res.end(JSON.stringify({ error: e.message }));
    }
    return;
  }

  // ── LLM Wiki 검색 API ──
  if (parsedUrl.pathname === '/api/wiki-search' && req.method === 'GET') {
    // (v4.7) all=1 — 전체 목록(필터·정렬은 화면에서). 임베딩 호출 없음
    if (parsedUrl.searchParams.get('all') === '1') {
      try {
        const pl = require('./lib/wiki_search').listPayload();
        if (req.headers['if-none-match'] === pl.etag) { res.writeHead(304, { ...CORS, 'Cache-Control': 'no-cache', ETag: pl.etag }); res.end(); return; }
        const gz = /\bgzip\b/.test(req.headers['accept-encoding'] || '');
        res.writeHead(200, { ...CORS, 'Cache-Control': 'no-cache', ETag: pl.etag, Vary: 'Accept-Encoding', ...(gz ? { 'Content-Encoding': 'gzip' } : {}) });
        res.end(gz ? pl.gz : pl.json);
      } catch (e) {
        console.error('[wiki-search] list 오류:', e.message);
        res.writeHead(500, CORS);
        res.end(JSON.stringify({ error: e.message }));
      }
      return;
    }
    // (v4.7) similar=<id> — 그 노트와 의미가 가까운 5개(저장된 벡터만, Gemini 호출 없음)
    if (parsedUrl.searchParams.has('similar')) {
      const ws = require('./lib/wiki_search');
      const id = parsedUrl.searchParams.get('similar') || '';
      if (!ws.ID_RE.test(id)) { res.writeHead(400, CORS); res.end(JSON.stringify({ error: '잘못된 id 입니다.' })); return; }
      try {
        const r = ws.similar(id, 5);
        res.writeHead(r ? 200 : 404, CORS);
        res.end(JSON.stringify(r ? { results: r } : { error: '없는 노트입니다.' }));
      } catch (e) {
        console.error('[wiki-search] similar 오류:', e.message);
        res.writeHead(500, CORS); res.end(JSON.stringify({ error: e.message }));
      }
      return;
    }
    const q = (parsedUrl.searchParams.get('q') || '').trim();
    if (!q || q.length > 500) {
      res.writeHead(400, CORS);
      res.end(JSON.stringify({ error: '검색어(q)는 1~500자여야 합니다.' }));
      return;
    }
    // (v4.7) scores=1 — 모든 노트의 점수만(화면이 목록에 붙여 정렬·필터)
    if (parsedUrl.searchParams.get('scores') === '1') {
      require('./lib/wiki_search').scoreAll(q)
        .then(r => { res.writeHead(200, CORS); res.end(JSON.stringify(r)); })
        .catch(e => {
          console.error('[wiki-search] scores 오류:', e.message);
          res.writeHead(500, CORS);
          res.end(JSON.stringify({ error: e.message }));
        });
      return;
    }
    const topic = (parsedUrl.searchParams.get('topic') || '').trim();
    const limit = Math.min(parseInt(parsedUrl.searchParams.get('limit') || '10', 10) || 10, 30);
    const wikiSearch = require('./lib/wiki_search');
    wikiSearch.search(q, { topic, limit })
      .then(({ results, mode }) => {
        res.writeHead(200, CORS);
        res.end(JSON.stringify({ results, mode }));
      })
      .catch(e => {
        console.error('[wiki-search] 오류:', e.message);
        res.writeHead(500, CORS);
        res.end(JSON.stringify({ error: e.message }));
      });
    return;
  }

  // ── (v4.7) LLM Wiki 노트 본문 미리보기 — 읽기 전용, id 로만 찾는다 ──
  if (parsedUrl.pathname === '/api/wiki-note' && req.method === 'GET') {
    const ws = require('./lib/wiki_search');
    const id = parsedUrl.searchParams.get('id') || '';
    if (!ws.ID_RE.test(id)) { res.writeHead(400, CORS); res.end(JSON.stringify({ error: '잘못된 id 입니다.' })); return; }
    try {
      const r = ws.noteById(id);
      res.writeHead(r ? 200 : 404, CORS);
      res.end(JSON.stringify(r || { error: '없는 노트입니다.' }));
    } catch (e) {
      console.error('[wiki-note] 오류:', e.message);
      res.writeHead(404, CORS); res.end(JSON.stringify({ error: '노트를 읽지 못했습니다.' }));
    }
    return;
  }

  // ── LLM Wiki AI 답변 API (RAG) ──
  if (parsedUrl.pathname === '/api/wiki-ask' && req.method === 'POST') {
    collectBody(req, (err, body) => {
      if (err) {
        res.writeHead(413, CORS);
        res.end(JSON.stringify({ error: err.message }));
        return;
      }
      let question = '';
      try { question = (JSON.parse(body || '{}').question || '').trim(); } catch (e) {}
      if (!question || question.length > 500) {
        res.writeHead(400, CORS);
        res.end(JSON.stringify({ error: '질문(question)은 1~500자여야 합니다.' }));
        return;
      }
      const wikiSearch = require('./lib/wiki_search');
      wikiSearch.ask(question)
        .then(result => {
          res.writeHead(200, CORS);
          res.end(JSON.stringify(result));
        })
        .catch(e => {
          console.error('[wiki-ask] 오류:', e.message);
          // 답변 생성 실패 시에도 검색 결과는 최대한 반환
          wikiSearch.search(question, { limit: 8 })
            .then(({ results }) => {
              res.writeHead(503, CORS);
              res.end(JSON.stringify({ error: 'AI 답변 생성 불가 (일일 한도 도달 또는 API 중단)', results }));
            })
            .catch(() => {
              res.writeHead(500, CORS);
              res.end(JSON.stringify({ error: e.message }));
            });
        });
    });
    return;
  }

  // ── HTML 서빙 ──
  if (parsedUrl.pathname === '/' || parsedUrl.pathname === '/index.html') {
    fs.readFile(path.join(__dirname, 'index.html'), (err, data) => {
      if (err) { res.writeHead(404); res.end('Not Found'); return; }
      res.writeHead(200, {
        'Content-Type': 'text/html; charset=utf-8',
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'Cache-Control': 'no-store',
      });
      res.end(data);
    });
    return;
  }

  // ── 이메일 전송 ──
  if (parsedUrl.pathname === '/send-email' && req.method === 'POST') {
    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', () => {
      try {
        const { from, to, appPass, subject, body: msgBody } = JSON.parse(body);
        if (!from || !to || !appPass || !subject) {
          res.writeHead(400, CORS);
          res.end(JSON.stringify({ ok: false, error: '필수 파라미터 누락' }));
          return;
        }
        const tls = require('tls');
        const auth = Buffer.from(`\0${from}\0${appPass.replace(/\s/g,'')}`).toString('base64');
        const subjectEncoded = `=?UTF-8?B?${Buffer.from(subject).toString('base64')}?=`;
        const bodyBase64 = Buffer.from(msgBody || '').toString('base64');
        const msg = [
          `From: YouTube 요약기 <${from}>`,
          `To: ${to}`,
          `Subject: ${subjectEncoded}`,
          'MIME-Version: 1.0',
          'Content-Type: text/plain; charset=UTF-8',
          'Content-Transfer-Encoding: base64',
          '',
          bodyBase64,
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
          socket.on('data', d => {
            const r = d.toString();
            if ((r.startsWith('220') || r.includes('250') || r.includes('235')) && step < 5) {
              socket.write(cmds[step++]);
            } else if (r.startsWith('354') && step === 5) {
              socket.write(cmds[step++]);
            } else if (r.startsWith('250') && step === 6) {
              socket.write(cmds[step++]);
            } else if (r.startsWith('221')) {
              res.writeHead(200, CORS);
              res.end(JSON.stringify({ ok: true }));
              socket.destroy();
            }
          });
          socket.on('error', e => {
            res.writeHead(500, CORS);
            res.end(JSON.stringify({ ok: false, error: e.message }));
          });
        });
        socket.on('error', e => {
          res.writeHead(500, CORS);
          res.end(JSON.stringify({ ok: false, error: e.message }));
        });
      } catch(e) {
        res.writeHead(500, CORS);
        res.end(JSON.stringify({ ok: false, error: e.message }));
      }
    });
    return;
  }

  // ── 재생목록 읽기 ──
  if (parsedUrl.pathname === '/playlists' && req.method === 'GET') {
    const filePath = path.join(__dirname, 'playlists.json');
    fs.readFile(filePath, 'utf8', (err, data) => {
      res.writeHead(200, CORS);
      res.end(err ? '[]' : data);
    });
    return;
  }

  // ── 재생목록 저장 ──
  if (parsedUrl.pathname === '/playlists' && req.method === 'POST') {
    collectBody(req, (err, body) => {
      if (err) {
        res.writeHead(413, CORS);
        res.end(JSON.stringify({ error: err.message }));
        return;
      }
      // 입력값 검증
      if (!validatePlaylists(body)) {
        res.writeHead(400, CORS);
        res.end(JSON.stringify({ error: '유효하지 않은 재생목록 데이터입니다.' }));
        return;
      }
      const filePath = path.join(__dirname, 'playlists.json');
      fs.writeFile(filePath, body, 'utf8', (err) => {
        res.writeHead(err ? 500 : 200, CORS);
        res.end(JSON.stringify({ ok: !err }));
      });
    });
    return;
  }

  // ── 404 ──
  res.writeHead(404, CORS);
  res.end(JSON.stringify({ error: 'Not Found' }));
});

server.listen(PORT, '127.0.0.1', () => {
  console.log('');
  console.log('========================================');
  console.log('  YouTube AI 요약기 (보안 강화, v4.0 로컬 장부)');
  console.log('========================================');
  console.log(`  브라우저 접속: http://localhost:${PORT}`);
  console.log('  종료: Ctrl+C');
  console.log('========================================');
  console.log('');
});
