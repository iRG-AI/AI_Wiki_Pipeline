# [CC-1104-B] v4.19 — 꿀팁 판정 글자에서 URL 빼기 · 인스타 제목·공유 파라미터 · 오분류 4건 + 인스타 1건 보정

- 작성: 2026-11-04 12:25 KST · pm-wiki
- 근거: XP-1103-C 라운드 1 회신의 보류 3건 → 대표님 11-04 「지시서 작성」
- 실행: implementer 를 **두 번** 부른다 — 1부(코드·테스트·문서, 커밋) → verifier → 2부(장부 보정). 1부가 verifier 통과한 뒤에만 2부.
- **2부 기한: 11-04 17:49 까지 끝낸다**(이유는 2부 배경). 못 맞추면 2부를 하지 말고 멈춰 보고한다.

## 배경

1. **노션 꿀팁 「지식관리」 오분류(관찰 H).** `lib/kakao_parse.guess_meta` 가 `classify(url, message, fetched_title)` 로 메시지 글 **전체**를 넘긴다. 카톡·텔레그램 메시지 글에는 링크 자체가 들어 있다(`https://xxx.notion.site/...`). v4.9 의 `_tag_text` 는 첫 인자 `url` 에서만 노션 호스트를 빼므로, 메시지 안의 같은 URL 에서 `notion` 이 잡혀 태그 `Notion` → 「지식관리」가 된다. 11-03 카톡 적재 4건이 그렇다(아래 표). 텔레그램 입구(v4.18)도 같은 함수를 쓴다.
   - 같은 함수 안에서 「사용자가 붙인 글」 제목 후보(`extra`)는 이미 URL 을 뺀 글이다(`re.sub(r'https?://\S+', '', message)`). 판정 글자도 같은 글을 쓰면 된다.
2. **인스타 릴스 제목이 「Instagram」.** 11-04 텔레그램 실측에서 `lib/title_fetch.py` 가 로그인 벽 화면의 일반 제목 「Instagram」을 받아들였다(`_BAD_EXACT` 에 없음). 거부되면 추정 제목으로 가야 하는데, 지금 추정 규칙은 인스타 주소에서 경로 끝 조각을 써서 `De qY6Tz KN` 같은 글이 된다 — 유튜브처럼 「인스타 릴스 (제목 미확인)」 꼴이 맞다.
3. **인스타 공유 파라미터.** 공유 링크에 `?dlrf=…`(11-04) · `?igsh=…`(11-03 표본)가 붙는다. `STRIP_PARAMS` 에는 `igshid` 만 있다. 남으면 같은 릴스를 다시 공유했을 때 `url_key` 가 달라 중복으로 못 거르고, 공유자 식별 값일 수 있는 글자가 시트·Vault 에 남는다. 장부에 이 두 파라미터를 가진 행은 **1건뿐**(아래 인스타 행) — 다른 행의 `url_key` 는 바뀌지 않는다.
4. **이미 들어간 행 보정.**
   - 노션 오분류 4건 중 `recategorize_tips.py` 가 지금 규칙으로 잡는 것은 2건(`eb8f2341`·`039e0964`, 11-04 dry-run `rows: 2`)뿐이다. `3dc03276`·`66cf7794` 는 메시지 글로 매긴 값이라 「v4.8 규칙 값」과 달라 사람이 고른 값으로 보고 건너뛴다. → 지정한 record_id 를 규칙 값으로 보고 다시 매기는 `--ids` 를 더한다.
   - 인스타 1행(`title=Instagram`, URL 에 `dlrf`)은 **노트가 아직 없다** — 11-04 18:00 정시 실행의 `sync_obsidian` 이 처음 만든다. 그 전에 장부 행만 고치면 노트·시트는 고친 값으로 만들어진다. 18:00 이후면 노트 제목·파일명·`link_url` 까지 고쳐야 해 일이 커진다 → **2부 기한 17:49**(장부 쓰기 창 · wiki-ingest 17:30 창 고려).

