# v4.8 — 카톡 꿀팁 원문 제목 자동 조회

> 지시 번호는 발행할 때 채팅으로 준다(`[CC-1013-J]`). 보고는 한국어로.
> 선행: `60a4621`(원격 main 과 같음). 스케줄러는 내리지 않는다(4-0 의 시간 창만 피한다).
> 장부·스키마·`.env` 변경 없음. **데몬 재기동 없음**(`kakao_ingest.py`·`scheduler.js` 는 실행마다 새로 뜬다). 장부 쓰기 없음.

## 1. 배경

- `kakao_ingest.py` 는 링크를 열지 않고 URL 로 제목을 추정한다(`lib/kakao_parse.py:guess_meta`). 노션 공개 페이지는 슬러그에 한글이 없으면 「노션 자료 (…)」, 유튜브는 「유튜브 영상 (제목 미확인)」, 그 밖은 URL 마지막 조각(`claude and n8n`·`view`·`mobilebasic`)이 제목이 된다.
- 그래서 10-12(5건)·10-13(43건) 두 차례 `scripts/retitle_tips.py` 로 손으로 고쳤다. 2차 때 Cowork 가 쓴 조회 방법(노션 공개 페이지 API `syncRecordValuesMain` · og:title/`<title>`)이 44건 중 43건에서 통했다.
- 이번에는 그 조회를 인제스트 안에 넣어, 다음 카톡 내보내기부터는 원문 제목으로 들어오게 한다.

## 2. 설계 결정 (바꾸지 말 것)

| 항목 | 결정 |
|---|---|
| 조회 대상 | 신규 꿀팁 중 **제목이 URL 추정인 것만**(`guess_meta(...)['title_src'] == 'guess'`). 사용자가 메시지에 글을 붙였으면(`message`) 그 글이 제목이고, GitHub 레포(`github`)는 「레포 (GitHub 레포)」가 더 짧고 정확해서 조회하지 않는다 |
| 조회 방법 | `lib/title_fetch.py:lookup_title(url) -> (제목 또는 None, 사유)`. 노션(`*.notion.site`·`notion.so`·`app.notion.com`) = 공개 페이지 API `POST /api/v3/syncRecordValuesMain`(페이지 id 는 경로 마지막 조각의 **끝 32자리** — 「Opus-5-5-…」의 숫자에 속지 않는다, `?p=` 우선) · 유튜브 = oEmbed(YouTube Data API 할당량 무관) · 그 밖 = HTML 앞 512KB 의 og:title → twitter:title → `<title>` |
| 안전 | 요청당 timeout 8초 · **재시도 없음** · 예외를 던지지 않는다(HTTP 오류·시간 초과·DNS·파싱 실패 → `(None, 사유)`). 조회는 장부 트랜잭션 **전**에 끝난다. 실행당 60건 · 180초(`.env KAKAO_TITLE_MAX`·`KAKAO_TITLE_BUDGET`, 잘못된 값이면 기본값) — 넘는 링크는 추정 제목. 스케줄러의 카톡 훅 timeout(10분) 안 |
| 끄기 | `kakao_ingest.py --no-lookup` 또는 `.env KAKAO_TITLE_LOOKUP=false` — 예전 동작(링크를 열지 않음) |
| 실패 | 비공개 노션(`private`)·HTTP 오류(`http_<코드>`)·시간 초과·HTML 아님·제목 없음·로그인/차단/일반 문구(`bad_title`) → 예전 추정 제목 + 「원문 확인 필요」 메모 그대로. 나중에 `retitle_tips.py` 로 고친다 |
| 제목 정리 | NFC · 공백 정리 · 앞뒤 이모지·장식 기호 제거 · `|`(·`｜`) → ` — ` · `[[`·`]]` 제거(Obsidian 링크 별칭 보호 — `retitle_tips.py` 와 같은 금지) · 사이트 꼬리(` : 네이버 블로그`·` - YouTube`·` - Google Drive` 등) 제거 · 120자. 「Notion — Where teams…」·「Sign in」·「로그인」·「Just a moment...」 등은 버린다 |
| 성공 | 제목 교체 · 메모 비움 · 태그·카테고리를 제목 글자까지 보고 다시 정함 |
| 기록 | `RESULT_JSON.title_lookup = {need, ok, fail, skipped}`(dry-run·apply·쓰기 실패 모두). 로그 `🔎 제목 조회: 대상 N · 성공 N · 실패 N (사유 n) · N초`. `scheduler.js` 카톡 로그 끝에 ` · 제목 조회 성공/대상`(대상 있을 때만) |
| dry-run | 조회한다(읽기만) — 들어갈 제목을 미리 볼 수 있게. 장부·상태 파일은 그대로 쓰지 않는다 |
| 무변경 | 장부·스키마·중복 판정(`url_key`)·트랜잭션·`.kakao_state.json` 규칙·시트·`sync_obsidian`·이미 들어간 꿀팁 |

