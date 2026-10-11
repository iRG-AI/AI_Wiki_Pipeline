# v4.0 3단계 — 구글 시트 미러 + 노션 코드 정리 + 재구성 같은 내용 안 쓰기 (v4.0 완료)

> 지시 번호는 발행할 때 채팅으로 준다. **1부(4·5절) = `[CC-1012-B]`**, **2부(8절, 대표님 시트 설치 뒤) = `[CC-1012-C]`**. 보고는 한국어로.
> 선행: 2-b `114d3cb` 커밋 + Cowork 판정 통과(10-11 23:55). push 여부와는 무관하다.
> 스케줄러는 내리지 않는다(4-0 의 시간 창만 피한다).

## 1. 배경

v4.0 2단계로 파이프라인의 노션 호출은 0이 됐다. 남은 것:

- **보는 곳이 없다.** 방안 A 의 "보는 곳 = 구글 시트" 가 아직 없다. 장부(`data/library.db`)는 맥 안의 파일이라 폰·다른 기기에서 볼 수 없다.
- **앱이 노션 모듈을 아직 import 한다.** `kakao_ingest.py` 가 `.env` 를 읽으려고 노션 래퍼 `lib/tips_notion.py` 를 import 하고, `sync_obsidian.py` 에 노션 블록 → 마크다운 변환(`block_to_md`)이 남아 있다(은퇴한 `scripts/notion_to_sqlite.py` 가 쓰려고).
- `server.js` 의 `POST /api/sync-obsidian` 은 2-b 이후 부르는 화면이 없다.
- `build_search_index.py` 는 `notion_id` 를 파일 전체에서 찾는다(sync 는 2-b 에서 프론트매터 한정으로 바꿨다).
- **저장 0건 실행마다 Vault 전체 mtime 이 바뀐다**(2-b 판정 때 3,193개). `scheduler.js` → `sync_obsidian.py --rebuild` → `build_obsidian_wiki.py` 가 노트 본문 하단(🔗 관련 항목)을 비교 없이 다시 쓴다. 내용은 같다. 하루 최대 4회.
- README·CLAUDE·AGENTS 에 v3.x(노션) 설명이 남아 있다.

## 2. 설계 결정 (Cowork 확정 — 바꾸지 말 것)

