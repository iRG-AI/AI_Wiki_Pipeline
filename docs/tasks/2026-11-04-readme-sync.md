# [CC-1104-D] README 현행화 — v4.6~v4.19 반영 (문서만, 버전 유지)

- 작성: 2026-11-04 · pm-wiki (대표님 요청 「readme.md 를 전수 조사해서 낡은 것이 있으면 현행화」)
- 실행: `implementer`(Sonnet · medium) → 검수 `verifier`(Opus · high)
- 근거: investigator 전수 대조(HEAD `ea5cb13`, 읽기 전용) — 아래 표의 「근거」 열이 그 결과다.
- 승인 범위: `README.md` 수정 · `CLAUDE.md`·`AGENTS.md` 「변경 이력」 1줄씩 · 이 지시서 커밋 1건. push 는 PM 이 검수 뒤 한다.

## 배경

README 본문(1~478행)이 v4.2~v4.5 시점에 머물러 있다. v4.18 텔레그램 꿀팁 입구가 제목·개요·흐름도·사이클 표·구조·장부 설명에 없고, v4.6 실제 영상 요약·v4.6-b 재요약·v4.14 분류 모델·회귀 테스트 16종·push 규칙이 반영되지 않았다. 마스터 모드는 통계를 갱신하지 않는데 README 는 갱신한다고 적는다. 버전 이력(479행~)은 v4.0~v4.19 가 빠짐없이 맞다 — 고치지 않는다.

## 범위

- 바꿀 것: `README.md` 의 아래 표 항목 · `CLAUDE.md`·`AGENTS.md` 「## 변경 이력」 맨 위 1줄(같은 문구) · 이 지시서
- 바꾸면 안 되는 것: 코드·설정·장부·Vault · README 「🔄 버전 관리」 절(479행~)의 표·상세 본문 · README 전체 구성(절 순서·제목 체계 개편은 범위 밖) · 머리 버전 블록 9~27행
- 공개 레포: 개인 절대경로·맥 이름·집 네트워크 대역·`.env` 값을 새로 쓰지 않는다(`<REPO_ROOT>`·`~` 표기).

## 확인(먼저)

| # | 명령 | 기대값 |
|---|---|---|
| 0-1 | `git log --oneline -1` | `ea5cb13` 또는 그 뒤 PM 커밋(README 무변경) |
| 0-2 | `git status --porcelain -uall` | `?? docs/tasks/2026-11-04-readme-sync.md` 한 줄 |
| 0-3 | `wc -l README.md` | `1029` |
| 0-4 | `grep -n "회귀 테스트 15종" README.md` | 232·234 행 두 줄 |

행 번호는 0-3 기준이다. 앞 항목을 고치면 뒤 행이 밀리므로 **글 내용으로 찾아** 고친다.

## 단계 — 바꿀 곳 (README.md)

