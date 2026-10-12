# v4.4 — 꿀팁 제목 보완 도구 + 첫 적용 5건

> 지시 번호는 발행할 때 채팅으로 준다(`[CC-1012-O]`). 보고는 한국어로.
> 선행: `46667ac`(원격 main 과 같음). 스케줄러는 내리지 않는다(4-0 의 시간 창만 피한다).
> **장부·Vault 를 고친다**(5행 · 노트 5개 · 링크 약 24곳). `.env` 변경 없음, 데몬 재기동 없음.

## 1. 배경

- `kakao_ingest.py` 는 링크를 열지 않고 URL 로만 제목을 추정한다(`lib/kakao_parse.py:guess_meta`). 유튜브 shorts·노션 공개 페이지는 「유튜브 영상 (제목 미확인)」·「노션 자료 (제목 미확인)」, 그 밖은 URL 마지막 조각(`courses` 등)이 제목이 된다. 「원문 확인 필요」 메모가 붙은 꿀팁이 3월부터 46건 쌓였다.
- **장부만 고치면 안 된다.** `sync_obsidian.py:sync_tips` 는 꿀팁 노트를 새로 만들기만 하고 기존 노트는 다시 쓰지 않는다. 시트는 새 제목이 되지만 Obsidian 노트·파일명은 옛 제목으로 남고, `_wiki`·`_MOC`·전체 인덱스의 `[[옛 파일명]]` 링크도 그대로다.
- 대표님 결정(10-12): 재사용 스크립트로 만들고 이번 5건부터 적용. 노트 파일명도 새 제목으로 바꾸고 링크를 고친다. 나머지 41건은 Cowork 가 원문 제목을 조사해 같은 스크립트로 다음 배치.

## 2. 설계 결정 (바꾸지 말 것)

| 항목 | 결정 |
|---|---|
| 입력 | CSV `record_id,old_title,new_title`(UTF-8, 머리글). 기본 dry-run. `--apply` 로만 쓴다 |
| 장부 | 한 트랜잭션 `UPDATE tips SET title, memo, updated_at WHERE record_id = ? AND title = <옛 제목>` — 행 수 1이 아니면 전체 롤백. `updated_at` 은 kakao_ingest 와 같은 형식(시트 미러 워터마크). memo 는 카톡 자동 메모 2종(「원문 확인 필요」·「슬러그에 한글 제목 없음 — 원문 확인 필요」)일 때만 비운다 |
| 노트 | 다시 생성하지 않고 **제자리 수정** — 프론트매터 `title`·`memo` 줄, 첫 H1, `- 📝 메모:` 줄. 편집 지점이 1곳씩이 아니면(손으로 고친 노트) 전체 중단. 파일명 `<저장일>_<새 제목>.md`(`sync_tips` 와 같은 `safe_filename`, 충돌 시 record_id 끝 6자리). `notion_id` 는 그대로 → wiki_ingest 상태·검색 인덱스 id 유지 |
| 링크 | Vault 의 `[[옛]]`·`[[옛\|별칭]]`·`[[AI 꿀팁/옛#앵커]]` → 새 파일명. 별칭이 옛 제목이면 새 제목으로, 사용자 별칭은 그대로. NFC·NFD 둘 다. `_trash/`·숨김 폴더 제외 |
| 금지 | 새 제목에 `\|`·`[[`·`]]`(Obsidian 별칭 구분자와 겹침 — 스크립트가 거부). 그래서 `courses` 의 원문 「강의 \| 메이크패밀리 라운지」는 「메이크패밀리 라운지 — 강의 목록」으로 적었다 |
| 백업 | 쓰기 전 `data/retitle_backup/<YYYYmmdd-HHMMSS>/` — 장부 사본(SQLite 온라인 백업 API) · 바뀔 Vault 파일 원본 · `manifest.json`. `data/` 아래라 gitignore |
| 뒤처리 | `--apply` 뒤 `build_obsidian_wiki.py` → `build_search_index.py`(sync_obsidian 이 변경 뒤 부르는 것과 같은 두 단계. 검색 인덱스는 바뀐 노트 5개만 Gemini 임베딩). 시트는 다음 정시 실행이 보낸다(수동 미러 안 함) |
| 앱 코드 | 무변경. 데몬 재기동 불필요(검색 서버들은 인덱스 mtime 이 바뀌면 다시 읽는다) |

## 3. 파일 — 패치 1개

`docs/tasks/patches/2026-10-12-retitle-tips.patch` (기준 = `46667ac`, 6개 파일, +691 −6)

```
sha256  0ab806dd770e0c4af221755f00dfed72e2c3bd94def82ed6cb2602e3c14ad739
```