| 항목 | 결정 |
|---|---|
| 시트 | 대표님 결정(10-12): **ai@irichgreen.com 의 새 스프레드시트**, 탭 **'영상'**(11열)·**'꿀팁'**(13열), **요약 전문 포함**, 장부 → 시트 **단방향**. 시트를 고쳐도 장부로 돌아가지 않는다. |
| 보내는 쪽 | `sheet_mirror.py`(레포 루트, Python). 받는 쪽 `gas/sheet_mirror.gs`(시트에 붙인 Apps Script 웹앱 — 실행 계정 "나", 액세스 "모든 사용자" + 토큰). YouTube OAuth 토큰은 건드리지 않는다(Sheets API 를 쓰면 같은 OAuth 를 다시 발급해야 해서 계정 불일치 사고 위험이 있다). |
| 갱신 시점 | 대표님 결정: **스케줄러 실행 끝마다 변경분만**. `scheduler.js:runSheetMirror()` 가 카톡 인제스트 뒤·Obsidian 동기화 앞에 부른다. **reject 하지 않는다**(카톡 훅과 같은 원칙). 실패는 텔레그램에 한 줄. |
| 변경분 판정 | handoff 의 "outbox 테이블" 대신 **`updated_at` 워터마크**(장부 `meta.sheet_wm_videos`·`sheet_wm_tips`). 장부를 쓰는 코드(`insertVideo`·`addTopic`·`updateStats`·`kakao_ingest`)는 모두 `updated_at` 을 새로 찍으므로 같은 효과이고 **스키마 무변경**(user_version 1 그대로). 워터마크는 그 탭 묶음을 **전부** 보낸 뒤에만 올린다. |
| 전체 다시 쓰기 | 첫 실행·`--full`·시트 주소 변경(`meta.sheet_target` = URL 해시) 때. 시작하면서 `sheet_target` 을 지우고 끝나야 다시 쓴다 → 중간에 끊기면 다음 실행도 전체. |
| 시트 쪽 쓰기 | 1열 `record_id` 기준 있으면 **제자리 덮어쓰기**, 없으면 아래에 추가. 머리글이 다르면 쓰지 않는다(`headers_mismatch` → `--full` 로만 복구). 탭 화이트리스트(영상·꿀팁). `= + - @` 로 시작하는 글자는 `'` 를 붙여 수식 방지(실데이터 238칸). 1열 글자 서식. 1,000행을 넘으면 행을 늘린다. |
| 안전 | HTTP 401/403/404·`auth`·`not_configured`·HTML 응답(로그인 화면 = 액세스 권한 오류) → **재시도 없이 즉시 중단 exit 2**. 429·5xx·네트워크·`busy` → 2·4·8초 지수 백오프, 4회 시도 후 exit 1. 토큰은 **본문으로만**(URL·로그에 없음). URL 은 `https://script.google.com/macros/s/` 만. 장부는 `meta` 의 `sheet_*` 키 말고 쓰지 않는다. |
| 설정 전 | `.env` 에 `SHEET_MIRROR_URL` 이 없으면 `skipped: not_configured`, exit 0. 그래서 1부를 커밋해도 스케줄러가 안전하다. `--dry-run` 은 URL 없이도 건수를 센다. |
| 노션 정리 범위 | 대표님 결정: **앱 코드만 정리, 키·적재 스크립트는 보관.** `kakao_ingest.py` → `lib/env_util.py`(신규, 같은 파싱 규칙). `block_to_md`·`rich_to_md` → `scripts/notion_to_sqlite.py` 안으로. `lib/tips_notion.py`·`notion_to_sqlite.py`·`.env` 의 `NOTION_*` 는 그대로 두고 머리 주석에 "보관 — 노션 해지 때 삭제". 앱은 노션 모듈을 import 하지 않는다. |
| `server.js` | `POST /api/sync-obsidian` 블록 삭제(호출 화면 없음). 다른 라우트 무변경. |
| 검색 인덱스 | `build_search_index.py:collect_notes()` 의 `notion_id`·`title`·`channel`·`tags`·`upload_date`·`view_count`·`video_url` 을 **맨 앞 프론트매터에서만** 읽는다(`sync_obsidian.FM_RE` 와 같은 정규식). 섹션 본문(영상 개요 등)은 그대로. 실 Vault 3,121 노트 — 옛 코드와 id·제목·태그·해시 전부 동일. |
| 같은 내용 안 쓰기 | `build_obsidian_wiki.py:write_if_changed()` — 파일 내용과 같으면 쓰지 않는다. MOC·허브·인덱스·lint·schema·노트 전부. 실행 끝에 `📝 파일 쓰기 — 바뀜 n개 / 내용 같아 건너뜀 m개`. |
| 잠복 결함 | 프론트매터 없는 파일은 `fm_end` 가 '🔗 관련 항목' 앞의 `---` 를 잡아 재구성마다 그 절이 한 벌씩 쌓였다 → 프론트매터가 없으면 `fm_end = 0`. 실 Vault 해당 파일 0개(지금 피해 없음). |
| 문서 | README v4.0(요약 행 + 상세 1절 + 머리·기능·아키텍처·구조·환경변수·설치·장부 구조 절 갱신). CLAUDE.md: 머리 버전·경로(`<REPO_ROOT>`), 명령, 파일 표, 카톡 절 다시 씀, 「구글 시트 미러」 절 신설, 노션 API 한계 절 삭제, 이력. **AGENTS.md = 머리글 3줄 + CLAUDE.md 4행부터**(같은 내용. 낡은 v2.5 프로젝트 지침 사본은 뺌). |

## 3. 파일 — 패치 1개

`docs/tasks/patches/2026-10-12-v4-sheet-mirror-cleanup.patch` (기준 = `114d3cb`)

```
sha256  ad574cfb837072b07dda447669732c5a4555de75c83d9adb8ab2e4ace6016611
```

