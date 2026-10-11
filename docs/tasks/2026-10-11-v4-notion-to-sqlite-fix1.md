# [CC-1011-B] v4.0 1단계 보정 — Vault 스캔을 프론트매터로 한정 + 고아 꿀팁 노트 1건 격리

> 선행: `docs/tasks/2026-10-11-v4-notion-to-sqlite.md` ([CC-1011-A]). 그 지시서는 **고치지 않는다.**
> 이 문서가 A 의 2절(해시)·4-1(시작 상태)·4-2(테스트 수)·4-3(게이트)·5절·6절 일부를 **대체**한다. 나머지는 A 그대로.

## 1. 배경 — A 의 4-3 dry-run 이 멈춘 이유 (Cowork 확인, 2026-10-11 17:44)

A 의 dry-run 은 `vault_missing 1`·`tips_missing 1` 로 게이트에서 멈췄다. 다른 값은 전부 기대 안
(영상 페이지 3,185 · videos 2,982 · videos_dup 203 · tips 135 · 요약 대조 100/100 일치).
노션 읽기 + Vault 읽기로 두 id 를 찾았다.

| 구분 | Vault 파일 | notion_id | 노션 | 원인 |
|---|---|---|---|---|
| 영상 | `schema.md` (Vault 루트) | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` | 형식 오류(uuid 아님) | `build_obsidian_wiki.py` 가 매번 생성하는 스키마 문서의 **본문 코드블록 예시**. `sync_obsidian.get_existing_vault_info()` 가 파일 전체에서 `^notion_id:` 를 찾아 영상 노트로 셌다 → **스캔 범위 문제** |
| 꿀팁 | `AI 꿀팁/20260903_개인 아카이브 페이지 (제목 미확인)_4187b1.md` | `3d3a3cbc-5c7a-8139-8b42-ef79c74187b1` | GET 404 (삭제됨) | 같은 URL(`…3bfd86104de280319550e7e13a18a4ee.html`)의 꿀팁이 다른 page(`…81de-887a-…`)로 노션에 살아 있고 그 노트도 Vault 에 있다. 지워진 **중복 page 의 잔여 노트**. 꿀팁 폴더는 고아 격리 대상이 아니라 남아 있었다 |

조치:
- 영상 쪽은 **스크립트 수정**. `schema.md` 는 매 실행 다시 생성되므로 파일을 옮겨도 소용없다.
- 꿀팁 쪽은 **노트를 `_trash/` 로 격리**(삭제 아님, 되돌릴 수 있음). 게이트 기준(0)은 완화하지 않는다.

## 2. 파일 — Cowork 가 미리 고쳐 둠 (내용 바꾸지 말고 해시만 확인)

| 파일 | 줄 | sha256 | A 대비 |
|---|---|---|---|
| `lib/library_schema.sql` | 73 | `b2def8c19819c2baa6084b44d72c54aaff802ae7d2487d665e6312a70326b7f4` | 같음 |
| `lib/library_db.py` | 32 | `7af5073f4cca04e54421ed29e3aa50832cebfd0abeed75a554610a9bd97a549a` | 같음 |
| `scripts/notion_to_sqlite.py` | 457 | `324a68ea33960396ae0a7203a65202f7cb8b6237df1245462eb3b265f90e2a91` | 변경 |
| `scripts/test_notion_to_sqlite.py` | 291 | `c97d39c963091ec75eef46f91ed78b7f3a11ac7986871cecc8a3da0025ffacd5` | 변경 |

```bash
cd <REPO_ROOT>
shasum -a 256 lib/library_schema.sql lib/library_db.py scripts/notion_to_sqlite.py scripts/test_notion_to_sqlite.py
```

하나라도 다르면 멈추고 보고한다.

### 변경 내용

`scripts/notion_to_sqlite.py`
- `fm_notion_id(path)` 신설 — 파일 맨 앞 YAML 프론트매터(`---` … `---`) 안의 `notion_id` 만 읽는다.
- `vault_ids()` — 폴더 스캔 규칙은 `so.get_existing_vault_info()` 그대로, id 는 프론트매터 안의 것만 센다.
  본문에만 있는 파일은 모듈 변수 `VAULT_IGNORED` 에 모아 로그로 찍는다. 꿀팁 폴더도 같은 함수로 읽는다.
- dry-run 이 `[영상 없음]`·`[꿀팁 없음]` id 를 최대 10개 출력(전에는 verify 만 출력).
- dry-run·verify `RESULT_JSON` 에 `vault_ignored` 추가.

`scripts/test_notion_to_sqlite.py`
- 임시 Vault 에 `schema.md`(본문 코드블록에 예시 notion_id)와 `AI 꿀팁/README.md`(본문에 notion_id) 추가.
- 검사 1개 추가: `vault_missing 0 · tips_missing 0 · vault_ignored 1`. **31 → 32.**
- 변이 시험(Cowork): A 의 원래 스크립트로 이 테스트를 돌리면 `30/32` — 실측과 같은 `vault_missing 1 · tips_missing 1` 로 실패한다.

`sync_obsidian.py` 는 **고치지 않는다**(같은 스캔 방식이지만 고아 격리는 `video_url`+토픽 폴더만 대상이라 지금은 무해). 2단계 지시서에서 다룬다.

## 3. 실행

**스케줄러 실행 시각(00·06·12·18시) 앞뒤 15분은 피한다.** 데몬은 멈추지 않는다.

### 3-1. 시작 상태

```bash
cd <REPO_ROOT>
git status --short
git log --oneline -1
ls -d data 2>/dev/null
```

기대: ` M .gitignore`(A 의 2-1 에서 `data/` 추가한 것) + untracked 6개
(A 의 4파일 · A 지시서 · 이 문서 `docs/tasks/2026-10-11-v4-notion-to-sqlite-fix1.md`), HEAD `8ccbc09`, `data` 없음.
`git diff .gitignore` 는 `+data/` 관련 줄만이어야 한다. 다르면 멈추고 보고한다.

### 3-2. 고아 꿀팁 노트 격리 (삭제 아님)

```bash
V=~/"Documents/Obsidian/AI LLM Wiki/AI LLM Wiki"
F="20260903_개인 아카이브 페이지 (제목 미확인)_4187b1.md"
grep -n '^notion_id:' "$V/AI 꿀팁/$F"                      # 3d3a3cbc-5c7a-8139-8b42-ef79c74187b1 이어야 함. 다르면 멈춤
grep -l 'notion_id: 3d3a3cbc-5c7a-81de-887a-f62a2c644974' "$V/AI 꿀팁/"*.md   # 살아 있는 쪽 노트가 1개 나와야 함. 없으면 멈춤
STAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p "$V/_trash/$STAMP/AI 꿀팁"
mv "$V/AI 꿀팁/$F" "$V/_trash/$STAMP/AI 꿀팁/"
ls "$V/AI 꿀팁/"*.md | wc -l                                # 135
ls "$V/_trash/$STAMP/AI 꿀팁/"
```

파일명은 macOS 에서 NFD 일 수 있다. `mv` 가 "No such file" 이면 `ls "$V/AI 꿀팁/" | grep 4187b1` 로 실제 이름을 찾아 그 이름으로 옮기고 보고한다.
Obsidian `log.md` 에는 쓰지 않는다(수동 1건). `_trash/20260821_172922/` 는 건드리지 않는다.

### 3-3. 회귀 테스트

```bash
/opt/homebrew/bin/python3 scripts/test_notion_to_sqlite.py
ls -d data 2>/dev/null
```

기대: 마지막 줄 `32/32 PASS`, `data` 없음.

### 3-4. dry-run — A 의 4-3 명령 그대로

```bash
/opt/homebrew/bin/python3 scripts/notion_to_sqlite.py --summary-check=100 2>&1 | tee /tmp/n2s-dryrun.log
```

게이트는 A 의 4-3 표 그대로 + 아래 두 줄:

| 키 | 기대 | 어긋나면 |
|---|---|---|
| `vault_ignored` | 1 (로그 `프론트매터 밖 notion_id 라 제외 1 ['schema.md']`) | 다른 파일이 나오면 멈춤 |
| `vault_missing` · `tips_missing` | 둘 다 0 | 멈춤 (로그의 `[영상 없음]`·`[꿀팁 없음]` id 를 보고) |

참고 기대치(17:27 실측): `video_pages` 3,185 · `videos` 2,982 · `videos_dup` 203 · `tips` 135. 그사이 스케줄러가 저장했다면 그만큼만 늘어난다.

### 3-5. 이후 — A 의 4-4 ~ 4-7 그대로

A/B 선택 규칙도 그대로(이번 `summary_check` 불일치 0 → A). 4-5 verify 의 `RESULT_JSON` 에도 `vault_ignored 1` 이 나와야 한다.

## 4. 문서 — A 의 5절에서 바뀌는 것만

- 5-1 ① 의 테스트 주석 `31/31` → `32/32`.
- 5-1 ④ 이력 1행의 `(31/31, 네트워크 0회)` → `(32/32, 네트워크 0회)`, 그리고 문장 끝 `지시서 …` 앞에 다음을 넣는다:
  `Vault 대조는 프론트매터 안의 notion_id 만 센다(Vault 루트 schema.md 본문 예시가 영상 id 로 잡혀 1차 dry-run 이 멈췄다). 노션에서 지워진 중복 꿀팁 page 의 잔여 노트 1건을 _trash/<시각>/AI 꿀팁/ 으로 격리.`
  지시서 표기는 `docs/tasks/2026-10-11-v4-notion-to-sqlite.md`·`-fix1.md`.
- 5-2 `AGENTS.md` 도 같은 문구.

## 5. 커밋 (push 하지 않음) — A 의 6절 대체

```bash
git add .gitignore lib/library_schema.sql lib/library_db.py scripts/notion_to_sqlite.py scripts/test_notion_to_sqlite.py \
        CLAUDE.md AGENTS.md docs/tasks/2026-10-11-v4-notion-to-sqlite.md docs/tasks/2026-10-11-v4-notion-to-sqlite-fix1.md