| 파일 | 변경 |
|---|---|
| `scripts/retitle_tips.py` | 신규 381줄 |
| `scripts/test_retitle_tips.py` | 신규 257줄, 49건 |
| `docs/tasks/2026-10-12-retitle-tips.csv` | 신규 — 첫 적용 5건 |
| `CLAUDE.md` · `AGENTS.md` | 머리 버전 v4.4 + 안내 1줄, 회귀 목록 8종, 실행 명령, 파일 표 1행, 카톡 절 1줄, 이력 1행. AGENTS.md = 머리글 5줄 + CLAUDE.md 4행부터 |
| `README.md` | 머리 버전·안내, 프로젝트 구조 1줄·8종, 카톡 실행 예 3줄, 요약 행 + 상세 1절 |

첫 적용 5건(원문 확인: 유튜브 oEmbed · 노션 공개 API · 페이지 제목)

| 저장일 | 옛 제목 | 새 제목 |
|---|---|---|
| 10-11 | 유튜브 영상 (제목 미확인) | 클로드 코드 모드 안전한 TOP 5 — 나온 지 일주일 순위 |
| 10-12 | 노션 자료 (제목 미확인) | [시크아] 디자인 리소스 리스트 |
| 10-10 | courses | 메이크패밀리 라운지 — 강의 목록 |
| 10-09 | linkedin skills claude code setup | 링크드인 스킬 12개로 클로드를 그로스 팀으로 만드는 법 |
| 10-11 | munder difflin ai office setup | AI 오피스를 통째로 고용하는 법: 먼더 디플린 |

### Cowork 사전 검증 (2026-10-12 17:40, 맥 네이티브 · 레포 무변경)

- 임시 폴더에 `git archive 46667ac` + 변경 → 회귀 테스트 8종: `test_scheduler_guards.js` 29/29 · `test_retitle_tips.py` 49/49 · `test_verify_library.py` 16/16 · `test_kakao_ingest.py` 18/18 · `test_sync_obsidian.py` 23/23 · `test_sheet_mirror.py` 45/45 · `test_build_wiki_index.py` 10/10 · `test_backup_library.py` 50/50 (Python 3.14.8).
- 새 archive 에 패치를 다시 적용 → 작업 사본과 `diff -r` 동일. 레포 작업 트리 `git apply --check` 통과.
- 실데이터 dry-run(실제 장부 읽기 전용 + 실제 Vault 읽기): `rows 5 · notes 5 · renamed 5 · memo_cleared 2 · link_files 10 · links 24`, 백업 폴더 안 생김.
- 장부 사본 + Vault 사본에 `--apply --no-rebuild`: 바뀐 행 정확히 5(videos·나머지 tips 무변경, `created_at`·`url` 그대로), `integrity_check` ok, 꿀팁 노트 148 ↔ 장부 148(어긋남 0), `_trash` 밖 옛 링크 0, 노트의 관련 링크 블록 보존. 같은 CSV 재실행 → 옛 제목 불일치로 종료 2(무변경).

## 4. 실행 — `[CC-1012-O]`

### 4-0. 시간

스케줄러가 00·06·12·18시, wiki-ingest 가 17:30 에 돈다. **매시 50분 ~ 다음 시 20분, 17:25~17:45 에는 4-4 이후를 시작하지 않는다.**

### 4-1. 시작 상태 (읽기만)

```bash
cd <REPO_ROOT>
git --no-optional-locks rev-parse --short HEAD          # 46667ac
git --no-optional-locks status --porcelain
#   기대: 아래 두 줄만 (이 지시서와 패치)
#   ?? docs/tasks/2026-10-12-retitle-tips.md
#   ?? docs/tasks/patches/2026-10-12-retitle-tips.patch
shasum -a 256 docs/tasks/patches/2026-10-12-retitle-tips.patch      # 3절 값과 같아야 한다
grep -o '"outcome": "[a-z]*"' .run_state.json                       # "ok" (running 이면 멈춤 — 스케줄러 실행 중)
[ -e data/retitle_backup ] && echo EXISTS || echo ABSENT             # ABSENT
```

어긋나면 **멈추고 보고**한다.

### 4-2. 패치 적용

```bash
git apply --check docs/tasks/patches/2026-10-12-retitle-tips.patch && git apply docs/tasks/patches/2026-10-12-retitle-tips.patch
git --no-optional-locks status --porcelain
#   기대: M AGENTS.md · M CLAUDE.md · M README.md
#        ?? docs/tasks/2026-10-12-retitle-tips.csv · ?? scripts/retitle_tips.py · ?? scripts/test_retitle_tips.py · ?? 지시서 · ?? 패치
{ head -5 AGENTS.md; tail -n +4 CLAUDE.md; } | cmp - AGENTS.md && echo AGENTS_OK
git check-ignore -q data/retitle_backup/x/library.db && echo BACKUP_IGNORED
```