| 파일 | 변경 |
|---|---|
| `sheet_mirror.py` · `gas/sheet_mirror.gs` · `lib/env_util.py` | 신규 (2절) |
| `scripts/test_sheet_mirror.py` · `scripts/fake_gas_server.js` | 신규 **45**건. 가짜 서버가 `gas/sheet_mirror.gs` 원본을 node `vm` 에 올리고 시트·302 리다이렉트를 흉내 낸다(127.0.0.1, 실제 구글 요청 0) |
| `scripts/test_build_wiki_index.py` | 신규 **10**건 (임시 Vault) |
| `scheduler.js` | `runSheetMirror()` + 호출 + 텔레그램 절 + export (테스트용) |
| `scripts/test_scheduler_guards.js` | +3건(훅이 reject 하지 않음) → **19** |
| `kakao_ingest.py` · `scripts/test_kakao_ingest.py` | `tips_notion` → `env_util`, 테스트 +1(노션 모듈 import 안 함) → **18** |
| `sync_obsidian.py` · `scripts/notion_to_sqlite.py` | `block_to_md`·`rich_to_md` 이동 |
| `server.js` · `wiki_lan_server.js` | `/api/sync-obsidian` 삭제 · 주석 1줄(wiki_lan_server 는 **주석만** — 재기동 불필요) |
| `build_search_index.py` · `build_obsidian_wiki.py` | 프론트매터 한정 · 같은 내용 안 쓰기 · `fm_end` · schema.md 의 파이프라인 문구(Notion → 장부) |
| `lib/library.js` · `lib/library_db.py` | 장부 없음 오류 문구("새로 만들지 말고 백업에서 복원") — 테스트는 `장부 파일 없음` 만 본다 |
| `lib/tips_notion.py` · `lib/kakao_parse.py` | 주석만 |
| `README.md` · `CLAUDE.md` · `AGENTS.md` | 2절 "문서" |

### Cowork 사전 검증 (2026-10-12 01:2x)

- 샌드박스(`114d3cb` 사본, node 22 · Python 3.13): `git apply --check` 통과, 테스트 19/19 · 37/37 · 18/18 · 23/23 · 45/45 · 10/10.
- 변이 시험: 수식 방지 제거 · 행 늘리기 제거 · 토큰 불일치 무시 · 전체 다시 쓰기 중 대상 표시 유지 · 워터마크 `>=` · 5xx 대기 없음 · 항상 쓰기 · `fm_end` 원복 · 인덱스 본문 검색 — 각각 FAIL 확인.
- **맥 네이티브**(`/tmp` 임시 사본, 데몬 node v26.10.0 · `/opt/homebrew/bin/python3` 3.14.8): 이 패치(sha 위) 적용 후 6종 전부 PASS.
- **실데이터(읽기만, 장부·Vault 는 `/tmp` 사본)**:
  - `sheet_mirror.py --dry-run` → 전체 · 영상 2,986 · 꿀팁 135. 행 만들기 예외 0, 최대 셀 3,253자, 요청 1회 최대 782KB, 영상 요청 15회.
  - `lib/env_util.load_env(.env)` == `tips_notion.load_env()` (키 21개, 값까지 동일 — 값은 출력하지 않음).
  - 검색 인덱스 `collect_notes`: 옛 3,121 = 새 3,121, 빠지는 id 0, 제목·태그·해시 다른 노트 0.
  - Vault 사본 재구성 2회: 1회차 바뀜 2 / 같음 3,190 → **2회차 바뀜 0 / 같음 3,192**. 프론트매터 없는 토픽 폴더 파일 0, 관련 항목 2벌 이상 0.
  - 새 코드 `sync_obsidian.py --dry-run`: videos 2,986 · tips 135 · added 0 · tags 0 · 고아 0.
- **확인 못 한 것**: 실제 Apps Script 웹앱(대표님 설치 뒤 2부에서). Workspace 관리 설정이 웹앱 액세스 "모든 사용자"를 막고 있으면 응답이 로그인 HTML → 미러가 `auth` 로 멈춘다(8절 멈춤 조건).

## 4. 1부 실행 — `[CC-1012-B]`

### 4-0. 시간

**피할 창**: 스케줄러 자동 실행(00·06·12·18시)의 **앞 5분 ~ 뒤 15분**, wiki-ingest **17:15~17:45**. 그 안에 걸리면 창이 끝난 뒤 시작한다(4-8 수동 실행 포함).

### 4-1. 시작 상태 (읽기만)

