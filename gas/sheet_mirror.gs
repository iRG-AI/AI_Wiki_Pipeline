/**
 * YouTube_Notion_Grab v4.0 — 장부(data/library.db) → 구글 시트 미러 수신부 (Apps Script 웹앱)
 *
 * 보기 전용 단방향 미러다. 원본은 맥의 장부이고, 이 시트를 고쳐도 장부로 돌아가지 않는다.
 * 보내는 쪽: 레포 루트 sheet_mirror.py (스케줄러가 매 실행 끝에 변경분만 보낸다).
 *
 * 설치 (시트 하나에 한 번):
 *   1) 이 시트에서 확장 프로그램 → Apps Script → 이 파일 내용을 Code.gs 에 통째로 붙여 넣고 저장
 *   2) 프로젝트 설정(톱니) → 스크립트 속성 → MIRROR_TOKEN = (맥 .env 의 SHEET_MIRROR_TOKEN 과 같은 값)
 *   3) 배포 → 새 배포 → 유형 "웹 앱" → 실행 계정 "나", 액세스 권한 "모든 사용자" → 배포 → 웹 앱 URL 복사
 *      (권한 승인 창이 뜨면 이 시트 소유 계정으로 승인)
 *   코드를 고친 뒤에는 배포 → 배포 관리 → 연필 → 버전 "새 버전" 으로 같은 URL 을 유지한다.
 *
 * 요청 (POST, JSON 본문):
 *   { token, op: 'ping' }                                → { ok, counts: { 영상: n, 꿀팁: m } }
 *   { token, op: 'reset',  sheet, headers }              → 탭을 비우고 머리글만 쓴다
 *   { token, op: 'upsert', sheet, headers, rows: [[…]] } → 1열(record_id) 기준 있으면 덮어쓰기, 없으면 아래에 추가
 * 응답은 언제나 JSON. 실패는 { ok:false, error } — 'auth' | 'not_configured' | 'bad_request' | 'headers_mismatch' | 'busy' | 'internal'
 * (Apps Script 웹앱은 HTTP 상태 코드를 고를 수 없어서 오류도 200 으로 나간다. 보내는 쪽은 error 값으로 판단한다)
 *
 * 지키는 것:
 *   · 토큰이 맞지 않으면 아무것도 쓰지 않는다. 토큰은 URL 이 아니라 본문으로만 받는다.
 *   · 탭은 '영상'·'꿀팁' 둘만 만든다(화이트리스트).
 *   · 머리글이 보내는 쪽과 다르면 쓰지 않는다(headers_mismatch) — 열이 바뀌면 보내는 쪽이 --full 로 다시 깐다.
 *   · '=' '+' '-' '@' 로 시작하는 글자는 앞에 ' 를 붙여 수식으로 해석되지 않게 한다.
 *   · 동시에 두 요청이 오면 스크립트 잠금으로 줄 세운다(30초 대기 후 busy).
 */

var MIRROR_SHEETS = { '영상': true, '꿀팁': true };
var MIRROR_MAX_ROWS_PER_CALL = 500;

function doGet() {
  return ContentService.createTextOutput('YouTube 장부 미러 — POST 전용').setMimeType(ContentService.MimeType.TEXT);
}

function doPost(e) {
  var out;
  try {
    out = mirrorHandle_(e);
  } catch (err) {
    out = { ok: false, error: (err && err.mirrorCode) || 'internal', detail: String((err && err.message) || err).slice(0, 300) };
  }
  return ContentService.createTextOutput(JSON.stringify(out)).setMimeType(ContentService.MimeType.JSON);
}

function mirrorFail_(code, msg) {
  var err = new Error(msg || code);
  err.mirrorCode = code;
  return err;
}

