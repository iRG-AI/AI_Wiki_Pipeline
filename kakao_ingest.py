#!/usr/bin/env python3
"""
카카오톡 '나와의 채팅' CSV → 장부 tips 인제스트 (v2.8 → v4.0: 노션「AI 꿀팁」대신 data/library.db 의 tips 테이블)

    /usr/bin/python3 kakao_ingest.py                 # dry-run (기본). 생성될 행을 표로만 출력
    /usr/bin/python3 kakao_ingest.py --apply --limit=3
    /usr/bin/python3 kakao_ingest.py --apply
    옵션: --csv=<경로>  (기본: KAKAO_EXPORT_DIR 의 최신 KakaoTalk_Chat_안진훈_*.csv — NFC 비교)
          --since=YYYY-MM-DD  (기본: 2026-03-01 — DB 시작 시점. 그 이전 카톡 링크는 AI 자료가 아님)
          --if-new   스케줄러용. 최신 CSV 의 mtime 이 .kakao_state.json 에 기록된 값과 같으면 장부 조회 없이 즉시 종료
          --force    --if-new 무시

스케줄러 연동 (v3.0): scheduler.js 가 Obsidian 동기화 직전에 `--apply --if-new` 로 호출한다.
마지막 줄에 `RESULT_JSON:{...}` 를 찍어 scheduler.js 가 파싱한다 (sync_obsidian.py 와 같은 규약).
`.kakao_state.json` 은 "이 CSV 는 이미 봤다"는 스킵 최적화일 뿐, 중복 방지 장치가 아니다.

멱등성: 중복 판정은 로컬 상태 파일이 아니라 **장부 tips 전량 + URL 정규화 키(url_key)**로 한다.
같은 CSV를 몇 번 돌려도 신규 0건이어야 정상. (2026-09-06 중복 15건 사고 재발 방지 조건)

v4.0: 네트워크 요청 없음. 장부가 없으면 만들지 않고 실패한다(exit 1). 신규 행은 한 트랜잭션으로 넣는다(전부 들어가거나 하나도 안 들어가거나).
지침서 docs/tasks/2026-09-06-kakao-tips-ingest.md, docs/tasks/2026-10-11-v4-sqlite-switch-a.md
"""
import glob, json, os, sys, time, uuid
from datetime import datetime, timezone
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR, 'lib'))

from kakao_parse import parse_links, guess_meta, url_key, nfc
import tips_notion as tn          # .env 읽기(tn.ENV)만 쓴다. 노션 호출 없음 (노션 코드 정리는 지시서 3)
import library_db as ldb

DEFAULT_SINCE = '2026-03-01'
CSV_PREFIX = 'KakaoTalk_Chat_안진훈'          # '나와의 채팅' 내보내기 파일만. 다른 대화방 CSV 는 무시
STATE_FILE = os.path.join(SCRIPT_DIR, '.kakao_state.json')   # gitignore 대상


def load_state():
    try:
        return json.load(open(STATE_FILE, encoding='utf-8'))
    except Exception:
        return {}


