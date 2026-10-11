# [CC-1011-D] v4.0 2단계-a — 쓰기 전환 (scheduler·kakao_ingest → 로컬 장부)

> 선행: [CC-1011-B] 커밋 `c1025dc` (1단계 — 노션 → SQLite 적재). 다음: 2-b `docs/tasks/2026-10-11-v4-sqlite-switch-b.md` (별도 지시).
> **이 지시서는 스케줄러를 멈추고 끝낸다. 2-b 가 끝날 때까지 다시 켜지 않는다.**
> 보고는 한국어로.

## 1. 배경

- 노션 탈퇴 결정(10-11) → v4.0 방안 A: 원본 = 맥 로컬 SQLite `data/library.db`, 읽는 곳 = Obsidian, 보는 곳 = 구글 시트(3단계).
- 2단계는 파이프라인에서 노션을 끊는다. 커밋 단위를 작게 하려고 둘로 나눴다.
  - **2-a (이 문서) — 쓰기**: `scheduler.js`(캐시·저장·주제 추가·조회수 갱신), `kakao_ingest.py`(꿀팁 생성)를 장부로.
  - 2-b — 읽기: `sync_obsidian.py` 를 장부로, `server.js`·`index.html` 노션 프록시 제거, 은퇴 스크립트 이동.
- 2-a 이후 노션은 낡는다. 2-a 와 2-b 사이에는 `sync_obsidian.py` 가 아직 노션을 읽으므로 새 영상·꿀팁 노트가 생기지 않는다. 그래서 그 사이 스케줄러를 멈춰 둔다.
- **코드를 패치 파일로 주는 이유**: 작업 트리를 미리 고쳐 두면 스케줄러(00·06·12·18시)가 반쯤 바뀐 코드로 돈다. 스케줄러를 멈춘 뒤 CC 가 적용한다.

## 2. 설계 결정 (Cowork 확정 — 바꾸지 말 것)

| 항목 | 결정 |
|---|---|
| 장부 열기 (Node) | 신규 `lib/library.js:openLibrary()`. **파일이 없으면 만들지 않고 던진다**(빈 장부 = 전 영상 신규 = 중복 저장, 10-05 사고와 같은 구조). `PRAGMA user_version` 이 `lib/library_schema.sql` 의 값과 다르면 던진다. |
| 장부 열기 (Python) | 신규 `lib/library_db.py:open_existing()` — 같은 규칙. `kakao_ingest.py`·(2-b) `sync_obsidian.py` 가 쓴다. |
| 캐시 | `scheduler.js:loadNotionCache()` → `loadLibraryCache(db)`. `videos` 전량을 읽어 **같은 형식의 Map**(키 = video_id·제목·정규화 제목, 값의 `pageId` = 장부 record_id). 0건이면 던진다(`LIBRARY_ALLOW_EMPTY=true` 일 때만 허용). `main` 은 실패 시 영상 처리·큐 재시도를 건너뛰고(fail-closed) **텔레그램으로 알린다**(신설). |
| 저장 | `saveToNotion`·`saveToNotionWithTopics` → `saveToLibrary(v, summary, topics)` 하나. record_id = uuid4, `summary_src='app'`, `status='완료'`, 시각 ISO UTC. 같은 video_id 가 이미 있으면 **UNIQUE 위반으로 던진다**(덮어쓰지 않음 → 오류 1건). |
| 주제 추가 | `addTopicToPage` → `addTopicToRecord` → `library.addTopic()`. 캐시 값이 아니라 **장부의 현재 topics 를 다시 읽어** NFC 합집합. |
| 조회수 갱신 | `updateStats` → `updateStatsInLibrary`. 업로드일을 안 주면 기존 값 유지. |
| 카톡 | `kakao_ingest.py` 는 장부 `tips` 의 `url_key` 로 중복 판정, 신규 행은 **한 트랜잭션**(전부 아니면 전무). 노션 호출 0. 노션 시절 기본값 유지(제목 비면 URL, 카테고리 기타, 상태 미확인, 중요도 중). 종료 코드 2(auth)는 없어진다. |
| WAL | **전환하지 않는다.** 접근이 scheduler → kakao_ingest → sync_obsidian 순차이고 쓰기는 짧은 단일 문장이다. 겹치면(launchd + 웹 버튼) Node `PRAGMA busy_timeout=5000`·Python `sqlite3` 기본 timeout 5초로 기다린다. 장부가 파일 1개로 유지되어 백업·미러가 단순하다. |
| 재적재 금지 | `scripts/notion_to_sqlite.py --mark-switched` 신설(meta `switched_at`). 이후 `--apply --replace` 는 거부. 표시가 없어도 `summary_src='app'` 행이나 적재 이후 생긴 꿀팁이 있으면 거부(노션 스냅샷이 앱이 쓴 행을 덮는 사고 방지). |
| `node:sqlite` | Node 22.13+ 에서 플래그 없이 된다. 첫 require 때 찍히는 `ExperimentalWarning` 한 줄만 `lib/library.js` 가 삼킨다(웹 마스터 인제스트가 stderr 를 ⚠️ 로 띄우기 때문). 데몬 node(`/opt/homebrew/bin/node`)와 셸 PATH node 둘 다 4-5 에서 테스트한다. |
| 문구 | 로그·텔레그램의 "Notion" → "장부". `server.js` 가 파싱하는 `완료! 저장: … / Skip: … / 오류: …` 줄은 그대로. |

