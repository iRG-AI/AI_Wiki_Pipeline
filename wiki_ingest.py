#!/usr/bin/env python3
"""
Karpathy LLM Wiki Ingest Engine
- Raw Source(.md) → Gemini 분석 → 엔티티/개념 추출 → 장부 wiki_extract 에 소스별 누적 (v4.5)
- _wiki 개념·엔티티 페이지와 index.md 는 매 실행 끝에 wiki_extract 전체 + 현재 Vault(파일명·제목)로
  다시 그린다(내용이 같으면 쓰지 않는다). Vault 에서 빠진 소스는 저절로 빠지고, 바뀐 제목은 저절로 따라간다.
  ★ v4.4 까지는 그 실행분만으로 페이지를 통째로 다시 써서 페이지마다 마지막 실행분(1~10건)만 남았다.
- 무료 티어 Rate Limit 자동 준수 (wiki_config.gemini_call)

실행:
  python3 wiki_ingest.py                     증분(신규 소스) → backfill(하루 WIKI_BACKFILL_DAILY_MAX 회, 기본 30) → 재렌더
  python3 wiki_ingest.py --no-backfill       증분 → 재렌더 (sync_obsidian 경로)
  python3 wiki_ingest.py --render-only       Gemini 호출 없이 재렌더만
  python3 wiki_ingest.py --seed-from-pages [--apply]
                                             지금 _wiki 페이지의 항목을 wiki_extract 씨앗(status=seed)으로 옮긴다. 기본 dry-run
  python3 wiki_ingest.py --full | --limit=N  (종전) 전체 재분석 / 처리 상한 (둘 다 backfill 안 함)

.env: WIKI_BACKFILL_DAILY_MAX(기본 30, 0 = 끔) · WIKI_BACKFILL_BATCH(기본 20)

(v4.6-b) backfill 대상은 실제 영상으로 요약된 노트(프론트매터 summary_src: video)만이다 — 설명란만 보고 지어낸 옛 요약으로
         Wiki 를 채우지 않는다. 재요약(lib/resummarize.js)이 wiki_extract 를 stale 로 돌려 두면 여기서 새 요약으로 다시 추출한다.
         항목이 0개가 된 이름(목록 ENTITIES·CONCEPTS 안)의 기존 페이지는 안내 문구 페이지로 다시 그린다(지우지 않음 — 링크 유지).
"""

import os, re, json, sys, time, unicodedata
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import wiki_config as wc
from wiki_config import (
    VAULT, WIKI_DIR, ENTITIES_DIR, CONCEPTS_DIR, SYNTHESIS_DIR,
    STATE_FILE, ENTITIES, CONCEPTS, nfc, gemini_call, load_state, save_state,
    DailyQuotaExhausted
)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR, 'lib'))
import library_db as ldb   # noqa: E402  v4.5 wiki_extract

KST = timezone(timedelta(hours=9))
ROLES = ('주제', '도구', '비교대상', '관련')
MAX_FAILS = 3              # ok 가 아닌 행은 실패 3회에서 포기 (깨진 응답을 매일 다시 태우지 않는다)
BATCH_SIZE = 20            # backfill 한 호출에 묶는 소스 수 (.env WIKI_BACKFILL_BATCH 로 1~40)
BATCH_BODY_CHARS = 1500    # backfill 소스 본문 상한 (증분은 종전대로 3000)
BATCH_MAX_TOKENS = 16000
DEFAULT_BACKFILL_MAX = 30  # 하루(태평양시) backfill 호출 상한 — 같은 무료 키를 영상 요약이 쓴다

def log(msg): print(msg, flush=True)

def now_iso():
    t = datetime.now(timezone.utc)
    return t.strftime('%Y-%m-%dT%H:%M:%S.') + f'{t.microsecond // 1000:03d}Z'

def kst_label(iso):
    """'2026-10-12T07:39:33.000Z' → '2026-10-12 16:39' (KST). 형식이 다르면 앞 16자."""
    try:
        dt = datetime.strptime(iso[:19], '%Y-%m-%dT%H:%M:%S').replace(tzinfo=timezone.utc)
        return dt.astimezone(KST).strftime('%Y-%m-%d %H:%M')
    except (ValueError, TypeError):
        return str(iso or '')[:16]

