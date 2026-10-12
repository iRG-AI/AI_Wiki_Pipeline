# v4.3 — 노션 잔재 정리 (노션 해지 후)

> 지시 번호는 발행할 때 채팅으로 준다(`[CC-1012-L]`). 보고는 한국어로.
> 선행: `c1e23b4`(원격 main 과 같음). 스케줄러는 내리지 않는다(4-0 의 시간 창만 피한다).
> `.env` 변경 있음 — `NOTION_*` 3줄 삭제(값은 다루지 않는다. 4-5).

## 1. 배경

- v4.0(10-11) 부터 파이프라인은 노션을 부르지 않는다. 노션 모듈은 「Notion 데이터 이관」(별도 프로젝트)이 끝날 때까지 **보관**만 했다.
- 10-12 대표님: 이관을 마치고 **노션을 해지했다.** 보관 파일·키를 지울 차례다.
- 보관 파일 중 실제로 쓰던 기능은 `scripts/notion_to_sqlite.py --verify`(장부 ↔ Vault 대조, 노션 호출 없음) 하나뿐이다. 그런데 이 파일은 맨 위에서 `lib/tips_notion.py` 를 import 한다 — 그래서 대조 기능만 떼어 내야 둘을 지울 수 있다.
- 레포 밖 위생(같은 날 결정): 레포의 옛 `.env.bak.*` 3개에 옛 키 사본(노션 키 포함)이 있고, `~/Documents` 전체가 구글 드라이브 「컴퓨터 백업」으로 올라간다. 드라이브 백업은 유지하고 옛 사본만 지운다.

## 2. 설계 결정 (바꾸지 말 것)

| 항목 | 결정 |
|---|---|
| 대조 스크립트 | 신규 `scripts/verify_library.py` — `notion_to_sqlite.py` 의 `fm_notion_id`·`vault_ids`·`verify` 를 그대로 옮기고 노션 import 를 뺐다. 검사 항목·`RESULT_JSON` 키·통과 조건 동일. 인자 없음(인자를 주면 종료 2). 장부는 `mode=ro`, Vault 는 읽기만, 네트워크 0 |
| 삭제 | `lib/tips_notion.py` · `scripts/notion_to_sqlite.py` · `scripts/test_notion_to_sqlite.py` |
| 테스트 | 신규 `scripts/test_verify_library.py` 16건(옛 테스트의 verify 관련 검사 + 실패 판정 4종 + 장부·Vault 무변경 + 노션 모듈 import 0 + 네트워크 0). 회귀 테스트는 7종 유지 |
| 그대로 | 노트 프론트매터 키 `notion_id`(= 장부 `record_id`). wiki_ingest·검색 인덱스 상태가 이 값에 묶여 있다. `legacy_scripts/` 도 그대로(은퇴 보관, 실행 대상 아님) |
| 앱 코드 | 동작 변경 없음. 지운 파일을 가리키던 주석 3곳만 고침(`sync_obsidian.py`·`build_search_index.py`·`lib/env_util.py`) |
| 문서 | `CLAUDE.md`·`AGENTS.md`·`README.md` — v4.3, 보관 표기·`.env` 예시·점검 명령·회귀 목록·이력. 이름 변경 날짜 표기 `2026-10-13` → 실제 실행일 `2026-10-12`(지시서·패치 **파일 이름**은 그대로). `docs/cowork-project-instructions.md` 2줄 |
| `.env` | `NOTION_TOKEN`·`NOTION_DB_ID`·`NOTION_TIPS_DB_ID` 3줄만 지운다(다른 줄·주석·순서 그대로, 같은 inode 에 덮어쓰기). 바꾸기 전 사본은 `~/rename_backup_20261013/env.pre_v43`(레포·Documents 밖, 10-19 무렵 폴더째 정리) |
| `.env.bak.*` | 레포의 `.env.bak.20260909`·`.env.bak.20261003`·`.env.bak.20261012_095401` 삭제(gitignore 대상이라 커밋과 무관) |

## 3. 파일 — 패치 1개

`docs/tasks/patches/2026-10-12-notion-cleanup.patch` (기준 = `c1e23b4`, 12개 파일, +337 −1,092)

```
sha256  53d2370fee568b53d4148ed33e7742aae07771cf18e0c446c4849fe3a8492817
```

