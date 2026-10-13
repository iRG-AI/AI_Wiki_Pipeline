#!/usr/bin/env python3
# ===== Obsidian 증분 동기화 스크립트 (v4.0: 원본 = 로컬 장부 data/library.db) =====
# 스케줄러가 영상 저장·카톡 인제스트 뒤에 자동 실행:
#   1. 장부 videos 의 topics → 기존 노트 tags 동기화
#   2. 장부에만 있는 영상 → .md 추가 (본문 = 요약 마크다운)
#   3. 장부에 없는 notion_id 를 가진 영상 노트 → _trash/ 격리 (3중 안전장치)
#   4. 장부 tips 중 노트 없는 것 → AI 꿀팁/ 노트 추가 (꿀팁 고아는 보고만 한다)
#   (v4.6-b) 장부가 실제 영상 요약(summary_src video)인데 노트 프론트매터 summary_src·grade 가 다르면
#            그 노트의 요약 절만 제자리 교체 + grade·summary_src 를 맞춘다 (재요약 · 장부 grade 수정)
#   5. 변경이 있으면 MOC·Wiki·검색 인덱스 재구성
#
# 실행: /opt/homebrew/bin/python3 sync_obsidian.py [--rebuild] [--no-tips] [--orphans-dry-run] [--dry-run]
#   --dry-run  Vault·log.md·장부를 하나도 쓰지 않고 할 일만 센다 (재구성·인제스트·인덱스도 건너뜀)
#
# 네트워크: 이 파일은 노션을 부르지 않는다. 장부는 읽기 전용(mode=ro)으로만 연다.
# 프론트매터 키 `notion_id` 는 이름만 노션 시절 그대로다 — 값은 장부 record_id (노션에서 옮긴 행 = 노션 page id, 새 행 = uuid4).

import os, re, json, shutil, subprocess, sys, time, unicodedata
from datetime import datetime

VAULT    = '/Users/tycoonan/Documents/Obsidian/AI LLM Wiki/AI LLM Wiki'
MOC_DIR  = os.path.join(VAULT, '_MOC')
TRASH_DIR = os.path.join(VAULT, '_trash')
LOG_FILE = os.path.join(VAULT, 'log.md')
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TIPS_FOLDER = 'AI 꿀팁'   # v2.8 카톡 링크 노트 폴더. YouTube 로직(고아 격리·tags 동기화)에서 제외된다.
sys.path.insert(0, os.path.join(SCRIPT_DIR, 'lib'))
import library_db as ldb   # noqa: E402  v4.0 장부 (DB_PATH·open_existing)

def nfc(s):
    """macOS NFD 파일명을 NFC로 정규화 (한글 깨짐 방지)"""
    return unicodedata.normalize('NFC', s) if s else s

# ── Wiki log.md에 항목 추가 ──
def write_wiki_log(event_type, summary, details=None):
    """
    event_type: 'ingest' | 'rebuild' | 'error'
    summary: 한 줄 요약
    details: 추가 정보 dict (선택)
    """
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    today = datetime.now().strftime('%Y-%m-%d')

    # log.md 없으면 헤더와 함께 새로 생성
    if not os.path.exists(LOG_FILE):
        header = '# 📋 AI LLM Wiki 변경 이력\n\n> Wiki에 일어난 모든 변경사항을 시간순으로 기록합니다.\n> 파싱 팁: `grep "^## \\[" log.md | tail -10` 으로 최근 10개 확인\n\n'
        open(LOG_FILE, 'w', encoding='utf-8').write(nfc(header))

    # 아이콘 매핑
    icon = {'ingest': '📥', 'rebuild': '🔧', 'error': '❌', 'cleanup': '🧹'}.get(event_type, '📌')

    # 항목 작성
    entry = f'## [{today}] {event_type} | {summary}\n'
    entry += f'> {icon} {now}\n\n'
    if details:
        for k, v in details.items():
            entry += f'- **{k}**: {v}\n'
    entry += '\n'

    # 파일 앞에 추가 (최신이 위로)
    existing = open(LOG_FILE, encoding='utf-8').read()
    # 헤더 이후에 삽입
    insert_pos = existing.find('\n\n', existing.find('파싱 팁')) + 2
    new_content = existing[:insert_pos] + entry + existing[insert_pos:]
    open(LOG_FILE, 'w', encoding='utf-8').write(nfc(new_content))

def log(msg): print(msg, flush=True)

# ── 프론트매터 (맨 앞 YAML 블록) ──
# notion_id·video_url 은 프론트매터 안의 것만 센다. schema.md 처럼 본문 코드블록에 예시
# 'notion_id: xxxxxxxx-…' 를 담은 문서를 영상 노트로 오인하지 않기 위함 (2026-10-11 dry-run 실측, scripts/verify_library.py 와 같은 규칙).
FM_RE = re.compile(r'\A﻿?---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)', re.S)

