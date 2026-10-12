# 작업지시서 — v4.5 Wiki 합성 결과 누적 (장부 wiki_extract · 전체 재렌더 · backfill)

- 작성: 2026-10-12 (Cowork) · 실행: Claude Code (Sonnet 5.5) · 기준 커밋 `e1233e4`(v4.4)
- 패치: `docs/tasks/2026-10-12-wiki-extract-store.patch` — sha256 `192044535032fb2040a0f5e2709cc2039bb2ef1a907e566091a2f39e9958f51f`
- 보고는 한국어로. 기대값과 다르면 **그 단계에서 멈추고** 보고한다(다음 단계로 넘어가지 않는다).

## 1. 배경

`wiki_ingest.py` 는 소스마다 Gemini 로 엔티티·개념을 뽑아 `_wiki/entities`·`_wiki/concepts` 페이지와 `_wiki/index.md` 를 만든다. 그런데 `update_concept_page`·`update_entity_page`·`build_wiki_index` 가 **그 실행에서 뽑은 것만으로** 파일 전체를 다시 썼고, 추출 결과는 어디에도 저장하지 않았다(2026-05-12 도입 때부터).

- 실측(10-12 18:15): 합성 소스 3,619건인데 페이지 56개의 source_count 가 1~10, index 9행(마지막 실행분), `.wiki_state.json` 의 entities·concepts 도 마지막 실행분.
- 응답 JSON 이 깨지면 빈 결과로 성공 처리돼 그 소스가 조용히 빠졌다.
- 검색 인덱스·MCP 는 `_` 폴더를 읽지 않아 영향 없음. 타임머신에는 오늘 백업 2개뿐이라 옛 페이지를 되살릴 수 없다.

## 2. AS-IS → TO-BE

| 항목 | AS-IS | TO-BE |
|---|---|---|
| 추출 결과 | 저장 안 함 | 장부 새 표 `wiki_extract`(record_id = 노트 `notion_id`, status `ok`·`seed`·`failed`, entities·concepts·relations JSON, attempts) |
| 장부 버전 | user_version 1 | **2** (`lib/library_schema.sql`·`lib/library_db.py:SCHEMA_VERSION`). 기존 장부는 신규 `scripts/migrate_library.py --apply` |
| 페이지·index | 그 실행분으로 통째로 다시 씀 | 매 실행 끝에 `wiki_extract` 전체 × 현재 Vault(파일명·제목)로 다시 그림. 결정적(`last_updated` = 기여 행의 `updated_at`), 내용 같으면 안 씀. Vault 에서 빠진 소스 제외, retitle 반영 |
| 깨진 응답 | 빈 결과로 성공 처리 | `failed`, ingested 에 안 넣어 다음 실행이 재시도, 3회에서 포기 |
| 옛 소스 | — | 씨앗 `--seed-from-pages [--apply]`(지금 페이지 항목 → `seed`, 1회) + backfill(인자 없는 실행 = launchd 17:30 만, 20개 묶음, 하루(태평양시) 30회 상한, `.env`/환경변수 `WIKI_BACKFILL_DAILY_MAX`·`WIKI_BACKFILL_BATCH`) |
| sync_obsidian 경로 | `wiki_ingest.py` | `wiki_ingest.py --no-backfill` |
| 그 밖 | — | `--render-only`, `WIKI_RESULT` 에 `failed`·`entities`·`concepts`·`backfill_calls`·`backfill_done`·`backfill_left`, `backup_library.py` 행 수에 `wiki_extract`, `test_backup_library.py` 버전 기대값 = `SCHEMA_VERSION`, 신규 `scripts/test_wiki_ingest.py`(51), 문서 README·CLAUDE.md·AGENTS.md |

패치가 바꾸는 파일 11개: `AGENTS.md` `CLAUDE.md` `README.md` `backup_library.py` `lib/library_db.py` `lib/library_schema.sql` `scripts/migrate_library.py`(신규) `scripts/test_backup_library.py` `scripts/test_wiki_ingest.py`(신규) `sync_obsidian.py` `wiki_ingest.py`

파일 sha256(적용 후):

```
e8d69945c77054771a0d49018b916fa951dcd2bd9678e9eb0594b07ed95a0fd5  wiki_ingest.py
03049b484da8b9d420c917805a0345da3c8edb1fb8a9c0e105d164c75af35dbb  scripts/migrate_library.py
faa90ef733edb36225235496476c09d4cdf04cfac2e01cb07680df29d557b82d  scripts/test_wiki_ingest.py
24f654774b69f1598bc12576806381d4caf2e94456db9a8f88e7d893bbc985b1  lib/library_schema.sql
```

