#!/usr/bin/env node
// 테스트 전용 — gas/sheet_mirror.gs 를 실제 코드 그대로 vm 에 올리고, 구글 시트·Apps Script 를 흉내 낸다.
// scripts/test_sheet_mirror.py 가 띄운다. 네트워크는 127.0.0.1 만. 실제 구글에는 아무 요청도 하지 않는다.
//
//   POST /exec        → doPost 실행 → 302 /echo/<n> (Apps Script 웹앱과 같은 방식)
//   GET  /echo/<n>    → 결과 JSON
//   POST /__ctl       → { queue:[{status}|{html:true}|{busy:true}], token, setCell:{sheet,row,col,value}, deleteRow:{sheet,row} }
//   GET  /__state     → { sheets:{탭:[[…],…]}, formulas:[…], log:[op…], posts:n }
'use strict';
const http = require('http');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const GS = fs.readFileSync(path.join(__dirname, '..', 'gas', 'sheet_mirror.gs'), 'utf8');
const MAX_ROWS_INIT = Number(process.env.FAKE_GAS_MAXROWS || 1000);   // 실제 새 탭은 1,000행

let token = process.env.FAKE_GAS_TOKEN || 'test-token';
let queue = [];
const results = [];
const opLog = [];
const formulas = [];
let posts = 0;

class Range {
  constructor(sh, r, c, nr, nc) { Object.assign(this, { sh, r, c, nr, nc }); }
  _check() {
    if (this.r < 1 || this.c < 1 || this.r + this.nr - 1 > this.sh.maxRows) {
      throw new Error(`범위가 시트 밖: ${this.r}+${this.nr} > ${this.sh.maxRows}`);
    }
  }
  getValues() {
    this._check();
    const out = [];
    for (let i = 0; i < this.nr; i++) {
      const row = this.sh.data[this.r - 1 + i] || [];
      const vals = [];
      for (let j = 0; j < this.nc; j++) vals.push(row[this.c - 1 + j] ?? '');
      out.push(vals);
    }
    return out;
  }
  setValues(v) {
    this._check();
    if (v.length !== this.nr || v.some(r => r.length !== this.nc)) throw new Error('setValues 크기 불일치');
    for (let i = 0; i < this.nr; i++) {
      const ri = this.r - 1 + i;
      this.sh.data[ri] = this.sh.data[ri] || [];
      for (let j = 0; j < this.nc; j++) {
        let x = v[i][j];
        if (typeof x === 'string' && x.startsWith("'")) x = x.slice(1);          // 시트처럼: 앞의 ' 는 '글자로' 표시
        else if (typeof x === 'string' && /^[=+\-@]/.test(x)) formulas.push(x);   // 수식으로 해석됐을 값
        this.sh.data[ri][this.c - 1 + j] = x;
      }
    }
    return this;
  }
  setNumberFormat() { return this; }
  setFontWeight() { return this; }
  setWrapStrategy() { return this; }
}

class Sheet {
  constructor(name) { this.name = name; this.data = []; this.maxRows = MAX_ROWS_INIT; }
  getLastRow() {
    for (let i = this.data.length - 1; i >= 0; i--) {
      if ((this.data[i] || []).some(x => x !== '' && x !== undefined && x !== null)) return i + 1;
    }
    return 0;
  }
  getMaxRows() { return this.maxRows; }
  insertRowsAfter(after, n) { this.maxRows += n; return this; }
  getRange(r, c, nr = 1, nc = 1) { return new Range(this, r, c, nr, nc); }
  clear() { this.data = []; return this; }
  setFrozenRows() { return this; }
}

const sheets = new Map();
const ctx = {
  ContentService: {
    MimeType: { TEXT: 'text', JSON: 'json' },
    createTextOutput(s) { return { content: s, setMimeType() { return this; } }; },
  },
  PropertiesService: { getScriptProperties: () => ({ getProperty: (k) => (k === 'MIRROR_TOKEN' ? token : null) }) },
  LockService: { getScriptLock: () => ({ tryLock: () => true, releaseLock() {} }) },
  SpreadsheetApp: {
    WrapStrategy: { CLIP: 'CLIP' },
    getActiveSpreadsheet: () => ({
      getSheetByName: (n) => sheets.get(n) || null,
      insertSheet: (n) => { const s = new Sheet(n); sheets.set(n, s); return s; },
    }),
  },
  JSON, String, Array, Object, Math, Error,
};
vm.createContext(ctx);
vm.runInContext(GS, ctx, { filename: 'sheet_mirror.gs' });

function readBody(req) {
  return new Promise((resolve) => { let b = ''; req.on('data', c => b += c); req.on('end', () => resolve(b)); });
}

const server = http.createServer(async (req, res) => {
  const body = await readBody(req);
  if (req.method === 'POST' && req.url === '/__ctl') {
    const c = JSON.parse(body || '{}');
    if (c.queue) queue = c.queue.slice();
    if (c.token !== undefined) token = c.token;
    if (c.setCell) { const s = sheets.get(c.setCell.sheet); s.data[c.setCell.row - 1][c.setCell.col - 1] = c.setCell.value; }
    if (c.deleteRow) { const s = sheets.get(c.deleteRow.sheet); s.data.splice(c.deleteRow.row - 1, 1); }
    res.writeHead(200, { 'Content-Type': 'application/json' }); res.end('{"ok":true}'); return;
  }
  if (req.method === 'GET' && req.url === '/__state') {
    const out = {};
    for (const [n, s] of sheets) out[n] = s.data.slice(0, s.getLastRow()).map(r => r.slice());
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ sheets: out, formulas, log: opLog, posts }));
    return;
  }
  if (req.method === 'POST' && req.url.startsWith('/exec')) {
    posts++;
    const inj = queue.shift();
    if (inj && inj.status) { res.writeHead(inj.status, { 'Content-Type': 'text/plain' }); res.end('err'); return; }
    if (inj && inj.html) { res.writeHead(200, { 'Content-Type': 'text/html' }); res.end('<!DOCTYPE html><html>로그인</html>'); return; }
    let out;
    if (inj && inj.busy) out = JSON.stringify({ ok: false, error: 'busy' });
    else {
      try { const p = JSON.parse(body); opLog.push(p.op + (p.sheet ? ':' + p.sheet : '') + (p.rows ? ':' + p.rows.length : '')); } catch { opLog.push('?'); }
      out = ctx.doPost({ postData: { contents: body } }).content;
    }
    results.push(out);
    res.writeHead(302, { Location: `/echo/${results.length - 1}` }); res.end(); return;
  }
  if (req.method === 'GET' && req.url.startsWith('/echo/')) {
    const n = Number(req.url.slice('/echo/'.length));
    res.writeHead(200, { 'Content-Type': 'application/json' }); res.end(results[n]); return;
  }
  res.writeHead(404); res.end('no');
});
server.listen(0, '127.0.0.1', () => { console.log('PORT ' + server.address().port); });