def fm_text(content):
    m = FM_RE.match(content or '')
    return m.group(1) if m else ''

def fm_value(content, key):
    m = re.search(rf'^{re.escape(key)}:\s*(.+)$', fm_text(content), re.MULTILINE)
    return m.group(1).strip() if m else None

def fm_notion_id(path):
    try:
        return fm_value(nfc(open(path, encoding='utf-8', errors='ignore').read()), 'notion_id')
    except Exception:
        return None

# ── 파일명 안전 변환 ──
def safe_filename(s):
    return re.sub(r'[\/\\:*?"<>|#]', '_', s or 'untitled').strip()[:120]

# ── 기존 Vault 파일 정보 수집 (notion_id, relpath, video_url) ──
def get_existing_vault_info():
    """
    id_to_path: notion_id -> fpath   (프론트매터 안의 notion_id 만)
    relpath_set: Vault 상대 파일 경로 집합
    url_to_path: video_url -> fpath  (프론트매터 안의 video_url 만)
    """
    id_to_path = {}
    relpath_set = set()
    url_to_path = {}

    for root, dirs, files in os.walk(VAULT):
        # 꿀팁 폴더는 YouTube 영상 로직(고아 격리 분모·tags 동기화)에 섞이지 않게 제외 (v2.8)
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('_MOC', '_trash') and nfc(d) != TIPS_FOLDER]
        for f in files:
            if not f.endswith('.md'): continue
            fpath = os.path.join(root, f)
            relpath = nfc(os.path.relpath(fpath, VAULT))
            relpath_set.add(relpath)
            try:
                content = nfc(open(fpath, encoding='utf-8', errors='ignore').read())
            except Exception:
                continue
            nid = fm_value(content, 'notion_id')
            if nid:
                id_to_path[nid] = fpath
            url = fm_value(content, 'video_url')
            if url and url != 'null':
                url_to_path[url] = fpath
    return id_to_path, relpath_set, url_to_path

def get_existing_notion_ids():
    id_to_path, _, _ = get_existing_vault_info()
    return id_to_path


# ── 장부 읽기 (읽기 전용) ──
def _json_list(s):
    try:
        v = json.loads(s or '[]')
        return [nfc(x) for x in v if x] if isinstance(v, list) else []
    except Exception:
        return []

def load_library():
    """(videos, tips) — 각 행은 dict, topics·tags 는 list. 장부가 없거나 버전이 다르면 던진다(만들지 않는다)."""
    conn = ldb.open_existing(readonly=True)
    try:
        videos = [dict(r) for r in conn.execute('SELECT * FROM videos ORDER BY created_at, record_id')]
        tips = [dict(r) for r in conn.execute('SELECT * FROM tips ORDER BY created_at, record_id')]
    finally:
        conn.close()
    for v in videos:
        v['topics'] = _json_list(v.get('topics'))
    for t in tips:
        t['tags'] = _json_list(t.get('tags'))
    return videos, tips


# ── 기존 .md 파일의 frontmatter tags 업데이트 ──
def update_tags_in_file(fpath, new_topics, dry_run=False):
    """프론트매터의 tags: 라인만 교체. 변경(dry_run 이면 변경 예정) 시 True 반환."""
    try:
        content = nfc(open(fpath, encoding='utf-8', errors='ignore').read())
    except Exception:
        return False
    m_fm = FM_RE.match(content)
    if not m_fm:
        return False
    new_tags_line = f'tags: [{", ".join(chr(34) + t + chr(34) for t in new_topics)}]'
    m = re.search(r'^tags:.*$', m_fm.group(1), re.MULTILINE)
    if not m:
        return False  # tags 라인 없으면 스킵
    if m.group(0) == new_tags_line:
        return False  # 변경 없음
    if dry_run:
        return True
    start = m_fm.start(1) + m.start()
    end = m_fm.start(1) + m.end()
    open(fpath, 'w', encoding='utf-8').write(nfc(content[:start] + new_tags_line + content[end:]))
    return True

# ── 기존 파일 tags 를 장부 topics 와 동기화 ──
def sync_existing_tags(videos, dry_run=False):
    """장부의 현재 topics 와 Obsidian .md tags 를 맞춤. 변경된(dry_run 이면 변경될) 파일 수 반환."""
    log('🏷  기존 파일 tags 동기화 중...')
    id_to_path = get_existing_notion_ids()

    updated = 0
    for v in videos:
        rid = v['record_id']
        if rid not in id_to_path:
            continue
        if update_tags_in_file(id_to_path[rid], v['topics'], dry_run):
            updated += 1
            if dry_run and updated <= 10:
                log(f'    [dry-run] tags → {v["topics"]}  {nfc(os.path.relpath(id_to_path[rid], VAULT))}')

    if updated > 0:
        log(f'  ✅ {updated}개 파일 tags {"갱신 예정 (dry-run)" if dry_run else "갱신"}\n')
    else:
        log(f'  ✅ 변경 없음 (모두 최신 상태)\n')
    return updated

