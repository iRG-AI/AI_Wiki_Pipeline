# 명령 모음 · OAuth 계정 일치 검증 (루트 CLAUDE.md 「Commands」에서 이관 — 2026-11-11)

> 명령을 실행하기 전에 읽는다. 루트 CLAUDE.md 와 어긋나면 **루트가 우선**한다. 아래는 옮기기 전 본문이다(글자 그대로).

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

# 회귀 테스트 20종 — 네트워크 0회, 실제 장부·Vault·.env 무관 (데몬과 같은 인터프리터로)
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
/opt/homebrew/bin/node scripts/test_proposals.js             # 33/33  (v4.20) 제안함 — 읽기·승인(스킬 설치)·409·보류·거절·되돌리기 (임시 폴더)
/opt/homebrew/bin/python3 scripts/test_skill_review.py       # 55/55  (v4.20) 매일 Wiki 검토 — 대상·검증·기준점·알림·(v4.21) 투자·backfill·꿀팁 우선 (가짜 claude·가짜 텔레그램)

# (2026-10-31) 회귀 테스트 20종 한 번에 — 마지막 줄 RESULT: 20/20 통과, 실패하면 exit 1
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
# 매일 Wiki 검토 (v4.20)
/opt/homebrew/bin/python3 skill_review.py --dry-run     # 대상 건수만 (호출 0 · 쓰기 0 · 발송 0)
/opt/homebrew/bin/python3 skill_review.py --days=7      # 시험 (data/proposals/trial/, 기준점 불변)
/opt/homebrew/bin/python3 skill_review.py --backfill=30 # (v4.21) 지난 자료 1회 훑기 → trial/ 15건 (--dry-run 병용)
launchctl start com.irichgreen.skill-review

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
