# AGENTS.md

> Claude 외 코딩 에이전트(Codex 등)용 사본이다. 내용은 `CLAUDE.md` 와 같고, 어긋나면 **`CLAUDE.md` 가 이긴다**.
> 갱신 방법(v4.0 3단계, 2026-10-12~): `CLAUDE.md` 를 고친 뒤 이 파일을 다시 만든다 — 이 머리글 + `CLAUDE.md` 4행부터 끝까지.
> (예전 이 파일 끝에 붙어 있던 v2.5 시절 「Imported Claude Cowork project instructions」 사본은 낡아서 뺐다. 프로젝트 지침 원본은 Cowork 프로젝트 설정에 있다.)

**현재 버전: v4.7** (2026-10-13) · 레포 경로: `<REPO_ROOT>` = `~/Documents/Claude/Projects/AI_Wiki_Pipeline` · GitHub `iRG-AI/AI_Wiki_Pipeline`

> v4.0: 노션을 뺐다. 원본 = 로컬 장부 `data/library.db`(SQLite), 읽는 곳 = Obsidian, 보는 곳 = 구글 시트(단방향 미러). 파이프라인에 노션 호출이 없다.
> v4.1: 장부 하루 1회 백업(`backup_library.py` → `data/backups/` + 구글 드라이브).
> v4.2: 실행 실패 알림 — 통째 실패(저장 0 · Skip 0 · 오류 ≥1)·치명적 오류는 그 자리에서, 못 보낸 알림·끝나지 못한 실행·빠진 정시 실행은 다음 실행이 알린다(`.run_state.json`).
> v4.3: 노션 해지(2026-10-12)에 따라 노션 모듈·`.env NOTION_*` 를 지웠다. 장부 ↔ Vault 대조는 `scripts/verify_library.py`.
> v4.4: 꿀팁 제목 보완 `scripts/retitle_tips.py` — 장부 `title`·`updated_at` + 노트 제자리 수정·파일명 변경 + Vault 링크 치환을 한 번에(dry-run 기본, 쓰기 전 백업).
> v4.5: Wiki 합성 결과 누적 — 장부 `wiki_extract`(user_version 2)에 소스별로 쌓고, `_wiki` 개념·엔티티·index 페이지는 매 실행 전체로 다시 그린다. 옛 소스는 `--backfill` 묶음 추출(하루 30회).
> v4.6-a: 신규 영상은 실제 영상(YouTube URL)으로 요약하고 같은 호출의 사실 신호로 코드가 등급(keep·exclude)을 매긴다. 장부 user_version 3(`videos.grade`·`quality`·`summarized_at`). `grade: exclude` 노트는 Wiki 합성·검색에서만 뺀다. 안 되면 설명란 요약으로 대체.
> v4.6-b: 설명란 요약 약 3,000편을 정시 실행마다 최대 5편 · 하루 20편씩 실제 영상(Gemini 3.5 Flash-Lite)으로 다시 요약(`lib/resummarize.js`, 신규 영상 분량 3시간 예약, 실패하면 기존 요약 유지). 노트는 요약 절만 제자리 교체(`sync_obsidian.py:refresh_changed_notes`), Wiki backfill 은 실제 영상 요약 노트만, 항목 0 `_wiki` 페이지는 안내 문구로.
> v4.7: Wiki 검색 화면 개편 — 처음 열면 전체 목록(필터·정렬은 브라우저에서), 토픽 다중 선택·종류·날짜·조회수·채널·요약 방식·꿀팁 분류 필터, 머리줄 정렬, 표/카드 보기, 비슷한 영상(저장 벡터), 지난 방문 뒤 새로 들어온 것, 엑셀 내려받기, 노트 전체 보기(`/api/wiki-note`). iRichGreen Design System 웹 계층 DS 1.1.23 을 따랐다(밝은 테마만).

> 2026-08-17에 `~/Documents/Claude/` → `~/Documents/Claude/Projects/` 로 이관했습니다.
> 이전 경로가 박힌 문서·스크립트를 발견하면 갱신 대상입니다.
> 구 백업: `~/Claude/Youtube_Notion_Grap_BACKUP_20260717`.
> 2026-10-12에 이름을 `Youtube_Notion_Grap`(GitHub `YouTube_Notion_Grab`) → `AI_Wiki_Pipeline`(폴더·GitHub 동일)으로 바꿨습니다. 옛 이름·경로가 박힌 문서·스크립트를 발견하면 갱신 대상입니다(`docs/tasks/` 의 옛 지시서·패치는 기록이라 그대로 둡니다).

## Commands

```bash
# 서버 (웹 UI + 마스터 인제스트 SSE + Wiki 검색, 127.0.0.1:3000)
node server.js

# 스케줄러 (수동 1회 실행)
node scheduler.js              # 마스터 인제스트 모드 (기본)
node scheduler.js --legacy     # 레거시 33개 재생목록 모드

# Obsidian 동기화 (원본 = 장부, 읽기 전용). --dry-run 은 Vault·장부를 하나도 쓰지 않고 할 일만 센다
/opt/homebrew/bin/python3 sync_obsidian.py             # 장부 → Obsidian .md 증분 동기화 + Wiki Ingest (영상 + AI 꿀팁)
/opt/homebrew/bin/python3 sync_obsidian.py --dry-run
/opt/homebrew/bin/python3 sync_obsidian.py --no-tips   # 꿀팁 동기화 제외 (YouTube 쪽만 진단할 때)
/opt/homebrew/bin/python3 build_obsidian_wiki.py       # MOC + 키워드 허브 파일 재구성 (내용 같은 파일은 쓰지 않는다)

# 구글 시트 미러 (v4.0 3단계, 보기 전용 단방향). .env 에 SHEET_MIRROR_URL 이 없으면 건너뛴다
/opt/homebrew/bin/python3 sheet_mirror.py --dry-run    # 보낼 건수만 (네트워크·장부 쓰기 0)
/opt/homebrew/bin/python3 sheet_mirror.py              # 변경분만 보냄 (스케줄러가 매 실행 자동 호출)
/opt/homebrew/bin/python3 sheet_mirror.py --full       # 두 탭을 비우고 전부 다시 (열이 바뀌었거나 시트가 어긋났을 때)
/opt/homebrew/bin/python3 sheet_mirror.py --check      # 시트 행 수 ↔ 장부 행 수 대조 (읽기만)

# 장부 백업 (v4.1) — 스케줄러가 매 실행 자동 호출, 오늘(KST) 것이 있으면 건너뛴다 → 실제로는 하루 1회
/opt/homebrew/bin/python3 backup_library.py --dry-run  # 만들 곳·지울 파일만 (쓰기 0)
/opt/homebrew/bin/python3 backup_library.py            # 오늘 백업이 없는 곳(로컬·드라이브)에만 만든다
/opt/homebrew/bin/python3 backup_library.py --status   # 두 곳의 개수·가장 최근 날짜 (읽기만)

# 카카오톡 → 장부 tips (스케줄러가 --apply --if-new 로 자동 호출)
/opt/homebrew/bin/python3 kakao_ingest.py                    # dry-run (기본). 생성될 행 표만 출력
/opt/homebrew/bin/python3 kakao_ingest.py --apply --limit=3  # 3건만 장부에 → 확인
/opt/homebrew/bin/python3 kakao_ingest.py --apply            # 전량
/opt/homebrew/bin/python3 kakao_ingest.py --apply --if-new   # 스케줄러 모드: 같은 CSV(mtime)면 장부 조회 없이 즉시 종료 (--force 로 무시)

# Karpathy LLM Wiki
python3 wiki_ingest.py              # 증분(미처리 소스) → backfill(하루 WIKI_BACKFILL_DAILY_MAX 회) → 페이지 재렌더 (launchd 17:30)
python3 wiki_ingest.py --no-backfill   # 증분 → 재렌더 (sync_obsidian 경로)
python3 wiki_ingest.py --render-only   # Gemini 호출 없이 wiki_extract 로 페이지만 다시 그림
python3 wiki_ingest.py --full       # 전체: 모든 소스 재분석 (backfill 안 함)
python3 wiki_ingest.py --limit=20   # 테스트: 20개만 처리 (backfill 안 함)
python3 wiki_ingest.py --seed-from-pages [--apply]   # (v4.5 1회) 옛 _wiki 페이지 항목 → wiki_extract 씨앗. 기본 dry-run

# 장부 스키마 올리기 (v4.6: user_version 1·2 → 3, 한 번에). 기본 dry-run. 옛 백업(v1·v2)을 복원했을 때도
/opt/homebrew/bin/python3 scripts/migrate_library.py [--apply] [--db=<경로>]

# 기존 영상 일괄 마이그레이션 — v4.0 에서 은퇴 (legacy_scripts/migrate_classify.js, 노션 전제라 그대로 돌지 않는다)

# 회귀 테스트 12종 — 네트워크 0회, 실제 장부·Vault·.env 무관 (데몬과 같은 인터프리터로)
/opt/homebrew/bin/node scripts/test_scheduler_guards.js      # 33/33  장부 캐시·재시도·배치 조회(길이·공개 상태)·시트 미러·장부 백업 훅·실행 실패 알림·요약 방식 저장·재요약 단계 무해
/opt/homebrew/bin/node scripts/test_video_summary.js         # 23/23  (v4.6) 실제 영상 요약 — 요청 모양·영상 토큰 0·대체 경로·403 연속·분량 상한·등급 · (v4.6-b) 모델별 thinking·대체 없음·예약·bad_summary 사유 (가짜 요청)
/opt/homebrew/bin/node scripts/test_resummarize.js           # 9/9    (v4.6-b) 기존분 재요약 — 후보·장부 갱신·stale·건너뜀/실패/중단·하루·실행 상한 (임시 장부, 가짜 요약기)
/opt/homebrew/bin/python3 scripts/test_verify_library.py     # 16/16  장부 ↔ Vault 대조 (임시 장부·Vault)
/opt/homebrew/bin/python3 scripts/test_retitle_tips.py       # 49/49  꿀팁 제목 보완 (임시 장부·Vault·백업 폴더)
/opt/homebrew/bin/python3 scripts/test_wiki_ingest.py        # 64/64  Wiki 추출 누적·재렌더·backfill(v4.6-b 영상 요약 소스만·stale)·씨앗·품질 제외·항목 0 안내 페이지 + 장부 스키마 이전 v1·v2 → v3 (가짜 Gemini)
/opt/homebrew/bin/python3 scripts/test_kakao_ingest.py       # 18/18  카톡 → 장부 tips
/opt/homebrew/bin/python3 scripts/test_sync_obsidian.py      # 32/32  장부 → Vault (임시 Vault) · (v4.6-b) 재요약 노트 요약 절 제자리 교체
/opt/homebrew/bin/python3 scripts/test_sheet_mirror.py       # 45/45  시트 미러 (가짜 Apps Script 서버가 gas/sheet_mirror.gs 를 그대로 실행)
/opt/homebrew/bin/python3 scripts/test_build_wiki_index.py   # 15/15  재구성 같은 내용 안 쓰기 · 검색 인덱스 프론트매터 한정 · grade: exclude 제외 · (v4.7) 화면 필터용 메타
/opt/homebrew/bin/node scripts/test_wiki_search.js           # 34/34  (v4.7) 검색 화면 API — 전체 목록·전체 점수·비슷한 노트·노트 본문 + 집 안 서버 경로 (임시 인덱스·Vault, 가짜 Gemini)
/opt/homebrew/bin/python3 scripts/test_backup_library.py     # 50/50  장부 백업 (임시 폴더 — 하루 1회 · 보관 규칙 · 드라이브 빠짐)

# 대기 큐 정리 (중복 제거 + dead-letter 격리) — 기본 dry-run
node scripts/clean_pending_queue.js
node scripts/clean_pending_queue.js --apply

# 장부 ↔ Vault 대조 (읽기 전용, 네트워크 없음) — 통과 0 · 실패 1, 마지막 RESULT_JSON 의 vault_missing·tips_missing 0
/opt/homebrew/bin/python3 scripts/verify_library.py

# 꿀팁 제목 보완 (v4.4) — CSV record_id,old_title,new_title. 기본 dry-run, --apply 는 정시 실행 창(매시 50분~다음 시 20분) 밖에서
/opt/homebrew/bin/python3 scripts/retitle_tips.py <CSV>
/opt/homebrew/bin/python3 scripts/retitle_tips.py <CSV> --apply

# launchd 제어 (6시간 자동 실행)
launchctl start com.irichgreen.ytsummarizer
launchctl stop com.irichgreen.ytsummarizer

# YouTube OAuth 토큰 재발급 (1회성) — 반드시 「타이쿤안」 채널 선택
node oauth_setup.js

# OAuth 연결 확인 (토큰 발급 여부만 확인 — 계정 일치는 확인 못 함)
node -e "require('./lib/youtube_oauth').getAccessToken().then(t => console.log('✅', t.slice(0,20))).catch(e => console.error('❌', e.message))"

# 상태 스냅샷 (진단 1순위)
cat .quota_state.json
cat .run_state.json            # (v4.2) 직전 실행이 어떻게 끝났나 — outcome·reason·notified·pending
node -e "for(const f of ['pending_playlist_adds.json','pending_playlist_adds.dead.json'])console.log(f, JSON.parse(require('fs').readFileSync(f)).length)"
# Wiki 검색 (v3.2) — 입구는 여럿, 엔진은 lib/wiki_search.js 하나
#   이 맥    http://localhost:3000/wiki          server.js (127.0.0.1 전용)
#   가족 PC  http://<맥이름>.local:3100/wiki     wiki_lan_server.js (집 대역 전용·읽기 전용)
#   Claude   MCP wiki-search                     wiki_mcp.js (stdio, 서버 불필요)
python3 build_search_index.py                    # 검색 인덱스 증분 갱신 (sync_obsidian.py 가 변경 시 자동 호출)
launchctl list | grep irichgreen.wiki-lan        # 집 안 전용 서버 상태
tail -20 ~/Library/Logs/irichgreen/wiki-lan.log  # 기동·차단 기록
```