# ── (v4.6-b) 재요약된 영상 노트 요약 절 제자리 교체 ──
# 노트 모양: 프론트매터 · (빈 줄) · '**▶ 영상 보기: **URL' · '---' · 요약 · (build_obsidian_wiki 가 붙인) '\n\n---\n## 🔗 관련 항목…'
# 요약 = '---' 줄 다음부터 관련 항목 절 앞까지. 관련 항목 절은 그대로 둔다. 경계를 못 찾으면 그 노트는 건드리지 않는다.
WATCH_RE = re.compile(r'^\*\*▶ 영상 보기: \*\*[^\n]*\n---[ \t]*\n', re.M)
RELATED_MARK = '\n\n---\n## 🔗 관련 항목'

def _set_fm_key(content, key, value):
    """프론트매터의 key 줄을 value 로. 없으면 notion_id 줄 앞(없으면 프론트매터 끝)에 넣는다. 프론트매터가 없으면 None"""
    m = FM_RE.match(content)
    if not m:
        return None
    fm = m.group(1)
    line = f'{key}: {value}'
    km = re.search(rf'^{re.escape(key)}:.*$', fm, re.M)
    if km:
        fm2 = fm[:km.start()] + line + fm[km.end():]
    else:
        nm = re.search(r'^notion_id:.*$', fm, re.M)
        fm2 = (fm[:nm.start()] + line + '\n' + fm[nm.start():]) if nm else (fm + '\n' + line)
    return content[:m.start(1)] + fm2 + content[m.end(1):]

def refreshed_note(content, rec, replace_body):
    """새 노트 내용(바뀔 게 없으면 원문 그대로) 또는 경계를 못 찾으면 None"""
    new = content
    if replace_body:
        m = FM_RE.match(new)
        w = WATCH_RE.search(new, m.end() if m else 0)
        if not m or not w:
            return None
        start = w.end()
        end = new.find(RELATED_MARK, start)
        if end < 0:
            end = len(new)
            tail = '\n' if new.endswith('\n') else ''
        else:
            tail = ''
        new = new[:start] + nfc(rec.get('summary') or '').strip('\n') + tail + new[end:]
    for key, val in (('grade', rec.get('grade') or 'null'), ('summary_src', rec.get('summary_src') or 'app')):
        new = _set_fm_key(new, key, val)
        if new is None:
            return None
    return nfc(new)

REFRESH_STATS = {'skipped': 0}

def refresh_changed_notes(videos, dry_run=False):
    """장부 summary_src 가 'video' 인 행만 본다. 노트 프론트매터 summary_src 가 video 가 아니면 요약 절 교체 + 키 맞춤,
    video 인데 grade 만 다르면 grade 줄만. 바뀐(dry_run 이면 바뀔) 노트 수 반환. 설명란 요약 행·노트 없는 행은 건드리지 않는다."""
    REFRESH_STATS['skipped'] = 0
    targets = [v for v in videos if v.get('summary_src') == 'video']
    if not targets:
        return 0
    log('🔁 재요약·등급 변경 노트 맞춤 중...')
    id_to_path = get_existing_notion_ids()
    changed = 0
    for v in targets:
        p = id_to_path.get(v['record_id'])
        if not p:
            continue
        try:
            content = nfc(open(p, encoding='utf-8', errors='ignore').read())
        except Exception:
            continue
        cur_src, cur_grade = fm_value(content, 'summary_src'), fm_value(content, 'grade')
        want_grade = v.get('grade') or 'null'
        if cur_src == 'video' and cur_grade == want_grade:
            continue
        new = refreshed_note(content, v, replace_body=(cur_src != 'video'))
        if new is None:
            REFRESH_STATS['skipped'] += 1
            log(f'    ⚠️  요약 절 경계를 못 찾음 — 건드리지 않음: {nfc(os.path.relpath(p, VAULT))}')
            continue
        if new == content:
            continue
        changed += 1
        if dry_run:
            if changed <= 10:
                log(f'    [dry-run] {"요약 교체" if cur_src != "video" else "grade"} → {want_grade}  {nfc(os.path.relpath(p, VAULT))}')
            continue
        open(p, 'w', encoding='utf-8').write(new)
    log(f'  ✅ {changed}개 노트 {"맞춤 예정 (dry-run)" if dry_run else "맞춤"}'
        + (f' · 경계 못 찾아 건너뜀 {REFRESH_STATS["skipped"]}' if REFRESH_STATS['skipped'] else '') + '\n')
    return changed