## 3. 파일 — 패치 1개

`docs/tasks/patches/2026-10-13-v48-kakao-title-lookup.patch` (기준 = `60a4621`, 9개 파일, +646 −36)

```
sha256  7c6865afb7dac241d724f026db19a68bf50310e274b107bb0cd1439d757f3f4f
```

| 파일 | 변경 |
|---|---|
| `lib/title_fetch.py` | 신규 — `lookup_title`·`clean_title`·`notion_page_id`·`notion_api_base`·`fetch_notion`·`fetch_youtube`·`fetch_html`·`title_from_html`. 표준 라이브러리만. `python3 lib/title_fetch.py <URL>…` 로 한 건씩 시험 |
| `kakao_ingest.py` | `lookup_settings()`·`resolve_titles()` 추가, 계획 표 만들기 전에 조회, `RESULT_JSON.title_lookup`, `--no-lookup`, 머리 주석 |
| `lib/kakao_parse.py` | `guess_meta(url, message, fetched_title=None)` + 반환값 `title_src`. 메모 문구는 그대로(`retitle_tips.py` `AUTO_MEMOS` 와 같아야 한다) |
| `scheduler.js` | `runKakaoIngest` 로그 한 줄에 제목 조회 건수 |
| `scripts/test_title_fetch.py` | 신규 43건 — 가짜 opener(네트워크 0) |
| `scripts/test_kakao_ingest.py` | +19건(37) — 조회 대상·교체·실패 무해·끄기·상한·잘못된 상한 값·실제 함수 + 막힌 네트워크. 맥 `.env` 값이 테스트를 바꾸지 않게 `load_env` 를 고정 |
| `CLAUDE.md` · `AGENTS.md` · `README.md` | 머리 버전 v4.8 · 명령 · 회귀 13종 · 파일 표 · 카톡 절(흐름·`.env`·「제목은 원문에서 조회」) · 이력 / README 안내 1줄 · 흐름도 · 구조 · `.env` 예시 · 명령 · 요약 행 · 상세 1절. AGENTS.md = 머리글 5줄 + CLAUDE.md 4행부터 |

### Cowork 사전 검증 (2026-10-13 20:00~20:20, 맥 네이티브 · 레포 무변경)

- 홈 임시 폴더에 `git archive 60a4621` + 코드 패치 → 회귀 테스트 13종: `test_title_fetch.py` 43/43 · `test_kakao_ingest.py` 37/37 · `test_verify_library.py` 16/16 · `test_retitle_tips.py` 49/49 · `test_wiki_ingest.py` 64/64 · `test_sync_obsidian.py` 32/32 · `test_sheet_mirror.py` 45/45 · `test_build_wiki_index.py` 15/15 · `test_backup_library.py` 50/50 · `test_scheduler_guards.js` 33/33 · `test_video_summary.js` 23/23 · `test_resummarize.js` 9/9 · `test_wiki_search.js` 34/34.
- 실제 조회(장부 읽기 전용): 장부 꿀팁 148건 전부 `lookup_title` → **143 성공** · 실패 5(비공개 노션 3 `private` · id 없는 노션 주소 1 `no_id` · JS 로 그리는 페이지 1 `no_title`) · 요청당 최대 3.4초 · 148건 78초. 2차 수동 확인 제목과 대부분 같은 문구(2차에서 괄호 설명을 덧붙인 7건은 원문 제목 그대로).
- 사본 장부 인제스트: 장부 사본에서 저장일 9-15 이후 44건을 지우고 같은 URL 로 만든 CSV 를 dry-run → apply. 조회 대상 42(GitHub 2 제외) · **성공 42** · 24초 · 신규 44 · 메모 남은 행 0 · 제목에 `|`·`[[`·`]]` 0 · 최장 52자.
- 노션 HTML 의 일반 제목(「Notion | Where teams and agents work together」)을 확인해 거부 목록에 넣었다(비공개 페이지의 HTML 대체 조회는 의미가 없어 하지 않는다).

