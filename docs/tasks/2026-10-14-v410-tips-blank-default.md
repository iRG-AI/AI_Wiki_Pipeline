# v4.10 — 꿀팁 빈 기본값 재분류 · 제목 3차

> 지시 번호는 발행할 때 채팅으로 준다. 보고는 한국어로.
> 선행: `9bbebb5`(v4.9, 원격 main 과 같음). 스케줄러는 내리지 않는다(4-0 의 시간 창만 피한다).
> 스키마·`.env` 변경 없음. **데몬 재기동 없음**. 장부·Vault 쓰기는 **6절 두 번**(제목 25행 → 재분류 28행 — 대표님 승인 단계).

## 1. 배경

v4.9(10-13) 뒤 꿀팁 카테고리 「기타」가 66건이다. 두 가지가 남았다.

1. **노션 기본값이 남은 행.** 「기타」 중 사람이 고른 값 43건 — 그중 **태그가 빈 19건**(08-14 14 · 09-03 1 · 09-06 4)은 「클로드 코드 토큰 3배로 오래 쓰는 무료 도구 3개」·「클로드 시크릿코드 — 프롬프트 단축 명령어 100개」처럼 내용이 뻔한데 노션 이관 때 기본값(기타·태그 없음)이 그대로 남았다. v4.9 `recategorize_tips.py` 는 「v4.8 규칙 값과 같은 행」만 고치므로 이 행들을 사람이 고른 값으로 보고 건너뛴다. **대표님 결정(10-13 22:50): 「기타」 + 태그 없음은 규칙 재분류 허용.**
2. **URL 추정 제목 26건.** 09-12~10-10 적재분의 제목이 `agent reach`·`mobilebasic`·`view` 같은 URL 조각이다(v4.8 자동 조회는 신규 행만 대상). Cowork 가 `lib/title_fetch.py` 로 조회했다(10-13 22:40) — 25 성공 · 1 `private`(비공개 노션 `3bca3cbc-…-e78edaad2a09`, 제외). **대표님 결정: 제목 3차 진행.** 제목이 바뀌면 분류도 새 제목으로 다시 매긴다(URL 추정 제목은 판정 글자에서 빠져 있었다).

## 2. 설계 결정 (바꾸지 말 것)

| 항목 | 결정 |
|---|---|
| 빈 기본값 | `decide()` — 지금 (카테고리, 태그)가 `('기타', [])` 이면 v4.8 규칙 값이 아니어도 `rule_made` 로 보고 `kakao_parse.classify` 로 다시 매긴다(`BLANK_DEFAULT`). 태그가 하나라도 있거나 카테고리가 「기타」가 아니면 지금처럼 사람이 고른 값 |
| 표시 | `decide()` 반환 `blank_default`(v4.8 규칙 값이 아니고 빈 기본값이라 다시 매긴 행). `RESULT_JSON.blank_default` = 분류가 실제로 바뀐 그런 행 수. 로그 행 끝 「(빈 기본값)」 |
| 무변경 | 분류 규칙(`lib/kakao_parse.py`) · 태그 이름·카테고리 값 · 출처 정리 · 노트 편집 규칙 · 백업·트랜잭션 · `retitle_tips.py` |
| 제목 3차 | CSV 25행. 원문 제목 그대로, 다만 사이트 이름 꼬리(「— REBORN LABS」·「— 낭만빌더 김스듴」·「— 누끼토끼」·「- Tips_2026 - Biggie AI」)와 `.pdf`·「(클로드코드) 49_」 접두는 뺐다. 목록 페이지 1건은 「(가이드 모음)」을 덧붙였다. 금지 문자(`|`·`[[`·`]]`) 없음 |
| 순서 | **제목 먼저 → 재분류.** 재분류가 새 제목을 판정 글자로 쓴다 |
| 재실행 | 고친 행은 지금 규칙 값과 같아 다시 대상이 되지 않는다 — 두 번째 실행 0행 |

## 3. 파일