### 4-3. 회귀 테스트 8종 (네트워크 0회, 실제 장부·.env·Vault 무관)

```bash
/opt/homebrew/bin/node scripts/test_scheduler_guards.js      # 29/29 PASS
/opt/homebrew/bin/python3 scripts/test_retitle_tips.py       # 49/49
/opt/homebrew/bin/python3 scripts/test_verify_library.py     # 16/16
/opt/homebrew/bin/python3 scripts/test_kakao_ingest.py       # 18/18
/opt/homebrew/bin/python3 scripts/test_sync_obsidian.py      # 23/23
/opt/homebrew/bin/python3 scripts/test_sheet_mirror.py       # 45/45
/opt/homebrew/bin/python3 scripts/test_build_wiki_index.py   # 10/10
/opt/homebrew/bin/python3 scripts/test_backup_library.py     # 50/50
```

하나라도 FAIL 이면 멈추고 보고(7절 롤백).

### 4-4. 실데이터 dry-run (무변경)

```bash
/opt/homebrew/bin/python3 scripts/retitle_tips.py docs/tasks/2026-10-12-retitle-tips.csv > /tmp/v44_dry.txt; echo "exit $?"; grep -c ' → ' /tmp/v44_dry.txt; tail -1 /tmp/v44_dry.txt
[ -e data/retitle_backup ] && echo EXISTS || echo ABSENT             # ABSENT
```

기대: exit 0, `RESULT_JSON` 의 `ok true · dry_run true · rows 5 · notes 5 · renamed 5 · memo_cleared 2 · links ≥ 1`.
`link_files`·`links` 는 사전 검증 때 10·24 였다. 그 사이 정시 실행이 MOC·Wiki 페이지를 다시 만들었으면 달라질 수 있다 — **숫자는 보고만 하고 멈추지 않는다.** `ok false`(검증 실패)면 멈추고 출력 전체를 보고.

### 4-5. 반영

```bash
/opt/homebrew/bin/python3 scripts/retitle_tips.py docs/tasks/2026-10-12-retitle-tips.csv --apply > /tmp/v44_apply.txt 2>&1; echo "exit $?"; tail -6 /tmp/v44_apply.txt
```

기대: exit 0, `RESULT_JSON` 의 `ok true · rows 5 · notes 5 · renamed 5 · memo_cleared 2`, `rebuild` 의 `build_obsidian_wiki.py 0 · build_search_index.py 0`, `backup` 경로. `links`·`link_files` 는 4-4 와 같아야 한다.
exit 1 이면 그 자리에서 멈추고 `/tmp/v44_apply.txt` 전체를 보고한다(롤백은 Cowork 판단 후 — 7절).

### 4-6. 확인 (읽기만)

```bash
sqlite3 "file:data/library.db?mode=ro" "select substr(record_id,1,8), title, memo, updated_at from tips where record_id in ('2d591722-e31a-4ec0-abde-78491f4eecc7','1f8e69b6-618b-49ba-a5b3-c83f544c049c','75de39d8-9e68-4950-a509-9ba3d014b822','bd3dac6b-cf95-47cc-a2af-741853de7b76','3d3327d3-56b5-4f52-a474-a9094869c89e');"
#   기대: 5행, 새 제목, memo 빈칸 5, updated_at = 4-5 RESULT_JSON 의 updated_at
sqlite3 "file:data/library.db?mode=ro" "select count(*) from tips where updated_at = (select max(updated_at) from tips);"   # 5
/opt/homebrew/bin/python3 scripts/verify_library.py | grep RESULT_JSON   # ok true · tips 148 · vault_missing 0 · tips_missing 0
ls ~/Documents/Obsidian/"AI LLM Wiki"/"AI LLM Wiki"/"AI 꿀팁" | grep -c '\.md$'    # 4-1 시점과 같은 개수(148, 늘거나 줄지 않음)
/opt/homebrew/bin/python3 - <<'EOF'
import os, unicodedata as u
V = os.path.expanduser('~/Documents/Obsidian/AI LLM Wiki/AI LLM Wiki')
olds = ['20261011_유튜브 영상 (제목 미확인)', '20261012_노션 자료 (제목 미확인)', '20261010_courses',
        '20261009_linkedin skills claude code setup', '20261011_munder difflin ai office setup']
left = 0
for root, ds, fs in os.walk(V):
    ds[:] = [d for d in ds if not d.startswith('.') and d != '_trash']
    for f in fs:
        if f.endswith('.md'):
            t = u.normalize('NFC', open(os.path.join(root, f), encoding='utf-8', errors='ignore').read())
            left += sum(t.count('[[' + s + e) for s in olds for e in (']]', '|', '#'))
print('OLD_LINKS', left)                                              # OLD_LINKS 0
EOF
grep -c '클로드 코드 모드 안전한 TOP 5' wiki_index.json                # ≥ 1 (검색 인덱스에 새 제목)
/opt/homebrew/bin/python3 sheet_mirror.py --dry-run | tail -1        # error "" · tips_sent ≥ 5 (다음 정시 실행이 보낼 몫)
```

