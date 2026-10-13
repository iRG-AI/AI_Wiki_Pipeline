# v4.9 — 꿀팁 분류 보정

> 지시 번호는 발행할 때 채팅으로 준다. 보고는 한국어로.
> 선행: `e48208b`(v4.8). 스케줄러는 내리지 않는다(4-0 의 시간 창만 피한다).
> 스키마·`.env` 변경 없음. **데몬 재기동 없음**. 장부 쓰기는 **6절 한 번**(꿀팁 87행 값 수정 — 대표님 승인 단계).

## 1. 배경

v4.8 사전 검증에서 꿀팁 분류에 세 가지 문제가 보였다.

1. **노션 주소 → 「지식관리」.** `lib/kakao_parse.py` 가 URL 전체 글자에서 태그를 찾아, 노션에 올린 자료(`*.notion.site`·`notion.so`·`app.notion.com`)는 주소의 `notion` 때문에 모두 태그 `Notion` → 카테고리 「지식관리」가 됐다. 장부 지식관리 17건 중 14건이 노션에 올린 클로드·GPT 자료다.
2. **한글 표기를 못 잡는다.** 규칙이 영문만 봐서 「클로드」가 `Claude` 태그에 안 걸린다(제목에 「클로드」가 있는데 `Claude` 태그가 없는 꿀팁 27건). v4.8 부터 원문 제목(대개 한글)이 들어오므로 앞으로 더 커진다.
3. **옛 행의 출처.** 노션 이관 시절(08-14 적재) 71행의 `tips.source` 가 `https://…` 다. 규칙은 호스트만(`CLAUDE.md`)이고, 「채널별 목차」가 출처로 묶어 같은 사이트가 둘로 갈린다.

## 2. 설계 결정 (바꾸지 말 것)

| 항목 | 결정 |
|---|---|
| 규칙 위치 | `lib/kakao_parse.classify(url, *texts) -> (category, tags)` 한 곳. `guess_meta` 와 재분류 스크립트가 같이 쓴다 |
| 노션 주소 | `is_notion_host`(= `*.notion.site`·`notion.so`·`app.notion.com`, `guess_meta` 의 노션 분기와 같은 조건)면 판정 글자에서 **호스트를 뺀다**. `notion.com`(노션 회사 사이트)은 그대로 `Notion` |
| 한글 별칭 | `ClaudeCode` ← (claude\|클로드)[-_ ]?(code\|코드) · `Claude` ← 클로드 · `Gemini` ← 제미나이·제미니 · `GPT` ← 오픈 AI·지피티 · `Notion` ← 노션 · `Obsidian` ← 옵시디언 · `Antigravity` ← 안티그래비티 · `Ollama` ← 올라마 · `HuggingFace` ← 허깅 페이스. 「커서」는 일반 명사라 넣지 않는다 |
| 무변경 | 태그 이름·순서·카테고리 값 목록·카테고리 보정 순서(프롬프트 → 개발툴 → 지식관리 → 모델/LLM). 제목 추정·메모·`title_src`·중복 판정 |
| 기존 꿀팁 대상 | 지금 (카테고리, 태그)가 **v4.8 규칙 값**과 같은 행만 — v4.8 규칙 값 = (URL + 제목) 또는 (URL 만)으로 매긴 결과(스크립트 안에 v4.8 규칙을 얼려 둔 사본). 아니면 사람이 고른 값(노션 시절·9-03~9-06 정리분)으로 보고 그대로 둔다 |
| 판정 글자 | URL + 제목. 단 제목이 URL 추정 제목(`guess_meta(url, '')['title']` 과 같음 — 「노션 자료 (제목 미확인)」 등)이면 제목은 넣지 않는다(추정 문구의 「노션」이 태그가 되지 않게) |
| 출처 | `http(s)://` 로 시작하면 `host_of(source)`(소문자·`www.` 제거). URL 호스트와 다르면 고치지 않고 `source_mismatch` 로 보고 |
| 노트 | 「AI 꿀팁」 노트(프론트매터 `notion_id` = record_id)를 **제자리에서** 바뀌는 칸의 줄만 — 프론트매터 `channel`·`category`·`keywords`, 본문 `- 📂 카테고리:`·`- 🏷 태그:`·`- 🗓 저장일: … 출처:`. 지금 장부 값과 글자 그대로 같은 줄이 정확히 1개씩이어야 한다. 아니면(손으로 고친 노트·노트 2개) 그 행은 **장부·노트 모두 건너뛰고** `skipped_note` 로 보고. 파일명·제목·관련 링크 그대로 |
| 쓰기 | 기본 dry-run. `--apply` 는 쓰기 전 `data/recategorize_backup/<시각>/`(장부 사본 = 온라인 백업 API · 바뀔 노트 원본 · manifest.json). 장부는 한 트랜잭션, 조건 `record_id` + 옛 `category`·`tags`·`source`, 행 수 1 아니면 전체 롤백. `updated_at` 새로 → 시트 미러가 다음 실행에 보낸다. 반영 뒤 `build_obsidian_wiki.py` → `build_search_index.py` |
| 재실행 | 고친 행은 v4.9 규칙 값과 같아 다시 대상이 되지 않는다 — 두 번째 실행 0행 |

