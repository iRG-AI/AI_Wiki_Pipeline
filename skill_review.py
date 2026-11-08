#!/usr/bin/env python3
"""매일 Wiki 검토 1단계 [CC-1109-A] — 그날 들어온 영상·꿀팁을 Claude 가 읽고 스킬/적용 제안 0~3건을 data/proposals/ 에 JSON 으로 남긴다.

Claude 에게 도구·MCP 를 주지 않는다(프롬프트 → JSON 만). 장부는 읽기 전용. 재시도 없음(실패는 기록하고 끝, 다음 날 같은 기준점에서 다시 본다).

    /opt/homebrew/bin/python3 skill_review.py [--dry-run] [--days=N] [--no-notify]
테스트 전용: --db= --out-dir= --profile=   환경변수: CLAUDE_BIN · SKILL_REVIEW_SKILLS_DIR
"""
import glob, json, os, re, subprocess, sys, tempfile, urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(REPO, 'lib'))
import library_db as ldb
import env_util

KST = ZoneInfo('Asia/Seoul')
CLAUDE_TIMEOUT = 900
MAX_ITEMS, SUMMARY_CHARS, MAX_PROPOSALS = 40, 2500, 3
SLUG_RE = re.compile(r'^[a-z0-9-]{3,40}$')
SCHEMA = {"type": "object", "required": ["proposals"], "properties": {
    "proposals": {"type": "array", "maxItems": 3, "items": {"type": "object",
        "required": ["kind", "area", "title", "why", "evidence", "effort"], "properties": {
            "kind": {"enum": ["skill", "action"]}, "area": {"enum": ["dev", "work", "knowledge", "content"]},
            "title": {"type": "string"}, "why": {"type": "string"},
            "evidence": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "effort": {"enum": ["낮음", "중간", "높음"]},
            "skill": {"type": "object", "properties": {"slug": {"type": "string"}, "skill_md": {"type": "string"}}},
            "action_prompt": {"type": "string"}}}},
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


def select_targets(conn, since):
    vids = [dict(r) for r in conn.execute(
        "SELECT record_id,title,channel,topics,video_url,summary_src,summary,created_at FROM videos "
        "WHERE created_at > ? AND coalesce(grade,'')<>'exclude' ORDER BY created_at DESC", (since,))]
    tips = [dict(r) for r in conn.execute(
        "SELECT record_id,title,url,category,tags,memo,created_at FROM tips WHERE created_at > ? ORDER BY created_at DESC", (since,))]
    truncated = max(0, len(vids) - MAX_ITEMS) + max(0, len(tips) - MAX_ITEMS)
    vids, tips = vids[:MAX_ITEMS], tips[:MAX_ITEMS]
    for v in vids:
        v['summary'] = (v['summary'] or '')[:SUMMARY_CHARS]
    return vids, tips, truncated


def recent_context(out_dir, now):
    titles, rejects = [], []
    today = now.astimezone(KST).date()
    for p in sorted(glob.glob(os.path.join(out_dir, '[0-9]' * 8 + '.json'))):
        age = (today - datetime.strptime(os.path.basename(p)[:8], '%Y%m%d').date()).days
        if 0 <= age <= 6:
            titles += [x.get('title', '') for x in (read_json(p) or {}).get('proposals', [])]
    dec = (read_json(os.path.join(out_dir, 'decisions.json')) or {}).get('decisions')
    items = [x for x in (dec.values() if isinstance(dec, dict) else []) if isinstance(x, dict) and x.get('decision') == 'rejected']
    for x in sorted(items, key=lambda x: x.get('at') or '', reverse=True)[:30]:
        rejects.append(f"{x.get('title', '')}: {x.get('reason') or '(사유 없음)'}")
    return titles, rejects


def build_prompt(profile, skills, titles, rejects, vids, tips):
    L = ["당신은 대표님의 매일 Wiki 검토 담당입니다. 아래는 오늘 새로 들어온 영상 요약과 꿀팁입니다.",
         "대표님께 실제로 쓸모 있는 스킬(SKILL.md) 또는 적용 아이디어를 0~3건 제안하세요.", "",
         "## 대표님 프로필", profile.strip(), "",
         "## 이미 설치된 스킬 이름", ', '.join(skills) or '(없음)', "",
         "## 최근 7일 제안 제목", '\n'.join('- ' + t for t in titles) or '(없음)', "",
         "## 최근 거절 사유", '\n'.join('- ' + t for t in rejects) or '(없음)', "",
         "## 규칙",
         "- 제안 0~3건. 억지로 채우지 마세요(\"오늘은 없음\"도 정상, proposals 를 빈 배열로). 판매·일반론·뉴스는 제외.",
         "- 설치된 스킬, 최근 제안, 거절된 것과 겹치면 제외.",
         "- evidence 는 아래 목록의 record_id 만, 1개 이상.",
         "- kind=skill 이면 skill.slug(정규식 ^[a-z0-9-]{3,40}$, 접두 없이)와 skill.skill_md(완전한 SKILL.md: 프론트매터 `name: wiki-<slug>` · `description:`(언제 쓰는지, 호출 문구 포함), 본문은 한국어 절차). 비밀값·개인 경로 금지.",
         "- kind=action 이면 action_prompt(대표님이 Claude Code 에 그대로 붙여 넣을 지시 한 단락).",
         "- 결과는 지정된 JSON 스키마로만 답하세요.", "", "## 오늘의 영상"]
    for v in vids:
        L.append(f"### [{v['record_id']}] {v['title']} ({v['channel']}) topics={v['topics']} {v['video_url'] or ''}\n{v['summary']}")
    L.append("\n## 오늘의 꿀팁")
    for t in tips:
        L.append(f"- [{t['record_id']}] {t['title']} | {t['url']} | {t['category']} | {t['tags']} | {t['memo']}")
    return '\n'.join(L)


def call_claude(prompt):
    claude = os.environ.get('CLAUDE_BIN') or os.path.expanduser('~/.local/bin/claude')
    with tempfile.TemporaryDirectory() as empty:
      try:
        p = subprocess.run([claude, '-p', '--model', 'opus', '--output-format', 'json', '--json-schema', json.dumps(SCHEMA),
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
    if not isinstance(data, dict) or not isinstance(data.get('proposals'), list):
        raise ValueError('proposals 없음')
    return data


def validate(p, allowed):
    """None = 통과, 아니면 버리는 사유."""
    if not isinstance(p, dict):
        return 'not_object'
    for k in ('kind', 'area', 'title', 'why', 'effort'):
        if not isinstance(p.get(k), str) or not p[k]:
            return f'missing:{k}'
    if p['kind'] not in ('skill', 'action') or p['area'] not in ('dev', 'work', 'knowledge', 'content') or p['effort'] not in ('낮음', '중간', '높음'):
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


def main(argv):
    a = {}
    for x in argv:
        k, _, v = x.partition('=')
        a[k] = v or True
    dry = '--dry-run' in a
    out_dir = a.get('--out-dir') or os.path.join(ldb.DATA_DIR, 'proposals')
    profile_path = a.get('--profile') or os.path.join(ldb.DATA_DIR, 'review_profile.md')
    res = {'ok': False, 'considered_videos': 0, 'considered_tips': 0, 'proposals': 0, 'dropped': 0, 'file': None, 'error': None, 'notified': None}

    formal = '--days' not in a and not dry and '--no-notify' not in a
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
        conn = ldb.open_existing(a.get('--db') or None, readonly=True)
    except Exception as e:
        res['error'] = f'{type(e).__name__}: {e}'
        return done(1)
    try:
        if days is not None:
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
        vids, tips, truncated = select_targets(conn, since)
        res['considered_videos'], res['considered_tips'] = len(vids), len(tips)
        has_profile = os.path.exists(profile_path)
        if not has_profile:
            print(f'경고: 프로필 파일 없음 ({profile_path})', file=sys.stderr)
        profile = open(profile_path, encoding='utf-8').read() if has_profile else ''
        titles, rejects = recent_context(out_dir, now)
        prompt = build_prompt(profile, installed_skills(), titles, rejects, vids, tips) if (vids or tips) else ''
        if dry:
            print(f'dry-run: since={since} videos={len(vids)} tips={len(tips)} truncated={truncated} prompt_chars={len(prompt)}')
            res['ok'] = True
            return done(0)
        note, props, dropped = '대상 0건', [], []
        if vids or tips:
            data = call_claude(prompt)
            note = data.get('note') or ''
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
               'model': 'opus', 'proposals': props, 'dropped': dropped,
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