```bash
cd <REPO_ROOT>
git log -1 --format='%h %s'            # 114d3cb v4.0 2단계-b: …
git status --short                      # ?? 이 지시서 · ?? 이 패치 — 두 줄만
pgrep -fl 'scheduler\.js|sync_obsidian\.py|wiki_ingest\.py|kakao_ingest\.py|build_obsidian_wiki\.py' || echo "실행 중 없음"
shasum -a 256 docs/tasks/patches/2026-10-12-v4-sheet-mirror-cleanup.patch
git apply --check docs/tasks/patches/2026-10-12-v4-sheet-mirror-cleanup.patch && echo APPLY-OK
/opt/homebrew/bin/python3 scripts/notion_to_sqlite.py --verify > /tmp/v4c-verify0.log 2>&1; echo "exit=$?"; grep RESULT_JSON /tmp/v4c-verify0.log
/usr/bin/sqlite3 data/library.db "SELECT (SELECT COUNT(*) FROM videos), (SELECT COUNT(*) FROM tips)"
grep -c '^SHEET_MIRROR_' .env || true
```

멈춤 조건: HEAD 가 `114d3cb` 가 아님 · status 에 두 줄 말고 다른 것 · pgrep 출력 있음 · sha 불일치 · APPLY-OK 없음 · verify `ok` 가 true 아님.
적어 둘 값: **V** = videos 수, **T** = tips 수 (sqlite3 출력 `V|T`). 마지막 줄(`SHEET_MIRROR_` 개수)은 보통 0 — 1 이상이면 4-7 에서 새로 만들지 않는다.

### 4-2. 패치 적용

```bash
git apply docs/tasks/patches/2026-10-12-v4-sheet-mirror-cleanup.patch
git status --short
```

기대: `M` AGENTS.md · CLAUDE.md · README.md · build_obsidian_wiki.py · build_search_index.py · kakao_ingest.py · lib/kakao_parse.py · lib/library.js · lib/library_db.py · lib/tips_notion.py · scheduler.js · scripts/notion_to_sqlite.py · scripts/test_kakao_ingest.py · scripts/test_scheduler_guards.js · server.js · sync_obsidian.py · wiki_lan_server.js (17개),
`??` gas/ · lib/env_util.py · scripts/fake_gas_server.js · scripts/test_build_wiki_index.py · scripts/test_sheet_mirror.py · sheet_mirror.py · 지시서 · 패치.

### 4-3. 회귀 테스트 (네트워크 0회, 실제 장부·Vault·.env 무관)

```bash
/opt/homebrew/bin/node scripts/test_scheduler_guards.js | tail -1      # 19/19 PASS
/opt/homebrew/bin/python3 scripts/test_notion_to_sqlite.py | tail -1   # 37/37 PASS
/opt/homebrew/bin/python3 scripts/test_kakao_ingest.py | tail -1       # 18/18 PASS
/opt/homebrew/bin/python3 scripts/test_sync_obsidian.py | tail -1      # 23/23 PASS
/opt/homebrew/bin/python3 scripts/test_sheet_mirror.py | tail -1       # 45/45 PASS
/opt/homebrew/bin/python3 scripts/test_build_wiki_index.py | tail -1   # 10/10 PASS
grep -lE '^(import|from) tips_notion' *.py lib/*.py scripts/*.py       # scripts/notion_to_sqlite.py · scripts/test_notion_to_sqlite.py 두 줄만
grep -c 'sync-obsidian' server.js index.html                           # server.js:0 · index.html:0
grep -c 'def block_to_md' sync_obsidian.py scripts/notion_to_sqlite.py # sync_obsidian.py:0 · scripts/notion_to_sqlite.py:1
```

하나라도 다르면 멈추고 보고(7절 롤백).

### 4-4. 실데이터 dry-run (장부·Vault·네트워크 무변경)

```bash
/opt/homebrew/bin/python3 sync_obsidian.py --dry-run > /tmp/v4c-dry.log 2>&1; echo "exit=$?"; grep RESULT_JSON /tmp/v4c-dry.log
/opt/homebrew/bin/python3 sheet_mirror.py --dry-run; echo "exit=$?"
```

| 값 | 기대 |
|---|---|
| sync exit · `videos` · `tips` | 0 · **V** · **T** |
| sync `orphans_candidates` · `tips_orphans` | 0 · 0 |
| sync `added` · `tags_updated` | 0~20 · 0~30 (10-12 01시 실측 0 · 0. 06시 이후 신규 영상이 있었으면 그만큼) |
| mirror exit · `full` · `videos_sent` · `tips_sent` | 0 · true · **V** · **T** |