def save_state(s):
    json.dump(s, open(STATE_FILE, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)


def emit_result(**kw):
    print('RESULT_JSON:' + json.dumps(kw, ensure_ascii=False), flush=True)


def arg(name, default=None):
    for a in sys.argv[1:]:
        if a.startswith(f'--{name}='):
            return a.split('=', 1)[1]
    return default


def log(m): print(m, flush=True)


def latest_csv():
    """KAKAO_EXPORT_DIR 에서 '나와의 채팅' CSV 중 mtime 최신. macOS 파일명은 NFD 라 NFC 로 맞춰 비교한다."""
    d = os.path.expanduser(tn.ENV.get('KAKAO_EXPORT_DIR', '~/Downloads'))
    files = [f for f in glob.glob(os.path.join(d, 'KakaoTalk_Chat_*.csv'))
             if nfc(os.path.basename(f)).startswith(CSV_PREFIX)]
    files.sort(key=os.path.getmtime)
    return files[-1] if files else None


def main():
    apply = '--apply' in sys.argv
    if_new = '--if-new' in sys.argv and '--force' not in sys.argv
    limit = int(arg('limit', 0) or 0)
    since = arg('since', DEFAULT_SINCE)
    csv_path = arg('csv') or latest_csv()
    if not csv_path or not os.path.exists(csv_path):
        log('ℹ️  카톡 CSV 없음 (--csv=<경로> 또는 KAKAO_EXPORT_DIR 확인) — 건너뜀')
        emit_result(skipped='no_csv', csv=None, created=0, candidates=0, db_total=None)
        sys.exit(0 if if_new else 1)

    csv_name = nfc(os.path.basename(csv_path))
    csv_mtime = int(os.path.getmtime(csv_path))
    state = load_state()
    if if_new and state.get('csv') == csv_name and state.get('mtime') == csv_mtime:
        log(f'ℹ️  {csv_name} 은 이미 처리됨 ({state.get("processed_at", "")}) — 건너뜀')
        emit_result(skipped='already_processed', csv=csv_name, created=0, candidates=0, db_total=state.get('db_total'))
        return

    log(f"{'🚀 APPLY' if apply else '👀 DRY-RUN'} · CSV: {csv_name} · since {since}" + (f' · limit {limit}' if limit else ''))

    links = parse_links(csv_path, since)
    log(f'📎 CSV 링크 {len(links)}건 (since {since}, CSV 내부 중복 제거 후)')

    try:
        conn = ldb.open_existing(readonly=not apply)
        rows = [dict(r) for r in conn.execute('SELECT url, url_key FROM tips')]
    except Exception as e:
        log(f'❌ 장부 열기 실패: {e}'); emit_result(error=str(e)[:200], csv=csv_name, created=0, candidates=0, db_total=None); sys.exit(1)
    # url_key 열이 비어 있는 행(이론상 없음)은 url 로 다시 계산해 대조에서 빠지지 않게 한다
    existing = {r['url_key'] or url_key(r['url']) for r in rows if r['url'] or r['url_key']}
    log(f'🗂  장부 tips {len(rows)}건 로드 (URL 키 {len(existing)}개)')

    new = [l for l in links if l['key'] not in existing]
    log(f'✨ 신규 후보 {len(new)}건\n')
    if limit:
        new = new[:limit]

    def mark_done(created):
        # apply 로 끝까지 돌았을 때만 "이 CSV 는 봤다"고 기록 (dry-run 은 기록하지 않는다)
        if apply and not limit:
            save_state({'csv': csv_name, 'mtime': csv_mtime, 'processed_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                        'created': created, 'db_total': len(rows) + created})

    if not new:
        conn.close()
        log('✅ 생성할 행 없음 — 멱등성 OK')
        mark_done(0)
        emit_result(csv=csv_name, created=0, candidates=0, db_total=len(rows))
        return

    log(f"{'날짜':10} | {'카테고리':6} | {'제목':42} | URL")
    log('-' * 110)
    plan = []
    for l in new:
        g = guess_meta(l['url'], l['message'])
        row = {
            'title': g['title'], 'url': l['url'], 'source': g['source'], 'tags': g['tags'],
            'category': g['category'], 'status': '미확인', 'importance': '중',
            'saved_date': l['date'][:10], 'memo': g['memo'],
        }
        plan.append(row)
        log(f"{row['saved_date']:10} | {row['category']:6} | {row['title'][:42]:42} | {row['url'][:70]}")

    if not apply:
        conn.close()
        log(f'\n👀 dry-run 종료 — 위 {len(plan)}건은 생성되지 않았습니다. 실제 생성은 --apply')
        emit_result(dry_run=True, csv=csv_name, created=0, candidates=len(plan), db_total=len(rows))
        return

    # 노션 tips_notion.build_properties 와 같은 기본값: 제목이 비면 URL, 카테고리 '기타', 상태 '미확인', 중요도 '중'
    dt = datetime.now(timezone.utc)
    now = dt.strftime('%Y-%m-%dT%H:%M:%S.') + f'{dt.microsecond // 1000:03d}Z'   # scheduler 와 같은 ISO 형식
    vals = []
    for row in plan:
        vals.append((str(uuid.uuid4()), nfc((row['title'] or row['url'])[:200]), row['url'], url_key(row['url']),
                     row.get('source') or '', json.dumps([nfc(t) for t in row.get('tags') or []], ensure_ascii=False),
                     nfc(row.get('category') or '기타'), nfc(row.get('status') or '미확인'), nfc(row.get('importance') or '중'),
                     (row.get('saved_date') or '')[:10] or None, nfc(row.get('memo') or ''), '', now, now))
    try:
        with conn:   # 한 트랜잭션 — 실패하면 아무 행도 남지 않는다
            conn.executemany('INSERT INTO tips (record_id, title, url, url_key, source, tags, category, status, importance, '
                             'saved_date, memo, body_md, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)', vals)
        db_total = conn.execute('SELECT COUNT(*) FROM tips').fetchone()[0]
    except Exception as e:
        log(f'❌ 장부 쓰기 실패 — 아무 행도 넣지 않았습니다: {e}')
        emit_result(error=str(e)[:200], csv=csv_name, created=0, candidates=len(plan), db_total=len(rows))
        sys.exit(1)
    finally:
        conn.close()
    created = len(vals)
    titles = [v[1] for v in vals]
    for i, t in enumerate(titles, 1):
        log(f'  [{i}/{created}] ✅ {t[:40]}')
    log(f'\n🎉 생성 {created}건 · 장부 tips 총 {db_total}건')
    mark_done(created)
    emit_result(csv=csv_name, created=created, failed=0, candidates=len(plan), db_total=db_total, titles=titles[:10])


if __name__ == '__main__':
    main()
