# 작업지시서 [CC-1011-A] — v4.0 1단계: 노션 → SQLite 적재 (노션 읽기 전용)

- 작성: 2026-10-11 · Cowork
- 영역: **Python** (신규 파일만. 기존 코드 무변경)
- 대상 파일: `scripts/notion_to_sqlite.py`(신규), `scripts/test_notion_to_sqlite.py`(신규), `lib/library_db.py`(신규), `lib/library_schema.sql`(신규), `.gitignore`, `CLAUDE.md`, `AGENTS.md`
- 요약: 노션「AI YouTube 요약 자료」「AI 꿀팁」 두 DB 를 읽어 로컬 `data/library.db`(SQLite 1파일)로 옮긴다. 노션에는 읽기 요청만 보낸다. 스케줄러·동기화 코드는 이번에 건드리지 않는다(2단계).

## 1. 배경

노션을 떠나기로 했다(2026-10-11). v4.0 방안 A 는 다음 셋으로 나눈다.

| 단계 | 내용 | 지시서 |
|---|---|---|
| 1 | 노션 → SQLite 적재 (노션 읽기 전용) | **이 문서** |
| 2 | `scheduler.js`·`kakao_ingest.py`·`sync_obsidian.py` 를 SQLite 로 전환, 노션 프록시 제거 | 다음 |
| 3 | 구글 시트 미러(GAS 웹앱), 노션 코드·키 제거, 문서 정리, v4.0 | 그다음 |

노션 해지는 이 1단계가 끝나야 할 수 있다. 정확한 page id(= Obsidian 노트의 `notion_id`)를 잃지 않고 옮기는 것이 이 단계의 목적이다.

### 설계 결정

- **record_id = 노션 page id(하이픈 포함).** Obsidian 프론트매터 `notion_id` 와 같은 값이다. 이름을 바꾸지 않으므로 `wiki_ingest`·`build_search_index`·고아 격리가 그대로 맞물린다. v4.0 이후 새로 만드는 행은 uuid4.
- **중복(같은 video_id) 은 하나만 남긴다.** v3.2.1 이전 빈 캐시 사고로 생긴 중복 약 195건을 여기서 정리한다(`[CC-1005-B]` 는 취소됨).
  - 남길 행: Obsidian 노트가 가리키는 page. 여럿이면 그중 가장 오래된 것. 노트가 없으면 전체에서 가장 오래된 것.
  - 나머지는 `videos_dup` 에 **보관**한다(삭제 아님). `has_vault_note=1` 인 행은 2단계 첫 동기화에서 고아 격리(`_trash/`) 대상이 된다 — 같은 영상의 두 번째 노트이므로 의도된 결과다.
  - 남긴 행의 `topics` 는 그룹 전체의 합집합이다(재생목록 소속을 잃지 않게).
- **summary 는 `요약 내용` 속성의 원문 마크다운**(Gemini 출력 그대로, `**` 포함). 비어 있으면 본문 블록(구분선 뒤)에서 복원한다. rich_text 가 25개 이상이면 잘렸을 수 있으므로 속성 단독 조회로 끝까지 다시 받는다.
- **속성과 본문이 다른 페이지가 있는지 모른다**(옛 코드가 속성을 잘라 저장했을 가능성). 그래서 dry-run 에서 무작위 100건을 본문 블록과 대조하고, 하나라도 다르면 apply 를 `--summary-check=all`(전량 대조, 다르면 본문 쪽 채택)로 돌린다. 4-4 절의 규칙대로 기계적으로 고른다.
- **전부 읽었거나, 아무것도 쓰지 않거나.** `library.db.tmp` 에 쓰고 건수·`integrity_check` 가 맞을 때만 rename 한다. 노션 401/403 은 즉시 종료(코드 2), 429/5xx 는 `lib/tips_notion.py:notion_call` 의 지수 백오프(2·4·8·16초) 후 실패. 0건이면 중단. Vault 에서 `notion_id` 를 하나도 못 찾으면 노션 호출 전에 중단(중복 판정 근거가 없으므로).
- 스키마 원본은 `lib/library_schema.sql` 하나다. 2단계에서 Node(`node:sqlite`)도 같은 파일을 실행한다. 이번 4-6 절에서 데몬 node 로 읽기만 확인한다.
- `library.db` 는 **스냅샷**이다. 2단계 전환 때까지 노션이 계속 원본이고, 스케줄러가 노션에 계속 쓴다. 2단계 지시서는 스케줄러를 멈춘 상태에서 `--apply --replace` 로 다시 적재한 뒤 전환한다.