# ── 영상 노트 내용 ──
# 노션 시절 노트(본문 블록 → 마크다운)와 같은 모양: 빈 줄(썸네일 자리) · '▶ 영상 보기' · 구분선 · 요약.
def _q(s):
    return (s or '').replace('"', "'")

def video_target(rec):
    """(폴더, 파일명, Vault 상대 경로)"""
    topics = rec['topics']
    folder = topics[0] if topics else '기타'
    upload_date = rec.get('upload_date') or ''
    date_part = (upload_date[:10].replace('-', '') if upload_date else '00000000')
    filename = nfc(safe_filename(f'{rec.get("channel") or ""}_{rec.get("title") or ""}_{date_part}') + '.md')
    folder_name = nfc(safe_filename(folder))
    return folder_name, filename, nfc(os.path.join(folder_name, filename))

def video_note_md(rec):
    video_url = rec.get('video_url') or ''
    body_md = '\n'.join(['', f'**▶ 영상 보기: **{video_url}', '---', rec.get('summary') or ''])
    md = '\n'.join([
        '---',
        f'title: "{_q(rec.get("title"))}"',
        f'channel: "{_q(rec.get("channel"))}"',
        f'tags: [{", ".join(f"{chr(34)}{t}{chr(34)}" for t in rec["topics"])}]',
        f'upload_date: {rec.get("upload_date") or "null"}',
        f'view_count: {rec.get("view_count") or 0}',
        f'subscriber_count: {rec.get("subscriber_count") or 0}',
        f'video_url: {video_url or "null"}',
        f'thumbnail: {rec.get("thumbnail_url") or "null"}',
        f'status: {rec.get("status") or ""}',
        # (v4.6) grade: keep | exclude | null(미판정). exclude 노트는 Vault 에 두고 Wiki 합성·검색 인덱스에서만 뺀다
        f'grade: {rec.get("grade") or "null"}',
        f'summary_src: {rec.get("summary_src") or "app"}',
        f'notion_id: {rec["record_id"]}',
        '---',
        '',
        body_md,
    ])
    return nfc(md)  # NFD→NFC 정규화

def save_record_as_md(rec):
    folder_name, filename, _ = video_target(rec)
    dir_path = os.path.join(VAULT, folder_name)
    os.makedirs(dir_path, exist_ok=True)
    open(os.path.join(dir_path, filename), 'w', encoding='utf-8').write(video_note_md(rec))
    return folder_name, filename

def sync_new_pages(videos, dry_run=False):
    log('📦 기존 Vault 파일 및 notion_id 정보 수집 중...')
    id_to_path, relpath_set, url_to_path = get_existing_vault_info()
    existing_ids = set(id_to_path.keys())
    log(f'  기존 notion_id 등록 파일: {len(existing_ids)}개, Vault md 문서: {len(relpath_set)}개\n')

    new_recs = []
    seen_targets = set()
    skipped = {'same_path': [], 'same_url': []}

    for rec in videos:
        if rec['record_id'] in existing_ids:
            continue
        _, _, target_relpath = video_target(rec)
        video_url = rec.get('video_url') or ''

        # 이미 Vault에 동일 상대 경로 문서가 존재하거나 동일 video_url 문서가 존재하는 경우 스킵 (중복 무한 덮어쓰기 방지)
        if target_relpath in relpath_set or target_relpath in seen_targets:
            skipped['same_path'].append(target_relpath); continue
        if video_url and video_url in url_to_path:
            skipped['same_url'].append(video_url); continue

        seen_targets.add(target_relpath)
        new_recs.append(rec)

    log(f'✨ 신규 영상: {len(new_recs)}개'
        + (f' (노트 없이 건너뜀: 같은 경로 {len(skipped["same_path"])} · 같은 video_url {len(skipped["same_url"])})'
           if skipped['same_path'] or skipped['same_url'] else '') + '\n')
    for x in (skipped['same_path'] + skipped['same_url'])[:5]:
        log(f'    [건너뜀] {x}')

    added = 0
    for i, rec in enumerate(new_recs):
        if dry_run:
            log(f'  [dry-run {i+1}/{len(new_recs)}] {video_target(rec)[2]}')
            added += 1
            continue
        try:
            folder, fname = save_record_as_md(rec)
            log(f'  [{i+1}/{len(new_recs)}] {folder}/{fname}')
            added += 1
        except Exception as e:
            log(f'  ❌ 오류: {e}')

    log(f'\n✅ {added}개 신규 파일 {"추가 예정 (dry-run)" if dry_run else "추가 완료"}\n')
    return added, {k: len(v) for k, v in skipped.items()}