## 4. 실행 — `[CC-1013-J]`

### 4-0. 시간

스케줄러가 00·06·12·18시, wiki-ingest 가 17:30 에 돈다. **매시 50분 ~ 다음 시 20분, 17:25~17:45 에는 4-2 이후를 시작하지 않는다.**
(이번 변경은 스케줄러가 카톡 단계를 돌 때만 쓰이고, 새 CSV 가 없으면 조회 자체가 없다 — 그래도 적용 중에 정시 실행이 겹치지 않게 한다.)

### 4-1. 시작 상태 (읽기만)

```bash
cd <REPO_ROOT>
git --no-optional-locks rev-parse --short HEAD          # 60a4621
git --no-optional-locks status --porcelain
#   기대: 아래 두 줄만
#   ?? docs/tasks/2026-10-13-v48-kakao-title-lookup.md
#   ?? docs/tasks/patches/2026-10-13-v48-kakao-title-lookup.patch
shasum -a 256 docs/tasks/patches/2026-10-13-v48-kakao-title-lookup.patch   # 3절 값과 같아야 한다
grep -o '"outcome": "[a-z]*"' .run_state.json                               # "ok" (running 이면 멈춤 — 스케줄러 실행 중)
```

어긋나면 **멈추고 보고**한다.

### 4-2. 패치 적용

```bash
git apply --check docs/tasks/patches/2026-10-13-v48-kakao-title-lookup.patch && git apply docs/tasks/patches/2026-10-13-v48-kakao-title-lookup.patch
git --no-optional-locks status --porcelain
#   기대: M AGENTS.md · M CLAUDE.md · M README.md · M kakao_ingest.py · M lib/kakao_parse.py · M scheduler.js
#        M scripts/test_kakao_ingest.py · ?? lib/title_fetch.py · ?? scripts/test_title_fetch.py · ?? 지시서 · ?? 패치
{ head -5 AGENTS.md; tail -n +4 CLAUDE.md; } | cmp - AGENTS.md && echo AGENTS_OK
node --check scheduler.js && /opt/homebrew/bin/python3 -m py_compile kakao_ingest.py lib/kakao_parse.py lib/title_fetch.py && echo SYNTAX_OK
```

### 4-3. 회귀 테스트 13종 (네트워크 0회, 실제 장부·Vault·.env 무관)

```bash
/opt/homebrew/bin/node scripts/test_scheduler_guards.js      # 33/33 PASS
/opt/homebrew/bin/node scripts/test_video_summary.js         # 23/23
/opt/homebrew/bin/node scripts/test_resummarize.js           # 9/9
/opt/homebrew/bin/node scripts/test_wiki_search.js           # 34/34
/opt/homebrew/bin/python3 scripts/test_title_fetch.py        # 43/43  (신규)
/opt/homebrew/bin/python3 scripts/test_kakao_ingest.py       # 37/37  (+19)
/opt/homebrew/bin/python3 scripts/test_verify_library.py     # 16/16
/opt/homebrew/bin/python3 scripts/test_retitle_tips.py       # 49/49
/opt/homebrew/bin/python3 scripts/test_wiki_ingest.py        # 64/64
/opt/homebrew/bin/python3 scripts/test_sync_obsidian.py      # 32/32
/opt/homebrew/bin/python3 scripts/test_sheet_mirror.py       # 45/45
/opt/homebrew/bin/python3 scripts/test_build_wiki_index.py   # 15/15
/opt/homebrew/bin/python3 scripts/test_backup_library.py     # 50/50
```

하나라도 FAIL 이면 멈추고 보고(7절 롤백). 테스트가 만든 `__pycache__/` 는 gitignore 라 status 에 나오지 않는다.

### 4-4. 실제 조회 확인 (읽기만 — 장부는 읽기 전용, 외부 사이트에 GET/POST 3회)