### 4-5. 재구성 — 같은 내용 안 쓰기 (실제 Vault, 2회)

```bash
VAULT="$HOME/Documents/Obsidian/AI LLM Wiki/AI LLM Wiki"
touch /tmp/v4c-mark1; sleep 1
/opt/homebrew/bin/python3 build_obsidian_wiki.py > /tmp/v4c-bow1.log 2>&1; echo "exit=$?"
grep '파일 쓰기' /tmp/v4c-bow1.log; find "$VAULT" -name '*.md' -newer /tmp/v4c-mark1 | wc -l
touch /tmp/v4c-mark2; sleep 1
/opt/homebrew/bin/python3 build_obsidian_wiki.py > /tmp/v4c-bow2.log 2>&1; echo "exit=$?"
grep '파일 쓰기' /tmp/v4c-bow2.log; find "$VAULT" -name '*.md' -newer /tmp/v4c-mark2 | wc -l
```

기대: 두 번 다 exit 0 · `바뀜` **5 이하** · `-newer` 개수 **6 이하**(시각이 박힌 `_MOC/lint.md`·`schema.md` + `log.md` 기록, 1회차는 schema.md 의 파이프라인 문구 변경 1개 더). 10-11 판정 때는 3,193 이었다.
**바뀜이 50 을 넘으면 멈추고 보고**(Vault 는 내용이 같은 재작성이라 되돌릴 것은 없다).

### 4-6. server 재기동 + 확인

```bash
launchctl kickstart -k gui/$(id -u)/com.irichgreen.server
sleep 3
curl -s -o /dev/null -w '/ %{http_code}\n' http://127.0.0.1:3000/
curl -s -X POST -o /dev/null -w 'sync-obsidian %{http_code}\n' http://127.0.0.1:3000/api/sync-obsidian -d '{}'
curl -s -o /dev/null -w 'wiki %{http_code}\n' http://127.0.0.1:3000/wiki
curl -s 'http://127.0.0.1:3000/api/wiki-search?q=claude' | /opt/homebrew/bin/python3 -c "import json,sys; d=json.load(sys.stdin); print('search', len(d.get('results', d if isinstance(d, list) else [])))"
```

기대: `/ 200` · `sync-obsidian 404` · `wiki 200` · `search` 1 이상. **`/api/master-ingest` 는 부르지 않는다**(스케줄러가 돈다).

### 4-7. 시트 토큰 만들기 (값은 출력하지 않는다)

```bash
git check-ignore -q .env && echo ENV-IGNORED
if grep -q '^SHEET_MIRROR_TOKEN=' .env; then
  echo "이미 있음 — 새로 만들지 않음"
else
  TOKEN=$(openssl rand -hex 24)
  printf '\n# v4.0 구글 시트 미러 (지시서 3) — Apps Script 스크립트 속성 MIRROR_TOKEN 과 같은 값\nSHEET_MIRROR_TOKEN=%s\n' "$TOKEN" >> .env
  unset TOKEN
fi
grep '^SHEET_MIRROR_TOKEN=' .env | cut -d= -f2- | tr -d '\n' | pbcopy
grep -c '^SHEET_MIRROR_TOKEN=' .env
pbpaste | wc -c | tr -d ' '
```

기대: `ENV-IGNORED` · `1` · `48`. **토큰 값·`.env` 내용을 보고에 붙이지 말 것.** 클립보드에 들어간 값은 대표님이 Apps Script 에 붙여 넣는다(9절).

### 4-8. 스케줄러 1회 수동 실행 (시트는 아직 미설정 → 건너뜀이 정상)

```bash
touch /tmp/v4c-mark3; sleep 1
nohup /opt/homebrew/bin/node scheduler.js > /tmp/v4c-run.log 2>&1 &
echo "pid=$!"
```

60초 간격으로 `pgrep -f 'node scheduler.js' || echo 끝남`, 최대 40분. 끝나면:

```bash
grep -E "장부 캐시 완료|장부 로드 실패|완료! 저장|카톡 인제스트|시트 미러|Obsidian 동기화|❌" /tmp/v4c-run.log
find "$HOME/Documents/Obsidian/AI LLM Wiki/AI LLM Wiki" -name '*.md' -newer /tmp/v4c-mark3 | wc -l
```

