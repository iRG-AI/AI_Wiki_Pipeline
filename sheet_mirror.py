#!/usr/bin/env python3
"""
v4.0 3단계 — 장부(data/library.db) → 구글 시트 미러 (보기 전용, 단방향)

    /opt/homebrew/bin/python3 sheet_mirror.py             # 변경분만 보낸다 (스케줄러가 매 실행 끝에 부른다)
    /opt/homebrew/bin/python3 sheet_mirror.py --dry-run   # 보낼 건수만 센다. 네트워크·장부 쓰기 0 (URL 설정 전에도 된다)
    /opt/homebrew/bin/python3 sheet_mirror.py --full      # 두 탭을 비우고 전부 다시 보낸다 (열이 바뀌었거나 시트가 어긋났을 때)
    /opt/homebrew/bin/python3 sheet_mirror.py --check     # 시트 행 수 ↔ 장부 행 수 대조 (읽기만)

받는 쪽: gas/sheet_mirror.gs (구글 시트에 붙인 Apps Script 웹앱). 설치 순서는 그 파일 머리 주석.
.env: SHEET_MIRROR_URL (웹앱 URL, https://script.google.com/macros/s/…/exec) · SHEET_MIRROR_TOKEN (gas 스크립트 속성 MIRROR_TOKEN 과 같은 값)
      URL 이 없으면 아무것도 하지 않고 skipped 로 끝난다 (설치 전에도 스케줄러가 안전하게 부를 수 있게).

변경분 판정 — 별도 outbox 테이블 대신 updated_at 워터마크 (스키마 무변경):
  · 장부 meta 의 sheet_wm_videos·sheet_wm_tips = 마지막으로 시트에 다 보낸 행들의 최대 updated_at.
  · 다음 실행은 updated_at > 워터마크 인 행만 보낸다. 장부 쓰기(insertVideo·addTopic·updateStats·kakao_ingest)는 모두 updated_at 을 새로 찍는다.
  · 워터마크는 그 탭의 묶음을 **전부** 보낸 뒤에만 올린다. 중간에 실패하면 다음 실행이 같은 행을 다시 보낸다(덮어쓰기라 무해).
  · 시트 주소가 바뀌면(meta sheet_target ≠ URL 해시) 자동으로 --full.
  · 장부에서 행을 지우는 일은 앱에 없다. 손으로 지웠다면 --full 로 맞춘다.

안전 (CLAUDE.md 1순위):
  · 401/403·토큰 불일치·웹앱 미설정·HTML 응답(로그인 화면 = 액세스 권한 설정 오류) → 재시도 없이 즉시 중단, exit 2.
  · 429·5xx·네트워크 오류·busy → 지수 백오프 2·4·8초, 최대 4회 시도 후 중단, exit 1.
  · 토큰은 본문으로만 보낸다(URL·로그에 남기지 않는다). URL 은 script.google.com 만 허용.
  · 장부는 meta 의 sheet_* 키 말고는 쓰지 않는다.

마지막 줄은 RESULT_JSON:{...} (scheduler.js 가 파싱). exit 0 = 성공 또는 skipped.
"""
import hashlib, json, os, ssl, sys, time
from datetime import datetime, timedelta, timezone
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR, 'lib'))
import library_db as ldb          # noqa: E402
from env_util import load_env     # noqa: E402

ALLOWED_URL_PREFIXES = ('https://script.google.com/macros/s/',)
CHUNK = 200                 # 요청 1회 행 수 (gas 상한 500)
MAX_ATTEMPTS = 4            # 일시 오류 재시도 포함 총 시도 (대기 2·4·8초)
TIMEOUT = 120
CELL_MAX = 45000            # 구글 시트 셀 한도 50,000자 — 여유를 두고 자른다 (현재 요약 최대 약 3,300자)
KST = timezone(timedelta(hours=9))

VIDEO_HEADERS = ['record_id', '업로드일', '채널', '제목', '주제', '조회수', '구독자', 'URL', '요약', '저장', '수정']
TIP_HEADERS = ['record_id', '저장일', '제목', 'URL', '출처', '카테고리', '태그', '중요도', '상태', '메모', '본문', '저장', '수정']
TABS = (  # (장부 테이블, 시트 탭, 머리글, 워터마크 키)
    ('videos', '영상', VIDEO_HEADERS, 'sheet_wm_videos'),
    ('tips', '꿀팁', TIP_HEADERS, 'sheet_wm_tips'),
)


class AuthError(RuntimeError):
    """재시도 금지 — 즉시 중단 (exit 2)"""


class TransientError(RuntimeError):
    """재시도 초과 (exit 1)"""


def log(m=''):
    print(m, flush=True)


def emit(**kw):
    print('RESULT_JSON:' + json.dumps(kw, ensure_ascii=False), flush=True)


def _list(s):
    try:
        v = json.loads(s or '[]')
        return ', '.join(str(x) for x in v if x) if isinstance(v, list) else ''
    except Exception:
        return ''


