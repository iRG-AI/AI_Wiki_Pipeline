#!/usr/bin/env python3
"""sync_obsidian.py 회귀 테스트 (v4.0 — 원본 = 장부 data/library.db). 네트워크 0회, 임시 Vault·임시 장부만 쓴다.
하위 단계(build_obsidian_wiki·wiki_ingest·build_search_index)는 실제로 띄우지 않는다 — subprocess.run 을 가짜로 바꾼다
(그 스크립트들은 실제 Vault 경로가 박혀 있어 테스트에서 돌리면 진짜 Vault 를 건드린다).

    /opt/homebrew/bin/python3 scripts/test_sync_obsidian.py

지키는 것:
  1) 장부가 없으면 Vault 를 하나도 건드리지 않고 exit 1
  2) --dry-run 은 Vault·장부를 하나도 쓰지 않고 할 일만 센다
  3) 새 노트는 노션 시절 노트와 같은 모양 (프론트매터 순서 · '▶ 영상 보기' · 구분선 · 요약)
  4) notion_id·video_url 은 프론트매터 안의 것만 센다 (schema.md 예시 오인 금지)
  5) 장부에 없는 영상 노트는 _trash 로 이동, 3중 안전장치 유지. 꿀팁 고아는 보고만 한다
  6) 두 번째 실행은 할 일 0 (멱등)
  7) 장부는 읽기 전용 — 실행 전후 바이트가 같다
  8) (v4.6-b) 재요약(장부 summary_src video)·등급 변경 → 노트 요약 절만 제자리 교체(관련 항목 절 보존)·grade·summary_src 맞춤,
     설명란 요약 행은 안 건드림, 경계를 못 찾으면 파일 그대로, 두 번째 실행은 0
"""
import hashlib, io, json, os, sqlite3, subprocess, sys, tempfile
from contextlib import redirect_stdout

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, 'lib'))
import urllib.request
net_calls = []
def _no_net(*a, **k):
    net_calls.append(a[0] if a else k)
    raise RuntimeError('네트워크 요청 금지 (테스트)')
urllib.request.urlopen = _no_net
import library_db as ldb
import sync_obsidian as so

sub_calls = []
class _Done:
    returncode = 0; stdout = ''; stderr = ''
def _fake_run(args, **kw):
    sub_calls.append(os.path.basename(args[1]) if len(args) > 1 else str(args))
    return _Done()
so.subprocess.run = _fake_run

results = []
def check(name, cond, detail=''):
    results.append(bool(cond))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f'  — {detail}' if detail and not cond else ''), flush=True)

def tree_hash(root):
    h = hashlib.sha256()
    for d, dirs, files in sorted(os.walk(root)):
        dirs.sort()
        for f in sorted(files):
            p = os.path.join(d, f)
            h.update(os.path.relpath(p, root).encode()); h.update(open(p, 'rb').read())
    return h.hexdigest()

def run(argv):
    sys.argv = ['sync_obsidian.py'] + argv
    sub_calls.clear()
    buf = io.StringIO(); code = 0
    with redirect_stdout(buf):
        try:
            so.main()
        except SystemExit as e:
            code = e.code or 0
    out = buf.getvalue()
    rj = next((json.loads(l[len('RESULT_JSON:'):]) for l in out.splitlines() if l.startswith('RESULT_JSON:')), None)
    return code, out, rj

def note(root, rel, nid, extra='', tags='["AI Claude"]', body='\n**▶ 영상 보기: **https://www.youtube.com/watch?v=X\n---\n## 요약\n기존 본문'):
    p = os.path.join(root, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'w', encoding='utf-8').write(f'---\ntitle: "t"\nchannel: "ch"\ntags: {tags}\n{extra}notion_id: {nid}\n---\n{body}\n')
    return p

