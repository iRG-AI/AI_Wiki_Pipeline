# [CC-1103-A] v4.18 꿀팁 두 번째 입구 — 텔레그램 전용 봇 → 장부 tips (카톡과 같은 엔진)

- 작성: 2026-11-03 12:49 KST (pm-wiki) · 발주 XP-1103-C (cw-wiki → pm-wiki, 대표님 착수 승인 11-03 12:34)
- 승인: 대표님 2026-11-03 13:12 「XP-1103-C 를 읽고 진행」 — 범위 밖 3건(H · igsh · 제목 거부 목록)은 이 지시서에 넣지 않는다(기본값 보류)
- 실행: implementer · 검수: verifier
- 버전: v4.18 (마이너 — 같은 tips 표·같은 엔진에 입구만 추가)

## 배경
- 꿀팁 링크의 실제 흐름은 인스타 → 대표님이 카톡 '나와의 채팅'에 옮김 → 맥 카톡 CSV 내보내기(수동) → 정시 실행 `kakao_ingest.py --apply --if-new`. 카톡 내보내기는 자동화할 길이 없다(읽기 API 없음 · 데이터 파일 암호화 · 인스타 웹 수집은 계정 위험).
- 새 입구: 휴대폰 공유 → **텔레그램 전용 봇 방**(실행 알림 봇과 별개). 정시 실행마다 봇의 `getUpdates` 를 읽어 카톡과 같은 함수로 장부 `tips` 에 넣는다. 카톡 경로는 그대로 안전망(중복은 `url_key` 대조).
- 설계 조사(investigator, 11-03 읽기 전용) 결론을 이 지시서에 그대로 옮겼다:
  - 공용화는 새 lib 없이 `kakao_ingest.py` 안 함수 3개 + `lib/kakao_parse.py` 함수 1개로 뗀다. `test_kakao_ingest.py` 가 `ki.lookup_title`·`ki.load_env` 등 모듈 속성을 바꿔치기하므로 함수가 `kakao_ingest` 안에 남아야 테스트가 그대로 먹는다.
  - offset·마지막 성공 수신 시각은 장부 `meta`(key, value) 표의 새 키 2개 — 스키마 무변경(user_version 3). tips INSERT 와 같은 `with conn:` 트랜잭션으로 쓰면 "커밋 뒤에만 offset" 이 된다.
  - 새 상태 파일 없음.

## 수행 범위

### 바꿀 파일
| 파일 | 변경 |
|---|---|
| `lib/kakao_parse.py` | `parse_links` 의 메시지 순회 부분을 `links_from_messages(msgs, since=None)` 로 떼고 `parse_links` 는 그것을 부른다(출력 동일). 입력 `[{'date','message', 'ref'(선택)}]`, 출력 원소에 `ref` 를 그대로 싣는다 |
| `kakao_ingest.py` | `main` 안 덩어리를 같은 파일 함수로 뗀다 — `existing_keys(conn) -> (n_rows, keys)` · `plan_rows(new, found) -> [row]`(표 로그 포함) · `insert_rows(conn, plan, meta=()) -> (titles, db_total)`(`meta=[(key, value)]` 를 **같은 `with conn:`** 안에서 `INSERT OR REPLACE INTO meta`). `main` 의 동작·로그 문구·RESULT_JSON 은 그대로 |
| `telegram_tips_ingest.py` (신규, 레포 루트) | 아래 「새 입구 명세」 |
| `scheduler.js` | `runTipsBot()` — `runKakaoIngest` 와 같은 꼴(절대 reject 안 함, RESULT_JSON 파싱). `main` 에서 카톡 훅 다음 · 시트 미러 앞. 완료 텔레그램 묶음에 `📮 텔레그램 → AI 꿀팁` 줄(저장·이미 있음·링크 없음 건수). `r.error ∈ {auth, conflict, bad_request}` 이거나 `r.stale_h ≥ 18` 이면 기존 알림 봇으로 `⚠️ [텔레그램 꿀팁 입구] …` 를 따로 보낸다(장부 백업 실패 알림과 같은 방식). `module.exports` 에 `runTipsBot` |
| `scripts/test_tips_bot.py` (신규) | 아래 「테스트」 15항목. 가짜 urlopen · 임시 장부 · 가짜 env 딕셔너리, 네트워크 0 |
| `scripts/test_scheduler_guards.js` | `runTipsBot` 3건 — 가짜 인터프리터 exit 2 · 출력 없이 죽음 · skipped — 모두 reject 없이 결과 객체 |
| `scripts/run_all_tests.sh` | `PY_TESTS` 에 `test_tips_bot` → 16종 |
| `README.md` | 요약표 1행 + 상세 1절 `[v4.18] - 2026-11-03`, 카톡 절에 두 번째 입구 · `.env` 키 이름 · 명령 · 대표님 봇 만들기 단계 |
| `CLAUDE.md`·`AGENTS.md` | 머리 버전 v4.18 + 한 줄 요약, Commands 에 새 명령 3줄, 회귀 테스트 목록 16종, 파일 표 1행, 카톡 절에 두 번째 입구 문단, 변경 이력 1줄(두 파일 같은 내용) |