| 파일 | 변경 |
|---|---|
| `scripts/verify_library.py` | 신규 125줄 |
| `scripts/test_verify_library.py` | 신규 164줄, 16건 |
| `lib/tips_notion.py` · `scripts/notion_to_sqlite.py` · `scripts/test_notion_to_sqlite.py` | 삭제 |
| `sync_obsidian.py` · `build_search_index.py` · `lib/env_util.py` | 주석 1줄씩 |
| `CLAUDE.md` · `AGENTS.md` | 머리 버전 v4.3 + 안내 1줄, 회귀 목록, 대조 명령, 파일 표 2행, 외부 서비스의 노션 줄, 장부 절 2줄, 이력 1행, 이름 변경 날짜 2곳. AGENTS.md = 머리글 5줄 + CLAUDE.md 4행부터 |
| `README.md` | 머리 버전·안내, 프로젝트 구조 2줄, `.env` 예시의 노션 블록, 요약 행 + 상세 1절, 이름 변경 날짜 2곳 |
| `docs/cowork-project-instructions.md` | 2줄(v4.3 · 날짜) |

### Cowork 사전 검증 (2026-10-12 17:00, 맥 네이티브 · 레포 무변경)

- 임시 폴더에 `git archive c1e23b4` + 위 변경 → 회귀 테스트 7종: `test_scheduler_guards.js` 29/29 · `test_verify_library.py` 16/16 · `test_kakao_ingest.py` 18/18 · `test_sync_obsidian.py` 23/23 · `test_sheet_mirror.py` 45/45 · `test_build_wiki_index.py` 10/10 · `test_backup_library.py` 50/50. `py_compile`·import(`kakao_ingest`·`sync_obsidian`·`sheet_mirror`·`backup_library`·`build_search_index`) 통과.
- 실데이터(장부 사본 + 실제 Vault 읽기): 옛 `notion_to_sqlite.py --verify` 와 새 `verify_library.py` 의 `RESULT_JSON` 이 **글자까지 같다** — videos 2,999 · videos_dup 203 · tips 148 · vault_missing 0 · tips_missing 0 · vault_ignored 0.
- 레포 작업 트리에서 `git apply --check` 통과. `{ head -5 AGENTS.md; tail -n +4 CLAUDE.md; } | cmp - AGENTS.md` 통과.
- 남은 참조: `.py`·`.js`·`.sh` 중 노션 모듈을 import 하는 곳 0(`legacy_scripts/`·`docs/tasks/` 제외). `scripts/test_kakao_ingest.py` 의 "tips_notion 을 import 하지 않음" 검사는 그대로 유효.

## 4. 실행 — `[CC-1012-L]`

### 4-0. 시간

스케줄러가 00·06·12·18시에 돈다. **매시 50분 ~ 다음 시 20분(예: 17:50~18:20)에는 4-2 이후를 시작하지 않는다.**

### 4-1. 시작 상태 (읽기만)

```bash
cd <REPO_ROOT>
git --no-optional-locks rev-parse --short HEAD          # c1e23b4
git --no-optional-locks status --porcelain
#   기대: 아래 두 줄만 (이 지시서와 패치)
#   ?? docs/tasks/2026-10-12-notion-cleanup.md
#   ?? docs/tasks/patches/2026-10-12-notion-cleanup.patch
shasum -a 256 docs/tasks/patches/2026-10-12-notion-cleanup.patch   # 3절 값과 같아야 한다
grep -c -E '^NOTION_(TOKEN|DB_ID|TIPS_DB_ID)=' .env               # 3
ls .env.bak.20260909 .env.bak.20261003 .env.bak.20261012_095401    # 3개 있음
[ -e ~/rename_backup_20261013/env.pre_v43 ] && echo EXISTS || echo ABSENT   # ABSENT
```

어긋나면 **멈추고 보고**한다.

### 4-2. 패치 적용