# launchd 의 com.irichgreen.wiki-ingest 가 StandardOutPath 로 쓰는 바로 그 파일.
# sync_obsidian 경로에서 띄운 wiki_ingest 의 출력도 여기에 append 해서
# 두 실행 경로를 한 로그에서 보게 한다.
WIKI_LOG = os.path.expanduser('~/Library/Logs/irichgreen/wiki-ingest.log')

def _tee_wiki_log(stdout, stderr):
    """서브프로세스로 띄운 wiki_ingest 의 출력을 wiki-ingest.log 에 append.

    실패해도 본 동기화를 죽이지 않는다 (로그는 부가 기능).
    """
    if not (stdout or stderr):
        return
    try:
        os.makedirs(os.path.dirname(WIKI_LOG), exist_ok=True)
        with open(WIKI_LOG, 'a', encoding='utf-8') as f:
            f.write(f"\n───── via sync_obsidian.py (subprocess) {datetime.now().isoformat(timespec='seconds')} ─────\n")
            if stdout:
                f.write(stdout if stdout.endswith('\n') else stdout + '\n')
            if stderr:
                f.write('[stderr]\n' + stderr)
    except OSError as e:
        log(f'⚠️  wiki-ingest.log 기록 실패(무시): {e}')

# ── 장부 tips → VAULT/AI 꿀팁/*.md (신규만, 평면 폴더) ──
# 설계 제약 (docs/tasks/2026-09-06-kakao-tips-ingest.md §4-1):
#   · 프론트매터 키는 link_url — video_url 절대 금지 (고아 격리 오탐 방지)
#   · 폴더는 TIPS_FOLDER 평면 구조 — wiki_ingest/build_obsidian_wiki 가 최상위 폴더만 순회하므로 하위 폴더 금지
#   · tags 키를 쓰지 않는다 — build_obsidian_wiki 가 tags 없으면 폴더명으로 MOC 를 만든다 (_MOC/AI 꿀팁.md)
#   · 카테고리 '모델/LLM' 의 슬래시는 파일명에 못 쓴다 → safe_filename 이 '_' 로 치환
# 꿀팁 고아(장부에 없는 notion_id 를 가진 꿀팁 노트)는 옮기지 않고 보고만 한다 (v4.0 2단계 결정):
#   꿀팁 삭제는 장부를 직접 고칠 때만 생기는 드문 일이고, 꿀팁 폴더는 영상 고아 격리의 안전장치 분모 밖이다.
def tip_note_md(r):
    q = _q
    saved = r.get('saved_date') or ''
    lines = [
        '---',
        f'title: "{q(r["title"])}"',
        f'channel: "{q(r["source"])}"',
        'source_type: tip',
        f'category: "{q(r["category"])}"',
        f'keywords: [{", ".join(chr(34) + q(t) + chr(34) for t in r["tags"])}]',
        f'importance: {r["importance"] or "null"}',
        f'status: {r["status"] or "null"}',
        f'upload_date: {saved[:10] if saved else "null"}',
        f'link_url: {r["url"] or "null"}',
        f'memo: "{q(r["memo"])}"',
        f'notion_id: {r["record_id"]}',
        '---',
        '',
        f'# {r["title"]}',
        '',
        f'- 🔗 링크: {r["url"]}',
        f'- 📂 카테고리: {r["category"]}  ·  중요도: {r["importance"]}  ·  상태: {r["status"]}',
        f'- 🏷 태그: {", ".join(r["tags"]) if r["tags"] else "(없음)"}',
        f'- 🗓 저장일: {saved}  ·  출처: {r["source"]}',
    ]
    if r['memo']:
        lines.append(f'- 📝 메모: {r["memo"]}')
    if (r.get('body_md') or '').strip():
        lines += ['', '## 본문', '', r['body_md']]
    return nfc('\n'.join(lines)) + '\n'