### OAuth 계정 일치 검증 (1유닛, 재발급 후 필수)

토큰이 발급되는 것과 **33개 재생목록을 소유한 계정인지**는 별개입니다.
재발급 직후 반드시 아래를 돌려 `✅ 일치`를 확인하세요.

```bash
cd <REPO_ROOT> && node -e "
const yt=require('./lib/youtube_oauth');
(async()=>{const t=await yt.getAccessToken();
const j=await(await fetch('https://www.googleapis.com/youtube/v3/playlists?part=snippet&mine=true&maxResults=50',{headers:{Authorization:'Bearer '+t}})).json();
if(j.error)return console.log('ERR',j.error.errors?.[0]?.reason);
const mine=new Map((j.items||[]).map(x=>[x.id,x.snippet]));
const want=require('./playlists.json').map(p=>(p.url.match(/list=([^&]+)/)||[])[1]).filter(Boolean);
const hit=want.filter(x=>mine.has(x));
console.log('채널:',[...new Set([...mine.values()].map(s=>s.channelTitle))].join(','),'| 일치',hit.length+'/'+want.length);
console.log(hit.length===want.length?'✅ 일치':'❌ 불일치 — 재발급 필요');})();"
```

## 🚨 보안 및 안전 최우선 개발 원칙 (Security & Safety Guidelines)

이 프로젝트에서 코드를 설계하고 수정할 때 다음 **보안 및 예외 안전성 원칙을 최우선(1순위)**으로 고려해야 합니다. 단순 기능 구현보다 플랫폼의 보안 정책 준수와 사용자 계정 보호가 먼저입니다.

1. **플랫폼 보안 규정 준수 및 계정 보호 (Anti-Abuse)**:
   - 구글(Google/YouTube), 노션 등 외부 API 호출 시, 인증 만료(401)나 권한 거부/프로젝트 정지(403 Forbidden, Suspended 등) 상태가 감지되면 **추가적인 연쇄 요청을 멈추고 즉시 프로세스를 강제 종료(Exit)**해야 합니다.
   - 단시간 내에 실패하는 요청을 루프 형태로 난사하는 행위는 구글 보안 봇에 의해 계정이 도용/어뷰징된 것으로 오인받아 **연쇄 계정 정지(Suspension)**를 유발하므로 절대 금지합니다.
2. **견고한 예외 처리 및 스케줄러 안전장치 (Fail-Safe & Backoff)**:
   - 일시적인 오류(Rate Limit 429, 서버 오류 5xx)에 대해 재시도할 때는, 3초 고정 대기 대신 점진적으로 대기 시간을 늘리는 **지수 백오프(Exponential Backoff)** 알고리즘을 필수 적용합니다.
   - 무한 루프나 과도한 재시도를 원천 차단하고, 최대 시도 횟수 초과 시 안전하게 실패를 기록한 후 중단해야 합니다.
3. **사용자 환경 자산 격리 가이드**:
   - 개인 메인 계정의 정지를 예방하기 위해, 개발 및 테스트에는 항상 별도의 테스트용 구글 계정과 GCP 프로젝트를 생성하여 격리된 채널을 통해 연동하도록 권고합니다.

## 아키텍처 개요

### 전체 파이프라인

```
YouTube "AI 영상목록" (마스터 모드)
    → scheduler.js:processMasterIngest()
    → lib/classifier.js:classifyTopics()  [Gemini 2.5 Flash, 토픽 1~5개]
    → saveToLibrary()                     [로컬 장부 data/library.db 저장 — lib/library.js]
    → runResummary()                      [(v4.6-b) 기존분 재요약 — lib/resummarize.js, 실행당 최대 5편]
    → lib/youtube_oauth.js:addToPlaylist() [토픽별 YouTube 재생목록 추가]
    → kakao_ingest.py --apply --if-new    [카톡 CSV → 장부 tips]
    → sheet_mirror.py                     [장부 변경분 → 구글 시트 (보기용)]
    → backup_library.py                   [장부 하루 1회 백업 → data/backups/ + 구글 드라이브]
    → sync_obsidian.py                    [장부 → Obsidian .md 파일 생성/갱신]
    → wiki_ingest.py                      [Gemini 2.5 Flash, 엔티티/개념 Wiki 페이지 합성]
    → build_obsidian_wiki.py              [MOC + 키워드 허브 재구성]
```

레거시 모드(`--legacy`)는 33개 토픽 재생목록을 순회하며 동일한 Gemini 요약 → 장부 저장 흐름을 수행합니다.

### 핵심 파일 역할