## 3. 파일 — 패치 1개

`docs/tasks/patches/2026-10-11-v4-sqlite-switch-a.patch` (기준 커밋 `c1025dc`)

```
sha256  c3e3256c27f8e157bbec2896b10207d44d5d7a0e65cf54ea1c9cd83fcfbb86b3
```

| 파일 | 변경 |
|---|---|
| `lib/library.js` | 신규 — Node 장부 헬퍼 (openLibrary·allVideos·insertVideo·addTopic·updateStats·loadSqlite) |
| `scheduler.js` | 노션 호출부 전부 제거(`notionCall`·`cleanToken`·블록 생성·rich_text 분할) → 장부 함수. `main` 의 캐시 분기. 문구 |
| `kakao_ingest.py` | 노션 조회·생성 → 장부 `tips` 조회·한 트랜잭션 삽입 |
| `lib/library_db.py` | `open_existing()` 추가, WAL 결정 주석 |
| `scripts/notion_to_sqlite.py` | `--mark-switched`, `switched_reasons()` 재적재 거부, verify 에 `switched_at` |
| `scripts/test_scheduler_guards.js` | 노션 캐시 5건 → 장부 9건 (12 → **16**) |
| `scripts/test_notion_to_sqlite.py` | 전환 표시·거부 5건 추가 (32 → **37**) |
| `scripts/test_kakao_ingest.py` | 신규 **17**건 (장부 없음·dry-run·apply·멱등·트랜잭션·네트워크 0) |
| `CLAUDE.md`·`AGENTS.md` | v4.0 절 상태 줄, 캐시 제약 절(노션 → 장부), 파일 표, 명령 목록, 이력 1행 |

패치에 맥 이름·집 대역·개인 절대경로는 없다(Cowork grep 확인).

### Cowork 사전 검증 (2026-10-11 22:40, 리눅스 샌드박스 node v22.23 · python 3)

- `c1025dc` 의 추적 파일 사본에 `git apply --check` 통과 → 적용 → 테스트 16/16 · 37/37 · 17/17.
- 변이 시험 — 아래를 하나씩 되돌리면 해당 테스트가 FAIL 한다(테스트가 실제로 지킨다는 확인):
  파일 없음 검사 제거 · 0건 throw 제거 · topics NFC 제거 · 업로드일 무조건 덮어쓰기 · user_version 검사 제거 · 정규화 제목 키 제거 ·
  `open_existing` 존재 검사 제거 · 카톡 url_key 대조 제거 · 카톡 트랜잭션 제거.
- **맥 네이티브**(23:00, `/tmp` 임시 사본 — 레포 무변경): `git apply --check` 통과(실제 레포), 데몬 node v26.10.0 · 셸 PATH node · `/opt/homebrew/bin/python3` 로 16/16 · 16/16 · 37/37 · 17/17.
- 실데이터 사본(10-11 18:21 `library.db`): `loadLibraryCache` 2,986개 영상 → 캐시 키 8,949. `switched_reasons()` = [] (재적재 허용 상태).

## 4. 실행