게이트: `장부 캐시 완료` · `오류: 0개` · **`ℹ️  시트 미러 건너뜀: not_configured`** · `✅ Obsidian 동기화 완료` · `❌` 없음(Gemini 429 로 인한 Wiki Ingest 오류는 예외 — 보고만) · `-newer` 개수 **50 이하**(저장 S 건이면 새 노트 S 개 + 재구성 몇 개 + Wiki 합성 몇 개).

## 5. 커밋 (push 하지 않음)

```bash
git add -A AGENTS.md CLAUDE.md README.md build_obsidian_wiki.py build_search_index.py kakao_ingest.py \
           lib/kakao_parse.py lib/library.js lib/library_db.py lib/tips_notion.py lib/env_util.py \
           scheduler.js server.js sync_obsidian.py wiki_lan_server.js sheet_mirror.py gas \
           scripts/notion_to_sqlite.py scripts/test_kakao_ingest.py scripts/test_scheduler_guards.js \
           scripts/test_sheet_mirror.py scripts/fake_gas_server.js scripts/test_build_wiki_index.py \
           docs/tasks/2026-10-12-v4-sheet-mirror-cleanup.md docs/tasks/patches/2026-10-12-v4-sheet-mirror-cleanup.patch
git status --short            # 남는 것 없음 (.env·data/ 는 ignore)
git commit -m "v4.0 3단계: 구글 시트 미러 + 앱 노션 코드 정리 + 재구성 같은 내용 안 쓰기 — v4.0 완료"
git show --stat HEAD | tail -3
```

push 는 Cowork 판정 뒤 별도 지시.

## 6. 데몬

| 데몬 | 조치 |
|---|---|
| `com.irichgreen.server` | 4-6 에서 재기동 (코드 바뀜) |
| `com.irichgreen.ytsummarizer` | 조치 없음 — 매 실행이 새 프로세스라 다음 실행부터 새 코드. 내리지 않는다 |
| `com.irichgreen.wiki-ingest` | 조치 없음 (`wiki_ingest.py` 무변경) |
| `com.irichgreen.wiki-lan` | 조치 없음 — `wiki_lan_server.js` 는 **주석만** 바뀜 |

## 7. 롤백

- 4-3 ~ 4-5 에서 멈춤: `git apply -R docs/tasks/patches/2026-10-12-v4-sheet-mirror-cleanup.patch` 후 남은 새 파일 확인(`git status --short` 에 지시서·패치만 남아야 함). 서버를 재기동했다면 `launchctl kickstart -k gui/$(id -u)/com.irichgreen.server`.
- 커밋 뒤: `git revert --no-edit HEAD` + 서버 재기동. `.env` 의 `SHEET_MIRROR_*` 줄은 남겨도 무해하다(옛 코드는 읽지 않는다).
- 장부: 이 패치는 장부에 `meta` 의 `sheet_*` 키 말고 쓰지 않는다(2부 이후). 지우려면 `DELETE FROM meta WHERE key LIKE 'sheet\_%' ESCAPE '\'`.
- Vault: 4-5·4-8 의 재작성은 내용이 같거나(관련 항목) schema.md 문구 1줄이라 되돌릴 것이 없다.

## 8. 2부 — 시트 연결 `[CC-1012-C]` (대표님이 9절을 끝내고 웹앱 URL 을 준 뒤)

URL 은 채팅 지시문 본문으로만 받는다(이 문서에 적지 않는다).

```bash
cd <REPO_ROOT>
git log -1 --format='%h %s'                 # 5절 커밋
grep -c '^SHEET_MIRROR_URL=' .env || true   # 0 이어야 함 (1 이면 값이 지시문과 같은지만 확인하고 추가하지 않음)
printf 'SHEET_MIRROR_URL=%s\n' '<지시문의 URL>' >> .env
/opt/homebrew/bin/python3 sheet_mirror.py --check; echo "exit=$?"
```

게이트 A(연결): exit **0**, `RESULT_JSON` 의 `error` 가 `""`, `sheet` 가 `{"영상": 0, "꿀팁": 0}`(빈 시트라 match false 가 정상).
**exit 2(auth) 면 즉시 멈추고 출력만 보고** — 재시도·다른 설정 시도 금지. 원인 후보는 토큰 붙여 넣기·배포 액세스 "모든 사용자"·URL 끝 `/exec`(9절).