## 5. 커밋 (push 하지 않음)

```bash
git add AGENTS.md CLAUDE.md README.md scripts/retitle_tips.py scripts/test_retitle_tips.py docs/tasks/2026-10-12-retitle-tips.csv \
        docs/tasks/2026-10-12-retitle-tips.md docs/tasks/patches/2026-10-12-retitle-tips.patch
git commit -m "v4.4 꿀팁 제목 보완 도구 — scripts/retitle_tips.py(장부·노트 파일명·링크 일괄, dry-run 기본·백업) + 첫 적용 5건"
git --no-optional-locks status --porcelain       # 커밋 뒤 기대: 빈 출력
git --no-optional-locks log --oneline -2
git --no-optional-locks show --stat HEAD | tail -10   # 8개 파일
```

**push 는 하지 않는다.** Cowork 가 커밋 diff 와 장부·Vault 를 확인한 뒤 따로 지시한다.

## 6. 데몬

- 재기동 불필요. 앱 코드 무변경. `server.js`·`wiki_lan_server.js`·`wiki_mcp.js` 는 `wiki_index.json` mtime 이 바뀌면 다시 읽는다.

## 7. 롤백

- 커밋 전, 4-5 이전: `git apply -R docs/tasks/patches/2026-10-12-retitle-tips.patch`.
- 4-5 이후(장부·Vault 되돌리기 — 정시 실행 창 밖에서):

```bash
B=<4-5 RESULT_JSON 의 backup 경로>
/opt/homebrew/bin/python3 - "$B" <<'EOF'
import json, os, shutil, sys
b = sys.argv[1]; m = json.load(open(os.path.join(b, 'manifest.json'), encoding='utf-8')); v = m['vault']
for r in m['renamed']:                       # 새 이름 파일 제거
    p = os.path.join(v, r['to'])
    if os.path.exists(p): os.remove(p)
for rel in m['edited']:                      # 원본(옛 이름) 복원
    shutil.copy2(os.path.join(b, 'vault', rel), os.path.join(v, rel))
shutil.copy2(os.path.join(b, 'library.db'), m['db'])
print('restored', len(m['edited']), 'files + db')
EOF
/opt/homebrew/bin/python3 build_obsidian_wiki.py && /opt/homebrew/bin/python3 build_search_index.py
/opt/homebrew/bin/python3 scripts/verify_library.py | grep RESULT_JSON
```

  시트가 이미 새 제목을 받았다면(정시 실행 뒤) `sheet_mirror.py --full`.
- 커밋 후: `git revert HEAD`(push 전이면 `git reset --hard 46667ac` 도 가능 — 지시서·패치는 다시 untracked 로 둔다). 장부·Vault 는 위 절차로 따로.

## 8. 범위 밖

- `git push`.
- 나머지 「원문 확인 필요」 41건(Cowork 가 제목 조사 → 다음 CSV).
- `kakao_ingest` 가 인제스트 때 제목을 직접 가져오게 하는 개선(oEmbed·노션 공개 API·`og:title`).
- `data/retitle_backup/` 정리(10-19 이후 Cowork 제안).

## 9. 보고 형식 (한국어)

```
[CC-1012-O] 결과
- 4-1 시작 상태: HEAD / porcelain / 패치 sha256 일치 여부 / outcome / retitle_backup 없음
- 4-2 적용: status 요약 / AGENTS_OK / BACKUP_IGNORED
- 4-3 테스트: 8종 각 n/n
- 4-4 dry-run: exit, ' → ' 줄 수, RESULT_JSON 원문, 백업 폴더 없음
- 4-5 반영: exit, RESULT_JSON 원문
- 4-6 확인: 5행 출력 원문 / 최신 updated_at 행 수 / verify_library RESULT_JSON / 꿀팁 노트 수 / OLD_LINKS / 인덱스 grep / sheet_mirror --dry-run 마지막 줄
- 5 커밋: 해시, show --stat
- 특이사항(멈춘 단계·기대와 다른 출력 원문)
```