### 바꾸면 안 되는 것
- 장부 스키마(`PRAGMA user_version` 3, `lib/library_schema.sql` 무변경) · tips 열 의미(`source` = 호스트만) · 카테고리·태그 이름·순서.
- **카톡 경로 결과**: 같은 CSV 에 대한 RESULT_JSON·tips 행·로그 문구가 리팩터 전후 같아야 한다. `classify` 에 넘기는 글자도 지금 그대로(아래 「범위 밖」 H 참고).
- `lib/kakao_parse.py` 의 `STRIP_PARAMS`·`url_key`·`classify`·`guess_meta` 동작, `lib/title_fetch.py`.
- 실행 알림 봇과 `.env` 의 `TELEGRAM_*` 키 · launchd plist 4개 · `.gitignore` · `.env`(값 입력은 대표님 몫, 아래 B 단계).

## 새 입구 명세 — `telegram_tips_ingest.py`
- 실행: `/opt/homebrew/bin/python3`. 모드 — 기본 dry-run(장부·meta 쓰기 0 · sendMessage 0 · offset 그대로) / `--apply` / `--whoami` / `--no-lookup`(카톡과 같은 뜻).
- `.env`(읽기는 `lib/env_util.py`): `TIPS_BOT_TOKEN` · `TIPS_BOT_CHAT_ID`(허용할 개인 대화 chat id 하나). 토큰이 없으면 `skipped: "not_configured"` exit 0 · 요청 0. 토큰은 있고 chat id 가 없으면 `skipped: "no_chat_id"` exit 0. 제목 조회 설정은 카톡과 같은 `KAKAO_TITLE_*` 를 쓴다(새 키 없음).
- `--whoami`: offset 없이 getUpdates 1회(확인 처리 안 됨) → 개인 대화의 `chat.id`·이름을 **터미널(stdout)에만** 찍는다. 장부·로그 파일·RESULT_JSON 에 남기지 않는다.
- 흐름(`--apply`):
  1. 장부 `meta` 에서 `tips_bot_offset` 을 읽는다(없으면 0).
  2. `getUpdates` — `offset = 저장값+1`(0 이면 생략), `timeout=0`, `limit=100`, `allowed_updates=["message"]`. 이 호출이 지난 실행분의 텔레그램 쪽 확인을 겸한다. 100건이 꽉 차면 로그 「남음」, 다음 실행이 이어 받는다.
  3. `message.chat.id` 가 `TIPS_BOT_CHAT_ID` 와 다른 업데이트는 버린다 — 건수만(`dropped`), id 는 어디에도 찍지 않는다.
  4. 링크 뽑기: `text`·`caption` 에 기존 `extract_urls`, 더해 `entities`·`caption_entities` 중 `type=="text_link"` 의 `.url`. 날짜 = `message.date` → KST `YYYY-MM-DD HH:MM:SS` 꼴(카톡 `date` 와 같은 꼴, `saved_date` 는 앞 10자). `ref=(update_id, message_id)`.
  5. `links_from_messages` → `existing_keys` 대조 → `resolve_titles` → `plan_rows` → `insert_rows(conn, plan, meta=[('tips_bot_offset', 받은 최대 update_id), ('tips_bot_last_ok', 지금 ISO UTC)])` — 한 트랜잭션. 업데이트가 0건이어도 `tips_bot_last_ok` 만 같은 방식으로 쓴다. meta 쓰기는 tips `updated_at` 을 건드리지 않는다.
  6. **커밋 뒤에** 메시지마다 답장(허용 chat 만): `저장: <제목> · <카테고리>` / `이미 있음` / `링크 없음`. 한 메시지에 링크가 여럿이면 링크마다 한 줄. 일반 텍스트(parse_mode 없음), `reply_parameters={message_id, allow_sending_without_reply: true}`, 1초 간격. 답장 실패는 적재를 되돌리지 않는다.
  7. 판정: 메시지 결과 `saved`(이번에 만든 행의 키를 처음 실은 메시지) / `dup` / `no_link`.
