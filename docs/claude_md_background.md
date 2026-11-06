# CLAUDE.md 배경 — 규칙의 경위 · 실측 · 연혁

규칙의 정본은 `CLAUDE.md` 다. 이 파일은 왜 그 규칙이 생겼는지를 남긴다. 규칙과 이 파일이 다르면 `CLAUDE.md` 를 따른다.

<a id="bg-versions"></a>
## CLAUDE.md 머리 — 버전별 한 줄 요약

> v4.0: 노션을 뺐다. 원본 = 로컬 장부 `data/library.db`(SQLite), 읽는 곳 = Obsidian, 보는 곳 = 구글 시트(단방향 미러). 파이프라인에 노션 호출이 없다.
> v4.1: 장부 하루 1회 백업(`backup_library.py` → `data/backups/` + 구글 드라이브).
> v4.2: 실행 실패 알림 — 통째 실패(저장 0 · Skip 0 · 오류 ≥1)·치명적 오류는 그 자리에서, 못 보낸 알림·끝나지 못한 실행·빠진 정시 실행은 다음 실행이 알린다(`.run_state.json`).
> v4.3: 노션 해지(2026-10-12)에 따라 노션 모듈·`.env NOTION_*` 를 지웠다. 장부 ↔ Vault 대조는 `scripts/verify_library.py`.
> v4.4: 꿀팁 제목 보완 `scripts/retitle_tips.py` — 장부 `title`·`updated_at` + 노트 제자리 수정·파일명 변경 + Vault 링크 치환을 한 번에(dry-run 기본, 쓰기 전 백업).
> v4.5: Wiki 합성 결과 누적 — 장부 `wiki_extract`(user_version 2)에 소스별로 쌓고, `_wiki` 개념·엔티티·index 페이지는 매 실행 전체로 다시 그린다. 옛 소스는 `--backfill` 묶음 추출(하루 30회).
> v4.6-a: 신규 영상은 실제 영상(YouTube URL)으로 요약하고 같은 호출의 사실 신호로 코드가 등급(keep·exclude)을 매긴다. 장부 user_version 3(`videos.grade`·`quality`·`summarized_at`). `grade: exclude` 노트는 Wiki 합성·검색에서만 뺀다. 안 되면 설명란 요약으로 대체.
> v4.6-b: 설명란 요약 약 3,000편을 정시 실행마다 최대 5편 · 하루 20편씩 실제 영상(Gemini 3.5 Flash-Lite)으로 다시 요약(`lib/resummarize.js`, 신규 영상 분량 3시간 예약, 실패하면 기존 요약 유지). 노트는 요약 절만 제자리 교체(`sync_obsidian.py:refresh_changed_notes`), Wiki backfill 은 실제 영상 요약 노트만, 항목 0 `_wiki` 페이지는 안내 문구로.
> v4.7: Wiki 검색 화면 개편 — 처음 열면 전체 목록(필터·정렬은 브라우저에서), 토픽 다중 선택·종류·날짜·조회수·채널·요약 방식·꿀팁 분류 필터, 머리줄 정렬, 표/카드 보기, 비슷한 영상(저장 벡터), 지난 방문 뒤 새로 들어온 것, 엑셀 내려받기, 노트 전체 보기(`/api/wiki-note`). iRichGreen Design System 웹 계층 DS 1.1.23 을 따랐다(밝은 테마만).
> v4.8: 카톡 꿀팁 원문 제목 자동 조회 — 제목이 URL 추정인 신규 꿀팁만 `lib/title_fetch.py`(노션 공개 API · 유튜브 oEmbed · og:title)로 조회, 실패하면 추정 제목 그대로.
> v4.9: 꿀팁 분류 보정 — 노션 페이지 주소(`notion.site`·`notion.so`·`app.notion.com`)는 태그 판정에서 호스트를 빼고(「지식관리」 오분류), 한글 표기(「클로드」·「노션」·「제미나이」 등)도 같은 태그로(`lib/kakao_parse.classify`). 기존 꿀팁은 `scripts/recategorize_tips.py`(규칙이 매긴 행만 다시 매김 · 출처 `https://` 접두 정리 · 노트 제자리 수정)로 한 번 반영.
> v4.11: 재요약(3.5 Flash-Lite)은 5xx 를 영상 1편에 `RESUMMARY_MAX_5XX`(기본 1)회 받으면 재시도 없이 그 실행의 재요약을 멈춘다(10-14 00시 503 8회 = 약 13분). 그 영상은 `quality.resummary_5xx` +1, 3회면 건너뜀. 신규 영상 경로는 그대로 키 4개 × 2회.
> v4.13: 영상 하루 8시간을 모델별·키(프로젝트)별로 따로 센다(`.video_quota.json` `models`·`keys`) — 둘 다 넘지 않을 때만 요청, 찬 키는 다음 키로. PT 10-14 실측 키 4개 · 모델 2개 합계 약 10.4시간에 429 0건("전체 합계 8시간"이 아님). 재요약 신규 몫 예약 기본 3시간 → 0. 장부 무변경.
> v4.14: 토픽 분류 모델 2.5 Flash → 3.5 Flash-Lite(`lib/classifier.js`, `.env CLASSIFY_MODEL` 로 되돌림) — 신규 영상 1편의 2.5 Flash 요청 2회 → 1회. 비교 20편에서 영상당 토픽 4.4 → 2.5개(추상 토픽 과추천이 줄어듦, 대표님 결정 A안). 분류 응답 한글 청크 경계 깨짐(`chunks += c`) 수정. 장부 무변경.
> v4.15: 정시 실행을 `/usr/bin/caffeinate -i` 로 감싼다(`com.irichgreen.ytsummarizer` plist) — 실행 중 유휴 잠자기(배터리 설정 `sleep 1` = 1분)를 막는다. 덮개를 닫은 잠자기·이미 잠든 맥은 못 막는다(10-15 12시 실패 = 11:54 Clamshell Sleep). 레포 plist 원본 4개·`install-server.sh`·`install-scheduler.sh` sed 패턴을 10-16 이관 경로(`~/Dev`)로 맞췄다. 코드·장부 무변경.
> v4.16: 17:30 Wiki 인제스트(`com.irichgreen.wiki-ingest`)도 `/usr/bin/caffeinate -i` 로 감싼다(v4.15 와 같은 이유). `brew upgrade` 뒤 점검 순서를 「launchd 데몬」 절에 적었다(10-30 simdjson 업그레이드로 node 가 기동 즉시 죽어 정시 실행 2회가 로그 없이 빠진 사건). 코드·장부 무변경.
> v4.17: `computeGrade` 의 `not_ai` 제외를 「`ai_related=false` AND 토픽 분류 0개」로 좁혔다(v4.12 promo 의 AND 와 같은 방향). 신규는 분류 뒤 `regrade`, 재요약은 장부 `topics` 를 후보에 실어 넘긴다. 장부·프롬프트·스키마 무변경.

