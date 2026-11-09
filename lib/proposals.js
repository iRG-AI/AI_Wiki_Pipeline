// 매일 Wiki 검토 제안함 [CC-1109-B] — 제안 파일(skill_review.py 가 씀)을 읽고 결정(승인·보류·거절·되돌리기)을 decisions.json 에 쓴다.
// 의존성 0. 설치할 내용은 저장된 제안 파일에서만 가져온다(함수 인자로 내용을 받지 않는다).
const fs = require('fs');
const os = require('os');
const path = require('path');

const ID_RE = /^(trial-\d{8}-\d{6}|\d{8})-\d{1,2}$/;
const SLUG_RE = /^[a-z0-9-]{3,40}$/;
const STATUS = { approve: 'approved', hold: 'held', reject: 'rejected' };

function paths(opts = {}) {
  const dir = opts.dir || path.join(__dirname, '..', 'data', 'proposals');
  const skillsDir = opts.skillsDir || process.env.SKILL_REVIEW_SKILLS_DIR || path.join(os.homedir(), '.claude', 'skills');
  return { dir, skillsDir, now: opts.now ? new Date(opts.now) : new Date() };
}

function readJson(p) {
  return JSON.parse(fs.readFileSync(p, 'utf8'));
}

function loadProposals(dir) {
  const items = [], errors = [], reviews = [];
  const files = [];
  for (const [sub, re] of [['', /^\d{8}\.json$/], ['trial', /^\d{8}-\d{6}\.json$/]]) {
    let names = [];
    try { names = fs.readdirSync(path.join(dir, sub)); } catch (e) { continue; }
    for (const n of names) if (re.test(n)) files.push({ n, p: path.join(dir, sub, n), trial: !!sub });
  }
  for (const f of files) {
    try {
      const d = readJson(f.p);
      if (!d || !Array.isArray(d.proposals)) throw new Error('proposals 없음');
      for (const p of d.proposals) items.push({ ...p, date: d.created_at || null, trial: f.trial, _sort: f.n });
      if (Array.isArray(d.tip_review)) {
        const ri = d.tip_review.filter(r => r && typeof r.id === 'string' && typeof r.reason === 'string' && (r.verdict === 'proposed' || r.verdict === 'skipped'))
          .map(r => ({ id: r.id, verdict: r.verdict, reason: r.reason }));
        if (ri.length) reviews.push({ file: f.n, date: d.created_at || null, trial: f.trial, items: ri });
      }
    } catch (e) { errors.push(f.n); }
  }
  items.sort((a, b) => (a._sort < b._sort ? 1 : a._sort > b._sort ? -1 : 0));
  items.forEach(i => delete i._sort);
  reviews.sort((a, b) => (a.file < b.file ? 1 : a.file > b.file ? -1 : 0));
  return { items, errors, reviews };
}

function loadDecisions(dir) {
  let d;
  try { d = readJson(path.join(dir, 'decisions.json')); } catch (e) {
    if (e.code === 'ENOENT') return { version: 1, decisions: {}, undone: [] };
    throw e; // 깨진 파일을 빈 것으로 보고 덮어쓰면 기록이 사라진다
  }
  return { version: 1, decisions: d.decisions || {}, undone: d.undone || [] };
}

function saveDecisions(dir, d) {
  const p = path.join(dir, 'decisions.json');
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(p + '.tmp', JSON.stringify(d, null, 2), 'utf8');
  fs.renameSync(p + '.tmp', p);
}

function list(opts) {
  const { dir } = paths(opts);
  const { items, errors, reviews } = loadProposals(dir);
  const dec = loadDecisions(dir).decisions;
  const counts = { new: 0, held: 0, approved: 0, rejected: 0 };
  for (const i of items) {
    const d = dec[i.id];
    i.status = d ? d.decision : 'new';
    i.reason = d ? d.reason : '';
    i.at = d ? d.at : null;
    i.installed = d ? d.installed : null;
    counts[i.status in counts ? i.status : 'new']++;
  }
  return { items, errors, counts, reviews };
}

const fail = (code, error) => ({ ok: false, code, error });
const stamp = now => now.toISOString().replace(/[-:]/g, '').replace(/\.\d+Z$/, '').replace('T', '-');