## 3. 파일 — 패치 1개

`docs/tasks/patches/2026-10-13-v49-tips-recategorize.patch` (기준 = `e48208b`, 6개 파일, +702 −35)

```
sha256  3dd2601301a5d0fb35ecf538a717f1800668740a0f2de52aba68933416257cb8
```

| 파일 | 변경 |
|---|---|
| `lib/kakao_parse.py` | `_KEYWORD_TAGS` 한글 별칭 · `is_notion_host()` · `_tag_text()` · `classify()` 신규, `guess_meta` 가 `classify` 사용(분기별 `category = …` 제거). 반환값·메모 문구 그대로 |
| `scripts/recategorize_tips.py` | 신규 — 2절. `--apply` · `--no-rebuild` · `--db` · `--vault`. 종료 0 · 1 · 2(무변경). `RESULT_JSON:{tips, rows, category_changed, tags_changed, source_changed, notes, skipped_note, source_mismatch, manual_kept, moves, …}` |
| `scripts/test_recategorize_tips.py` | 신규 45건 — 분류 규칙 15 · 행 판단 7 · 임시 장부·Vault 흐름(dry-run 무변경·apply·노트 줄·관련 링크 보존·손으로 고친 노트 건너뜀·백업·재실행 0·계획 뒤 장부 변경 시 전체 롤백) · 입력 오류 · 네트워크 0 |
| `CLAUDE.md` · `AGENTS.md` · `README.md` | 머리 버전 v4.9 · 머리 요약(v4.8·v4.9) · 명령 · 회귀 14종 · 파일 표 · 카톡 절(「카테고리·태그는 classify 한 곳」·출처) · 이력 / README 안내 1줄 · 구조 · 명령 · 요약 행 · 상세 1절. AGENTS.md = 머리글 5줄 + CLAUDE.md 4행부터 |

### Cowork 사전 검증 (2026-10-13 22:00~, 맥 네이티브 · 레포 무변경)

- 홈 임시 폴더에 `git archive e48208b` + 코드 → 장부 사본(`.backup`)·Vault 「AI 꿀팁」 폴더 사본으로 실행.
- dry-run: 148건 중 **87행**(카테고리 15 · 태그 16 · 출처 71) · 노트 87 · 건너뜀 0 · 출처 불일치 0 · 사람이 고른 값 유지 91. 카테고리 이동 지식관리→모델/LLM 6 · 지식관리→기타 4 · 지식관리→개발툴 3 · 지식관리→프롬프트 1 · 기타→개발툴 1.
- apply(`--no-rebuild`, 사본): 장부 87행 · 노트 87개 수정(줄 204개) · 두 번째 dry-run 0행 · `integrity_check` ok · `source like 'http%'` 0 · 카테고리 기타 66 · 개발툴 41 · 모델/LLM 19 · 뉴스/트렌드 10 · 프롬프트 6 · 지식관리 3 · 사업/마케팅 3.
- 사람이 고른 값 유지 91 = 노션 이관 71(08-14) + 9-03·9-06 정리분 20(`MarkItDown`·`큐레이션`·`아카이브` 같은 손 태그, 의도적 `기타`). 규칙으로 덮지 않는 것이 맞다.

## 4. 실행 — 적용·테스트·커밋

### 4-0. 시간

스케줄러가 00·06·12·18시, wiki-ingest 가 17:30 에 돈다. **매시 50분 ~ 다음 시 20분, 17:25~17:45 에는 4-2 이후를 시작하지 않는다.** (6절 장부 쓰기도 같은 창을 피한다.)
판정은 시각의 **분**으로 한다 — `date '+%H:%M'` 의 분이 50~59 또는 00~20 이면(어느 시든) 창 **안**이다. 예: 21:51 은 창 안, 22:10 은 창 밖.