### 4-0. 시간

- 4-3 이 노션을 읽는다 → **00·06·12·18시 앞뒤 15분은 피한다.** 17:15~17:45(wiki-ingest)도 피한다.
- 전체 20~50분(4-3 재적재 수 분, 4-7 스케줄러 수동 실행이 길다).

### 4-1. 시작 상태 (읽기만)

```bash
cd <REPO_ROOT>
git log -1 --format='%h %s'          # c1025dc v4.0 1단계: …
git status --short                    # ?? docs/tasks/2026-10-11-v4-sqlite-switch-a.md · -b.md · docs/tasks/patches/ 만
shasum -a 256 docs/tasks/patches/2026-10-11-v4-sqlite-switch-a.patch
git apply --check docs/tasks/patches/2026-10-11-v4-sqlite-switch-a.patch && echo APPLY-OK
/opt/homebrew/bin/node -e "const {DatabaseSync}=require('node:sqlite'); console.log(process.version, typeof DatabaseSync)"
node -e "const {DatabaseSync}=require('node:sqlite'); console.log(process.version, typeof DatabaseSync)"
launchctl list | grep -E 'com\.irichgreen\.'
pgrep -fl 'scheduler\.js|sync_obsidian\.py|wiki_ingest\.py|kakao_ingest\.py'
ls -la data/
```

멈춤 조건 — 하나라도 해당하면 **아무것도 바꾸지 말고** 보고:
- HEAD 가 `c1025dc` 가 아님 / `git status` 에 위 3개 외 변경이 있음
- sha256 불일치 / `APPLY-OK` 안 나옴
- 두 node 중 하나라도 `function` 이 안 나옴(`node:sqlite` 없음)
- `pgrep` 에 출력이 있음(스케줄러·동기화가 도는 중 — 끝난 뒤 다시)

### 4-2. 스케줄러 멈춤

```bash
launchctl unload ~/Library/LaunchAgents/com.irichgreen.ytsummarizer.plist
launchctl list | grep ytsummarizer || echo "ytsummarizer 내려감"
```

`server`·`wiki-ingest`·`wiki-lan` 데몬은 그대로 둔다(`server` 는 2-b 에서 재기동).
2-b 전까지 웹 화면의 「▶ 선택 실행」은 쓰지 않는다(옛 server.js 가 아직 노션에 쓴다). 「🆕 AI 영상목록 처리」는 새 scheduler.js 를 띄우므로 써도 된다.

### 4-3. 마지막 노션 재적재 (패치 전 코드 = c1025dc 그대로)

```bash
/opt/homebrew/bin/python3 scripts/notion_to_sqlite.py --apply --replace > /tmp/v4a-reload.log 2>&1; echo "exit=$?"
tail -25 /tmp/v4a-reload.log
/opt/homebrew/bin/python3 scripts/notion_to_sqlite.py --verify > /tmp/v4a-verify.log 2>&1; echo "exit=$?"
tail -14 /tmp/v4a-verify.log
```

게이트 (apply `RESULT_JSON`):

| 값 | 기대 |
|---|---|
| exit | 0 |
| `video_pages` | ≥ 3,189 |
| `videos` | ≥ 2,986, 그리고 `videos − 2,986 = video_pages − 3,189` (새 중복 없음) |
| `videos_dup` | = 203 |
| `tips` | ≥ 135 |
| `vault_missing` · `tips_missing` | 0 · 0 |
| `vault_ignored` | 1 (schema.md — 1단계와 같음) |
| `summary_check` | `match` = `checked` (기본 20) |
| `backup` | `library.db.bak.<시각>` |

게이트 (verify `RESULT_JSON`): `ok true` · `vault_in_dup 0` · `vault_missing 0`.
**"장부에만 있는 영상" = `videos − vault_in_videos`** 를 보고에 적는다(10-11 18:21 실측 1 — 2-b 첫 동기화가 노트를 만든다).

어긋나면 4-4 로 가지 말고 멈춘다. 스케줄러는 `launchctl load ~/Library/LaunchAgents/com.irichgreen.ytsummarizer.plist` 로 되살리고 보고한다(장부 재적재는 무해 — 노션이 아직 원본).

### 4-4. 패치 적용

