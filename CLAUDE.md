# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

- **대표님과 직접 대화하는 메인 세션은 PM(pm-wiki) 이다 — 세션을 시작하면 `.claude/pm/PM_ROLE.md` 를 읽고 따른다** (2026-11-04 대표님 결정 · Claude Desktop(Code 탭)에서 이 저장소로 연 세션 · `./pm-wiki.sh` 로 띄워도 같다). 워커 서브에이전트(`implementer` · `verifier` · `investigator` · `scribe`)는 이 줄을 따르지 않는다.

**현재 버전: v4.19.8** (2026-11-08) · 레포 경로: `<REPO_ROOT>` = `~/Dev/AI_Wiki_Pipeline` · GitHub `iRG-AI/AI_Wiki_Pipeline`

> (경위: [배경 §버전별 한 줄 요약](docs/claude_md_background.md#bg-versions)) — v4.0~v4.17 중 규칙 문장이 없는 줄 · 버전 상세는 `docs/changelog/`
> v4.10: 꿀팁 「기타」 + 태그 없음(노션 이관 때 기본값 그대로 남은 행)은 사람이 고른 값으로 보지 않고 `recategorize_tips.py` 가 다시 매긴다(`blank_default`). 꿀팁 제목 3차 25건(URL 추정 제목 → 원문 제목, `retitle_tips.py`) 뒤 재분류 — 「기타」 66 → 42.
> v4.12: promo_main 만으로 판매 제외하지 않는다 — 영상 요약 신호에 `promo_share`(판매 멘트 비중 0~1)·`promo_subject`(본론 자체가 자기 상품)를 더하고 `promo_main AND (promo_share ≥ 0.5 OR promo_subject)` 일 때만 제외(끝에 자기 상품을 잠깐 알린 영상의 오판 3건). 지금보다 좁기만 하고 장부 무변경.
> v4.18: 꿀팁 두 번째 입구 — 휴대폰 공유 → 텔레그램 전용 봇 방. 정시 실행마다 `telegram_tips_ingest.py` 가 봇의 `getUpdates` 를 읽어 카톡과 같은 엔진(`kakao_ingest.py` 의 `existing_keys`·`resolve_titles`·`plan_rows`·`insert_rows`)으로 같은 장부 `tips` 에 넣는다. 읽은 위치(offset)·마지막 정상 수신 시각은 장부 `meta` 키 2개(tips 와 같은 트랜잭션), 스키마 무변경. 카톡 경로는 그대로(안전망).
> v4.19: 꿀팁 판정 글자에서 메시지 속 URL 을 뺐다(`guess_meta` — 노션 주소가 `Notion` 태그→「지식관리」가 되던 오분류, 사람이 쓴 「노션」 글은 그대로) · 인스타 공유 파라미터 `igsh`·`dlrf` 제거 · 인스타 추정 제목 「인스타 릴스/게시물 (제목 미확인)」 · 제목 「Instagram」·「Login • Instagram」 거부 · `recategorize_tips.py --ids=` (지정 행을 규칙 값으로 보고 다시 매김, `RESULT_JSON.forced`). 장부 스키마 무변경.

> 2026-10-16에 `~/Documents/Claude/Projects/AI_Wiki_Pipeline` → `~/Dev/AI_Wiki_Pipeline` 로 이관했습니다(Google Drive 백업 밖 · 옛 자리에 링크). launchd 4개(server · wiki-ingest · wiki-lan · ytsummarizer)도 새 경로로 바꿨습니다(원본 `*.plist.bak.20261016`).
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
/opt/homebrew/bin/python3 kakao_ingest.py --no-lookup        # (v4.8) 원문 제목 조회 없이 (URL 추정 제목 그대로)
# 텔레그램 전용 봇 → 장부 tips (v4.18, 스케줄러가 --apply 로 자동 호출). .env TIPS_BOT_TOKEN·TIPS_BOT_CHAT_ID
/opt/homebrew/bin/python3 telegram_tips_ingest.py            # dry-run (장부·meta 쓰기 0 · 답장 0)
/opt/homebrew/bin/python3 telegram_tips_ingest.py --apply    # 장부에 넣고 봇 방에 답장
/opt/homebrew/bin/python3 telegram_tips_ingest.py --whoami   # 봇 방 chat id 를 터미널에만 찍는다
/opt/homebrew/bin/python3 lib/title_fetch.py <URL> ...       # (v4.8) 링크 하나씩 제목 조회만 해 보기 (장부 무관)

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

# 회귀 테스트 18종 — 네트워크 0회, 실제 장부·Vault·.env 무관 (데몬과 같은 인터프리터로)
/opt/homebrew/bin/node scripts/test_scheduler_guards.js      # 37/37  장부 캐시·재시도·배치 조회(길이·공개 상태)·시트 미러·장부 백업 훅·실행 실패 알림·요약 방식 저장·재요약 단계 무해 · (v4.18) 텔레그램 꿀팁 훅
/opt/homebrew/bin/node scripts/test_video_summary.js         # 35/35  (v4.6) 실제 영상 요약 — 요청 모양·영상 토큰 0·대체 경로·403 연속·분량 상한·등급 · (v4.6-b) 모델별 thinking·대체 없음·예약·bad_summary 사유 · (v4.11) 5xx 상한 · (v4.12) 판매 비중·본론 신호 · (v4.13) 모델·키별 분량 · (v4.17) not_ai 토픽 조건 (가짜 요청)
/opt/homebrew/bin/node scripts/test_classifier.js            # 8/8    (v4.14) 토픽 분류 — 모델 기본값·CLASSIFY_MODEL·모델별 thinking·요청 주소·한글 청크 경계·allowedSet·오류 문구 (가짜 https)
/opt/homebrew/bin/node scripts/test_resummarize.js           # 12/12  (v4.6-b) 기존분 재요약 — 후보·장부 갱신·stale·건너뜀/실패/중단·하루·실행 상한 · (v4.11) 5xx 조기 중단·3회 건너뜀 · (v4.17) 후보 토픽 (임시 장부, 가짜 요약기)
/opt/homebrew/bin/python3 scripts/test_verify_library.py     # 16/16  장부 ↔ Vault 대조 (임시 장부·Vault)
/opt/homebrew/bin/python3 scripts/test_retitle_tips.py       # 49/49  꿀팁 제목 보완 (임시 장부·Vault·백업 폴더)
/opt/homebrew/bin/python3 scripts/test_wiki_ingest.py        # 64/64  Wiki 추출 누적·재렌더·backfill(v4.6-b 영상 요약 소스만·stale)·씨앗·품질 제외·항목 0 안내 페이지 + 장부 스키마 이전 v1·v2 → v3 (가짜 Gemini)
/opt/homebrew/bin/python3 scripts/test_kakao_ingest.py       # 42/42 (v4.19 +5)  카톡 → 장부 tips · (v4.8) 원문 제목 조회 대상·교체·실패 무해·끄기·상한 (가짜 조회)
/opt/homebrew/bin/python3 scripts/test_title_fetch.py        # 44/44 (v4.19 +1)  (v4.8) 링크 제목 조회 — 노션 id·API·oEmbed·og:title·실패 사유·제목 정리 (가짜 응답)
/opt/homebrew/bin/python3 scripts/test_recategorize_tips.py  # 57/57 (v4.19 +5 --ids)  (v4.9·v4.10) 꿀팁 분류 규칙(노션 주소·한글 표기) + 기존 꿀팁 재분류·출처 정리 + 빈 기본값 (임시 장부·Vault·백업 폴더)
/opt/homebrew/bin/python3 scripts/test_sync_obsidian.py      # 32/32  장부 → Vault (임시 Vault) · (v4.6-b) 재요약 노트 요약 절 제자리 교체
/opt/homebrew/bin/python3 scripts/test_sheet_mirror.py       # 45/45  시트 미러 (가짜 Apps Script 서버가 gas/sheet_mirror.gs 를 그대로 실행)
/opt/homebrew/bin/python3 scripts/test_build_wiki_index.py   # 15/15  재구성 같은 내용 안 쓰기 · 검색 인덱스 프론트매터 한정 · grade: exclude 제외 · (v4.7) 화면 필터용 메타
/opt/homebrew/bin/node scripts/test_wiki_search.js           # 34/34  (v4.7) 검색 화면 API — 전체 목록·전체 점수·비슷한 노트·노트 본문 + 집 안 서버 경로 (임시 인덱스·Vault, 가짜 Gemini)
/opt/homebrew/bin/python3 scripts/test_backup_library.py     # 50/50  장부 백업 (임시 폴더 — 하루 1회 · 보관 규칙 · 드라이브 빠짐)
/opt/homebrew/bin/python3 scripts/test_tips_bot.py           # 25/25  (v4.18) 텔레그램 꿀팁 입구 — 저장·dup·허용 밖·offset·치명 응답·429·5xx·답장 실패·토큰 미노출 (가짜 urlopen·임시 장부)
/opt/homebrew/bin/python3 scripts/test_readme_changelog.py   # 9/9    (v4.19.2) README 요약표 ↔ docs/changelog 월별 파일 구조 (읽기만)
/opt/homebrew/bin/python3 scripts/test_claude_md_budget.py   # 6/6    (v4.19.6) CLAUDE.md 크기·필수 제목·배경 앵커 (읽기만)

# (2026-10-31) 회귀 테스트 18종 한 번에 — 마지막 줄 RESULT: 18/18 통과, 실패하면 exit 1
scripts/run_all_tests.sh             # all | js | py
# (2026-10-31) 실행 PM 세션 띄우기 (Opus + 워커 서브에이전트, 「운영 체계」 절)
./pm-wiki.sh                         # --rc 면 Remote Control

# 대기 큐 정리 (중복 제거 + dead-letter 격리) — 기본 dry-run
node scripts/clean_pending_queue.js
node scripts/clean_pending_queue.js --apply

# 장부 ↔ Vault 대조 (읽기 전용, 네트워크 없음) — 통과 0 · 실패 1, 마지막 RESULT_JSON 의 vault_missing·tips_missing 0
/opt/homebrew/bin/python3 scripts/verify_library.py

# 꿀팁 제목 보완 (v4.4) — CSV record_id,old_title,new_title. 기본 dry-run, --apply 는 정시 실행 창(매시 50분~다음 시 20분) 밖에서
/opt/homebrew/bin/python3 scripts/retitle_tips.py <CSV>
/opt/homebrew/bin/python3 scripts/retitle_tips.py <CSV> --apply

# 꿀팁 분류 보정 (v4.9) — 규칙이 매긴 카테고리·태그(+ v4.10 빈 기본값 「기타」·태그 없음)를 지금 규칙으로 · 출처 https:// 접두 정리. 기본 dry-run, --apply 는 정시 실행 창 밖에서
/opt/homebrew/bin/python3 scripts/recategorize_tips.py
/opt/homebrew/bin/python3 scripts/recategorize_tips.py --apply
/opt/homebrew/bin/python3 scripts/recategorize_tips.py --ids=<record_id>[,<record_id>…]   # (v4.19) 지정 행을 규칙 값으로 보고 다시 매김 (dry-run 기본, --apply 병용)

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
    → lib/classifier.js:classifyTopics()  [(v4.14) Gemini 3.5 Flash-Lite, 토픽 0~5개]
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
- (v4.14) 분류 모델은 `gemini-3.5-flash-lite`(2.5 Flash 하루 요청 한도를 영상 요약에 남긴다). 같은 프롬프트로 2.5 Flash 보다 토픽을 적게(비교 20편 4.4 → 2.5개) 붙인다 — 프롬프트의 「추상 토픽 남발 금지」를 지킨 결과라 의도된 변화다(대표님 결정 10-15). 예전 분류로 되돌릴 때는 코드가 아니라 `.env CLASSIFY_MODEL=gemini-2.5-flash`. 응답은 `Buffer.concat` 으로 모은다 — `chunks += c` 로 되돌리지 말 것(한글 토픽이 청크 경계에서 깨져 allowedSet 에서 떨어진다).

**Gemini API 최적화 (중요)**: Gemini 2.5 Flash 모델 사용 시 내부 추론 과정에서 과다한 "Thinking 토큰" 과금을 방지하기 위해 반드시 API 호출 옵션에 `generationConfig: { thinkingConfig: { thinkingBudget: 0 } }`를 적용해야 합니다 (비용 85% 절감 효과). (v4.6-b) 3.x 모델(`gemini-3.5-flash-lite` 등)은 `thinkingBudget` 을 400 INVALID_ARGUMENT 로 거절한다 — `thinkingConfig: { thinkingLevel: 'minimal' }`(`lib/video_summary.js:thinkingConfigFor`).

**토픽 추가 시**: `playlists.json`에 새 항목 추가 + `build_obsidian_wiki.py`의 `VALID_NOTION_TAGS` 동기화 필수.

**Vault 경로 중첩 (2026-09-19)**: 실제 Vault는 `~/Documents/Obsidian/AI LLM Wiki/AI LLM Wiki` (바깥 `AI LLM Wiki/`는 빈 껍데기, `README-여기가-아님.txt` 있음). 동작에 문제 없음. 이 경로는 `sync_obsidian.py`·`build_obsidian_wiki.py`·`wiki_config.py`·`lib/wiki_search.js`·`cleanup_duplicates.py`·`notion_to_obsidian.js` 6곳 + `legacy_scripts/` 2곳 + Obsidian 앱 등록에 박혀 있다. **v3.3(2nd_Brain 2단계 — `build_search_index.py`에 `_Brain/` 포함)과 같은 작업지시서로 한 단계 승격한다. 그 전에 옮기지 말 것.** 절차: 데몬 전부 stop(`wiki-lan` 포함 — 같은 Vault 경로를 읽는다) → `mv` → 8파일 치환 → Obsidian 재등록 → `--orphans-dry-run --no-tips`로 "notion_id 2,542·고아 0" 확인 → 인덱스 재빌드 → 재기동.

**server.js 보안**: `127.0.0.1` 전용 바인딩. CORS는 `localhost:3000`만 허용. IP당 분당 120요청 rate limit. 노션 프록시(v4.0 2-b)·`/api/sync-obsidian`(v4.0 3단계)은 제거됐다 — 다시 만들지 말 것.

### launchd 데몬

| 라벨 | 실행 대상 | 스케줄 | 인터프리터 |
|------|-----------|--------|-----------|
| `com.irichgreen.server` | `server.js` (포트 3000) | `KeepAlive`, `RunAtLoad` — 상주 | `/opt/homebrew/bin/node` |
| `com.irichgreen.ytsummarizer` | `scheduler.js` (v4.15 `caffeinate -i` 로 감쌈) | 00 / 06 / 12 / 18시 | `/opt/homebrew/bin/node` |
| `com.irichgreen.wiki-ingest` | `wiki_ingest.py` (증분 + backfill + 재렌더, v4.16 `caffeinate -i` 로 감쌈) | 매일 17:30 | `/opt/homebrew/bin/python3` |
| `com.irichgreen.wiki-lan` | `wiki_lan_server.js` (포트 3100) | `KeepAlive`, `RunAtLoad`, `ThrottleInterval 60` — 상주 | `/opt/homebrew/bin/node` |

- **실제 동작하는 plist는 `~/Library/LaunchAgents/`에 있다.** 레포 루트의 plist 4개는 그 원본이며 모두 실경로(`<REPO_ROOT>` 의 절대경로)가 들어 있다. **원본은 설치본과 같게 유지한다** — 2026-10-12 대조에서 `wiki-ingest` 원본만 옛 값(03:00 · `/usr/bin/python3` · `--full`)이라 설치본(17:30 · Homebrew python3 · 증분)으로 맞췄다. 확인: `diff <(plutil -convert xml1 -o - ~/Library/LaunchAgents/<라벨>.plist) <(plutil -convert xml1 -o - <라벨>.plist)`. 예전에 `server`·`ytsummarizer` 두 개에 있던 `/Users/사용자명/youtube-notion-app` 플레이스홀더는 제거했다.
- **(v4.15) `com.irichgreen.ytsummarizer` 의 `ProgramArguments` 는 `/usr/bin/caffeinate -i /opt/homebrew/bin/node <REPO_ROOT>/scheduler.js` 다.** caffeinate 가 node 를 자식으로 띄우고 node 가 끝날 때까지 유휴 잠자기 방지 단언(`PreventUserIdleSystemSleep`)을 쥔다 — 배터리 설정이 `sleep 1`(1분)이라 덮개를 연 채 자리를 비우면 실행 도중 잠들 수 있었다. 종료 코드는 node 것을 그대로 돌려준다(10-16 실측). **덮개를 닫은 잠자기(Clamshell)·이미 잠든 맥은 막지 못한다**(10-15 12:00 실패 = 11:54 Clamshell Sleep, 배터리 36%) — 그 경우는 v4.2 알림과 다음 실행의 이어 처리로 버틴다. 강제로 막는 `pmset disablesleep` 은 가방 속 발열 위험이라 쓰지 않는다. `launchctl list` 의 PID 는 caffeinate 이고 `pgrep -f scheduler.js` 는 두 줄(caffeinate·node)이 나온다. 실행 중 확인: `pmset -g assertions | grep caffeinate`. `server.js` `/api/master-ingest` 로 띄운 수동 실행은 감싸지 않는다(범위 밖). caffeinate 를 빼지 말 것.
- **(v4.16) `com.irichgreen.wiki-ingest` 도 같다** — `/usr/bin/caffeinate -i /opt/homebrew/bin/python3 <REPO_ROOT>/wiki_ingest.py`. 실행 중 확인 `pmset -g assertions | grep caffeinate`, 지난 실행은 `pmset -g log | grep "17:3.*caffeinate"`(macOS 로그에는 `Summary`·`ClientDied` 로 찍힌다 — 다른 앱도 caffeinate 를 수시로 띄우므로 시작 시각으로 가린다). caffeinate 를 빼지 말 것.
- 각 plist는 `ProgramArguments`·`WorkingDirectory` **2곳에 절대경로**가 박혀 있다. 경로 변경 시 8군데(4개 × 2) 동기화 + `plutil -lint` + unload/load.
- **레포 경로 자체를 바꿀 때 함께 고칠 맥 설정(레포 밖):** 설치된 plist 4개, `~/Library/Scripts/rotate_extra_logs.sh` 의 `YTDIR`, Claude Code MCP `wiki-search` 등록(`~/.claude.json` 사용자 범위 — `claude mcp remove`/`add -s user`), 스킬 `kakao-tips-update` 의 경로. 절차·검증은 `docs/tasks/2026-10-13-rename-ai-wiki-pipeline.md`.
- `install-server.sh`·`install-scheduler.sh`는 plist를 `~/Library/LaunchAgents/`로 복사하며 **sed로 이 실경로를 `$APP_DIR`로 치환**한다. 레포 경로를 바꾸면 두 스크립트의 sed 패턴도 같이 고쳐야 치환이 동작한다. `install-wiki-ingest.sh` 는 치환 없이 그대로 복사한다(원본 = 설치본). `deploy.sh` 는 옛 일괄 업로드 스크립트라 쓰지 않는다.
- `com.irichgreen.server`는 상주 프로세스라 **코드를 고쳐도 재기동 전까지 반영되지 않는다.**
- `com.irichgreen.wiki-lan`의 로그(`wiki-lan.log`)는 **`rotate_extra_logs.sh`에 넣지 않는다.** 상주형이라 rename 회전이 안전하지 않다. 대신 서버가 기동·차단·오류만 찍는다.
- **macOS 방화벽의 수신 허용은 node 실행 파일의 실제 경로(Cellar 버전 폴더)에 걸린다**(2026-10-03 실측: 허용 목록에 옛 버전 경로만 남아 있었다). `brew upgrade node` 후에는 경로가 바뀌므로 `wiki-lan`이 살아 있어도 가족 PC에서만 접속이 막힐 수 있다 — 이 맥에서의 `curl`은 정상으로 보일 수 있으니 판정은 다른 기기로 한다. 재기동 + 방화벽 재허용이 한 세트다.
- **`brew upgrade` 후에는 상주 데몬을 반드시 재기동한다.** 데몬은 기동 시점의 Cellar 경로를 물고 도는데, 업그레이드로 그 폴더가 삭제되면 이후 지연 import가 전부 실패한다. 이미 로드된 모듈은 멀쩡히 동작해 **부분 실패로 나타나므로 알아채기 어렵다.** (2026-08-17 자매 프로젝트 실장애)
- **`brew upgrade` 뒤 점검 순서 (2026-10-30 사건):** 의존 라이브러리(simdjson 등)만 올라가도 node 가 `dyld: Library not loaded` 로 기동 즉시 죽을 수 있다. 정시 실행은 `scheduler.log` 에 아무것도 남기지 않고(`~/Library/Logs/irichgreen/ytsummarizer-err.log` 에만) 다음 실행의 `[직전 실행 점검]` 간격 경고로만 드러나며, 상주 데몬은 KeepAlive 재시작 실패를 반복한다(`launchctl list` 종료 코드 -6·78). 순서: ① `grep -l dyld ~/Library/Logs/irichgreen/*-err.log` ② `/opt/homebrew/bin/node -v` · `/opt/homebrew/bin/python3 -V` ③ `launchctl list | grep irichgreen` ④ 상주 데몬 재기동 ⑤ 방화벽 node Cellar 경로 재허용(가족 PC 로 판정) ⑥ `scripts/run_all_tests.sh`. node 26.13 부터 로그 날짜가 `2026/10/31 오후 12:00:05` 꼴이다(이전 `2026. 10. 31. 오후 …`) — 날짜로 grep 하는 명령은 두 꼴을 다 쓴다.

### 보안 — 절대 커밋 금지

`.gitignore` 대상: `.env`, `.env.*`, `node_modules/`, `__pycache__/`, `*.log`, `playlists.json`, `.DS_Store`, `.claude/settings.local.json`, `wiki_index.json`, `wiki_index.vec`, `.migrate_state.json`, `.quota_state.json`, `.wiki_state.json`, `.wiki_quota.json`, `pending_playlist_adds*`, `.run_state.json*`(v4.2), `.video_quota.json`(v4.6), `data/`(장부), `KakaoTalk_Chat_*`, `Claude outputs/`, `.codex/`(2026-11-08, Codex CLI 로컬 설정). 시트 미러는 상태 파일을 만들지 않는다(워터마크는 장부 `meta`). 장부 백업도 상태 파일이 없고(오늘 날짜 파일 유무로 판단) 백업은 `data/backups/` 라 `data/` 패턴에 들어간다.

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

## 운영 체계 — pm-wiki · 워커 · Cowork (2026-10-31~)

| 주체 | 어디서 | 하는 일 | 하지 않는 일 |
|---|---|---|---|
| **pm-wiki** (실행 PM) | Claude Code 메인 세션 — Claude Desktop(Code 탭)에서 이 저장소로 연 세션 또는 `./pm-wiki.sh` (Opus, 지침 `.claude/pm/PM_ROLE.md`) | 지시서 작성 → 워커 호출 → 검수 판정 → `git push`(검수 통과 뒤 승인 없이, 2026-11-04~) · 작은 수정(한 파일 20줄 안팎, 확인 방법이 뻔한 것)은 직접 고치고 테스트를 직접 돌림 · 인수인계 `.claude/pm/local/HANDOFF.md` | 작은 수정 밖의 코드·문서 직접 수정 · 워커가 도는 동안 파일 수정 |
| **워커** | pm-wiki 의 서브에이전트 `.claude/agents/` | `implementer`(Sonnet) 실행 · `verifier`(Opus, 읽기 전용) 검수 · `investigator`(Opus, 읽기 전용) 조사·설계 · `scribe`(Haiku) 문서 기록 | 지시서 범위 밖 변경 · `git push` |
| **Cowork(CW)** | claude.ai 프로젝트 「AI Wiki Pipeline」 | 정시 실행 판정·관찰, 대표님 상담(등급 오판 등 결정 자료), 조사·설계 메모, 다른 프로젝트 연계 | 레포·장부·데몬 쓰기 |

- 일의 흐름: 대표님 지시 또는 XP 요청서 → pm-wiki 가 `docs/tasks/` 지시서(워커 한 번에 끝나는 크기 — 고칠 파일 10개 초과면 2~3개로) → implementer → verifier(기준표 ✅/❌) → 미달이면 같은 implementer 에 재지시(지시서당 3회까지) → push → 통과 보고. 작은 수정은 pm-wiki 가 직접 고치고 `scripts/run_all_tests.sh` 를 직접 돌린다(기록은 커밋 메시지 · `docs/claude_history.md` 맨 위).
- (2026-11-04~) 승인은 **대표님의 작업 요청 메시지 자체**다 — 그 요청 범위 안의 지시서·워커 실행은 따로 승인받지 않는다(XP 요청서는 대표님이 진행하라고 한 메시지부터). 지시서가 요청 범위를 넘거나 고를 안이 갈리면 그 점만 묻는다. 범위 밖 변경·지시서에 없는 장부 쓰기·외부 발송·launchd/`.env`/OAuth·운영 상태 파일 손수정은 멈추고 묻는다. `git push` 는 검수 통과·회귀 통과 뒤 PM 이 승인 없이 한다(2026-11-04 대표님 결정, `--force` 금지).
- CW ↔ pm-wiki 는 XP 보드 `~/Documents/Claude/XP/`(`open/`·`done/`, 번호 `XP-<발주코드>-<MMDD>-<순번>`, `from: cw-wiki · to: pm-wiki` 또는 반대). CW 는 Claude Code 세션이 아니라 메시지를 받지 못한다 — 파일로만 주고받는다.
- (2026-11-03~) XP 보드 규칙 v2 의 정본은 `~/Documents/Claude/XP/README.md` — 세션 시작 때 `open/` 확인, 새 요청서는 `~/Documents/Claude/XP/new_xp.sh <발주코드>`(WIKI 등)로만 만들고, 파일명·번호는 바꾸지 않으며(상태는 본문 「상태」 줄에만), 상대에게는 경로 대신 번호로 말한다. 11-03 이전 `XP-MMDD-A` 파일은 번호 그대로.
- 훅(`.claude/settings.json`): `guard_run_window.sh`(PreToolUse) — 장부 쓰기·launchd 조작은 매시 분 50~59·00~20, 코드·plist 편집은 정시 실행·wiki-ingest 창과 실행 중에 막는다. `record_base.sh`(SubagentStart) + `gate_subagent_stop.sh`(SubagentStop) — 워커가 끝나기 전에 공개 레포 규칙(개인 절대경로·맥 이름·`.env` 값)·gitignore·`README.html`·plist/셸 문법·회귀 15종을 검사하고, 미통과면 3회까지 돌려보낸다(`/tmp/cc-gate-AI_Wiki_Pipeline-<세션>.log`).
- `.claude/agents/`·`.claude/pm/PM_ROLE.md`·`.claude/hooks/`·`.claude/settings.json`·`pm-wiki.sh` 는 git 추적. `.claude/agent-memory/`(워커 메모리)·`.claude/pm/local/`(인수인계)·`.claude/settings.local.json` 은 gitignore.

## 산출물 규칙

- 커밋 전 **`README.md`만** 갱신한다. **`README.html`은 v3.0에서 폐지 — 다시 만들지 않는다.** (2026-09-06)
- 버전 이력 (v4.19.1~, ERP·asset_manage 방식): README 「📝 버전 히스토리」 = 요약 이력 표(3칸 `| **[vX.Y.Z](docs/changelog/YYYY-MM.md#vX-Y-Z)** | 날짜 | **제목** |`, 버전 내림차순) + 월별 파일 링크뿐. 상세는 `docs/changelog/YYYY-MM.md` 맨 위에 헤딩 바로 윗줄 앵커 `<a id="vX-Y-Z"></a>` 와 함께. 규칙 정본 `docs/changelog/README.md`, 감지 `scripts/test_readme_changelog.py`.
- 버전 부여: 단일 줄 · HEAD 기준(`git log --oneline -1`) · 새 행이 요약표 맨 위가 아니면 번호가 틀린 것 · push 한 번호는 고쳐 쓰지 않는다. 메이저 = 아키텍처 확장(소스·저장소·합성 엔진 추가), 마이너 = 기능·동작·안정성, **패치 = 수정·문서·테스트 — 문서만 고친 커밋도 PATCH 를 올린다(2026-11-04~, 그 전 「버전 유지」 이력 줄은 그대로 둔다).** `-a`·`-b` 접미사는 새로 만들지 않는다. MAJOR, 또는 소스·저장소·실행 경로·예약 작업을 바꾸는 MINOR 는 같은 커밋에서 README 본문도 맞춘다.
- `CLAUDE.md`는 구조·제약이 바뀔 때 갱신하고, 이력은 `docs/claude_history.md` 맨 위에 날짜와 함께 남긴다(2026-11-06~, 그 전 이력도 그 파일에 있다).
- `AGENTS.md`는 **git 추적 대상**이다(2026-09-08~). `CLAUDE.md`와 함께 갱신하고, 두 문서가 어긋나면 **`CLAUDE.md`가 이긴다**.
- 문서에 **개인 절대경로를 새로 쓰지 않는다**(2026-09-09~). 앞으로 추가·수정하는 줄은 `<REPO_ROOT>/...` 또는 `~/...` 표기를 쓴다. 기존 표기는 소급 정리하지 않는다.
- 작업지시서는 `docs/tasks/YYYY-MM-DD-<슬러그>.md`(번호 `[CC-MMDD-X]`) — pm-wiki 가 쓰고 워커가 실행한다(「운영 체계」 절). Cowork 는 XP 요청서로 pm-wiki 에 발주한다.
- `git push`는 검수·회귀 통과 뒤 PM 이 승인 없이 한다(2026-11-04~, `--force` 금지).

## 변경 이력

→ `docs/claude_history.md` (운영 이력 · 새 줄은 그 파일 맨 위) · 버전 이력은 `docs/changelog/`