> ⚠️ 패치를 적용한 순간부터 장부를 이전(4단계)하기 전까지 **모든 실행(스케줄러·카톡·시트 미러·wiki_ingest)이 user_version 불일치로 던진다.** 3~5단계를 끊지 말고 이어서 한다.

## 3. 실행 순서 (`cd <REPO_ROOT>`, 파이썬은 `/opt/homebrew/bin/python3`)

### 3-0. 시간 창·사전 확인

- 지금 시각이 **정시 실행 창(00·06·12·18시 −10분 ~ +25분)과 17:25~17:55 밖**인지 확인. 안이면 창이 끝날 때까지 기다린다.
- `pgrep -fl "scheduler.js|wiki_ingest.py|sync_obsidian.py|kakao_ingest.py"` → 빈 출력.
- `git --no-optional-locks status --porcelain` → 아래 두 줄만(지시서·패치):
  ```
  ?? docs/tasks/2026-10-12-wiki-extract-store.md
  ?? docs/tasks/2026-10-12-wiki-extract-store.patch
  ```
- `git rev-parse --short HEAD` → `e1233e4`
- `shasum -a 256 docs/tasks/2026-10-12-wiki-extract-store.patch` → 위 sha256

### 3-1. 패치 적용

```bash
git apply --check docs/tasks/2026-10-12-wiki-extract-store.patch && git apply docs/tasks/2026-10-12-wiki-extract-store.patch
shasum -a 256 wiki_ingest.py scripts/migrate_library.py scripts/test_wiki_ingest.py lib/library_schema.sql   # 2절과 같아야 함
git --no-optional-locks status --porcelain   # M 9개 + ?? 4개(신규 2 + 지시서·패치)
```

### 3-2. 회귀 테스트 9종 (네트워크 0)

```bash
/opt/homebrew/bin/node scripts/test_scheduler_guards.js     # 29/29
for t in verify_library retitle_tips wiki_ingest kakao_ingest sync_obsidian sheet_mirror build_wiki_index backup_library; do
  printf "%s " $t; /opt/homebrew/bin/python3 scripts/test_$t.py 2>&1 | tail -1; done
```
기대: 16/16 · 49/49 · **51/51** · 18/18 · 23/23 · 45/45 · 10/10 · 50/50 — 전부 PASS.

### 3-3. 장부 이전 (user_version 1 → 2)

```bash
/opt/homebrew/bin/python3 scripts/migrate_library.py            # dry-run
/opt/homebrew/bin/python3 scripts/migrate_library.py --apply
```
- dry-run 기대: `"user_version": 1, "target": 2, "missing": ["wiki_extract"]`, 장부 무변경.
- apply 기대: `"ok": true, "user_version": 2, "integrity": "ok"`, `rows == rows_before`(행 수는 보고만), `backup` = `data/library.db.bak.v1-<시각>` 존재.

### 3-4. 씨앗 → 렌더

```bash
# 렌더 전 페이지 항목 목록 (비교용, 레포 밖 임시 파일)
/opt/homebrew/bin/python3 - <<'PY' > /tmp/wiki_links_before.json
import os, re, json, wiki_ingest as wi
out = {}
for kind, d in (('e', wi.ENTITIES_DIR), ('c', wi.CONCEPTS_DIR)):
    for f in sorted(os.listdir(d)):
        out[kind + '/' + f] = sorted(re.findall(r'^- \[\[([^|]+?)\|', open(os.path.join(d, f), encoding='utf-8').read(), re.M))
print(json.dumps(out, ensure_ascii=False))
PY
/opt/homebrew/bin/python3 wiki_ingest.py --seed-from-pages | grep -E "SEED_RESULT|매칭 실패"
/opt/homebrew/bin/python3 wiki_ingest.py --seed-from-pages --apply | grep SEED_RESULT
/opt/homebrew/bin/python3 wiki_ingest.py --render-only | grep WIKI_RESULT
/opt/homebrew/bin/python3 wiki_ingest.py --render-only | grep WIKI_RESULT     # 2회차
```
- 씨앗 dry-run 기대: `pages` 56 · `unmatched` 0 · `written` 0. (`items`·`records` 는 보고만 — 사전 검증 때 78 · 59)
- 씨앗 apply 기대: `written` = dry-run 의 `records`.
- 렌더 1회차 기대: `entities` 32 · `concepts` 24 · `processed` 0 · `backfill_left` null.
- 렌더 2회차 기대: `entities_updated` 0 · `concepts_updated` 0(결정적 렌더).
- 항목 보존 확인 — 위 스크립트를 `/tmp/wiki_links_after.json` 으로 다시 돌린 뒤:
  ```bash
  /opt/homebrew/bin/python3 -c "import json;a=json.load(open('/tmp/wiki_links_before.json'));b=json.load(open('/tmp/wiki_links_after.json'));print('같음' if a==b else [k for k in a if a[k]!=b.get(k)])"
  grep -c '^| \[\[' "$(/opt/homebrew/bin/python3 -c 'import wiki_config as w;print(w.WIKI_DIR)')/index.md"    # 56
  ```
  기대: `같음`, index 56행.