- HTTP `tg(method, payload)`: POST JSON, timeout 20초, urllib 만(`sheet_mirror.post` 와 같은 꼴). 실패 본문 `{"ok":false,"error_code","description","parameters":{"retry_after"}}` 는 `e.read()` 로 읽는다. 판정은 상태 코드로만.

  | 응답 | getUpdates | sendMessage(답장) |
  |---|---|---|
  | 401 · 403 · 404 | 즉시 중단 exit 2 `error: "auth"`, 재시도 0 | 남은 답장 중단(적재 유지) |
  | 409 | 즉시 중단 exit 2 `error: "conflict"` | — |
  | 400 | 중단 exit 2 `error: "bad_request"` | 그 답장만 건너뜀 |
  | 429 | `retry_after` 초(상한 60) 대기 후 재시도, 2회까지 | 1회 따르고 실패면 남은 답장 포기 |
  | 5xx · 네트워크 · timeout · JSON 아님 | 2·4초 백오프, 3회 뒤 exit 1 `error: "transient"` | 남은 답장 포기 |

  중단·실패 때 장부·offset 은 그대로(트랜잭션 전이거나 롤백).
- **토큰은 URL 경로에 들어간다 — 요청 URL·토큰·chat id 를 로그·RESULT_JSON·예외 문구에 쓰지 않는다.**
- 마지막 줄 `RESULT_JSON:{created, dup, no_link, dropped, candidates, db_total, titles, title_lookup, stale_h, error, skipped}`. `stale_h` = 지금 − 실행 전 `tips_bot_last_ok`(시간, 소수 1자리, 없으면 null).

## 확인(먼저)
| # | 확인 | 기대 | 다르면 |
|---|---|---|---|
| 1 | `git status --porcelain` · `git log --oneline -1` | 비어 있음 · `34127d0` 이후 | 멈추고 보고 |
| 2 | 지금 시각 | 정시 실행(00·06·12·18시 −10/+20분)·wiki-ingest(17:25~17:50) 창 밖, `pgrep -f scheduler.js` 비어 있음 | 창 밖까지 기다리지 말고 멈추고 보고 |
| 3 | `scripts/run_all_tests.sh` | `RESULT: 15/15 통과` | 멈추고 보고 |
| 4 | 리팩터 전 기준값: 임시 폴더에 장부 사본(`sqlite3 data/library.db ".backup <임시>/lib.db"`)과 `test_kakao_ingest.py` 의 임시 CSV 꼴 CSV 하나를 만들어 `kakao_ingest.py --apply --no-lookup` 을 사본 장부로 돌린다(사본을 가리키는 방법은 테스트가 쓰는 방식 그대로) → RESULT_JSON 과 새 tips 행(record_id·created_at·updated_at 제외)을 저장 | 저장됨 | — |

## 단계