# ══════════════════════════════════════
# 1. Raw Source 수집
# ══════════════════════════════════════
def collect_sources():
    """Vault에서 모든 원본 .md 파일 수집 (토픽 폴더 내 영상 요약 파일)"""
    sources = []
    for folder_raw in os.listdir(VAULT):
        folder = nfc(folder_raw)
        folder_path = os.path.join(VAULT, folder_raw)
        if not os.path.isdir(folder_path) or folder.startswith('.') or folder.startswith('_'):
            continue
        if folder in ('기타',):
            continue
        for fname_raw in os.listdir(folder_path):
            fname = nfc(fname_raw)
            if not fname.endswith('.md'): continue
            fpath = os.path.join(folder_path, fname_raw)
            try:
                content = nfc(open(fpath, encoding='utf-8', errors='ignore').read())
            except Exception:
                continue
            # frontmatter 파싱
            m = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
            fm = {}
            body = content
            if m:
                for line in m.group(1).split('\n'):
                    if ':' in line:
                        k, _, v = line.partition(':')
                        fm[k.strip()] = v.strip().strip('"')
                body = content[m.end():]
            sources.append({
                'path': fpath,
                'folder': folder,
                'filename': fname,
                'title': fm.get('title', fname[:-3]),
                'channel': fm.get('channel', ''),
                'notion_id': fm.get('notion_id', ''),
                'upload_date': fm.get('upload_date', ''),
                'grade': fm.get('grade', ''),
                'summary_src': fm.get('summary_src', ''),   # (v4.6-b) backfill 은 'video' 만
                'body': body[:3000],  # API 비용 절약
            })
    # (v4.6) grade: exclude 노트(판매 주목적·일반론·AI 무관)는 추출·backfill·페이지 렌더 모두에서 뺀다. 노트 자체는 그대로
    kept = [s for s in sources if s['grade'] != 'exclude']
    if len(kept) != len(sources):
        log(f'  🚫 품질 필터 제외 소스 {len(sources) - len(kept)}개 — Wiki 합성에서 뺌')
    return kept

# ══════════════════════════════════════
# 2. Gemini로 엔티티/개념 추출
# ══════════════════════════════════════
EXTRACT_PROMPT = """당신은 AI 기술 Wiki 관리자입니다. 아래 YouTube 영상 요약에서 엔티티와 개념을 추출하세요.

## 영상 정보
- 제목: {title}
- 채널: {channel}
- 폴더(주제): {folder}
- 업로드일: {upload_date}

## 요약 내용
{body}

## 추출 대상 엔티티 (아래 목록 중에서만 선택)
{entity_list}

## 추출 대상 개념 (아래 목록 중에서만 선택)
{concept_list}

## 규칙
1. 영상에서 **실질적으로 다루는** 엔티티/개념만 선택 (단순 언급 제외)
2. 각 항목에 대해 이 영상에서 얻을 수 있는 **핵심 정보 1~2문장** 작성
3. 엔티티/개념 간 **관계**가 있으면 기술 (예: "Claude Code로 바이브코딩")

## 출력 (JSON)
{{
  "entities": [
    {{"name": "엔티티명", "insight": "이 영상에서의 핵심 정보", "role": "주제|도구|비교대상"}}
  ],
  "concepts": [
    {{"name": "개념명", "insight": "이 영상에서의 핵심 정보"}}
  ],
  "relations": [
    {{"from": "A", "to": "B", "type": "사용|비교|통합|대체"}}
  ]
}}"""

def parse_json(raw):
    """Gemini 응답 → dict. 못 읽으면 None (빈 결과와 구분한다)."""
    if not raw:
        return None
    for cand in (raw, ):
        try:
            return json.loads(cand)
        except (json.JSONDecodeError, TypeError):
            pass
    m = re.search(r'\{[\s\S]*\}', raw)
    if not m:
        return None
    for cand in (m.group(0), re.sub(r',\s*([}\]])', r'\1', m.group(0))):
        try:
            return json.loads(cand)
        except json.JSONDecodeError:
            pass
    return None

def clean_result(data):
    """목록 밖 이름·형식 오류를 걸러 {'entities','concepts','relations'}. dict 가 아니면 None."""
    if not isinstance(data, dict):
        return None
    ents, cons, rels, seen_e, seen_c = [], [], [], set(), set()
    for e in data.get('entities') or []:
        if not isinstance(e, dict): continue
        name = nfc(str(e.get('name', '')).strip())
        if name not in ENTITIES or name in seen_e: continue
        role = nfc(str(e.get('role', '관련')).strip())
        ents.append({'name': name, 'insight': nfc(str(e.get('insight', '')).strip()),
                     'role': role if role in ROLES else '관련'})
        seen_e.add(name)
    for c in data.get('concepts') or []:
        if not isinstance(c, dict): continue
        name = nfc(str(c.get('name', '')).strip())
        if name not in CONCEPTS or name in seen_c: continue
        cons.append({'name': name, 'insight': nfc(str(c.get('insight', '')).strip())})
        seen_c.add(name)
    for r in data.get('relations') or []:
        if not isinstance(r, dict): continue
        f, t = nfc(str(r.get('from', '')).strip()), nfc(str(r.get('to', '')).strip())
        if f and t:
            rels.append({'from': f, 'to': t, 'type': nfc(str(r.get('type', '관련')).strip()) or '관련'})
    return {'entities': ents, 'concepts': cons, 'relations': rels}

