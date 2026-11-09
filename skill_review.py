#!/usr/bin/env python3
"""매일 Wiki 검토 1단계 [CC-1109-A] — 그날 들어온 영상·꿀팁을 Claude 가 읽고 스킬/적용 제안 0~5건을 data/proposals/ 에 JSON 으로 남긴다.

Claude 에게 도구·MCP 를 주지 않는다(프롬프트 → JSON 만). 장부는 읽기 전용. 재시도 없음(실패는 기록하고 끝, 다음 날 같은 기준점에서 다시 본다).

    /opt/homebrew/bin/python3 skill_review.py [--dry-run] [--days=N] [--backfill=DAYS] [--no-notify]
테스트 전용: --db= --out-dir= --profile=   환경변수: CLAUDE_BIN · SKILL_REVIEW_SKILLS_DIR
"""
import copy, glob, json, os, re, subprocess, sys, tempfile, urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(REPO, 'lib'))
import library_db as ldb
import env_util

KST = ZoneInfo('Asia/Seoul')
CLAUDE_TIMEOUT = 900
MAX_ITEMS, SUMMARY_CHARS, MAX_PROPOSALS = 40, 2500, 5
BATCH_CAND, RANK_KEEP, RANK_MIN = 8, 15, 15  # backfill: 묶음당 후보 상한 · 최종 상한 · 순위 호출 기준
SLUG_RE = re.compile(r'^[a-z0-9-]{3,40}$')
SCHEMA = {"type": "object", "required": ["proposals"], "properties": {
    "proposals": {"type": "array", "maxItems": 5, "items": {"type": "object",
        "required": ["kind", "area", "title", "why", "evidence", "effort"], "properties": {
            "kind": {"enum": ["skill", "action"]}, "area": {"enum": ["dev", "work", "knowledge", "content", "invest"]},
            "title": {"type": "string"}, "why": {"type": "string"},
            "evidence": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "effort": {"enum": ["낮음", "중간", "높음"]},
            "skill": {"type": "object", "properties": {"slug": {"type": "string"}, "skill_md": {"type": "string"}}},
            "action_prompt": {"type": "string"}}}},
    "tip_review": {"type": "array", "items": {"type": "object", "required": ["id", "verdict", "reason"], "properties": {
        "id": {"type": "string"}, "verdict": {"enum": ["proposed", "skipped"]}, "reason": {"type": "string"}}}},
    "note": {"type": "string"}}}


def send_telegram(token, chat, text):
    """실행 알림 봇으로 1회 발송(재시도 없음, 20초). 던지지 않고 True/False. 토큰·chat·URL 은 어디에도 쓰지 않는다."""
    try:
        req = urllib.request.Request(f'https://api.telegram.org/bot{token}/sendMessage',
                                     data=json.dumps({'chat_id': chat, 'text': text[:4000]}).encode('utf-8'),
                                     headers={'Content-Type': 'application/json'}, method='POST')
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status == 200
    except Exception:
        return False


def utcnow():
    return datetime.now(timezone.utc)


def iso(dt):
    return dt.strftime('%Y-%m-%dT%H:%M:%S.') + f'{dt.microsecond // 1000:03d}Z'


