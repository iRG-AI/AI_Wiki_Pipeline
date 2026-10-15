# v4.14 — 토픽 분류 모델 2.5 Flash → 3.5 Flash-Lite

> 지시 번호는 발행할 때 채팅으로 준다. 보고는 한국어로.
> 선행: `94e7275`(원격 main 과 같음). 스케줄러는 내리지 않는다(5-0 의 시간 창만 피한다).
> 스키마·`.env` 변경 없음. **데몬 재기동 없음**(`scheduler.js`·`lib/*.js` 는 실행마다 새로 읽힌다). **장부·Vault 쓰기 없음**. push 는 이 지시서 범위 밖(다음 지시).

## 1. 배경

신규 영상 1편에 Gemini 2.5 Flash 를 두 번 쓴다 — 영상 요약 1회(`lib/video_summary.js`) + 토픽 분류 1회(`lib/classifier.js`).

- 2.5 Flash 무료 하루 요청 한도는 프로젝트(키)당 20. AI Studio 28일 최대가 한 프로젝트 **36/20** — 키 4개를 돌려 버티는 상태다.
- 신규가 몰린 날(10-10, 29편)이면 2.5 Flash 요청만 약 60회(재시도 제외).
- 분류는 요약 글을 읽고 33개 토픽 중에서 고르는 가벼운 일이다. 재요약이 이미 쓰는 3.5 Flash-Lite(하루 500 — 10-15 확인)로 옮기면 2.5 Flash 를 영상 요약에만 쓴다.

### 비교 시험 (Cowork, 10-15 19:08~19:18, 맥 `~/v414chk`, 장부 읽기 전용)

최근 신규 영상 20편(`summary_src='video'` · 재요약 아님 — 앞으로 분류가 받을 입력과 같은 종류)을 **이 패치의 `lib/classifier.js`** 로, 같은 프롬프트·같은 토픽 33개로 두 모델에 분류했다(키 4개 순환, 호출 간격 4.5초).

| 항목 | 2.5 Flash (다시 돌림) | 3.5 Flash-Lite |
|---|---|---|
| 장부에 저장된 토픽과 완전히 같음 | 16/20 | 0/20 |
| 겹침(Jaccard 평균) | 0.95 | 0.44 |
| 영상당 토픽 | 4.5 (장부 4.4) | **2.5** |
| 오류 · 신뢰도 0.6 미만 · 목록 밖 토픽 | 0 · 0 · 0 | 0 · 0 · 0 |
| 응답 시간 평균 | 1.6초 | 1.9초 |

- 3.5 Flash-Lite 에서 빠진 토픽: 생산성 향상 13 · 자동화 7 · 에이전트 6 · 트렌드 4 · 프롬프트 4 · Codex 4 · 보안 3 · 수익화 2 · 슬라이드·Antigravity·전환 각 1. 대부분 프롬프트가 「추상 토픽 과추천 금지」로 적은 토픽이거나 곁다리 도구 언급(「Gemini 4 아르곤 출시」 영상들의 Codex·보안)이다.
- 더 맞게 붙은 것: 바이브코딩 4(「코딩 못해도 AI 게임 만드는 법」·「앱을 통째로 복사하는 REA」 등) · 트렌드 1(「왕초보가 알아야 할 AI 주요 소식」 — 2.5 Flash 는 안 붙임).
- 아쉬운 누락: 수익화 1(「얼굴 없이 유튜브로 돈과 브랜드」) · 전환 1(「제조업 대표가 ERP 직접 개발」).

## 2. 설계 결정 (대표님 결정 10-15 19:22 — A안, 바꾸지 말 것)