def sync_tips(tips, dry_run=False):
    """반환: (추가 건수, 꿀팁 고아 건수)"""
    log(f'🔗 장부 tips {len(tips)}건')
    tips_dir = os.path.join(VAULT, TIPS_FOLDER)
    if not dry_run:
        os.makedirs(tips_dir, exist_ok=True)

    existing = {}   # notion_id -> 파일명
    if os.path.isdir(tips_dir):
        for f in os.listdir(tips_dir):
            if not f.endswith('.md'): continue
            nid = fm_notion_id(os.path.join(tips_dir, f))
            if nid: existing[nid] = nfc(f)

    live = {t['record_id'] for t in tips}
    tip_orphans = sorted(fn for nid, fn in existing.items() if nid not in live)
    if tip_orphans:
        log(f'  ⚠️  장부에 없는 꿀팁 노트 {len(tip_orphans)}개 (옮기지 않음 — 확인용): {tip_orphans[:5]}')

    new_tips = [t for t in tips if t['record_id'] not in existing]
    log(f'✨ 신규 꿀팁: {len(new_tips)}개 (기존 {len(existing)}개)\n')

    added = 0
    for i, r in enumerate(new_tips):
        try:
            saved = r.get('saved_date') or ''
            date_part = (saved[:10].replace('-', '') if saved else '00000000')
            fname = nfc(safe_filename(f"{date_part}_{r['title']}") + '.md')
            # 같은 날 같은 추정 제목("노션 자료 (제목 미확인)" 등)이 여럿이면 덮어쓰기 → notion_id 유실 → 매 실행 재생성.
            # 파일이 이미 있으면(=다른 notion_id) id 끝 6자리를 붙여 유일하게 만든다.
            if os.path.exists(os.path.join(tips_dir, fname)):
                fname = nfc(safe_filename(f"{date_part}_{r['title']}_{r['record_id'][-6:]}") + '.md')
            if dry_run:
                log(f'  [dry-run {i+1}/{len(new_tips)}] {TIPS_FOLDER}/{fname}')
            else:
                open(os.path.join(tips_dir, fname), 'w', encoding='utf-8').write(tip_note_md(r))
                log(f'  [{i+1}/{len(new_tips)}] {TIPS_FOLDER}/{fname}')
            added += 1
        except Exception as e:
            log(f'  ❌ 꿀팁 오류: {e}')

    log(f'\n✅ 꿀팁 {added}개 신규 파일 {"추가 예정 (dry-run)" if dry_run else "추가 완료"}\n')
    return added, len(tip_orphans)

# ── 고아 파일 격리 (장부에 없는 영상 노트) ──
ORPHAN_STATS = {'candidates': 0, 'blocked': ''}   # 마지막 점검 결과 (RESULT_JSON 보고용)

def quarantine_orphans(videos, dry_run=False):
    """
    장부 videos 에 없는 notion_id 를 가진 영상 노트를 _trash/ 로 이동. 이동 건수 반환.
    v4.0 첫 실행에서 videos_dup(중복 보관) 을 가리키던 노트가 여기서 격리된다 — 의도 (10-11 실측 0건).
    삭제가 아니라 이동인 이유: 장부를 잘못 읽어 목록이 비면 대량 소실이 되므로 되돌릴 수 있어야 한다.
    아래 3중 안전장치가 모두 통과할 때만 실행한다 (완화 금지).
    """
    log('🧹 고아 파일 점검 중 (장부에 없는 영상 노트)...')
    id_to_path, _, _ = get_existing_vault_info()
    ORPHAN_STATS.update(candidates=0, blocked='')

    # 안전장치 1: 장부 0건이면 아무것도 하지 않는다
    if not videos:
        log('  ⚠️  장부 videos 0건 — 고아 정리를 건너뜁니다 (장부 이상 의심)\n')
        ORPHAN_STATS['blocked'] = 'empty'
        return 0
    # 안전장치 2: 장부 행이 기존 파일의 절반도 안 되면 부분 로드로 간주
    if len(videos) < len(id_to_path) * 0.5:
        log(f'  ⚠️  장부 {len(videos)}건 < Vault {len(id_to_path)}건의 50% — 부분 로드 의심, 건너뜁니다\n')
        ORPHAN_STATS['blocked'] = 'partial'
        return 0

    live_ids = {v['record_id'] for v in videos}

    def is_video_note(fpath):
        """영상 노트만 격리 대상. schema.md 등 Vault 시스템 문서 오탐 방지."""
        relpath = os.path.relpath(fpath, VAULT)
        if os.path.dirname(relpath) == '':      # 영상 노트는 항상 토픽 폴더 안에 있다
            return False
        try:
            content = nfc(open(fpath, encoding='utf-8', errors='ignore').read())
        except Exception:
            return False
        url = fm_value(content, 'video_url')
        return bool(url and url not in ('', 'null'))

    orphans = [(nid, fp) for nid, fp in id_to_path.items()
               if nid not in live_ids and is_video_note(fp)]
    ORPHAN_STATS['candidates'] = len(orphans)

    if not orphans:
        log('  ✅ 고아 파일 없음\n')
        return 0

    # 안전장치 3: 고아 비율이 40%를 넘으면 정상 상황이 아니다
    ratio = len(orphans) / max(len(id_to_path), 1)
    if ratio > 0.4:
        log(f'  🚨 고아가 {len(orphans)}개({ratio:.0%})로 과다 — 안전을 위해 중단합니다. 수동 확인 필요\n')
        ORPHAN_STATS['blocked'] = 'ratio'
        return 0

    log(f'  대상: {len(orphans)}개 ({ratio:.1%})')
    if dry_run:
        for nid, fp in orphans[:20]:
            log(f'    [dry-run] {nfc(os.path.relpath(fp, VAULT))}')
        if len(orphans) > 20:
            log(f'    ... 외 {len(orphans) - 20}개')
        log('  ℹ️  dry-run 모드 — 실제 이동 없음\n')
        return 0

    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    moved = 0
    for nid, fpath in orphans:
        try:
            relpath = os.path.relpath(fpath, VAULT)
            dest = os.path.join(TRASH_DIR, stamp, relpath)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.move(fpath, dest)
            moved += 1
        except Exception as e:
            log(f'  ❌ 이동 실패 {os.path.basename(fpath)}: {e}')

    log(f'  ✅ {moved}개를 _trash/{stamp}/ 로 이동 (내용 보존)\n')
    return moved