| # | 행 | 지금 글(짧게) | 근거 | 바꿀 글 |
|---|---|---|---|---|
| 1 | 1 | `# 🎬 YouTube + 📎 카카오톡 → 로컬 장부 → …` | v4.18 꿀팁 입구 둘(`telegram_tips_ingest.py`, `scheduler.js` 의 `runTipsBot`) | `# 🎬 YouTube + 📎 카카오톡·텔레그램 → 로컬 장부 → Obsidian LLM Wiki (+ 구글 시트 미러)` |
| 2 | 5 | 「Gemini AI로 자동 요약하고, 카카오톡 '나와의 채팅'에 저장해 둔 AI 자료 링크를 자동 수집하여」 | v4.6 실제 영상 요약, v4.18 | 그 구절을 `YouTube 재생목록의 영상을 **Gemini AI**가 실제 영상을 보고 요약·분류하고, 카카오톡 '나와의 채팅'과 텔레그램 전용 봇 방에 공유해 둔 **AI 자료 링크**를 자동 수집하여` 로 (문장 나머지는 그대로) |
| 3 | 28-29 | v4.18·v4.19 줄(반말·함수 이름 위주) | 9~27행의 존댓말·사용자 관점과 말투 맞춤 | 두 줄을 각각 다음으로: `> v4.18: 꿀팁 두 번째 입구 — 휴대폰에서 공유한 링크를 텔레그램 전용 봇 방으로 받습니다. 정시 실행마다 \`telegram_tips_ingest.py\` 가 봇 방을 읽어 카톡과 같은 엔진으로 같은 장부 \`tips\` 에 넣고 봇 방에 답장합니다. 읽은 위치는 장부 \`meta\` 에 두어 스키마 변경이 없고, 카톡 경로는 안전망으로 그대로 둡니다.` / `> v4.19: 메시지에 붙은 URL 을 꿀팁 분류 판정 글자에서 뺐습니다(노션 주소만 붙어 있어도 「지식관리」가 되던 오분류). 인스타 공유 파라미터(\`igsh\`·\`dlrf\`) 제거, 인스타 추정 제목, 로그인 화면 제목 「Instagram」 거부, 지정 행만 다시 분류하는 \`recategorize_tips.py --ids=\` 를 더했습니다. 장부 스키마 무변경.` |
| 4 | 31 | 「v3.0부터 지식 소스는 YouTube 영상 + 카카오톡 링크 두 갈래」 | v4.18 | `> v3.0부터 지식 소스는 **YouTube 영상 + AI 자료 링크(꿀팁)** 두 갈래이고(꿀팁 입구는 카카오톡 CSV · v4.18 텔레그램 전용 봇), 장부 이후 단계(Obsidian 노트 → Wiki 합성 → MOC)는 두 소스가 공유합니다.` |
| 5 | 37-38 | AI Model 줄 「Gemini 2.5 Flash — 요약 및 분류 엔진」 | 분류 `lib/classifier.js` 3.5 Flash-Lite · 재요약 `lib/resummarize.js` · 검색 `lib/wiki_search.js` 임베딩 | AI Model 줄을 `* **AI Model**: **Gemini 2.5 Flash**(신규 영상 요약 · Wiki 합성) · **Gemini 3.5 Flash-Lite**(토픽 분류 · 기존분 재요약) · \`gemini-embedding-001\`(검색 임베딩)` 로. AI Assistant 줄이 있으면 `* **AI Assistant**: Claude (Anthropic) — Claude Code 실행 PM(pm-wiki) + 워커 서브에이전트` 로 |
| 6 | 46 | 「영상 제목·설명·태그 기반 4섹션 보고서」 | v4.6 `lib/video_summary.js` | `- 🤖 **Gemini AI 자동 요약 (v4.6)** — 공개 영상은 실제 영상(YouTube URL)을 Gemini 에 넣어 4섹션 요약 + 사실 신호를 받고, 안 되면 제목·설명란으로 요약` |
| 7 | 49 | 「통계 자동 업데이트 — 조회수·구독자수 15% 이상 변화 시만 갱신」 | `updateStatsInLibrary` 는 레거시 `processPlaylist` 에서만 호출, 마스터 모드는 중복이면 skip | `- 📊 **통계 자동 업데이트** — (레거시 \`--legacy\` 모드) 이미 있는 영상의 조회수·구독자수가 15% 이상 변하면 갱신. 기본 마스터 모드는 중복 영상을 건너뛰기만 한다` |
| 8 | 50 다음 | 기능 줄 없음 | v4.6-a·v4.6-b·v4.8·v4.18 | 주요 기능 목록 안 적당한 자리에 4줄 추가: `- 📮 **텔레그램 꿀팁 입구 (v4.18)** — 휴대폰 공유 → 전용 봇 방 → 정시 실행마다 \`telegram_tips_ingest.py\` 가 카톡과 같은 엔진으로 장부 \`tips\` 에 넣고 봇 방에 답장` / `- 🏷️ **원문 제목 조회·분류 (v4.8~v4.19)** — 꿀팁 링크의 원문 제목을 가져오고(노션 공개 페이지·유튜브·og:title), 카테고리·태그는 규칙 한 곳(\`lib/kakao_parse.classify\`)에서` / `- 🎚 **품질 등급 (v4.6)** — 판매가 주목적·일반론·AI 무관(토픽 분류도 비었을 때) 영상은 \`grade: exclude\` 로 Wiki 합성·검색에서만 뺌(노트는 남김)` / `- 🔁 **기존분 재요약 (v4.6-b)** — 설명란으로 만든 옛 요약을 정시 실행마다 실제 영상으로 천천히 다시 요약(Gemini 3.5 Flash-Lite, 실패하면 기존 요약 유지)` |
| 9 | 56 | 「장부 저장·카톡·시트·Obsidian 결과 통합 전송」 | 완료 메시지에 📮·🔁 줄 | `- 📱 **텔레그램 알림** — 장부 저장·재요약·카톡·텔레그램 꿀팁·시트·Obsidian 결과 통합 전송` |
| 10 | 58 | 「Mac 로그인 시 서버 자동 시작, 6시간 간격 스케줄러 실행」 | launchd 4개, caffeinate 2개 | `- ⏰ **launchd 자동 스케줄링** — 웹 서버·집 안 검색 서버 상주, 스케줄러 00/06/12/18시 · Wiki 인제스트 17:30 (둘 다 \`caffeinate -i\` 로 감싸 실행 중 유휴 잠자기 방지)` |
| 11 | 62 | `## 🏗️ 시스템 아키텍처 (v4.2)` | | `## 🏗️ 시스템 아키텍처 (v4.19)` |
| 12 | 69-73 머메이드 | 꿀팁 입구가 카톡 하나 | v4.18 | SRC 안에 `U3["휴대폰 공유 →\n텔레그램 전용 봇 방"]` 추가. 카톡 subgraph 다음에 `subgraph TB["📮 ②-b 텔레그램 꿀팁 (telegram_tips_ingest.py, v4.18)"]` / `TBR["getUpdates (offset = 장부 meta.tips_bot_offset)\n허용 chat 하나만 → kakao_ingest 공용 함수\ntips + offset 한 트랜잭션 → 봇 방 답장"]` / `end` / `U3 --> TBR` / `SCHED -->\|"카톡 다음\n--apply"\| TBR` / `TBR --> LIB` |
| 13 | 87 GEMINI 노드 | `geminiSummarize() … 4섹션 요약` | 첫 경로는 `lib/video_summary.js` | `GEMINI["lib/video_summary.js — 실제 영상 요약\nGemini 2.5 Flash · 4섹션 + 사실 신호 → 등급\n안 되면 geminiSummarize() 설명란 요약"]` |
| 14 | 88 CLS 노드 | 토픽 분류만 | v4.17 `regrade` | `CLS["lib/classifier.js\nGemini 3.5 Flash-Lite · 토픽 0~5개 분류\n→ 등급 재판정 (v4.17)"]` |
| 15 | 104 뒤 | 재요약 노드 없음 | `scheduler.js:runResummary` | `RESUM["lib/resummarize.js (v4.6-b)\n기존분 재요약 · 3.5 Flash-Lite\n실행당·하루 상한, 실패 시 기존 요약 유지"]` + `LSAVE --> RESUM --> LIB` (기존 노드 이름이 다르면 그 이름에 맞춘다) |
| 16 | 104 LIB 노드 | `videos · tips · videos_dup · meta` | `wiki_extract` (v4.5) | `LIB[("🗄️ 로컬 장부 data/library.db\nvideos · tips · videos_dup · wiki_extract · meta")]` |
| 17 | 78·130 | WIKI_SCHED 「(증분)」 · WIKI_INGEST 「엔티티/개념 추출」 | v4.5 누적·재렌더, backfill 은 17:30 만 | `WIKI_SCHED["launchd · com.irichgreen.wiki-ingest\n매일 17:30 → wiki_ingest.py (증분 + backfill)"]` · `WIKI_INGEST["wiki_ingest.py\nGemini 2.5 Flash · 엔티티/개념 추출\n→ 장부 wiki_extract 누적 → _wiki 전체 재렌더"]` |
| 18 | 138 TG 노드 | 「YouTube 결과 + 꿀팁 신규 + 시트 + Obsidian 결과」 | | `VAULT --> TG["📱 Telegram 통합 알림 (1개 메시지)\nYouTube·재요약 결과 + 카톡·텔레그램 꿀팁 + 시트 + Obsidian 결과"]` |
| 19 | 152 사이클 2 | 「요약(`geminiSummarize`) → 토픽 분류 → 장부 …」 | #13·#14 | `\| 2 \| YouTube 마스터 인제스트 \| \`scheduler.js\` \| 'AI 영상목록' 신규 영상 \| 요약(\`lib/video_summary.js\` 실제 영상 → 안 되면 \`geminiSummarize\` 설명란) → 토픽 분류(\`lib/classifier.js\`) → 등급 재판정 → 장부 \`videos\` 행 → 토픽 재생목록 추가(\`YOUTUBE_PLAYLIST_SYNC=true\` 일 때만) \| 장부 캐시 대조 후 0건 처리 \|` |
| 20 | 152 뒤 새 행 | 재요약 행 없음 | `runResummary` 는 2b 앞 | `\| 2a \| 기존분 재요약 (v4.6-b) \| \`scheduler.js:runResummary()\` → \`lib/resummarize.js\` \| 장부 \`summary_src != 'video'\` 영상(최신 업로드부터) \| 요약·등급 교체 + 그 소스 \`wiki_extract\` stale \| 실행당·하루(PT) 상한이 차거나 대상 0이면 생략. 5xx·분량 상한이면 그 실행 재요약 중단(기존 요약 유지) \|` |
| 21 | 154 뒤 새 행 | 텔레그램 행 없음 | 카톡 다음 · 시트 앞 | `\| 3b \| 텔레그램 꿀팁 (v4.18) \| \`telegram_tips_ingest.py --apply\` \| 전용 봇 \`getUpdates\`(장부 \`meta.tips_bot_offset\` 이후) \| 장부 \`tips\` 신규 행 + 봇 방 답장 \| \`.env TIPS_BOT_TOKEN\` 이 없으면 건너뜀. 입구가 막히거나 18시간 동안 수신이 없으면 알림 봇이 따로 알림 \|` |
| 22 | 157·161·162 | 사이클 5·9·10 | 재요약 노트 요약 절 교체 · `--no-backfill` · 검색 인덱스 단계 없음 | 5 출력 칸: `VAULT/<토픽>/*.md` (v4.6-b 재요약 노트는 요약 절만 제자리 교체) · 9행: `\| 9 \| Wiki 합성 \| \`wiki_ingest.py --no-backfill\` \| 미처리 노트 \| 장부 \`wiki_extract\` 누적 → \`_wiki/entities\`·\`concepts\`·\`index.md\` 재렌더 \| 신규 노트 없으면 생략 (backfill 은 17:30 launchd 실행만) \|` · 9 뒤 새 행 `\| 9b \| 검색 인덱스 \| \`build_search_index.py\` \| 바뀐 노트 \| \`wiki_index.json\`·\`.vec\` 증분 \| 변경 0이면 생략 \|` · 10 입력 칸: `2·2a·3·3b·4·5~9 결과` |
| 23 | 168 | 머리글 「꿀팁 노트 (v3.0)」 | | `\| \| 영상 노트 \| 꿀팁 노트 (v3.0 카톡 · v4.18 텔레그램) \|` |
| 24 | 184 | scheduler 주석 | 재요약·텔레그램 단계 | `# 자동 스케줄러 (6시간 간격) — YouTube → 장부 → 재요약 → 카톡 → 텔레그램 꿀팁 → 시트 → 백업 → Obsidian → 알림` |
| 25 | 194 뒤 | 구조에 `telegram_tips_ingest.py` 없음 | `git ls-files` | `├── telegram_tips_ingest.py           # (v4.18) 텔레그램 전용 봇 → 장부 tips (카톡과 같은 엔진, 기본 dry-run, --apply / --whoami)` (주변 정렬에 맞춤) |
| 26 | 232·234 | 「회귀 테스트 15종」 | `scripts/run_all_tests.sh` 16종 | 232: `│   ├── run_all_tests.sh               # 회귀 테스트 16종 한 번에 (마지막 줄 RESULT: 16/16 통과)` · 234: `│   └── test_*.{js,py}                 # 회귀 테스트 16종 (네트워크 0회)` |
| 27 | 210·236·237 | deploy.sh·docs/tasks·cowork 문서 주석 | push 규칙(11-04~), 지시서는 pm-wiki, cowork 문서는 안내문 | 210: `# (옛) GitHub 일괄 업로드 스크립트 — 쓰지 않는다 (push 는 검수·회귀 통과 뒤 pm-wiki 가 한다)` · 236: `├── docs/tasks/                        # pm-wiki 작업지시서 (날짜-슬러그.md, 워커가 실행) + patches/` · 237: `├── docs/cowork-project-instructions.md # 안내문 — 옛 Cowork 지침 사본(v2.5)은 git 이력에, 운영 지침은 claude.ai 프로젝트 설정` |
| 28 | 215·224 | library.js·kakao_parse 주석 | `updateResummary`·`classify`·`links_from_messages` | 215: `# (v4.0) 장부 Node 헬퍼 (openLibrary·insertVideo·addTopic·updateStats · v4.6-b 재요약 updateResummary)` · 224: `# URL 추출·정규화·중복 키·제목 추정 · (v4.9) 분류 규칙 classify · (v4.18) links_from_messages (순수 함수)` |
| 29 | 248·251·252 기술 스택 | Runtime·AI·데이터 소스 | | 248: `\| **Runtime** \| Node.js 22.13+ (운영 26.x, 데몬 \`/opt/homebrew/bin/node\`, \`node:sqlite\`), Python 3 (운영 3.14, \`/opt/homebrew/bin/python3\`) \|` · 251: `\| **AI** \| Google Gemini 2.5 Flash(신규 영상 요약·Wiki 합성) · 3.5 Flash-Lite(토픽 분류·재요약) · gemini-embedding-001(검색) \|` · 252: `\| **데이터 소스** \| YouTube Data API v3, 카카오톡 내보내기 CSV, 텔레그램 Bot API(꿀팁 전용 봇 getUpdates) \|` · 표 끝 새 행: `\| **운영** \| Claude Code — 실행 PM \`pm-wiki\`(\`./pm-wiki.sh\`) + 워커 서브에이전트(\`.claude/agents/\`) · 훅(\`.claude/hooks/\`) \|` (첫 열 이름이 다르면 표에 맞춤) |
| 30 | 272 · 307 뒤 | `KAKAO_EXPORT_DIR=/Users/<사용자>/Downloads` · `WIKI_LAN_PORT` 없음 | `kakao_ingest.py` 가 `~` 를 풂 · `wiki_lan_server.js` 가 `WIKI_LAN_PORT` 읽음 | 272: `KAKAO_EXPORT_DIR=~/Downloads                         # KakaoTalk_Chat_*.csv 가 떨어지는 폴더 (없으면 ~/Downloads)` · 307 뒤: `# WIKI_LAN_PORT=3100                               # (선택) 집 안 검색 서버 포트` |
| 31 | 360·377 뒤·355·403 | 절 제목 · `--ids` 없음 · wiki-ingest 「(증분)」 · 백업 「매 실행 끝에」 | | 360: `### 3. 꿀팁 인제스트 (카카오톡 · 텔레그램)` · 377 뒤: `/opt/homebrew/bin/python3 scripts/recategorize_tips.py --ids=<record_id>[,…]   # (v4.19) 지정 행만 규칙 값으로 다시 매김 (dry-run 기본, --apply 병용)` · 355 의 wiki-ingest 설명 칸: `wiki_ingest.py` (증분 + backfill + 재렌더, v4.16 `caffeinate -i` 로 감쌈) · 403: 「매 실행 끝에」 → 「매 실행(시트 미러 뒤 · Obsidian 동기화 앞)에」 |
| 32 | 470·472·473 장부 구조 | tips·wiki_extract·meta 설명 | 텔레그램 공용 · `stale` · meta 키 2개 | 470: tips 설명 앞부분을 `꿀팁 링크 1건 1행(카톡 · v4.18 텔레그램 공용).` 로 (뒤는 그대로) · 472: status 목록을 `ok·seed·failed · v4.6-b stale = 재요약 뒤 다시 추출 대기` 로 · 473: meta 설명 끝에 ` · (v4.18) \`tips_bot_offset\`·\`tips_bot_last_ok\`(텔레그램 봇 읽은 위치·마지막 정상 수신, tips 와 같은 트랜잭션)` |
| 33 | 71 머메이드 | `KakaoTalk_Chat_<실명>_*.csv` | 공개 README 에 개인 실명 | 실명 부분만 `<이름>` 으로: `KakaoTalk_Chat_<이름>_*.csv` (코드 `kakao_ingest.py` 는 그대로) |
| 34 | `.env` 재요약 기본값 주석 | `RESUMMARY_PER_RUN=5`·`RESUMMARY_DAILY_MAX=20` | 운영값 실행당 20 · 하루 40 (CLAUDE.md 11-01) | 그 블록의 설명 주석 줄 끝에 ` (코드 기본값 — 운영은 실행당 20·하루 40)` 덧붙임. 값 줄은 그대로 |
| 35 | 설치 및 실행 끝(「6. Wiki 검색」 절 뒤, 「📓 Obsidian」 앞) | 회귀 테스트 실행법 없음 | | 새 절 `### 7. 회귀 테스트` + bash 블록 한 줄: `scripts/run_all_tests.sh             # 16종 (all \| js \| py) — 마지막 줄 RESULT: 16/16 통과, 실패하면 exit 1. 네트워크 0회, 실제 장부·Vault 무관` |

