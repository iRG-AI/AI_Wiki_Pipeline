#!/usr/bin/env python3
"""
텔레그램 전용 봇 → 장부 tips (v4.18) — 꿀팁 두 번째 입구. 카톡 CSV 와 같은 엔진(kakao_ingest 함수)으로 같은 tips 표에 넣는다.

    /opt/homebrew/bin/python3 telegram_tips_ingest.py            # dry-run (기본): 장부·meta 쓰기 0 · 답장 0
    /opt/homebrew/bin/python3 telegram_tips_ingest.py --apply    # 장부에 넣고 봇 방에 답장
    /opt/homebrew/bin/python3 telegram_tips_ingest.py --whoami   # 봇 방의 chat id 를 터미널에만 찍는다 (확인 처리 안 됨)
    옵션: --no-lookup  원문 제목 조회 없이 (카톡과 같은 뜻 · .env KAKAO_TITLE_* 설정을 그대로 쓴다)

.env: TIPS_BOT_TOKEN(전용 봇 토큰 — 실행 알림 봇과 다른 봇) · TIPS_BOT_CHAT_ID(허용할 개인 대화 하나). 토큰이 없으면 skipped.
상태는 장부 meta 두 키(tips_bot_offset · tips_bot_last_ok) — tips INSERT 와 같은 트랜잭션으로 쓴다(커밋 뒤에만 offset 이 오른다).
토큰은 URL 경로에 들어간다: 요청 URL·토큰·chat id 를 로그·RESULT_JSON·예외 문구에 쓰지 않는다.
마지막 줄 RESULT_JSON:{...} (scheduler.js:runTipsBot 이 파싱). 종료 0 정상/skipped · 1 일시 오류·장부 오류 · 2 중단(auth·conflict·bad_request).
지침서 docs/tasks/2026-11-03-v418-telegram-tips-bot.md
"""
import json, os, sys, time, urllib.error, urllib.request
from datetime import datetime, timezone, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
sys.path.insert(0, os.path.join(SCRIPT_DIR, 'lib'))

import kakao_ingest as ki          # 공용 엔진 + 로그/RESULT_JSON (테스트가 ki.load_env 등을 바꿔치기한다)
from kakao_parse import links_from_messages, extract_urls, url_key
import library_db as ldb

KST = timezone(timedelta(hours=9))
FATAL = {401: 'auth', 403: 'auth', 404: 'auth', 409: 'conflict', 400: 'bad_request'}


class TgError(Exception):
    """텔레그램 응답 실패. 메시지에는 상태 코드만 — URL(토큰 포함)을 넣지 않는다. code 0 = 네트워크·timeout·JSON 아님."""
    def __init__(self, code, retry_after=None):
        super().__init__(f'HTTP {code}')
        self.code, self.retry_after = code, retry_after


class Abort(Exception):
    def __init__(self, kind):
        super().__init__(kind)
        self.kind = kind