```bash
/opt/homebrew/bin/python3 - <<'EOF'
import sqlite3, sys
sys.path.insert(0, 'lib')
import title_fetch as tf
c = sqlite3.connect('file:data/library.db?mode=ro', uri=True)
pick = []
for cond in ("url like '%notion.site/%'", "url like '%youtube.com/%'", "url not like '%notion%' and url not like '%youtu%' and url not like '%github.com%'"):
    r = c.execute(f"select url from tips where {cond} order by saved_date desc limit 1").fetchone()
    if r: pick.append(r[0])
for u in pick:
    t, why = tf.lookup_title(u)
    print(why, '|', (t or '')[:60])
EOF
#   기대: 세 줄, 첫 칸이 모두 ok (제목은 보고만). ok 가 아니면 사유를 보고하고 멈추지 않는다 — 사이트 사정일 수 있다
/opt/homebrew/bin/python3 kakao_ingest.py --if-new | tail -1
#   기대: RESULT_JSON:{"skipped": "already_processed" …} 또는 {"skipped": "no_csv" …} — 새 CSV 가 없으면 조회도 쓰기도 없다
```

## 5. 커밋 (push 하지 않음)

```bash
git add AGENTS.md CLAUDE.md README.md kakao_ingest.py lib/kakao_parse.py lib/title_fetch.py scheduler.js \
        scripts/test_kakao_ingest.py scripts/test_title_fetch.py \
        docs/tasks/2026-10-13-v48-kakao-title-lookup.md docs/tasks/patches/2026-10-13-v48-kakao-title-lookup.patch
git commit -m "v4.8 카톡 꿀팁 원문 제목 자동 조회 — 노션 공개 API·유튜브 oEmbed·og:title (실패 시 추정 제목)"
git --no-optional-locks status --porcelain       # 커밋 뒤 기대: 빈 출력
git --no-optional-locks log --oneline -2
git --no-optional-locks show --stat HEAD | tail -14   # 11개 파일
```

**push 는 하지 않는다.** Cowork 가 커밋 diff 를 확인한 뒤 따로 지시한다.

## 6. 데몬

- 재기동 없음. `scheduler.js`·`kakao_ingest.py` 는 실행마다 새로 뜨므로 다음 정시 실행부터 새 코드다. 상주 데몬(`server`·`wiki-lan`)은 이 변경과 무관하다.

## 7. 롤백

- 급히 끄기(코드 그대로): `.env` 에 `KAKAO_TITLE_LOOKUP=false` 한 줄 — 다음 실행부터 링크를 열지 않는다.
- 커밋 전: `git apply -R docs/tasks/patches/2026-10-13-v48-kakao-title-lookup.patch` (새 파일 2개도 지워진다).
- 커밋 후: `git revert HEAD`(push 전이면 `git reset --hard 60a4621` 도 가능 — 지시서·패치는 다시 untracked 로 둔다).
- 이미 들어간 꿀팁 제목은 이 롤백으로 바뀌지 않는다(고칠 때는 `retitle_tips.py`).

## 8. 범위 밖

- `git push`.
- 이미 들어간 꿀팁 제목 다시 조회(1·2차 `retitle_tips.py` 로 끝남, 남은 1건은 비공개 노션).
- 카테고리 규칙 — 노션 주소의 `notion` 이 태그 `Notion` → 카테고리 「지식관리」로 잡히는 문제, 한글 「클로드」가 `Claude` 태그에 안 걸리는 문제(사전 검증에서 확인, 후속 후보).
- GitHub 레포 제목 조회(「레포 (GitHub 레포)」 유지).
- Cowork 스킬 `kakao-tips-update` 문구 갱신 — Cowork 몫.

## 9. 보고 형식 (한국어)

```
[CC-1013-J] 결과
- 4-1 시작 상태: HEAD / porcelain / 패치 sha256 일치 여부 / outcome
- 4-2 적용: status 요약 / AGENTS_OK / SYNTAX_OK
- 4-3 테스트: 13종 각 n/n
- 4-4 실제 조회: 세 줄 원문 / kakao_ingest --if-new 마지막 줄 원문
- 5 커밋: 해시, show --stat
- 특이사항(멈춘 단계·기대와 다른 출력 원문)
```