git status --short          # data/ 가 staged 목록에 없어야 한다
git commit -m "v4.0 1단계: 노션 → SQLite 적재 스크립트 (노션 읽기 전용, Vault 대조는 프론트매터 기준)"
git show --stat HEAD        # 정확히 9개
```

`git push` 는 하지 않는다.

## 6. 데몬 재기동

없음.

## 7. 롤백

A 의 8절 + 격리한 노트 되돌리기:

```bash
V=~/"Documents/Obsidian/AI LLM Wiki/AI LLM Wiki"
mv "$V/_trash/<STAMP>/AI 꿀팁/"*4187b1*.md "$V/AI 꿀팁/" && rmdir "$V/_trash/<STAMP>/AI 꿀팁" "$V/_trash/<STAMP>"
```

## 8. 범위 밖

- `sync_obsidian.py`·`build_obsidian_wiki.py` 수정(스키마 문서 예시 문구 포함) — 2단계.
- 노션 쓰기·수정·삭제, 노션 휴지통 확인.
- A 의 9절 전부.

## 9. 보고 형식 (한국어)

1. 2절 해시 4개 일치 여부, 3-1 출력
2. 3-2 출력 전문(격리 위치 `_trash/<STAMP>/` 포함)
3. 3-3 마지막 줄
4. 3-4 `📊 결과` 블록 + `RESULT_JSON` 전문, 파이썬 경로
5. A 의 10절 4 ~ 7 항목
6. 기대와 다른 점 — 없으면 "없음"