function mirrorHandle_(e) {
  var want = PropertiesService.getScriptProperties().getProperty('MIRROR_TOKEN');
  if (!want) throw mirrorFail_('not_configured', '스크립트 속성 MIRROR_TOKEN 이 비어 있습니다');

  var body;
  try {
    body = JSON.parse((e && e.postData && e.postData.contents) || '');
  } catch (x) {
    throw mirrorFail_('bad_request', 'JSON 본문이 아닙니다');
  }
  if (!body || typeof body !== 'object') throw mirrorFail_('bad_request', 'JSON 본문이 아닙니다');
  if (typeof body.token !== 'string' || body.token !== want) throw mirrorFail_('auth', '토큰 불일치');

  var ss = SpreadsheetApp.getActiveSpreadsheet();
  if (body.op === 'ping') {
    var counts = {};
    Object.keys(MIRROR_SHEETS).forEach(function (name) {
      var sh = ss.getSheetByName(name);
      counts[name] = sh ? Math.max(sh.getLastRow() - 1, 0) : 0;
    });
    return { ok: true, counts: counts };
  }

  if (body.op !== 'reset' && body.op !== 'upsert') throw mirrorFail_('bad_request', '알 수 없는 op: ' + body.op);
  if (!MIRROR_SHEETS[body.sheet]) throw mirrorFail_('bad_request', '허용되지 않은 탭: ' + body.sheet);
  var headers = body.headers;
  if (!Array.isArray(headers) || headers.length < 2 || headers[0] !== 'record_id') throw mirrorFail_('bad_request', 'headers 형식 오류');

  var lock = LockService.getScriptLock();
  if (!lock.tryLock(30000)) throw mirrorFail_('busy', '다른 요청 처리 중');
  try {
    var sh = ss.getSheetByName(body.sheet) || ss.insertSheet(body.sheet);
    if (body.op === 'reset') {
      sh.clear();
      mirrorWriteHeaders_(sh, headers);
      return { ok: true, sheet: body.sheet, total: 0 };
    }
    var rows = body.rows;
    if (!Array.isArray(rows) || rows.length > MIRROR_MAX_ROWS_PER_CALL) throw mirrorFail_('bad_request', 'rows 형식 오류 또는 ' + MIRROR_MAX_ROWS_PER_CALL + '행 초과');
    var r = mirrorUpsert_(sh, headers, rows);
    r.ok = true;
    r.sheet = body.sheet;
    r.total = Math.max(sh.getLastRow() - 1, 0);
    return r;
  } finally {
    lock.releaseLock();
  }
}

function mirrorWriteHeaders_(sh, headers) {
  var n = headers.length;
  sh.getRange(1, 1, sh.getMaxRows(), 1).setNumberFormat('@');   // record_id 는 언제나 글자
  sh.getRange(1, 1, 1, n).setValues([headers]).setFontWeight('bold');
  sh.setFrozenRows(1);
  sh.getRange(1, 1, sh.getMaxRows(), n).setWrapStrategy(SpreadsheetApp.WrapStrategy.CLIP);
}

function mirrorSafe_(v) {
  if (v === null || v === undefined) return '';
  if (typeof v === 'string' && /^[=+\-@]/.test(v)) return "'" + v;
  return v;
}

function mirrorUpsert_(sh, headers, rows) {
  var n = headers.length;
  var last = sh.getLastRow();
  if (last === 0) {
    mirrorWriteHeaders_(sh, headers);
    last = 1;
  } else {
    var have = sh.getRange(1, 1, 1, n).getValues()[0];
    for (var i = 0; i < n; i++) {
      if (String(have[i]) !== String(headers[i])) throw mirrorFail_('headers_mismatch', (i + 1) + '열 머리글 "' + have[i] + '" ≠ "' + headers[i] + '"');
    }
  }

  var pos = {};
  if (last > 1) {
    var ids = sh.getRange(2, 1, last - 1, 1).getValues();
    for (var j = 0; j < ids.length; j++) pos[String(ids[j][0])] = j + 2;
  }

  var appends = [], appendIdx = {}, updated = 0;
  for (var k = 0; k < rows.length; k++) {
    var row = rows[k];
    if (!Array.isArray(row) || row.length !== n || !row[0]) throw mirrorFail_('bad_request', (k + 1) + '번째 행 형식 오류');
    var id = String(row[0]);
    var vals = row.map(mirrorSafe_);
    if (pos[id]) {
      sh.getRange(pos[id], 1, 1, n).setValues([vals]);
      updated++;
    } else if (appendIdx[id] !== undefined) {
      appends[appendIdx[id]] = vals;          // 같은 요청 안에 같은 id 가 두 번 오면 뒤의 것
    } else {
      appendIdx[id] = appends.length;
      appends.push(vals);
    }
  }
  if (appends.length) {
    var need = last + appends.length - sh.getMaxRows();
    if (need > 0) sh.insertRowsAfter(sh.getMaxRows(), need);   // 새 탭은 1,000행 — 넘치면 늘린다
    var target = sh.getRange(last + 1, 1, appends.length, n);
    sh.getRange(last + 1, 1, appends.length, 1).setNumberFormat('@');
    target.setWrapStrategy(SpreadsheetApp.WrapStrategy.CLIP);
    target.setValues(appends);
  }
  return { inserted: appends.length, updated: updated };
}