def _kst(iso):
    """'2026-10-11T08:15:00.000Z' → '2026-10-11 17:15' (KST). 못 읽으면 원문"""
    if not iso:
        return ''
    try:
        dt = datetime.fromisoformat(iso.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(KST).strftime('%Y-%m-%d %H:%M')
    except Exception:
        return iso


def _cell(s):
    s = s or ''
    return s if len(s) <= CELL_MAX else s[:CELL_MAX] + ' …(잘림)'


def video_row(r):
    return [r['record_id'], r['upload_date'] or '', r['channel'], r['title'], _list(r['topics']),
            r['view_count'] if r['view_count'] is not None else '',
            r['subscriber_count'] if r['subscriber_count'] is not None else '',
            r['video_url'] or '', _cell(r['summary']), _kst(r['created_at']), _kst(r['updated_at'])]


def tip_row(r):
    return [r['record_id'], r['saved_date'] or '', r['title'], r['url'], r['source'], r['category'], _list(r['tags']),
            r['importance'], r['status'], _cell(r['memo']), _cell(r['body_md']), _kst(r['created_at']), _kst(r['updated_at'])]


ROW_FN = {'videos': video_row, 'tips': tip_row}


def url_hash(url):
    return hashlib.sha256(url.encode('utf-8')).hexdigest()[:16]


# ── HTTP ──
def post(url, payload):
    """gas 웹앱에 POST. Apps Script 는 302 로 결과 주소를 돌려주고 urllib 이 GET 으로 따라간다(본문은 다시 보내지 않는다)."""
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    ctx = ssl.create_default_context()
    for attempt in range(1, MAX_ATTEMPTS + 1):
        wait = 2 ** attempt
        try:
            req = Request(url, data=data, method='POST', headers={'Content-Type': 'application/json; charset=utf-8'})
            with urlopen(req, context=ctx, timeout=TIMEOUT) as res:
                raw = res.read().decode('utf-8', 'replace')
        except HTTPError as e:
            if e.code in (401, 403):
                raise AuthError(f'HTTP {e.code} — 웹앱 권한 거부. 연쇄 요청 중단')
            if e.code == 429 or e.code >= 500:
                if attempt == MAX_ATTEMPTS:
                    raise TransientError(f'HTTP {e.code} 재시도 {MAX_ATTEMPTS}회 초과')
                log(f'  ⏸ HTTP {e.code} — {wait}초 대기 후 재시도 ({attempt}/{MAX_ATTEMPTS})')
                time.sleep(wait)
                continue
            raise AuthError(f'HTTP {e.code} — 웹앱 주소·배포 확인 필요 (재시도 안 함)')
        except (URLError, TimeoutError, ConnectionError, OSError) as e:
            if attempt == MAX_ATTEMPTS:
                raise TransientError(f'네트워크 오류 재시도 {MAX_ATTEMPTS}회 초과: {e}')
            log(f'  ⏸ 네트워크 오류 ({e}) — {wait}초 대기 후 재시도 ({attempt}/{MAX_ATTEMPTS})')
            time.sleep(wait)
            continue

        try:
            res_json = json.loads(raw)
        except ValueError:
            # 로그인 화면 HTML 등 — 웹앱 액세스 권한이 '모든 사용자'가 아니거나 URL 이 틀렸다
            raise AuthError('웹앱 응답이 JSON 이 아님 — 배포의 액세스 권한(모든 사용자)·URL 확인. 앞부분: '
                            + raw[:80].replace('\n', ' '))
        if not isinstance(res_json, dict):
            raise AuthError('웹앱 응답 형식 오류')
        if res_json.get('ok'):
            return res_json
        err = res_json.get('error') or 'unknown'
        if err in ('auth', 'not_configured'):
            raise AuthError(f'웹앱 거부: {err} — 토큰(.env SHEET_MIRROR_TOKEN ↔ 스크립트 속성 MIRROR_TOKEN) 확인')
        if err == 'busy':
            if attempt == MAX_ATTEMPTS:
                raise TransientError(f'웹앱 busy 재시도 {MAX_ATTEMPTS}회 초과')
            log(f'  ⏸ 웹앱 busy — {wait}초 대기 후 재시도 ({attempt}/{MAX_ATTEMPTS})')
            time.sleep(wait)
            continue
        raise RuntimeError(f'웹앱 오류: {err} {res_json.get("detail", "")}'.strip())
    raise TransientError('재시도 초과')


# ── 본체 ──
def meta_get(conn, key):
    row = conn.execute('SELECT value FROM meta WHERE key = ?', (key,)).fetchone()
    return row[0] if row else None


def collect(conn, table, wm):
    rows = [dict(r) for r in conn.execute(
        f'SELECT * FROM {table} WHERE updated_at > ? ORDER BY created_at, record_id', (wm or '',))]
    return rows, (max(r['updated_at'] for r in rows) if rows else wm)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    dry = '--dry-run' in argv
    force_full = '--full' in argv
    check = '--check' in argv
    t0 = time.time()
    env = load_env()
    url = env.get('SHEET_MIRROR_URL', '')
    token = env.get('SHEET_MIRROR_TOKEN', '')

    if not url and not dry:
        log('ℹ️  SHEET_MIRROR_URL 미설정 — 시트 미러 건너뜀')
        emit(skipped='not_configured', videos_sent=0, tips_sent=0, error='')
        return 0
    # (설치 전에도 --dry-run 은 보낼 건수를 센다 — 네트워크 0)
    if url and not url.startswith(ALLOWED_URL_PREFIXES):
        log('❌ SHEET_MIRROR_URL 이 Apps Script 웹앱 주소가 아님 — 보내지 않음')
        emit(skipped='', videos_sent=0, tips_sent=0, error='bad_url')
        return 2
    if not token and not dry:
        log('❌ SHEET_MIRROR_TOKEN 미설정 — 보내지 않음')
        emit(skipped='', videos_sent=0, tips_sent=0, error='no_token')
        return 2

    try:
        conn = ldb.open_existing(readonly=dry or check)
    except Exception as e:
        log(f'❌ 장부 열기 실패: {e}')
        emit(skipped='', videos_sent=0, tips_sent=0, error='library')
        return 1

    try:
        if check:
            db = {tab: conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] for table, tab, _, _ in TABS}
            try:
                res = post(url, {'token': token, 'op': 'ping'})
            except AuthError as e:
                log(f'❌ {e}'); emit(check=True, error='auth'); return 2
            except Exception as e:
                log(f'❌ {e}'); emit(check=True, error='transient'); return 1
            sheet = res.get('counts', {})
            match = all(sheet.get(tab) == n for tab, n in db.items())
            for tab, n in db.items():
                log(f'  {tab}: 장부 {n:,} · 시트 {sheet.get(tab, 0):,} {"✅" if sheet.get(tab) == n else "❌"}')
            emit(check=True, db=db, sheet=sheet, match=match, error='')
            return 0

        target = url_hash(url) if url else None
        full = force_full or target is None or meta_get(conn, 'sheet_target') != target
        plan = []
        for table, tab, headers, wm_key in TABS:
            wm = None if full else meta_get(conn, wm_key)
            rows, new_wm = collect(conn, table, wm)
            plan.append((table, tab, headers, wm_key, rows, new_wm))
        n_v, n_t = len(plan[0][4]), len(plan[1][4])
        log(f'📗 시트 미러{" (전체 다시 쓰기)" if full else ""}: 보낼 영상 {n_v:,} · 꿀팁 {n_t:,}')

        if dry:
            emit(dry_run=True, full=full, videos_sent=n_v, tips_sent=n_t, skipped='', error='')
            return 0

        sent = {'videos': 0, 'tips': 0}
        if full:
            # 전체 다시 쓰기가 중간에 끊기면 다음 실행도 전체여야 한다 — 끝날 때까지 대상 표시를 지워 둔다
            with conn:
                conn.execute("DELETE FROM meta WHERE key = 'sheet_target'")
        try:
            for table, tab, headers, wm_key, rows, new_wm in plan:
                if full:
                    post(url, {'token': token, 'op': 'reset', 'sheet': tab, 'headers': headers})
                for i in range(0, len(rows), CHUNK):
                    part = [ROW_FN[table](r) for r in rows[i:i + CHUNK]]
                    res = post(url, {'token': token, 'op': 'upsert', 'sheet': tab, 'headers': headers, 'rows': part})
                    sent[table] += len(part)
                    log(f'  {tab} [{min(i + CHUNK, len(rows))}/{len(rows)}] 추가 {res.get("inserted", 0)} · 갱신 {res.get("updated", 0)} · 시트 {res.get("total", "?")}행')
                # 이 탭의 묶음을 전부 보냈다 → 워터마크 올림 (한 탭씩 따로 확정)
                with conn:
                    if new_wm:
                        conn.execute('INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)', (wm_key, new_wm))
                    if full and table == TABS[-1][0]:
                        conn.execute('INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)', ('sheet_target', target))
            with conn:
                conn.execute('INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)',
                             ('sheet_last_ok', datetime.now(timezone.utc).isoformat(timespec='seconds')))
        except AuthError as e:
            log(f'❌ 시트 미러 중단 (재시도 안 함): {e}')
            emit(full=full, videos_sent=sent['videos'], tips_sent=sent['tips'], skipped='', error='auth')
            return 2
        except TransientError as e:
            log(f'❌ 시트 미러 실패 (다음 실행에 다시 보냄): {e}')
            emit(full=full, videos_sent=sent['videos'], tips_sent=sent['tips'], skipped='', error='transient')
            return 1
        except Exception as e:
            log(f'❌ 시트 미러 실패: {e}')
            emit(full=full, videos_sent=sent['videos'], tips_sent=sent['tips'], skipped='', error='other')
            return 1

        el = round(time.time() - t0, 1)
        log(f'✅ 시트 미러 완료 — 영상 {sent["videos"]:,} · 꿀팁 {sent["tips"]:,} ({el}초)')
        emit(full=full, videos_sent=sent['videos'], tips_sent=sent['tips'], skipped='', error='', elapsed=el)
        return 0
    finally:
        conn.close()


if __name__ == '__main__':
    sys.exit(main())
