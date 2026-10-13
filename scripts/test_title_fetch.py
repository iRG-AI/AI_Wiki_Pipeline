#!/usr/bin/env python3
"""lib/title_fetch.py 회귀 테스트 (v4.8). 실제 네트워크 0회 — 가짜 opener 로 응답을 흉내 낸다.

    /opt/homebrew/bin/python3 scripts/test_title_fetch.py

지키는 것:
  1) 노션 URL → 페이지 id: 슬러그 안 숫자(「Opus-5-5-…」)에 속지 않고 끝 32자리만 · ?p= 우선 · uuid 형식 · id 없으면 no_id
  2) 노션은 공개 API(POST syncRecordValuesMain), 유튜브는 oEmbed, 그 밖은 HTML(og:title → twitter:title → <title>)
  3) 비공개 노션(값 없음)·로그인/차단 문구·HTML 아닌 응답·HTTP 오류·시간 초과는 (None, reason) — 예외를 던지지 않는다
  4) 제목 정리: 앞 이모지 제거 · `|` → ` — ` · `[[`·`]]` 제거 · 공백 정리 · 사이트 꼬리 제거 · 120자
"""
import io, json, os, socket, sys, unicodedata, urllib.error

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'lib'))
import urllib.request
real_calls = []
def _no_net(*a, **k):
    real_calls.append(a[0] if a else k)
    raise RuntimeError('네트워크 요청 금지 (테스트)')
urllib.request.urlopen = _no_net
import title_fetch as tf

results = []
def check(name, cond, detail=''):
    results.append(bool(cond))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f'  — {detail}' if detail and not cond else ''), flush=True)


class Resp(io.BytesIO):
    def __init__(self, body, ctype='text/html; charset=utf-8'):
        super().__init__(body if isinstance(body, bytes) else body.encode('utf-8'))
        self.headers = {'Content-Type': ctype}
    def __enter__(self): return self
    def __exit__(self, *a): self.close()


class Opener:
    """요청을 기록하고 정해 둔 응답(또는 예외)을 돌려준다."""
    def __init__(self, result):
        self.result, self.reqs = result, []
    def __call__(self, req, timeout=None):
        self.reqs.append({'url': req.full_url, 'method': req.get_method(), 'data': req.data, 'timeout': timeout})
        r = self.result(req) if callable(self.result) else self.result
        if isinstance(r, BaseException):
            raise r
        return r


def notion_body(pid, title_segs, nested=False):
    val = {'id': pid, 'properties': {'title': title_segs}}
    rec = {'value': {'value': val, 'role': 'reader'}} if nested else {'value': val, 'role': 'reader'}
    return json.dumps({'recordMap': {'block': {pid: rec}}})