### A. 구현 (implementer, 지금)
1. `lib/kakao_parse.py` · `kakao_ingest.py` 함수 떼기 → 확인 4 와 같은 방법으로 리팩터 뒤 값을 뽑아 **diff 0**.
2. `telegram_tips_ingest.py` 작성(명세대로).
3. `scheduler.js` 훅 · 테스트 2파일 · `run_all_tests.sh`.
4. 문서(README · CLAUDE.md · AGENTS.md — CLAUDE.md 와 AGENTS.md 는 같은 내용). README 「설치」에 대표님 단계를 아래 B 그대로.
5. `scripts/run_all_tests.sh` → `RESULT: 16/16 통과`.
6. 커밋 — 위 「바꿀 파일」 + 이 지시서만 `git add`. 메시지 `[CC-1103-A] v4.18 꿀팁 두 번째 입구 — 텔레그램 전용 봇 → 장부 tips (카톡과 같은 엔진 · 장부 스키마 무변경)`. push 하지 않는다.

### B. 대표님 (커밋 뒤, 따로 승인)
1. 텔레그램 BotFather 에서 `/newbot` → 새 봇 이름 정하기 → 토큰 받기(실행 알림 봇과 다른 봇).
2. 새 봇 방을 열고 `/start` 보내기.
3. `.env` 에 `TIPS_BOT_TOKEN=<토큰>` 한 줄 입력 → 터미널에서 `cd <REPO_ROOT> && /opt/homebrew/bin/python3 telegram_tips_ingest.py --whoami` → 나온 chat id 를 `.env` 에 `TIPS_BOT_CHAT_ID=<숫자>` 로 입력. 값은 XP·문서·대화에 붙이지 않는다.
4. 봇 방에 링크 2개를 보낸다 — 새 링크 1개, 장부에 이미 있는 링크 1개(PM 이 고른 것).

### C. 실측 (PM 이 implementer 를 이어 붙여, 장부 쓰기 창 밖에서)
1. `telegram_tips_ingest.py`(dry-run) → candidates 1 · dup 1.
2. `telegram_tips_ingest.py --apply` → created 1 · 답장 2통(저장 · 이미 있음, 대표님 화면).
3. `sync_obsidian.py` → 꿀팁 노트 +1 · `scripts/verify_library.py` ok · `sheet_mirror.py --dry-run` 꿀팁 1.
(다음 정시 실행이 대신 돌아도 된다 — 그때는 `scheduler.log` 의 `📮` 줄로 본다.)

## 테스트 — `scripts/test_tips_bot.py`
1. 토큰 없음 → skipped `not_configured`, 요청 0
2. chat id 없음 → `no_chat_id`, 출력에 id 없음
3. 허용 chat 링크 1건 저장 — 카톡과 같은 행 꼴(uuid·url_key·기본값·saved_date KST)
4. 허용 밖 chat → 적재 0 · `dropped` 만 · 출력에 그 id 없음
5. 이미 있는 URL → `dup`, 링크 없음 → `no_link`, 답장 문구 3종 정확
6. offset 이 커밋과 함께 오름 · 다음 getUpdates 인자 `offset=최대+1`
7. INSERT 실패(트리거) → 행 0 · offset 그대로 · 답장 0
8. 401·403·404·409 각각 요청 1회 뒤 exit 2 · 장부·offset 그대로
9. 429 → `retry_after` 대기(sleep 가짜) 뒤 성공
10. 5xx 3회 → exit 1 `transient` · 장부·offset 그대로
11. 답장 실패(403·5xx)에도 적재 유지 · exit 0
12. caption · `text_link` URL 도 뽑음
13. `stale_h` 계산 · last_ok 없으면 null
14. 모든 경로 stdout·stderr 에 토큰 문자열 0회
15. dry-run → 장부·meta 쓰기 0 · sendMessage 0

테스트 값은 가짜 토큰 `TEST:TOKEN` 꼴과 chat `1` 만.