| 항목 | 결정 |
|---|---|
| 모델 | `lib/classifier.js` 기본 `gemini-3.5-flash-lite`. `.env CLASSIFY_MODEL` 이 있으면 그 값(`resolveModel` — 앞뒤 공백 무시, 빈 값이면 기본). `opts.model` 로 호출마다 바꿀 수 있다(시험용 — scheduler 는 넘기지 않는다) |
| thinking | `thinkingConfigFor(model)` — 2.x 는 `{ thinkingBudget: 0 }`, 그 밖은 `{ thinkingLevel: 'minimal' }`(3.x 는 `thinkingBudget` 을 400 으로 거절). `lib/video_summary.js:thinkingConfigFor` 와 같은 규칙 |
| 결과 | `classifyTopics` 결과에 `model`. `scheduler.js` 분류 로그가 `🏷  분류: [...] (conf=0.90 · gemini-3.5-flash-lite)` |
| 잠복 결함 | 응답을 `chunks += c` 로 이어 붙여, 한글이 청크 경계에서 잘리면 토픽 문자열이 깨져 allowedSet 에서 떨어졌다 → `Buffer.concat`. 새 테스트로 재현(옛 코드 토픽 `[]`) |
| 무변경 | 프롬프트 · allowedSet 필터 · 5개 상한 · 신뢰도 0.6 재생목록 기준 · scheduler 분류 재시도(429·5xx 키 로테이션, 401/403 즉시 중단, `maxRetries: 0`) · 장부·스키마 · 과거 영상 토픽 · 레거시 경로(분류 안 함) |
| 되돌리기 | 코드가 아니라 `.env` 에 `CLASSIFY_MODEL=gemini-2.5-flash` 한 줄(재기동 불필요 — 다음 정시 실행부터) |
| 범위 밖 | 프롬프트 손질(수익화·전환 누락 보완) · 과거 영상 토픽 재분류 · 분류를 영상 요약 호출에 합치기 |

## 3. 파일

| 파일 | 내용 |
|---|---|
| `docs/tasks/patches/2026-10-15-v414-classify-flash-lite.patch` | 기준 = `94e7275`, 6개 파일, +211 −23 (새 파일 1 포함) |
| `docs/tasks/2026-10-15-v414-classify-flash-lite.md` | 이 지시서 |

```
sha256  4526b1dea3989fbbe86eeb2c48fa32ef1164b02df431a8bdc361090cdb2be1df  docs/tasks/patches/2026-10-15-v414-classify-flash-lite.patch
```

| 패치 안 파일 | 변경 |
|---|---|
| `lib/classifier.js` | 머리 설명 1줄 · `DEFAULT_MODEL`·`resolveModel`·`thinkingConfigFor` · `geminiCall(…, model)` · `Buffer.concat` · `opts.model` · 결과 `model` · export |
| `scheduler.js` | 분류 로그 1줄에 모델 |
| `scripts/test_classifier.js` | **신규** 8건(가짜 https — 네트워크 0) |
| `CLAUDE.md` · `AGENTS.md` · `README.md` | 머리 버전 v4.14 · 요약 1줄 · 테스트 15종 · 파이프라인 줄 · 파일 표 · 외부 서비스 · 분류 경로 절 · 이력 / README 요약 1줄 · 다이어그램 · 구조 주석 · `.env` 예시 · 요약 행 · 상세 1절. AGENTS.md = 머리글 5줄 + CLAUDE.md 4행부터 |

### Cowork 사전 검증 (2026-10-15 19:25~19:32, 레포 무변경 — 패치 파일만 놓음)

- 클라우드(Node 22): `test_classifier.js` 가 옛 코드에서 2/8(모델·thinking·한글 청크 경계 FAIL), 새 코드에서 8/8.
- 맥 네이티브(홈 임시 폴더 `git archive 94e7275` + 이 패치, 끝나고 삭제): `AGENTS_OK` · `SYNTAX_OK` · 실제 `.env` 로 `MODEL` = `gemini-3.5-flash-lite` · **회귀 15종 전부 통과** — classifier 8 · scheduler_guards 33 · video_summary 32 · resummarize 11 · wiki_search 34 · recategorize_tips 52 · title_fetch 43 · kakao_ingest 37 · verify_library 16 · retitle_tips 49 · wiki_ingest 64 · sync_obsidian 32 · sheet_mirror 45 · build_wiki_index 15 · backup_library 50.
- 실호출: 1절 비교 시험 40회(이 패치 코드, 3.5 Flash-Lite 20 · 2.5 Flash 20) 모두 200 — 3.5 Flash-Lite 의 `thinkingLevel: 'minimal'` 수락 확인.