### 사전 검증 (Cowork, 2026-10-11)

리눅스 샌드박스(Python 3.13, node 22)에서 가짜 노션(`urlopen` 교체)·임시 Vault 로 확인했다.

- `scripts/test_notion_to_sqlite.py` **31/31 PASS**. 네트워크 0회, 실제 Vault·`data/` 무변경.
- 변이 시험: 남길 행 규칙을 "가장 오래된 것"으로 바꾸면 3건 FAIL, rich_text 재조회를 끄면 2건 FAIL — 테스트가 규칙을 실제로 잡는다.
- Python 이 만든 DB 를 `node:sqlite`(`DatabaseSync`, readOnly)로 열어 `user_version`·한글 행을 읽음.
- 실제 노션·맥 Vault·Homebrew 파이썬에서는 돌려 보지 못했다 → 4절에서 확인한다.

## 2. 파일 배치

Cowork 가 아래 4개와 이 지시서를 레포에 미리 넣어 두었다(untracked). 내용을 바꾸지 말고 해시만 확인한다.

| 파일 | 줄 | sha256 |
|---|---|---|
| `lib/library_schema.sql` | 73 | `b2def8c19819c2baa6084b44d72c54aaff802ae7d2487d665e6312a70326b7f4` |
| `lib/library_db.py` | 32 | `7af5073f4cca04e54421ed29e3aa50832cebfd0abeed75a554610a9bd97a549a` |
| `scripts/notion_to_sqlite.py` | 427 | `0afc72874ced93d32e7cc31e100f084d6e514fb906fc25cf92a3d20b3f11ec96` |
| `scripts/test_notion_to_sqlite.py` | 285 | `d5d31d632eae602f430f249b7b75b9719c04849d57e8c137d66da81f85ac0735` |

```bash
cd <REPO_ROOT>
shasum -a 256 lib/library_schema.sql lib/library_db.py scripts/notion_to_sqlite.py scripts/test_notion_to_sqlite.py
```

하나라도 다르면 멈추고 보고한다.

### 2-1. `.gitignore`

`data/` 는 노션에서 옮긴 개인 요약 데이터다. 공개 레포에 절대 올라가면 안 된다.

**AS-IS** (파일 끝)

```
# Cowork 세션 산출물 사본 (앱이 연결 폴더에 만든다 — 개인 환경별 상이, 2026-10-03)
Claude outputs/
```

**TO-BE**

```
# Cowork 세션 산출물 사본 (앱이 연결 폴더에 만든다 — 개인 환경별 상이, 2026-10-03)
Claude outputs/

# v4.0 로컬 원본 장부 (노션에서 옮긴 요약·꿀팁 전체 — 공개 레포에 절대 포함 금지, 2026-10-11)
# library.db · .tmp · .bak.* · -journal 모두 이 폴더 안에 생긴다
data/
```

```bash
mkdir -p data && touch data/library.db data/library.db.tmp data/library.db.bak.20261011_000000
git check-ignore -v data/library.db data/library.db.tmp data/library.db.bak.20261011_000000
rm data/library.db data/library.db.tmp data/library.db.bak.20261011_000000 && rmdir data
```

기대: 3줄 모두 `.gitignore:<줄>:data/` 로 걸린다. 하나라도 안 걸리면 멈춘다.

## 3. 사용법 (스크립트 머리 주석과 같음)