def extract_from_source(source):
    """하나의 소스에서 엔티티/개념 추출. 응답을 못 읽으면 None (v4.4 까지는 빈 결과로 성공 처리돼 조용히 빠졌다)."""
    prompt = EXTRACT_PROMPT.format(
        title=source['title'],
        channel=source['channel'],
        folder=source['folder'],
        upload_date=source['upload_date'],
        body=source['body'],
        entity_list=', '.join(ENTITIES),
        concept_list=', '.join(CONCEPTS),
    )
    return clean_result(parse_json(gemini_call(prompt)))

BATCH_PROMPT = """당신은 AI 기술 Wiki 관리자입니다. 아래 YouTube 영상·링크 요약 {n}개 각각에서 엔티티와 개념을 추출하세요.

## 추출 대상 엔티티 (아래 목록 중에서만 선택)
{entity_list}

## 추출 대상 개념 (아래 목록 중에서만 선택)
{concept_list}

## 규칙
1. 각 소스가 **실질적으로 다루는** 엔티티/개념만 선택 (단순 언급 제외). 해당 없으면 빈 배열
2. 각 항목에 대해 그 소스에서 얻을 수 있는 **핵심 정보 1~2문장** 작성
3. 엔티티/개념 간 **관계**가 있으면 기술 (예: "Claude Code로 바이브코딩")
4. 소스마다 결과를 하나씩, 소스의 id 를 그대로 붙여 **{n}개 모두** 출력

## 소스
{sources}

## 출력 (JSON)
{{
  "results": [
    {{
      "id": "S1",
      "entities": [{{"name": "엔티티명", "insight": "핵심 정보", "role": "주제|도구|비교대상"}}],
      "concepts": [{{"name": "개념명", "insight": "핵심 정보"}}],
      "relations": [{{"from": "A", "to": "B", "type": "사용|비교|통합|대체"}}]
    }}
  ]
}}"""

def extract_batch(batch):
    """소스 여러 개를 한 호출로. 반환: {notion_id: 결과} (응답에 없거나 못 읽은 소스는 빠진다)."""
    blocks = []
    for i, s in enumerate(batch, 1):
        blocks.append(f"### S{i}\n- 제목: {s['title']}\n- 채널: {s['channel']}\n- 폴더(주제): {s['folder']}\n"
                      f"- 업로드일: {s['upload_date']}\n\n{s['body'][:BATCH_BODY_CHARS]}\n")
    prompt = BATCH_PROMPT.format(n=len(batch), entity_list=', '.join(ENTITIES),
                                 concept_list=', '.join(CONCEPTS), sources='\n'.join(blocks))
    data = parse_json(gemini_call(prompt, max_tokens=BATCH_MAX_TOKENS))
    out = {}
    if not isinstance(data, dict):
        return out
    for item in data.get('results') or []:
        if not isinstance(item, dict): continue
        m = re.fullmatch(r'S?(\d+)', str(item.get('id', '')).strip())
        if not m or not (1 <= int(m.group(1)) <= len(batch)): continue
        res = clean_result(item)
        if res is not None:
            out.setdefault(batch[int(m.group(1)) - 1]['notion_id'], res)
    return out

# ══════════════════════════════════════
# 3. 장부 wiki_extract (v4.5)
# ══════════════════════════════════════
def load_store(conn):
    rows = {}
    for r in conn.execute('SELECT * FROM wiki_extract'):
        d = dict(r)
        for k in ('entities', 'concepts', 'relations'):
            try:
                v = json.loads(d[k] or '[]')
                d[k] = v if isinstance(v, list) else []
            except ValueError:
                d[k] = []
        rows[d['record_id']] = d
    return rows

