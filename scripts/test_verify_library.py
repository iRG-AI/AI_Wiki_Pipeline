#!/usr/bin/env python3
"""
scripts/verify_library.py 회귀 테스트 — 네트워크 0회, 실제 Vault·data/ 무변경 (v4.3)

  /opt/homebrew/bin/python3 scripts/test_verify_library.py

임시 Vault·임시 장부로 돌린다. 끝에 'N/N PASS' 를 찍고 실패가 있으면 종료 코드 1.
"""
import io, json, os, shutil, sys, tempfile
import urllib.request

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, 'scripts'))
sys.path.insert(0, os.path.join(REPO_ROOT, 'lib'))
sys.path.insert(0, REPO_ROOT)

NET_CALLS = []
def _no_net(*a, **k):
    NET_CALLS.append(a)
    raise RuntimeError('네트워크 호출 금지')
urllib.request.urlopen = _no_net

import verify_library as m      # noqa: E402
import sync_obsidian as so      # noqa: E402
import library_db as ldb        # noqa: E402

TS = '2026-10-12T00:00:00.000Z'


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


def make_db(path):
    conn = ldb.open_db(path)
    ldb.apply_schema(conn)
    for rid, vid in (('aaaa-1', 'AAAAAAAAAAA'), ('cccc-1', 'CCCCCCCCCCC'), ('hhhh-1', 'HHHHHHHHHHH'), ('bbbb-0', None)):
        conn.execute('INSERT INTO videos (record_id, video_id, created_at, updated_at) VALUES (?,?,?,?)', (rid, vid, TS, TS))
    conn.execute('INSERT INTO videos_dup (record_id, keeper_record_id, video_id, created_at, updated_at) VALUES (?,?,?,?,?)',
                 ('aaaa-3', 'aaaa-1', 'AAAAAAAAAAA', TS, TS))
    conn.execute('INSERT INTO tips (record_id, created_at, updated_at) VALUES (?,?,?)', ('tttt-1', TS, TS))
    conn.execute("INSERT INTO meta (key, value) VALUES ('loaded_at', ?), ('switched_at', ?)", (TS, TS))
    conn.commit()
    conn.close()


def sql(path, stmt):
    conn = ldb.open_db(path)
    conn.execute(stmt)
    conn.commit()
    conn.close()


results = []


def check(name, cond, detail=''):
    results.append(bool(cond))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f'  — {detail}' if detail and not cond else ''), flush=True)


def run(argv):
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        code = m.main(argv)
    finally:
        sys.stdout = old
    out = buf.getvalue()
    rj = next((json.loads(l[len('RESULT_JSON '):]) for l in out.splitlines() if l.startswith('RESULT_JSON ')), None)
    return code, out, rj


def snapshot(root):
    """파일 경로 → (크기, mtime_ns, 내용) — 읽기 전용 확인용"""
    snap = {}
    for dp, _, fns in os.walk(root):
        for f in fns:
            p = os.path.join(dp, f)
            st = os.stat(p)
            snap[p] = (st.st_size, st.st_mtime_ns, open(p, 'rb').read())
    return snap


def main():
    tmp = tempfile.mkdtemp(prefix='verify-lib-test-')
    vault = os.path.join(tmp, 'vault')
    make_vault(vault)
    so.VAULT = vault
    db = os.path.join(tmp, 'data', 'library.db')
    ldb.DB_PATH = db
    try:
        print('▶ 장부 없음')
        code, out, rj = run([])
        check('장부 파일이 없으면 종료 1 · 만들지 않는다', code == 1 and not os.path.exists(db) and '없음' in out, out[-300:])

        make_db(db)
        print('▶ 정상')
        before_db = open(db, 'rb').read()
        before_vault = snapshot(vault)
        code, out, rj = run([])
        check('통과 종료 0 · ok true', code == 0 and rj and rj['ok'] is True, out[-600:])
        check('Vault 영상 id 4 → videos 3 · dup 1 · 없음 0',
              rj and rj['vault_video_ids'] == 4 and rj['vault_in_videos'] == 3 and rj['vault_in_dup'] == 1 and rj['vault_missing'] == 0, rj)
        check('꿀팁 id 1 (README 본문 notion_id 는 세지 않음) · 없음 0', rj and rj['vault_tip_ids'] == 1 and rj['tips_missing'] == 0, rj)
        check('schema.md 예시 id·_trash 는 Vault id 가 아니다',
              'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx' not in out and 'zzzz-trash' not in out and rj and rj['vault_video_ids'] == 4, out[-600:])
        check('RESULT_JSON 키 유지 (videos 4 · tips 1 · no_video_id 1 · switched_at)',
              rj and rj['videos'] == 4 and rj['tips'] == 1 and rj['no_video_id'] == 1 and rj['switched_at'] == TS and rj['mode'] == 'verify', rj)
        check('장부 바이트 무변경', open(db, 'rb').read() == before_db)
        check('Vault 파일 무변경 (내용·mtime)', snapshot(vault) == before_vault)
        check('노션 모듈을 import 하지 않음', 'tips_notion' not in sys.modules and 'notion_to_sqlite' not in sys.modules)
        check('네트워크 호출 0', not NET_CALLS, NET_CALLS[:2])

        print('▶ 실패 판정')
        sql(db, "DELETE FROM videos WHERE record_id = 'cccc-1'")
        code, out, rj = run([])
        check('Vault 영상 노트가 장부에 없으면 종료 1 · vault_missing 1', code == 1 and rj and rj['vault_missing'] == 1 and '[영상 없음] cccc-1' in out, out[-400:])
        sql(db, "INSERT INTO videos (record_id, video_id, created_at, updated_at) VALUES ('cccc-1', 'CCCCCCCCCCC', '%s', '%s')" % (TS, TS))

        sql(db, "DELETE FROM tips")
        code, out, rj = run([])
        check('꿀팁 노트가 장부에 없으면 종료 1 · tips_missing 1', code == 1 and rj and rj['tips_missing'] == 1 and '[꿀팁 없음] tttt-1' in out, out[-400:])
        sql(db, "INSERT INTO tips (record_id, created_at, updated_at) VALUES ('tttt-1', '%s', '%s')" % (TS, TS))

        sql(db, 'PRAGMA user_version = %d' % (ldb.SCHEMA_VERSION + 1))
        code, out, rj = run([])
        check('user_version 이 스키마와 다르면 종료 1', code == 1 and rj and rj['ok'] is False, out[-300:])
        sql(db, 'PRAGMA user_version = %d' % ldb.SCHEMA_VERSION)

        code, out, rj = run([])
        check('되돌리면 다시 통과', code == 0, out[-300:])

        so.VAULT = os.path.join(tmp, 'empty-vault'); os.makedirs(so.VAULT)
        sql(db, 'DELETE FROM videos')
        code, out, rj = run([])
        check('videos 0건이면 종료 1 (Vault 가 비어도)', code == 1 and rj and rj['videos'] == 0, out[-300:])

        print('▶ 인자')
        code, out, rj = run(['--apply'])
        check('인자를 주면 종료 2 · 아무것도 하지 않음', code == 2 and rj is None, out[-200:])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    n = len(results); p = sum(results)
    print(f'\n{p}/{n} PASS')
    return 0 if p == n else 1


if __name__ == '__main__':
    sys.exit(main())