표 속 `\|` 는 마크다운 표 칸 구분이 아니라 실제 `|` 문자다(README 에 쓸 때는 `|`).

### 변경 이력 1줄 (CLAUDE.md·AGENTS.md 「## 변경 이력」 바로 아래 맨 위, 같은 문구)

```
- **2026-11-04 (문서 현행화, 버전 유지)** — README 전수 대조(investigator) 35곳: v4.18 텔레그램 꿀팁 입구(제목·개요·기능·흐름도·사이클 표 3b·구조·장부 meta) · v4.6 실제 영상 요약·v4.6-b 재요약(흐름도·사이클 2a) · v4.14 분류 모델 · v4.5 `wiki_extract`·backfill · 회귀 16종 · push 규칙 · 마스터 모드 통계 갱신 서술 정정 · `.env` `KAKAO_EXPORT_DIR`·`WIKI_LAN_PORT` · 재요약 운영값 주석 · 머메이드 실명 일반화 · 「7. 회귀 테스트」 절. 버전 이력 절·코드·장부 무변경. 지시서 `docs/tasks/2026-11-04-readme-sync.md`.
```

### 커밋

```bash
git add README.md CLAUDE.md AGENTS.md docs/tasks/2026-11-04-readme-sync.md
git commit -m "[CC-1104-D] README 현행화 — v4.6~v4.19 반영 (텔레그램 입구·실제 영상 요약·재요약·분류 모델·회귀 16종·push 규칙, 문서만·버전 유지)"
```