| 파일 | 내용 |
|---|---|
| `docs/tasks/patches/2026-10-14-v410-tips-blank-default.patch` | 기준 = `9bbebb5`, 5개 파일, +71 −20 |
| `docs/tasks/2026-10-14-retitle-tips-3.csv` | 25행 + 머리글(`record_id,old_title,new_title`) |
| `docs/tasks/2026-10-14-v410-tips-blank-default.md` | 이 지시서 |

```
sha256  4d790f528e48948eb7a588d4810ba52c030ab9a707912283dc3fec854f5e96ec  docs/tasks/patches/2026-10-14-v410-tips-blank-default.patch
sha256  8fe04ea5db0542cdb9d0624cb50ad774512ce270d86546dd92c9659d22b0eeba  docs/tasks/2026-10-14-retitle-tips-3.csv
```

| 패치 안 파일 | 변경 |
|---|---|
| `scripts/recategorize_tips.py` | 머리 설명 2줄 · `BLANK_DEFAULT` · `decide()` 빈 기본값 · 계획 항목 `blank_default` · `summarize()` `blank_default` · 로그 「(빈 기본값)」·「빈 기본값 다시 매김 N건」 |
| `scripts/test_recategorize_tips.py` | +7건(빈 기본값 → 개발툴·프롬프트 · 규칙이 기타면 그대로 · 손 태그 보존 · 기타 아닌 카테고리 보존 · v4.8 규칙 값과 구분 · summarize) → 52건 |
| `CLAUDE.md` · `AGENTS.md` · `README.md` | 머리 버전 v4.10 · 요약 1줄 · 명령·파일 표·카톡 절 문구 · 이력 / README 요약 행 · 상세 1절. AGENTS.md = 머리글 5줄 + CLAUDE.md 4행부터 |

### Cowork 사전 검증 (2026-10-13 22:50~, 맥 네이티브 · 레포 무변경)

- 홈 임시 폴더에 `git archive 9bbebb5` + 코드 패치 → 장부 사본(`.backup`)·Vault 전체 사본(30MB)으로 실행. 회귀 14종 전부 통과(`test_recategorize_tips.py` 52/52).
- 재분류 dry-run(제목 전): 16행 · `blank_default` 16 · `manual_kept` 75 · 기타→프롬프트 6 · 기타→개발툴 6 · 기타→모델/LLM 4.
- 제목 dry-run: rows 25 · notes 25 · renamed 25 · memo_cleared 0 · link_files 12 · links 59. apply(`--no-rebuild`) 같은 숫자.
- 재분류 dry-run(제목 뒤): **28행**(빈 기본값 16 · 제목 따라 12 — 카테고리 9 · 태그만 3) · 노트 28 · 건너뜀 0 · 출처 불일치 0 · `manual_kept` 75. apply(`--no-rebuild`) 같은 숫자 · 두 번째 dry-run 0행 · `integrity_check` ok.
- 반영 뒤 카테고리: 개발툴 51 · **기타 42** · 모델/LLM 25 · 프롬프트 14 · 뉴스/트렌드 10 · 지식관리 3 · 사업/마케팅 3 (전 66 → 42).

## 4. 적용 목록

### 4-A. 제목 3차 (25건)