def save_ok(conn, rid, res, source, status='ok'):
    ts = now_iso()
    with conn:
        conn.execute(
            'INSERT INTO wiki_extract (record_id, status, source, entities, concepts, relations, attempts, created_at, updated_at) '
            'VALUES (?,?,?,?,?,?,0,?,?) ON CONFLICT(record_id) DO UPDATE SET status=excluded.status, source=excluded.source, '
            'entities=excluded.entities, concepts=excluded.concepts, relations=excluded.relations, updated_at=excluded.updated_at',
            (rid, status, source, json.dumps(res['entities'], ensure_ascii=False),
             json.dumps(res['concepts'], ensure_ascii=False), json.dumps(res.get('relations', []), ensure_ascii=False), ts, ts))

def save_fail(conn, rid, source):
    """실패 1회 기록. 있는 행(seed 등)은 내용·status 를 그대로 두고 attempts 만 올린다. 반환: 누적 실패 횟수."""
    ts = now_iso()
    with conn:
        conn.execute(
            "INSERT INTO wiki_extract (record_id, status, source, attempts, created_at, updated_at) VALUES (?, 'failed', ?, 1, ?, ?) "
            'ON CONFLICT(record_id) DO UPDATE SET attempts=attempts+1, updated_at=excluded.updated_at',
            (rid, source, ts, ts))
    return conn.execute('SELECT attempts FROM wiki_extract WHERE record_id=?', (rid,)).fetchone()[0]

def needs_backfill(row):
    return row is None or (row['status'] != 'ok' and row['attempts'] < MAX_FAILS)

def backfill_source(s, ingested, store):
    """(v4.6-b) backfill 대상 = 예전에 처리됐고 · 실제 영상 요약 노트이고 · wiki_extract 가 없거나 ok 가 아님(seed·failed·stale)"""
    rid = s['notion_id']
    return bool(rid) and rid in ingested and s.get('summary_src') == 'video' and needs_backfill(store.get(rid))

# ══════════════════════════════════════
# 4. 페이지 렌더 (wiki_extract 전체 + 현재 Vault)
# ══════════════════════════════════════
def write_if_changed(path, text):
    text = nfc(text)
    if os.path.exists(path):
        try:
            if open(path, encoding='utf-8').read() == text:
                return False
        except OSError:
            pass
    open(path, 'w', encoding='utf-8').write(text)
    return True

def build_page_data(store, sources):
    by_id = {}
    for s in sources:
        if s['notion_id']:
            by_id.setdefault(s['notion_id'], s)
    entity_data, concept_data = defaultdict(list), defaultdict(list)
    for rid, row in store.items():
        s = by_id.get(rid)
        if not s:
            continue   # Vault 에서 빠진 소스(고아) — 페이지에 싣지 않는다
        ref = {'source_filename': s['filename'][:-3], 'title': s['title'], 'channel': s['channel'],
               'upload_date': s['upload_date'], 'updated_at': row['updated_at']}
        for e in row['entities']:
            if isinstance(e, dict) and e.get('name') in ENTITIES:
                entity_data[e['name']].append({**ref, 'insight': e.get('insight', ''), 'role': e.get('role', '관련'),
                                               'relations': row['relations']})
        for c in row['concepts']:
            if isinstance(c, dict) and c.get('name') in CONCEPTS:
                concept_data[c['name']].append({**ref, 'insight': c.get('insight', '')})
    return entity_data, concept_data

def _sorted(entries):
    return sorted(entries, key=lambda x: (str(x.get('upload_date', '')), x['source_filename']), reverse=True)

def _item_lines(e):
    date = str(e.get('upload_date', ''))[:10]
    return [f"- [[{e['source_filename']}|{e['title']}]] `{e['channel']}` {date}", f"  > {e['insight']}"]

def render_entity_page(name, entries):
    last = kst_label(max(e['updated_at'] for e in entries))
    by_role = defaultdict(list)
    for e in entries:
        by_role[e.get('role') if e.get('role') in ROLES else '관련'].append(e)
    lines = ['---', 'type: entity', f'name: "{name}"', f'source_count: {len(entries)}', f'last_updated: {last}', '---', '',
             f'# {name}', '', f'> 총 **{len(entries)}개** 영상에서 언급됨', '']
    role_icon = {'주제': '🎯', '도구': '🔧', '비교대상': '⚖️', '관련': '🔗'}
    for role in ROLES:
        role_entries = by_role.get(role, [])
        if not role_entries: continue
        lines.append(f'## {role_icon[role]} {role}로 다룬 영상 ({len(role_entries)}개)')
        lines.append('')
        for e in _sorted(role_entries):
            lines.extend(_item_lines(e))
        lines.append('')
    rels, seen = [], set()
    for e in _sorted(entries):
        for r in e.get('relations', []):
            if not isinstance(r, dict) or name not in (r.get('from'), r.get('to')): continue
            other = r['to'] if r['from'] == name else r['from']
            key = f"{other}-{r.get('type', '관련')}"
            if other and other != name and key not in seen:
                rels.append(f"- [[{other}]] — {r.get('type', '관련')}")
                seen.add(key)
    if rels:
        lines += ['## 🔗 관련 엔티티/개념', ''] + rels + ['']
    return '\n'.join(lines)