| 파일 | 역할 |
|------|------|
| `scheduler.js` | 메인 오케스트레이터. YouTube API 조회, Gemini 요약, **로컬 장부 저장(v4.0, `lib/library.js`)**, Telegram 알림. launchd가 6시간 간격 실행. 노션 호출 없음. |
| `server.js` | HTTP 서버(포트 3000, `127.0.0.1` 전용). `index.html` 서빙 + SSE `/api/master-ingest`(scheduler.js 실행·실시간 로그) + Wiki 검색 API. v4.0 에서 노션 프록시·`/test-notion`·`/api/sync-obsidian` 제거. |
| `index.html` | 단일 페이지 웹 UI. 재생목록 관리, 마스터 인제스트 트리거, 처리 결과 테이블. |
| `lib/classifier.js` | Gemini 기반 토픽 분류기. `playlists.json`의 토픽 목록만 허용(allowedSet 필터). 신뢰도 0.6 미만이면 YouTube 추가 건너뜀. |
| `lib/youtube_oauth.js` | YouTube OAuth2 쓰기 전용. access_token 메모리 캐시(50분), 일일 quota 추적(`.quota_state.json`), 호출 간 200ms rate limit. |
| `sync_obsidian.py` | (v4.0) 장부 `data/library.db`(읽기 전용) → Obsidian 증분 동기화. 노션 호출 없음. 내부적으로 `wiki_ingest.py`와 연동. 고아 `.md` 격리 포함(아래 참조). `--dry-run` 으로 할 일만 센다. |
| `wiki_ingest.py` | Karpathy LLM Wiki 파이프라인. Obsidian 노트를 순회하며 Gemini로 엔티티·개념 추출 → (v4.5) 장부 `wiki_extract` 에 소스별 누적 → `_wiki/entities`·`concepts`·`index.md` 를 그 표 전체 + 현재 Vault 로 다시 그림(내용 같으면 안 씀). 아래 「Wiki 합성 결과 누적」. |
| `scripts/migrate_library.py` | (v4.5·v4.6) 장부 스키마 이전(user_version 1·2 → 3). 기본 dry-run, `--apply` 는 온라인 백업 `<장부>.bak.v<현재>-<시각>` 뒤 한 트랜잭션으로 단계별 `ALTER TABLE ADD COLUMN`(`ADD_COLUMNS`) + 스키마 실행(전부 `IF NOT EXISTS`) → 버전·무결성·행 수·새 표·새 열 확인. 열 추가는 `updated_at` 을 안 건드린다(시트 재전송 없음). `--db=` 로 복원본에도. |
| `wiki_config.py` | Wiki 인제스트 설정 + Gemini 호출 래퍼. 4키 로테이션, RPD 20 추적(`.wiki_quota.json`), 429 RPD/RPM 분기, 5xx 백오프. |
| `build_obsidian_wiki.py` | 키워드별 허브 파일 27개 자동 생성(`_MOC/Claude.md` 등) + MOC 재구성. (v4.0) `write_if_changed()` — 내용이 같은 파일은 쓰지 않는다. |
| `legacy_scripts/` | (v4.0) 은퇴한 노션 전제 스크립트 보관(`migrate_classify.js`·`check_duplicates.py`·`cleanup_duplicates.py`·`fix_nfc_topics.js`·`notion_to_obsidian.js`). 실행 대상 아님 — `legacy_scripts/README.md`. |
| `playlists.json` | 33개 토픽 재생목록 목록. 분류기의 허용 토픽 소스이기도 함. gitignore 대상. |
| `scripts/clean_pending_queue.js` | (v2.5) 큐 중복 제거 + dead-letter 격리. 기본 dry-run, `--apply` 필요. |
| `scripts/test_scheduler_guards.js` | (v3.2.1) `scheduler.js` 의 캐시·재시도·배치 조회 회귀 테스트. `https.request` 를 가짜로 바꾸고 `require` 한다. (v4.2) 실행 실패 알림(판정·점검 문구·상태 파일·`sendTelegram` 반환값) 포함. |
| `kakao_ingest.py` | (v3.0 → v4.0) 카톡 CSV → 장부 `tips` 테이블. 기본 dry-run, `--apply` 필요. 중복 판정은 상태 파일이 아니라 **장부 tips 전량 + URL 정규화 키(`url_key`)**. 신규 행은 한 트랜잭션. 노션 호출 없음. |
| `lib/kakao_parse.py` | (v3.0) URL 추출·트래킹 파라미터 제거·중복 키·규칙 기반 제목/카테고리 추정. 순수 함수, 네트워크 없음. |
| `lib/env_util.py` | (v4.0 3단계) `.env` 읽기(의존성 0). `kakao_ingest.py`·`sheet_mirror.py` 가 쓴다. |
| `sheet_mirror.py` | (v4.0 3단계) 장부 → 구글 시트 미러(보기 전용, 단방향). `updated_at` 워터마크로 변경분만, 200행씩 POST. `--dry-run`·`--full`·`--check`. 아래 "구글 시트 미러" 절. |
| `gas/sheet_mirror.gs` | (v4.0 3단계) 시트에 붙이는 Apps Script 웹앱(받는 쪽). 토큰 검사 · 탭 화이트리스트(영상·꿀팁) · 머리글 대조 · 수식 방지. 설치 순서는 파일 머리 주석. |
| `backup_library.py` | (v4.1) 장부 하루 1회 백업 → `data/backups/` + `.env LIBRARY_BACKUP_DIR`(구글 드라이브). 온라인 백업 API·무결성 검사·gzip·sha256 대조, 최신 7 + 주별 4 보관. 장부는 읽기 전용. `--dry-run`·`--status`·`--force`. 아래 "장부 백업" 절. |
| `scripts/test_backup_library.py` | (v4.1) 장부 백업 회귀 테스트. 임시 장부·임시 폴더(가짜 드라이브 경로 포함), 실제 장부·드라이브 무관. |
| `wiki.html` | Wiki 검색 화면. `server.js`와 `wiki_lan_server.js`가 같은 파일을 서빙한다. (v4.7) 처음 열면 전체 목록 — 필터(종류·토픽 다중·날짜·조회수·채널·요약 방식·꿀팁 분류·새로 들어온 것)·정렬·표/카드는 브라우저에서. 의미 검색·AI 답변·비슷한 영상·노트 전체 보기 패널·엑셀 내려받기(브라우저가 .xlsx 생성). DS 1.1.23 토큰(머리 CSS 변수). 상태는 URL 해시, 보기·새로 들어온 것은 localStorage. |
| `lib/wiki_search.js` | 검색 코어(의존성 0). `wiki_index.json`+`wiki_index.vec`(768차원) 로드, 임베딩 코사인 + 메타 부스트, 임베딩 실패 시 키워드 폴백, Gemini 401/403 래치. (v4.7) `listPayload`(전체 목록, gzip·ETag 캐시) · `scoreAll`(모든 노트 점수) · `similar`(저장 벡터끼리, Gemini 호출 없음) · `noteById`(id 로만, `readNote` 경로 검사). `WIKI_SEARCH_DIR`·`WIKI_VAULT` 는 테스트 전용. |
| `wiki_mcp.js` | 같은 코어를 Claude에 노출하는 stdio MCP(`search_wiki`, `read_note`). 웹 서버 없이 동작. |
| `build_search_index.py` | Obsidian 노트 → `gemini-embedding-001` → 인덱스 증분 빌드. `sync_obsidian.py`가 신규·변경·고아 격리·`--rebuild` 시 호출. (v4.0) `notion_id`·제목·태그는 맨 앞 프론트매터에서만 읽는다. (v4.7) 화면 필터용 `kind`·`subscriber_count`·`summary_src`·`link_url`·`category`·`importance`·`keywords` — 매 빌드 프론트매터에서 다시 읽고 임베딩 hash 와 무관. |
| `wiki_lan_server.js` | (v3.2) 집 안 전용 읽기 전용 검색 서버(포트 3100). `WIKI_LAN_ALLOW_CIDR` 대역 + 루프백만 허용. |
| `scripts/test_wiki_search.js` | (v4.7) 검색 화면 API 회귀 테스트 — `lib/wiki_search.js` 네 함수 + `wiki_lan_server.js` 를 임시 포트(127.0.0.1, 대역 일부러 틀림 → fail-closed)로 띄워 경로 검사. 임시 인덱스·Vault, Gemini 는 가짜. |
| `scripts/verify_library.py` · `scripts/test_verify_library.py` | (v4.3) 장부 ↔ Vault 대조, 읽기 전용·네트워크 없음. Vault 영상·꿀팁 노트의 `notion_id`(프론트매터 안의 것만)가 전부 장부(`videos`·`videos_dup`·`tips`)에 있는지, `user_version`·`integrity_check`·video_id 중복·videos ≥ 1 을 본다. `RESULT_JSON` 한 줄, 통과 0 · 실패 1. 노션 해지 때 지운 `notion_to_sqlite.py --verify` 를 떼어 온 것. |
| `scripts/test_wiki_ingest.py` | (v4.5) wiki_ingest 누적·재렌더·실패 처리·backfill 상한·씨앗 + `migrate_library` 회귀 테스트. 임시 Vault·장부·상태 파일, Gemini 는 가짜(네트워크 0). |
| `scripts/retitle_tips.py` · `scripts/test_retitle_tips.py` | (v4.4) 꿀팁 제목 보완. CSV(`record_id,old_title,new_title`) → 장부 `title`·`updated_at`(+ 카톡 자동 메모 비움) · 「AI 꿀팁」 노트 제자리 수정·파일명 변경 · Vault `[[링크]]` 치환 → `build_obsidian_wiki`·`build_search_index`. 기본 dry-run, 검증 전부 통과 뒤에만 쓰고 쓰기 전 `data/retitle_backup/<시각>/` 에 장부·파일 백업. 장부 조건은 `record_id` + 옛 제목(같은 CSV 재실행은 멈춤). 종료 0 · 1 · 2(무변경). |
| `lib/library_schema.sql` · `lib/library_db.py` | (v4.0) 로컬 원본 장부 스키마(원본은 `.sql` 하나) · Python 헬퍼(`open_existing()` = 있는 장부만 연다, 없으면 만들지 않고 던진다). |
| `lib/library.js` | (v4.0 2단계) Node 쪽 장부 헬퍼(`node:sqlite`). `openLibrary`(없으면 던짐·user_version 대조)·`allVideos`·`insertVideo`(같은 video_id 면 UNIQUE 로 던짐 · v4.6 `summarySrc`·`grade`·`quality`·`summarized_at`)·`addTopic`·`updateStats`. |
| `lib/video_summary.js` | (v4.6) 실제 영상 요약 — 요청 생성(`buildBody`)·응답 검사(`parseResponse`, 영상 토큰 0 = 실패)·등급 규칙(`computeGrade`)·하루 분량 누계(`.video_quota.json`)·대체 경로(`makeVideoSummarizer`). 아래 「실제 영상 요약·품질 필터」. |
| `scripts/test_video_summary.js` | (v4.6) `lib/video_summary.js` 회귀 테스트. 요청 함수는 가짜(네트워크 0), 상태 파일은 임시 폴더. |
| `lib/resummarize.js` | (v4.6-b) 기존분 재요약 — 후보 선정(`library.resummaryCandidates`)·`videos.list` 1회·요약기(`makeVideoSummarizer` 모델·`fallback:false`·`reserveSeconds`)·결과 분류(건너뜀·실패·중단)·장부 갱신. 아래 「기존분 재요약」. |
| `scripts/test_resummarize.js` | (v4.6-b) `lib/resummarize.js` + 장부 재요약 헬퍼 회귀 테스트. 임시 장부, 영상 조회·요약기는 가짜(네트워크 0). |
| `scripts/test_kakao_ingest.py` | (v4.0 2단계) `kakao_ingest.py` 회귀 테스트. 임시 장부·임시 CSV, 네트워크 0회. |
| `scripts/test_sync_obsidian.py` | (v4.0 2단계) `sync_obsidian.py` 회귀 테스트. 임시 Vault·임시 장부, 하위 단계(재구성·인제스트·인덱스)는 가짜로 바꿔 실제 Vault 를 건드리지 않는다. |
| `scripts/test_sheet_mirror.py` · `scripts/fake_gas_server.js` | (v4.0 3단계) 시트 미러 회귀 테스트. 가짜 서버가 `gas/sheet_mirror.gs` 원본을 node `vm` 에 올리고 시트·302 리다이렉트를 흉내 낸다(127.0.0.1). 실제 구글 요청 0. |
| `scripts/test_build_wiki_index.py` | (v4.0 3단계) 재구성 2회차 쓰기 0 · 프론트매터 없는 파일 누적 방지 · 검색 인덱스 프론트매터 한정. 임시 Vault. |

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

```
카톡 '나와의 채팅' 내보내기 (수동, 월 1회) → ~/Downloads/KakaoTalk_Chat_*.csv
  → scheduler.js (YouTube 인제스트 완료 후) → kakao_ingest.py --apply --if-new
       [최신 CSV mtime 비교(.kakao_state.json) → URL 정규화 → 장부 tips 전량 url_key 대조 → 신규만 한 트랜잭션 INSERT → RESULT_JSON]
  → 장부 data/library.db 의 tips 테이블
  → sheet_mirror.py → 구글 시트 '꿀팁' 탭 (보기용)
  → sync_obsidian.py:sync_tips()  [VAULT/AI 꿀팁/*.md, 신규만]
  → wiki_ingest.py / build_obsidian_wiki.py  (기존 그대로 공유 — 합성 로직 두 벌 만들지 않는다)
```

- `.env`: `KAKAO_EXPORT_DIR`(읽기는 `lib/env_util.py`). 노션을 부르지 않는다.
- 꿀팁 기본값(노션 시절과 같음): 제목이 비면 URL, 카테고리 `기타`, 상태 `미확인`, 중요도 `중`. 카테고리 값 목록은 `lib/kakao_parse.py` 상단. `tags` 는 JSON 배열, `source` 는 **호스트만**(`github.com`).
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
- **제목은 추정이다.** `kakao_ingest` 는 링크를 열지 않고 URL 로 제목을 만든다(「유튜브 영상 (제목 미확인)」·「노션 자료 (…)」·URL 마지막 조각, 메모 「원문 확인 필요」). 고칠 때는 장부를 직접 UPDATE 하지 말고 `scripts/retitle_tips.py` 를 쓴다 — `sync_tips` 는 기존 노트를 다시 쓰지 않으므로 장부만 고치면 노트·파일명·링크가 옛 제목으로 남는다. 새 제목에 `|`·`[[`·`]]` 금지(Obsidian 링크 별칭을 깨뜨림, 스크립트가 거부).

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
   │                                        └ JSON {summary_md, signals{promo_main, generic, ai_related, has_demo, sponsored, reason}}
   │                                        └ 등급 = 코드 규칙 → 장부 summary_src 'video' · grade keep|exclude · quality(JSON)
   └ 그 밖·실패 ─▶ 기존 설명란 요약(geminiSummarize) → summary_src 'app' · grade NULL(미판정)