```bash
git apply docs/tasks/patches/2026-10-11-v4-sqlite-switch-a.patch
git status --short
```

기대: `M` AGENTS.md · CLAUDE.md · kakao_ingest.py · lib/library_db.py · scheduler.js · scripts/notion_to_sqlite.py · scripts/test_notion_to_sqlite.py · scripts/test_scheduler_guards.js, `??` lib/library.js · scripts/test_kakao_ingest.py (+ 지시서·패치).

### 4-5. 회귀 테스트 (네트워크 0회)

```bash
/opt/homebrew/bin/node scripts/test_scheduler_guards.js | tail -1      # 16/16 PASS  (데몬 node)
node scripts/test_scheduler_guards.js | tail -1                        # 16/16 PASS  (셸 PATH node)
/opt/homebrew/bin/python3 scripts/test_notion_to_sqlite.py | tail -1   # 37/37 PASS
/opt/homebrew/bin/python3 scripts/test_kakao_ingest.py | tail -1       # 17/17 PASS
grep -c "api.notion.com" scheduler.js kakao_ingest.py                  # 0 / 0
git status --short scheduler.log                                       # 테스트가 로그를 안 건드림 (출력 없음)
```

하나라도 다르면 멈춘다(롤백 7-1).

### 4-6. 전환 표시 + 재적재 거부 실측

```bash
/opt/homebrew/bin/python3 scripts/notion_to_sqlite.py --mark-switched; echo "exit=$?"
ls data/ | grep -c '\.bak\.'                                            # 개수를 적어 둔다 (N)
/opt/homebrew/bin/python3 scripts/notion_to_sqlite.py --apply --replace > /tmp/v4a-refuse.log 2>&1; echo "exit=$?"
cat /tmp/v4a-refuse.log
ls data/ | grep -c '\.bak\.'                                            # 그대로 N
```

기대: `--mark-switched` exit 0 · `switched_at=` 출력. `--apply --replace` 는 **exit 1** · `거부` · `switched_at` 출력 · 노션 호출 없음(출력에 `노션 조회` 줄이 없어야 한다) · `.bak` 개수 그대로.

### 4-7. 스케줄러 1회 수동 실행 (장부 읽기·쓰기 실측)

실제 YouTube·Gemini 를 쓰는 정상 실행이다. 새 영상이 있으면 장부에 저장되고 재생목록 추가까지 한다. 뒤이어 카톡 훅과 (아직 옛) Obsidian 동기화가 돈다.

```bash
nohup /opt/homebrew/bin/node scheduler.js > /tmp/v4a-run.log 2>&1 &
echo "pid=$!"
```

60초 간격으로 `pgrep -f 'node scheduler.js' || echo 끝남` 과 `tail -3 /tmp/v4a-run.log` 를 본다. 최대 40분. 40분이 지나도 돌면 **죽이지 말고** 그때까지의 로그로 보고한다.

```bash
grep -E "장부 캐시 완료|장부 로드 실패|완료! 저장|카톡 인제스트|Obsidian 동기화|❌" /tmp/v4a-run.log
/opt/homebrew/bin/python3 - <<'PY'
import sqlite3
c = sqlite3.connect('file:data/library.db?mode=ro', uri=True)
q = lambda s: c.execute(s).fetchall()
print('videos', q('SELECT COUNT(*) FROM videos')[0][0], '· app', q("SELECT COUNT(*) FROM videos WHERE summary_src='app'")[0][0],
      '· tips', q('SELECT COUNT(*) FROM tips')[0][0], '· meta', dict(q('SELECT key, value FROM meta')))
for r in q("SELECT record_id, video_id, substr(title,1,30), topics, upload_date, length(summary) FROM videos WHERE summary_src='app' ORDER BY created_at"):
    print(' ', r)
PY
```

게이트:

| 확인 | 기대 |
|---|---|
| `✓ 장부 캐시 완료: N개 영상` | N = 4-3 의 `videos` |
| `장부 로드 실패` | 없음 |
| `완료! 저장: S개 / Skip: K개 / 오류: E개` | **E = 0** |
| 장부 `app` 행 수 | = S. 각 행 video_id 있음·summary 길이 > 0 |
| `videos` | = 4-3 `videos` + S |
| 카톡 줄 | `건너뜀: already_processed` 또는 `신규 n건` (n 이면 장부 tips 가 n 늘어남) |

