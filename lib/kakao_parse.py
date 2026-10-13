#!/usr/bin/env python3
"""
카카오톡 '나와의 채팅' CSV → 링크 후보 추출·정규화 (순수 함수, 네트워크 없음)

CSV 형식 (카카오톡 PC 내보내기, UTF-8 BOM):
    Date,User,Message
    2026-03-08 09:12:33,"안진훈","https://github.com/... 메모"

공개 API:
    read_kakao_csv(path)            -> [{'date','user','message'}]
    extract_urls(text)              -> [url]
    clean_url(url)                  -> 트래킹 파라미터 제거한 저장용 URL
    url_key(url)                    -> 중복 판정용 정규화 키
    parse_links(path, since=None)   -> [{'date','url','key','message'}]  (CSV 내부 중복 제거)
    classify(url, *texts)           -> (category, tags)  (v4.9 — guess_meta·scripts/recategorize_tips.py 공용 규칙)
    guess_meta(url, message, fetched_title=None) -> {'title','category','tags','memo','source','title_src'}
        title_src (v4.8): 'message'(사용자가 붙인 글) · 'github'(레포 이름) · 'guess'(URL 추정 — kakao_ingest 가 원문 제목을 조회) · 'fetched'(조회한 제목)

지침서: docs/tasks/2026-09-06-kakao-tips-ingest.md §3
"""
import csv, os, re, unicodedata
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode, unquote

# 제거 대상 쿼리 파라미터 (지침서 §3, 검증 완료 — 그대로 이식)
STRIP_PARAMS = {
    'fbclid', 'utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term',
    'pvs', 'si', 'mcp_token', '_phid', '_phsrc', 'source', 'shareKey', 'navType',
    'pli', 'usp', 'gclid', 'igshid',
}

# 추정 제목에 붙는 메모 표지 (scripts/retitle_tips.py AUTO_MEMOS 와 같은 문구 — 바꾸지 말 것)
NEED_TITLE_MARK = '원문 확인 필요'

# 카테고리 값 목록 (v3.x 노션 select 옵션 그대로 — 장부 tips.category·Obsidian 노트·시트에 같은 값을 쓴다)
CATEGORIES = ['프롬프트', '개발툴', '기타', '모델/LLM', '뉴스/트렌드', '지식관리', '사업/마케팅']

_URL_RE = re.compile(r'https?://[^\s"<>\)\]\'`]+')
_TRAIL = '.,;:!?)]}\'"'


def nfc(s):
    return unicodedata.normalize('NFC', s or '')


