---
paths:
  - "**/*.py"
  - "**/*.js"
  - "**/*.sh"
  - "**/*.plist"
  - "lib/**"
  - "scripts/**"
  - "gas/**"
  - "playlists.json"
---

# 아키텍처 상세 — 핵심 파일 역할 · 기능별 구조 (루트 CLAUDE.md 에서 이관 — 2026-11-11)

> 위 경로의 파일을 Read 하면 자동으로 읽힌다. 코드·plist·장부를 건드리기 전에는 직접 Read 해도 된다. 루트 CLAUDE.md 와 어긋나면 **루트가 우선**한다. 아래는 옮기기 전 본문이다(글자 그대로).

### 핵심 파일 역할

→ README 「📁 파일 구조 및 역할」 이 파일 안내의 정본 · 아래는 경고·임계값·가드가 있는 행만 (경위: [배경 §핵심 파일 역할](docs/claude_md_background.md#bg-files))

| 파일 | 역할 |
|------|------|
| `lib/classifier.js` | Gemini 기반 토픽 분류기. `playlists.json`의 토픽 목록만 허용(allowedSet 필터). 신뢰도 0.6 미만이면 YouTube 추가 건너뜀. (v4.14) 모델 기본 `gemini-3.5-flash-lite` — `.env CLASSIFY_MODEL`(`resolveModel`)로 바꾸고 `opts.model` 로 호출마다도. thinking 은 `thinkingConfigFor`(2.x 예산 0 · 3.x minimal). 결과에 `model`. 테스트 `scripts/test_classifier.js`. |
| `lib/youtube_oauth.js` | YouTube OAuth2 쓰기 전용. access_token 메모리 캐시(50분), 일일 quota 추적(`.quota_state.json`), 호출 간 200ms rate limit. |
| `scripts/migrate_library.py` | (v4.5·v4.6) 장부 스키마 이전(user_version 1·2 → 3). 기본 dry-run, `--apply` 는 온라인 백업 `<장부>.bak.v<현재>-<시각>` 뒤 한 트랜잭션으로 단계별 `ALTER TABLE ADD COLUMN`(`ADD_COLUMNS`) + 스키마 실행(전부 `IF NOT EXISTS`) → 버전·무결성·행 수·새 표·새 열 확인. 열 추가는 `updated_at` 을 안 건드린다(시트 재전송 없음). `--db=` 로 복원본에도. |
| `build_obsidian_wiki.py` | 키워드별 허브 파일 27개 자동 생성(`_MOC/Claude.md` 등) + MOC 재구성. (v4.0) `write_if_changed()` — 내용이 같은 파일은 쓰지 않는다. |
| `telegram_tips_ingest.py` · `scripts/test_tips_bot.py` | (v4.18) 꿀팁 두 번째 입구 — 전용 봇 `getUpdates`(timeout 0, offset = 장부 `meta.tips_bot_offset`+1) → 허용 chat(`.env TIPS_BOT_CHAT_ID`)만 → `kakao_parse.links_from_messages` → `kakao_ingest` 공용 함수 → 한 트랜잭션(tips + meta offset·last_ok) → 커밋 뒤 메시지별 답장(저장·이미 있음·링크 없음). 401·403·404·409·400 즉시 중단(exit 2), 429 `retry_after`, 5xx·네트워크 2·4초 백오프 3회(exit 1). 토큰은 URL 경로에 들어가므로 URL·토큰·chat id 를 출력하지 않는다. 기본 dry-run, `--apply`·`--whoami`. 테스트는 가짜 urlopen. |
| `lib/kakao_parse.py` | (v3.0) URL 추출·트래킹 파라미터 제거·중복 키·규칙 기반 제목/카테고리 추정. 순수 함수, 네트워크 없음. (v4.8) `guess_meta(…, fetched_title)` · `title_src`(`message`·`github`·`guess`·`fetched`). (v4.9) 분류 규칙은 `classify(url, *texts)` 한 곳 — 노션 페이지 주소는 호스트를 빼고 판정, 한글 표기 별칭. |
| `lib/title_fetch.py` · `scripts/test_title_fetch.py` | (v4.8) 링크 원문 제목 조회 — 노션 공개 API(`syncRecordValuesMain`) · 유튜브 oEmbed · og:title/`<title>`. 요청당 8초·재시도 없음, 예외를 던지지 않고 `(None, 사유)`. 제목 정리(앞뒤 이모지·`|` → ` — `·`[[`·`]]` 제거·120자·로그인/일반 문구 거부). 테스트는 가짜 응답(네트워크 0). |
| `gas/sheet_mirror.gs` | (v4.0 3단계) 시트에 붙이는 Apps Script 웹앱(받는 쪽). 토큰 검사 · 탭 화이트리스트(영상·꿀팁) · 머리글 대조 · 수식 방지. 설치 순서는 파일 머리 주석. |
| `lib/wiki_search.js` | 검색 코어(의존성 0). `wiki_index.json`+`wiki_index.vec`(768차원) 로드, 임베딩 코사인 + 메타 부스트, 임베딩 실패 시 키워드 폴백, Gemini 401/403 래치. (v4.7) `listPayload`(전체 목록, gzip·ETag 캐시) · `scoreAll`(모든 노트 점수) · `similar`(저장 벡터끼리, Gemini 호출 없음) · `noteById`(id 로만, `readNote` 경로 검사). `WIKI_SEARCH_DIR`·`WIKI_VAULT` 는 테스트 전용. |
| `build_search_index.py` | Obsidian 노트 → `gemini-embedding-001` → 인덱스 증분 빌드. `sync_obsidian.py`가 신규·변경·고아 격리·`--rebuild` 시 호출. (v4.0) `notion_id`·제목·태그는 맨 앞 프론트매터에서만 읽는다. (v4.7) 화면 필터용 `kind`·`subscriber_count`·`summary_src`·`link_url`·`category`·`importance`·`keywords` — 매 빌드 프론트매터에서 다시 읽고 임베딩 hash 와 무관. |
| `scripts/recategorize_tips.py` · `scripts/test_recategorize_tips.py` | (v4.9) 기존 꿀팁 분류 보정. 카테고리·태그가 「v4.8 규칙이 매긴 값」(URL+제목 또는 URL 만)과 같은 행만 `kakao_parse.classify` 로 다시 매기고(사람이 고른 값은 그대로), 출처가 `http(s)://` 로 시작하면 호스트만(URL 호스트와 다르면 보고만). 장부 `category`·`tags`·`source`·`updated_at` + 「AI 꿀팁」 노트의 해당 줄만 제자리 수정(손으로 고친 노트는 행째 건너뜀) → `build_obsidian_wiki`·`build_search_index`. 기본 dry-run, 쓰기 전 `data/recategorize_backup/<시각>/`. 장부 조건은 `record_id` + 옛 세 값, 다시 돌리면 0건. 종료 0 · 1 · 2(무변경). (v4.10) 카테고리 「기타」 + 태그 없음은 빈 기본값으로 보고 같이 다시 매긴다 — `RESULT_JSON.blank_default`·로그 「(빈 기본값)」. |
| `scripts/retitle_tips.py` · `scripts/test_retitle_tips.py` | (v4.4) 꿀팁 제목 보완. CSV(`record_id,old_title,new_title`) → 장부 `title`·`updated_at`(+ 카톡 자동 메모 비움) · 「AI 꿀팁」 노트 제자리 수정·파일명 변경 · Vault `[[링크]]` 치환 → `build_obsidian_wiki`·`build_search_index`. 기본 dry-run, 검증 전부 통과 뒤에만 쓰고 쓰기 전 `data/retitle_backup/<시각>/` 에 장부·파일 백업. 장부 조건은 `record_id` + 옛 제목(같은 CSV 재실행은 멈춤). 종료 0 · 1 · 2(무변경). |
| `lib/library_schema.sql` · `lib/library_db.py` | (v4.0) 로컬 원본 장부 스키마(원본은 `.sql` 하나) · Python 헬퍼(`open_existing()` = 있는 장부만 연다, 없으면 만들지 않고 던진다). |

### Wiki 검색 — 입구는 여럿, 엔진은 하나 (v3.2)

| 입구 | 프로세스 | 바인딩 | 용도 |
|---|---|---|---|
| `http://localhost:3000/wiki` | `server.js` | `127.0.0.1:3000` | 이 맥에서 직접 |
| `http://<맥이름>.local:3100/wiki` | `wiki_lan_server.js` | `0.0.0.0:3100` + 대역 필터 | 집 안 다른 컴퓨터(가족) |
| MCP `wiki-search` | `wiki_mcp.js` (stdio) | 없음 | Claude Code 대화 중 |

- **`server.js`를 `0.0.0.0`으로 열지 말 것.** `/api/master-ingest`(스케줄러 실행)·`/api/config`(키 노출)가 같이 열린다. (노션 쓰기 프록시·`/api/sync-obsidian` 은 v4.0 에서 제거) 집 안 공유는 `wiki_lan_server.js`가 전담한다.
- **`wiki_lan_server.js`에 쓰기·실행 엔드포인트를 추가하지 말 것.** 라우트는 `/`, `/wiki`, `/favicon.svg`, `/api/wiki-topics`, `/api/wiki-search`, `/api/wiki-ask`, (v4.7) `/api/wiki-note` 뿐이다.
- `.env`의 `WIKI_LAN_ALLOW_CIDR`(사설 대역 `/16`~`/32`, 쉼표로 여러 개)가 없거나 틀리면 **`127.0.0.1` 전용으로 떨어진다(fail-closed).** 가족이 "갑자기 안 된다"고 하면 `wiki-lan.log`의 `바인딩:` 줄부터 본다.
- 클라이언트 IP는 **소켓 주소만** 본다. `X-Forwarded-For`를 읽는 코드를 넣지 말 것(위조 가능).
- AI 답변은 scheduler·wiki-ingest와 **같은 Gemini 무료 키**를 쓴다. IP당 분당 5회 + 전체 24시간 `WIKI_LAN_ASK_DAILY_MAX`회(기본 20, 메모리 카운터 — 재기동하면 0). 한도를 올리면 영상 요약·Wiki 합성이 429를 맞는다. 일반 검색은 임베딩 모델을 쓰므로 별개이고, 한도에 걸리면 키워드 검색으로 대체된다.
- (v4.7) 화면은 `/api/wiki-search?all=1`(전체 목록, gzip·ETag)을 한 번 받아 필터·정렬을 브라우저에서 한다. 검색어는 `?scores=1&q=`(모든 노트 점수 — 의미 검색이면 화면이 상위 200건을 관련 결과로 본다), 비슷한 영상은 `?similar=<id>`(저장 벡터끼리, Gemini 호출 없음), 노트 전체 보기는 `/api/wiki-note?id=`(경로를 받지 않고 id 로만 — `readNote` 가 Vault 밖을 막는다). 기존 `?q=&limit=` 응답은 그대로(AI 답변 503 대체 경로가 쓴다). **`/api/wiki-note` 에 경로(path) 인자를 받게 바꾸지 말 것.**
- (v4.7) 화면은 iRichGreen Design System 웹 계층 DS 1.1.23 을 따른다 — 색·크기는 `wiki.html` 머리의 CSS 변수만(밝은 테마만, DS 에 다크 테마가 없다). 엑셀은 브라우저가 .xlsx 를 직접 만든다(외부 라이브러리 없음, 파일명 `ai-llm-wiki-YYYYMMDD.xlsx`, 시트 「목록」·「조건」). 「새로 들어온 것」은 그 브라우저 localStorage(`wiki.seen`·`wiki.new`)에만 기억한다.
- (v4.7) 인덱스에 화면 필터용 메타가 붙은 뒤에야 종류·요약 방식·꿀팁 분류 필터가 맞게 센다 — 적용 직후 `build_search_index.py` 한 번(임베딩 호출 0).
- 화면의 「Obsidian에서 열기」는 `location.hostname`이 `localhost`/`127.0.0.1`일 때만 나온다(`wiki.html:IS_LOCAL`). 가족 PC에는 Vault가 없다.
- **맥북이 집에 켜져 있을 때만 된다.** 덮개를 닫아 잠들거나 들고 나가면 가족은 접속할 수 없다. IPv6로는 열지 않는다(대역 검사가 IPv4 전제).
- `<맥이름>`은 `scutil --get LocalHostName`이다. macOS가 이름 충돌 시 끝 숫자를 올려 바꾸는 일이 있다 — 주소가 안 먹으면 이름부터 확인한다. 기동 로그의 `가족 접속:` 줄도 같은 값(`scutil --get LocalHostName`)을 찍는다. `os.hostname()`은 쓰지 않는다 — 2026-10-03 실측에서 `.local`로 풀리지 않는 이름을 줬다.

### 카카오톡 → 장부 tips → Obsidian (v3.0 → v4.0)

- **(v4.18) 두 번째 입구 — 텔레그램 전용 봇.** 인스타 등에서 휴대폰 공유 → 전용 봇 방(실행 알림 봇과 별개). 같은 `tips` 표·같은 엔진이고 카톡 CSV 경로는 안전망으로 그대로 둔다(중복은 `url_key` 대조). `scheduler.js:runTipsBot` 이 카톡 훅 다음 · 시트 미러 앞에서 `telegram_tips_ingest.py --apply` 를 부른다(reject 없음). `.env`: `TIPS_BOT_TOKEN` · `TIPS_BOT_CHAT_ID`(허용할 개인 대화 하나 — 그 밖 발신자는 건수만 세고 버림). 토큰이 없으면 `skipped=not_configured` 로 요청 없이 끝난다. 상태는 장부 `meta` 의 `tips_bot_offset`·`tips_bot_last_ok` — tips INSERT 와 같은 트랜잭션이라 커밋 뒤에만 offset 이 오른다(새 상태 파일 없음). 답장은 커밋 뒤에 보내고 실패해도 적재를 되돌리지 않는다. 입구가 막히면(`auth`·`conflict`·`bad_request`) 또는 마지막 정상 수신이 18시간을 넘으면 알림 봇이 `⚠️ [텔레그램 꿀팁 입구]` 를 따로 보낸다. **webhook 을 걸거나 같은 봇을 다른 곳에서 읽으면 `getUpdates` 가 409(conflict)로 막힌다.** 이 입구도 `kakao_ingest.py:plan_rows` → `guess_meta` 를 쓰므로 분류 규칙은 카톡과 같다(v4.19: 메시지 글은 URL 을 뺀 글만 판정에 쓴다).

```
카톡 '나와의 채팅' 내보내기 (수동, 월 1회) → ~/Downloads/KakaoTalk_Chat_*.csv
  → scheduler.js (YouTube 인제스트 완료 후) → kakao_ingest.py --apply --if-new
       [최신 CSV mtime 비교(.kakao_state.json) → URL 정규화 → 장부 tips 전량 url_key 대조 → (v4.8) URL 추정 제목만 원문 제목 조회 → 신규만 한 트랜잭션 INSERT → RESULT_JSON]
  → 장부 data/library.db 의 tips 테이블
  → sheet_mirror.py → 구글 시트 '꿀팁' 탭 (보기용)
  → sync_obsidian.py:sync_tips()  [VAULT/AI 꿀팁/*.md, 신규만]
  → wiki_ingest.py / build_obsidian_wiki.py  (기존 그대로 공유 — 합성 로직 두 벌 만들지 않는다)
```

- `.env`: `KAKAO_EXPORT_DIR`(읽기는 `lib/env_util.py`). 노션을 부르지 않는다(v4.8 제목 조회의 노션 공개 페이지 API 는 계정·토큰 없는 읽기다). (선택, v4.8) `KAKAO_TITLE_LOOKUP`(없으면 켜짐, `false` 면 끔) · `KAKAO_TITLE_MAX`(실행당 조회 상한, 기본 60) · `KAKAO_TITLE_BUDGET`(조회 전체 시간 상한초, 기본 180).
- 꿀팁 기본값(노션 시절과 같음): 제목이 비면 URL, 카테고리 `기타`, 상태 `미확인`, 중요도 `중`. 카테고리 값 목록은 `lib/kakao_parse.py` 상단. `tags` 는 JSON 배열, `source` 는 **호스트만**(`github.com`). (v4.9) 노션 이관 시절 행의 `https://…` 출처는 `recategorize_tips.py` 로 호스트만 남겼다 — 「채널별 목차」가 출처로 묶는다.
- **(v4.9) 카테고리·태그는 `lib/kakao_parse.classify` 한 곳에서 매긴다.** 판정 글자 = URL + 사용자가 붙인 글(메시지에서 URL 을 뺀 글 — v4.19) + 조회한 원문 제목(URL 추정 제목은 넣지 않는다 — 「노션 자료」의 「노션」이 태그가 되지 않게). 노션 페이지 주소(`notion.site`·`notion.so`·`app.notion.com`)는 **호스트를 빼고** 판정한다 — 노션에 올린 자료일 뿐 노션 이야기가 아니다(v4.8 까지 노션 주소 꿀팁이 모두 `Notion` → 「지식관리」였다). `notion.com`(노션 회사 사이트)은 그대로 `Notion`. 한글 표기 별칭: 클로드(코드)·제미나이/제미니·지피티/오픈AI·노션·옵시디언·안티그래비티·올라마·허깅페이스. 「커서」는 일반 명사라 넣지 않는다. **태그 이름·순서·카테고리 값 목록은 바꾸지 않는다**(장부·노트 `keywords`·검색 필터가 쓴다). 사람이 고른 분류(노션 시절 행 · 9-03~9-06 정리분)는 규칙으로 덮지 않는다 — `recategorize_tips.py` 는 v4.8 규칙 값과 같은 행만 고친다. **(v4.10) 단 카테고리 「기타」 + 태그 없음은 사람이 고른 값이 아니라 빈 기본값**(노션 이관 때 기본값 그대로 — 08-14·09-03·09-06 의 19건이 그랬다)으로 보고 다시 매긴다. 태그가 하나라도 있거나 「기타」가 아니면 지금처럼 보존.
- `kakao_ingest.py`의 `--since` 기본값은 `2026-03-01`. 그 이전 카톡 링크 103건은 쇼핑·개인 링크라 AI 자료가 아니다.
- **꿀팁 노트는 YouTube 로직과 격리된다.** `get_existing_vault_info()`가 `AI 꿀팁/` 폴더를 걷지 않으므로 고아 격리 분모·tags 동기화에 섞이지 않는다. 노트 프론트매터는 `link_url`이며 **`video_url`을 절대 쓰지 않는다** — 쓰는 순간 고아 격리 대상이 된다. `tags` 키도 쓰지 않는다(`keywords`) — `build_obsidian_wiki`가 tags 없는 파일을 폴더명 MOC(`_MOC/AI 꿀팁 MOC.md`)로 묶는다.
- 폴더는 **평면 구조**다. `wiki_ingest`·`build_obsidian_wiki`가 최상위 폴더 바로 아래 파일만 읽으므로 카테고리 하위 폴더를 만들면 위키에서 사라진다. 카테고리는 프론트매터 `category`로만 둔다.
- 같은 날 같은 추정 제목이 여럿이면 파일명이 충돌한다. 충돌 시 **id 끝 6자리**를 붙인다(앞자리는 워크스페이스 공통 접두라 구분 불가).
- 꿀팁 노트는 본문이 거의 없다(제목·링크·태그·메모). `wiki_ingest`가 그대로 먹지만 추출 품질은 낮다. URL 본문을 긁어 Gemini로 요약하는 2차 확장은 미구현(선택).
- **실행은 `/opt/homebrew/bin/python3`**(스케줄러·wiki-ingest 데몬과 같은 인터프리터).
- `.kakao_state.json`은 "이 CSV는 이미 봤다"는 **스킵 최적화일 뿐 중복 방지 장치가 아니다.** 중복 방지는 언제나 장부 대조다. `--apply`가 실패 없이 끝났을 때만 기록하고 dry-run·`--limit`은 기록하지 않는다.
- `scheduler.js`의 카톡 훅(`runKakaoIngest`)은 **절대 reject하지 않는다.** 카톡 단계가 Obsidian 동기화를 막으면 안 된다. (지시서 `docs/tasks/2026-09-06-scheduler-kakao-hook.md`)
- 꿀팁이 신규 추가되면 `sync_obsidian.py`가 **제한 없이** `wiki_ingest.py`를 띄운다(기존 동작). 처음 대량 적재할 때는 `wiki_ingest.py --limit=20`으로 나눠 돌릴 것. 2026-09-06 첫 적재 시 99건이 한꺼번에 들어가 수동 중단했다.
- 수동 즉시 반영은 Cowork 스킬 `kakao-tips-update`(장부판).
- **(v4.8) 제목은 원문에서 조회하고, 실패하면 추정이다.** 사용자가 메시지에 글을 붙이지 않았고 GitHub 레포가 아닌 링크(`title_src == 'guess'`)만 `lib/title_fetch.py` 로 원문 제목을 조회한다 — 노션 공개 페이지는 `syncRecordValuesMain`, 유튜브는 oEmbed(YouTube Data API 할당량 무관), 그 밖은 og:title/`<title>`. 성공하면 제목을 바꾸고 메모를 비우며 태그·카테고리도 제목 글자까지 보고 정한다. 실패(비공개 노션 `private`·HTTP 오류·로그인/일반 문구 `bad_title` 등)면 예전처럼 URL 추정 제목(「유튜브 영상 (제목 미확인)」·「노션 자료 (…)」·URL 마지막 조각, 메모 「원문 확인 필요」)이 들어간다. 조회는 장부 쓰기 **전**에 끝나고 예외를 던지지 않는다 — 조회 실패가 인제스트를 막으면 안 된다. 사전 검증(10-13): 실제 꿀팁 148건 143 성공(비공개 노션 3·id 없는 노션 1·JS 화면 1 실패), 요청당 최대 3.4초. 이미 들어간 꿀팁 제목을 고칠 때는 장부를 직접 UPDATE 하지 말고 `scripts/retitle_tips.py` 를 쓴다 — `sync_tips` 는 기존 노트를 다시 쓰지 않으므로 장부만 고치면 노트·파일명·링크가 옛 제목으로 남는다. 새 제목에 `|`·`[[`·`]]` 금지(Obsidian 링크 별칭을 깨뜨림, 스크립트가 거부).

### 구글 시트 미러 (v4.0 3단계) — 보기 전용, 장부 → 시트 단방향

```
scheduler.js (카톡 인제스트 뒤, Obsidian 동기화 앞) → runSheetMirror() → sheet_mirror.py
   [장부 meta.sheet_wm_videos·sheet_wm_tips 이후 updated_at 인 행 → 200행씩 POST(JSON, 토큰은 본문)]
   → Apps Script 웹앱 gas/sheet_mirror.gs (실행 계정 = 시트 소유자, 액세스 = 모든 사용자 + 토큰)
   → 시트 탭 '영상'(11열) · '꿀팁'(13열). 1열 record_id 기준 있으면 제자리 덮어쓰기, 없으면 아래에 추가
```

- **원본은 장부다.** 시트를 고쳐도 장부로 돌아가지 않고 다음 변경 때 덮어써진다. 시트 쪽에 열을 추가하지 말 것 — 머리글이 다르면 웹앱이 쓰기를 거부(`headers_mismatch`)하고, 미러는 `--full` 로만 복구된다.
- `.env`: `SHEET_MIRROR_URL`(웹앱 `/exec` 주소, `https://script.google.com/macros/s/` 만 허용) · `SHEET_MIRROR_TOKEN`(Apps Script 스크립트 속성 `MIRROR_TOKEN` 과 같은 값). **URL 이 없으면 아무것도 하지 않고 `skipped`** — 설치 전에도 스케줄러가 안전하다.
- **변경분 = `updated_at` 워터마크.** 별도 outbox 테이블을 두지 않았다(스키마 무변경). 그래서 **장부를 고치는 코드는 반드시 `updated_at` 을 새로 찍어야 한다** — `lib/library.js` 의 `insertVideo`·`addTopic`·`updateStats`, `kakao_ingest.py` 가 그렇게 한다. 손으로 고쳤다면 `--full`.
- 워터마크는 그 탭의 묶음을 **전부** 보낸 뒤에만 올린다. 중간 실패분은 다음 실행이 다시 보낸다(덮어쓰기라 무해). 전체 다시 쓰기(`--full`·첫 실행·주소 변경)는 시작할 때 `meta.sheet_target` 을 지우고 끝나야 다시 쓴다 — 끊기면 다음 실행도 전체.
- **안전(1순위 원칙 그대로):** HTTP 401/403·404·토큰 불일치(`auth`)·스크립트 속성 없음(`not_configured`)·HTML 응답(로그인 화면 = 웹앱 액세스가 "모든 사용자"가 아님)은 **재시도 없이 즉시 중단(exit 2)**. 429·5xx·네트워크 오류·`busy` 만 2·4·8초 지수 백오프, 4회 시도 후 중단(exit 1). 웹앱은 HTTP 상태를 고를 수 없어 오류도 200 + `{ok:false, error}` 로 온다.
- Apps Script 웹앱은 POST 에 302 를 주고 결과는 리다이렉트 주소(GET)에 있다. urllib 의 기본 동작(302 → GET, 본문 재전송 없음)이 정확히 그것이다. 리다이렉트 처리를 바꾸지 말 것.
- `= + - @` 로 시작하는 글자는 웹앱이 앞에 `'` 를 붙여 수식이 되지 않게 한다(10-12 실데이터 238칸). 1열은 글자 서식(`@`).
- 스케줄러 훅 `runSheetMirror` 는 **절대 reject 하지 않는다**(카톡 훅과 같은 원칙). 실패하면 텔레그램 메시지에 `📗 구글 시트 미러 ⚠️ 실패` 한 줄이 붙는다(`auth` 면 토큰·배포 확인).
- 웹앱 코드를 고치면 Apps Script 에서 **배포 관리 → 새 버전**으로 같은 URL 을 유지한다(새 배포를 만들면 URL 이 바뀌어 다음 실행이 전체 다시 쓰기).

### 장부 백업 (v4.1) — 하루 1회, 로컬 + 구글 드라이브

```
scheduler.js (시트 미러 뒤, Obsidian 동기화 앞) → runLibraryBackup() → backup_library.py
   [오늘(KST) library-YYYYMMDD.db.gz 가 없는 폴더만 → SQLite 온라인 백업(장부 mode=ro) → integrity_check·user_version·videos≥1
    → gzip → 압축 해제 sha256 대조 → .tmp 로 쓰고 이름 바꾸기 → 그 폴더에서만 보관 규칙]
   → <REPO_ROOT>/data/backups/ (gitignore) + .env LIBRARY_BACKUP_DIR (구글 드라이브 데스크톱 앱 폴더)
```

- **장부에 쓰지 않는다.** 읽기 전용 연결로 백업 API 만 쓴다. `meta` 에도 기록하지 않는다 — 하루 1회 판단은 오늘 날짜 파일이 그 폴더에 있느냐로만 한다(상태 파일 없음).
- 백업을 `cp` 로 만들지 말 것 — journal_mode=DELETE 라 쓰는 도중의 장부가 찍힐 수 있다. 온라인 백업 API(`Connection.backup`, `sqlite3 .backup`)만 쓴다.
- 사본 검사(`integrity_check`·`user_version`·`videos ≥ 1`)에 걸리면 아무것도 만들지 않고 **기존 백업도 지우지 않는다.** 이 검사를 빼지 말 것 — 망가진 장부가 좋은 백업을 밀어낸다.
- 보관: 최신 7개 + 일별이 대표하지 않는 옛 ISO 주마다 가장 최근 1개(보통 일요일)씩 4주 = 최대 11개(약 45MB). 정리는 **그 실행에 새로 쓴 폴더에서만**, 이름이 정확히 `library-YYYYMMDD.db.gz` 인 파일만 대상이다(`NAME_RE`). 정규식을 넓히지 말 것.
- `LIBRARY_BACKUP_DIR` 의 **부모 폴더가 없으면 만들지 않는다**(`drive: unavailable`, exit 1). 드라이브 앱이 꺼져 `~/Library/CloudStorage/...` 가 사라졌을 때 로컬 디스크에 같은 경로를 만들면 백업된 줄 착각한다. 마지막 폴더 하나만 만든다.
- 드라이브 쪽에서 지운 파일은 구글 드라이브 휴지통(30일)으로 간다.
- 스케줄러 훅 `runLibraryBackup` 은 **reject 하지 않고 네트워크를 쓰지 않는다**. 실패하면 main 이 `⚠️ [장부 백업 실패]` 텔레그램을 따로 보낸다(저장 0건 실행에도). 드라이브가 빠진 날은 실행마다(최대 4회) 알린다 — 의도.
- 복원 절차는 README 「장부 백업」. 복원 후에는 그 날짜 이후 영상이 장부에 없으므로 `sync_obsidian.py --orphans-dry-run` 부터 보고, 시트는 `sheet_mirror.py --full`.
- 타임머신(외장 디스크)은 이 백업과 별개다 — 디스크가 연결돼 있을 때만 돈다.

### 실행 실패 알림 (v4.2) — 그 자리에서 + 다음 실행이

```
main 시작  → .run_state.json 읽기 → runNotices(직전 기록, 지금)
             [직전이 running 이고 3시간↑ = 끝을 기록하지 못한 실행 · 직전이 fail 이고 notified=false = 못 보낸 실패 · 간격 9시간↑ = 빠진 정시 실행]
           → 이번 실행 시작 기록(outcome=running, pending=점검 문구) → 있으면 [직전 실행 점검] 텔레그램 → 보냈으면 pending 비움
"완료!" 뒤 → 저장 0 · Skip 0 · 오류 ≥1 이면 [실행 실패] 텔레그램(장부 로드 실패는 이미 알렸으므로 다시 보내지 않음) → outcome=fail/ok 기록
main().catch → outcome=fail 먼저 기록 → [실행 실패] 텔레그램 → 보냈으면 notified=true
```

- **네트워크가 죽은 실행은 그 자리에서 알림도 못 보낸다.** 그래서 `notified` 를 `sendTelegram` 의 실제 결과(true/false)로 남기고, 다음 실행이 다시 알린다. `sendTelegram` 은 reject 하지 않고 성공 여부만 돌려준다 — JSON 이 아닌 응답에도 죽지 않고, 20초에 끊는다.
- 판정은 `isWholeRunFailure`·`runNotices`(순수 함수, `scheduler.js`)가 한다. 기준 상수 `RUN_STALE_H = 3`(이보다 짧은 running 은 겹친 실행일 수 있어 알리지 않음)·`RUN_GAP_ALERT_H = 9`(정시 6시간 + 지연 3시간)·`RUN_PENDING_MAX = 10`.
- 상태 파일 기록이 실패해도 실행은 계속한다(로그만). `.run_state.json*` 는 gitignore. 지워도 무해하다 — 다음 실행이 "처음"으로 시작한다.
- Gemini 401/403 경로의 `process.exit(1)`(자체 텔레그램을 보냄)은 상태를 running 으로 남긴다 → 다음 실행이 "끝을 기록하지 못했습니다" 를 한 번 더 알린다(의도 — 멈춘 실행은 두 번 알려도 된다).
- 겹친 실행(수동 실행이 정시 실행과 겹침)은 나중에 끝난 쪽 기록이 남는다. 그 정도의 부정확은 받아들인다.
- `.env`·`lib/youtube_oauth` 로드 실패로 마스터 인제스트를 통째로 건너뛰면 "저장 0 · Skip 0 · 오류 0" 이라 이 판정에 걸리지 않는다(빈 재생목록과 구분 불가). 범위 밖.

### Wiki 합성 결과 누적 (v4.5) — 장부 `wiki_extract` 가 원본, 페이지는 그림

```
소스(노트) ─Gemini─▶ wiki_extract (record_id = notion_id, status ok | seed | failed, attempts)
                         │  매 실행 끝: 표 전체 × 현재 Vault(record_id → 파일명·제목) 로 렌더
                         ▼
             _wiki/entities/*.md · _wiki/concepts/*.md · _wiki/index.md   (내용 같으면 안 씀)
```

- **v4.4 까지의 결함:** `update_concept_page`·`update_entity_page`·`build_wiki_index` 가 그 실행분만으로 파일 전체를 다시 써서, 페이지마다 그 페이지를 마지막으로 건드린 실행분(1~10건)만 남았다(05-12 도입 때부터). 추출 결과를 어디에도 저장하지 않아 되살릴 원본이 없었다. **페이지를 실행분으로 다시 쓰는 코드로 되돌리지 말 것.**
- 페이지는 파생물이다. 손으로 고치면 다음 실행에 덮인다. 고칠 것은 `wiki_extract` 또는 노트다. `--render-only` 로 Gemini 없이 다시 그린다.
- 렌더는 결정적이다 — `last_updated`·index 「마지막 갱신」은 실행 시각이 아니라 기여한 행의 `updated_at` 최댓값(KST). 그래서 할 일 없는 실행은 파일을 하나도 쓰지 않는다.
- Vault 에서 빠진 소스(고아·격리)는 페이지에서 저절로 빠진다(장부 행은 남김). retitle 로 바뀐 파일명·제목도 저절로 따라간다. 항목이 0이 된 이름의 기존 페이지는 지우지 않는다 — (v4.6-b) 이름이 `ENTITIES`·`CONCEPTS` 목록 안이면 안내 문구 페이지(`source_count: 0`, 시각 없음 — 결정적)로 다시 그리고 index 에서 뺀다. 목록 밖 파일은 건드리지 않는다.
- **응답을 못 읽으면(깨진 JSON) 실패다.** v4.4 까지는 빈 결과로 성공 처리해 그 소스가 조용히 빠졌다. 지금은 `failed` 행 attempts+1, ingested 에 안 넣어 다음 실행이 다시 시도, **3회(`MAX_FAILS`)에서 포기**(ingested 표시). 정상 JSON 의 빈 결과는 `ok`.
- **backfill:** (v4.6-b) **노트 프론트매터 `summary_src: video`(실제 영상 요약)인 소스만** — 설명란만 보고 지어낸 옛 요약으로 Wiki 를 채우지 않는다. 재요약이 `wiki_extract` 를 `stale` 로 돌려 두면 다시 추출된다(`stale` 행은 그때까지 페이지에 그대로). `.wiki_state.json` ingested 에 있지만 `wiki_extract` 가 없거나 ok 가 아닌(seed·failed·stale) 소스를 `WIKI_BACKFILL_BATCH`(기본 20)개씩 한 호출로 추출. 하루(태평양시) `WIKI_BACKFILL_DAILY_MAX`(기본 30, 0 = 끔)회 상한(두 설정 모두 프로세스 환경변수가 `.env` 보다 먼저 — 시험 1회는 `WIKI_BACKFILL_DAILY_MAX=1 python3 wiki_ingest.py`) — 사용량은 `.wiki_state.json` 의 `backfill: {date, calls}`. **영상 요약과 같은 무료 키를 쓰므로 상한을 올리면 요약이 429 를 맞는다.** 실패한 호출도 1회로 센다.
- backfill 은 launchd 17:30 실행(인자 없음)에서만 돈다. `sync_obsidian` 경로는 `--no-backfill` — 스케줄러 실행 시간을 늘리지 않는다. `--full`·`--limit` 도 backfill 하지 않는다.
- 씨앗(`--seed-from-pages`)은 v4.5 적용 때 1회 — 옛 페이지에 남아 있던 항목(약 80건)을 `seed` 로 옮겨 backfill 이 끝나기 전에도 페이지가 비지 않게 한다. `ok` 행은 덮지 않는다. backfill 이 seed 를 batch 결과로 바꾼다.
- `.wiki_state.json` 의 `entities`·`concepts` 는 이제 전체 카운트다(예전엔 마지막 실행분).
- 판정: `WIKI_RESULT` 에 `failed`·`entities`·`concepts`(전체 이름 수)·`backfill_calls`·`backfill_done`·`backfill_left` 가 더해졌다. `backfill_left` 가 0 이 되면 끝. `null` 은 그 실행에서 backfill 을 안 돌렸다는 뜻이다.

### 실제 영상 요약·품질 필터 (v4.6-a) — 신규 영상부터

```
videos.list(statistics,snippet,contentDetails,status — 1유닛 그대로) → 길이(초)·공개 상태
   │ public · 길이 있음 · 하루 분량 남음 ─▶ Gemini 2.5 Flash 에 YouTube URL 을 영상으로(LOW, 30분 넘으면 endOffset 1800s)
   │                                        └ JSON {summary_md, signals{promo_main, promo_share, promo_subject, generic, ai_related, has_demo, sponsored, reason}}
   │                                        └ 등급 = 코드 규칙 → 장부 summary_src 'video' · grade keep|exclude · quality(JSON)
   └ 그 밖·실패 ─▶ 기존 설명란 요약(geminiSummarize) → summary_src 'app' · grade NULL(미판정)
```

- 모듈은 `lib/video_summary.js`, 호출 자리는 `scheduler.js:processMasterIngest` 하나(레거시 재생목록 순회 경로는 설명란 요약 그대로).
- **등급은 모델이 아니라 코드가 매긴다** — `computeGrade`: `promo_main`(제작자 **자신의** 강의·컨설팅·커뮤니티·상품 판매가 주목적) · `generic`(구체 정보 없는 일반론) · `!ai_related` AND 토픽 분류 0개 중 하나라도면 `exclude`. 유료 광고·협찬(`sponsored`)·시연(`has_demo`)은 기록만 하고 등급에 안 쓴다. 모델에게 A/B/C 를 매기게 했더니 판매 영상에도 A 를 줬다(10-12 시험) — 모델 등급으로 되돌리지 말 것. `promo_main` 정의를 넓히지 말 것 — "판매·홍보가 주목적"으로 두면 다른 회사 도구를 시연하는 협찬 영상까지 제외됐다(10-13 시험). (v4.12) 판매 제외는 `promo_main AND (promo_share ≥ PROMO_SHARE_MIN(0.5) OR promo_subject)` — 두 모델 모두 영상 끝에 자기 상품을 잠깐 알리면 promo_main 을 true 로 낸다(오판 3건). promo_main 이 false 면 비중·본론과 상관없이 제외하지 않는다(이 AND 를 OR 로 바꾸지 말 것 — 정의 넓히기). 비중은 같은 영상도 회차마다 0.05 ↔ 0.32 로 흔들려 안전망으로만 쓰고, 광고성 본문(자기 상품의 고객 사례·소개)은 `promo_subject` 가 잡는다. 판매 구간 시각(spans)은 영상 길이를 넘는 값이 나와 쓰지 않는다(10-14 시험). promo_main 이 true 인데 제외 안 되면 로그 `(promo_minor 0.03)`. (v4.17) `!ai_related` 만으로는 제외하지 않는다 — `computeGrade(signals, topics)` 가 토픽 배열이 비었거나 없을 때만 `not_ai` 를 사유로 삼고, 토픽이 있으면 `not_ai_minor` 로 알린다(신호 5건 중 진짜 비 AI 1건, 토픽 분류는 5/5). 신규 영상은 `🎬 … → exclude [not_ai]` 가 요약 시점의 임시 값이고 분류 뒤 `regrade` 로 다시 매겨 최종 등급은 `🎚 등급(토픽 반영)`·`✓ 장부 저장 완료 … · keep` 줄로 본다. 재요약은 장부 `topics` 를 쓴다. 분야형 토픽(「AI 여행계획」 등)이 비 AI 영상에 붙으면 keep 이 되므로 `not_ai_minor` 로 관찰한다. 이 조건을 OR 로 되돌리거나 토픽 없이 not_ai 를 끄지 말 것.
- **영상 토큰 0 이면 실패다.** 삭제된 영상은 200 + 영상 토큰 0 + 지어낸 답을 돌려준다(10-13 시험). `parseResponse` 의 이 검사를 빼지 말 것.
- 공개(`public`)가 아닌 영상은 영상 입력을 시도하지 않는다(일부공개 = 403 PERMISSION_DENIED). 영상 입력 403 은 영상 단위라 그 영상만 대체하고, **연속 2회면 그 실행에서 영상 입력을 끈다**(403 난사 방지). 대체 요약(같은 키)도 403 이면 `geminiSummarize` 의 기존 즉시 종료 경로를 탄다.
- 429·5xx·네트워크 오류는 키를 돌려 재시도(키 4개 × 2회 상한) 후 대체. 400 등 그 밖의 오류는 재시도 없이 대체.
- 무료 등급 영상 입력은 하루 8시간 분량 상한(미리보기 기능). `.video_quota.json` `{date(PT), seconds, calls, models, keys, legacy}` 에 시도한 영상의 (앞 30분 기준) 초를 센다 — 실패 요청도 센다. (v4.13) 판단은 **모델별(`models`)·키별(`keys`, sha256 앞 8자리 — 키 원문을 쓰지 않는다) 누계 둘 다** `VIDEO_DAILY_SECONDS`(기본 28800) 안일 때만 요청한다 — 지금 키가 찼으면 다음 키로(키 수만큼), 모두 찼거나 그 모델이 찼으면 대체(`daily_video_cap`). 재시도로 요청을 받은 키는 모두 센다(모델·합계는 1회). PT 10-14 실측: 키 4개 · 모델 2개 합계 약 10.4시간(파이프라인 17,524초 + v4.12 시험 19,810초)에 영상 429 0건 → "전체 합계 8시간"은 아니다. 모델별로는 둘 다 8시간 미만이라 단위가 모델인지 프로젝트인지는 모른다 — **두 누계 중 하나를 빼지 말 것.** v4.13 전 파일의 그날 누계는 `legacy` 로 모든 모델·키에 더한다. `seconds`·`calls` 는 전체 합계(표시용).
- `.env` 스위치: `VIDEO_SUMMARY=false` 면 전부 설명란 요약(되돌리기), `VIDEO_MAX_SECONDS`(기본 1800), `VIDEO_DAILY_SECONDS`(기본 28800).
- `PARALLEL = 1` 유지 — 30분 영상 1편 ≈ 18만 토큰(약 103토큰/초: 영상 71 + 음성 32). 병렬이면 무료 분당 토큰 한도에 걸린다.
- 노트 프론트매터에 `grade:`(keep·exclude·null)·`summary_src:` 가 붙는다(새 노트 · v4.6-b 재요약된 옛 노트). **`grade: exclude` 노트는 Vault 에 남고** `wiki_ingest.py:collect_sources`(추출·backfill·페이지 렌더)와 `build_search_index.py:collect_notes`(검색)에서만 빠진다. MOC·시트는 그대로. 제외를 되돌리려면 (v4.6-b) 장부 `grade`(+ `updated_at`)만 고친다 — 다음 `sync_obsidian` 이 노트 프론트매터를 맞춘다.
- 판정: `scheduler.log` 의 `🎬 요약 방식: 영상 N (제외 등급 N) · 설명란 대체 N {사유}` 줄, `sqlite3 "file:data/library.db?mode=ro" "select summary_src, grade, count(*) from videos group by 1,2"`.
- (v4.6-b) `promo_main` 프롬프트에 "무료 자료·템플릿·키트 배포, 구독·댓글 유도는 판매가 아니다 — 돈을 받는 판매·모집만 true" 를 넣었다(좁힘 — 10-13 12:00 무료 키트 시연 영상 오판). 영상 대부분이 사용법·정보이고 끝이나 중간에 자기 강의·상품을 잠깐 알리는 정도도 false(사전 검증: 끝에 강의 모집을 붙인 시연 영상이 exclude 로 잡혔다). bad_summary 는 어느 검사에 걸렸는지 로그 1줄(`summaryProblem`: `empty`·`missing:<절>`·`short_tail:N`).

### 기존분 재요약 (v4.6-b) — 옛 설명란 요약을 실제 영상 요약으로, 천천히

```
scheduler.js main: 마스터 인제스트(신규 영상) 뒤 · 장부 연결이 열려 있을 때 → runResummary() → lib/resummarize.run()
   [오늘(PT) 재요약 수 = 장부 quality.resummary_day · 상한 안이면 후보(summary_src != 'video' · resummary_skip 없음 · 최신 업로드부터)
    → videos.list 1회 → 요약기(RESUMMARY_MODEL, fallback:false, reserveSeconds) → 성공: updateResummary / 실패: 건너뜀·실패 표시 / 중단]
   → sheet_mirror (updated_at 변경분) → sync_obsidian:refresh_changed_notes (요약 절 교체) → 17:30 wiki_ingest backfill (stale 재추출)
```

- **신규 영상이 먼저다.** 실행당 `RESUMMARY_PER_RUN`(5) · 하루(PT) `RESUMMARY_DAILY_MAX`(20). 분량 누계는 신규와 같은 `.video_quota.json` — (v4.13) 모델별·키별로 세므로 재요약(3.5 Flash-Lite)과 신규(2.5 Flash)는 각자 8시간을 쓰고, `RESUMMARY_RESERVE_SECONDS` 기본값은 0(v4.6-b ~ v4.12 는 10800 — 합계 하나로 세던 때. PT 10-14 신규 14편 10,590초가 공용 분량을 먼저 써서 재요약이 9편에서 `daily_video_cap` 으로 멈췄다). 값을 주면 재요약은 모델·키 누계 둘 다에서 그만큼 남긴다.
- 모델은 `RESUMMARY_MODEL`(기본 `gemini-3.5-flash-lite`). 무료 한도가 모델별로 따로라 본 파이프라인의 2.5 Flash 하루 한도를 먹지 않는다. **3.x 모델은 `thinkingBudget` 을 400 으로 거절한다** — `video_summary.thinkingConfigFor` 가 2.x 는 `thinkingBudget: 0`, 그 밖은 `thinkingLevel: 'minimal'`. 2.5 Flash 의 `thinkingBudget: 0` 은 그대로 둘 것.
- **실패하면 설명란 요약으로 대체하지 않는다**(기존 요약 유지). 목록에 없음(`gone`)·공개 아님·길이 모름·영상 토큰 0 → `quality.resummary_skip`(다시 안 함). `bad_json`·`bad_signals`·`bad_summary`·`video_403`·그 밖 4xx → `resummary_fail` +1, 2회면 건너뜀. 429·5xx·네트워크·하루 분량·`video_403_repeated`·`VIDEO_SUMMARY=false` → 그 실행 재요약 중단. (v4.11) 5xx 는 영상 1편에 `RESUMMARY_MAX_5XX`(기본 1, 0 = 신규와 같은 8회)회면 재시도 없이 중단하고(3.5 Flash-Lite 503 은 1~2분 뒤에 와서 8회면 약 13분 — 10-14 00시) 그 영상 `quality.resummary_5xx` +1, 3회면 `resummary_skip = '5xx:…'`(후보 맨 앞 영상이 매번 막지 않게). 상한은 `makeVideoSummarizer` 의 `maxServerErrors`(5xx 만 셈 — 429·네트워크 오류는 그대로 키를 돌린다)로 넘긴다. 신규 영상 경로는 넘기지 않는다 — 신규 쪽 상한을 줄이지 말 것(2.5 Flash 503 은 1~2회 뒤 성공한다). 건너뜀·실패 표시는 시트에 안 보이는 `quality` 만 바꾸므로 `updated_at` 을 안 건드린다.
- 성공(`lib/library.js:updateResummary`, 한 트랜잭션): `summary`·`summary_src='video'`·`grade`·`quality`(+`resummary:true`·`resummary_day`)·`summarized_at`·`updated_at` + 그 소스의 `wiki_extract` → `status='stale'`, `attempts=0`(`updated_at` 은 그대로 — 렌더 결정성). 이미 `video` 인 행은 건드리지 않는다. 토픽(재생목록 분류)은 다시 하지 않는다.
- `runResummary` 는 던지지 않는다 — 재요약 단계가 실패해도 저장·Skip·오류 집계·실행 판정에 영향이 없다. 결과 줄 `🔁 재요약: N편 (제외 등급 N) · 건너뜀 N · 실패 N {사유} · 오늘 N/20 · 남은 대상 N`(1편 이상이면 그 실행의 완료 텔레그램에도 한 줄 — 텔레그램은 기존 조건대로 신규·변경이 있을 때만 나간다).
- 노트(`sync_obsidian.py:refresh_changed_notes`): 장부 `summary_src` 가 `video` 인 행만 본다. 노트 프론트매터 `summary_src` 가 `video` 가 아니면 요약 절(`**▶ 영상 보기: **` 줄 다음 `---` 줄 뒤부터 `\n\n---\n## 🔗 관련 항목` 앞까지)을 새 요약으로 바꾸고 `grade`·`summary_src` 를 맞춘다(없으면 `notion_id` 줄 앞에 넣음). `video` 인데 `grade` 만 다르면 그 줄만. 경계를 못 찾으면 파일을 통째로 다시 쓰지 않고 그대로 둔 채 `RESULT_JSON.refresh_skipped` 로 보고. 바뀐 노트가 있으면 검색 인덱스를 갱신한다(재구성·인제스트는 안 함).
- 끄기: `.env RESUMMARY=false`(재요약만) · `VIDEO_SUMMARY=false`(영상 입력 전부). 진행 판정: `sqlite3 "file:data/library.db?mode=ro" "select json_extract(quality,'$.model'), grade, count(*) from videos where summary_src='video' group by 1,2"` · 건너뜀 `… where json_extract(quality,'$.resummary_skip') is not null`.
- 처리량: (11-01 실측, PT 10-16~10-30) 하루 평균 22.3편. 실제 천장은 3.5 Flash-Lite 모델 누계 8시간 ÷ 편당 약 858초 ≈ 하루 33.6편이라 `RESUMMARY_DAILY_MAX` 40 에는 닿지 않는다. 부족분은 503 중단 52% · 통째 실패(잠자기·ENOTFOUND) 26% · 실행 누락 11% · 분량 상한 10%. `.env` 는 실행당 20 · 하루 40(11-01~) — 실행당 몫을 하루 몫의 절반으로 둬 앞 실행이 빠지거나 503 으로 멈춘 날 같은 PT 하루의 다음 실행이 채운다. 천장을 넘기려면 모델 누계 상한(v4.13)을 건드려야 한다 — 대표님 결정 사항(시험 필요).

### 매일 Wiki 검토 → 제안함 (v4.20)

- 흐름: launchd 08:30 `skill_review.py` → 장부(읽기 전용) `created_at > 지난 through` 영상(exclude 제외)·꿀팁 → `claude -p`(도구 0 · MCP 0 · 재시도 0) → `data/proposals/YYYYMMDD.json`(KST) → 텔레그램(제안 ≥1·실패만, 실행 알림 봇) → `localhost:3000/wiki#tab=proposals` 에서 승인·보류·거절.
- 쓰는 주체 분리: 날짜 파일은 `skill_review.py` 만, `decisions.json` 은 `lib/proposals.js`(server.js) 만. 기준점 = 마지막 날짜 파일의 `through`(상태 파일 없음). `--days` 시험은 `trial/` 이라 기준점을 안 움직인다.
- **Claude 호출에 도구·MCP 를 주지 말 것**(`--tools ''`·`--strict-mcp-config`). 같은 날 파일이 있으면 멈춘다(`exists`, 알림 없음).
- 승인 = `~/.claude/skills/wiki-<slug>/SKILL.md` 설치, 내용은 저장된 제안에서만(요청 본문 값 불사용). **이미 있으면 덮어쓰지 않는다(409)**. 되돌리기는 `data/proposals/_trash/` 로 이동(삭제 아님).
- POST `/api/proposals/decide` 는 Host·Origin 이 `localhost:3000`/`127.0.0.1:3000` 이고 JSON 일 때만. **`wiki_lan_server.js` 에 제안함 라우트를 넣지 말 것.**
- (v4.21) 분야에 `invest`, 하루 상한 5건, 꿀팁 우선(`tip_review` 저장). `--backfill=DAYS` = 40편 묶음마다 호출 → 후보 15건 초과 시 순위 호출(번호만, 내용 무변경) → `trial/`(기준점·알림 무영향).
- 프로필 `data/review_profile.md`(gitignore, 대표님이 고침). 구독 사용량을 쓴다 — 하루 1회. 판정: `~/Library/Logs/irichgreen/skill-review.log` 의 `RESULT_JSON`.

### Obsidian 고아 파일 격리 (`sync_obsidian.py:quarantine_orphans`)

장부 `videos` 에 없는 notion_id 를 가진 영상 노트를 **삭제하지 않고** `VAULT/_trash/<타임스탬프>/`로 이동합니다 (v4.0 전에는 "Notion에서 삭제된 페이지").
장부를 잘못 읽어 목록이 비면 대량 소실이 되므로 되돌릴 수 있어야 합니다. `videos_dup` 을 가리키던 노트도 여기서 격리된다(의도).

**안전장치 3중 — 하나라도 걸리면 아무것도 하지 않는다. 완화 금지.**

1. 장부 videos 0건이면 건너뜀 (장부 이상 의심)
2. 장부 행이 Vault 파일의 50% 미만이면 건너뜀 (부분 로드 의심)
3. 고아 비율이 40%를 넘으면 중단 (수동 확인 필요)

`video_url` 프론트매터가 있고 토픽 폴더 안에 있는 **영상 노트만** 대상입니다.
`schema.md` 등 Vault 시스템 문서는 오탐하지 않습니다. v4.0 부터 `notion_id`·`video_url` 은 **맨 앞 프론트매터 안의 것만** 센다(`sync_obsidian.fm_value`).
**꿀팁 고아**(장부 `tips` 에 없는 꿀팁 노트)는 옮기지 않고 `RESULT_JSON.tips_orphans` 로 보고만 한다(v4.0 2단계 결정).

- `python3 sync_obsidian.py --orphans-dry-run` — 대상만 출력, 이동 없음
- 실행 이력은 Obsidian `log.md`의 `cleanup` 항목에 남습니다
- 2026-08-21 첫 실행에서 435개 격리 (`_trash/20260821_172922/`). **이 폴더는 삭제 금지.**

### 재생목록 대기 큐 파일 (v2.5)

| 파일 | 역할 |
|------|------|
| `pending_playlist_adds.json` | 처리 대기 큐. quota 초과·실패 시 적재되고 다음 실행에서 소진. |
| `pending_playlist_adds.dead.json` | 영구 실패·재시도 초과 격리 (dead-letter). 자동 복구되지 않음. |
| `pending_playlist_adds.backup.*.json` | `clean_pending_queue.js --apply`가 만드는 백업. **삭제 금지.** |

### 외부 서비스

- **YouTube Data API v3** (읽기전용): `YOUTUBE_API_KEY`
- **YouTube OAuth v3** (재생목록 쓰기): `YOUTUBE_OAUTH_CLIENT_ID/SECRET/REFRESH_TOKEN`
- **Gemini 2.5 Flash**: `GEMINI_API_KEY`·`GEMINI_API_KEYS` (요약 + Wiki 합성 + 검색 임베딩) · **3.5 Flash-Lite**: 같은 키 (재요약 v4.6-b · 토픽 분류 v4.14)
- **Google Apps Script 웹앱** (v4.0, 시트 미러 받는 쪽): `SHEET_MIRROR_URL`, `SHEET_MIRROR_TOKEN`
- **Telegram Bot**: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
- **구글 드라이브 데스크톱 앱** (v4.1, 장부 백업 사본): `LIBRARY_BACKUP_DIR` — API 호출 없음, 앱이 동기화하는 로컬 폴더에 파일만 쓴다

모든 API 키는 `.env`에서 로드. `scheduler.js`와 `lib/*.js` 각각 자체 `loadEnv()` 포함.

### v4.0 — 로컬 원본 장부 `data/library.db` (2026-10-11~)

- **장부가 원본이다.** `scheduler.js`·`kakao_ingest.py` 는 `data/library.db` 에 쓰고, `sync_obsidian.py`·`sheet_mirror.py` 는 장부를 읽어 노트·시트를 만든다(`sheet_mirror.py` 는 `meta` 의 `sheet_*` 키만 쓴다). 파이프라인에 노션 호출이 없고 앱 코드는 노션 모듈을 import 하지 않는다. 노션은 2026-10-12 해지했다(v4.3 에서 노션 모듈·`.env NOTION_*` 삭제).
- **장부는 이 맥에만 있는 원본이다.** 지우거나 새로 만들지 말 것 — 파일이 없으면 Node·Python 모두 만들지 않고 던진다. 복원은 `data/backups/library-YYYYMMDD.db.gz`(v4.1, 하루 1회 · 드라이브에도 사본) 또는 `data/library.db.bak.*` 에서 — 절차는 README 「장부 백업」.
- 새 영상 노트 본문 = 장부 `summary`(Gemini 요약 원문 마크다운). 모양은 노션 시절 노트와 같다(빈 줄 · `**▶ 영상 보기: **URL` · `---` · 요약).
- 노션 → 장부 적재 스크립트(`notion_to_sqlite.py`)는 v4.3 에서 지웠다. 장부를 되살리는 경로는 백업 복원뿐이다(README 「장부 백업」).
- journal_mode 는 기본(DELETE) 그대로 둔다. 접근이 scheduler → kakao_ingest → sync_obsidian 순차라 WAL 이 필요 없다. 겹치면 Node·Python 모두 busy_timeout 5초 대기.
- `record_id` = 노션 page id(하이픈 포함) = Obsidian `notion_id`. **프론트매터 키 이름 `notion_id` 를 바꾸지 말 것** — wiki_ingest·검색 인덱스 상태가 이 값에 묶여 있다. 새 행은 uuid4.
- `data/` 는 gitignore. 개인 요약 전체가 들어 있다 — `git check-ignore -q data/library.db` 로 확인.
- `videos_dup` 은 지우지 않는다(중복 페이지 보관, 되돌림용). `has_vault_note=1` 행의 노트는 2단계 첫 동기화에서 `_trash/` 로 격리된다(의도됨).
- 스키마를 바꾸면 `lib/library_schema.sql` 의 `PRAGMA user_version` 을 올리고 `lib/library_db.py:SCHEMA_VERSION` 도 같이 올린다. 기존 장부는 `scripts/migrate_library.py --apply` 로 올린다 — **코드를 올린 뒤 이전 전까지는 모든 실행이 user_version 불일치로 던진다**(정시 실행 창 밖에서 연달아 할 것). 테스트 `test_backup_library.py` 의 버전 기대값은 `SCHEMA_VERSION` 을 따른다.
- (v4.5, user_version 2) `wiki_extract` — Wiki 합성 추출 결과(위 「Wiki 합성 결과 누적」). Gemini 무료 한도로 얻은 값이라 지우지 않는다. 시트로 보내지 않는다. 장부 백업에 들어간다.
- (v4.6, user_version 3) `videos.grade`(keep·exclude·NULL)·`quality`(신호 JSON)·`summarized_at` — 기존 장부는 `migrate_library.py` 가 열만 붙인다(옛 행 NULL). 열은 `CREATE TABLE` 끝에만 추가한다(ALTER 결과와 순서가 같아야 한다). 시트 열은 그대로(머리글 변경 금지 규칙) — 등급은 시트로 보내지 않는다. `summary_src` 값: `property`·`blocks`·`empty`(노션 시절) · `app`(설명란 요약) · `video`(실제 영상 요약).