```bash
/opt/homebrew/bin/python3 sheet_mirror.py --dry-run
/opt/homebrew/bin/python3 sheet_mirror.py > /tmp/v4c-mirror1.log 2>&1; echo "exit=$?"
grep -E "\] 추가|✅|❌|⏸|RESULT_JSON" /tmp/v4c-mirror1.log
/opt/homebrew/bin/python3 sheet_mirror.py --check; echo "exit=$?"
/opt/homebrew/bin/python3 sheet_mirror.py; echo "exit=$?"
/usr/bin/sqlite3 data/library.db "SELECT key FROM meta WHERE key LIKE 'sheet\_%' ESCAPE '\' ORDER BY key"
```

게이트 B:

| 값 | 기대 |
|---|---|
| 전체 전송 exit · `full` | 0 · true |
| `videos_sent` · `tips_sent` | = 장부 videos · tips 수 (4-1 의 V·T + 그 뒤 저장분) |
| 로그 | 영상 `[200/…]` … 15줄 + 꿀팁 1줄, `❌` 없음 (`⏸` 재시도는 있어도 됨 — 보고) |
| `--check` | exit 0 · `match: true` |
| 두 번째 실행 | exit 0 · `videos_sent 0` · `tips_sent 0` · `full false` |
| meta 키 | `sheet_last_ok` · `sheet_target` · `sheet_wm_tips` · `sheet_wm_videos` |

다음 스케줄러 실행부터 자동이다(조치 없음). 커밋할 것 없음(`.env` 는 ignore).

## 9. 대표님이 하는 것 (1부와 2부 사이, 약 5분)

1. Cowork 가 만든 시트(채팅 링크)를 연다 → **확장 프로그램 → Apps Script**.
2. 편집기의 `Code.gs` 내용을 지우고 레포 `gas/sheet_mirror.gs` 전체를 붙여 넣는다 → 저장.
3. 왼쪽 **⚙ 프로젝트 설정 → 스크립트 속성 → 속성 추가**: 이름 `MIRROR_TOKEN`, 값 = **클립보드**(4-7 이 넣어 둠, 48자) → 저장.
4. **배포 → 새 배포 → 유형 선택(⚙) 웹 앱** → 실행 계정 **나** · 액세스 권한 **모든 사용자** → 배포 → 권한 승인(시트 소유 계정) → **웹 앱 URL 복사**(`…/exec` 로 끝남) → Cowork 채팅에 붙여 넣기.
   - "모든 사용자"가 목록에 없으면 Workspace 관리 콘솔 설정 때문이다 — 그대로 Cowork 에 알려 주면 대안(개인 계정 시트)을 정한다.

## 10. 범위 밖

- `lib/tips_notion.py`·`scripts/notion_to_sqlite.py`·`.env` `NOTION_*` 삭제 — 「Notion 데이터 이관」이 끝나 노션을 해지할 때(대표님 결정 10-12).
- 장부 백업 자동화(장부는 이 맥에만 있는 원본이다) — 별도 후보.
- 시트 → 장부 역방향, 시트 서식·필터 보기 꾸미기, 썸네일 열.
- push(별도 지시), `_trash/` 정리, `kakao-tips-update` 스킬(Cowork).

## 11. 보고 형식 (한국어)

**1부 `[CC-1012-B]`**
1. 4-1 출력 (verify RESULT_JSON, V·T)
2. 4-3 마지막 줄 6개 + grep 3개
3. 4-4 출력 2개 + 게이트 표 대조
4. 4-5 `파일 쓰기` 줄 2개 + `-newer` 개수 2개
5. 4-6 출력
6. 4-7 출력 (`ENV-IGNORED` · 개수 · 48 — 값 없이)
7. 4-8 grep 결과 · `-newer` 개수 · 소요 시간
8. `git show --stat HEAD | tail -3`
9. 기대와 다른 점 — 없으면 "없음"

**2부 `[CC-1012-C]`**
1. 게이트 A 출력
2. 게이트 B 의 각 출력과 표 대조
3. 기대와 다른 점 — 없으면 "없음"