## 4. 기대 효과

| | v4.13 | v4.14 |
|---|---|---|
| 신규 1편의 2.5 Flash 요청 | 2 (요약 + 분류) | 1 (요약) |
| 신규 1편의 3.5 Flash-Lite 요청 | 0 | 1 (분류) — 하루 재요약 40 + 분류 약 15~30, 한도 500 |
| 영상당 토픽 (비교 20편) | 약 4.4 | 약 2.5 |
| 토픽 재생목록 추가 (`playlistItems.insert` 50유닛) | 영상당 약 4.4 | 약 2.5 (약 45% 감소) |

토픽이 줄어 「AI 생산성 향상」·「AI 자동화」·「AI 에이전트」 재생목록·허브에 새로 들어오는 영상이 크게 준다(의도 — 대표님 결정). 과거 영상 토픽은 그대로라 옛 영상(넓은 태그)과 새 영상(좁은 태그)이 섞인다.

## 5. 실행 — 적용·테스트·커밋

### 5-0. 시간

스케줄러가 00·06·12·18시, wiki-ingest 가 17:30 에 돈다. **매시 50분 ~ 다음 시 20분, 17:25~17:45 에는 5-2 이후를 시작하지 않는다.**
판정은 시각의 **분**으로 한다 — `date '+%H:%M'` 의 분이 50~59 또는 00~20 이면(어느 시든) 창 **안**이다. 예: 19:15 는 창 안, 19:25 는 창 밖.
(이 지시서는 장부를 쓰지 않지만, 스케줄러가 패치 도중의 `lib/classifier.js`·`scheduler.js` 를 읽지 않게 창을 피한다.)

### 5-1. 시작 상태 (읽기만)

```bash
cd <REPO_ROOT>
date '+%H:%M'                                            # 창 밖이어야 한다
git --no-optional-locks rev-parse --short HEAD          # 94e7275
git --no-optional-locks status --porcelain
#   기대: 아래 두 줄만
#   ?? docs/tasks/2026-10-15-v414-classify-flash-lite.md
#   ?? docs/tasks/patches/2026-10-15-v414-classify-flash-lite.patch
shasum -a 256 docs/tasks/patches/2026-10-15-v414-classify-flash-lite.patch   # 3절 값과 같아야 한다
grep -o '"outcome": "[a-z]*"' .run_state.json            # "ok" (running 이면 멈춤 — 스케줄러 실행 중)
pgrep -fl scheduler.js || echo "scheduler 미실행"         # 미실행이어야 한다
grep -c '^CLASSIFY_MODEL=' .env                          # 0 (값은 출력하지 않는다)
```

어긋나면 **멈추고 보고**한다.

### 5-2. 패치 적용

```bash
git apply --check docs/tasks/patches/2026-10-15-v414-classify-flash-lite.patch && git apply docs/tasks/patches/2026-10-15-v414-classify-flash-lite.patch
git --no-optional-locks status --porcelain
#   기대: M AGENTS.md · M CLAUDE.md · M README.md · M lib/classifier.js · M scheduler.js
#         ?? docs/tasks/2026-10-15-v414-classify-flash-lite.md · ?? docs/tasks/patches/…patch · ?? scripts/test_classifier.js
git --no-optional-locks diff --stat | tail -1            # 5 files changed, 79 insertions(+), 23 deletions(-)   (새 테스트 파일은 untracked 라 빠진다)
wc -l < scripts/test_classifier.js                       # 132
{ head -5 AGENTS.md; tail -n +4 CLAUDE.md; } | cmp - AGENTS.md && echo AGENTS_OK
/opt/homebrew/bin/node --check lib/classifier.js && /opt/homebrew/bin/node --check scheduler.js && echo SYNTAX_OK
```

### 5-3. 회귀 테스트 15종 (네트워크 0회, 실제 장부·Vault·.env 무관)