def tg(token, method, payload):
    req = urllib.request.Request(f'https://api.telegram.org/bot{token}/{method}', data=json.dumps(payload).encode('utf-8'),
                                 headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            code, raw = r.status, r.read()
    except urllib.error.HTTPError as e:
        code, raw = e.code, e.read()
    except Exception:
        raise TgError(0)
    try:
        body = json.loads(raw)
    except Exception:
        body = None
    if code == 200 and isinstance(body, dict) and body.get('ok'):
        return body
    ra = ((body or {}).get('parameters') or {}).get('retry_after') if isinstance(body, dict) else None
    raise TgError(code if code != 200 else 0, ra)


def get_updates(token, payload, attempts=3):
    """getUpdates. 401·403·404·409·400 은 재시도 없이 중단, 429 는 retry_after(상한 60) 대기, 5xx·네트워크는 2·4초 백오프, 소진되면 transient."""
    for i in range(attempts):
        try:
            return tg(token, 'getUpdates', payload)['result']
        except TgError as e:
            if e.code in FATAL:
                raise Abort(FATAL[e.code])
            if i == attempts - 1:
                raise Abort('transient')
            time.sleep(min(e.retry_after or 5, 60) if e.code == 429 else 2 * 2 ** i)


def send_reply(token, chat, mid, text):
    """답장 1통 → 'ok' | 'skip'(이 답장만 건너뜀) | 'stop'(남은 답장 포기). 적재에는 영향이 없다."""
    payload = {'chat_id': int(chat) if chat.lstrip('-').isdigit() else chat, 'text': text,
               'reply_parameters': {'message_id': mid, 'allow_sending_without_reply': True}}
    for i in (0, 1):
        try:
            tg(token, 'sendMessage', payload)
            return 'ok'
        except TgError as e:
            if e.code == 400:
                return 'skip'
            if e.code == 429 and i == 0:
                time.sleep(min(e.retry_after or 5, 60))
                continue
            return 'stop'
    return 'stop'


def meta_get(conn, key):
    r = conn.execute('SELECT value FROM meta WHERE key = ?', (key,)).fetchone()
    return r[0] if r else None


def stale_hours(last_ok, now):
    if not last_ok:
        return None
    try:
        t = datetime.strptime(last_ok, '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=timezone.utc)
        return round((now - t).total_seconds() / 3600, 1)
    except ValueError:
        return None


def collect(updates, chat):
    """업데이트 → (메시지 목록, 허용 밖 건수, 허용 밖 출처 요약). 메시지 = {'date','message','urls','ref'}.
    출처 요약은 방 종류별 건수 · 그중 대표님 발신 · 링크 있음 (id 는 남기지 않는다)."""
    msgs, dropped, kinds, own, linked = [], 0, {}, 0, 0
    for u in updates:
        m = u.get('message')
        if not m:
            continue
        if str((m.get('chat') or {}).get('id')) != chat:
            dropped += 1
            k = (m.get('chat') or {}).get('type') or '?'
            kinds[k] = kinds.get(k, 0) + 1
            own += str((m.get('from') or {}).get('id')) == chat
            linked += bool(extract_urls(m.get('text') or m.get('caption') or ''))
            continue
        text = m.get('text') or m.get('caption') or ''
        urls = extract_urls(text) + [e['url'] for e in (m.get('entities') or []) + (m.get('caption_entities') or [])
                                     if e.get('type') == 'text_link' and e.get('url')]
        date = datetime.fromtimestamp(m.get('date') or 0, KST).strftime('%Y-%m-%d %H:%M:%S')
        msgs.append({'date': date, 'message': text, 'urls': urls, 'ref': (u['update_id'], m['message_id'])})
    why = ' · '.join(f'{k} {n}' for k, n in sorted(kinds.items()))
    return msgs, dropped, (f' ({why} · 본인 발신 {own} · 링크 {linked})' if dropped else '')


def main():
    apply = '--apply' in sys.argv
    env = ki.load_env()
    token, chat = (env.get('TIPS_BOT_TOKEN') or '').strip(), (env.get('TIPS_BOT_CHAT_ID') or '').strip()
    if not token:
        ki.log('ℹ️  TIPS_BOT_TOKEN 없음 — 텔레그램 꿀팁 입구 건너뜀')
        ki.emit_result(skipped='not_configured', created=0, candidates=0)
        return 0

    if '--whoami' in sys.argv:
        try:
            ups = get_updates(token, {'timeout': 0, 'limit': 100, 'allowed_updates': ['message']})
        except Abort as a:
            ki.log(f'❌ 조회 실패: {a.kind}')
            return 2 if a.kind != 'transient' else 1
        seen = {}
        for u in ups:
            c = (u.get('message') or {}).get('chat') or {}
            if c.get('type') == 'private':
                seen[c['id']] = ' '.join(filter(None, [c.get('first_name'), c.get('last_name')])) or c.get('username') or ''
        for cid, name in seen.items():   # 터미널에만 — 로그 파일·RESULT_JSON 에 남기지 않는다
            print(f'chat id: {cid}  ({name})', flush=True)
        if not seen:
            print('개인 대화 없음 — 봇 방에서 /start 를 보낸 뒤 다시', flush=True)
        return 0

    if not chat:
        ki.log('ℹ️  TIPS_BOT_CHAT_ID 없음 — --whoami 로 확인해 .env 에 넣으세요')
        ki.emit_result(skipped='no_chat_id', created=0, candidates=0)
        return 0

    ki.log(f"{'🚀 APPLY' if apply else '👀 DRY-RUN'} · 텔레그램 꿀팁 입구")
    try:
        conn = ldb.open_existing(readonly=not apply)
        n_rows, existing = ki.existing_keys(conn)
        offset = int(meta_get(conn, 'tips_bot_offset') or 0)
        last_ok = meta_get(conn, 'tips_bot_last_ok')
    except Exception as e:
        ki.log(f'❌ 장부 열기 실패: {type(e).__name__}')
        ki.emit_result(error='ledger', created=0, candidates=0, db_total=None)
        return 1
    now = datetime.now(timezone.utc)
    stale = stale_hours(last_ok, now)
    res = dict(created=0, dup=0, no_link=0, dropped=0, candidates=0, db_total=n_rows, stale_h=stale)

    payload = {'timeout': 0, 'limit': 100, 'allowed_updates': ['message']}
    if offset:
        payload['offset'] = offset + 1
    try:
        updates = get_updates(token, payload)
    except Abort as a:
        conn.close()
        ki.log(f'❌ getUpdates 실패: {a.kind}')
        ki.emit_result(error=a.kind, **res)
        return 1 if a.kind == 'transient' else 2
    if len(updates) >= 100:
        ki.log('ℹ️  업데이트 100건 — 남음, 다음 실행이 이어 받음')
    msgs, res['dropped'], why = collect(updates, chat)
    ki.log(f'📨 업데이트 {len(updates)}건 (허용 대화 메시지 {len(msgs)} · 허용 밖 {res["dropped"]}{why})')

    links = links_from_messages(msgs)
    new = [l for l in links if l['key'] not in existing]
    res['candidates'] = len(new)
    found, tstat = ki.resolve_titles(new) if new else ({}, {'need': 0, 'ok': 0, 'fail': 0, 'skipped': 0})
    res['title_lookup'] = {k: tstat[k] for k in ('need', 'ok', 'fail', 'skipped')}
    plan = ki.plan_rows(new, found) if new else []
    owner = {l['key']: l['ref'] for l in new}   # 이번에 만든 행을 처음 실은 메시지

    if not apply:
        conn.close()
        ki.log(f'\n👀 dry-run 종료 — 신규 {len(plan)}건은 생성되지 않았습니다. 실제 생성은 --apply')
        ki.emit_result(dry_run=True, **res)
        return 0

    meta = [('tips_bot_last_ok', now.strftime('%Y-%m-%dT%H:%M:%S.') + f'{now.microsecond // 1000:03d}Z')]
    if updates:
        meta.append(('tips_bot_offset', max(u['update_id'] for u in updates)))
    try:
        titles, res['db_total'] = ki.insert_rows(conn, plan, meta)
    except Exception as e:
        ki.log(f'❌ 장부 쓰기 실패 — 아무 행도 넣지 않았습니다: {type(e).__name__}')
        ki.emit_result(error='ledger', **res)
        return 1
    finally:
        conn.close()
    res['created'] = len(titles)
    shown = {l['key']: (t, p['category']) for l, p, t in zip(new, plan, titles)}   # owner 와 같은 키(원본 기준)

    # 커밋 뒤에 답장 — 실패해도 적재는 그대로
    replies = []
    for m in msgs:
        mid = m['ref'][1]
        keys = list(dict.fromkeys(url_key(u) for u in m['urls']))
        if not keys:
            res['no_link'] += 1
            replies.append((mid, '링크 없음'))
        for k in keys:
            if owner.get(k) == m['ref']:
                replies.append((mid, '저장: {} · {}'.format(*shown[k])))
            else:
                res['dup'] += 1
                replies.append((mid, '이미 있음'))
    for i, (mid, text) in enumerate(replies):
        if i:
            time.sleep(1)
        if send_reply(token, chat, mid, text) == 'stop':
            ki.log('⚠️ 답장 중단 (적재는 유지)')
            break
    ki.log(f'🎉 생성 {res["created"]}건 · 이미 있음 {res["dup"]} · 링크 없음 {res["no_link"]} · 장부 tips 총 {res["db_total"]}건')
    ki.emit_result(titles=titles[:10], **res)
    return 0


if __name__ == '__main__':
    sys.exit(main())
