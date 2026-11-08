#!/usr/bin/env node
// [CC-1109-B] lib/proposals.js 회귀 테스트 — 임시 폴더(제안 폴더·스킬 폴더)만 쓴다. 네트워크 0회.
//   /opt/homebrew/bin/node scripts/test_proposals.js
'use strict';
const fs = require('fs');
const os = require('os');
const path = require('path');
const P = require('../lib/proposals');

const results = [];
function check(name, cond, detail) {
  results.push(!!cond);
  console.log(`  ${cond ? 'PASS' : 'FAIL'}  ${name}${!cond && detail !== undefined ? '  — ' + JSON.stringify(detail).slice(0, 300) : ''}`);
}

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'prop-'));
const dir = path.join(tmp, 'proposals'), skills = path.join(tmp, 'skills');
fs.mkdirSync(path.join(dir, 'trial'), { recursive: true });
fs.mkdirSync(skills);
const O = { dir, skillsDir: skills, now: '2026-11-09T01:02:03Z' };
const md = slug => `---\nname: wiki-${slug}\ndescription: d\n---\n본문 한글\n`;
const sk = (id, slug, over = {}) => ({ id, kind: 'skill', area: 'dev', title: 'T-' + id, why: 'w', evidence: ['v1'], effort: '낮음', skill: { slug, skill_md: md(slug) }, status: 'new', ...over });
const wr = (rel, o) => fs.writeFileSync(path.join(dir, rel), typeof o === 'string' ? o : JSON.stringify(o));
const snap = () => JSON.stringify([fs.readdirSync(skills), fs.existsSync(path.join(dir, 'decisions.json')) && fs.readFileSync(path.join(dir, 'decisions.json'), 'utf8')]);

wr('20261109.json', { created_at: '2026-11-09T00:00:00Z', proposals: [
  sk('20261109-1', 'alpha-skill'), sk('20261109-2', 'beta-skill'), sk('20261109-3', 'gamma-skill'),
  sk('20261109-4', 'wiki-pre'), sk('20261109-5', 'name-mis', { skill: { slug: 'name-mis', skill_md: md('other') } }),
  sk('20261109-6', 'no-fm', { skill: { slug: 'no-fm', skill_md: 'name: wiki-no-fm\n' } }),
  sk('20261109-7', 'Bad_Slug'),
  { id: '20261109-8', kind: 'action', area: 'work', title: 'A8', why: 'w', evidence: ['v1'], effort: '중간', action_prompt: 'do it' }] });
wr('trial/20261108-152234.json', { created_at: '2026-11-08T15:22:34Z', proposals: [sk('trial-20261108-152234-1', 'trial-skill')] });
wr('20261108.json', '{broken');
wr('notes.json', '{}');