```bash
/opt/homebrew/bin/node scripts/test_classifier.js            # 8/8 PASS  (신규)
/opt/homebrew/bin/node scripts/test_scheduler_guards.js      # 33/33
/opt/homebrew/bin/node scripts/test_video_summary.js         # 32/32
/opt/homebrew/bin/node scripts/test_resummarize.js           # 11/11
/opt/homebrew/bin/node scripts/test_wiki_search.js           # 34/34
/opt/homebrew/bin/python3 scripts/test_recategorize_tips.py  # 52/52
/opt/homebrew/bin/python3 scripts/test_title_fetch.py        # 43/43
/opt/homebrew/bin/python3 scripts/test_kakao_ingest.py       # 37/37
/opt/homebrew/bin/python3 scripts/test_verify_library.py     # 16/16
/opt/homebrew/bin/python3 scripts/test_retitle_tips.py       # 49/49
/opt/homebrew/bin/python3 scripts/test_wiki_ingest.py        # 64/64
/opt/homebrew/bin/python3 scripts/test_sync_obsidian.py      # 32/32
/opt/homebrew/bin/python3 scripts/test_sheet_mirror.py       # 45/45
/opt/homebrew/bin/python3 scripts/test_build_wiki_index.py   # 15/15
/opt/homebrew/bin/python3 scripts/test_backup_library.py     # 50/50
```

하나라도 FAIL 이면 멈추고 보고(8절 롤백).

### 5-4. 실제 설정으로 모델 확인 (읽기만 — 네트워크 0)

```bash
/opt/homebrew/bin/node -e "const c=require('./lib/classifier'); console.log(c.MODEL, JSON.stringify(c.thinkingConfigFor(c.MODEL)))"
#   기대: gemini-3.5-flash-lite {"thinkingLevel":"minimal"}
```

## 6. 커밋 (push 하지 않음)

```bash
git add AGENTS.md CLAUDE.md README.md lib/classifier.js scheduler.js scripts/test_classifier.js \
        docs/tasks/2026-10-15-v414-classify-flash-lite.md docs/tasks/patches/2026-10-15-v414-classify-flash-lite.patch
git commit -m "v4.14 토픽 분류 모델 2.5 Flash → 3.5 Flash-Lite — 2.5 Flash 하루 요청을 영상 요약에 남긴다 (CLASSIFY_MODEL 로 되돌림)"
git --no-optional-locks status --porcelain       # 커밋 뒤 기대: 빈 출력
git --no-optional-locks log --oneline -2
git --no-optional-locks show --stat HEAD | tail -9    # 8개 파일
```

## 7. 데몬

재기동 없음. `lib/classifier.js`·`scheduler.js` 는 정시 실행마다 새로 읽힌다 — 커밋 뒤 첫 정시 실행부터 적용. 상주 데몬(`server`·`wiki-lan`)은 분류기를 쓰지 않는다(`server.js` 는 스케줄러를 자식 프로세스로 띄울 뿐).

## 8. 롤백

- 커밋 전: `git checkout -- AGENTS.md CLAUDE.md README.md lib/classifier.js scheduler.js && rm scripts/test_classifier.js` (지시서·패치는 untracked 로 남김).
- 커밋 뒤(push 전): `git reset --hard 94e7275` 는 지시서·패치까지 지우므로 쓰지 않는다 → `git revert --no-edit HEAD`.
- 분류만 예전 모델로: 코드 대신 `.env` 에 `CLASSIFY_MODEL=gemini-2.5-flash`(다음 정시 실행부터).
- 장부에 이미 저장된 토픽은 어느 쪽으로 되돌려도 그대로다(재분류 없음).

## 9. 보고

5-1 ~ 6 의 각 명령 출력(기대값과 다르면 그 줄을 먼저), 커밋 해시, `show --stat` 마지막 9줄.

## 10. 범위 밖

- push(다음 지시).
- 프롬프트 손질 · 과거 영상 재분류 · 분류를 영상 요약 호출에 합치기.
- 첫 신규 영상 실행 판정(Cowork) — `🏷  분류: [...] (conf=… · gemini-3.5-flash-lite)` · 분류 429·5xx 재시도 · 영상당 토픽 수 · `droppedTopics` · 재요약과 같은 실행에서 3.5 Flash-Lite 429 유무.