```bash
git apply --check docs/tasks/patches/2026-10-12-notion-cleanup.patch && git apply docs/tasks/patches/2026-10-12-notion-cleanup.patch
git --no-optional-locks status --porcelain
#   기대: M AGENTS.md · M CLAUDE.md · M README.md · M build_search_index.py · M docs/cowork-project-instructions.md
#        M lib/env_util.py · M sync_obsidian.py · D lib/tips_notion.py · D scripts/notion_to_sqlite.py · D scripts/test_notion_to_sqlite.py
#        ?? scripts/test_verify_library.py · ?? scripts/verify_library.py · ?? 지시서 · ?? 패치
{ head -5 AGENTS.md; tail -n +4 CLAUDE.md; } | cmp - AGENTS.md && echo AGENTS_OK
git --no-optional-locks grep -n -E "import (tips_notion|notion_to_sqlite)|from (tips_notion|notion_to_sqlite)" -- ':!legacy_scripts' ':!docs/tasks' | wc -l   # 0
```

### 4-3. 회귀 테스트 7종 (네트워크 0회, 실제 장부·.env·Vault 무관)

```bash
/opt/homebrew/bin/node scripts/test_scheduler_guards.js      # 29/29 PASS
/opt/homebrew/bin/python3 scripts/test_verify_library.py     # 16/16
/opt/homebrew/bin/python3 scripts/test_kakao_ingest.py       # 18/18
/opt/homebrew/bin/python3 scripts/test_sync_obsidian.py      # 23/23
/opt/homebrew/bin/python3 scripts/test_sheet_mirror.py       # 45/45
/opt/homebrew/bin/python3 scripts/test_build_wiki_index.py   # 10/10
/opt/homebrew/bin/python3 scripts/test_backup_library.py     # 50/50
```

하나라도 FAIL 이면 멈추고 보고(7절 롤백).

### 4-4. 실데이터 대조 (읽기만, 네트워크 0)

```bash
/opt/homebrew/bin/python3 scripts/verify_library.py > /tmp/v43_verify.txt; echo "exit $?"; tail -3 /tmp/v43_verify.txt
#   기대: RESULT_JSON 의 ok true · vault_missing 0 · tips_missing 0 · videos ≥ 2,999 · tips ≥ 148, "✅ 검증 통과", exit 0
```

### 4-5. `.env` 노션 키 3줄 삭제 + 옛 사본 삭제

값은 화면에 찍지 않는다 — 개수만 본다.

```bash
cp -p .env ~/rename_backup_20261013/env.pre_v43
grep -v -E '^NOTION_(TOKEN|DB_ID|TIPS_DB_ID)=' ~/rename_backup_20261013/env.pre_v43 > .env    # 같은 파일(inode)에 덮어쓰기
grep -c '^NOTION_' .env                                                                         # 0
diff ~/rename_backup_20261013/env.pre_v43 .env | grep -c '^<'                                   # 3
diff ~/rename_backup_20261013/env.pre_v43 .env | grep '^<' | grep -vc '^< NOTION_'              # 0
diff ~/rename_backup_20261013/env.pre_v43 .env | grep -c '^>'                                   # 0
ls -l .env | awk '{print $1}'                                                                   # -rw-r--r--
/opt/homebrew/bin/python3 -c "
import sys; sys.path.insert(0,'lib'); from env_util import load_env; e=load_env()
need=['GEMINI_API_KEY','SHEET_MIRROR_URL','SHEET_MIRROR_TOKEN','LIBRARY_BACKUP_DIR','KAKAO_EXPORT_DIR','TELEGRAM_BOT_TOKEN','YOUTUBE_OAUTH_REFRESH_TOKEN']
print('keys_ok', all(e.get(k) for k in need), 'notion', any(k.startswith('NOTION_') for k in e))"   # keys_ok True notion False
/opt/homebrew/bin/python3 sheet_mirror.py --check | tail -1          # error "" (시트를 읽었다 = .env 의 SHEET_MIRROR_* 정상)
/opt/homebrew/bin/python3 sheet_mirror.py --dry-run | tail -1        # error "" · tips_sent·videos_sent = 바로 위 --check 의 장부 − 시트 차이
/opt/homebrew/bin/python3 backup_library.py --status | tail -4       # 로컬·드라이브 최근 0일 전
rm .env.bak.20260909 .env.bak.20261003 .env.bak.20261012_095401
for f in .env.bak.20260909 .env.bak.20261003 .env.bak.20261012_095401; do [ -e "$f" ] && echo "LEFT $f"; done; echo BAK_CHECKED   # BAK_CHECKED 한 줄만
```