| 저장일 | 옛 제목 | 새 제목 |
|---|---|---|
| 09-12 | agent reach | 클로드가 유튜브·레딧·깃허브를 무료로 긁어오게 만드는 도구 |
| 09-12 | claude youtube skill | 유튜브 튜토리얼을 클로드가 실행하는 스킬로 바꾸는 세 가지 세팅 |
| 09-13 | news 20260913 astra prompts sharing safety | OpenAI, GPT-6 프롬프트 가이드 공개…구글 공유 설정·클로드 악용 보고서 |
| 09-13 | claude skills top5 0815 | 클로드 코드를 쓰기 전에 깔아야 하는 플러그인 5개 |
| 09-18 | stitch | Stitch → 클로드 코드 · 짐작 대신 디자인 시스템에서 짓기 |
| 09-21 | open generative ai | 유료 영상 AI 대신 쓰는 무료 스튜디오 입문 가이드 |
| 09-21 | agency | 클로드 코드 AI 직원 68명 — 한 줄로 설치 |
| 09-21 | agency agents 279 ai roles install guide | AI에 전문가 역할 279개 붙이기: Agency Agents 설치 가이드 |
| 09-21 | claude designer kill | 클로드로 전문가가 만든 것 같은 웹사이트 만드는 법 |
| 09-22 | guides | 게으른 빌더 · AI한테 일을 시킵니다 (가이드 모음) |
| 09-23 | d367nxm3wr133mj98pv1 | 클로드 다크 프롬프트 10 |
| 09-23 | claude and n8n | 클로드로 첫 n8n 에이전트 만드는 6단계 |
| 09-26 | nvidia free ai models 100 | 엔비디아가 열어둔 AI 모델 100개, 무료로 어디까지 쓸 수 있나 |
| 09-26 | mobilebasic | Watercolour Travel Posters ColdPress Guide |
| 09-26 | ai delegation loop playbook | AI 위임 루프: 에이전트 대신 매뉴얼으로 일 넘기기 |
| 09-27 | view | 클로드코드 플러그인 설치 방법 |
| 09-30 | claude opus motion design prompts | 클로드 오퍼스 5.5, 프롬프트 하나로 15초 모션 영상 뽑는 법 |
| 09-30 | ecc claude code agent team | ECC 하나 설치해서 클로드에 엔지니어 전부를 맡기는 법 |
| 10-02 | business jobs to agent files | 회사 전체를 파일과 폴더로 옮기는 4단계, 업무 137개 지도 |
| 10-03 | view | 클로드 코드로 AI 직원(담당) 두는 법 |
| 10-05 | mobilebasic | 주식·재테크·코인 GitHub 스킬 100선 — 발동문과 한국어 프롬프트 |
| 10-05 | chatgpt metricool social manager | 2주 만에 팔로워 7천 명, ChatGPT로 SNS 관리하는 법 |
| 10-07 | phil ai trader paper 1000 | 클로드 트레이더 Phil, 가상 1,000달러로 진화시키는 법 |
| 10-09 | vibe coding design sites | 바이브 코딩 디자인 사이트 5곳 |
| 10-10 | codex guide | 클로드 안에서 GPT 쓰는 법 |

### 4-B. 빈 기본값 재분류 (19건 중 16건 이동, 3건 「기타」 그대로)

| 적재 | 제목 | 새 분류 |
|---|---|---|
| 08-14 | 클로드로 내 인스타그램 분석 | 모델/LLM |
| 08-14 | 클로드 코드 토큰 3배로 오래 쓰는 무료 도구 3개 | 개발툴 |
| 08-14 | 클로드 시크릿코드 — 프롬프트 단축 명령어 100개 | 프롬프트 |
| 08-14 | 클로드코드 스킬 실전 활용 플레이북 | 개발툴 |
| 08-14 | 콘텐츠 기획과 제작에 활용할 수 있는 클로드 프롬프트 모음 | 프롬프트 |
| 08-14 | 리얼리티 프롬프트 올인원 팩 (이미지 + 영상) | 프롬프트 |
| 08-14 | 만세력 캡처로 사주 분석하는 제미나이 프롬프트 | 프롬프트 |
| 08-14 | 이건 찐이다! 클로드 코드 완전정복, 3~10시간 무료 강의 모음 | 개발툴 |
| 08-14 | 클로드 in 크롬: 반복 업무 0시간 만들기 가이드 | 모델/LLM |
| 08-14 | 저화질 → 고화질 시네마틱 사진으로 만드는 프롬프트 | 프롬프트 |
| 08-14 | 믿지 마세요, 이제 우리는 의심해야 합니다 (Higgsfield 이미지 프롬프트) | 프롬프트 |
| 08-14 | 클로드코드 기초 총정리 시리즈 2편 | 개발툴 |
| 09-03 | 클로드 코드 끊김 없이 쓰는 무료 도구 3종 설치 가이드 | 개발툴 |
| 09-06 | 클로드 토큰절약가이드 | 모델/LLM |
| 09-06 | 딱 이 3가지만 보고 그대로 설정하세요 (클로드 튜토리얼·Firecrawl MCP·원격 제어) | 개발툴 |
| 09-06 | 클로드 한도 끝까지 쥐어짜기 | 모델/LLM |
| — | 그대로: 「바이브코딩하는데 이걸 이제 알아버림 (UI 애니메이션·컴포넌트 라이브러리)」·「애플 디자인 스킬 — 설치부터 검토까지」·「노션 자료 (제목 미확인)」(비공개) | 기타 |