### 4-1. 시작 상태 (읽기만)

```bash
cd <REPO_ROOT>
git --no-optional-locks rev-parse --short HEAD          # e48208b
git --no-optional-locks status --porcelain
#   기대: 아래 두 줄만
#   ?? docs/tasks/2026-10-13-v49-tips-recategorize.md
#   ?? docs/tasks/patches/2026-10-13-v49-tips-recategorize.patch
shasum -a 256 docs/tasks/patches/2026-10-13-v49-tips-recategorize.patch   # 3절 값과 같아야 한다
grep -o '"outcome": "[a-z]*"' .run_state.json                              # "ok" (running 이면 멈춤)
```

어긋나면 **멈추고 보고**한다.

### 4-2. 패치 적용

```bash
git apply --check docs/tasks/patches/2026-10-13-v49-tips-recategorize.patch && git apply docs/tasks/patches/2026-10-13-v49-tips-recategorize.patch
git --no-optional-locks status --porcelain
#   기대: M AGENTS.md · M CLAUDE.md · M README.md · M lib/kakao_parse.py
#        ?? scripts/recategorize_tips.py · ?? scripts/test_recategorize_tips.py · ?? 지시서 · ?? 패치
{ head -5 AGENTS.md; tail -n +4 CLAUDE.md; } | cmp - AGENTS.md && echo AGENTS_OK
/opt/homebrew/bin/python3 -m py_compile lib/kakao_parse.py scripts/recategorize_tips.py scripts/test_recategorize_tips.py kakao_ingest.py && echo SYNTAX_OK
```

### 4-3. 회귀 테스트 14종 (네트워크 0회, 실제 장부·Vault·.env 무관)

```bash
/opt/homebrew/bin/node scripts/test_scheduler_guards.js      # 33/33 PASS
/opt/homebrew/bin/node scripts/test_video_summary.js         # 23/23
/opt/homebrew/bin/node scripts/test_resummarize.js           # 9/9
/opt/homebrew/bin/node scripts/test_wiki_search.js           # 34/34
/opt/homebrew/bin/python3 scripts/test_recategorize_tips.py  # 45/45  (신규)
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

### 4-4. 실데이터 dry-run (읽기만 — 장부·Vault 무변경)

```bash
/opt/homebrew/bin/python3 scripts/recategorize_tips.py > /tmp/v49_dry.log 2>&1; echo "exit=$?"
grep -c '' /tmp/v49_dry.log
tail -1 /tmp/v49_dry.log
#   기대 exit=0, 마지막 줄:
#   RESULT_JSON:{"ok": true, "dry_run": true, "tips": 148, "rows": 87, "category_changed": 15, "tags_changed": 16,
#                "source_changed": 71, "notes": 87, "skipped_note": 0, "source_mismatch": 0, "manual_kept": 91,
#                "moves": {"지식관리→모델/LLM": 6, "지식관리→기타": 4, "지식관리→개발툴": 3, "지식관리→프롬프트": 1, "기타→개발툴": 1}}
```

숫자가 하나라도 다르면 **멈추고** 그 줄과 `grep -E '건너뜀|출처·URL' /tmp/v49_dry.log` 를 그대로 보고한다(6절로 가지 않는다).

## 5. 커밋 (push 하지 않음)

```bash
git add AGENTS.md CLAUDE.md README.md lib/kakao_parse.py scripts/recategorize_tips.py scripts/test_recategorize_tips.py \
        docs/tasks/2026-10-13-v49-tips-recategorize.md docs/tasks/patches/2026-10-13-v49-tips-recategorize.patch