def make_vault(root):
    note(root, 'AI Claude/ch_v1_20260901.md', 'rec-1', 'video_url: https://www.youtube.com/watch?v=VVVVVVVVVV1\n')
    note(root, 'AI Claude/ch_v2_20260902.md', 'rec-2', 'video_url: https://www.youtube.com/watch?v=VVVVVVVVVV2\n', tags='["AI Claude", "AI Gemini"]')
    note(root, 'AI Gemini/ch_dup_20260903.md', 'dup-1', 'video_url: https://www.youtube.com/watch?v=VVVVVVVVVV1\n')
    note(root, 'AI 꿀팁/20260901_기존 팁.md', 'tip-1', 'link_url: https://github.com/a/b\n', tags='[]')
    note(root, 'AI 꿀팁/20260902_지운 팁.md', 'tip-gone', 'link_url: https://x.com/y\n', tags='[]')
    note(root, '_trash/20260821_172922/AI Claude/old.md', 'trash-1', 'video_url: https://www.youtube.com/watch?v=OLD\n')
    open(os.path.join(root, 'schema.md'), 'w', encoding='utf-8').write(
        '# Schema\n\n```yaml\n---\ntitle: "영상 제목"\nvideo_url: https://youtube.com/watch?v=xxxxx\nnotion_id: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx\n---\n```\n')
    open(os.path.join(root, 'log.md'), 'w', encoding='utf-8').write(
        '# 📋 AI LLM Wiki 변경 이력\n\n> Wiki에 일어난 모든 변경사항을 시간순으로 기록합니다.\n> 파싱 팁: `grep "^## \\[" log.md | tail -10` 으로 최근 10개 확인\n\n')

V = ['record_id', 'video_id', 'title', 'channel', 'topics', 'upload_date', 'view_count', 'subscriber_count',
     'video_url', 'thumbnail_url', 'status', 'summary', 'summary_src', 'created_at', 'updated_at']
def vrow(rid, vid, title, topics, date, summary='## 영상 개요\n내용 **굵게**\n- 항목', channel='ch'):
    return (rid, vid, title, channel, json.dumps(topics, ensure_ascii=False), date, 1234, 5678,
            f'https://www.youtube.com/watch?v={vid}', f'https://i.ytimg.com/vi/{vid}/mqdefault.jpg', '완료', summary, 'app',
            '2026-10-01T00:00:00.000Z', '2026-10-01T00:00:00.000Z')

def make_db(path, videos):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    c = ldb.open_db(path); ldb.apply_schema(c)
    with c:
        c.executemany(f'INSERT INTO videos ({",".join(V)}) VALUES ({",".join("?" * len(V))})', videos)
        c.execute("INSERT INTO videos_dup (record_id, keeper_record_id, video_id, created_at, updated_at, has_vault_note) "
                  "VALUES ('dup-1','rec-1','VVVVVVVVVV1','2026-09-01T00:00:00.000Z','2026-09-01T00:00:00.000Z',1)")
        for rid, title, url, date in (('tip-1', '기존 팁', 'https://github.com/a/b', '2026-09-01'),
                                      ('tip-2', '새 "팁"', 'https://github.com/c/d', '2026-10-02')):
            c.execute("INSERT INTO tips (record_id,title,url,url_key,source,tags,category,status,importance,saved_date,memo,body_md,created_at,updated_at) "
                      "VALUES (?,?,?,?,'github.com',?,'개발툴','미확인','중',?,'',?,'2026-10-01T00:00:00.000Z','2026-10-01T00:00:00.000Z')",
                      (rid, title, url, url, json.dumps(['MCP']), date, '사용자 메모' if rid == 'tip-2' else ''))
    c.close()

VIDEOS = [
    vrow('rec-1', 'VVVVVVVVVV1', 'v1', ['AI Claude', 'AI 에이전트'], '2026-09-01'),       # tags 갱신 대상
    vrow('rec-2', 'VVVVVVVVVV2', 'v2', ['AI Claude', 'AI Gemini'], '2026-09-02'),          # 변경 없음
    vrow('rec-3', 'VVVVVVVVVV3', '새 영상 "따옴표"', ['AI 에이전트', 'AI Claude'], '2026-10-10', channel='새채널'),  # 신규
    vrow('rec-4', 'VVVVVVVVVV4', 'v2', ['AI Claude'], '2026-09-02'),                     # 같은 경로 → 건너뜀
    vrow('rec-5', 'VVVVVVVVVV2', 'v5', ['AI Gemini'], '2026-09-05'),                     # 같은 video_url → 건너뜀
]
VIDEOS[4] = tuple(list(VIDEOS[4][:1]) + [None] + list(VIDEOS[4][2:]))   # UNIQUE 회피: video_id 만 비운다(url 은 rec-2 와 같음)