## 5. 실행 — 적용·테스트·커밋

### 5-0. 시간

스케줄러가 00·06·12·18시, wiki-ingest 가 17:30 에 돈다. **매시 50분 ~ 다음 시 20분, 17:25~17:45 에는 5-2 이후를 시작하지 않는다.** (6절 장부 쓰기도 같은 창을 피한다.)
판정은 시각의 **분**으로 한다 — `date '+%H:%M'` 의 분이 50~59 또는 00~20 이면(어느 시든) 창 **안**이다. 예: 00:15 는 창 안, 00:25 는 창 밖.

### 5-1. 시작 상태 (읽기만)

```bash
cd <REPO_ROOT>
date '+%H:%M'                                            # 창 밖이어야 한다
git --no-optional-locks rev-parse --short HEAD          # 9bbebb5
git --no-optional-locks status --porcelain
#   기대: 아래 세 줄만
#   ?? docs/tasks/2026-10-14-retitle-tips-3.csv
#   ?? docs/tasks/2026-10-14-v410-tips-blank-default.md
#   ?? docs/tasks/patches/2026-10-14-v410-tips-blank-default.patch
shasum -a 256 docs/tasks/patches/2026-10-14-v410-tips-blank-default.patch docs/tasks/2026-10-14-retitle-tips-3.csv   # 3절 값과 같아야 한다
grep -o '"outcome": "[a-z]*"' .run_state.json            # "ok" (running 이면 멈춤 — 스케줄러 실행 중)
ls data/retitle_backup/ data/recategorize_backup/        # retitle 2개 · recategorize 1개 (지난 백업)
sqlite3 "file:data/library.db?mode=ro" "select count(*) from tips; select category, count(*) from tips group by 1 order by 2 desc;"
#   기대: 148 · 기타 66 · 개발툴 41 · 모델/LLM 19 · 뉴스/트렌드 10 · 프롬프트 6 · 지식관리 3 · 사업/마케팅 3
```

어긋나면 **멈추고 보고**한다(카톡 인제스트로 tips 가 늘었으면 그 숫자를 보고하고 멈춘다 — 6절 기대값이 달라진다).

### 5-2. 패치 적용

```bash
git apply --check docs/tasks/patches/2026-10-14-v410-tips-blank-default.patch && git apply docs/tasks/patches/2026-10-14-v410-tips-blank-default.patch
git --no-optional-locks status --porcelain
#   기대: M AGENTS.md · M CLAUDE.md · M README.md · M scripts/recategorize_tips.py · M scripts/test_recategorize_tips.py
#        ?? CSV · ?? 지시서 · ?? 패치
{ head -5 AGENTS.md; tail -n +4 CLAUDE.md; } | cmp - AGENTS.md && echo AGENTS_OK
/opt/homebrew/bin/python3 -m py_compile scripts/recategorize_tips.py scripts/test_recategorize_tips.py && echo SYNTAX_OK
```

### 5-3. 회귀 테스트 14종 (네트워크 0회, 실제 장부·Vault·.env 무관)