def read_json(p):
    try:
        with open(p, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def installed_skills():
    root = os.environ.get('SKILL_REVIEW_SKILLS_DIR') or os.path.expanduser('~/.claude/skills')
    names = set()
    for d in glob.glob(os.path.join(root, '*')) + glob.glob(os.path.join(root, 'synced', '*', '*')):
        if os.path.isdir(d):
            names.add(os.path.basename(d))
    return sorted(names)


RANK_SCHEMA = {"type": "object", "required": ["pick"], "properties": {
    "pick": {"type": "array", "items": {"type": "integer"}, "maxItems": 15}, "note": {"type": "string"}}}


def select_targets(conn, since, limit=MAX_ITEMS):
    vids = [dict(r) for r in conn.execute(
        "SELECT record_id,title,channel,topics,video_url,summary_src,summary,created_at FROM videos "
        "WHERE created_at > ? AND coalesce(grade,'')<>'exclude' ORDER BY created_at DESC", (since,))]
    tips = [dict(r) for r in conn.execute(
        "SELECT record_id,title,url,category,tags,memo,created_at FROM tips WHERE created_at > ? ORDER BY created_at DESC", (since,))]
    if limit:
        truncated = max(0, len(vids) - limit) + max(0, len(tips) - limit)
        vids, tips = vids[:limit], tips[:limit]
    else:
        truncated = 0
    for v in vids:
        v['summary'] = (v['summary'] or '')[:SUMMARY_CHARS]
    return vids, tips, truncated


def recent_context(out_dir, now):
    titles, rejects = [], []
    today = now.astimezone(KST).date()
    for p in sorted(glob.glob(os.path.join(out_dir, '[0-9]' * 8 + '.json'))) + sorted(glob.glob(os.path.join(out_dir, 'trial', '[0-9]' * 8 + '-' + '[0-9]' * 6 + '.json'))):
        age = (today - datetime.strptime(os.path.basename(p)[:8], '%Y%m%d').date()).days
        if 0 <= age <= 6:
            titles += [x.get('title', '') for x in (read_json(p) or {}).get('proposals', [])]
    titles = list(dict.fromkeys(titles))
    dec = (read_json(os.path.join(out_dir, 'decisions.json')) or {}).get('decisions')
    items = [x for x in (dec.values() if isinstance(dec, dict) else []) if isinstance(x, dict) and x.get('decision') == 'rejected']
    for x in sorted(items, key=lambda x: x.get('at') or '', reverse=True)[:30]:
        rejects.append(f"{x.get('title', '')}: {x.get('reason') or '(사유 없음)'}")
    return titles, rejects


def build_prompt(profile, skills, titles, rejects, vids, tips, n=MAX_PROPOSALS):
    L = ["당신은 대표님의 매일 Wiki 검토 담당입니다. 아래는 오늘 새로 들어온 영상 요약과 꿀팁입니다.",
         f"대표님께 실제로 쓸모 있는 스킬(SKILL.md) 또는 적용 아이디어를 0~{n}건 제안하세요.", "",
         "## 대표님 프로필", profile.strip(), "",
         "## 이미 설치된 스킬 이름", ', '.join(skills) or '(없음)', "",
         "## 최근 7일 제안 제목", '\n'.join('- ' + t for t in titles) or '(없음)', "",
         "## 최근 거절 사유", '\n'.join('- ' + t for t in rejects) or '(없음)', "",
         "## 규칙",
         f"- 제안 0~{n}건. 억지로 채우지 마세요(\"오늘은 없음\"도 정상, proposals 를 빈 배열로). 판매·일반론·뉴스는 제외.",
         "- 설치된 스킬, 최근 제안, 거절된 것과 겹치면 제외.",
         "- area: dev=개발 자동화 · work=회사 업무 · knowledge=지식관리 · content=콘텐츠·영상 · invest=투자·자산관리.",
         "- 꿀팁은 대표님이 직접 골라 남긴 자료라 영상보다 우선한다. 정보가 얇아도 제목·메모·URL 로 무엇인지 알 수 있으면 후보로 본다. 내용을 알 수 없으면(예: 「(제목 미확인)」 인스타 릴스) 버리지 말고 kind=action 「원문 확인 후 스킬화」 제안이 맞는지 판단한다. 영상 요약과 같은 주제면 둘 다 evidence 로 묶는다.",
         "- tip_review: 대상 꿀팁마다 하나씩 — 제안에 썼으면 verdict=proposed, 아니면 skipped 와 이유 한 줄.",
         "- evidence 는 아래 목록의 record_id 만, 1개 이상.",
         "- kind=skill 이면 skill.slug(정규식 ^[a-z0-9-]{3,40}$, 접두 없이)와 skill.skill_md(완전한 SKILL.md: 프론트매터 `name: wiki-<slug>` · `description:`(언제 쓰는지, 호출 문구 포함), 본문은 한국어 절차). 비밀값·개인 경로 금지.",
         "- kind=action 이면 action_prompt(대표님이 Claude Code 에 그대로 붙여 넣을 지시 한 단락).",
         "- 결과는 지정된 JSON 스키마로만 답하세요.", "", "## 오늘의 영상"]
    for v in vids:
        L.append(f"### [{v['record_id']}] {v['title']} ({v['channel']}) topics={v['topics']} {v['video_url'] or ''}\n{v['summary']}")
    L.append("\n## 대표님이 직접 남긴 꿀팁 (우선)")
    for t in tips:
        L.append(f"- [{t['record_id']}] {t['title']} | {t['url']} | {t['category']} | {t['tags']} | {t['memo']}")
    return '\n'.join(L)


def call_claude(prompt, schema=SCHEMA, key='proposals'):
    claude = os.environ.get('CLAUDE_BIN') or os.path.expanduser('~/.local/bin/claude')
    with tempfile.TemporaryDirectory() as empty:
      try:
        p = subprocess.run([claude, '-p', '--model', 'opus', '--output-format', 'json', '--json-schema', json.dumps(schema),
                            '--tools', '', '--strict-mcp-config', '--no-session-persistence'],
                           input=prompt, cwd=empty, timeout=CLAUDE_TIMEOUT, capture_output=True, text=True)
      except subprocess.TimeoutExpired as e:
        err = e.stderr.decode('utf-8', 'replace') if isinstance(e.stderr, bytes) else (e.stderr or '')
        raise RuntimeError('claude timeout: ' + ' '.join(err[:200].split()))
    if p.returncode != 0:
        raise RuntimeError(f'claude exit {p.returncode}: ' + ' '.join((p.stderr or '')[:200].split()))
    out = json.loads(p.stdout)
    if out.get('is_error'):
        raise RuntimeError('claude is_error')
    data = out.get('structured_output')
    if data is None:
        data = json.loads(out['result'])
    if not isinstance(data, dict) or not isinstance(data.get(key), list):
        raise ValueError(key + ' 없음')
    return data


def validate(p, allowed):
    """None = 통과, 아니면 버리는 사유."""
    if not isinstance(p, dict):
        return 'not_object'
    for k in ('kind', 'area', 'title', 'why', 'effort'):
        if not isinstance(p.get(k), str) or not p[k]:
            return f'missing:{k}'
    if p['kind'] not in ('skill', 'action') or p['area'] not in ('dev', 'work', 'knowledge', 'content', 'invest') or p['effort'] not in ('낮음', '중간', '높음'):
        return 'enum'
    ev = p.get('evidence')
    if not isinstance(ev, list) or not ev:
        return 'evidence_empty'
    if any(e not in allowed for e in ev):
        return 'evidence_unknown'
    if p['kind'] == 'skill':
        s = p.get('skill')
        if not isinstance(s, dict) or not isinstance(s.get('slug'), str) or not isinstance(s.get('skill_md'), str):
            return 'skill_missing'
        if not SLUG_RE.match(s['slug']) or s['slug'].startswith('wiki-'):
            return 'slug'
        md = s['skill_md']
        fm = md[4:].split('\n---')[0] if md.startswith('---\n') else ''
        if not re.search(r'^name:[ \t]*wiki-' + re.escape(s['slug']) + r'[ \t]*$', fm, re.M):
            return 'skill_md'
    elif not isinstance(p.get('action_prompt'), str) or not p['action_prompt'].strip():
        return 'action_prompt_missing'
    return None


def clean_tip_review(raw, tip_ids):
    """대상 꿀팁 id 의 올바른 모양 항목만. 없거나 틀리면 빈 배열(실패 아님)."""
    if not isinstance(raw, list):
        return []
    out, seen = [], set()
    for x in raw:
        if (isinstance(x, dict) and isinstance(x.get('id'), str) and x['id'] in tip_ids and x['id'] not in seen
                and x.get('verdict') in ('proposed', 'skipped') and isinstance(x.get('reason'), str)):
            seen.add(x['id'])
            out.append({'id': x['id'], 'verdict': x['verdict'], 'reason': x['reason'][:200]})
    return out[:len(tip_ids)]


def rank_prompt(profile, cands, tip_ids=()):
    L = ["## 순위 매기기", "아래 후보 중 겹치는 것은 하나만 남기고 대표님께 가장 쓸모 있는 순서로 최대 15개 번호를 고르세요(pick). 번호만 답하세요.",
         "꿀팁(대표님이 직접 남긴 자료)이 evidence 에 들어간 후보(꿀팁근거: 예)를 우선합니다.", "",
         "## 대표님 프로필", profile.strip(), "", "## 후보"]
    for i, c in enumerate(cands, 1):
        L.append(f"{i}. [{c['kind']}/{c['area']}] {c['title']} | {c['why']} | 품 {c['effort']} | 꿀팁근거: {'예' if any(e in tip_ids for e in c['evidence']) else '아니오'}"
                 + (f"\n{c['skill']['skill_md'][:600]}" if c['kind'] == 'skill' else ''))
    return '\n'.join(L)


def run_backfill(vids, tips, prompts, profile, res):
    """묶음마다 claude 1회(연속 2회 실패면 중단) → 후보가 15건 넘으면 순위 호출 1회(번호만). 반환 (후보, note, 묶음 수)."""
    schema = copy.deepcopy(SCHEMA)
    schema['properties']['proposals']['maxItems'] = BATCH_CAND
    cands, notes, fails, reviews = [], [], 0, []
    for i, (v, t, prompt) in enumerate(prompts):
        try:
            data = call_claude(prompt, schema)
            allowed = {x['record_id'] for x in v + t}
            good = [p for p in data['proposals'] if validate(p, allowed) is None]
            rev = clean_tip_review(data.get('tip_review'), {x['record_id'] for x in t})
            fails = 0
        except Exception as e:
            res['batch_errors'].append(f'{i + 1}: {type(e).__name__}: {str(e)[:150]}')
            fails += 1
            if fails >= 2:
                break
            continue
        res['batches'] += 1
        notes.append(data.get('note') or '')
        cands += good
        reviews += rev
    res['candidates_total'] = len(cands)
    if len(cands) > RANK_MIN:
        try:
            pick = call_claude(rank_prompt(profile, cands, {x['record_id'] for x in tips}), RANK_SCHEMA, 'pick')
            seen, idx = set(), []
            for n in pick['pick']:
                if isinstance(n, int) and not isinstance(n, bool) and 1 <= n <= len(cands) and n not in seen:
                    seen.add(n); idx.append(n - 1)
            notes = [pick.get('note') or ''] if idx else notes
            cands = [cands[j] for j in idx][:RANK_KEEP] if idx else cands[:RANK_KEEP]
        except Exception as e:
            res['batch_errors'].append(f'순위: {type(e).__name__}: {str(e)[:150]}')
            cands = cands[:RANK_KEEP]
    return cands, ' / '.join(n for n in notes if n), reviews


def main(argv):
    a = {}
    for x in argv:
        k, _, v = x.partition('=')
        a[k] = v or True
    dry = '--dry-run' in a
    out_dir = a.get('--out-dir') or os.path.join(ldb.DATA_DIR, 'proposals')
    profile_path = a.get('--profile') or os.path.join(ldb.DATA_DIR, 'review_profile.md')
    res = {'ok': False, 'considered_videos': 0, 'considered_tips': 0, 'proposals': 0, 'dropped': 0, 'file': None, 'error': None, 'notified': None, 'batches': 0, 'candidates': 0, 'candidates_total': 0, 'batch_errors': []}

    formal = '--days' not in a and '--backfill' not in a and not dry and '--no-notify' not in a
    lines = []  # 제안 한 줄씩

    def notify():
        if res['ok'] and res['proposals'] >= 1:
            text = (f"🧭 [매일 Wiki 검토] 제안 {res['proposals']}건 (영상 {res['considered_videos']} · 꿀팁 {res['considered_tips']} 검토)\n"
                    + '\n'.join(lines) + '\nhttp://localhost:3000/wiki#tab=proposals')
        elif not res['ok'] and res['error'] != 'exists':
            text = '⚠️ [매일 Wiki 검토 실패] ' + (res['error'] or '')[:150]
        else:
            return
        try:
            env = env_util.load_env()
        except Exception:  # .env 를 못 읽어도 실행 결과는 그대로
            env = {}
        token, chat = env.get('TELEGRAM_BOT_TOKEN'), env.get('TELEGRAM_CHAT_ID')
        res['notified'] = send_telegram(token, chat, text) if token and chat else 'not_configured'

    def done(code):
        if formal:
            notify()
        print('RESULT_JSON ' + json.dumps(res, ensure_ascii=False))
        return code

    now = utcnow()
    know = now.astimezone(KST)
    try:
        days = int(a['--days']) if a.get('--days') else None
        bf = int(a['--backfill']) if a.get('--backfill') else None
        conn = ldb.open_existing(a.get('--db') or None, readonly=True)
    except Exception as e:
        res['error'] = f'{type(e).__name__}: {e}'
        return done(1)
    try:
        if bf is not None:
            since = iso(now - timedelta(days=bf))
            pid = 'trial-' + know.strftime('%Y%m%d-%H%M%S')
            path = os.path.join(out_dir, 'trial', pid[6:] + '.json')
        elif days is not None:
            since = iso(now - timedelta(days=days))
            pid = 'trial-' + know.strftime('%Y%m%d-%H%M%S')
            path = os.path.join(out_dir, 'trial', pid[6:] + '.json')
        else:
            files = sorted(glob.glob(os.path.join(out_dir, '[0-9]' * 8 + '.json')))
            since = ((read_json(files[-1]) or {}).get('through') if files else None) or iso(now - timedelta(days=1))
            pid = know.strftime('%Y%m%d')
            path = os.path.join(out_dir, pid + '.json')
        if os.path.exists(path) and not dry:
            res['error'] = 'exists'
            return done(1)
        vids, tips, truncated = select_targets(conn, since, None if bf is not None else MAX_ITEMS)
        res['considered_videos'], res['considered_tips'] = len(vids), len(tips)
        has_profile = os.path.exists(profile_path)
        if not has_profile:
            print(f'경고: 프로필 파일 없음 ({profile_path})', file=sys.stderr)
        profile = open(profile_path, encoding='utf-8').read() if has_profile else ''
        titles, rejects = recent_context(out_dir, now)
        prompt = build_prompt(profile, installed_skills(), titles, rejects, vids, tips) if (vids or tips) else ''
        if bf is not None:
            n = -(-max(len(vids), len(tips)) // MAX_ITEMS)
            if not n:
                res['error'] = 'no_targets'
                return done(1)
            skills = installed_skills()
            prompts = [(vids[k * MAX_ITEMS:(k + 1) * MAX_ITEMS], tips[k::n]) for k in range(n)]  # 꿀팁은 묶음에 돌아가며
            prompts = [(v, t, build_prompt(profile, skills, titles, rejects, v, t, BATCH_CAND).replace('제안 0~8건', '후보 0~8건')) for v, t in prompts]
            if dry:
                print(f'dry-run backfill: since={since} videos={len(vids)} tips={len(tips)} batches={n} prompt_chars={[len(x[2]) for x in prompts]}')
                res.update(ok=True, batches=n, batch_errors=0)
                return done(0)
            cands, note, reviews = run_backfill(vids, tips, prompts, profile, res)
            if not res['batches']:
                res['error'] = 'all batches failed'
                res['batch_errors'] = len(res['batch_errors'])
                return done(1)
            props = [dict(c, id=f'{pid}-{i}', status='new') for i, c in enumerate(cands, 1)]
            out = {'version': 1, 'mode': 'backfill', 'created_at': iso(now), 'through': iso(now), 'window': {'from': since, 'to': iso(now)},
                   'considered': {'videos': len(vids), 'tips': len(tips), 'truncated': 0}, 'batches': res['batches'], 'candidates': len(cands), 'candidates_total': res['candidates_total'],
                   'batch_errors': res['batch_errors'], 'tip_review': reviews, 'model': 'opus', 'proposals': props, 'dropped': [], 'note': note}
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path + '.tmp', 'w', encoding='utf-8') as f:
                json.dump(out, f, ensure_ascii=False, indent=2)
            os.replace(path + '.tmp', path)
            res.update(ok=True, proposals=len(props), candidates=len(props), file=path, batch_errors=len(res['batch_errors']))
            return done(0)
        if dry:
            print(f'dry-run: since={since} videos={len(vids)} tips={len(tips)} truncated={truncated} prompt_chars={len(prompt)}')
            res['ok'] = True
            return done(0)
        note, props, dropped, tip_review = '대상 0건', [], [], []
        if vids or tips:
            data = call_claude(prompt)
            note = data.get('note') or ''
            tip_review = clean_tip_review(data.get('tip_review'), {x['record_id'] for x in tips})
            allowed = {x['record_id'] for x in vids + tips}
            for p in data['proposals']:
                why = validate(p, allowed)
                if why:
                    dropped.append({'title': p.get('title') if isinstance(p, dict) else None, 'reason': why})
                elif len(props) >= MAX_PROPOSALS:
                    dropped.append({'title': p['title'], 'reason': 'over_limit'})
                else:
                    props.append(dict(p, id=f'{pid}-{len(props) + 1}', status='new'))
        times = [x['created_at'] for x in vids + tips]
        out = {'version': 1, 'created_at': iso(now), 'through': max(times) if times else iso(now),
               'window': {'from': since, 'to': iso(now)},
               'considered': {'videos': len(vids), 'tips': len(tips), 'truncated': truncated},
               'model': 'opus', 'proposals': props, 'dropped': dropped, 'tip_review': tip_review,
               'note': note if has_profile else (note + ' · 프로필 없음').strip(' ·')}
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path + '.tmp', 'w', encoding='utf-8') as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        os.replace(path + '.tmp', path)
        lines.extend(f"{i}. [{'스킬' if p['kind'] == 'skill' else '적용'}] {p['title']}" for i, p in enumerate(props, 1))
        res.update(ok=True, proposals=len(props), dropped=len(dropped), file=path)
        return done(0)
    except Exception as e:
        res['error'] = f'{type(e).__name__}: {str(e)[:300]}'
        return done(1)
    finally:
        conn.close()


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