def render_concept_page(name, entries):
    last = kst_label(max(e['updated_at'] for e in entries))
    lines = ['---', 'type: concept', f'name: "{name}"', f'source_count: {len(entries)}', f'last_updated: {last}', '---', '',
             f'# {name}', '', f'> 총 **{len(entries)}개** 영상에서 다룸', '', '## 📚 관련 영상', '']
    for e in _sorted(entries):
        lines.extend(_item_lines(e))
    lines.append('')
    return '\n'.join(lines)

def render_index(entity_data, concept_data):
    stamps = [e['updated_at'] for d in (entity_data, concept_data) for es in d.values() for e in es]
    now = kst_label(max(stamps)) if stamps else ''
    lines = ['# 🧠 AI LLM Wiki — Knowledge Index', '', f'> 마지막 갱신: {now}', '> Karpathy LLM Wiki 패턴 기반 지식 합성 시스템',
             '', '---', '', f'## 📦 엔티티 (AI 도구/서비스) — {len(entity_data)}개', '',
             '| 엔티티 | 소스 수 | 최근 갱신 |', '|--------|---------|-----------|']
    for name in sorted(entity_data):
        latest = max((str(e.get('upload_date', '')) for e in entity_data[name]), default='')[:10]
        lines.append(f'| [[{name}]] | {len(entity_data[name])}개 | {latest} |')
    lines += ['', f'## 💡 개념 (기술/방법론) — {len(concept_data)}개', '', '| 개념 | 소스 수 | 최근 갱신 |', '|------|---------|-----------|']
    for name in sorted(concept_data):
        latest = max((str(e.get('upload_date', '')) for e in concept_data[name]), default='')[:10]
        lines.append(f'| [[{name}]] | {len(concept_data[name])}개 | {latest} |')
    lines += ['', '---', '', '*이 파일은 `wiki_ingest.py` 실행 시 자동 갱신됩니다 (장부 wiki_extract 전체 기준).*']
    return '\n'.join(lines)

def render_empty_page(kind, name):
    """(v4.6-b) 항목이 0개가 된 이름의 페이지 — 결정적(시각 없음)이라 할 일 없는 실행은 다시 쓰지 않는다"""
    return '\n'.join(['---', f'type: {kind}', f'name: "{name}"', 'source_count: 0', '---', '', f'# {name}', '',
                      '> 지금 이 항목을 다룬 영상이 없습니다 — 품질 필터로 제외됐거나, 실제 영상 재요약 뒤 다시 추출되기를 기다리는 중입니다.',
                      '', '*이 파일은 `wiki_ingest.py` 실행 시 자동 갱신됩니다 (장부 wiki_extract 전체 기준).*', ''])

def empty_pages(dir_path, names, data, kind):
    """목록(names) 안 이름인데 이번 렌더에 항목이 없고 파일은 있는 페이지 → 안내 페이지로. 쓴 수 반환. 목록 밖 파일은 건드리지 않는다"""
    w = 0
    if not os.path.isdir(dir_path):
        return 0
    for f in sorted(os.listdir(dir_path)):
        name = nfc(f)[:-3] if f.endswith('.md') else None
        if not name or name in data or name not in names:
            continue
        w += write_if_changed(os.path.join(dir_path, f), render_empty_page(kind, name))
    return w

def render_all(conn, sources):
    """반환: (entity_data, concept_data, 쓴 엔티티 수, 쓴 개념 수, index 를 썼는가, 안내 페이지로 쓴 수).
    (v4.6-b) 항목 0개인 이름(목록 안)의 기존 페이지는 지우지 않고 안내 문구 페이지로 다시 그린다. index 에는 안 실린다."""
    os.makedirs(ENTITIES_DIR, exist_ok=True)
    os.makedirs(CONCEPTS_DIR, exist_ok=True)
    entity_data, concept_data = build_page_data(load_store(conn), sources)
    ent_w = sum(write_if_changed(os.path.join(ENTITIES_DIR, nfc(f'{n}.md')), render_entity_page(n, es)) for n, es in entity_data.items())
    con_w = sum(write_if_changed(os.path.join(CONCEPTS_DIR, nfc(f'{n}.md')), render_concept_page(n, es)) for n, es in concept_data.items())
    empty_w = (empty_pages(ENTITIES_DIR, set(ENTITIES), entity_data, 'entity') +
               empty_pages(CONCEPTS_DIR, set(CONCEPTS), concept_data, 'concept'))
    idx_w = write_if_changed(os.path.join(WIKI_DIR, 'index.md'), render_index(entity_data, concept_data))
    return entity_data, concept_data, ent_w, con_w, idx_w, empty_w

