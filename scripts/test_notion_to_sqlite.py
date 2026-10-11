#!/usr/bin/env python3
"""
scripts/notion_to_sqlite.py 회귀 테스트 — 네트워크 0회, 실제 Vault·data/ 무변경.

  /opt/homebrew/bin/python3 scripts/test_notion_to_sqlite.py

가짜 노션(urlopen 교체)·임시 Vault·임시 data/ 로 돌린다. 끝에 'N/N PASS' 를 찍고 실패가 있으면 종료 코드 1.
"""
import io, json, os, shutil, sqlite3, sys, tempfile
from urllib.error import HTTPError

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, 'scripts'))
sys.path.insert(0, os.path.join(REPO_ROOT, 'lib'))
sys.path.insert(0, REPO_ROOT)

import notion_to_sqlite as m   # noqa: E402
import tips_notion as tn       # noqa: E402
import sync_obsidian as so     # noqa: E402
import library_db as ldb       # noqa: E402

VDB, TDB = 'vdb-test', 'tdb-test'
m.NOTION_DB_ID, m.TIPS_DB_ID = VDB, TDB
m.RATE_SLEEP = 0
tn.time.sleep = lambda s: None
m.time.sleep = lambda s: None


def rt(s):
    return [{'type': 'text', 'text': {'content': s}, 'plain_text': s}]


def vpage(pid, vid, title, topics, created, summary='요약 **본문**', url=None):
    return {'object': 'page', 'id': pid, 'created_time': created, 'last_edited_time': created, 'properties': {
        '영상 제목': {'id': 'title', 'title': rt(title)},
        '유튜브 채널': {'id': 'ch', 'rich_text': rt('채널')},
        '주제': {'id': 'tp', 'multi_select': [{'name': t} for t in topics]},
        '업로드 일자': {'id': 'ud', 'date': {'start': '2026-09-01'}},
        '조회수': {'id': 'vc', 'number': 100}, '구독자수': {'id': 'sc', 'number': 10},
        '영상 URL': {'id': 'vu', 'url': url if url is not None else f'https://www.youtube.com/watch?v={vid}'},
        '썸네일 URL': {'id': 'th', 'url': 'https://img/x.jpg'},
        '처리 상태': {'id': 'st', 'select': {'name': '완료'}},
        '요약 내용': {'id': 'sum1', 'rich_text': rt(summary) if summary else []},
    }}


LONG = ['가' * 1900] * 30
VPAGES = [
    vpage('aaaa-1', 'AAAAAAAAAAA', 'A 원본', ['Claude'], '2026-08-01T00:00:00.000Z'),
    vpage('aaaa-2', 'AAAAAAAAAAA', 'A 중복', ['Claude'], '2026-08-25T00:00:00.000Z'),
    vpage('aaaa-3', 'AAAAAAAAAAA', 'A 중복2', ['Gemini'], '2026-09-01T00:00:00.000Z'),
    vpage('bbbb-1', 'BBBBBBBBBBB', 'B 새것', ['Claude'], '2026-09-10T00:00:00.000Z'),
    vpage('bbbb-0', 'BBBBBBBBBBB', 'B 옛것', ['Claude'], '2026-07-10T00:00:00.000Z'),
    vpage('cccc-1', 'CCCCCCCCCCC', 'C 요약없음', ['MCP'], '2026-08-02T00:00:00.000Z', summary=''),
    vpage('dddd-1', 'DDDDDDDDDDD', 'D 긴요약', ['MCP'], '2026-08-03T00:00:00.000Z'),
    vpage('eeee-1', None, 'E 주소없음', ['기타'], '2026-08-04T00:00:00.000Z', url=''),
    vpage('ffff-1', 'FFFFFFFFFFF', 'F 쇼츠', ['기타'], '2026-08-05T00:00:00.000Z', url='https://youtube.com/shorts/FFFFFFFFFFF'),
    vpage('hhhh-0', 'HHHHHHHHHHH', 'H 옛것', ['Claude'], '2026-07-01T00:00:00.000Z'),
    vpage('hhhh-1', 'HHHHHHHHHHH', 'H 새것(노트)', ['Claude'], '2026-09-20T00:00:00.000Z'),
    vpage('gggg-1', 'GGGGGGGGGGG', 'G 가 NFD', ['가'], '2026-08-06T00:00:00.000Z'),
]
VPAGES[6]['properties']['요약 내용']['rich_text'] = [rt(x)[0] for x in LONG[:25]]   # 잘린 것처럼 25개만


