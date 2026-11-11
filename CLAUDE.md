# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

- **대표님과 직접 대화하는 메인 세션은 PM(pm-wiki) 이다 — 세션을 시작하면 `.claude/pm/PM_ROLE.md` 를 읽고 따른다** (2026-11-04 대표님 결정 · Claude Desktop(Code 탭)에서 이 저장소로 연 세션 · `./pm-wiki.sh` 로 띄워도 같다). 워커 서브에이전트(`implementer` · `verifier` · `investigator` · `scribe`)는 이 줄을 따르지 않는다.

**현재 버전: v4.21.4** (2026-11-11) · 레포 경로: `<REPO_ROOT>` = `~/Dev/AI_Wiki_Pipeline` · GitHub `iRG-AI/AI_Wiki_Pipeline`

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

→ 명령 전체(서버 · 스케줄러 · 동기화 · 백업 · 꿀팁 수집 · 회귀 20종 · PM 세션 · launchd 제어 · OAuth 재발급과 **계정 일치 검증** · 상태 스냅샷 · Wiki 검색)는 `docs/commands.md` — **명령을 실행하기 전에 읽는다.** 진단 1순위는 그 파일의 「상태 스냅샷」, OAuth 재발급 뒤에는 「OAuth 계정 일치 검증」(1유닛)이 필수다.

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

→ `.claude/rules/architecture.md` (파일별 역할 + Wiki 검색 · 카카오톡/텔레그램 꿀팁 · 시트 미러 · 장부 백업 · 실패 알림 · Wiki 합성 · 영상 요약 · 재요약 · 매일 검토 · 고아 격리 · 대기 큐 · 외부 서비스 · v4.0 장부). 코드 파일을 Read 하면 자동으로 읽힌다.

### 중요한 제약사항

전문은 `.claude/rules/constraints.md` — **구현·검수 전에 반드시 읽는다**(코드 파일 Read 때 자동으로도 읽힌다). 핵심만:
- 장부 `data/library.db` 가 없거나 0건이면 **던진다(fail-closed)** — 빈 장부를 만들거나 빈 결과로 바꾸지 말 것. 「저장 15 · Skip 0」은 성공이 아니라 캐시 이상 신호.
- 한글은 장부 topics·tags · 재생목록명 · Obsidian 파일명 모두 `.normalize('NFC')`.
- YouTube 할당량 하루 10,000 유닛, 일 경계 태평양시(KST 16:00). 실패 요청도 소비 → 재생목록 추가 하루 약 190건 상한.
- 대기 큐 안전장치(중복 미적재 · 연속 실패 10회 중단 · `invalid_grant` 즉시 중단 · dead-letter)는 건드리지 말 것.
- 401/403 은 즉시 중단(재시도 대상 아님). `403 playlistItemsNotAccessible` 은 재생목록 삭제가 아니라 **계정 불일치부터 의심**(토큰은 「타이쿤안」 채널로).
- Gemini 429 는 `quotaId` 로 두 종류를 구분, 5xx 는 재시도. Vault 실제 경로는 중첩(`AI LLM Wiki/AI LLM Wiki`).

### launchd 데몬

→ `.claude/rules/launchd.md` — launchd 조작(load · unload · kickstart · plist 수정) 전에 읽는다.

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