```

- 모듈은 `lib/video_summary.js`, 호출 자리는 `scheduler.js:processMasterIngest` 하나(레거시 재생목록 순회 경로는 설명란 요약 그대로).
- **등급은 모델이 아니라 코드가 매긴다** — `computeGrade`: `promo_main`(제작자 **자신의** 강의·컨설팅·커뮤니티·상품 판매가 주목적) · `generic`(구체 정보 없는 일반론) · `!ai_related` 중 하나라도면 `exclude`. 유료 광고·협찬(`sponsored`)·시연(`has_demo`)은 기록만 하고 등급에 안 쓴다. 모델에게 A/B/C 를 매기게 했더니 판매 영상에도 A 를 줬다(10-12 시험) — 모델 등급으로 되돌리지 말 것. `promo_main` 정의를 넓히지 말 것 — "판매·홍보가 주목적"으로 두면 다른 회사 도구를 시연하는 협찬 영상까지 제외됐다(10-13 시험).
- **영상 토큰 0 이면 실패다.** 삭제된 영상은 200 + 영상 토큰 0 + 지어낸 답을 돌려준다(10-13 시험). `parseResponse` 의 이 검사를 빼지 말 것.
- 공개(`public`)가 아닌 영상은 영상 입력을 시도하지 않는다(일부공개 = 403 PERMISSION_DENIED). 영상 입력 403 은 영상 단위라 그 영상만 대체하고, **연속 2회면 그 실행에서 영상 입력을 끈다**(403 난사 방지). 대체 요약(같은 키)도 403 이면 `geminiSummarize` 의 기존 즉시 종료 경로를 탄다.
- 429·5xx·네트워크 오류는 키를 돌려 재시도(키 4개 × 2회 상한) 후 대체. 400 등 그 밖의 오류는 재시도 없이 대체.
- 무료 등급 영상 입력은 하루 8시간 분량 상한(미리보기 기능). `.video_quota.json` `{date(PT), seconds, calls}` 에 시도한 영상의 (앞 30분 기준) 초를 센다 — 실패 요청도 센다. `VIDEO_DAILY_SECONDS`(기본 28800)를 넘을 영상은 대체.
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

- **신규 영상이 먼저다.** 실행당 `RESUMMARY_PER_RUN`(5) · 하루(PT) `RESUMMARY_DAILY_MAX`(20) · 하루 영상 분량 8시간 중 `RESUMMARY_RESERVE_SECONDS`(10800)는 신규 몫으로 남긴다(PT 하루 안 실행 순서 18→00→06→12시 — 앞 실행이 다 쓰면 12시 신규가 설명란 요약으로 밀린다). 분량 누계는 신규와 같은 `.video_quota.json`.
- 모델은 `RESUMMARY_MODEL`(기본 `gemini-3.5-flash-lite`). 무료 한도가 모델별로 따로라 본 파이프라인의 2.5 Flash 하루 한도를 먹지 않는다. **3.x 모델은 `thinkingBudget` 을 400 으로 거절한다** — `video_summary.thinkingConfigFor` 가 2.x 는 `thinkingBudget: 0`, 그 밖은 `thinkingLevel: 'minimal'`. 2.5 Flash 의 `thinkingBudget: 0` 은 그대로 둘 것.
- **실패하면 설명란 요약으로 대체하지 않는다**(기존 요약 유지). 목록에 없음(`gone`)·공개 아님·길이 모름·영상 토큰 0 → `quality.resummary_skip`(다시 안 함). `bad_json`·`bad_signals`·`bad_summary`·`video_403`·그 밖 4xx → `resummary_fail` +1, 2회면 건너뜀. 429·5xx·네트워크·하루 분량·`video_403_repeated`·`VIDEO_SUMMARY=false` → 그 실행 재요약 중단. 건너뜀·실패 표시는 시트에 안 보이는 `quality` 만 바꾸므로 `updated_at` 을 안 건드린다.
- 성공(`lib/library.js:updateResummary`, 한 트랜잭션): `summary`·`summary_src='video'`·`grade`·`quality`(+`resummary:true`·`resummary_day`)·`summarized_at`·`updated_at` + 그 소스의 `wiki_extract` → `status='stale'`, `attempts=0`(`updated_at` 은 그대로 — 렌더 결정성). 이미 `video` 인 행은 건드리지 않는다. 토픽(재생목록 분류)은 다시 하지 않는다.
- `runResummary` 는 던지지 않는다 — 재요약 단계가 실패해도 저장·Skip·오류 집계·실행 판정에 영향이 없다. 결과 줄 `🔁 재요약: N편 (제외 등급 N) · 건너뜀 N · 실패 N {사유} · 오늘 N/20 · 남은 대상 N`(1편 이상이면 그 실행의 완료 텔레그램에도 한 줄 — 텔레그램은 기존 조건대로 신규·변경이 있을 때만 나간다).
- 노트(`sync_obsidian.py:refresh_changed_notes`): 장부 `summary_src` 가 `video` 인 행만 본다. 노트 프론트매터 `summary_src` 가 `video` 가 아니면 요약 절(`**▶ 영상 보기: **` 줄 다음 `---` 줄 뒤부터 `\n\n---\n## 🔗 관련 항목` 앞까지)을 새 요약으로 바꾸고 `grade`·`summary_src` 를 맞춘다(없으면 `notion_id` 줄 앞에 넣음). `video` 인데 `grade` 만 다르면 그 줄만. 경계를 못 찾으면 파일을 통째로 다시 쓰지 않고 그대로 둔 채 `RESULT_JSON.refresh_skipped` 로 보고. 바뀐 노트가 있으면 검색 인덱스를 갱신한다(재구성·인제스트는 안 함).
- 끄기: `.env RESUMMARY=false`(재요약만) · `VIDEO_SUMMARY=false`(영상 입력 전부). 진행 판정: `sqlite3 "file:data/library.db?mode=ro" "select json_extract(quality,'$.model'), grade, count(*) from videos where summary_src='video' group by 1,2"` · 건너뜀 `… where json_extract(quality,'$.resummary_skip') is not null`.
- 처리량: 하루 약 19편 → 공개 약 2,950편에 약 5개월. 영상 8시간 상한이 프로젝트별(키별)이면 나중에 상한만 올려 당길 수 있다(미확인).

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
- **Gemini 2.5 Flash**: `GEMINI_API_KEY`·`GEMINI_API_KEYS` (요약 + 분류 + Wiki 합성 + 검색 임베딩)
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

### 중요한 제약사항

**장부 캐시 — 전부 읽었거나, 던지거나 (v3.2.1 → v4.0) — 건드리지 말 것**

v4.0 2단계부터 `scheduler.js:loadLibraryCache()`(장부 `videos` 전량)가 중복 판정의 유일한 근거다. 아래 이력은 노션 캐시 시절 것이지만 원칙은 같다. `scheduler.js:loadNotionCache()` 는 중복 판정의 유일한 근거였다. 빈 캐시·부분 캐시가 한 번이라도 반환되면 전 영상이 신규로 보여 `MAX_NEW_PER_RUN`(15)편을 다시 요약·저장한다. 2026-08-12 ~ 10-01 사이 13회 발생해 Notion 중복 195건이 쌓였고, 결과가 "저장 15 · Skip 0 · 오류 0" 이라 성공으로 보였다.

- 장부 파일이 없으면 `lib/library.js:openLibrary()` 가 **만들지 않고 던진다.** 빈 장부를 새로 만들면 전 영상이 신규로 보인다. `user_version` 이 스키마와 다르면 던진다.
- 0건은 **던진다**. 빈 `Map` 반환으로 바꾸지 말 것. `main` 이 받아 영상 처리와 큐 재시도를 건너뛰고 텔레그램으로 알린다(fail-closed).
- 새로 만든 빈 장부로 처음 돌릴 때만 `.env` 에 `LIBRARY_ALLOW_EMPTY=true`. 평소에는 넣지 않는다. (`NOTION_CACHE_ALLOW_EMPTY` 는 더 이상 읽지 않는다)
- `insertVideo` 는 같은 video_id 를 덮어쓰지 않는다(UNIQUE 위반으로 던짐 → 오류 1건). `INSERT OR REPLACE` 로 바꾸지 말 것.
- **스케줄러 결과가 "저장 15 · Skip 0" 이면 성공이 아니라 캐시 이상을 의심한다.**

**YouTube 조회 재시도·배치 (v3.2.1)**

- `ytFetch()` 는 네트워크 오류·429·5xx 만 지수 백오프(2→16초, 최대 5회)로 재시도한다. 401/403 은 즉시 던진다 — 재시도 대상을 넓힐 때 이 구분을 지우지 말 것.
- 채널 구독자 수는 `getBatchSubs()` 로 50개씩 순차 조회한다. 채널마다 `Promise.all` 로 부르던 방식(실행당 새 연결·유닛 약 450)으로 되돌리지 말 것.
- `scheduler.js` 는 `require.main === module` 일 때만 `main` 을 돈다. 이 가드를 지우면 테스트가 실제 실행을 일으킨다.

**한글 NFC 정규화**: macOS는 파일명을 NFD로 저장함. 장부 topics·tags, 재생목록명, Obsidian 파일명은 모두 `.normalize('NFC')` 필수. `lib/library.js:addTopic()`(v4.0, 장부의 현재 topics 를 다시 읽어 NFC 합집합)이 중복 태그 방지의 핵심.

**YouTube Quota**: 일일 10,000 유닛, 태평양시 자정 리셋 = **KST 16:00**. `playlistItems.insert` 50유닛, 대부분의 읽기 1유닛, `search.list` 100유닛. 안전 버퍼 500을 뺀 임계 **9,500유닛**(`QUOTA_THRESHOLD`) 도달 시 `pending_playlist_adds.json`에 적재 후 다음 실행에서 처리.

- **실패 요청도 quota를 동일하게 소비한다.** v2.5에서 `addToPlaylist`의 실패 경로에도 `consumeQuota(50)`을 넣었다(`lib/youtube_oauth.js:217`). 이전에는 실패가 계상되지 않아 `.quota_state.json`이 0에 머무른 채 실제 한도를 넘겼다.
- 따라서 **하루 재생목록 추가 상한은 약 190건**이다(9,500 ÷ 50). 코드로 늘릴 수 없다.
- 무료 할당량이자 상한선이라 **초과해도 과금되지 않는다.** 403으로 거부될 뿐이다.
- **일 경계는 태평양시(PT) 기준이다** (v2.6). `todayKey()`가 `Intl.DateTimeFormat('en-CA', { timeZone: 'America/Los_Angeles' })`를 쓴다(`lib/youtube_oauth.js:45`). UTC를 쓰면 카운터만 KST 09:00에 리셋돼 **09:00~16:00 동안 스로틀이 무력화**된다. 실패도 50유닛을 먹으므로 소진된 quota에 계속 요청을 밀어넣게 된다. **날짜 키를 만드는 코드를 새로 쓸 때는 반드시 `todayKey()`를 재사용할 것** — `scheduler.js:1475`의 텔레그램 경고도 같은 키를 써야 오경보가 안 난다.
- `.quota_state.json` 스키마는 **`{date, used, ok, fail}`** 이다 (v2.7). `ok`/`fail`은 `playlistItems.insert`의 성공·실패 건수이고, 읽기(`list`)는 `used`에만 반영된다. `consumeQuota(units, outcome)`의 `outcome`은 `'ok' | 'fail' | undefined`. 기존 파일에 `ok`/`fail`이 없으면 `loadQuotaState()`가 0으로 채운다(하위호환).
- `.quota_state.json`의 `date`가 **PT 기준 오늘**이 아니면 그날 YouTube 쓰기가 한 건도 시도되지 않았다는 뜻이다. 최우선 이상 신호.
- **`date`가 오늘이라고 정상인 것은 아니다.** 실패도 `date`를 찍는다. `fail > 0 && ok === 0`이면 **인증은 되는데 쓰기만 전부 실패** — 계정 불일치를 의심할 자리다(v2.7이 이 분기를 텔레그램으로 경고한다).
- 상태 파일이 멈춰 있으면 "동작 안 함"과 "계측 안 됨"을 **둘 다** 의심할 것. (2026-08-17 오판 이력)