## 기준표

| # | 기준 |
|---|---|
| 1 | 0-1~0-4 기대값 일치 |
| 2 | 표 1~35 가 모두 반영됨(항목별 반영 행 번호 보고). 「기존 노드 이름이 다르면 맞춤」 등 조정한 곳은 이유와 함께 보고 |
| 3 | 머메이드 블록 문법이 깨지지 않음 — 새 노드 id 가 기존과 겹치지 않고 모든 화살표 대상 노드가 정의됨(`grep` 으로 id 목록 대조 보고) |
| 4 | README 「🔄 버전 관리」 절(머리 `## 🔄 버전 관리` 부터 끝까지) diff 0 · 머리 버전 블록 9~27행 diff 0 |
| 5 | `grep -c "회귀 테스트 15종" README.md` = 0 · `grep -c "telegram_tips_ingest" README.md` ≥ 5 · `grep -n "(v4.2)" README.md` 가 아키텍처 제목에 없음 |
| 6 | 공개 레포 규칙 — 추가된 줄에 `/Users/`·맥 이름·집 대역·`.env` 값 0 · README 에 실명 0 (`git diff` 추가 줄 기준) |
| 7 | CLAUDE.md·AGENTS.md 이력 줄 동일 · 두 파일의 다른 곳 diff 0 |
| 8 | 커밋 1건, 변경 파일 4개(README·CLAUDE·AGENTS·이 지시서) · 코드·`data/` 미포함 · push 안 함 |
| 9 | `scripts/run_all_tests.sh` → `RESULT: 16/16 통과` (게이트와 같은 확인) |

## 하지 말 것

- README 절 순서·제목 체계 개편, 버전 이력 절 수정, 머리 9~27행 수정
- 코드·설정·장부·Vault 수정, `README.html` 생성
- 표에 없는 「낡아 보이는 곳」 임의 수정 — 찾으면 보고만
- `git push`

## 롤백

`git revert <커밋>` (문서만).

## 범위 밖 (대표님 판단)

- README 를 전역 README 표준 구성(⚡ Vibe Coding with AI → … → `#### [vX.Y.Z] - YYYY-MM-DD`)으로 개편 — 별도 지시서.
- 「실제 영상 요약·품질 필터」 전용 절 신설 — 지금은 기능 줄·흐름도·사이클 표로 충분하다고 봄.