```bash
/opt/homebrew/bin/python3 scripts/notion_to_sqlite.py                      # dry-run: 노션을 읽고 보고만. 파일 안 씀
/opt/homebrew/bin/python3 scripts/notion_to_sqlite.py --apply              # data/library.db 생성 (이미 있으면 거부)
/opt/homebrew/bin/python3 scripts/notion_to_sqlite.py --apply --replace    # 기존 파일을 .bak.<시각> 으로 옮기고 새로 생성
/opt/homebrew/bin/python3 scripts/notion_to_sqlite.py --verify             # 노션 호출 없이 library.db ↔ Vault 대조
  --summary-check=N     무작위 N건 요약 대조(보고만, 기본 20, 0=끔)
  --summary-check=all   전량 대조, 다르면 본문 블록 쪽 채택 (페이지당 1회 호출, 약 30분)
```

마지막 줄에 `RESULT_JSON {...}` 을 찍는다. 판정은 이 줄로 한다.

## 4. 실행·검증

**스케줄러 실행 시각(00·06·12·18시) 앞뒤 15분은 피한다.** 노션 조회가 겹치면 rate limit 을 나눠 쓰게 된다. 데몬은 멈추지 않는다(이번 단계는 노션 읽기만 한다).

### 4-1. 시작 상태

```bash
cd <REPO_ROOT>
git status --short
git log --oneline -1
```

기대: untracked 는 2절 4개 + 이 지시서(`docs/tasks/2026-10-11-v4-notion-to-sqlite.md`)뿐, HEAD `8ccbc09`. 다른 변경이 있으면 멈추고 보고한다.

### 4-2. 회귀 테스트 (네트워크 0회)

```bash
/opt/homebrew/bin/python3 scripts/test_notion_to_sqlite.py
```

기대: 마지막 줄 `31/31 PASS`, `data/` 폴더가 생기지 않음(`ls -d data 2>/dev/null` 결과 없음 — 테스트는 임시 폴더만 쓴다).

### 4-3. dry-run (노션 읽기, 파일 안 씀)

```bash
/opt/homebrew/bin/python3 scripts/notion_to_sqlite.py --summary-check=100 2>&1 | tee /tmp/n2s-dryrun.log
```

`CERTIFICATE_VERIFY_FAILED` 가 나면 `/usr/bin/python3` 로 한 번 더 시도하고 어느 쪽이 됐는지 보고한다.
종료 코드 2(🛑 401/403)면 **재시도하지 말고** 멈춰 보고한다.

기대 (`RESULT_JSON` 기준):

| 키 | 기대 | 어긋나면 |
|---|---|---|
| 종료 코드 | 0 | 멈춤 |
| `video_pages` | 3,175 이상 (10-11 내보내기 시점 3,175) | 멈춤 |
| `videos_dup` | 200 안팎 (빈 캐시 중복 195 + 이전 중복) | 300 넘으면 멈춤 |
| `tips` | 135 이상 | 멈춤 |
| `vault_missing` | 0 | 멈춤 (Vault 노트가 노션에 없는 page 를 가리킴) |
| `tips_missing` | 0 | 멈춤 |
| `no_video_id` | 0 에 가까움 | 보고만 |
| `summary_src` | 대부분 `property` | `empty` 가 10 넘으면 보고만 |
| `summary_check.match` | 보고 | 4-4 에서 분기 |

멈출 때는 `/tmp/n2s-dryrun.log` 의 `📊 결과` 블록 전체를 보고에 붙인다.

### 4-4. apply

4-3 의 `summary_check` 에서 불일치(`checked - match`)가 **0 이면 A, 1 이상이면 B** 를 실행한다. 다른 선택은 하지 않는다.

```bash
# A — 요약 속성 = 본문
/opt/homebrew/bin/python3 scripts/notion_to_sqlite.py --apply --summary-check=0 2>&1 | tee /tmp/n2s-apply.log
# B — 다른 페이지가 있음: 전량 대조 (약 30분)
/opt/homebrew/bin/python3 scripts/notion_to_sqlite.py --apply --summary-check=all 2>&1 | tee /tmp/n2s-apply.log
```