def main():
    print('▶ 노션 페이지 id')
    pid_of = tf.notion_page_id
    check('슬러그 끝 32자리 (Opus-5-5-…)', pid_of('https://app.notion.com/p/Opus-5-5-3edfd99f0e5f81edbaa1f72b0401fef9')
          == '3edfd99f-0e5f-81ed-baa1-f72b0401fef9')
    check('id 만 있는 경로', pid_of('https://grand-count-2aa.notion.site/3ee50157ef1380e69c02d2aaef50a334')
          == '3ee50157-ef13-80e6-9c02-d2aaef50a334')
    check('uuid 형식 그대로', pid_of('https://www.notion.so/x/3ee50157-ef13-80e6-9c02-d2aaef50a334')
          == '3ee50157-ef13-80e6-9c02-d2aaef50a334')
    check('?p= 가 경로보다 우선', pid_of('https://www.notion.so/ws/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa?p=3ee50157ef1380e69c02d2aaef50a334&pm=s')
          == '3ee50157-ef13-80e6-9c02-d2aaef50a334')
    check('대문자 hex 는 소문자로', pid_of('https://x.notion.site/A-3EE50157EF1380E69C02D2AAEF50A334')
          == '3ee50157-ef13-80e6-9c02-d2aaef50a334')
    check('id 없음 → None', pid_of('https://x.notion.site/') is None and pid_of('https://x.notion.site/about') is None)
    check('API 주소: notion.site 는 그 하위 도메인, 나머지는 www.notion.so',
          tf.notion_api_base('https://abc-1.notion.site/a') == 'https://abc-1.notion.site'
          and tf.notion_api_base('https://app.notion.com/p/x') == 'https://www.notion.so'
          and tf.notion_api_base('https://notion.so/x') == 'https://www.notion.so'
          and tf.notion_api_base('https://example.com/notion') is None)

    print('▶ 노션 조회')
    pid = '3edfd99f-0e5f-81ed-baa1-f72b0401fef9'
    url = 'https://app.notion.com/p/Opus-5-5-3edfd99f0e5f81edbaa1f72b0401fef9'
    op = Opener(Resp(notion_body(pid, [['🎬 Opus 5.5 '], ['모션그래픽', [['b']]], [' 프롬프트 모음']]), 'application/json'))
    t, why = tf.lookup_title(url, op)
    check('조각을 이어 붙이고 앞 이모지 제거', (t, why) == ('Opus 5.5 모션그래픽 프롬프트 모음', 'ok'), (t, why))
    r = op.reqs[0]
    body = json.loads(r['data'])
    check('POST https://www.notion.so/api/v3/syncRecordValuesMain · block · version -1',
          r['method'] == 'POST' and r['url'] == 'https://www.notion.so/api/v3/syncRecordValuesMain'
          and body == {'requests': [{'pointer': {'table': 'block', 'id': pid}, 'version': -1}]}, r)
    check('timeout 8초', r['timeout'] == 8)
    op = Opener(Resp(notion_body(pid, [['한 겹 더 감싼 응답']], nested=True), 'application/json'))
    check('value.value 형식도 읽는다', tf.lookup_title(url, op) == ('한 겹 더 감싼 응답', 'ok'))
    op = Opener(Resp(json.dumps({'recordMap': {'block': {pid: {'role': 'none'}}}}), 'application/json'))
    check('비공개(값 없음) → private', tf.lookup_title(url, op) == (None, 'private'))
    op = Opener(Resp(json.dumps({'recordMap': {}}), 'application/json'))
    check('recordMap 비어 있음 → private', tf.lookup_title(url, op) == (None, 'private'))
    op = Opener(Resp(notion_body(pid, [['Notion']]), 'application/json'))
    check('제목이 「Notion」 → bad_title', tf.lookup_title(url, op) == (None, 'bad_title'))
    op = Opener(Resp(b'<html>not json</html>', 'text/html'))
    check('JSON 아님 → parse', tf.lookup_title(url, op) == (None, 'parse'))
    op = Opener(lambda req: None)
    check('id 없는 노션 URL 은 요청하지 않는다(no_id)', tf.lookup_title('https://x.notion.site/about', op) == (None, 'no_id') and not op.reqs)

    print('▶ 유튜브 oEmbed')
    op = Opener(Resp(json.dumps({'title': 'Claude Code 30분 완성 | 실전편', 'author_name': 'x'}), 'application/json'))
    t, why = tf.lookup_title('https://youtu.be/abc123XYZ00', op)
    check('oEmbed 제목 · `|` → ` — `', (t, why) == ('Claude Code 30분 완성 — 실전편', 'ok'), (t, why))
    check('oEmbed 주소(URL 인코딩)', op.reqs[0]['url'] == 'https://www.youtube.com/oembed?format=json&url=https%3A%2F%2Fyoutu.be%2Fabc123XYZ00', op.reqs)
    op = Opener(urllib.error.HTTPError('u', 401, 'Unauthorized', {}, None))
    check('비공개 영상(401) → http_401', tf.lookup_title('https://www.youtube.com/watch?v=x', op) == (None, 'http_401'))

    print('▶ 일반 HTML')
    page = ('<html><head><title>사이트 제목</title>'
            '<meta content="AI 에이전트 &amp; 하네스 정리" property="og:title"></head></html>')
    check('og:title(content 가 앞) 우선 · 엔티티 해제', tf.lookup_title('https://example.com/a', Opener(Resp(page))) == ('AI 에이전트 & 하네스 정리', 'ok'))
    page = '<meta name="twitter:title" content="트위터 제목"><title>T</title>'
    check('og 없으면 twitter:title', tf.lookup_title('https://example.com/a', Opener(Resp(page))) == ('트위터 제목', 'ok'))
    page = '<html><head><title>\n  클로드   스킬\n 모음 </title></head>'
    check('그다음 <title> · 공백 정리', tf.lookup_title('https://example.com/a', Opener(Resp(page))) == ('클로드 스킬 모음', 'ok'))
    euc = '<html><head><meta charset="euc-kr"><title>한글 제목</title></head>'.encode('euc-kr')
    check('meta charset(euc-kr) 해석', tf.lookup_title('https://example.com/a', Opener(Resp(euc, 'text/html'))) == ('한글 제목', 'ok'))
    check('네이버 블로그 꼬리 제거', tf.lookup_title('https://m.blog.naver.com/a/1',
          Opener(Resp('<title>바이브코딩 후기 : 네이버 블로그</title>'))) == ('바이브코딩 후기', 'ok'))
    check('제목 없음 → no_title', tf.lookup_title('https://example.com/a', Opener(Resp('<html><body>x</body></html>'))) == (None, 'no_title'))
    check('HTML 아님(PDF) → not_html', tf.lookup_title('https://example.com/a.pdf', Opener(Resp(b'%PDF', 'application/pdf'))) == (None, 'not_html'))
    check('로그인 화면 → bad_title', tf.lookup_title('https://drive.google.com/x',
          Opener(Resp('<title>Google Drive - Sign in</title>'))) == (None, 'bad_title'))
    check('Cloudflare 대기 화면 → bad_title', tf.lookup_title('https://example.com/a',
          Opener(Resp('<title>Just a moment...</title>'))) == (None, 'bad_title'))

    print('▶ 실패는 예외 없이 (None, reason)')
    u = 'https://example.com/a'
    check('HTTP 404 → http_404', tf.lookup_title(u, Opener(urllib.error.HTTPError(u, 404, 'NF', {}, None))) == (None, 'http_404'))
    check('socket.timeout → timeout', tf.lookup_title(u, Opener(socket.timeout('t'))) == (None, 'timeout'))
    check('URLError(timeout) → timeout', tf.lookup_title(u, Opener(urllib.error.URLError(socket.timeout('t')))) == (None, 'timeout'))
    check('URLError(DNS) → network', tf.lookup_title(u, Opener(urllib.error.URLError('nodename nor servname'))) == (None, 'network'))
    check('그 밖 예외 → network', tf.lookup_title(u, Opener(ConnectionResetError())) == (None, 'network'))
    check('기본 opener 는 urllib.request.urlopen (테스트에서는 막혀 network)', tf.lookup_title(u) == (None, 'network') and len(real_calls) == 1)

    print('▶ 제목 정리')
    ct = tf.clean_title
    check('앞 이모지·기호 여러 개', ct('🎁✨ ▶ 무료 배포 키트') == '무료 배포 키트', ct('🎁✨ ▶ 무료 배포 키트'))
    check('[[ ]] 제거 · ｜ 도 바꿈', ct('[[노트]] 정리 ｜ 2편') == '[노트] 정리 — 2편', ct('[[노트]] 정리 ｜ 2편'))
    check('앞 숫자·괄호·따옴표는 그대로', ct('3분 정리') == '3분 정리' and ct('[가이드] 설치') == '[가이드] 설치' and ct('"인용" 제목') == '"인용" 제목')
    check('120자 자르기', len(ct('가' * 300)) == 120)
    check('빈 값·1글자·일반 문구 → None', ct('') is None and ct('가') is None and ct('YouTube') is None and ct('로그인') is None and ct('  Notion ') is None)
    check('결과에 | · [[ · ]] 가 남지 않는다', all(x not in (ct('a|b [[c]] d||e') or '') for x in ('|', '[[', ']]')), ct('a|b [[c]] d||e'))
    check('NFD 입력은 NFC 로', ct(unicodedata.normalize('NFD', '가나') + ' 제목') == '가나 제목')
    check('끝 이모지 제거 · 느낌표는 둔다', ct('Gems 완벽 활용 가이드💙') == 'Gems 완벽 활용 가이드' and ct('공식 가이드! ✨') == '공식 가이드!',
          (ct('Gems 완벽 활용 가이드💙'), ct('공식 가이드! ✨')))
    check('노션 HTML 일반 제목 → None', ct('Notion | Where teams and agents work together') is None)

    ok = all(results)
    print(f'\n{sum(results)}/{len(results)} PASS')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