<a id="bg-files"></a>
### 핵심 파일 역할

| 파일 | 역할 |
|------|------|
| `scheduler.js` | 메인 오케스트레이터. YouTube API 조회, Gemini 요약, **로컬 장부 저장(v4.0, `lib/library.js`)**, Telegram 알림. launchd가 6시간 간격 실행. 노션 호출 없음. |
| `server.js` | HTTP 서버(포트 3000, `127.0.0.1` 전용). `index.html` 서빙 + SSE `/api/master-ingest`(scheduler.js 실행·실시간 로그) + Wiki 검색 API. v4.0 에서 노션 프록시·`/test-notion`·`/api/sync-obsidian` 제거. |
| `index.html` | 단일 페이지 웹 UI. 재생목록 관리, 마스터 인제스트 트리거, 처리 결과 테이블. |
| `sync_obsidian.py` | (v4.0) 장부 `data/library.db`(읽기 전용) → Obsidian 증분 동기화. 노션 호출 없음. 내부적으로 `wiki_ingest.py`와 연동. 고아 `.md` 격리 포함(아래 참조). `--dry-run` 으로 할 일만 센다. |
| `wiki_ingest.py` | Karpathy LLM Wiki 파이프라인. Obsidian 노트를 순회하며 Gemini로 엔티티·개념 추출 → (v4.5) 장부 `wiki_extract` 에 소스별 누적 → `_wiki/entities`·`concepts`·`index.md` 를 그 표 전체 + 현재 Vault 로 다시 그림(내용 같으면 안 씀). 아래 「Wiki 합성 결과 누적」. |
| `wiki_config.py` | Wiki 인제스트 설정 + Gemini 호출 래퍼. 4키 로테이션, RPD 20 추적(`.wiki_quota.json`), 429 RPD/RPM 분기, 5xx 백오프. |
| `legacy_scripts/` | (v4.0) 은퇴한 노션 전제 스크립트 보관(`migrate_classify.js`·`check_duplicates.py`·`cleanup_duplicates.py`·`fix_nfc_topics.js`·`notion_to_obsidian.js`). 실행 대상 아님 — `legacy_scripts/README.md`. |
| `playlists.json` | 33개 토픽 재생목록 목록. 분류기의 허용 토픽 소스이기도 함. gitignore 대상. |
| `scripts/clean_pending_queue.js` | (v2.5) 큐 중복 제거 + dead-letter 격리. 기본 dry-run, `--apply` 필요. |
| `scripts/test_scheduler_guards.js` | (v3.2.1) `scheduler.js` 의 캐시·재시도·배치 조회 회귀 테스트. `https.request` 를 가짜로 바꾸고 `require` 한다. (v4.2) 실행 실패 알림(판정·점검 문구·상태 파일·`sendTelegram` 반환값) 포함. |
| `kakao_ingest.py` | (v3.0 → v4.0) 카톡 CSV → 장부 `tips` 테이블. 기본 dry-run, `--apply` 필요. 중복 판정은 상태 파일이 아니라 **장부 tips 전량 + URL 정규화 키(`url_key`)**. 신규 행은 한 트랜잭션. 노션 호출 없음. (v4.8) 제목이 URL 추정인 신규 행만 원문 제목 조회(`lib/title_fetch.py`) — 장부 쓰기 전, 실패하면 추정 제목 그대로, `--no-lookup`. |
| `lib/kakao_parse.py` | (v3.0) URL 추출·트래킹 파라미터 제거·중복 키·규칙 기반 제목/카테고리 추정. 순수 함수, 네트워크 없음. (v4.8) `guess_meta(…, fetched_title)` · `title_src`(`message`·`github`·`guess`·`fetched`). (v4.9) 분류 규칙은 `classify(url, *texts)` 한 곳 — 노션 페이지 주소는 호스트를 빼고 판정, 한글 표기 별칭. |
| `lib/env_util.py` | (v4.0 3단계) `.env` 읽기(의존성 0). `kakao_ingest.py`·`sheet_mirror.py` 가 쓴다. |
| `sheet_mirror.py` | (v4.0 3단계) 장부 → 구글 시트 미러(보기 전용, 단방향). `updated_at` 워터마크로 변경분만, 200행씩 POST. `--dry-run`·`--full`·`--check`. 아래 "구글 시트 미러" 절. |
| `gas/sheet_mirror.gs` | (v4.0 3단계) 시트에 붙이는 Apps Script 웹앱(받는 쪽). 토큰 검사 · 탭 화이트리스트(영상·꿀팁) · 머리글 대조 · 수식 방지. 설치 순서는 파일 머리 주석. |
| `backup_library.py` | (v4.1) 장부 하루 1회 백업 → `data/backups/` + `.env LIBRARY_BACKUP_DIR`(구글 드라이브). 온라인 백업 API·무결성 검사·gzip·sha256 대조, 최신 7 + 주별 4 보관. 장부는 읽기 전용. `--dry-run`·`--status`·`--force`. 아래 "장부 백업" 절. |
| `scripts/test_backup_library.py` | (v4.1) 장부 백업 회귀 테스트. 임시 장부·임시 폴더(가짜 드라이브 경로 포함), 실제 장부·드라이브 무관. |
| `wiki.html` | Wiki 검색 화면. `server.js`와 `wiki_lan_server.js`가 같은 파일을 서빙한다. (v4.7) 처음 열면 전체 목록 — 필터(종류·토픽 다중·날짜·조회수·채널·요약 방식·꿀팁 분류·새로 들어온 것)·정렬·표/카드는 브라우저에서. 의미 검색·AI 답변·비슷한 영상·노트 전체 보기 패널·엑셀 내려받기(브라우저가 .xlsx 생성). DS 1.1.23 토큰(머리 CSS 변수). 상태는 URL 해시, 보기·새로 들어온 것은 localStorage. |
| `wiki_mcp.js` | 같은 코어를 Claude에 노출하는 stdio MCP(`search_wiki`, `read_note`). 웹 서버 없이 동작. |
| `wiki_lan_server.js` | (v3.2) 집 안 전용 읽기 전용 검색 서버(포트 3100). `WIKI_LAN_ALLOW_CIDR` 대역 + 루프백만 허용. |
| `scripts/test_wiki_search.js` | (v4.7) 검색 화면 API 회귀 테스트 — `lib/wiki_search.js` 네 함수 + `wiki_lan_server.js` 를 임시 포트(127.0.0.1, 대역 일부러 틀림 → fail-closed)로 띄워 경로 검사. 임시 인덱스·Vault, Gemini 는 가짜. |
| `scripts/verify_library.py` · `scripts/test_verify_library.py` | (v4.3) 장부 ↔ Vault 대조, 읽기 전용·네트워크 없음. Vault 영상·꿀팁 노트의 `notion_id`(프론트매터 안의 것만)가 전부 장부(`videos`·`videos_dup`·`tips`)에 있는지, `user_version`·`integrity_check`·video_id 중복·videos ≥ 1 을 본다. `RESULT_JSON` 한 줄, 통과 0 · 실패 1. 노션 해지 때 지운 `notion_to_sqlite.py --verify` 를 떼어 온 것. |
| `scripts/test_wiki_ingest.py` | (v4.5) wiki_ingest 누적·재렌더·실패 처리·backfill 상한·씨앗 + `migrate_library` 회귀 테스트. 임시 Vault·장부·상태 파일, Gemini 는 가짜(네트워크 0). |
| `lib/library.js` | (v4.0 2단계) Node 쪽 장부 헬퍼(`node:sqlite`). `openLibrary`(없으면 던짐·user_version 대조)·`allVideos`·`insertVideo`(같은 video_id 면 UNIQUE 로 던짐 · v4.6 `summarySrc`·`grade`·`quality`·`summarized_at`)·`addTopic`·`updateStats`. |
| `lib/video_summary.js` | (v4.6) 실제 영상 요약 — 요청 생성(`buildBody`)·응답 검사(`parseResponse`, 영상 토큰 0 = 실패)·등급 규칙(`computeGrade`)·하루 분량 누계(`.video_quota.json`)·대체 경로(`makeVideoSummarizer`). 아래 「실제 영상 요약·품질 필터」. |
| `scripts/test_video_summary.js` | (v4.6) `lib/video_summary.js` 회귀 테스트. 요청 함수는 가짜(네트워크 0), 상태 파일은 임시 폴더. |
| `lib/resummarize.js` | (v4.6-b) 기존분 재요약 — 후보 선정(`library.resummaryCandidates`)·`videos.list` 1회·요약기(`makeVideoSummarizer` 모델·`fallback:false`·`reserveSeconds`)·결과 분류(건너뜀·실패·중단)·장부 갱신. 아래 「기존분 재요약」. |
| `scripts/test_resummarize.js` | (v4.6-b) `lib/resummarize.js` + 장부 재요약 헬퍼 회귀 테스트. 임시 장부, 영상 조회·요약기는 가짜(네트워크 0). |
| `scripts/test_kakao_ingest.py` | (v4.0 2단계) `kakao_ingest.py` 회귀 테스트. 임시 장부·임시 CSV, 네트워크 0회(v4.8 제목 조회는 가짜 함수, 실제 함수 구간은 막힌 urlopen). |
| `scripts/test_sync_obsidian.py` | (v4.0 2단계) `sync_obsidian.py` 회귀 테스트. 임시 Vault·임시 장부, 하위 단계(재구성·인제스트·인덱스)는 가짜로 바꿔 실제 Vault 를 건드리지 않는다. |
| `scripts/test_sheet_mirror.py` · `scripts/fake_gas_server.js` | (v4.0 3단계) 시트 미러 회귀 테스트. 가짜 서버가 `gas/sheet_mirror.gs` 원본을 node `vm` 에 올리고 시트·302 리다이렉트를 흉내 낸다(127.0.0.1). 실제 구글 요청 0. |
| `scripts/test_build_wiki_index.py` | (v4.0 3단계) 재구성 2회차 쓰기 0 · 프론트매터 없는 파일 누적 방지 · 검색 인덱스 프론트매터 한정. 임시 Vault. |