```bash
/opt/homebrew/bin/node scripts/test_scheduler_guards.js      # 33/33 PASS
/opt/homebrew/bin/node scripts/test_video_summary.js         # 23/23
/opt/homebrew/bin/node scripts/test_resummarize.js           # 9/9
/opt/homebrew/bin/node scripts/test_wiki_search.js           # 34/34
/opt/homebrew/bin/python3 scripts/test_recategorize_tips.py  # 52/52  (+7)
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

하나라도 FAIL 이면 멈추고 보고(9절 롤백).

### 5-4. 실데이터 dry-run 두 개 (읽기만 — 장부·Vault 무변경)

```bash
/opt/homebrew/bin/python3 scripts/recategorize_tips.py > /tmp/v410_recat0.log 2>&1; echo "exit=$?"; tail -1 /tmp/v410_recat0.log
#   기대 exit=0 · RESULT_JSON 의 rows 16 · category_changed 16 · tags_changed 16 · source_changed 0 · blank_default 16 ·
#   notes 16 · skipped_note 0 · source_mismatch 0 · manual_kept 75 · moves {"기타→프롬프트": 6, "기타→개발툴": 6, "기타→모델/LLM": 4}
/opt/homebrew/bin/python3 scripts/retitle_tips.py docs/tasks/2026-10-14-retitle-tips-3.csv > /tmp/v410_rt_dry.log 2>&1; echo "exit=$?"; tail -1 /tmp/v410_rt_dry.log
#   기대 exit=0 · ok true · dry_run true · rows 25 · notes 25 · renamed 25 · memo_cleared 0
#   link_files·links 는 사전 검증 때 12·59 — 정시 실행이 MOC·Wiki 를 다시 그렸으면 다를 수 있다. 숫자는 보고만(멈추지 않음)
ls data/retitle_backup/ data/recategorize_backup/        # 5-1 과 같음(새 폴더 없음)
```

`rows`·`notes`·`renamed`·`blank_default`·`manual_kept`·`moves` 가 하나라도 다르거나 `ok false` 면 **멈추고** 출력 전체를 보고한다(6절로 가지 않는다).

## 6. 커밋 (push 하지 않음)

```bash
git add AGENTS.md CLAUDE.md README.md scripts/recategorize_tips.py scripts/test_recategorize_tips.py \
        docs/tasks/2026-10-14-retitle-tips-3.csv docs/tasks/2026-10-14-v410-tips-blank-default.md \
        docs/tasks/patches/2026-10-14-v410-tips-blank-default.patch