# ══════════════════════════════════════
# 5. 옛 페이지 → 씨앗 (v4.5 1회)
# ══════════════════════════════════════
ITEM_RE = re.compile(r'^- \[\[([^|]+?)\|.*\]\] ')   # 파일명에 [ ] 가 들어간다([한영자막]·[Tech he'Story]). | 는 없다
ROLE_HEAD_RE = re.compile(r'^## \S+ (주제|도구|비교대상|관련)로 다룬 영상')

def parse_page(path, kind):
    """페이지의 영상 항목 → [{'file','role','insight'}]."""
    items, cur, role, in_list = [], None, '관련', False
    for line in nfc(open(path, encoding='utf-8').read()).split('\n'):
        if line.startswith('## '):
            m = ROLE_HEAD_RE.match(line)
            if kind == 'entity':
                in_list, role = bool(m), (m.group(1) if m else '관련')
            else:
                in_list = '관련 영상' in line
            cur = None
            continue
        if not in_list:
            continue
        m = ITEM_RE.match(line)
        if m:
            cur = {'file': m.group(1), 'role': role, 'insight': ''}
            items.append(cur)
        elif cur is not None and line.startswith('  > '):
            cur['insight'] = line[4:].strip()
    return items

def seed_from_pages(conn, sources, apply):
    by_file = {s['filename'][:-3]: s['notion_id'] for s in sources if s['notion_id']}
    store = load_store(conn)
    seeds = defaultdict(lambda: {'entities': [], 'concepts': [], 'relations': []})
    pages = items = 0
    unmatched = []
    for kind, folder, names, key in (('entity', ENTITIES_DIR, ENTITIES, 'entities'), ('concept', CONCEPTS_DIR, CONCEPTS, 'concepts')):
        if not os.path.isdir(folder): continue
        for fn in sorted(os.listdir(folder)):
            name = nfc(fn)[:-3]
            if not fn.endswith('.md') or name not in names: continue
            pages += 1
            for it in parse_page(os.path.join(folder, fn), kind):
                items += 1
                rid = by_file.get(it['file'])
                if not rid:
                    unmatched.append(f"{name} ← {it['file']}")
                    continue
                lst = seeds[rid][key]
                if any(x['name'] == name for x in lst): continue
                entry = {'name': name, 'insight': it['insight']}
                if kind == 'entity': entry['role'] = it['role']
                lst.append(entry)
    skipped_ok = [rid for rid in seeds if store.get(rid, {}).get('status') == 'ok']
    todo = {rid: v for rid, v in seeds.items() if rid not in skipped_ok}
    log(f'🌱 씨앗: 페이지 {pages}개 · 항목 {items}건 · 소스 {len(seeds)}건 (이미 ok {len(skipped_ok)}건 제외 → {len(todo)}건) · 매칭 실패 {len(unmatched)}건')
    for u in unmatched[:10]:
        log(f'   - 매칭 실패: {u}')
    if apply:
        for rid, res in todo.items():
            save_ok(conn, rid, res, 'seed', status='seed')
        log(f'  ✅ wiki_extract 에 seed {len(todo)}건 기록')
    else:
        log('  (dry-run — 쓰지 않음. 적용은 --apply)')
    print('SEED_RESULT:' + json.dumps({'pages': pages, 'items': items, 'records': len(seeds), 'skipped_ok': len(skipped_ok),
                                       'written': len(todo) if apply else 0, 'unmatched': len(unmatched), 'apply': bool(apply)},
                                      ensure_ascii=False))