- 이번 실행의 Obsidian 동기화는 **옛 코드(노션 읽기)** 다. 새로 저장된 S 편의 노트는 생기지 않는 게 정상이다(2-b 에서 생긴다).
- "저장 15 · Skip 0" 이면 캐시 이상이다 — 멈추고 보고.

### 4-8. 카톡 dry-run (장부 읽기)

```bash
/opt/homebrew/bin/python3 kakao_ingest.py > /tmp/v4a-kakao.log 2>&1; echo "exit=$?"
grep RESULT_JSON /tmp/v4a-kakao.log
```

기대: exit 0 · `candidates 0` · `db_total` = 장부 tips 수. (CSV 가 없으면 `skipped: no_csv` exit 1 — 보고만.) CSV 내용·표는 보고에 옮기지 않는다(개인 대화).

### 4-9. 무변경 확인

```bash
git check-ignore -q data/library.db && echo "data/ ignored"
git status --short
```

## 5. 커밋 (push 하지 않음)

```bash
git add kakao_ingest.py lib/library.js lib/library_db.py scheduler.js scripts/notion_to_sqlite.py \
        scripts/test_kakao_ingest.py scripts/test_notion_to_sqlite.py scripts/test_scheduler_guards.js \
        CLAUDE.md AGENTS.md docs/tasks/2026-10-11-v4-sqlite-switch-a.md docs/tasks/patches/2026-10-11-v4-sqlite-switch-a.patch
git status --short            # data/ 없음. 2-b 지시서·패치는 ?? 로 남는다 (2-b 에서 커밋)
git commit -m "v4.0 2단계-a: 쓰기 전환 — scheduler·kakao_ingest 가 노션 대신 로컬 장부(data/library.db)에 쓴다"
git show --stat HEAD
```

README 는 건드리지 않는다(v4.0 행은 지시서 3). push 는 Cowork 판정 뒤 별도 지시.

## 6. 데몬

| 데몬 | 조치 |
|---|---|
| `com.irichgreen.ytsummarizer` | **내린 채 둔다.** 2-b 끝에 다시 올린다 |
| `com.irichgreen.server` | 그대로 (2-b 에서 재기동) |
| `com.irichgreen.wiki-ingest` · `com.irichgreen.wiki-lan` | 그대로 |

## 7. 롤백

7-1. 커밋 전 (4-4 ~ 4-9 에서 멈춤):

```bash
git apply -R docs/tasks/patches/2026-10-11-v4-sqlite-switch-a.patch
rm -f lib/library.js scripts/test_kakao_ingest.py      # -R 로 지워지지 않았을 때만
launchctl load ~/Library/LaunchAgents/com.irichgreen.ytsummarizer.plist
```

7-2. 커밋 후: `git revert --no-edit HEAD` → 위 `launchctl load`.

- 장부(`library.db`)는 그대로 둬도 옛 코드가 읽지 않는다.
- 4-7 에서 장부에만 저장된 영상(S 편)은 노션에 없으므로 옛 스케줄러가 다음 실행에 다시 요약·저장한다(Gemini 호출 S 회 추가, 데이터 손실 없음).

## 8. 범위 밖

- `sync_obsidian.py`·`server.js`·`index.html`·은퇴 스크립트 이동 — 2-b.
- 노션 코드·`.env` 노션 키·`lib/tips_notion.py` 제거, README·CLAUDE 전면 갱신, 구글 시트 미러 — 지시서 3.
- 노션 쓰기·삭제(노션의 중복 페이지 포함). `.env` 수정. push.
- `kakao-tips-update` 스킬 갱신 — 2-b 판정 뒤 Cowork.

## 9. 보고 형식 (한국어)

1. 4-1 출력 전문(두 node 버전 포함)
2. 4-3 apply·verify `RESULT_JSON` 전문 + "장부에만 있는 영상" 수
3. 4-5 마지막 줄 4개 + grep 결과
4. 4-6 출력 전문, `.bak` 개수 전후
5. 4-7 grep 결과 + 장부 조회 출력, 소요 시간
6. 4-8 `RESULT_JSON`
7. `git show --stat HEAD`
8. 기대와 다른 점 — 없으면 "없음"