def read_kakao_csv(path):
    with open(path, encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        out.append({
            'date': (r.get('Date') or '').strip(),
            'user': nfc((r.get('User') or '').strip()),
            'message': nfc(r.get('Message') or ''),
        })
    return out


def extract_urls(text):
    return [u.rstrip(_TRAIL) for u in _URL_RE.findall(text or '')]


def clean_url(url):
    """저장용: 스킴/호스트는 유지, 트래킹 파라미터만 제거."""
    url = url.strip().rstrip(_TRAIL)
    s = urlsplit(url)
    q = [(k, v) for k, v in parse_qsl(s.query, keep_blank_values=True) if k not in STRIP_PARAMS]
    return urlunsplit((s.scheme, s.netloc, s.path, urlencode(q), ''))


def url_key(url):
    """중복 판정용: https 통일, 소문자 호스트, www. 제거, 끝 슬래시 제거, 파라미터 정리, fragment 제거."""
    s = urlsplit(clean_url(url))
    host = s.netloc.lower()
    if host.startswith('www.'):
        host = host[4:]
    path = s.path.rstrip('/') or ''
    q = sorted(parse_qsl(s.query, keep_blank_values=True))
    return urlunsplit(('https', host, path, urlencode(q), ''))


def host_of(url):
    h = urlsplit(url).netloc.lower()
    return h[4:] if h.startswith('www.') else h


def parse_links(path, since=None):
    """CSV → 링크 목록. since('YYYY-MM-DD') 이전 메시지는 제외. CSV 내부 중복은 첫 등장만 유지."""
    seen, out = set(), []
    for m in read_kakao_csv(path):
        if since and m['date'][:10] < since:
            continue
        for u in extract_urls(m['message']):
            k = url_key(u)
            if k in seen:
                continue
            seen.add(k)
            out.append({'date': m['date'], 'url': clean_url(u), 'key': k, 'message': m['message']})
    return out


# ── 제목/카테고리/태그 추정 (규칙 기반, 1차) ──
# (v4.9) 한글 표기도 같은 태그로 — v4.8 부터 원문 제목(대개 한글)이 들어오므로 「클로드」·「노션」 등을 잡아야 한다.
#   태그 이름·순서는 바꾸지 않는다(장부 tips.tags·노트 keywords·검색 필터가 이 값을 쓴다). 「커서」는 일반 명사라 넣지 않는다.
_KEYWORD_TAGS = [
    (r'(?:claude|클로드)[-_ ]?(?:code|코드)', 'ClaudeCode'), (r'claude|클로드', 'Claude'),
    (r'antigravity|안티그래비티', 'Antigravity'),
    (r'gemini|제미나이|제미니', 'Gemini'), (r'gpt|openai|chatgpt|오픈\s?ai|지피티', 'GPT'), (r'ollama|올라마', 'Ollama'),
    (r'notion|노션', 'Notion'), (r'obsidian|옵시디언', 'Obsidian'), (r'prompt|프롬프트', '프롬프트'),
    (r'mcp', 'MCP'), (r'agent|에이전트', 'Agent'), (r'cursor', 'Cursor'), (r'github\.com', 'GitHub'),
    (r'youtube\.com|youtu\.be', 'YouTube'), (r'huggingface|허깅\s?페이스', 'HuggingFace'),
]


def is_notion_host(host):
    """노션에 올린 페이지 주소(notion.site·notion.so·app.notion.com). notion.com(노션 회사 사이트)은 아니다."""
    return host.endswith('notion.site') or host in ('notion.so', 'app.notion.com')


def _tag_text(url, *texts):
    """태그 판정 글자(소문자). (v4.9) 노션 페이지 주소는 호스트를 뺀다 — 노션에 올린 자료일 뿐 노션 이야기가 아니다
    (v4.8 까지 노션 주소 꿀팁이 전부 Notion 태그 → 「지식관리」로 잡혔다)."""
    u = url or ''
    if is_notion_host(host_of(u)):
        s = urlsplit(u)
        u = urlunsplit(('', '', s.path, s.query, ''))
    return ' '.join([u] + [t or '' for t in texts]).lower()


def classify(url, *texts):
    """(category, tags). texts = 사용자가 붙인 글·원문 제목 등 URL 밖의 글자.
    guess_meta 와 scripts/recategorize_tips.py(기존 꿀팁 재분류)가 같이 쓴다 — 규칙은 여기 한 곳."""
    text = _tag_text(url, *texts)
    tags = []
    for pat, tag in _KEYWORD_TAGS:
        if re.search(pat, text) and tag not in tags:
            tags.append(tag)
    category = '개발툴' if 'github.com' in host_of(url or '') else '기타'
    # 카테고리 세부 보정
    if any(t in tags for t in ('프롬프트',)):
        category = '프롬프트'
    elif any(t in tags for t in ('ClaudeCode', 'Antigravity', 'Cursor', 'MCP', 'Ollama')) and category == '기타':
        category = '개발툴'
    elif any(t in tags for t in ('Notion', 'Obsidian')) and category == '기타':
        category = '지식관리'
    elif any(t in tags for t in ('GPT', 'Gemini', 'Claude')) and category == '기타':
        category = '모델/LLM'
    assert category in CATEGORIES
    return category, tags


def _slug_title(url):
    """URL 마지막 경로 조각에서 제목 추정. notion.site 슬러그는 끝 32자리 hex 제거."""
    s = urlsplit(url)
    seg = [unquote(p) for p in s.path.split('/') if p]
    if not seg:
        return ''
    last = seg[-1]
    last = re.sub(r'-?[0-9a-f]{32}$', '', last)          # notion id
    last = re.sub(r'\.(html?|md|pdf)$', '', last, flags=re.I)
    return last.replace('-', ' ').replace('_', ' ').strip()


def guess_meta(url, message='', fetched_title=None):
    """fetched_title(v4.8): kakao_ingest 가 원문에서 조회한 제목(lib/title_fetch.clean_title 을 거친 값).
    주면 그 제목을 쓰고 메모를 비우며, 태그·카테고리도 제목 글자까지 보고 정한다. 메시지에 사용자가 붙인 글이 있으면 그것이 여전히 우선."""
    host = host_of(url)
    memo = ''
    title_src = 'guess'
    if 'github.com' in host:
        parts = [p for p in urlsplit(url).path.split('/') if p]
        repo = parts[1] if len(parts) >= 2 else (parts[0] if parts else host)
        title = f'{repo} (GitHub 레포)'
        title_src = 'github'
    elif is_notion_host(host):
        slug = _slug_title(url)
        if slug and re.search(r'[가-힣]', slug):
            title = slug
        else:
            title = f'노션 자료 ({slug[:40]})' if slug else '노션 자료 (제목 미확인)'
            memo = f'슬러그에 한글 제목 없음 — {NEED_TITLE_MARK}'
    elif 'youtube.com' in host or 'youtu.be' in host:
        title = '유튜브 영상 (제목 미확인)'
        memo = NEED_TITLE_MARK
    else:
        slug = _slug_title(url)
        title = slug[:80] if slug else host
        if not slug:
            memo = NEED_TITLE_MARK

    if fetched_title:
        title = fetched_title
        title_src = 'fetched'
        memo = ''

    category, tags = classify(url, message, fetched_title)

    # 메시지에 URL 외 텍스트가 있으면 제목 후보로 우선 (사용자가 직접 붙인 메모)
    extra = re.sub(r'https?://\S+', '', message or '').strip()
    extra = re.sub(r'\s+', ' ', extra)
    if 4 <= len(extra) <= 80:
        title = extra
        title_src = 'message'
        memo = ''

    return {'title': nfc(title), 'category': category, 'tags': tags, 'memo': memo, 'source': host, 'title_src': title_src}


if __name__ == '__main__':
    import sys
    p = sys.argv[1] if len(sys.argv) > 1 else None
    since = sys.argv[2] if len(sys.argv) > 2 else None
    if not p:
        print('usage: kakao_parse.py <csv> [since YYYY-MM-DD]'); sys.exit(1)
    links = parse_links(p, since)
    print(f'{len(links)} links')
    for l in links[:20]:
        g = guess_meta(l['url'], l['message'])
        print(f"{l['date'][:10]} | {g['category']:6} | {g['title'][:40]:40} | {l['url'][:60]}")
