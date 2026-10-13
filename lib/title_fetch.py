#!/usr/bin/env python3
"""
링크 원문 제목 조회 (v4.8) — kakao_ingest.py 전용. 표준 라이브러리만 쓴다.

    lookup_title(url) -> (title 또는 None, reason)
        reason: 'ok' · 'no_id' · 'private' · 'not_html' · 'no_title' · 'bad_title' · 'http_<코드>' · 'timeout' · 'network' · 'parse'

경로
  - 노션(<sub>.notion.site · notion.so · app.notion.com): 공개 페이지 API `syncRecordValuesMain` → block.properties.title
    (2026-10-13 꿀팁 2차에서 44건 중 43건 확인한 방법. 비공개 페이지는 값이 없어 'private')
  - 유튜브(youtube.com · youtu.be): oEmbed JSON (`/oembed?format=json&url=`) — YouTube Data API 할당량을 쓰지 않는다
  - 그 밖: HTML 앞부분(최대 512KB)의 og:title → twitter:title → <title>

원칙
  - 요청마다 timeout 8초, 재시도 없음. 실패는 (None, reason) 으로 돌려준다 — 예외를 밖으로 던지지 않는다.
  - 로그인·차단·일반 문구(「Notion」, 「로그인」, 「Just a moment...」 등)는 제목으로 쓰지 않는다('bad_title').
  - 돌려주는 제목은 clean_title() 을 거친다: NFC · 공백 정리 · 앞 이모지·기호 제거 · `|` → ` — ` · `[[`·`]]` 제거 · 120자.
    (`|`·`[[`·`]]` 는 Obsidian 링크 [[파일|별칭]] 을 깨뜨린다 — scripts/retitle_tips.py 와 같은 금지 규칙)
"""
import html, json, re, socket, unicodedata, urllib.error, urllib.request
from urllib.parse import urlsplit, parse_qsl, quote

TIMEOUT = 8
MAX_BYTES = 512 * 1024
MAX_LEN = 120
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/129.0 Safari/537.36')