## 완료 기준 (verifier)
| # | 기준 | 확인 방법 |
|---|---|---|
| 1 | 카톡 경로 결과 동일 — 리팩터 전후 RESULT_JSON·tips 행 diff 0 · `test_kakao_ingest.py` 37/37 | implementer 가 남긴 전후 값 · 테스트 출력 |
| 2 | `scripts/run_all_tests.sh` → `RESULT: 16/16 통과` | 직접 실행 |
| 3 | `test_tips_bot.py` 15/15 · `test_scheduler_guards.js` 36/36 | 직접 실행 |
| 4 | 장부 스키마 무변경 — `lib/library_schema.sql` diff 0 · 실제 장부 `PRAGMA user_version` 3 | `git diff` · sqlite3 ro |
| 5 | 401·403·404·409 즉시 중단(요청 1회), 커밋 실패 시 offset 그대로 | 테스트 7·8 + 코드 읽기 |
| 6 | 허용 밖 발신자 적재 0 · id 미출력 | 테스트 4 |
| 7 | 토큰·chat id 값·요청 URL 이 레포 diff·로그·RESULT_JSON 에 없다 | `git diff` grep(`api.telegram.org/bot` 뒤에 상수 없음) · 테스트 14 |
| 8 | 새 훅은 reject 하지 않고, 실패해도 시트 미러·백업·Obsidian 동기화가 그대로 돈다 | `test_scheduler_guards.js` 3건 + `main` 호출 자리 읽기 |
| 9 | 키 없으면 `skipped=not_configured` — 지금 `.env` 로 `telegram_tips_ingest.py` dry-run 이 요청 0 으로 끝난다 | 직접 실행(B 단계 전) |
| 10 | plist 4개 diff 0 · `.gitignore` 무변경 · 새 상태 파일 없음 · `README.html` 없음 | `git diff --stat` · `git status` |
| 11 | README 요약표 1행 + 상세 1절, CLAUDE.md·AGENTS.md 같은 내용으로 v4.18 · 공개 레포 금지값(개인 절대경로·맥 이름·`.env` 값) 추가 없음 | diff 읽기 |
| 12 | 커밋 1개, 범위 밖 파일 없음 | `git show --stat HEAD` |

(C 실측은 이 표 밖 — B 뒤에 PM 이 별도로 판정해 XP 회신 기준 5 로 올린다.)

## 하지 말 것
- 텔레그램 실제 API 호출(테스트·확인 모두 가짜로). 실제 장부에 쓰기(A 단계에서는 사본만).
- `.env` 편집 · launchd 조작 · `git push`.
- 카톡 결과를 바꾸는 "덤" 수정(H·`igsh`·제목 거부 목록 등 — 아래 범위 밖).
- webhook 방식 · long polling · 새 상태 파일.

## 롤백
- 코드: `git revert <커밋>`. 장부는 A 단계에서 쓰지 않는다.
- C 단계 뒤: 새 tips 1행과 `meta` 키 2개만 생긴다 — 되돌릴 일이 생기면 지시서로(`tips` 행 삭제 + 노트 `_trash/` 이동 + `sheet_mirror --full`).
- 입구만 끄기: `.env` 에서 `TIPS_BOT_TOKEN` 줄 삭제 → `skipped`.

## 범위 밖 (대표님 결정 대기 — XP-1103-C 회신 「보류」)
- **H. 노션 링크 「지식관리」 오분류(원인 확인됨, CW 추정과 다름).** DM 문구가 아니라 `kakao_ingest.py:186` 이 메시지 전체(URL 포함)를 `guess_meta` → `classify` 의 "붙인 글"로 넘겨, `_tag_text` 가 URL 인자에서만 노션 호스트를 빼고 메시지 안의 `notion.site` 는 남는다. 10-01 이후 노션 링크 메시지 12건은 모두 URL 한 줄뿐인데 메시지를 넣으면 `('지식관리', ['Notion'])`, URL 만이면 `('기타', [])`. v4.9 수정이 카톡 경로에서는 처음부터 듣지 않았다. 추천: 별도 지시서로 「classify 에 넘기는 글 = 메시지에서 URL 을 뺀 글」 1줄 + 기존 행 `recategorize_tips.py`(dry-run 상 2행만 고쳐짐). 텔레그램 입구도 같은 함수라 이 지시서 뒤 같은 결함을 물려받는다 — H 를 고치면 두 입구가 같이 고쳐진다.
- 인스타 공유 링크 `igsh=` 를 `STRIP_PARAMS` 에 넣을지(같은 릴스가 공유마다 다른 키 · 기존 장부 해당 0행).
- `title_fetch` 거부 목록에 `Instagram`·`Login • Instagram` 류를 넣을지(C 실측 뒤).