### 3-5. backfill 시험 1회 (실제 Gemini 1호출)

묶음 응답 형식을 실제 모델로 1회 확인한다. 증분 대상이 있으면 그것도 처리된다(보통 0).

```bash
WIKI_BACKFILL_DAILY_MAX=1 /opt/homebrew/bin/python3 wiki_ingest.py | grep -E "backfill|WIKI_RESULT|⏸|❌"
sqlite3 "file:data/library.db?mode=ro" "select status, source, count(*) from wiki_extract group by 1,2;"
```
- 기대: `backfill_calls` 1 · `backfill_done` **15 이상**(20개 중) · `errors` 0. `backfill_left` 는 보고(3,137 근처 − done).
- `backfill_calls` 0 이고 `⏸`(할당량)면 오늘 키가 소진된 것 — 실패 아님, 보고만 하고 다음 단계로.
- **`backfill_done` 이 0~14 면 멈춘다.** `.env` 에 `WIKI_BACKFILL_DAILY_MAX=0` 한 줄을 넣어 내일 17:30 backfill 을 막고, 출력 전체를 보고한다(커밋은 진행 — 누적·렌더 수정은 유효하다).

### 3-6. 장부·연계 확인

```bash
/opt/homebrew/bin/python3 scripts/verify_library.py | grep RESULT_JSON        # "ok": true · vault_missing 0 · tips_missing 0
/opt/homebrew/bin/python3 sheet_mirror.py --check                              # match true (장부 v2 로 열림)
/opt/homebrew/bin/python3 backup_library.py --status                           # 오류 없이 출력
sqlite3 "file:data/library.db?mode=ro" "pragma user_version; pragma integrity_check;"   # 2 / ok
git check-ignore -q data/library.db && echo ignored
```

### 3-7. 커밋 (push 는 별도 지시)

```bash
git add AGENTS.md CLAUDE.md README.md backup_library.py lib/library_db.py lib/library_schema.sql \
  scripts/migrate_library.py scripts/test_backup_library.py scripts/test_wiki_ingest.py sync_obsidian.py wiki_ingest.py \
  docs/tasks/2026-10-12-wiki-extract-store.md docs/tasks/2026-10-12-wiki-extract-store.patch
git commit -m "v4.5 Wiki 합성 결과 누적 — 장부 wiki_extract(user_version 2) + 전체 재렌더 · 실패 재시도 · 씨앗 · backfill"
git --no-optional-locks status --porcelain    # 빈 출력 (커밋 뒤)
git log --oneline -1
```

## 4. 데몬 재기동

없음. 상주 데몬(`server`·`wiki-lan`)은 장부·wiki_ingest 를 쓰지 않는다. `ytsummarizer`·`wiki-ingest` 는 실행마다 새 프로세스. plist·`.env` 무변경(backfill 설정은 기본값 30·20).

## 5. 롤백

- 커밋 전: `git checkout -- . && rm scripts/migrate_library.py scripts/test_wiki_ingest.py` → 장부 되돌리기 `cp data/library.db.bak.v1-<시각> data/library.db`(이전이 표 하나 추가뿐이라 그 사이 변경은 wiki_extract 뿐) → `wiki_ingest.py` 옛 코드로 `_wiki` 페이지는 다음 실행부터 다시 실행분 방식.
- 커밋 뒤: `git revert <커밋>` + 위 장부 되돌리기. 정시 실행 창 밖에서.

## 6. 범위 밖

- `git push`(검증 뒤 별도 지시), plist·`.env` 변경, Gemini 무료 한도 방침, `--full` 재분석, 꿀팁 41건 제목 보완.
- backfill 진행 판정은 Cowork 가 이후 17:30 실행의 `WIKI_RESULT`(`~/Library/Logs/irichgreen/wiki-ingest.log`)로 한다 — 약 6일.