function decide(id, decision, reason, opts) {
  const { dir, skillsDir, now } = paths(opts);
  if (decision !== 'undo' && !STATUS[decision]) return fail(400, 'bad_decision');
  if (typeof id !== 'string' || !ID_RE.test(id)) return fail(400, 'bad_id');
  reason = String(reason == null ? '' : reason).trim();
  if (reason.length > 300) return fail(400, 'reason_too_long');
  try {
    const prop = loadProposals(dir).items.find(i => i.id === id);
    if (!prop) return fail(404, 'not_found');
    const store = loadDecisions(dir);
    const cur = store.decisions[id];
    const at = now.toISOString();

    if (decision === 'undo') {
      if (!cur) return fail(409, 'nothing');
      let trashed, from;
      if (cur.installed) {
        const root = path.resolve(skillsDir);
        from = path.resolve(cur.installed);
        if (path.dirname(from) !== root || !path.basename(from).startsWith('wiki-')) return fail(500, 'bad_installed_path');
        if (fs.existsSync(from)) {
          trashed = path.join(dir, '_trash', stamp(now) + '-' + path.basename(from));
          fs.mkdirSync(path.dirname(trashed), { recursive: true });
          fs.renameSync(from, trashed);
        }
      }
      delete store.decisions[id];
      store.undone.push({ ...cur, undone_at: at });
      try { saveDecisions(dir, store); } catch (e) {
        if (trashed) fs.renameSync(trashed, from);
        throw e;
      }
      const r = { ok: true, code: 200, status: 'new' };
      if (cur.installed && !trashed) r.missing = true;
      if (trashed) r.trashed = trashed;
      return r;
    }

    const next = STATUS[decision];
    if (cur && cur.decision === next) return fail(409, 'already');
    if (cur && cur.installed) return fail(409, 'undo_first'); // 설치된 스킬은 되돌리기를 거쳐야 한다
    let installed = null;
    if (next === 'approved' && prop.kind === 'skill') {
      const s = prop.skill || {};
      const md = s.skill_md;
      if (typeof s.slug !== 'string' || !SLUG_RE.test(s.slug) || s.slug.startsWith('wiki-')) return fail(400, 'bad_slug');
      const fm = typeof md === 'string' && md.startsWith('---\n') ? md.slice(4).split('\n---')[0] : '';
      if (!new RegExp('^name:[ \\t]*wiki-' + s.slug + '[ \\t]*$', 'm').test(fm)) return fail(400, 'bad_skill_md');
      let st; try { st = fs.statSync(skillsDir); } catch (e) { /* 없음 */ }
      if (!st || !st.isDirectory()) return fail(409, 'skills_dir_missing');
      installed = path.join(skillsDir, 'wiki-' + s.slug);
      try { fs.lstatSync(installed); return fail(409, 'exists'); } catch (e) { if (e.code !== 'ENOENT') throw e; }
      fs.mkdirSync(installed);
      try { fs.writeFileSync(path.join(installed, 'SKILL.md'), md, { flag: 'wx' }); } catch (e) {
        fs.rmSync(installed, { recursive: true, force: true });
        throw e;
      }
    }
    const history = cur ? [...(cur.history || []), { decision: cur.decision, at: cur.at, reason: cur.reason }] : [];
    store.decisions[id] = { id, title: prop.title, kind: prop.kind, decision: next, reason, at, installed, history };
    try { saveDecisions(dir, store); } catch (e) {
      if (installed) fs.rmSync(installed, { recursive: true, force: true });
      throw e;
    }
    const r = { ok: true, code: 200, status: next };
    if (installed) r.installed = installed;
    return r;
  } catch (e) {
    return fail(500, 'internal');
  }
}

// 다른 사이트 브라우저를 통한 요청·DNS 리바인딩 차단: Host·Origin·Content-Type 셋 다 맞아야 한다.
function writeAllowed(headers, port) {
  const h = String(headers.host || '').toLowerCase();
  const o = String(headers.origin || '').toLowerCase();
  const hosts = [`localhost:${port}`, `127.0.0.1:${port}`];
  return hosts.includes(h) && !!o && hosts.some(x => o === 'http://' + x)
    && String(headers['content-type'] || '').toLowerCase().startsWith('application/json');
}

module.exports = { list, decide, writeAllowed, ID_RE, SLUG_RE };