**대기 큐 안전장치 (v2.5) — 건드리지 말 것**

`scheduler.js:flushPendingQueue()`와 `processMasterIngest()` 내부 `appendPending`에 들어간 장치입니다. 큐에 쓰는 코드는 `scheduler.js` 한 곳이다(같은 큐 파일에 쓰던 `migrate_classify.js` 는 v4.0 에서 `legacy_scripts/` 로 은퇴).

- `appendPending`은 `(videoId, playlistId)` 중복을 적재하지 않는다(`scheduler.js:1124`). 없으면 큐가 며칠 만에 2배로 부푼다. 실제 46.7%까지 중복된 이력이 있다.
- `flushPendingQueue`는 **연속 실패 10회에서 큐 처리를 중단**한다(`scheduler.js:894`). 403을 수백 번 난사하면 구글이 어뷰징으로 판단해 계정을 정지시킨다. 보안 원칙 1의 구현체다.
- `invalid_grant` / `Token refresh failed` 감지 시 큐를 보존한 채 즉시 중단한다.
- 영구 실패 사유(`playlistItemsNotAccessible`, `playlistNotFound`, `videoNotFound`, `forbidden`)는 dead-letter로 격리한다.
- 그 외 실패는 `retryCount` 5회 초과 시 dead-letter로 보낸다. 무한 순환 금지.

**YouTube OAuth — 가장 자주 깨지는 지점**

```
필요 채널 : 타이쿤안 (UCGDu0ceSSUgzhrRHbW0pQ9w)
GCP       : youtube-data-api-487306, 게시 상태 = 프로덕션
```

- 토큰 재발급 시 **반드시 「타이쿤안」 채널을 선택**한다. 다른 계정/채널로 발급하면 33개 재생목록 전체에 `403 playlistItemsNotAccessible`이 난다.
- **이 에러를 "재생목록이 삭제됨"으로 단정하지 말 것. 계정 불일치를 먼저 의심한다.** 2026-08-17에 이 오판으로 복구 가능한 165건을 영구 폐기할 뻔했다.
- GCP 게시 상태가 「테스트」로 돌아가면 refresh token이 **7일마다 만료**된다. `invalid_grant`가 재발하면 게시 상태부터 확인한다.
- 재발급 중 `accounts.google.com/info/unknownerror`가 뜨면 다중 로그인 세션 충돌이다. 출력된 URL을 **시크릿 창**에 붙여넣는다.
- 발급 후 위 §"OAuth 계정 일치 검증"을 먼저 돌린다(1유닛).

**wiki-ingest 의 Gemini 무료 할당량 — 3중 함정 (2026-09-10)**

`wiki_config.py:gemini_call`. 로그 근거: `~/Library/Logs/irichgreen/wiki-ingest.log` WIKI_RESULT 29회 = processed 212 / errors 165(44%).
오류 내역은 **429 125건(RPD 108 + RPM 17) · 503 39건 · 타임아웃 1건**. 파싱 실패는 0건이다.

- **429 는 두 종류다. `quotaId` 로만 구분된다.** 응답 `error.details[].QuotaFailure.violations[].quotaId` 가
  `GenerateRequestsPerDayPerProjectPerModel-FreeTier`(quotaValue 20)면 RPD,
  `GenerateRequestsPerMinutePerProjectPerModel-FreeTier`(quotaValue 5)면 RPM이다.
  `RetryInfo.retryDelay` 에 권장 대기시간이 같이 온다. **추측으로 분기하지 말 것 — 근거는 응답 안에 있다.**
  예전 코드는 둘을 구분하지 않고 전부 `dead` 처리해서 분당 한도 한 번에 키 하나를 하루치 통째로 버렸다.
  지금은 RPM이면 `retryDelay+2`초(상한 65) 대기 후 **같은 키로** 재시도하고, RPD일 때만 dead 처리한다.
  `quotaId` 가 없으면 `unknown` — 본문 전체를 로그에 남기고 보수적으로 RPD 취급한다.
- **5xx 는 재시도 대상이다.** 오류 165건 중 39건(24%)이 503인데 예전에는 그대로 올려서 소스가 떨어졌다.
  지금은 지수 백오프(2→15초 상한, 3회)로 같은 키에 재시도한다. `<urlopen error timed out>` 도 같은 취급.
  **`scheduler.js` v2.7.1 이 JS 쪽에서 고친 것과 같은 결함이었다. 한쪽만 고치면 다른 쪽이 남는다.**
- **일 경계는 태평양시다.** `_today()` 가 `time.gmtime(now - 8h)` 를 쓴다. KST 자정 기준으로 세면
  로컬 카운터만 리셋되고 구글 RPD 는 그대로라, **00시 실행이 매번 '깨끗한 장부'로 시작해 즉시 429 를 맞는다.**
  `lib/youtube_oauth.js:todayKey()` 와 같은 취지의 교정이다.

**wiki_ingest 실행 경로는 두 개다 (2026-09-10)**

```
① launchd  com.irichgreen.wiki-ingest         매일 17:30 (= PT 01:30, RPD 리셋 직후)
② scheduler.js:1525  totalSaved === 0  →  sync_obsidian.py --rebuild
     └ sync_obsidian.py:516  --rebuild → force=True
       └ sync_obsidian.py:538  subprocess.run([sys.executable, 'wiki_ingest.py', '--no-backfill'], capture_output=True)
```

②는 **저장 0건인 스케줄러 실행마다(00/06/12/18시)** 돈다. 증분 모드라 할 일이 없으면 즉시 끝나고,
KST 00/06/12 시는 PT 기준 전날 장부·17:30 은 PT 당일 리셋 직후라 서로 할당량을 뺏지 않는다.
**②를 끄지 말 것 — 의도된 동작이다.**

- ②의 stdout 은 `capture_output=True` 라 예전에는 `ytsummarizer.log` 로 흡수돼
  `wiki-ingest.log` 에 아무것도 안 남았다. `.wiki_state.json` 의 `last_run` 만 갱신되고 로그는 그대로여서
  "안 도는 줄" 오판하기 좋았다(2026-09-10 06:01:11 사건).
  지금은 `sync_obsidian.py:_tee_wiki_log()` 가 캡처한 출력을 `wiki-ingest.log` 에 append 한다.
  `───── via sync_obsidian.py (subprocess) <ISO시각> ─────` 헤더가 붙고 **`WIKI_RESULT` 줄이 그대로 남는다.**
  `WIKI_RESULT` 가 유일한 판정 지표이므로 이 tee 를 지우면 ②는 다시 안 보이게 된다.
- **두 경로의 인터프리터는 같다: `/opt/homebrew/bin/python3`.**
  plist 의 `ProgramArguments`, `scheduler.js:1514`, `server.js:232` 가 모두 이 경로를 하드코딩하고,
  `sync_obsidian.py` 는 `sys.executable` 을 물려주므로 ②도 같은 파이썬을 탄다.
  **셋 중 하나만 바꾸면 라이브러리가 갈린다 — 바꿀 때는 3곳을 함께 고칠 것.**

**Gemini 분류 경로 — 요약 경로와 대응이 달랐던 자리 (v2.7.1)**

- `scheduler.js`의 분류 재시도 catch는 원래 **429/quota만** 재시도했다. 요약 경로(`:459`)는 503에 키 로테이션 + 재시도로 대응하는데 분류만 빠져 있어 **503 한 번에 영상이 떨어졌다**(2026-08-28 06:00 실제 발생). 지금은 `5xx`·`UNAVAILABLE`·`overloaded`·`high demand`도 지수 백오프(2→15초 상한)로 재시도한다. **분류 쪽 재시도 조건을 손댈 때 요약 경로와 대칭인지 먼저 확인할 것.**
- `401`/`403`은 **명시적으로 즉시 중단**한다(보안 원칙 1). 재시도 조건을 넓힐 때 이 가드를 지우지 말 것.
- 재시도 소진 시 `cls`가 `undefined`인 채 `cls.topics`로 진입하던 잠복 TypeError 경로가 있었다. `clsAttempt < maxClsAttempts` 가드와 루프 직후 `if (!cls) throw` **가드 2개가 짝**이다. 한쪽만 지우면 되살아난다.
- `classifyTopics`를 `maxRetries: 0`으로 호출하는 것은 **의도된 설계**다. 재시도는 키 교체를 하는 바깥 루프가 담당한다.

**Gemini API 최적화 (중요)**: Gemini 2.5 Flash 모델 사용 시 내부 추론 과정에서 과다한 "Thinking 토큰" 과금을 방지하기 위해 반드시 API 호출 옵션에 `generationConfig: { thinkingConfig: { thinkingBudget: 0 } }`를 적용해야 합니다 (비용 85% 절감 효과). (v4.6-b) 3.x 모델(`gemini-3.5-flash-lite` 등)은 `thinkingBudget` 을 400 INVALID_ARGUMENT 로 거절한다 — `thinkingConfig: { thinkingLevel: 'minimal' }`(`lib/video_summary.js:thinkingConfigFor`).

**토픽 추가 시**: `playlists.json`에 새 항목 추가 + `build_obsidian_wiki.py`의 `VALID_NOTION_TAGS` 동기화 필수.

**Vault 경로 중첩 (2026-09-19)**: 실제 Vault는 `~/Documents/Obsidian/AI LLM Wiki/AI LLM Wiki` (바깥 `AI LLM Wiki/`는 빈 껍데기, `README-여기가-아님.txt` 있음). 동작에 문제 없음. 이 경로는 `sync_obsidian.py`·`build_obsidian_wiki.py`·`wiki_config.py`·`lib/wiki_search.js`·`cleanup_duplicates.py`·`notion_to_obsidian.js` 6곳 + `legacy_scripts/` 2곳 + Obsidian 앱 등록에 박혀 있다. **v3.3(2nd_Brain 2단계 — `build_search_index.py`에 `_Brain/` 포함)과 같은 작업지시서로 한 단계 승격한다. 그 전에 옮기지 말 것.** 절차: 데몬 전부 stop(`wiki-lan` 포함 — 같은 Vault 경로를 읽는다) → `mv` → 8파일 치환 → Obsidian 재등록 → `--orphans-dry-run --no-tips`로 "notion_id 2,542·고아 0" 확인 → 인덱스 재빌드 → 재기동.

**server.js 보안**: `127.0.0.1` 전용 바인딩. CORS는 `localhost:3000`만 허용. IP당 분당 120요청 rate limit. 노션 프록시(v4.0 2-b)·`/api/sync-obsidian`(v4.0 3단계)은 제거됐다 — 다시 만들지 말 것.

### launchd 데몬

| 라벨 | 실행 대상 | 스케줄 | 인터프리터 |
|------|-----------|--------|-----------|
| `com.irichgreen.server` | `server.js` (포트 3000) | `KeepAlive`, `RunAtLoad` — 상주 | `/opt/homebrew/bin/node` |
| `com.irichgreen.ytsummarizer` | `scheduler.js` | 00 / 06 / 12 / 18시 | `/opt/homebrew/bin/node` |
| `com.irichgreen.wiki-ingest` | `wiki_ingest.py` (증분 + backfill + 재렌더) | 매일 17:30 | `/opt/homebrew/bin/python3` |
| `com.irichgreen.wiki-lan` | `wiki_lan_server.js` (포트 3100) | `KeepAlive`, `RunAtLoad`, `ThrottleInterval 60` — 상주 | `/opt/homebrew/bin/node` |