_HEX32_END = re.compile(r'([0-9a-f]{32})$', re.I)
_UUID_END = re.compile(r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$', re.I)
_HEX32 = re.compile(r'^[0-9a-f]{32}$', re.I)

# 제목으로 쓰면 안 되는 문구(소문자 비교, 전체 일치)
_BAD_EXACT = {
    'notion', 'notion – the all-in-one workspace for your notes, tasks, wikis, and databases.',
    'youtube', 'google drive', 'google docs', 'google 드라이브', 'google 문서', 'naver blog', '네이버 블로그',
    'login', 'log in', 'sign in', '로그인', 'just a moment...', 'attention required!', 'access denied',
    '403 forbidden', '404 not found', 'page not found', 'not found', 'error', 'untitled', '제목 없음',
}
# 이 말로 시작하면 버린다(로그인·차단 화면)
_BAD_PREFIX = ('sign in', 'log in', '로그인', 'google 드라이브 - 로그인', 'google drive - sign in', 'just a moment',
               'notion —', 'notion –', 'notion -')   # 노션 HTML 의 일반 제목 「Notion | Where teams and agents work together」
# 끝에 붙는 사이트 이름(대소문자 무시)
_SUFFIXES = (' : 네이버 블로그', ' - youtube', ' - google drive', ' - google docs', ' - google 드라이브', ' - google 문서')


def _nfc(s):
    return unicodedata.normalize('NFC', s or '')


_DECOR = ('So', 'Sk', 'Mn', 'Me', 'Cf', 'Co', 'Cs')   # 이모지·장식 기호·변형 선택자·ZWJ


def _strip_leading_symbols(t):
    """앞쪽 이모지·기호·장식 문자를 뗀다(🎬 · ⚡ · ✅ · ▶ 등). 글자·숫자·괄호·따옴표에서 멈춘다."""
    i = 0
    while i < len(t):
        ch = t[i]
        cat = unicodedata.category(ch)
        if ch.isspace() or cat in _DECOR or cat in ('Sm', 'Sc') or ch in '|·•-–—':
            i += 1
            continue
        break
    return t[i:]


def _strip_trailing_decor(t):
    """끝의 이모지·장식 기호만 뗀다(「가이드💙」·「가이드! ✨」). 마침표·느낌표·괄호는 둔다."""
    j = len(t)
    while j > 0 and (t[j - 1].isspace() or unicodedata.category(t[j - 1]) in _DECOR):
        j -= 1
    return t[:j]


def clean_title(t):
    """조회한 제목을 장부·파일명에 쓸 수 있게 정리한다. 쓸 수 없으면 None."""
    if not t:
        return None
    t = _nfc(html.unescape(str(t)))
    t = re.sub(r'\s+', ' ', t).strip()
    low = t.lower()
    for suf in _SUFFIXES:
        if low.endswith(suf):
            t = t[:-len(suf)].rstrip()
            low = t.lower()
    t = _strip_trailing_decor(_strip_leading_symbols(t))
    t = t.replace('[[', '[').replace(']]', ']')
    t = re.sub(r'\s*[|｜]\s*', ' — ', t)
    t = re.sub(r'\s+', ' ', t).strip(' —')
    if len(t) > MAX_LEN:
        t = t[:MAX_LEN].rstrip()
    low = t.lower()
    if len(t) < 2 or low in _BAD_EXACT or any(low.startswith(p) for p in _BAD_PREFIX):
        return None
    return t


# ── 노션 ──
def notion_page_id(url):
    """노션 URL → 페이지 uuid(소문자, 하이픈). 못 찾으면 None. ?p=<id>(미리보기 창)가 있으면 그것이 우선."""
    s = urlsplit(url)
    for k, v in parse_qsl(s.query):
        if k == 'p' and _HEX32.match(v):
            h = v.lower()
            return f'{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}'
    segs = [p for p in s.path.split('/') if p]
    if not segs:
        return None
    last = segs[-1]
    m = _UUID_END.search(last)
    if m:
        return m.group(1).lower()
    m = _HEX32_END.search(last)          # 'Opus-5-5-3edfd99f…' — 하이픈을 지우지 않고 끝 32자만 본다
    if m:
        h = m.group(1).lower()
        return f'{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}'
    return None


def notion_api_base(url):
    host = urlsplit(url).netloc.lower()
    if host.endswith('.notion.site'):
        return f'https://{host}'
    if host in ('notion.so', 'www.notion.so', 'app.notion.com'):
        return 'https://www.notion.so'
    return None


def is_notion(url):
    return notion_api_base(url) is not None


def is_youtube(url):
    host = urlsplit(url).netloc.lower()
    return host in ('youtu.be', 'youtube.com', 'www.youtube.com', 'm.youtube.com', 'music.youtube.com')


def _open(req, opener):
    return (opener or urllib.request.urlopen)(req, timeout=TIMEOUT)


def _read(resp):
    data = resp.read(MAX_BYTES)
    return data if isinstance(data, bytes) else bytes(data)


def _notion_title_from(data, pid):
    blocks = ((data or {}).get('recordMap') or {}).get('block') or {}
    rec = blocks.get(pid) or blocks.get(pid.replace('-', '')) or {}
    val = rec.get('value') or {}
    if isinstance(val, dict) and isinstance(val.get('value'), dict):   # 응답 형식이 한 겹 더 감싼 경우
        val = val['value']
    segs = ((val.get('properties') or {}).get('title')) if isinstance(val, dict) else None
    if not segs:
        return None
    return ''.join(seg[0] for seg in segs if isinstance(seg, list) and seg and isinstance(seg[0], str))


def fetch_notion(url, opener=None):
    pid, base = notion_page_id(url), notion_api_base(url)
    if not pid or not base:
        return None, 'no_id'
    body = json.dumps({'requests': [{'pointer': {'table': 'block', 'id': pid}, 'version': -1}]}).encode()
    req = urllib.request.Request(base + '/api/v3/syncRecordValuesMain', data=body, method='POST',
                                 headers={'Content-Type': 'application/json', 'User-Agent': UA})
    with _open(req, opener) as r:
        data = json.loads(_read(r).decode('utf-8', 'replace'))
    raw = _notion_title_from(data, pid)
    if raw is None:
        return None, 'private'
    return raw, 'ok'


def fetch_youtube(url, opener=None):
    req = urllib.request.Request('https://www.youtube.com/oembed?format=json&url=' + quote(url, safe=''),
                                 headers={'User-Agent': UA})
    with _open(req, opener) as r:
        data = json.loads(_read(r).decode('utf-8', 'replace'))
    return data.get('title'), 'ok'


_META_RES = [re.compile(p, re.I | re.S) for p in (
    r'<meta[^>]+property=["\']og:title["\'][^>]*content=["\']([^"\']*)["\']',
    r'<meta[^>]+content=["\']([^"\']*)["\'][^>]*property=["\']og:title["\']',
    r'<meta[^>]+name=["\']twitter:title["\'][^>]*content=["\']([^"\']*)["\']',
    r'<meta[^>]+content=["\']([^"\']*)["\'][^>]*name=["\']twitter:title["\']',
    r'<title[^>]*>(.*?)</title>',
)]


def _charset(ctype, head):
    m = re.search(r'charset=["\']?([\w-]+)', ctype or '', re.I) or re.search(rb'<meta[^>]+charset=["\']?([\w-]+)', head, re.I)
    if not m:
        return 'utf-8'
    cs = m.group(1)
    return cs.decode('ascii', 'ignore') if isinstance(cs, bytes) else cs


def title_from_html(raw, ctype=''):
    cs = _charset(ctype, raw[:4096])
    try:
        text = raw.decode(cs, 'replace')
    except LookupError:
        text = raw.decode('utf-8', 'replace')
    for rx in _META_RES:
        m = rx.search(text)
        if m and m.group(1).strip():
            return m.group(1)
    return None


def fetch_html(url, opener=None):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'text/html,application/xhtml+xml',
                                               'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8'})
    with _open(req, opener) as r:
        ctype = (r.headers.get('Content-Type') if getattr(r, 'headers', None) else '') or ''
        if 'html' not in ctype.lower():
            return None, 'not_html'
        raw = _read(r)
    t = title_from_html(raw, ctype)
    return (t, 'ok') if t else (None, 'no_title')


def lookup_title(url, opener=None):
    """(정리된 제목 또는 None, reason). 예외를 던지지 않는다."""
    try:
        if is_notion(url):
            raw, why = fetch_notion(url, opener)
        elif is_youtube(url):
            raw, why = fetch_youtube(url, opener)
        else:
            raw, why = fetch_html(url, opener)
    except urllib.error.HTTPError as e:
        return None, f'http_{e.code}'
    except (socket.timeout, TimeoutError):
        return None, 'timeout'
    except urllib.error.URLError as e:
        return None, 'timeout' if isinstance(getattr(e, 'reason', None), (socket.timeout, TimeoutError)) else 'network'
    except (ValueError, KeyError, TypeError, AttributeError):
        return None, 'parse'
    except Exception:
        return None, 'network'
    if raw is None:
        return None, why
    t = clean_title(raw)
    return (t, 'ok') if t else (None, 'bad_title')


if __name__ == '__main__':
    import sys
    for u in sys.argv[1:]:
        print(lookup_title(u), u)
