#!/usr/bin/env python3
"""build_obsidian_wiki.py (내용 같으면 안 쓰기) + build_search_index.py (프론트매터 한정) 회귀 테스트 — v4.0 3단계.
임시 Vault 만 쓴다. 네트워크 0회(임베딩 호출 없음 — collect_notes 만 부른다).

    /opt/homebrew/bin/python3 scripts/test_build_wiki_index.py

지키는 것:
  1) 두 번째 재구성은 노트를 하나도 다시 쓰지 않는다 (mtime 그대로) — 2026-10-11 Vault 전체 mtime 3,193개 변경의 재발 방지
  2) 바뀐 노트 하나만 다시 쓴다
  3) 검색 인덱스는 맨 앞 프론트매터의 notion_id 만 노트로 센다 (본문 예시의 'notion_id: …' 는 노트가 아니다)
  4) (v4.6) 프론트매터 grade: exclude 노트는 검색 인덱스에서 빠진다 (grade: null·keep 은 그대로)
  5) (v4.7) 검색 화면 필터용 메타(kind·subscriber_count·summary_src·link_url·category·importance·keywords)를 담고, 임베딩 hash 는 그대로
"""
import os, shutil, sys, tempfile, time
from contextlib import redirect_stdout
import io

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
import urllib.request
calls = []
def _no_net(*a, **k):
    calls.append(a[0] if a else k)
    raise RuntimeError('네트워크 요청 금지 (테스트)')
urllib.request.urlopen = _no_net

import build_obsidian_wiki as bow   # noqa: E402
import build_search_index as bsi    # noqa: E402
bsi.urlopen = _no_net

results = []
def check(name, cond, detail=''):
    results.append(bool(cond))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f'  — {detail}' if detail and not cond else ''), flush=True)


def note(title, nid, topic, body_extra=''):
    return (f'---\ntitle: "{title}"\nchannel: "채널가"\ntags: ["{topic}"]\nupload_date: 2026-09-01\nview_count: 10\n'
            f'subscriber_count: 20\nvideo_url: https://www.youtube.com/watch?v={nid[-11:]}\nthumbnail: null\nstatus: 완료\n'
            f'notion_id: {nid}\n---\n\n\n**▶ 영상 보기: **https://www.youtube.com/watch?v={nid[-11:]}\n---\n'
            f'## 영상 개요\nClaude Code 와 Gemini 를 비교한다. {body_extra}\n\n## 핵심 내용\n- 하나\n')