- **실제 동작하는 plist는 `~/Library/LaunchAgents/`에 있다.** 레포 루트의 plist 4개는 그 원본이며 모두 실경로(`<REPO_ROOT>` 의 절대경로)가 들어 있다. **원본은 설치본과 같게 유지한다** — 2026-10-12 대조에서 `wiki-ingest` 원본만 옛 값(03:00 · `/usr/bin/python3` · `--full`)이라 설치본(17:30 · Homebrew python3 · 증분)으로 맞췄다. 확인: `diff <(plutil -convert xml1 -o - ~/Library/LaunchAgents/<라벨>.plist) <(plutil -convert xml1 -o - <라벨>.plist)`. 예전에 `server`·`ytsummarizer` 두 개에 있던 `/Users/사용자명/youtube-notion-app` 플레이스홀더는 제거했다.
- 각 plist는 `ProgramArguments`·`WorkingDirectory` **2곳에 절대경로**가 박혀 있다. 경로 변경 시 8군데(4개 × 2) 동기화 + `plutil -lint` + unload/load.
- **레포 경로 자체를 바꿀 때 함께 고칠 맥 설정(레포 밖):** 설치된 plist 4개, `~/Library/Scripts/rotate_extra_logs.sh` 의 `YTDIR`, Claude Code MCP `wiki-search` 등록(`~/.claude.json` 사용자 범위 — `claude mcp remove`/`add -s user`), 스킬 `kakao-tips-update` 의 경로. 절차·검증은 `docs/tasks/2026-10-13-rename-ai-wiki-pipeline.md`.
- `install-server.sh`·`install-scheduler.sh`는 plist를 `~/Library/LaunchAgents/`로 복사하며 **sed로 이 실경로를 `$APP_DIR`로 치환**한다. 레포 경로를 바꾸면 두 스크립트의 sed 패턴도 같이 고쳐야 치환이 동작한다. `install-wiki-ingest.sh` 는 치환 없이 그대로 복사한다(원본 = 설치본). `deploy.sh` 는 옛 일괄 업로드 스크립트라 쓰지 않는다.
- `com.irichgreen.server`는 상주 프로세스라 **코드를 고쳐도 재기동 전까지 반영되지 않는다.**
- `com.irichgreen.wiki-lan`의 로그(`wiki-lan.log`)는 **`rotate_extra_logs.sh`에 넣지 않는다.** 상주형이라 rename 회전이 안전하지 않다. 대신 서버가 기동·차단·오류만 찍는다.
- **macOS 방화벽의 수신 허용은 node 실행 파일의 실제 경로(Cellar 버전 폴더)에 걸린다**(2026-10-03 실측: 허용 목록에 옛 버전 경로만 남아 있었다). `brew upgrade node` 후에는 경로가 바뀌므로 `wiki-lan`이 살아 있어도 가족 PC에서만 접속이 막힐 수 있다 — 이 맥에서의 `curl`은 정상으로 보일 수 있으니 판정은 다른 기기로 한다. 재기동 + 방화벽 재허용이 한 세트다.
- **`brew upgrade` 후에는 상주 데몬을 반드시 재기동한다.** 데몬은 기동 시점의 Cellar 경로를 물고 도는데, 업그레이드로 그 폴더가 삭제되면 이후 지연 import가 전부 실패한다. 이미 로드된 모듈은 멀쩡히 동작해 **부분 실패로 나타나므로 알아채기 어렵다.** (2026-08-17 자매 프로젝트 실장애)

### 보안 — 절대 커밋 금지

`.gitignore` 대상: `.env`, `.env.*`, `node_modules/`, `__pycache__/`, `*.log`, `playlists.json`, `.DS_Store`, `.claude/settings.local.json`, `wiki_index.json`, `wiki_index.vec`, `.migrate_state.json`, `.quota_state.json`, `.wiki_state.json`, `.wiki_quota.json`, `pending_playlist_adds*`, `.run_state.json*`(v4.2), `.video_quota.json`(v4.6), `data/`(장부), `KakaoTalk_Chat_*`, `Claude outputs/`. 시트 미러는 상태 파일을 만들지 않는다(워터마크는 장부 `meta`). 장부 백업도 상태 파일이 없고(오늘 날짜 파일 유무로 판단) 백업은 `data/backups/` 라 `data/` 패턴에 들어간다.

> ⚠️ **새 상태 파일을 만들면 `.gitignore` 패턴을 반드시 재확인한다.**
> `pending_playlist_adds.json*` 패턴이 `.dead.json`·`.backup.*.json`을 못 잡아 커밋될 뻔한 사고가 있었다(2026-08-17). 현재는 `pending_playlist_adds*`로 수정됨.
> 새 파일 추가 시 `git check-ignore -q <파일>`로 확인할 것.

`.env`·`.claude/`·상태 파일은 gitignore라 **`git clone`으로 복제되지 않는다.** 환경 이전은 clone이 아니라 `mv`/수동 복사로 한다.

### 로그 파일

- `scheduler.log` / `scheduler-stdout.log`: 스케줄러 실행 로그. 10MB 를 넘으면 `~/Library/Scripts/rotate_extra_logs.sh`(`com.irichgreen.log_rotate` 가 호출)가 회전한다(`.1.gz`~`.6.gz`). 통째로 읽지 말고 `tail`/`grep`으로 볼 것.
- `server.log`: 서버 요청 로그
- Obsidian vault의 `log.md`: wiki 변경 이력

### 진단 원칙

추측하지 말고 근거를 먼저 확보한다 — 로그(`tail`/`grep`), `git status`, `launchctl list | grep irichgreen`, 파일 mtime, `.quota_state.json`, 큐 파일 건수.

---

## 산출물 규칙

- 커밋 전 **`README.md`만** 갱신한다. **`README.html`은 v3.0에서 폐지 — 다시 만들지 않는다.** (2026-09-06)
- `README.md` 버전 이력은 요약 표 1행 + 상세 변경 내역 1절을 함께 쓴다. 메이저는 아키텍처 확장(소스·저장소·합성 엔진 추가), 마이너는 기능·안정성.
- `CLAUDE.md`는 구조·제약이 바뀔 때 갱신하고 하단 이력에 날짜와 함께 남긴다.
- `AGENTS.md`는 **git 추적 대상**이다(2026-09-08~). `CLAUDE.md`와 함께 갱신하고, 두 문서가 어긋나면 **`CLAUDE.md`가 이긴다**.
- 문서에 **개인 절대경로를 새로 쓰지 않는다**(2026-09-09~). 앞으로 추가·수정하는 줄은 `<REPO_ROOT>/...` 또는 `~/...` 표기를 쓴다. 기존 표기는 소급 정리하지 않는다.
- Cowork → Claude Code 핸드오프는 `docs/tasks/YYYY-MM-DD-<슬러그>.md` 작업지시서로 한다.
- `git push`는 사용자 확인 후.

## 변경 이력