| record_id 앞 8자리 | saved_date | 지금 | 기대(`classify(url, title)`) | 2부에서 |
|---|---|---|---|---|
| `eb8f2341` | 10-13 | 지식관리 `["Notion"]` | 기타 `[]` | 기본 실행 |
| `039e0964` | 10-17 | 지식관리 `["Claude","Notion"]` | 모델/LLM `["Claude"]` | 기본 실행 |
| `3dc03276` | 10-20 | 지식관리 `["Claude","Notion"]` | 모델/LLM `["Claude"]` | `--ids` |
| `66cf7794` | 10-31 | 지식관리 `["Claude","Notion"]` | 모델/LLM `["Claude"]` | `--ids` |
| `d9ab26b5` | 10-10 | 지식관리 `["Notion"]` | (노션 대시보드 자료 — 제목이 노션 이야기) | **건드리지 않는다** |

## 범위

### 1부 — 바꿀 파일
- `lib/kakao_parse.py`
  - `STRIP_PARAMS` 에 `'igsh'`, `'dlrf'` 추가(다른 항목·순서 그대로).
  - `guess_meta`: `classify` 에 넘기는 메시지 글을 **URL 을 뺀 글**로(이미 계산하는 `extra` 와 같은 정리 — 한 번 계산해 두 곳에 쓴다). `classify` 의 시그니처·규칙·태그 목록·카테고리 목록은 그대로.
  - `guess_meta`: 호스트가 `instagram.com`(www 포함)이면 추정 제목 = 경로가 `/reel/`·`/reels/` 면 `인스타 릴스 (제목 미확인)`, 그 밖이면 `인스타 게시물 (제목 미확인)`, 메모 = `NEED_TITLE_MARK`. `title_src` 는 `'guess'` 그대로(원문 제목 조회는 계속 시도 — 공개 게시물은 좋은 제목이 올 수 있다).
- `lib/title_fetch.py`: `_BAD_EXACT` 에 `'instagram'` 추가. `_BAD_PREFIX` 에 로그인 화면 꼴 `'login • instagram'` 추가(소문자 비교). 다른 항목 그대로.
- `scripts/recategorize_tips.py`: `--ids=<record_id>[,<record_id>…]` — 목록의 행은 「규칙이 매긴 값」으로 보고 지금 규칙(`classify(url, title)`)으로 다시 매긴다. 목록에 없는 행은 지금 판단 그대로(옵션을 안 주면 동작 무변경). 목록의 id 가 장부에 없으면 쓰기 전에 멈춘다(exit 1). `RESULT_JSON` 에 `forced` 건수. 백업·노트 제자리 수정·재실행 0건 규칙은 기존 그대로.
- 테스트(기존 파일에 추가, 네트워크 0):
  - `scripts/test_kakao_ingest.py` — (a) 메시지 글에 노션 주소가 들어 있어도 노션 태그가 붙지 않는다(제목 「Claude …」 → 모델/LLM `["Claude"]`), (b) 메시지에 사람이 쓴 「노션 템플릿」 같은 글은 지금처럼 `Notion` 태그(동작 유지), (c) `igsh`·`dlrf` 가 빠진 `clean_url`·`url_key`, 같은 릴스의 두 공유 링크가 같은 `url_key`, (d) 인스타 릴스·게시물 추정 제목·메모.
  - `scripts/test_title_fetch.py` — 「Instagram」·「Login • Instagram」 → `bad_title`.
  - `scripts/test_recategorize_tips.py` — `--ids` 로 사람이 고른 값처럼 보이는 행을 다시 매김 · 목록 밖 행은 보존 · 없는 id 면 쓰기 0 · exit 1 · 두 번째 실행 0건.
- 문서: README 요약표 1행 + 상세 1절(v4.19) · `CLAUDE.md` 머리 버전 줄 + 카톡 절(v4.9 판정 글자 문장에 「메시지 글은 URL 을 뺀 글」) + 명령 절의 `recategorize_tips.py --ids` 한 줄 + 이력 1줄 · `AGENTS.md` 동기. 회귀 테스트 개수 표기 갱신.

