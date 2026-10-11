// v4.0 로컬 원본 장부(data/library.db) — Node 쪽 헬퍼. Python 쪽은 lib/library_db.py.
// 스키마 원본은 lib/library_schema.sql 하나다. 이 파일은 user_version 을 그 파일에서 읽어 대조만 한다.
//
// ★ openLibrary 는 파일이 없으면 만들지 않고 던진다. 빈 장부를 새로 만들면 모든 영상이 신규로 보여 중복 저장이 난다
//   (2026-10-05 빈 Notion 캐시 사고와 같은 구조). 호출자(scheduler.js main)는 던지면 영상 처리를 건너뛴다(fail-closed).
// ★ journal_mode 는 기본(DELETE) 그대로 둔다. 쓰기는 짧은 단일 문장이고 접근 순서가 scheduler → kakao_ingest → sync_obsidian
//   으로 순차라 WAL 이 필요 없다. 동시 실행(launchd + 웹 버튼)이 겹치면 busy_timeout 5초 동안 기다린다.
'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const REPO_ROOT = path.join(__dirname, '..');
const DB_PATH = path.join(REPO_ROOT, 'data', 'library.db');
const SCHEMA_PATH = path.join(__dirname, 'library_schema.sql');
const BUSY_TIMEOUT_MS = 5000;

// node:sqlite 는 Node 22 에서 실험 기능이라 require 순간 ExperimentalWarning 을 stderr 로 찍는다.
// 그 한 줄만 삼킨다 (server.js 의 마스터 인제스트가 stderr 를 '⚠️' 로 화면에 흘리기 때문). 다른 경고는 그대로 통과.
function loadSqlite() {
  const orig = process.emitWarning;
  process.emitWarning = function (w, ...rest) {
    if (String((w && w.message) || w).includes('SQLite is an experimental feature')) return;
    return orig.call(process, w, ...rest);
  };
  try { return require('node:sqlite'); } finally { process.emitWarning = orig; }
}

function schemaVersion() {
  const m = fs.readFileSync(SCHEMA_PATH, 'utf8').match(/PRAGMA\s+user_version\s*=\s*(\d+)/i);
  if (!m) throw new Error(`${SCHEMA_PATH} 에서 user_version 을 못 찾았습니다`);
  return Number(m[1]);
}

function openLibrary(dbPath = DB_PATH) {
  if (!fs.existsSync(dbPath)) {
    throw new Error(`장부 파일 없음: ${path.relative(REPO_ROOT, dbPath) || dbPath} — 원본 장부다. 새로 만들지 말고 백업(data/library.db.bak.*)에서 복원할 것`);
  }
  const { DatabaseSync } = loadSqlite();
  const db = new DatabaseSync(dbPath);
  try {
    db.exec(`PRAGMA busy_timeout = ${BUSY_TIMEOUT_MS}`);
    const uv = db.prepare('PRAGMA user_version').get().user_version;
    const want = schemaVersion();
    if (uv !== want) throw new Error(`장부 user_version ${uv} ≠ 스키마 ${want} — 다른 버전의 장부입니다`);
  } catch (e) {
    try { db.close(); } catch {}
    throw e;
  }
  return db;
}

const nfc = (s) => String(s || '').normalize('NFC');
const nowIso = () => new Date().toISOString();

function parseTopics(json) {
  try {
    const a = JSON.parse(json || '[]');
    return Array.isArray(a) ? a.map(nfc).filter(Boolean) : [];
  } catch { return []; }
}

// 중복 판정용 전체 행 (videos 만. videos_dup 은 같은 video_id 의 보관본이라 판정에 필요 없다)
function allVideos(db) {
  return db.prepare(
    'SELECT record_id, video_id, title, topics, view_count, subscriber_count, upload_date FROM videos'
  ).all().map(r => ({ ...r, topics: parseTopics(r.topics) }));
}

// 신규 영상 1건 저장 → record_id(uuid4). 같은 video_id 가 이미 있으면 UNIQUE 위반으로 던진다(덮어쓰지 않는다).
function insertVideo(db, v) {
  const topics = [...new Set((v.topics || []).map(nfc).filter(Boolean))];
  const id = crypto.randomUUID();
  const ts = nowIso();
  db.prepare(`INSERT INTO videos
    (record_id, video_id, title, channel, topics, upload_date, view_count, subscriber_count,
     video_url, thumbnail_url, status, summary, summary_src, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'app', ?, ?)`).run(
    id, v.videoId || null, nfc(v.title), nfc(v.channelTitle), JSON.stringify(topics),
    v.uploadDate || null, v.viewCount ?? null, v.subscriberCount ?? null,
    v.videoId ? `https://www.youtube.com/watch?v=${v.videoId}` : null,
    v.thumbnail || null, '완료', nfc(v.summary), ts, ts);
  return id;
}

// 주제 1개 추가. 장부의 현재 값을 다시 읽어 합집합으로 쓴다(캐시 값을 믿지 않는다). 반환: 추가했으면 true
function addTopic(db, recordId, topic) {
  const t = nfc(topic);
  if (!t) return false;
  const row = db.prepare('SELECT topics FROM videos WHERE record_id = ?').get(recordId);
  if (!row) throw new Error(`장부에 없는 record_id: ${recordId}`);
  const cur = parseTopics(row.topics);
  if (cur.includes(t)) return false;
  db.prepare('UPDATE videos SET topics = ?, updated_at = ? WHERE record_id = ?')
    .run(JSON.stringify([...cur, t]), nowIso(), recordId);
  return true;
}

// 조회수·구독자수(·업로드일) 갱신. uploadDate 가 없으면 기존 값을 그대로 둔다.
function updateStats(db, recordId, viewCount, subscriberCount, uploadDate) {
  const r = uploadDate
    ? db.prepare('UPDATE videos SET view_count = ?, subscriber_count = ?, upload_date = ?, updated_at = ? WHERE record_id = ?')
        .run(viewCount || 0, subscriberCount || 0, uploadDate, nowIso(), recordId)
    : db.prepare('UPDATE videos SET view_count = ?, subscriber_count = ?, updated_at = ? WHERE record_id = ?')
        .run(viewCount || 0, subscriberCount || 0, nowIso(), recordId);
  return Number(r.changes) === 1;
}

module.exports = { DB_PATH, loadSqlite, openLibrary, allVideos, insertVideo, addTopic, updateStats, schemaVersion };