git commit -m "v4.9 꿀팁 분류 보정 — 노션 주소는 호스트 빼고 판정·한글 표기 별칭 · 기존 꿀팁 재분류·출처 호스트만 (recategorize_tips.py)"
git --no-optional-locks status --porcelain       # 커밋 뒤 기대: 빈 출력
git --no-optional-locks log --oneline -2
git --no-optional-locks show --stat HEAD | tail -10   # 8개 파일
```

## 6. 기존 꿀팁 반영 — 장부·Vault 쓰기 (대표님 승인 단계)

4-4 가 기대값과 같고 5 커밋이 끝났을 때만. 시간 창(4-0)을 다시 확인한다.

```bash
date '+%H:%M'                                                     # 창 밖이어야 한다
/opt/homebrew/bin/python3 scripts/recategorize_tips.py --apply > /tmp/v49_apply.log 2>&1; echo "exit=$?"
grep -E '💾 백업|🗄|📂 노트|✅|❌' /tmp/v49_apply.log
tail -1 /tmp/v49_apply.log
#   기대 exit=0 · 「장부 tips 87행 갱신」 · 「노트 87개 수정」 · ✅ build_obsidian_wiki.py · ✅ build_search_index.py
#   마지막 줄 RESULT_JSON 의 ok true · rows 87 · rebuild 둘 다 0
```

확인 (읽기만):

```bash
/opt/homebrew/bin/python3 scripts/recategorize_tips.py | tail -1        # rows 0 · manual_kept 91
sqlite3 "file:data/library.db?mode=ro" "select count(*) from tips where source like 'http%';"            # 0
sqlite3 "file:data/library.db?mode=ro" "select category, count(*) from tips group by 1 order by 2 desc;"
#   기타 66 · 개발툴 41 · 모델/LLM 19 · 뉴스/트렌드 10 · 프롬프트 6 · 지식관리 3 · 사업/마케팅 3
sqlite3 "file:data/library.db?mode=ro" "pragma integrity_check;"                                       # ok
/opt/homebrew/bin/python3 scripts/verify_library.py | grep RESULT_JSON                                  # ok true · tips_missing 0
/opt/homebrew/bin/python3 sync_obsidian.py --dry-run | grep RESULT_JSON                                 # tips_added 0
git --no-optional-locks status --porcelain                                                            # 빈 출력 (백업은 data/ 아래 — gitignore)
```

- 시트 「꿀팁」 탭은 다음 정시 실행의 시트 미러가 87행을 보낸다(`updated_at` 워터마크). 그 전 `sheet_mirror.py --check` 불일치는 정상.
- 자동 모드가 장부 쓰기를 막으면 그대로 멈추고 보고한다 — 대표님이 터미널에서 위 `--apply` 줄을 직접 실행한다.

## 7. 데몬

- 재기동 없음. `kakao_ingest.py`·`scheduler.js` 는 실행마다 새로 뜬다. 검색 서버(`server`·`wiki-lan`)는 인덱스 파일 mtime 이 바뀌면 다시 읽는다.

## 8. 롤백

- 커밋 전: `git apply -R docs/tasks/patches/2026-10-13-v49-tips-recategorize.patch` (새 파일 2개도 지워진다).
- 커밋 후·6절 전: `git revert HEAD`(push 전이면 `git reset --hard e48208b` 도 가능 — 지시서·패치는 다시 untracked 로 둔다).
- 6절 뒤 값 되돌리기: `data/recategorize_backup/<시각>/library.db` 로 장부 교체(스케줄러 창 밖, 교체 전 지금 장부를 따로 복사) · `manifest.json` 의 `edited` 노트를 백업 `vault/` 에서 Vault 로 복사 → `build_obsidian_wiki.py` · `build_search_index.py` · `sheet_mirror.py --full`.

## 9. 범위 밖

- `git push`.
- 사람이 고른 분류(91건) 손보기 — 바꿀 것이 있으면 따로 정한다.
- 카테고리 값·태그 이름 추가(예: `Codex`·`NotebookLM` 태그), 「뉴스/트렌드」·「사업/마케팅」 자동 판정 — 규칙이 이 둘을 만들지 않는 것은 그대로.
- 꿀팁 본문을 읽어 분류하는 2차 확장(Gemini) — 미구현 그대로.
- Cowork 스킬 `kakao-tips-update` 문구 갱신 — Cowork 몫.

## 10. 보고 형식 (한국어)

```
[CC-…] 결과
- 4-1 시작 상태: HEAD / porcelain / 패치 sha256 일치 여부 / outcome
- 4-2 적용: status 요약 / AGENTS_OK / SYNTAX_OK
- 4-3 테스트: 14종 각 n/n
- 4-4 dry-run: exit · 줄 수 · 마지막 줄 원문
- 5 커밋: 해시, show --stat
- 6 반영: 시각 · exit · grep 줄 원문 · 마지막 줄 원문 · 확인 명령 출력 원문
- 특이사항(멈춘 단계·기대와 다른 출력 원문)
```