### 2부 — 장부 보정 (1부 커밋·verifier 통과 뒤)
- 인스타 1행: 장부 `tips` 1행의 `title`·`url`·`url_key`·`memo`·`updated_at`.
- 노션 4행: `recategorize_tips.py --apply`(2행) → `recategorize_tips.py --ids=<3dc03276…>,<66cf7794…> --apply`(2행). 전체 record_id 는 실행 시 장부에서 읽는다.

### 바꾸면 안 되는 것
- 장부 스키마(user_version 3) · tips 열 의미 · 카테고리 값 목록 · 태그 이름·순서 · `classify` 규칙 표 · `_tag_text`.
- `kakao_ingest.py`·`telegram_tips_ingest.py` 의 흐름(이번 변경은 `kakao_parse`·`title_fetch` 안에서 끝난다).
- 다른 꿀팁 행(위 5행 외) · `d9ab26b5` · 영상 표 · launchd · `.env` · 운영 상태 파일.

## 확인 (먼저)

| # | 무엇 | 명령 | 기대 |
|---|---|---|---|
| 0-1 | 작업 트리·HEAD | `git status --porcelain` · `git log --oneline -1` | 비어 있음 · 지시서 커밋이 HEAD |
| 0-2 | 파라미터 가진 행 | `sqlite3 "file:data/library.db?mode=ro" "select count(*) from tips where url like '%igsh=%' or url like '%dlrf=%'"` | 1 |
| 0-3 | 인스타 행 | `… "select record_id, title, url from tips where url like '%instagram.com/reel/De_qY6Tz_KN%'"` | 1행 · title `Instagram` |
| 0-4 | 인스타 노트 없음 | Vault `AI 꿀팁/` 에서 `De_qY6Tz_KN` grep | 0건(있으면 2부 인스타 단계 멈춤 → 보고) |
| 0-5 | 재분류 미리보기 | `/opt/homebrew/bin/python3 scripts/recategorize_tips.py` | `rows: 2` · `eb8f2341`·`039e0964` |
| 0-6 | 회귀 | `scripts/run_all_tests.sh` | `RESULT: 16/16 통과` |

## 단계

### 1부 (implementer 1회차)
1. 「범위 · 1부」대로 코드·테스트 수정.
2. `scripts/run_all_tests.sh` → `RESULT: 16/16 통과`(종 수는 그대로, 각 테스트 개수만 늘어남).
3. 읽기 전용 점검 — 장부 쓰기 없음:
   - `recategorize_tips.py` dry-run → `rows: 2`(1부 전과 같다 — 규칙 값 판단은 `classify(url, title)` 이라 이번 변경과 무관해야 한다).
   - `recategorize_tips.py --ids=<3dc03276 전체 id>,<66cf7794 전체 id>` dry-run → `rows: 4` · `forced: 2` · 바뀌는 값이 위 표의 「기대」와 같음 · `d9ab26b5` 없음.
   - `python3 -c` 로 `url_key('https://www.instagram.com/reel/De_qY6Tz_KN/?dlrf=x')` == `url_key('https://www.instagram.com/reel/De_qY6Tz_KN/?igsh=y')` 출력.
4. 문서 갱신 → 커밋 1개 `[CC-1104-B] v4.19 …`(지시서 커밋과 별개). push 하지 않는다.

### 2부 (implementer 2회차 — verifier 통과 뒤, 11-04 17:49 까지)
시간: 매시 **분 21~49** · `pgrep -f "scheduler.js|wiki_ingest.py|sync_obsidian.py"` 없음. 17:25~17:50 은 하지 않는다.

5. 장부 백업: `sqlite3 data/library.db ".backup data/library.db.bak.manual-20261104b"`.
6. 인스타 행(0-4 가 0건일 때만): 새 값은 코드로 계산한다 — `clean_url(옛 url)`, `url_key(그 값)`, `guess_meta(새 url, 새 url)` 의 `title`·`memo`(기대: `인스타 릴스 (제목 미확인)` · `원문 확인 필요`). 한 트랜잭션에서
   `UPDATE tips SET title=?, url=?, url_key=?, memo=?, updated_at=<scheduler 와 같은 ISO 형식 UTC> WHERE record_id=? AND title='Instagram' AND url=<옛 url>` → `changes()` = 1 이 아니면 ROLLBACK 하고 멈춤.