git commit -m "v4.10 꿀팁 빈 기본값 재분류(기타·태그 없음) · 제목 3차 25건 (recategorize_tips.py · retitle_tips.py)"
git --no-optional-locks status --porcelain       # 커밋 뒤 기대: 빈 출력
git --no-optional-locks log --oneline -2
git --no-optional-locks show --stat HEAD | tail -10   # 8개 파일
```

## 7. 반영 — 장부·Vault 쓰기 (대표님 승인 단계)

5-4 가 기대값과 같고 6 커밋이 끝났을 때만. 시간 창(5-0)을 다시 확인한다. **7-1 → 7-2 순서, 같은 시간 창 밖 구간 안에서 이어서.**

### 7-1. 제목 25건

```bash
date '+%H:%M'                                                     # 창 밖이어야 한다
/opt/homebrew/bin/python3 scripts/retitle_tips.py docs/tasks/2026-10-14-retitle-tips-3.csv --apply > /tmp/v410_rt_apply.log 2>&1; echo "exit=$?"; tail -1 /tmp/v410_rt_apply.log
#   기대 exit=0 · ok true · rows 25 · notes 25 · renamed 25 · memo_cleared 0 · links·link_files 는 5-4 와 같음
#   rebuild 의 build_obsidian_wiki.py 0 · build_search_index.py 0 · backup 경로
```

exit 1 이면 그 자리에서 멈추고 `/tmp/v410_rt_apply.log` 전체를 보고한다(7-2 로 가지 않는다 — 롤백은 Cowork 판단 후, 9절).

### 7-2. 재분류

```bash
/opt/homebrew/bin/python3 scripts/recategorize_tips.py > /tmp/v410_recat1.log 2>&1; echo "exit=$?"; tail -1 /tmp/v410_recat1.log
#   기대(dry-run): rows 28 · category_changed 25 · tags_changed 28 · source_changed 0 · blank_default 16 · notes 28 ·
#   skipped_note 0 · source_mismatch 0 · manual_kept 75 ·
#   moves {"기타→개발툴": 9, "기타→프롬프트": 8, "기타→모델/LLM": 7, "모델/LLM→개발툴": 1}
```

숫자가 다르면 **멈추고** 보고한다(제목은 이미 바뀐 상태 — 그대로 두고 Cowork 판단). 같으면:

```bash
/opt/homebrew/bin/python3 scripts/recategorize_tips.py --apply > /tmp/v410_recat_apply.log 2>&1; echo "exit=$?"
grep -E '💾 백업|🗄|📂 노트|✅|❌' /tmp/v410_recat_apply.log
tail -1 /tmp/v410_recat_apply.log
#   기대 exit=0 · 「장부 tips 28행 갱신」 · 「노트 28개 수정」 · ✅ build_obsidian_wiki.py · ✅ build_search_index.py
#   마지막 줄 RESULT_JSON 의 ok true · rows 28 · rebuild 둘 다 0
```

### 7-3. 확인 (읽기만)

```bash
/opt/homebrew/bin/python3 scripts/recategorize_tips.py | tail -1        # rows 0 · blank_default 0 · manual_kept 75
sqlite3 "file:data/library.db?mode=ro" "select category, count(*) from tips group by 1 order by 2 desc;"
#   개발툴 51 · 기타 42 · 모델/LLM 25 · 프롬프트 14 · 뉴스/트렌드 10 · 지식관리 3 · 사업/마케팅 3
sqlite3 "file:data/library.db?mode=ro" "pragma integrity_check;"                                       # ok
sqlite3 "file:data/library.db?mode=ro" "select title, category, tags from tips where record_id='3bca3cbc-5c7a-80b9-aa34-e78edaad2a09';"
#   노션 자료 (제목 미확인)|기타|[]   (제외분 그대로)
/opt/homebrew/bin/python3 scripts/verify_library.py | grep RESULT_JSON                                  # ok true · vault_missing 0 · tips_missing 0
/opt/homebrew/bin/python3 sync_obsidian.py --dry-run | grep RESULT_JSON                                 # tips_added 0
ls ~/Documents/Obsidian/"AI LLM Wiki"/"AI LLM Wiki"/"AI 꿀팁" | grep -c '\.md$'                          # 148 (늘거나 줄지 않음)
B=$(ls -d data/retitle_backup/*/ | tail -1); echo "$B"
/opt/homebrew/bin/python3 - "$B" <<'EOF'
import json, os, sys, unicodedata as u
m = json.load(open(os.path.join(sys.argv[1], 'manifest.json'), encoding='utf-8'))
olds = [u.normalize('NFC', os.path.splitext(os.path.basename(r['from']))[0]) for r in m['renamed']]
print('RENAMED', len(olds))                                            # RENAMED 25
left = 0
for root, ds, fs in os.walk(m['vault']):
    ds[:] = [d for d in ds if not d.startswith('.') and d != '_trash']
    for f in fs:
        if f.endswith('.md'):
            t = u.normalize('NFC', open(os.path.join(root, f), encoding='utf-8', errors='ignore').read())
            left += sum(t.count('[[' + s + e) for s in olds for e in (']]', '|', '#'))
print('OLD_LINKS', left)                                               # OLD_LINKS 0
EOF
grep -c '클로드 코드 AI 직원 68명' wiki_index.json                     # ≥ 1 (검색 인덱스에 새 제목)
/opt/homebrew/bin/python3 sheet_mirror.py --dry-run | tail -1        # error "" · tips_sent ≥ 41 (제목 25 + 빈 기본값 16, 다음 정시 실행이 보낸다)
git --no-optional-locks status --porcelain                            # 빈 출력 (백업은 data/ 아래 — gitignore)
```

- 시트 「꿀팁」 탭은 다음 정시 실행의 시트 미러가 보낸다(`updated_at` 워터마크). 그 전 `sheet_mirror.py --check` 불일치는 정상.
- 자동 모드가 장부 쓰기를 막으면 그대로 멈추고 보고한다 — 대표님이 터미널에서 해당 `--apply` 줄을 직접 실행한다.

## 8. 데몬

- 재기동 없음. 앱 코드 무변경(스크립트만). 검색 서버(`server`·`wiki-lan`)는 인덱스 파일 mtime 이 바뀌면 다시 읽는다.

## 9. 롤백

- 커밋 전: `git apply -R docs/tasks/patches/2026-10-14-v410-tips-blank-default.patch`.
- 커밋 후·7절 전: `git revert HEAD`(push 전이면 `git reset --hard 9bbebb5` 도 가능 — CSV·지시서·패치는 다시 untracked 로 둔다).
- 7절 뒤 값 되돌리기(스케줄러 창 밖, 지금 장부를 먼저 따로 복사). `RB` = 7-2 `RESULT_JSON` 의 `backup`, `TB` = 7-1 `RESULT_JSON` 의 `backup`:

```bash
RB=<7-2 backup 경로>; TB=<7-1 backup 경로>
/opt/homebrew/bin/python3 - "$RB" "$TB" <<'EOF'
import json, os, shutil, sys
rb, tb = sys.argv[1], sys.argv[2]
r = json.load(open(os.path.join(rb, 'manifest.json'), encoding='utf-8'))
for rel in r['edited']:                       # 1) 재분류 전 노트로 (제목 바뀐 이름 그대로)
    shutil.copy2(os.path.join(rb, 'vault', rel), os.path.join(r['vault'], rel))
t = json.load(open(os.path.join(tb, 'manifest.json'), encoding='utf-8')); v = t['vault']
for x in t['renamed']:                        # 2) 제목 바꾼 파일 지우고 옛 노트·링크 파일 복원
    p = os.path.join(v, x['to'])
    if os.path.exists(p): os.remove(p)
for rel in t['edited']:
    shutil.copy2(os.path.join(tb, 'vault', rel), os.path.join(v, rel))
shutil.copy2(os.path.join(tb, 'library.db'), t['db'])   # 3) 장부 = 7-1 직전
print('restored', len(r['edited']), '+', len(t['edited']), 'files + db')
EOF
/opt/homebrew/bin/python3 build_obsidian_wiki.py && /opt/homebrew/bin/python3 build_search_index.py
/opt/homebrew/bin/python3 scripts/verify_library.py | grep RESULT_JSON
```

  시트가 이미 새 값을 받았다면 `sheet_mirror.py --full`. **복원 장부는 7-1 직전 것이라 그 사이 정시 실행분이 있으면 되돌리지 말고 Cowork 에 보고**한다.

## 10. 범위 밖

- `git push`.
- 비공개 노션 1건(`3bca3cbc-…-e78edaad2a09`) — 대표님이 원문을 아시면 다음 CSV 로.
- 「기타」 남은 42건 중 태그가 있는 사람 분류(`큐레이션`·`아카이브` 등) — 그대로.
- 카톡 메시지 글로 매긴 규칙 값을 재분류가 알아보게 하는 보완(지금은 URL + 제목만 본다 — 예: 09-27 「클로드코드 플러그인 설치 방법」 `MCP` 태그는 그대로 남는다).
- 태그 추가(`Codex`·`NotebookLM` 등) · 「뉴스/트렌드」·「사업/마케팅」 자동 판정.
- `data/retitle_backup/`·`data/recategorize_backup/` 정리(10-19 이후 Cowork 제안).

## 11. 보고 형식 (한국어)

```
[CC-…] 결과
- 5-1 시작 상태: 시각 / HEAD / porcelain / sha256 두 개 일치 여부 / outcome / 백업 폴더 목록 / tips 수 · 카테고리 분포
- 5-2 적용: status 요약 / AGENTS_OK / SYNTAX_OK
- 5-3 테스트: 14종 각 n/n
- 5-4 dry-run: 두 개 각 exit · 마지막 줄 원문 · 백업 폴더 목록
- 6 커밋: 해시, show --stat
- 7-1 제목: 시각 · exit · 마지막 줄 원문
- 7-2 재분류: dry-run 마지막 줄 · apply exit · grep 줄 원문 · 마지막 줄 원문
- 7-3 확인: 명령별 출력 원문
- 특이사항(멈춘 단계·기대와 다른 출력 원문)
```