- **2026-10-13 (v4.7 — Wiki 검색 화면 개편)** — 대표님 요청 6건(처음 열면 전체 목록 · 건수 선택 제거 · 토픽 다중 선택 · 정렬 목록 유지 · 필터 추가 · 머리줄 정렬) + 결정(관련 결과 = 의미 점수 상위 200건 · 비슷한 영상 · 새로 들어온 것 · 엑셀 내려받기 · 노트 전체 보기 · 밝은 테마만). `wiki.html` 전면 교체(iRichGreen Design System 웹 계층 DS 1.1.23 토큰·FilterChip·SegmentedControl·표 30px 줄, 표/카드, 줄 펼침, URL 해시 상태, `/`·Esc, 휴대폰 서랍 필터). `lib/wiki_search.js` `listPayload`·`scoreAll`·`similar`·`noteById`, `server.js`·`wiki_lan_server.js` `/api/wiki-search` 에 `all=1`·`scores=1`·`similar=` 옵션 + 새 읽기 전용 경로 `/api/wiki-note`(id 로만). `build_search_index.py` 화면 필터용 메타 7개(임베딩 hash 무관 — 실 Vault 사본 실행 임베딩 0건). 장부·스키마·스케줄러 무변경. 테스트: 신규 `test_wiki_search.js` 34/34, `test_build_wiki_index.py` 15/15(+4). 회귀 테스트 12종. 지시서 `docs/tasks/2026-10-13-v47-wiki-ui.md`.
- **2026-10-13 (v4.6-b — 기존분 재요약 + 노트 요약 절 교체 + backfill 재개)** — 배경: 장부의 옛 요약 약 3,000편이 설명란 추론이라 일부가 지어낸 내용이고, 그래서 Wiki backfill 을 정지해 뒀다. 10-13 비교 5건에서 `gemini-3.5-flash-lite` 가 2.5 Flash 와 등급·신호 5/5 일치(말 내용 포함, 요약은 약 65% 길이), 3.x 는 `thinkingBudget: 0` 을 400 으로 거절. 수정: `lib/resummarize.js` 신규(scheduler 매 실행 신규 처리 뒤, 실행당 5 · 하루 20 · 신규 몫 3시간 예약, 실패 시 기존 요약 유지·건너뜀/실패/중단 분류), `lib/video_summary.js` 모델 인자·`thinkingConfigFor`·`fallback:false`·`reserveSeconds`·`summaryProblem`(bad_summary 사유 로그)·promo_main 프롬프트 좁힘(무료 자료 배포·구독 유도·끝에 잠깐 하는 자기 홍보는 판매 아님), `lib/library.js` 재요약 헬퍼(`updateResummary` — `updated_at` + `wiki_extract` stale), `sync_obsidian.py:refresh_changed_notes`(요약 절 제자리 교체·관련 항목 보존·장부 grade 만 고쳐도 노트가 따라옴), `wiki_ingest.py` backfill 대상 = `summary_src: video` 만 · 항목 0 페이지 안내 문구. 스키마 무변경(user_version 3). `.env WIKI_BACKFILL_DAILY_MAX=0` 정지 줄 제거. 테스트: 신규 `test_resummarize.js` 9/9, `test_video_summary.js` 23/23(+6), `test_scheduler_guards.js` 33/33(+2), `test_sync_obsidian.py` 32/32(+8), `test_wiki_ingest.py` 64/64(+7). 회귀 테스트 11종. 지시서 `docs/tasks/2026-10-13-v46b-resummarize.md`.
- **2026-10-13 (v4.6-a — 실제 영상 요약 + 품질 필터, 신규 영상부터)** — 배경(10-12 시험): 요약이 제목·설명란만 보고 "추론해서라도 작성"이라 설명란이 빈약하면 지어낸 내용이 됐다(`mW5k5CbO4sA` 「AI 데이터 활용」 = 실제는 Python 문자열 강의). 수정: `lib/video_summary.js` 신규 — 공개 영상은 Gemini 2.5 Flash 에 YouTube URL 을 영상으로(LOW, 30분 넘으면 앞 30분), JSON 으로 요약 + 사실 신호, 등급은 코드 규칙(판매 주목적·일반론·AI 무관 → exclude). 영상 토큰 0(삭제 영상)·비공개·403(연속 2회면 그 실행 끔)·429 소진·하루 8시간 분량(`.video_quota.json`)은 설명란 요약으로 대체. `getBatchDetails` 가 `contentDetails,status` 도 받음(1유닛 그대로). 장부 user_version 3(`videos.grade`·`quality`·`summarized_at`, `migrate_library.py` 가 v1·v2 → v3 한 번에). 노트 프론트매터 `grade`·`summary_src`, `grade: exclude` 는 `wiki_ingest`·`build_search_index` 에서만 제외. `.env` 스위치 `VIDEO_SUMMARY`·`VIDEO_MAX_SECONDS`·`VIDEO_DAILY_SECONDS`. 테스트: 신규 `test_video_summary.js` 17/17, `test_scheduler_guards.js` 31/31(+2), `test_wiki_ingest.py` 57/57(+6), `test_sync_obsidian.py` 24/24(+1), `test_build_wiki_index.py` 11/11(+1). 회귀 테스트 10종. 지시서 `docs/tasks/2026-10-13-v46a-video-summary.md`.
- **2026-10-12 (v4.5 — Wiki 합성 결과 누적)** — 결함: `wiki_ingest.py` 가 개념·엔티티 페이지와 index 를 그 실행분만으로 다시 써서(05-12 도입 때부터) 페이지 56개의 source_count 가 1~10, index 9행뿐이었다(합성 소스 3,619건). 추출 결과를 저장하지 않아 되살릴 원본이 없었다. 수정: 장부에 `wiki_extract` 표(user_version 1 → 2, `scripts/migrate_library.py`), 소스별 누적 + 매 실행 전체 재렌더(결정적, 내용 같으면 안 씀, 고아 제외·retitle 반영), 깨진 응답은 실패로 3회까지 재시도, 옛 페이지 항목 씨앗(`--seed-from-pages`), 옛 소스 backfill(20개 묶음, 하루 30회, launchd 경로만 — `sync_obsidian` 은 `--no-backfill`). `backup_library.py` 행 수에 `wiki_extract` 추가. 테스트: 신규 `test_wiki_ingest.py` 51/51, `test_backup_library.py` 버전 기대값을 `SCHEMA_VERSION` 으로. 회귀 테스트 9종. 지시서 `docs/tasks/2026-10-12-wiki-extract-store.md`.
- **2026-10-12 (v4.4 — 꿀팁 제목 보완 도구)** — `scripts/retitle_tips.py`(+ `scripts/test_retitle_tips.py` 49/49) 신규: 장부 tips 제목·`updated_at` + 「AI 꿀팁」 노트 제자리 수정·파일명 변경 + Vault 링크 치환, dry-run 기본·쓰기 전 백업(`data/retitle_backup/`, gitignore 의 `data/` 아래). 앱 코드·데몬 무변경. 첫 적용 5건(`docs/tasks/2026-10-12-retitle-tips.csv`). 회귀 테스트 8종. 지시서 `docs/tasks/2026-10-12-retitle-tips.md`.
- **2026-10-12 (v4.3 — 노션 잔재 정리)** — 노션 해지(10-12)에 따라 `lib/tips_notion.py`·`scripts/notion_to_sqlite.py`·`scripts/test_notion_to_sqlite.py` 삭제, `.env` 의 `NOTION_*` 3키 삭제. 그중 계속 쓰던 장부 ↔ Vault 대조(`--verify`)는 `scripts/verify_library.py`(+ `scripts/test_verify_library.py` 16/16)로 떼어 냈다 — 검사 항목·`RESULT_JSON` 키 동일, 실데이터 결과 동일(영상 2,999 · 꿀팁 148 · 없음 0). 앱 코드 변경 없음(주석 3곳). 회귀 테스트 7종 유지. 이름 변경 날짜 표기를 실제 실행일(10-12)로 정정.
- **2026-10-12 (이름 변경, 버전 유지)** — 폴더 `Youtube_Notion_Grap` · GitHub `YouTube_Notion_Grab` → 둘 다 `AI_Wiki_Pipeline`. 레포 안: plist 원본 4개 · `install-server.sh`·`install-scheduler.sh` sed 패턴 · `package.json` 이름 · `wiki_mcp.js`·`gas/sheet_mirror.gs` 주석 · README 구조도 · `docs/cowork-project-instructions.md`(v2.5 시절 사본 → 안내문). 레포 밖: 설치된 plist 4개 · `rotate_extra_logs.sh` `YTDIR` · Claude Code MCP `wiki-search` 재등록 · crontab 의 죽은 줄(08-17 이전 경로의 `migrate_classify.js`, 두 달째 매일 실패) 삭제. 함께 고친 낡은 줄: 대기 큐 절의 `migrate_classify.js` 공유(v4.0 은퇴), plist 경로 "6군데" → 8군데, `scheduler.log` "약 20MB · 로테이션 미도입" → 10MB 회전. `docs/tasks/` 의 옛 지시서·패치는 기록이라 그대로 둔다. 지시서 `docs/tasks/2026-10-13-rename-ai-wiki-pipeline.md`.
- **2026-10-12 (문서 현행화, 버전 유지)** — README 전수 대조 후 수정: 다이어그램(요약 `geminiSummarize` · 분류 `classifier.js` 분리, 백업·`.run_state.json` 추가), 사이클 표 순서(대기 큐 소진이 인제스트보다 먼저 — `scheduler.js` 실제 순서), `YOUTUBE_PLAYLIST_SYNC` 설명, Node 22.13+, launchd 4개 표, 프로젝트 구조 누락 파일 5개, 장부 `meta`·`tips` 열, v4.0 이력의 낡은 표기. 레포 `com.irichgreen.wiki-ingest.plist` 를 설치본과 같게(17:30 · Homebrew python3 · 증분), `install-wiki-ingest.sh`·`install-scheduler.sh`·`deploy.sh` 의 낡은 문구(03:00·노션·00:30) 정리. 코드 동작 무변경, 데몬 재기동 불필요. 지시서 `docs/tasks/2026-10-12-docs-sync.md`.
- **2026-10-12 (v4.2 — 실행 실패 알림)** — 10-04 ~ 10-12 실행 35회 재집계: 프로세스가 죽은 실행 0, "저장 0 · Skip 0 · 오류 1" 로 끝난 실행 2(10-04 06:00·10-05 00:00 ENOTFOUND), 아예 돌지 않은 정시 실행 1(10-09 12:00) — 셋 다 텔레그램 없이 지나갔다(`hasNewOrUpdated` 에 안 걸리고, `main().catch` 는 로그만). `scheduler.js`: 통째 실패면 `[실행 실패]` 텔레그램, `main().catch` 도 기록 후 알림, 실행 상태 파일 `.run_state.json` 으로 못 보낸 실패·끝나지 못한 실행·9시간 넘는 간격을 다음 실행이 `[직전 실행 점검]` 으로 알림(못 보내면 pending 으로 넘김, 최대 10줄). `sendTelegram` 이 성공 여부(true/false)를 돌려주고 JSON 아닌 응답에 죽던 잠복 결함·무응답 대기를 막음(20초). `.gitignore` 에 `.run_state.json*`. 테스트: `test_scheduler_guards.js` 29/29(+7), 사본 폴더 `main()` 모의 실행 10종(가짜 https·하위 스크립트). 지시서 `docs/tasks/2026-10-12-run-failure-alert.md`.
- **2026-10-12 (v4.1 — 장부 자동 백업)** — `backup_library.py` 신설: 장부를 하루 1회(KST 날짜 파일 유무로 판단, 상태 파일 없음) SQLite 온라인 백업 → `integrity_check`·`user_version`·`videos≥1` 검사 → gzip → 압축 해제 sha256 대조 후 `data/backups/` + `.env LIBRARY_BACKUP_DIR`(구글 드라이브 데스크톱 앱 폴더)에 저장, 최신 7개 + 주별 4개 보관(형식 맞는 이름만 정리). 드라이브 부모 폴더가 없으면 만들지 않고 실패. 장부는 읽기 전용. `scheduler.js:runLibraryBackup()`(reject 없음, 실패는 텔레그램 별도). 배경: 타임머신 디스크 미마운트·iCloud 동기화 꺼짐으로 장부 사본이 같은 디스크의 `.bak` 하나뿐이었다. 테스트: 신규 `test_backup_library.py` 50/50, `test_scheduler_guards.js` 22/22(+3). 지시서 `docs/tasks/2026-10-12-library-backup.md`.
- **2026-10-12 (v4.0 3단계 — v4.0 완료)** — 구글 시트 미러: `sheet_mirror.py`(장부 → 시트, `updated_at` 워터마크로 변경분만, 401/403·토큰·HTML 응답 즉시 중단, 5xx 지수 백오프) + `gas/sheet_mirror.gs`(Apps Script 웹앱, 토큰·탭 화이트리스트·머리글 대조·수식 방지), `scheduler.js:runSheetMirror()`(reject 없음, 실패는 텔레그램). 노션 정리: `kakao_ingest.py` 의 `tips_notion` import → `lib/env_util.py`, `block_to_md` → `scripts/notion_to_sqlite.py`(보관) — 앱은 노션 모듈을 import 하지 않는다. `lib/tips_notion.py`·`notion_to_sqlite.py`·`.env` `NOTION_*` 는 노션 해지 때 삭제. `server.js` `/api/sync-obsidian` 제거. `build_search_index.py` 프론트매터 한정(실 Vault 3,121 노트 옛 코드와 동일). `build_obsidian_wiki.py` 내용 같으면 안 쓰기(실 Vault 사본 재구성 2회차 쓰기 0 — 10-11 의 Vault 전체 mtime 갱신 해소) + 프론트매터 없는 파일에 관련 항목이 쌓이던 잠복 결함 수정. 문서 전면 갱신(README v4.0, 이 파일의 카톡 절·명령·파일 표, AGENTS.md 를 이 파일과 같은 내용으로). 테스트: `test_scheduler_guards.js` 19/19(+3), `test_kakao_ingest.py` 18/18(+1), 신규 `test_sheet_mirror.py` 45/45 · `test_build_wiki_index.py` 10/10, 기존 37/37 · 23/23. 지시서 `docs/tasks/2026-10-12-v4-sheet-mirror-cleanup.md`.
- **2026-10-11 (v4.0 2단계-b)** — 읽기 전환. `sync_obsidian.py` 가 장부(읽기 전용)를 읽어 노트를 만든다 — 노션 호출 0, 본문은 `summary` 마크다운(노션 시절 노트와 같은 모양). `notion_id`·`video_url` 은 프론트매터 안의 것만 센다. 고아 격리 3중 안전장치 유지, 꿀팁 고아는 보고만. `--dry-run` 신설. `server.js`·`index.html` 노션 프록시·토큰 테스트·브라우저 직접 처리 제거. `migrate_classify.js` 등 5개 → `legacy_scripts/`. 테스트: 신규 `test_sync_obsidian.py` 23/23, `test_notion_to_sqlite.py` 37/37(vault_ignored 1 → 0). 지시서 `docs/tasks/2026-10-11-v4-sqlite-switch-b.md`.
- **2026-10-11 (v4.0 2단계-a)** — 쓰기 전환. `scheduler.js` 의 노션 캐시·저장·주제 추가·통계 갱신을 로컬 장부(`lib/library.js`, `node:sqlite`)로 교체 — 노션 호출 0. `kakao_ingest.py` 는 장부 `tips` 에 한 트랜잭션으로 쓴다. `lib/library_db.py:open_existing()`(없으면 만들지 않음). `notion_to_sqlite.py --mark-switched` + 전환 후 `--apply --replace` 거부. WAL 미전환(순차 접근, busy_timeout 5초). 테스트: `test_scheduler_guards.js` 16/16(노션 캐시 5건 → 장부 9건), `test_notion_to_sqlite.py` 37/37, 신규 `test_kakao_ingest.py` 17/17. 지시서 `docs/tasks/2026-10-11-v4-sqlite-switch-a.md`.
- **2026-10-11 (v4.0 1단계)** — 노션 → SQLite 적재. 신규 `scripts/notion_to_sqlite.py`(노션 읽기 전용, 기본 dry-run, `--apply`·`--replace`·`--verify`·`--summary-check`), `scripts/test_notion_to_sqlite.py`(32/32, 네트워크 0회), `lib/library_schema.sql`·`lib/library_db.py`. `.gitignore` 에 `data/`. 적재 결과: 영상 페이지 3,189 → videos 2,986 · videos_dup 203 · tips 135, 요약 대조 무작위 100건 100/100 일치(속성=본문). 기존 파이프라인 코드 무변경(노션이 아직 원본). Vault 대조는 프론트매터 안의 notion_id 만 센다(Vault 루트 schema.md 본문 예시가 영상 id 로 잡혀 1차 dry-run 이 멈췄다). 노션에서 지워진 중복 꿀팁 page 의 잔여 노트 1건을 _trash/<시각>/AI 꿀팁/ 으로 격리. 지시서 `docs/tasks/2026-10-11-v4-notion-to-sqlite.md`·`-fix1.md`.
- **2026-10-05 (v3.2.1)** — 스케줄러 네트워크 안전장치. 배경: 로그 집계(08-12 ~ 10-05, 실행 219회)에서 실행 통째 실패 62회(28%, ENOTFOUND 41·ETIMEDOUT 17·기타 4)와, Notion 캐시 첫 조회 실패 → 빈 캐시 진행 23회(그중 13회가 영상 15편 재저장, 중복 195건). `loadNotionCache()` 를 "전부 읽었거나, 던지거나" 로 교체(재시도 초과·0건은 throw, 401/403 은 fatalAuth 즉시 종료, `NOTION_CACHE_ALLOW_EMPTY` 로만 빈 DB 허용)하고 `main` 은 캐시 실패 시 영상 처리·큐 재시도를 건너뜀(fail-closed). `ytFetch()` 에 일시 오류 지수 백오프(2→16초, 5회) 추가, 채널 구독자 수 조회를 채널당 1회·동시 호출(약 450)에서 `getBatchSubs()` 50개 배치 순차(9회)로 교체, `scheduler.js` 를 `require.main === module` 가드로 `require` 가능하게 함. 검증: `scripts/test_scheduler_guards.js` 12/12, 모의 실행 2종(네트워크 전면 실패·Notion 401) 기대대로, 읽기 전용 실측(캐시 3,042 · 영상 1,412 · 고유 채널 450 → 구독자 응답 450 · 신규 판정 22). 야간 ENOTFOUND 의 직접 원인은 밝히지 못했다. 지시서 `docs/tasks/2026-10-05-scheduler-network-guards.md`.
- **2026-10-03 (v3.2)** — 집 안 전용 읽기 전용 Wiki 검색 서버 `wiki_lan_server.js`(포트 3100) 신설 + `com.irichgreen.wiki-lan` 데몬. `server.js` 는 Notion 쓰기 프록시·인제스트 실행 엔드포인트가 함께 있어 `127.0.0.1` 전용을 유지하고, 검색 라우트 6개만 별도 서버로 노출한다. 안전장치: `.env` 의 `WIKI_LAN_ALLOW_CIDR` 대역 + 루프백만 허용(미설정·오류 시 127.0.0.1 전용, fail-closed), 소켓 주소만 신뢰(XFF 무시), Host 검사, AI 답변 IP당 분당 5회 + 24시간 총량 제한. `wiki.html` 에 `IS_LOCAL` 추가(가족 PC 에서 Obsidian 링크 숨김). 검증: 바인딩 `*:3100`/`127.0.0.1:3000` 분리 유지, server.js 전용 경로 6종 전부 404, 위조 Host·타 출처 403, 검색 vector 2건, AI 답변 정상 1회. `CLAUDE.md` 머리 버전을 v3.0→v3.2 로 교정(README 는 09-10 에 이미 v3.1)하고, 표에 없던 검색 계열 파일(`wiki.html`·`lib/wiki_search.js`·`wiki_mcp.js`·`build_search_index.py`)을 추가. 방화벽 수신 허용(sudo)과 가족 PC 실접속 확인은 사용자 몫. 지시서 `docs/tasks/2026-10-03-wiki-lan-server.md`. 같은 날 보완: 기동 로그의 접속 주소를 `os.hostname()` → `scutil --get LocalHostName` 기준으로 교정(전자는 `.local`로 풀리지 않는 이름을 줬다), `.gitignore`에 `Claude outputs/` 추가, `AGENTS.md`의 낡은 인터프리터 문구 정정. 지시서 `docs/tasks/2026-10-03-wiki-lan-hostname-fix.md`.
- **2026-09-10** — wiki-ingest 429 처리를 RPD/RPM 분기로 교정(`wiki_config.py`). 로그 실측 근거: 오류 165건 = 429 125(RPD 108/RPM 17) + 503 39 + 타임아웃 1, 파싱 실패 0. `quotaId` 로 구분해 RPM 은 `retryDelay` 대기 후 같은 키 재시도, RPD 만 dead 처리(`unknown` 은 본문 전량 로깅 후 보수적 RPD). 5xx·URLError 지수 백오프 추가(24%의 오류가 재시도 없이 버려지던 자리). `_today()` 를 태평양시로 교정. 부수 발견: `scheduler.js:1525` 의 `--rebuild` 경로가 `wiki_ingest.py` 를 `capture_output` 으로 띄워 로그에 안 남는 실행이 하루 최대 4회 있었다. `sync_obsidian.py` 에 `_tee_wiki_log()` 추가 — `--rebuild` 경로로 띄운 wiki_ingest 의 출력(WIKI_RESULT 포함)을 `wiki-ingest.log` 에 append 해 두 실행 경로를 한 로그에서 보게 했다(`--rebuild` 중복 실행 자체는 의도된 동작이라 유지). launchd 표의 wiki-ingest 인터프리터·스케줄 기재를 실제값(`/opt/homebrew/bin/python3`, 17:30, 증분)으로 교정. 검증: `--limit=6` processed 6 / errors 0(429 2건을 키 교체로 흡수), `sync_obsidian.py --rebuild` 후 `wiki-ingest.log` 에 tee 블록·WIKI_RESULT 기록 확인. 백업 `wiki_config.py.bak.20260910`(며칠 관찰 후 삭제).
- **2026-09-09 (문서)** — 규약 1줄: 문서에 개인 절대경로를 새로 쓰지 않는다(`<REPO_ROOT>`·`~` 표기). 기존 8곳(CLAUDE.md 3 · AGENTS.md 5)은 09-06 push 분이 이미 공개라 소급 정리하지 않는다(사용자 판정).
- **2026-09-08 (문서)** — `AGENTS.md` git 추적 시작(420줄, 그동안 untracked). 추적 밖이라 diff·리뷰에 안 잡혀 `AGENTS.md:409`가 "README.md + README.html 양쪽 동시 갱신"으로 남아 `CLAUDE.md:284`(v3.0 폐지)와 어긋나 있었다 — 금지 문구로 교체하고 추적 규약을 산출물 규칙에 추가. 코드 무변경.
- **2026-09-06 (v3.0)** — 메이저 승격: 지식 소스 2원화(YouTube + 카카오톡). `kakao_ingest.py`에 `--if-new`·`.kakao_state.json`·`RESULT_JSON`·`KakaoTalk_Chat_안진훈_` 접두 필터(NFC) 추가. `scheduler.js` 훅 지시서 `docs/tasks/2026-09-06-scheduler-kakao-hook.md`. 생성 경로 검증(테스트 행 생성→아카이브). **`README.html` 삭제·폐지 — 앞으로 만들지 않는다.** README.md v3.0 상세 이력·데이터 흐름도.
- **2026-09-06 (v2.8, 같은 날 v3.0에 흡수)** — 카카오톡 → Notion「AI 꿀팁」→ Obsidian 연동. 신규 `kakao_ingest.py`(기본 dry-run, `--apply`), `lib/kakao_parse.py`, `lib/tips_notion.py`. `sync_obsidian.py`에 `sync_tips()` 추가(`AI 꿀팁/` 평면 폴더, `link_url` 프론트매터, YouTube 고아 격리·tags 동기화에서 폴더 제외, `--no-tips`, `RESULT_JSON.tips_added`). `.env`에 `NOTION_TIPS_DB_ID`·`KAKAO_EXPORT_DIR`, `.gitignore`에 `KakaoTalk_Chat_*`. 첫 적재 99건, 멱등성(같은 CSV 재실행 0건) 확인. 지시서 `docs/tasks/2026-09-06-kakao-tips-ingest.md`.
- **2026-08-28 (v2.7.1)** — 토픽 분류의 일시적 서버 오류(5xx) 재시도 추가. `scheduler.js` 분류 catch 블록의 재시도 대상을 429/quota → +`5xx`·`UNAVAILABLE`·`overloaded`·`high demand`로 확장하고 지수 백오프(2→15초 상한)를 적용, 401/403은 즉시 중단으로 명시, `keysCount > 1` 조건을 키 교체에만 적용해 키 1개 환경에서도 재시도되게 했다. 재시도 소진 시 `cls`가 `undefined`인 채 `cls.topics`로 진입하던 잠복 TypeError 경로를 가드 2개로 차단. 지시서 `docs/tasks/2026-08-28-classify-transient-retry.md`.
- **2026-08-19 (v2.7)** — 재생목록 쓰기 성공/실패 계측 도입. `.quota_state.json`에 `ok`/`fail` 추가(하위호환 기본값 0), `consumeQuota(units, outcome)`로 확장해 `addToPlaylist` 양쪽 경로에서 계상. 텔레그램 큐 블록을 쓰기 결과 3분기(성공/전부실패/시도없음) + 순감 기준 소진 예상일로 교체 — v2.5 이후 "시도했으나 전부 실패한 날"을 구조적으로 감지하지 못하던 구멍을 막았다. 지시서 `docs/tasks/2026-08-18-write-outcome-metrics.md`.
- **2026-08-17 (v2.6)** — quota 일 경계를 UTC → 태평양시(PT)로 교정. `todayKey()`를 `Intl` 기반으로 바꾸고 export해 `scheduler.js:1475`이 같은 키를 쓰게 했다(텔레그램 오경보 제거). KST 09:00~16:00 동안 스로틀이 무력화되던 구간을 없앴다. 지시서 `docs/tasks/2026-08-17-quota-day-boundary.md`. 커밋 `7eb112c`.
- **2026-08-17 (v2.5)** — 레포를 `Projects/` 하위로 이관. 대기 큐 안전장치 도입(중복 방지·연속 실패 10회 차단기·dead-letter 격리·실패 요청 quota 계상), `scripts/clean_pending_queue.js` 신규, `.gitignore` 패턴 수정. OAuth 토큰을 「타이쿤안」 채널로 재발급하고 GCP 게시 상태를 프로덕션으로 전환. 큐 5,392 → 2,365 정리. 커밋 `66ab4a2`.
- **2026-05-21** — 최초 작성.