tmp = tempfile.mkdtemp(prefix='wiki-build-test-')
V = os.path.join(tmp, 'vault')
try:
    os.makedirs(os.path.join(V, 'AI Claude'))
    os.makedirs(os.path.join(V, 'AI 꿀팁'))
    files = {
        'AI Claude/채널가_영상 하나_20260901.md': note('영상 하나', 'aaaaaaaa-0000-0000-0000-00000000001a', 'AI Claude'),
        'AI Claude/채널가_영상 둘_20260902.md': note('영상 둘', 'aaaaaaaa-0000-0000-0000-00000000002b', 'AI Claude'),
        # 프론트매터 없이 본문에 예시만 있는 문서 — 노트가 아니다
        'AI Claude/메모.md': '# 메모\n\n```yaml\nnotion_id: bbbbbbbb-0000-0000-0000-000000000099\ntitle: "가짜"\n```\n',
        # 프론트매터는 있으나 notion_id 는 본문 예시에만 — 노트가 아니다
        'AI Claude/설명.md': '---\ntitle: "설명"\n---\n\n```\nnotion_id: cccccccc-0000-0000-0000-000000000098\n```\n',
        'AI 꿀팁/2026-09-02_팁.md': '---\ntitle: "팁"\nlink_url: https://github.com/a/b\ncategory: 개발툴\nkeywords: ["Claude"]\nnotion_id: tip-0001\n---\n\n메모\n',
    }
    for rel, text in files.items():
        with open(os.path.join(V, rel), 'w', encoding='utf-8') as fh:
            fh.write(text)

    bow.VAULT = V
    bow.MOC_DIR = os.path.join(V, '_MOC')
    bsi.VAULT = V

    def rebuild():
        bow.WRITE_STATS.update(written=0, same=0)
        with redirect_stdout(io.StringIO()):
            fs = bow.get_all_files()
            bow.build_moc_files(fs)
            bow.add_keyword_links(fs)
            bow.build_keyword_hubs(fs)
            fs = bow.get_all_files()
            bow.build_keyword_index(fs)
            bow.lint_wiki(fs)
            bow.build_schema(fs)
        return dict(bow.WRITE_STATS)

    note_paths = [os.path.join(V, r) for r in files]

    def mtimes():
        return {p: os.stat(p).st_mtime_ns for p in note_paths}

    print('▶ 1. 첫 재구성 — 관련 항목이 붙는다')
    s1 = rebuild()
    body = open(note_paths[0], encoding='utf-8').read()
    check('첫 재구성은 노트에 🔗 관련 항목을 쓴다', '## 🔗 관련 항목' in body and '[[AI Claude MOC]]' in body and s1['written'] > 0, s1)

    print('▶ 2. 두 번째 재구성 — 노트를 다시 쓰지 않는다')
    old = time.time() - 3600
    for p in note_paths:
        os.utime(p, (old, old))
    m0 = mtimes()
    s2 = rebuild()
    m1 = mtimes()
    check('노트 mtime 전부 그대로', m0 == m1, [os.path.relpath(p, V) for p in note_paths if m0[p] != m1[p]])
    check('내용 같아 건너뜀 > 0', s2['same'] >= len(note_paths), s2)
    check('다시 쓴 것은 시각이 박힌 lint.md·schema.md 정도 (≤ 2)', s2['written'] <= 2, s2)
    check('두 번째 결과 파일 내용 = 첫 번째', open(note_paths[0], encoding='utf-8').read() == body)
    memo = open(os.path.join(V, 'AI Claude/메모.md'), encoding='utf-8').read()
    check('프론트매터 없는 파일도 관련 항목이 한 벌만 (쌓이지 않음)', memo.count('## 🔗 관련 항목') == 1, memo.count('## 🔗 관련 항목'))

    print('▶ 3. 바뀐 노트 하나만')
    p = note_paths[1]
    txt = open(p, encoding='utf-8').read().replace('## 핵심 내용\n- 하나', '## 핵심 내용\n- 하나\n- Cursor 도 다룬다')
    with open(p, 'w', encoding='utf-8') as fh:
        fh.write(txt)
    os.utime(p, (old, old))
    m0 = mtimes()
    rebuild()
    m1 = mtimes()
    changed = [os.path.relpath(x, V) for x in note_paths if m0[x] != m1[x]]
    check('바뀐 노트 1개만 다시 씀', changed == ['AI Claude/채널가_영상 둘_20260902.md'], changed)

    print('▶ 4. 검색 인덱스 — 프론트매터 한정')
    notes = bsi.collect_notes()
    ids = sorted(n['id'] for n in notes)
    check('노트 = 영상 2 + 꿀팁 1 (본문 예시 2개는 제외)', ids == ['aaaaaaaa-0000-0000-0000-00000000001a', 'aaaaaaaa-0000-0000-0000-00000000002b', 'tip-0001'], ids)
    n1 = next(n for n in notes if n['id'].endswith('1a'))
    check('제목·태그·조회수는 프론트매터 값', n1['title'] == '영상 하나' and n1['tags'] == ['AI Claude'] and n1['view_count'] == 10, n1)

    print('▶ 5. (v4.6) grade: exclude 는 검색에서 제외')
    for rel, nid, g in (('AI Claude/채널가_판매_20260903.md', 'aaaaaaaa-0000-0000-0000-00000000003c', 'exclude'),
                        ('AI Claude/채널가_좋음_20260904.md', 'aaaaaaaa-0000-0000-0000-00000000004d', 'keep'),
                        ('AI Claude/채널가_미판정_20260905.md', 'aaaaaaaa-0000-0000-0000-00000000005e', 'null')):
        with open(os.path.join(V, rel), 'w', encoding='utf-8') as fh:
            fh.write(note('x', nid, 'AI Claude').replace('status: 완료\n', f'status: 완료\ngrade: {g}\n'))
    ids = sorted(n['id'] for n in bsi.collect_notes())
    check('exclude 1건만 빠지고 keep·null 은 포함', '…003c' not in ids and not any(i.endswith('3c') for i in ids)
          and any(i.endswith('4d') for i in ids) and any(i.endswith('5e') for i in ids) and len(ids) == 5, ids)
    print('▶ 6. (v4.7) 화면 필터용 메타')
    with open(os.path.join(V, 'AI 꿀팁/20260906_꿀팁 둘.md'), 'w', encoding='utf-8') as fh:
        fh.write('---\ntitle: "꿀팁 둘"\nchannel: "https://github.com"\nsource_type: tip\ncategory: "개발툴"\n'
                 'keywords: ["Claude", "MCP"]\nimportance: 상\nupload_date: 2026-09-06\nlink_url: https://github.com/x/y\n'
                 'notion_id: tip-0002\n---\n\n메모\n')
    with open(os.path.join(V, 'AI Claude/채널가_영상요약_20260907.md'), 'w', encoding='utf-8') as fh:
        fh.write(note('영상요약', 'aaaaaaaa-0000-0000-0000-00000000006f', 'AI Claude').replace('status: 완료\n', 'status: 완료\nsummary_src: video\ngrade: keep\n'))
    by = {n['id']: n for n in bsi.collect_notes()}
    t2, v6, v1 = by.get('tip-0002', {}), by.get('aaaaaaaa-0000-0000-0000-00000000006f', {}), by.get('aaaaaaaa-0000-0000-0000-00000000001a', {})
    check('꿀팁: kind tip · link_url · category · importance · keywords', t2.get('kind') == 'tip' and t2.get('link_url') == 'https://github.com/x/y'
          and t2.get('category') == '개발툴' and t2.get('importance') == '상' and t2.get('keywords') == ['Claude', 'MCP'], t2)
    check('영상: kind video · subscriber_count · summary_src', v6.get('kind') == 'video' and v6.get('subscriber_count') == 20
          and v6.get('summary_src') == 'video' and v6.get('link_url') == '', v6)
    check('summary_src 없는 옛 노트는 빈 값 · keywords 빈 배열', v1.get('summary_src') == '' and v1.get('keywords') == [], v1)
    check('메타를 더해도 임베딩 hash 는 그대로 (재임베딩 없음)', v1.get('hash') == n1['hash'], [v1.get('hash'), n1['hash']])
    check('네트워크 요청 0건', not calls, calls[:2])
finally:
    shutil.rmtree(tmp, ignore_errors=True)

ok = sum(results)
print(f'\n{ok}/{len(results)} PASS')
sys.exit(0 if ok == len(results) else 1)