# ══════════════════════════════════════
# 6. Wiki Log 기록
# ══════════════════════════════════════
def write_wiki_log(event, summary, details=None):
    log_path = os.path.join(WIKI_DIR, 'log.md')
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    today = datetime.now().strftime('%Y-%m-%d')

    if not os.path.exists(log_path):
        header = '# 📋 Wiki Ingest Log\n\n> Karpathy LLM Wiki 변경 이력\n\n'
        open(log_path, 'w', encoding='utf-8').write(nfc(header))

    entry = f'## [{today}] {event} | {summary}\n> ⏰ {now}\n\n'
    if details:
        for k, v in details.items():
            entry += f'- **{k}**: {v}\n'
    entry += '\n'

    existing = open(log_path, encoding='utf-8').read()
    # 헤더 이후에 삽입
    insert_pos = existing.find('\n\n', existing.find('변경 이력'))
    if insert_pos < 0:
        insert_pos = len(existing)
    else:
        insert_pos += 2
    open(log_path, 'w', encoding='utf-8').write(nfc(existing[:insert_pos] + entry + existing[insert_pos:]))

# ══════════════════════════════════════
# 메인 실행
# ══════════════════════════════════════
def _setting(key, default):
    """프로세스 환경변수가 .env 보다 먼저 (1회 시험 실행용: WIKI_BACKFILL_DAILY_MAX=1 python3 wiki_ingest.py)"""
    return os.environ.get(key) or wc.ENV.get(key, default)

def backfill_max():
    try:
        return max(0, int(_setting('WIKI_BACKFILL_DAILY_MAX', DEFAULT_BACKFILL_MAX)))
    except (TypeError, ValueError):
        return DEFAULT_BACKFILL_MAX

def batch_size():
    try:
        return min(40, max(1, int(_setting('WIKI_BACKFILL_BATCH', BATCH_SIZE))))
    except (TypeError, ValueError):
        return BATCH_SIZE

def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    full_mode = '--full' in argv
    render_only = '--render-only' in argv
    seed_mode = '--seed-from-pages' in argv
    no_backfill = '--no-backfill' in argv
    limit = None
    for arg in argv:
        if arg.startswith('--limit='):
            limit = int(arg.split('=')[1])

    log('🧠 Karpathy LLM Wiki Ingest 시작\n')
    start = time.time()
    state = load_state()
    ingested = state.setdefault('ingested', {})

    log('📂 Raw Source 수집 중...')
    sources = collect_sources()
    log(f'  총 {len(sources)}개 소스 파일\n')

    conn = ldb.open_existing()   # 장부가 없거나 user_version 이 다르면 던진다 (Vault 는 건드리지 않음)
    try:
        if seed_mode:
            seed_from_pages(conn, sources, '--apply' in argv)
            return 0
        return run(conn, state, ingested, sources, full_mode, render_only, no_backfill, limit, start)
    finally:
        conn.close()