try {
  console.log('--- 1 list');
  let L = P.list(O);
  check('날짜+trial 합침 · 최신 먼저 · trial 표시', L.items.length === 9 && L.items[0].id === '20261109-1' && L.items[8].trial === true && L.items[8].date === '2026-11-08T15:22:34Z', L.items.map(i => i.id));
  check('깨진 파일 → errors · notes.json 무시 · counts', L.errors.join() === '20261108.json' && L.counts.new === 9, [L.errors, L.counts]);

  console.log('--- 2 스킬 승인');
  let r = P.decide('20261109-1', 'approve', '  좋음 ', O);
  const target = path.join(skills, 'wiki-alpha-skill');
  check('승인 200 · installed', r.ok && r.code === 200 && r.status === 'approved' && r.installed === target, r);
  check('SKILL.md 바이트 동일', Buffer.compare(fs.readFileSync(path.join(target, 'SKILL.md')), Buffer.from(md('alpha-skill'))) === 0);
  const dj = JSON.parse(fs.readFileSync(path.join(dir, 'decisions.json'), 'utf8'));
  check('decisions.json 에 installed·사유 trim', dj.decisions['20261109-1'].installed === target && dj.decisions['20261109-1'].reason === '좋음', dj);
  L = P.list(O);
  check('list 에 상태 합침', L.items[0].status === 'approved' && L.items[0].installed === target && L.counts.approved === 1 && L.counts.new === 8, L.counts);

  console.log('--- 3 중복·덮어쓰기 금지');
  r = P.decide('20261109-1', 'approve', '', O);
  check('같은 id 재승인 → 409 already', r.code === 409 && r.error === 'already', r);
  fs.mkdirSync(path.join(skills, 'wiki-beta-skill'));
  fs.writeFileSync(path.join(skills, 'wiki-beta-skill', 'SKILL.md'), 'ORIGINAL');
  r = P.decide('20261109-2', 'approve', '', O);
  check('대상 폴더 있음 → 409 exists · 내용 불변', r.code === 409 && r.error === 'exists' && fs.readFileSync(path.join(skills, 'wiki-beta-skill', 'SKILL.md'), 'utf8') === 'ORIGINAL', r);
  fs.rmSync(path.join(skills, 'wiki-beta-skill'), { recursive: true });

  console.log('--- 4 검증 실패 → 변화 없음');
  const before = snap();
  const codes = ['20261109-4', '20261109-5', '20261109-6', '20261109-7'].map(id => P.decide(id, 'approve', '', O).code);
  check('wiki- 접두 · name 불일치 · --- 아님 · slug 위반 → 400 · 변화 0', codes.every(c => c === 400) && snap() === before, codes);

  console.log('--- 5 skillsDir 없음');
  const miss = path.join(tmp, 'nope');
  r = P.decide('20261109-3', 'approve', '', { ...O, skillsDir: miss });
  check('409 skills_dir_missing · 폴더 안 만듦', r.code === 409 && r.error === 'skills_dir_missing' && !fs.existsSync(miss), r);

  console.log('--- 6 내용 인자 없음');
  check('decide 인자 4개(id, decision, reason, opts) — 내용 받는 자리 없음', P.decide.length === 4);

  console.log('--- 7 되돌리기');
  r = P.decide('20261109-1', 'undo', '', O);
  check('휴지통(dir/_trash/…-wiki-slug) 으로 이동', r.ok && r.status === 'new' && r.trashed.startsWith(path.join(dir, '_trash') + path.sep) && r.trashed.endsWith('-wiki-alpha-skill') && fs.existsSync(path.join(r.trashed, 'SKILL.md')) && !fs.existsSync(target), r);
  const dj2 = JSON.parse(fs.readFileSync(path.join(dir, 'decisions.json'), 'utf8'));
  check('상태 new · undone 1줄', P.list(O).items[0].status === 'new' && dj2.undone.length === 1 && !dj2.decisions['20261109-1'], dj2);
  r = P.decide('20261109-1', 'undo', '', O);
  check('기록 없음 → 409 nothing', r.code === 409 && r.error === 'nothing', r);
  P.decide('20261109-1', 'approve', '', O);
  fs.rmSync(target, { recursive: true });
  r = P.decide('20261109-1', 'undo', '', O);
  check('폴더 이미 없음 → missing:true', r.ok && r.missing === true && !r.trashed, r);

  console.log('--- 8 보류·거절·오류');
  r = P.decide('20261109-3', 'hold', '', O);
  check('보류 200', r.ok && r.status === 'held', r);
  check('같은 결정 반복 → 409 already', P.decide('20261109-3', 'hold', '', O).code === 409);
  r = P.decide('20261109-3', 'reject', '필요 없음', O);
  const rec = JSON.parse(fs.readFileSync(path.join(dir, 'decisions.json'), 'utf8')).decisions['20261109-3'];
  check('거절 사유 저장 · history 에 보류', r.status === 'rejected' && rec.reason === '필요 없음' && rec.history[0].decision === 'held', rec);
  check('사유 301자 → 400', P.decide('20261109-8', 'reject', 'x'.repeat(301), O).code === 400);
  check('사유 300자 통과', P.decide('20261109-8', 'reject', 'x'.repeat(300), O).ok);
  check('잘못된 decision → 400', P.decide('20261109-8', 'delete', '', O).code === 400);
  check('없는 id → 404', P.decide('20261109-9', 'hold', '', O).code === 404);
  check('ID_RE 위반 → 400', ['../x', '2026110-1', 'x-1', '20261109-123', 20261109].every(i => P.decide(i, 'hold', '', O).code === 400));
  r = P.decide('20261109-8', 'undo', '', O);
  check('적용 아이디어 승인은 기록만', P.decide('20261109-8', 'approve', '', O).installed === undefined && r.ok);

  console.log('--- 9 writeAllowed');
  const good = { host: 'localhost:3000', origin: 'http://localhost:3000', 'content-type': 'application/json; charset=utf-8' };
  check('정상 true', P.writeAllowed(good, 3000) && P.writeAllowed({ ...good, host: '127.0.0.1:3000', origin: 'http://127.0.0.1:3000' }, 3000));
  check('Origin 없음 · 다른 Origin · Host 다름 · text/plain → false',
    !P.writeAllowed({ ...good, origin: undefined }, 3000) && !P.writeAllowed({ ...good, origin: 'http://evil.com' }, 3000)
    && !P.writeAllowed({ ...good, host: 'evil.com:3000' }, 3000) && !P.writeAllowed({ ...good, 'content-type': 'text/plain' }, 3000));

  console.log('--- 10 wiki_lan_server.js');
  check('wiki_lan_server.js 에 proposals 없음', !/proposals/i.test(fs.readFileSync(path.join(__dirname, '..', 'wiki_lan_server.js'), 'utf8')));

  console.log('--- 12 name 줄 정규식 · 깨진 decisions.json');
  wr('20261110.json', { created_at: '2026-11-10T00:00:00Z', proposals: [sk('20261110-1', 'nl-skill', { skill: { slug: 'nl-skill', skill_md: '---\nname:\nwiki-nl-skill\n---\n' } })] });
  check('name:\\nwiki-x → 400', P.decide('20261110-1', 'approve', '', O).code === 400);
  fs.writeFileSync(path.join(dir, 'decisions.json'), '{broken');
  let threw = false; try { P.list(O); } catch (e) { threw = true; }
  check('깨진 decisions.json → list 가 던진다(server 가 500 으로 받는다)', threw);
  check('깨진 decisions.json → decide 는 500 · 파일 그대로', P.decide('20261109-3', 'hold', '', O).code === 500 && fs.readFileSync(path.join(dir, 'decisions.json'), 'utf8') === '{broken');
  fs.rmSync(path.join(dir, 'decisions.json'));

  console.log('--- 11 decisions.json 쓰기 실패');
  fs.mkdirSync(path.join(dir, 'decisions.json.tmp'));
  const s0 = fs.readdirSync(skills).join();
  r = P.decide('20261109-3', 'approve', '', { ...O }); // rejected → approve, 스킬 설치 시도 후 쓰기 실패
  check('500 · 설치한 스킬 폴더 남지 않음', r.code === 500 && fs.readdirSync(skills).join() === s0, [r, fs.readdirSync(skills)]);
} catch (e) {
  check('예외 없이 끝남', false, e.stack);
} finally {
  fs.rmSync(tmp, { recursive: true, force: true });
}
const ok = results.filter(Boolean).length;
console.log(`\n${ok}/${results.length} PASS`);
process.exit(ok === results.length ? 0 : 1);