`keys_ok` 가 False 이거나, `--check`·`--dry-run` 에 error 가 있거나, 장부 − 시트 차이가 `--dry-run` 의 보낼 건수와 다르면 멈추고 `.env` 를 되돌린다(7절).

> 10-12 17:09 1차 실행은 이 자리의 옛 기준 "`--check` match true" 에서 멈췄다(`.env` 원복, 커밋 전). 16:37 수동 반영한 꿀팁 13건이 아직 시트로 가지 않아(다음 정시 실행이 보냄) 장부 148 · 시트 135 였고, 원래 `.env` 로도 같았다 — 기준이 틀렸다. 시트 미러는 실행 사이에 늘 뒤처질 수 있으므로 `.env` 확인은 "시트를 읽을 수 있는가 + 차이가 보낼 건수로 설명되는가" 로 본다.

## 5. 커밋 (push 하지 않음)

```bash
git add -A AGENTS.md CLAUDE.md README.md build_search_index.py docs/cowork-project-instructions.md lib/env_util.py sync_obsidian.py \
           lib/tips_notion.py scripts/notion_to_sqlite.py scripts/test_notion_to_sqlite.py \
           scripts/verify_library.py scripts/test_verify_library.py \
           docs/tasks/2026-10-12-notion-cleanup.md docs/tasks/patches/2026-10-12-notion-cleanup.patch
git --no-optional-locks status --porcelain       # 기대: 빈 출력
git commit -m "v4.3 노션 잔재 정리 — 노션 모듈·테스트 삭제, 장부 ↔ Vault 대조를 scripts/verify_library.py 로 분리, 이름 변경 날짜 10-12 정정"
git --no-optional-locks log --oneline -2
git --no-optional-locks show --stat HEAD | tail -16   # 14개 파일
```

**push 는 하지 않는다.** Cowork 가 커밋 diff 를 확인한 뒤 따로 지시한다.

## 6. 데몬

- 재기동 불필요. 지운 파일은 어느 데몬도 import 하지 않는다(`server.js`·`wiki_lan_server.js`·`wiki_mcp.js`·`scheduler.js`·`wiki_ingest.py` 무관). 런타임 파일 변경은 주석 3줄뿐.
- `.env` 는 스케줄러가 실행마다 새로 읽는다. 상주 데몬은 `NOTION_*` 를 쓰지 않는다.

## 7. 롤백

- `.env`: `cat ~/rename_backup_20261013/env.pre_v43 > .env` (같은 inode 로 되돌림).
- 커밋 전: `git apply -R docs/tasks/patches/2026-10-12-notion-cleanup.patch`.
- 커밋 후: `git revert HEAD`(push 전이면 `git reset --hard c1e23b4` 도 가능 — 지시서·패치 파일은 다시 untracked 로 둔다).
- 지운 `.env.bak.*` 는 되돌릴 필요가 없다(현행 `.env` 가 원본, 노션 키는 해지로 무효).

## 8. 범위 밖

- `git push`.
- 스킬 `kakao-tips-update` 의 `notion_to_sqlite.py` 언급 1줄, claude.ai 프로젝트 지침의 "보관" 표기 — Cowork·대표님이 따로.
- 데스크톱 앱·Claude 의 노션 커넥터 정리, 「Notion_Archive」 프로젝트.
- `~/rename_backup_20261013/` 정리(10-19 무렵, `env.pre_v43` 포함).

## 9. 보고 형식 (한국어)

```
[CC-1012-L] 결과
- 4-1 시작 상태: HEAD / porcelain / 패치 sha256 일치 여부 / NOTION 줄 3 / .env.bak 3개 / env.pre_v43 없음
- 4-2 적용: status 요약 / AGENTS_OK / 노션 import 0
- 4-3 테스트: 7종 각 n/n
- 4-4 실데이터: exit 코드, RESULT_JSON 원문, 마지막 줄
- 4-5 .env: NOTION 0 / diff < 3 · 그 외 0 · > 0 / 권한 / keys_ok·notion / --check / --status / BAK_CHECKED
- 5 커밋: 해시, show --stat
- 특이사항(멈춘 단계·기대와 다른 출력 원문. .env 값은 절대 출력하지 않는다)
```