7. `recategorize_tips.py --apply` → `rows: 2`.
8. `recategorize_tips.py --ids=<3dc03276 전체 id>,<66cf7794 전체 id> --apply` → `rows: 2` · `forced: 2`.
9. 사후 확인:
   - `sqlite3 "file:…?mode=ro" "pragma integrity_check"` → `ok`.
   - `scripts/verify_library.py` → `✅ 검증 통과`.
   - `recategorize_tips.py` dry-run 과 `--ids=…` dry-run → 둘 다 `rows: 0`.
   - 위 5행 조회: 표의 「기대」 · 인스타 행 새 값 · `d9ab26b5` 그대로.
   - `sync_obsidian.py --dry-run` → `tips_added: 1`(인스타 노트는 18:00 실행이 만든다) · `sheet_mirror.py --dry-run` → 꿀팁 5.
10. 장부·노트 변경은 커밋 대상이 아니다(`data/`·Vault 는 레포 밖·gitignore). 2부는 커밋하지 않는다.

## 기준표 (verifier)

| # | 기준 |
|---|---|
| 1 | 1부 diff 가 「1부 — 바꿀 파일」 안에서만 · 「바꾸면 안 되는 것」 무변경(`classify` 규칙 표·`_tag_text`·카테고리·태그 목록 diff 0) |
| 2 | `guess_meta` 판정 글자에 URL 이 없다 · 사람이 쓴 「노션」 글은 여전히 `Notion` 태그 (테스트 a·b) |
| 3 | `igsh`·`dlrf` 제거 · 같은 릴스 두 공유 링크 같은 `url_key` (테스트 c) · 장부의 다른 행 `url_key` 영향 0(0-2 = 1) |
| 4 | 인스타 추정 제목·메모 (테스트 d) · 「Instagram」·「Login • Instagram」 `bad_title` |
| 5 | `--ids` 동작·옵션 없을 때 무변경 · 없는 id 쓰기 0 (테스트) |
| 6 | `scripts/run_all_tests.sh` → `RESULT: 16/16 통과` |
| 7 | 단계 3 dry-run 값이 지시서 기대와 같다 |
| 8 | README 1행 + 1절 · CLAUDE.md 버전·카톡 절·명령·이력 · AGENTS.md 동기 · `README.html` 없음 · 공개 레포 규칙(개인 절대경로·맥 이름·`.env` 값·chat id 없음) |
| 9 | (2부) 백업 파일 존재 · 단계 6 `changes()` = 1 · 단계 9 전부 기대값 · 장부 쓰기 시각이 창 안 · 17:49 이전 |

## 하지 말 것
- `classify`·`_tag_text`·태그 규칙 표를 고쳐 노션을 따로 다루기(이번 고침은 「메시지에서 URL 빼기」 하나다).
- 인스타 주소 쿼리를 통째로 지우기(이름을 정한 두 파라미터만).
- 장부를 손으로 고칠 때 `INSERT OR REPLACE`·조건 없는 `UPDATE` · 5행 밖 행 수정 · `retitle_tips.py` 로 인스타 행 처리(노트가 아직 없어 그 도구의 전제와 다르다).
- 텔레그램 시험 발송 · 시트 `--full` · `sync_obsidian`·`wiki_ingest` 실제 실행(18:00 실행이 한다) · push.

## 롤백
- 1부: `git revert <1부 커밋>`.
- 2부: 데몬이 돌지 않는 창에서 `data/library.db.bak.manual-20261104b` 로 되돌리기(`cp` 가 아니라 `sqlite3 data/library.db ".restore data/library.db.bak.manual-20261104b"`) + 재분류가 고친 노트는 `data/recategorize_backup/<시각>/` 에서 되돌린다.

## 범위 밖
- 카톡 메시지 글로 매긴 다른 옛 행 전수 조사(이번은 11-03 노션 4건만).
- 인스타 공개 게시물 제목을 로그인 없이 얻는 다른 방법(oEmbed 등 — 앱 토큰 필요).
- 입구 구분(카톡·텔레그램)을 장부에 남기기(스키마 변경).