EXPECT_REC3 = '''---
title: "새 영상 '따옴표'"
channel: "새채널"
tags: ["AI 에이전트", "AI Claude"]
upload_date: 2026-10-10
view_count: 1234
subscriber_count: 5678
video_url: https://www.youtube.com/watch?v=VVVVVVVVVV3
thumbnail: https://i.ytimg.com/vi/VVVVVVVVVV3/mqdefault.jpg
status: 완료
grade: null
summary_src: app
notion_id: rec-3
---


**▶ 영상 보기: **https://www.youtube.com/watch?v=VVVVVVVVVV3
---
## 영상 개요
내용 **굵게**
- 항목'''
import unicodedata
EXPECT_REC3 = unicodedata.normalize('NFC', EXPECT_REC3)

def main():
    tmp = tempfile.mkdtemp(prefix='sync-test-')
    vault = os.path.join(tmp, 'vault'); make_vault(vault)
    so.VAULT = vault; so.TRASH_DIR = os.path.join(vault, '_trash'); so.LOG_FILE = os.path.join(vault, 'log.md')
    so.MOC_DIR = os.path.join(vault, '_MOC')
    ldb.DB_PATH = os.path.join(tmp, 'data', 'library.db')

    print('▶ 장부 없음')
    h0 = tree_hash(vault)
    code, out, rj = run([])
    check('exit 1 · RESULT_JSON error', code == 1 and rj and 'library' in rj.get('error', ''), out[-300:])
    check('Vault 무변경 · 장부 파일 안 만듦', tree_hash(vault) == h0 and not os.path.exists(ldb.DB_PATH))

    make_db(ldb.DB_PATH, VIDEOS)
    db_bytes = open(ldb.DB_PATH, 'rb').read()

    print('▶ 프론트매터 규칙')
    ids, _, urls = so.get_existing_vault_info()
    check('schema.md 의 예시 notion_id·video_url 은 세지 않는다', 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx' not in ids
          and 'https://youtube.com/watch?v=xxxxx' not in urls, sorted(ids))
    check('Vault 영상 id = rec-1·rec-2·dup-1 (꿀팁·_trash 제외)', set(ids) == {'rec-1', 'rec-2', 'dup-1'}, sorted(ids))

    print('▶ dry-run')
    code, out, rj = run(['--dry-run'])
    check('dry-run exit 0', code == 0, out[-300:])
    check('Vault·장부 무변경', tree_hash(vault) == h0 and open(ldb.DB_PATH, 'rb').read() == db_bytes)
    check('하위 단계 실행 0', sub_calls == [], sub_calls)
    check('예정: 영상 1 · 꿀팁 1 · tags 1 · 고아 후보 1 · 같은 경로 1 · 같은 url 1 · 꿀팁 고아 1',
          rj and (rj['added'], rj['tips_added'], rj['tags_updated'], rj['orphans_candidates'], rj['skipped_same_path'],
                  rj['skipped_same_url'], rj['tips_orphans']) == (2, 1, 1, 1, 1, 1, 1), rj)

    print('▶ 실행')
    code, out, rj = run([])
    check('exit 0 · added 2(꿀팁 1) · tags 1 · 고아 이동 1', code == 0 and rj and (rj['added'], rj['tips_added'], rj['tags_updated'],
          rj['orphans_removed']) == (2, 1, 1, 1), (code, rj, out[-400:]))
    p3 = os.path.join(vault, 'AI 에이전트', '새채널_새 영상 _따옴표__20261010.md')
    got = open(p3, encoding='utf-8').read() if os.path.exists(p3) else ''
    check('새 노트: 첫 topic 폴더 · 파일명 규칙 · 노션 시절과 같은 모양(+ v4.6 grade·summary_src)', got == EXPECT_REC3, got[:600] or os.listdir(vault))
    mdx = so.video_note_md({'record_id': 'rx', 'topics': ['AI Claude'], 'title': 't', 'grade': 'exclude', 'summary_src': 'video'})
    check('(v4.6) 영상 요약·제외 등급 노트 프론트매터: grade: exclude · summary_src: video (notion_id 바로 위)',
          '\nstatus: \ngrade: exclude\nsummary_src: video\nnotion_id: rx\n---' in mdx, mdx[:400])
    t1 = open(os.path.join(vault, 'AI Claude/ch_v1_20260901.md'), encoding='utf-8').read()
    check('rec-1 tags 만 바뀌고 본문은 그대로', 'tags: ["AI Claude", "AI 에이전트"]' in t1 and '기존 본문' in t1, t1[:300])
    moved = [os.path.relpath(os.path.join(d, f), so.TRASH_DIR) for d, _, fs in os.walk(so.TRASH_DIR) for f in fs]
    check('dup-1 노트 → _trash/<시각>/AI Gemini/ (기존 _trash 보존)', any(m.endswith('AI Gemini/ch_dup_20260903.md') and not m.startswith('20260821')
          for m in moved) and 'AI Gemini/ch_dup_20260903.md' not in os.listdir(vault) and
          os.path.exists(os.path.join(so.TRASH_DIR, '20260821_172922/AI Claude/old.md')), moved)
    tip2 = [f for f in os.listdir(os.path.join(vault, 'AI 꿀팁')) if f.startswith('20261002')]
    tc = open(os.path.join(vault, 'AI 꿀팁', tip2[0]), encoding='utf-8').read() if tip2 else ''
    check('새 꿀팁 노트: link_url · video_url 없음 · tags 키 없음 · 본문 블록', 'link_url: https://github.com/c/d' in tc and 'video_url' not in tc
          and '\ntags:' not in tc and 'keywords: ["MCP"]' in tc and '## 본문\n\n사용자 메모' in tc and 'notion_id: tip-2' in tc, tc[:500])
    check('꿀팁 고아(tip-gone)는 그대로 둔다', os.path.exists(os.path.join(vault, 'AI 꿀팁', '20260902_지운 팁.md')))
    check('schema.md 그대로', 'xxxxxxxx-xxxx' in open(os.path.join(vault, 'schema.md'), encoding='utf-8').read())
    check('하위 단계: 재구성 → 인제스트 → 검색 인덱스', sub_calls == ['build_obsidian_wiki.py', 'wiki_ingest.py', 'build_search_index.py'], sub_calls)
    lg = open(so.LOG_FILE, encoding='utf-8').read()
    check('log.md 기록 (ingest·cleanup·tags-sync)', 'ingest | 신규 영상 1개 · 꿀팁 1개' in lg and 'cleanup | 고아 파일 1개' in lg and 'tags-sync' in lg, lg[:600])
    check('장부는 읽기 전용 (바이트 동일)', open(ldb.DB_PATH, 'rb').read() == db_bytes)

    print('▶ 두 번째 실행 (멱등)')
    code, out, rj = run([])
    check('할 일 0 · 하위 단계 0', code == 0 and rj and (rj['added'], rj['tags_updated'], rj['orphans_removed']) == (0, 0, 0)
          and sub_calls == [], (rj, sub_calls))

    print('▶ (v4.6-b) 재요약·등급 변경 노트 맞춤')
    REL = '\n\n---\n## 🔗 관련 항목\n\n**재생목록**: [[AI Claude MOC]]\n'
    p1 = os.path.join(vault, 'AI Claude/ch_v1_20260901.md')
    orig1 = open(p1, encoding='utf-8').read()
    open(p1, 'a', encoding='utf-8').write(REL)   # build_obsidian_wiki 가 붙인 절 흉내
    before1 = open(p1, encoding='utf-8').read()
    p2 = os.path.join(vault, 'AI Claude/ch_v2_20260902.md')
    orig2 = open(p2, encoding='utf-8').read()
    open(p2, 'w', encoding='utf-8').write('---\ntitle: "t"\nchannel: "ch"\ntags: ["AI Claude", "AI Gemini"]\n'
                                           'video_url: https://www.youtube.com/watch?v=VVVVVVVVVV2\nnotion_id: rec-2\n---\n본문에 영상 보기 줄 없음\n')
    before2 = open(p2, encoding='utf-8').read()
    db_bak = open(ldb.DB_PATH, 'rb').read()
    NEW = '## 영상 개요\n실제 영상 요약\n\n## 핵심 내용\n* **A**: 새 내용'
    c = sqlite3.connect(ldb.DB_PATH)
    c.execute("UPDATE videos SET summary=?, summary_src='video', grade='exclude' WHERE record_id='rec-1'", (NEW,))
    c.execute("UPDATE videos SET summary='새요약2', summary_src='video', grade='keep' WHERE record_id='rec-2'")
    c.commit(); c.close()
    h3 = tree_hash(vault)
    code, out, rj = run(['--dry-run'])
    check('dry-run: 맞춤 예정 1 · 경계 못 찾음 1 · Vault 무변경', code == 0 and rj['refreshed'] == 1 and rj['refresh_skipped'] == 1 and tree_hash(vault) == h3, rj)
    code, out, rj = run([])
    t1 = open(p1, encoding='utf-8').read()
    check('요약 절만 교체 · 관련 항목 절 보존 · 영상 보기 줄 그대로',
          t1.endswith('---\n' + NEW + REL) and '기존 본문' not in t1 and '**▶ 영상 보기: **https://www.youtube.com/watch?v=X\n---\n' + NEW in t1, t1[-400:])
    check('프론트매터: grade: exclude · summary_src: video 를 notion_id 앞에 넣음 · 다른 줄 그대로',
          '\ngrade: exclude\nsummary_src: video\nnotion_id: rec-1\n---' in t1 and t1.split('\ngrade:')[0] == before1.split('\nnotion_id:')[0], t1[:400])
    check('경계 못 찾은 노트는 그대로 · refresh_skipped 1', open(p2, encoding='utf-8').read() == before2 and rj['refresh_skipped'] == 1, rj)
    check('refreshed 1 → 검색 인덱스 갱신 · 재구성·인제스트는 안 함', rj['refreshed'] == 1 and sub_calls == ['build_search_index.py'], (rj, sub_calls))
    check('log.md 에 resummary 기록', 'resummary | 재요약·등급 변경 노트 1개' in open(so.LOG_FILE, encoding='utf-8').read())
    code, out, rj = run([])
    check('두 번째 실행: 맞춤 0 · 하위 단계 0', rj['refreshed'] == 0 and sub_calls == [], (rj, sub_calls))
    c = sqlite3.connect(ldb.DB_PATH); c.execute("UPDATE videos SET grade='keep' WHERE record_id='rec-1'"); c.commit(); c.close()
    code, out, rj = run([])
    t1b = open(p1, encoding='utf-8').read()
    check('장부 grade 만 고치면 노트 grade 줄만 바뀜(요약은 그대로)', rj['refreshed'] == 1 and t1b == t1.replace('grade: exclude', 'grade: keep'), t1b[:300])
    sub_calls.clear()
    open(ldb.DB_PATH, 'wb').write(db_bak)   # 이후 안전장치 시험은 원래 장부로
    open(p1, 'w', encoding='utf-8').write(orig1); open(p2, 'w', encoding='utf-8').write(orig2)

    print('▶ 안전장치')
    h1 = tree_hash(vault)
    os.replace(ldb.DB_PATH, ldb.DB_PATH + '.full')
    make_db(ldb.DB_PATH, VIDEOS[:1])            # videos 1건 < Vault 3건의 50%
    code, out, rj = run([])
    check('장부가 Vault 의 50% 미만이면 고아 이동 0 (partial)', code == 0 and rj['orphans_removed'] == 0 and rj['orphans_blocked'] == 'partial', rj)
    os.remove(ldb.DB_PATH)
    make_db(ldb.DB_PATH, VIDEOS[2:])           # rec-3·4·5 — Vault 의 rec-1·rec-2 가 고아 2/3 = 67%
    code, out, rj = run([])
    check('고아 비율 40% 초과면 이동 0 (ratio)', code == 0 and rj['orphans_removed'] == 0 and rj['orphans_blocked'] == 'ratio'
          and os.path.exists(os.path.join(vault, 'AI Claude/ch_v1_20260901.md')), rj)
    os.remove(ldb.DB_PATH)
    os.replace(ldb.DB_PATH + '.full', ldb.DB_PATH)
    c = sqlite3.connect(ldb.DB_PATH); c.execute('PRAGMA user_version = 0'); c.commit(); c.close()
    h2 = tree_hash(vault)
    code, out, rj = run([])
    check('user_version 이 다르면 Vault 를 건드리지 않고 exit 1', code == 1 and tree_hash(vault) == h2, out[-200:])

    check('네트워크 요청 0건', not net_calls, net_calls[:3])
    print(f'\n{sum(results)}/{len(results)} PASS')
    return 0 if all(results) else 1

if __name__ == '__main__':
    sys.exit(main())