def tpage(pid, title, url):
    return {'object': 'page', 'id': pid, 'created_time': '2026-09-06T00:00:00.000Z', 'last_edited_time': '2026-09-06T00:00:00.000Z',
            'properties': {'제목': {'title': rt(title)}, 'URL': {'url': url}, '출처': {'url': 'github.com'},
                           '태그': {'rich_text': rt('a,b')}, '카테고리': {'select': {'name': '개발툴'}},
                           '상태': {'select': {'name': '미확인'}}, '중요도': {'select': {'name': '중'}},
                           '저장일': {'date': {'start': '2026-09-06'}}, '메모': {'rich_text': []}}}


TPAGES = [tpage('tttt-1', '팁1', 'https://github.com/x/y?utm_source=k'), tpage('tttt-2', '팁2', 'https://example.com/z')]

BLOCKS = {
    'cccc-1': [{'type': 'image', 'image': {}},
               {'type': 'paragraph', 'paragraph': {'rich_text': rt('▶ 영상 보기: https://youtu.be/x')}},
               {'type': 'divider', 'divider': {}},
               {'type': 'heading_2', 'heading_2': {'rich_text': rt('핵심')}},
               {'type': 'bulleted_list_item', 'bulleted_list_item': {'rich_text': rt('블록에서 복원')}}],
    'tttt-1': [{'type': 'paragraph', 'paragraph': {'rich_text': rt('사용자 메모 블록')}}],
}


class Fake:
    def __init__(self):
        self.calls = []
        self.fail_plan = []   # [(predicate, code)] 한 번씩 소비
        self.vpages = VPAGES
        self.tpages = TPAGES

    def __call__(self, req, context=None, timeout=None):
        method, url = req.get_method(), req.full_url
        path = url.split('api.notion.com', 1)[1]
        self.calls.append((method, path))
        for i, (pred, code) in enumerate(self.fail_plan):
            if pred(method, path):
                self.fail_plan.pop(i)
                raise HTTPError(url, code, 'x', {}, io.BytesIO(b'{"message":"fake"}'))
        body = json.loads(req.data) if req.data else {}
        if method == 'POST' and path == f'/v1/databases/{VDB}/query':
            return self._page(self.vpages, body)
        if method == 'POST' and path == f'/v1/databases/{TDB}/query':
            return self._page(self.tpages, body)
        if method == 'GET' and '/properties/sum1' in path:
            start = int((path.split('start_cursor=')[1]) if 'start_cursor=' in path else 0)
            items = [{'object': 'property_item', 'type': 'rich_text', 'rich_text': rt(x)[0]} for x in LONG]
            chunk = items[start:start + 20]
            nxt = start + 20 if start + 20 < len(items) else None
            return self._json({'object': 'list', 'results': chunk, 'has_more': nxt is not None, 'next_cursor': str(nxt) if nxt else None})
        if method == 'GET' and path.startswith('/v1/blocks/'):
            pid = path.split('/')[3]
            blocks = BLOCKS.get(pid)
            if blocks is None:   # 요약이 속성에 있는 영상 페이지: buildBlocks 와 같은 모양
                p = next((x for x in self.vpages if x['id'] == pid), None)
                s = p['properties']['요약 내용']['rich_text'] if p else []
                if pid == 'dddd-1':
                    s = [rt(x)[0] for x in LONG]   # 본문에는 잘리지 않은 전체가 있다
                blocks = [{'type': 'image', 'image': {}}, {'type': 'divider', 'divider': {}},
                          {'type': 'paragraph', 'paragraph': {'rich_text': [dict(t) for t in s]}}]
            return self._json({'results': blocks, 'has_more': False, 'next_cursor': None})
        raise AssertionError(f'예상 밖 호출 {method} {path}')

    def _page(self, items, body):
        start = int(body.get('start_cursor') or 0)
        chunk = items[start:start + 4]   # 페이지네이션을 타게 4개씩
        nxt = start + 4 if start + 4 < len(items) else None
        return self._json({'results': chunk, 'has_more': nxt is not None, 'next_cursor': str(nxt) if nxt else None})

    @staticmethod
    def _json(obj):
        class R(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self, *a): return False
        return R(json.dumps(obj).encode())


def make_vault(root):
    def note(rel, nid, extra='video_url: https://www.youtube.com/watch?v=x'):
        p = os.path.join(root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, 'w', encoding='utf-8').write(f'---\ntitle: "t"\n{extra}\nnotion_id: {nid}\n---\n본문\n')
    note('Claude/a1.md', 'aaaa-1')
    note('Gemini/a3.md', 'aaaa-3')
    note('MCP/c1.md', 'cccc-1')
    note('Claude/h1.md', 'hhhh-1')
    note('AI 꿀팁/20260906_팁1.md', 'tttt-1', extra='link_url: https://github.com/x/y')
    note('_trash/old/x.md', 'zzzz-trash')   # _trash 는 스캔하지 않아야 한다
    # schema.md 처럼 본문 코드블록에만 예시 notion_id 가 있는 시스템 문서 — Vault id 로 세면 안 된다 (10-11 실측)
    open(os.path.join(root, 'schema.md'), 'w', encoding='utf-8').write(
        '# Schema\n\n```yaml\n---\ntitle: "영상 제목"\nvideo_url: https://youtube.com/watch?v=xxxxx\nnotion_id: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx\n---\n```\n')
    open(os.path.join(root, 'AI 꿀팁', 'README.md'), 'w', encoding='utf-8').write('# 안내\n\nnotion_id: yyyy-tip-example\n')