# ── 메인 실행 ──
def main():
    DRY = '--dry-run' in sys.argv
    log(f'🚀 Obsidian 증분 동기화 시작 (원본: 장부 data/library.db{" · DRY-RUN — 아무것도 쓰지 않음" if DRY else ""})\n')
    start = time.time()

    # 장부 1회 로드 (tags 동기화·신규 추가·고아 격리·꿀팁에서 재사용). 못 읽으면 Vault 를 건드리지 않고 끝낸다.
    try:
        videos, tips = load_library()
    except Exception as e:
        log(f'❌ 장부 읽기 실패 — Vault 를 건드리지 않고 종료: {e}')
        print('RESULT_JSON:' + json.dumps({'added': 0, 'tips_added': 0, 'tags_updated': 0, 'orphans_removed': 0,
                                           'rebuilt': False, 'elapsed': round(time.time() - start),
                                           'error': f'library: {e}'[:200]}, ensure_ascii=False))
        sys.exit(1)
    log(f'📚 장부: 영상 {len(videos):,}개 · 꿀팁 {len(tips):,}개\n')

    # 기존 파일 tags 를 장부 topics 로 항상 동기화 (변경이 없으면 파일 쓰기 0건)
    tags_updated = sync_existing_tags(videos, dry_run=DRY)

    # 1.2단계 (v4.6-b): 재요약·등급 변경 노트 요약 절 제자리 교체 (해당 없으면 파일 읽기만)
    refreshed = refresh_changed_notes(videos, dry_run=DRY)

    # 1단계: 신규 파일 추가
    added, skipped = sync_new_pages(videos, dry_run=DRY)

    # 1.5단계: 장부에 없는 영상 노트 격리 (--orphans-dry-run: 대상만 출력)
    orphans_removed = quarantine_orphans(videos, dry_run=DRY or '--orphans-dry-run' in sys.argv)

    # 1.8단계 (v2.8): 장부 tips → AI 꿀팁/ 노트 (신규만). 고아 격리 이후에 실행해 격리 분모에 섞이지 않게 한다.
    tips_added, tips_orphans = (0, 0) if '--no-tips' in sys.argv else sync_tips(tips, dry_run=DRY)
    added += tips_added

    if DRY:
        log('ℹ️  dry-run — Wiki 재구성·인제스트·검색 인덱스·log.md 를 건너뜁니다')
        print('RESULT_JSON:' + json.dumps({
            'dry_run': True, 'videos': len(videos), 'tips': len(tips),
            'added': added, 'tips_added': tips_added, 'tags_updated': tags_updated,
            'refreshed': refreshed, 'refresh_skipped': REFRESH_STATS['skipped'],
            'orphans_candidates': ORPHAN_STATS['candidates'], 'orphans_blocked': ORPHAN_STATS['blocked'], 'skipped_same_path': skipped['same_path'], 'skipped_same_url': skipped['same_url'],
            'tips_orphans': tips_orphans, 'elapsed': round(time.time() - start),
        }, ensure_ascii=False))
        sys.exit(0)

    # 2단계: 신규/갱신이 있거나 강제 재구성 옵션일 때 Wiki 재구성
    force = '--rebuild' in sys.argv
    rebuilt = False
    rebuild_err = ''
    if added > 0 or tags_updated > 0 or orphans_removed > 0 or force:
        log('🔧 Wiki 재구성 중 (MOC + 키워드 링크)...')
        build_script = os.path.join(SCRIPT_DIR, 'build_obsidian_wiki.py')
        result = subprocess.run(
            [sys.executable, build_script],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            rebuild_err = result.stderr
            log(f'❌ Wiki 재구성 오류:\n{rebuild_err}')
        else:
            rebuilt = True
            log('✅ Wiki 재구성 완료!')
    else:
        log('ℹ️  신규 영상 없음 — Wiki 재구성 생략')

    # 3단계: Karpathy Wiki Ingest (신규 소스가 있을 때만)
    wiki_ingested = False
    wiki_err = ''
    if added > 0 or force:
        log('\n🧠 Karpathy Wiki Ingest 실행 중...')
        wiki_script = os.path.join(SCRIPT_DIR, 'wiki_ingest.py')
        if os.path.exists(wiki_script):
            wiki_result = subprocess.run(
                [sys.executable, wiki_script, '--no-backfill'],   # v4.5 backfill 은 launchd 17:30 실행만 (스케줄러 시간을 늘리지 않는다)
                capture_output=True, text=True
            )
            # ★ 캡처한 출력을 launchd 와 같은 로그에 흘려보낸다 (2026-09-10).
            #   안 그러면 이 경로의 실행이 ytsummarizer.log 에만 남아
            #   wiki-ingest.log 로는 안 보인다 — WIKI_RESULT 가 유일한 판정 지표인데
            #   그게 사라지면 "돌았는지 안 돌았는지" 자체를 알 수 없다.
            _tee_wiki_log(wiki_result.stdout, wiki_result.stderr)
            if wiki_result.returncode != 0:
                wiki_err = wiki_result.stderr[:200]
                log(f'❌ Wiki Ingest 오류:\n{wiki_err}')
            else:
                wiki_ingested = True
                log('✅ Wiki Ingest 완료!')
        else:
            log('ℹ️  wiki_ingest.py 없음 — 건너뜀')

    # 4단계: 검색 인덱스 증분 갱신 (신규/변경이 있을 때만. v4.6-b 재요약·등급 변경 포함 — exclude 는 인덱스에서 빠진다)
    if added > 0 or tags_updated > 0 or orphans_removed > 0 or refreshed > 0 or force:
        log('\n🔍 검색 인덱스 갱신 중...')
        idx_script = os.path.join(SCRIPT_DIR, 'build_search_index.py')
        if os.path.exists(idx_script):
            idx_result = subprocess.run([sys.executable, idx_script], capture_output=True, text=True)
            if idx_result.returncode != 0:
                log(f'❌ 검색 인덱스 갱신 오류:\n{idx_result.stderr[:200]}')
            else:
                log('✅ 검색 인덱스 갱신 완료!')

    elapsed = round(time.time() - start)
    log('\n🎉 Obsidian 동기화 완료!')

    # ── log.md 기록 ──
    if tags_updated > 0:
        write_wiki_log('tags-sync', f'기존 파일 tags {tags_updated}개 갱신', {
            '갱신 파일': f'{tags_updated}개',
            '소요시간': f'{elapsed}초',
        })
    if added > 0:
        write_wiki_log('ingest', f'신규 영상 {added - tips_added}개 · 꿀팁 {tips_added}개 추가', {
            '추가된 파일': f'{added}개 (영상 {added - tips_added} / 꿀팁 {tips_added})',
            'Wiki 재구성': '완료' if rebuilt else '생략',
            '소요시간': f'{elapsed}초',
        })
    if refreshed > 0:
        write_wiki_log('resummary', f'재요약·등급 변경 노트 {refreshed}개 맞춤', {
            '내용': '요약 절 제자리 교체(관련 항목 절 보존) · grade·summary_src 맞춤',
        })
    if orphans_removed > 0:
        write_wiki_log('cleanup', f'고아 파일 {orphans_removed}개 격리', {
            '격리 위치': '_trash/ (내용 보존)',
            '사유': '장부(data/library.db)에 없는 영상 노트',
        })
    if rebuilt:
        write_wiki_log('rebuild', 'MOC + 키워드 링크 재구성', {
            '처리': 'MOC 전체 재생성, 키워드 링크 삽입',
        })
    if rebuild_err:
        write_wiki_log('error', 'Wiki 재구성 실패', {'오류': rebuild_err[:200]})

    # 결과를 JSON으로 출력 (scheduler.js에서 파싱)
    print('RESULT_JSON:' + json.dumps({
        'added': added,
        'tips_added': tips_added,
        'tags_updated': tags_updated,
        'refreshed': refreshed,
        'refresh_skipped': REFRESH_STATS['skipped'],
        'orphans_removed': orphans_removed,
        'orphans_candidates': ORPHAN_STATS['candidates'],
        'orphans_blocked': ORPHAN_STATS['blocked'],
        'tips_orphans': tips_orphans,
        'skipped_same_path': skipped['same_path'],
        'skipped_same_url': skipped['same_url'],
        'rebuilt': rebuilt,
        'elapsed': elapsed,
        'error': rebuild_err,
    }))


if __name__ == '__main__':
    main()