def run(conn, state, ingested, sources, full_mode, render_only, no_backfill, limit, start):
    processed = errors = failed = 0
    bf_calls = bf_done = 0
    quota_out = False
    no_id = sum(1 for s in sources if not s['notion_id'])
    if no_id:
        log(f'  ⚠️  notion_id 없는 소스 {no_id}개 — 건너뜀')

    if not render_only:
        if full_mode:
            pending = [s for s in sources if s['notion_id']]
            log('🔄 전체 재분석 모드 (--full)\n')
        else:
            pending = [s for s in sources if s['notion_id'] and s['notion_id'] not in ingested]
            log(f'✨ 신규/미처리: {len(pending)}개\n')
        if limit:
            pending = pending[:limit]
            log(f'📊 처리 제한: {limit}개\n')

        consecutive_429_errors = 0
        for i, source in enumerate(pending):
            rid = source['notion_id']
            try:
                log(f'  [{i+1}/{len(pending)}] {source["title"][:50]}...')
                res = extract_from_source(source)
                if res is None:
                    n = save_fail(conn, rid, 'single')
                    failed += 1
                    if n >= MAX_FAILS:
                        ingested[rid] = datetime.now().isoformat()   # 포기 — 더 태우지 않는다
                        log(f'  ⚠️  응답 해석 실패 {n}회 — 포기')
                    else:
                        log(f'  ⚠️  응답 해석 실패 ({n}/{MAX_FAILS}) — 다음 실행에서 다시')
                else:
                    save_ok(conn, rid, res, 'single')
                    ingested[rid] = datetime.now().isoformat()
                    processed += 1
                consecutive_429_errors = 0
                if (processed + failed) % 10 == 0:
                    state['ingested'] = ingested
                    save_state(state)
            except DailyQuotaExhausted as e:
                log(f'\n  ⏸  {e}')
                log(f'  ℹ️  내일 다시 실행하면 자동으로 이어서 처리됩니다.')
                quota_out = True
                break
            except Exception as e:
                log(f'  ❌ 오류: {e}')
                errors += 1
                if '429' in str(e) or 'RESOURCE_EXHAUSTED' in str(e):
                    consecutive_429_errors += 1
                    if consecutive_429_errors >= 3:
                        log('\n  🚨 연속적인 429 에러 발생. 일일 할당량이 소진된 것으로 간주하고 종료합니다.')
                        quota_out = True
                        break
                    log('  ⏸  Rate limit — 60초 대기...')
                    time.sleep(60)
        state['ingested'] = ingested
        save_state(state)

    # ── backfill (v4.5): 예전에 처리됐지만 wiki_extract 에 없는(또는 seed 뿐인) 소스를 묶어서 다시 추출 ──
    bf_left = None
    if not (render_only or full_mode or no_backfill or quota_out or limit):
        cap = backfill_max()
        today = wc._today()
        bf = state.get('backfill') or {}
        if bf.get('date') != today:
            bf = {'date': today, 'calls': 0}
        store = load_store(conn)
        targets = [s for s in sources if backfill_source(s, ingested, store)]
        log(f'\n🧩 backfill: 대상 {len(targets)}건 · 오늘 {bf["calls"]}/{cap}회 사용')
        while targets and bf['calls'] < cap:
            bs = batch_size()
            batch, targets = targets[:bs], targets[bs:]
            try:
                got = extract_batch(batch)
            except DailyQuotaExhausted as e:
                log(f'  ⏸  {e}')
                targets = batch + targets
                break
            except Exception as e:
                log(f'  ❌ backfill 오류: {e} — 이번 실행 backfill 중단')
                errors += 1
                targets = batch + targets
                break
            bf['calls'] += 1
            bf_calls += 1
            for s in batch:
                res = got.get(s['notion_id'])
                if res is None:
                    save_fail(conn, s['notion_id'], 'batch')
                    failed += 1
                else:
                    save_ok(conn, s['notion_id'], res, 'batch')
                    bf_done += 1
            state['backfill'] = bf
            save_state(state)
            log(f'  [{bf["calls"]}/{cap}] {len(got)}/{len(batch)}건 기록')
        store = load_store(conn)
        bf_left = sum(1 for s in sources if backfill_source(s, ingested, store))
        state['backfill'] = bf
        log(f'  backfill 남은 대상 {bf_left}건')

    # ── 페이지 재렌더 (wiki_extract 전체 기준, 내용 같으면 안 씀) ──
    log(f'\n📝 Wiki 페이지 렌더 중...')
    entity_data, concept_data, ent_updated, con_updated, idx_w, empty_w = render_all(conn, sources)
    log(f'  엔티티 {len(entity_data)}개 중 {ent_updated}개 · 개념 {len(concept_data)}개 중 {con_updated}개 · index {"갱신" if idx_w else "그대로"}'
        + (f' · 항목 0 안내 페이지 {empty_w}개' if empty_w else ''))

    state['ingested'] = ingested
    state['last_run'] = datetime.now().isoformat()
    state['entities'] = {k: len(v) for k, v in sorted(entity_data.items())}
    state['concepts'] = {k: len(v) for k, v in sorted(concept_data.items())}
    save_state(state)

    elapsed = round(time.time() - start)
    log(f'\n🎉 Wiki Ingest 완료!')
    log(f'  처리: {processed}개 | 해석 실패: {failed}개 | 오류: {errors}개 | backfill: {bf_calls}회 {bf_done}건')
    log(f'  소요시간: {elapsed}초')

    if processed or failed or bf_calls or ent_updated or con_updated or empty_w:
        write_wiki_log('ingest', f'{processed}개 소스 처리' + (f' · backfill {bf_done}건' if bf_calls else ''), {
            '처리': f'{processed}개',
            '해석 실패': f'{failed}개',
            '오류': f'{errors}개',
            'backfill': f'{bf_calls}회 {bf_done}건' + (f' (남은 {bf_left}건)' if bf_left is not None else ''),
            '엔티티 갱신': f'{ent_updated}/{len(entity_data)}개',
            '개념 갱신': f'{con_updated}/{len(concept_data)}개',
            '소요시간': f'{elapsed}초',
            '모드': '렌더만' if render_only else ('전체' if full_mode else '증분'),
        })

    print('WIKI_RESULT:' + json.dumps({
        'processed': processed, 'errors': errors, 'failed': failed,
        'entities_updated': ent_updated, 'concepts_updated': con_updated,
        'entities': len(entity_data), 'concepts': len(concept_data), 'empty_pages': empty_w,
        'backfill_calls': bf_calls, 'backfill_done': bf_done, 'backfill_left': bf_left,
        'elapsed': elapsed,
    }))
    return 0

if __name__ == '__main__':
    sys.exit(main())