results = []


def check(name, cond, detail=''):
    results.append(bool(cond))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f'  — {detail}' if detail and not cond else ''), flush=True)


def run(argv, fake):
    tn.urlopen = fake
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        try:
            code = m.main(argv)
        except tn.NotionAuthError:
            code = 2
    finally:
        sys.stdout = old
    out = buf.getvalue()
    rj = next((json.loads(l[len('RESULT_JSON '):]) for l in out.splitlines() if l.startswith('RESULT_JSON ')), None)
    return code, out, rj


def main():
    tmp = tempfile.mkdtemp(prefix='n2s-test-')
    vault = os.path.join(tmp, 'vault')
    make_vault(vault)
    so.VAULT = vault
    ldb.DB_PATH = os.path.join(tmp, 'data', 'library.db')
    try:
        print('▶ dry-run')
        f = Fake()
        code, out, rj = run(['--summary-check=3'], f)
        check('dry-run 종료 0', code == 0, out[-500:])
        check('dry-run 은 파일을 쓰지 않는다', not os.path.exists(ldb.DB_PATH))
        check('노션 쓰기 요청 0건 (POST 는 query 만, PATCH/DELETE 없음)',
              all(meth == 'GET' or (meth == 'POST' and p.endswith('/query')) for meth, p in f.calls))
        check('영상 12 → videos 8 · dup 4', rj and rj['videos'] == 8 and rj['videos_dup'] == 4, rj)
        check('요약 대조 3/3 일치', rj and rj['summary_check']['match'] == 3, rj and rj['summary_check'])
        check('본문에만 notion_id 가 있는 문서는 Vault id 에서 제외 (영상 1 · 꿀팁 0 없음)',
              rj and rj['vault_missing'] == 0 and rj['tips_missing'] == 0 and rj['vault_ignored'] == 1, rj)

        print('▶ apply')
        code, out, rj = run(['--apply', '--summary-check=0'], Fake())
        check('apply 종료 0', code == 0, out[-500:])
        db = sqlite3.connect(ldb.DB_PATH)
        q = lambda s, *a: db.execute(s, a).fetchall()
        check('user_version 1', q('PRAGMA user_version')[0][0] == 1)
        a = q("SELECT record_id, topics FROM videos WHERE video_id='AAAAAAAAAAA'")
        check('A: Vault 노트가 가리키는 것 중 가장 오래된 aaaa-1 을 남긴다', a and a[0][0] == 'aaaa-1', a)
        check('A: topics 합집합 [Claude, Gemini]', a and json.loads(a[0][1]) == ['Claude', 'Gemini'], a)
        h = q("SELECT record_id FROM videos WHERE video_id='HHHHHHHHHHH'")
        check('H: 더 오래된 행이 있어도 Vault 노트가 가리키는 hhhh-1 을 남긴다', h == [('hhhh-1',)], h)
        b = q("SELECT record_id FROM videos WHERE video_id='BBBBBBBBBBB'")
        check('B: 노트 없으면 가장 오래된 bbbb-0', b == [('bbbb-0',)], b)
        d = dict(q('SELECT record_id, has_vault_note FROM videos_dup'))
        check('dup: aaaa-2(노트 없음) · aaaa-3(노트 있음) · bbbb-1 · hhhh-0', d == {'aaaa-2': 0, 'aaaa-3': 1, 'bbbb-1': 0, 'hhhh-0': 0}, d)
        c = q("SELECT summary, summary_src FROM videos WHERE record_id='cccc-1'")
        check('C: 빈 요약은 블록(구분선 뒤)에서 복원', c and c[0][1] == 'blocks' and c[0][0] == '## 핵심\n- 블록에서 복원', c)
        dd = q("SELECT length(summary) FROM videos WHERE record_id='dddd-1'")
        check('D: 25개 이상 rich_text 는 속성 재조회로 끝까지 (1900×30)', dd and dd[0][0] == 1900 * 30, dd)
        e = q("SELECT video_id FROM videos WHERE record_id='eeee-1'")
        check('E: URL 없으면 video_id NULL 로 보존', e == [(None,)], e)
        ff = q("SELECT video_id FROM videos WHERE record_id='ffff-1'")
        check('F: shorts URL 에서도 video_id', ff == [('FFFFFFFFFFF',)], ff)
        g = q("SELECT title, topics FROM videos WHERE record_id='gggg-1'")
        check('G: NFD → NFC', g and g[0][0] == 'G 가 NFD' and json.loads(g[0][1]) == ['가'], g)
        t = dict(q('SELECT record_id, url_key FROM tips'))
        check('tips 2건 · url_key 에서 utm 제거', t.get('tttt-1') == 'https://github.com/x/y', t)
        tb = q("SELECT body_md FROM tips WHERE record_id='tttt-1'")
        check('tips 본문 블록 보존', tb == [('사용자 메모 블록',)], tb)
        db.close()

        print('▶ --summary-check=all')
        f = Fake()
        f.vpages = [dict(x) for x in VPAGES]
        trunc = vpage('iiii-1', 'IIIIIIIIIII', 'I 잘린속성', ['MCP'], '2026-08-07T00:00:00.000Z', summary='앞부분만')
        f.vpages.append(trunc)
        BLOCKS['iiii-1'] = [{'type': 'divider', 'divider': {}},
                            {'type': 'paragraph', 'paragraph': {'rich_text': rt('앞부분만 그리고 뒷부분')}}]
        code, out, rj = run(['--summary-check=all'], f)
        check('all: 불일치 1건(iiii-1)을 블록 본문으로 교체', code == 0 and rj['summary_check']['mismatch_ids'] == ['iiii-1']
              and rj['summary_check']['replaced_by_blocks'] == 1 and rj['summary_src'].get('blocks') == 2, out[-400:])
        del BLOCKS['iiii-1']

        print('▶ 재실행 보호')
        f = Fake()
        code, out, _ = run(['--apply'], f)
        check('이미 있으면 --replace 없이 거부 (노션 호출 0)', code == 1 and not f.calls, out[-300:])
        code, out, rj = run(['--apply', '--replace', '--summary-check=0'], Fake())
        bak = [x for x in os.listdir(os.path.dirname(ldb.DB_PATH)) if '.bak.' in x]
        check('--replace 는 기존 파일을 .bak.<시각> 으로 옮긴다', code == 0 and len(bak) == 1, (code, bak))

        print('▶ verify')
        code, out, rj = run(['--verify'], Fake())
        check('verify 통과 (Vault 영상 id 4 → videos 3 · dup 1 · 없음 0)',
              code == 0 and rj['vault_in_videos'] == 3 and rj['vault_in_dup'] == 1 and rj['vault_missing'] == 0, out[-600:])

        print('▶ 안전장치')
        before = open(ldb.DB_PATH, 'rb').read()
        f = Fake(); f.fail_plan = [(lambda meth, p: p.endswith(f'{TDB}/query'), 401)]
        code, out, _ = run(['--apply', '--replace'], f)
        check('401 → 종료 코드 2', code == 2, out[-300:])
        check('401 후 401 요청 다음 호출 0건', f.calls[-1][1].endswith(f'{TDB}/query'), f.calls[-3:])
        check('401 이면 기존 library.db 무변경', open(ldb.DB_PATH, 'rb').read() == before)
        f = Fake(); f.fail_plan = [(lambda meth, p: p.endswith(f'{VDB}/query'), 503)] * 2
        code, out, rj = run(['--summary-check=0'], f)
        check('503 두 번은 백오프 재시도 후 성공', code == 0 and rj['videos'] == 8, out[-300:])
        f = Fake(); f.fail_plan = [(lambda meth, p: p.endswith(f'{VDB}/query'), 503)] * 4
        try:
            code, out, _ = run(['--apply', '--replace'], f)
            ok = False
        except RuntimeError as ex:
            ok = '재시도 초과' in str(ex)
        check('503 네 번이면 실패로 끝나고', ok)
        check('  library.db 는 그대로', open(ldb.DB_PATH, 'rb').read() == before)
        f = Fake(); f.vpages = []
        try:
            run(['--apply', '--replace'], f); ok = False
        except RuntimeError as ex:
            ok = '0건' in str(ex)
        check('노션 0건이면 중단', ok and open(ldb.DB_PATH, 'rb').read() == before)
        so.VAULT = os.path.join(tmp, 'empty-vault'); os.makedirs(so.VAULT)
        f = Fake()
        code, out, _ = run(['--apply', '--replace'], f)
        check('Vault 에서 notion_id 0건이면 노션 호출 전에 중단', code == 1 and not f.calls, out[-300:])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    n = len(results); p = sum(results)
    print(f'\n{p}/{n} PASS')
    return 0 if p == n else 1


if __name__ == '__main__':
    sys.exit(main())