기대: 종료 코드 0, `💾 … 작성 {'videos': …, 'videos_dup': …, 'tips': …}` 줄, `RESULT_JSON.written` 이 4-3 의 건수와 같거나 그 사이 스케줄러가 더한 만큼만 많다. B 였다면 `summary_check.replaced_by_blocks` 를 보고한다.

### 4-5. verify (노션 호출 없음)

```bash
/opt/homebrew/bin/python3 scripts/notion_to_sqlite.py --verify
ls -la data/
```

기대: `✅ 검증 통과`, `user_version 1 · integrity_check ok`, `videos 안 video_id 중복 0`, `어디에도 없음 0`, 꿀팁 `없음 0`. `data/` 에는 `library.db` 하나(`.tmp` 없음).

### 4-6. 데몬 node 로 읽기 (2단계 준비)

```bash
/opt/homebrew/bin/node -e "
const {DatabaseSync}=require('node:sqlite');
const db=new DatabaseSync('data/library.db',{readOnly:true});
const one=s=>Object.values(db.prepare(s).get())[0];
console.log('node', process.version, '| user_version', one('PRAGMA user_version'),
  '| videos', one('SELECT COUNT(*) FROM videos'), '| dup', one('SELECT COUNT(*) FROM videos_dup'),
  '| tips', one('SELECT COUNT(*) FROM tips'));
const r=db.prepare(\"SELECT title, topics, length(summary) n FROM videos WHERE summary_src='property' ORDER BY created_at DESC LIMIT 1\").get();
console.log('최신 1건:', r.title.slice(0,40), r.topics, r.n+'자');"
```

기대: `node v26.x`, 건수가 4-5 와 같음, 한글 제목·topics JSON 이 깨지지 않음. 실험 기능 경고(ExperimentalWarning)는 무시한다.

### 4-7. 무변경 확인

```bash
git status --short
git diff --stat
```

기대: 수정은 `.gitignore` 하나(5절 문서 갱신 전), untracked 는 2절 4개 + 이 지시서뿐. `data/` 가 보이면 2-1 이 잘못된 것이다 — 커밋하지 말고 멈춘다.

## 5. 문서

### 5-1. `CLAUDE.md`

① Commands 블록의 `# 스케줄러 네트워크 안전장치 회귀 테스트 (v3.2.1)` 두 줄 **다음**에 추가:

```bash
# v4.0 1단계 — 노션 → SQLite 적재 (노션 읽기 전용, 기본 dry-run). 산출물 data/library.db (gitignore)
/opt/homebrew/bin/python3 scripts/notion_to_sqlite.py                    # dry-run
/opt/homebrew/bin/python3 scripts/notion_to_sqlite.py --apply --replace  # 다시 적재 (기존 파일은 .bak.<시각>)
/opt/homebrew/bin/python3 scripts/notion_to_sqlite.py --verify           # 노션 호출 없이 library.db ↔ Vault 대조
/opt/homebrew/bin/python3 scripts/test_notion_to_sqlite.py               # 회귀 테스트 (네트워크 0회, 31/31)
```

② 핵심 파일 역할 표 끝에 2행 추가:

```
| `scripts/notion_to_sqlite.py` | (v4.0 1단계) 노션 두 DB → `data/library.db`. 노션 읽기 전용, 기본 dry-run. 중복 video_id 는 Vault 노트 기준으로 하나만 남기고 `videos_dup` 에 보관. |
| `lib/library_schema.sql` · `lib/library_db.py` | (v4.0) 로컬 원본 장부 스키마(원본은 `.sql` 하나 — Node 도 같은 파일을 실행) · Python 헬퍼. |
```

③ `### 중요한 제약사항` 바로 위에 절 추가:

```markdown
### v4.0 이행 중 — 로컬 원본 장부 `data/library.db` (2026-10-11~)

- **지금(1단계 완료 ~ 2단계 전)은 노션이 여전히 원본이다.** `library.db` 는 적재 시점의 스냅샷이고 스케줄러는 노션에 쓴다. 2단계는 스케줄러를 멈추고 `--apply --replace` 로 다시 적재한 뒤 전환한다.
- `record_id` = 노션 page id(하이픈 포함) = Obsidian `notion_id`. **프론트매터 키 이름 `notion_id` 를 바꾸지 말 것** — wiki_ingest·검색 인덱스 상태가 이 값에 묶여 있다. 새 행은 uuid4.
- `data/` 는 gitignore. 개인 요약 전체가 들어 있다 — `git check-ignore -q data/library.db` 로 확인.
- `videos_dup` 은 지우지 않는다(중복 페이지 보관, 되돌림용). `has_vault_note=1` 행의 노트는 2단계 첫 동기화에서 `_trash/` 로 격리된다(의도됨).
- 스키마를 바꾸면 `lib/library_schema.sql` 의 `PRAGMA user_version` 을 올리고 `lib/library_db.py:SCHEMA_VERSION` 도 같이 올린다.
```

④ 변경 이력 맨 위에 1행:

```markdown
- **2026-10-11 (v4.0 1단계)** — 노션 → SQLite 적재. 신규 `scripts/notion_to_sqlite.py`(노션 읽기 전용, 기본 dry-run, `--apply`·`--replace`·`--verify`·`--summary-check`), `scripts/test_notion_to_sqlite.py`(31/31, 네트워크 0회), `lib/library_schema.sql`·`lib/library_db.py`. `.gitignore` 에 `data/`. 적재 결과: 영상 페이지 <N> → videos <N> · videos_dup <N> · tips <N>, 요약 대조 <결과>. 기존 파이프라인 코드 무변경(노션이 아직 원본). 지시서 `docs/tasks/2026-10-11-v4-notion-to-sqlite.md`.
```

`<N>`·`<결과>` 는 4-4·4-5 의 실제 값으로 채운다.

### 5-2. `AGENTS.md`

5-1 의 ③ 절과 ④ 이력 1행을 같은 내용으로 넣는다(위치는 AGENTS.md 의 대응 절). 어긋나면 `CLAUDE.md` 가 이긴다.

### 5-3. `README.md`

이번에는 버전 행을 추가하지 않는다. v4.0 행은 3단계에서 한 번에 쓴다.

## 6. 커밋 (push 하지 않음)

```bash
git add .gitignore lib/library_schema.sql lib/library_db.py scripts/notion_to_sqlite.py scripts/test_notion_to_sqlite.py CLAUDE.md AGENTS.md docs/tasks/2026-10-11-v4-notion-to-sqlite.md
git status --short          # data/ 가 staged 목록에 없어야 한다
git commit -m "v4.0 1단계: 노션 → SQLite 적재 스크립트 (노션 읽기 전용)"
git show --stat HEAD
```

`git push` 는 하지 않는다. 대표님 확인 후 별도로 한다.

## 7. 데몬 재기동

없음. 실행 중인 코드는 바뀌지 않았다.

## 8. 롤백

```bash
cd <REPO_ROOT>
rm -f data/library.db data/library.db.tmp data/library.db.bak.*     # 노션은 손대지 않았으므로 지우면 끝
git revert --no-edit HEAD                                              # 커밋까지 했다면
```

## 9. 범위 밖

- `scheduler.js`·`sync_obsidian.py`·`kakao_ingest.py`·`server.js` 수정 — 2단계.
- 노션 쓰기·수정·삭제. **노션의 중복 페이지도 지우지 않는다.** 노션은 해지와 함께 사라진다.
- 구글 시트 미러 — 3단계.
- `kakao-tips-update` 스킬 갱신 — 2단계 이후.
- `CLAUDE.md` 5행 개인 절대경로 표기 교정 — 3단계 문서 갱신 때.

## 10. 보고 형식 (한국어)

1. 2절 해시 4개 일치 여부, 2-1 `check-ignore` 출력
2. 4-2 마지막 줄
3. 4-3 `📊 결과` 블록 + `RESULT_JSON` 전문, 사용한 파이썬 경로
4. 4-4 에서 고른 것(A/B)과 `RESULT_JSON` 전문
5. 4-5 출력 전문, `ls -la data/`
6. 4-6 출력
7. `git show --stat HEAD`
8. 기대와 다른 점 — 없으면 "없음"
