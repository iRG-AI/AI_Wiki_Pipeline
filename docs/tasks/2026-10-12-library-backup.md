# v4.1 — 장부 하루 1회 자동 백업 (로컬 + 구글 드라이브)

> 지시 번호는 발행할 때 채팅으로 준다(`[CC-1012-E]`). 보고는 한국어로.
> 선행: v4.0 `9e272be`(원격 main 과 같음). 스케줄러는 내리지 않는다(4-0 의 시간 창만 피한다).
> **`.env` 에 넣을 실제 경로는 이 문서에 없다** — 지시문 본문(채팅)으로 받는다. 이 문서에는 `<LIBRARY_BACKUP_DIR 값>` 으로 적는다.

## 1. 배경

- v4.0 으로 원본이 맥의 장부 `data/library.db`(약 16MB) 한 파일이 됐다.
- 10-12 Cowork 점검: 타임머신 백업 디스크가 마운트되지 않아(`Failed to mount destination`) 이 맥의 백업 기록이 없다. iCloud Drive 동기화도 꺼져 있다.
- 그래서 장부 사본은 같은 폴더의 `data/library.db.bak.20261011_231534` 하나뿐이다(같은 디스크).
- 구글 시트 미러는 영상·꿀팁 본문은 담지만 `meta`·`videos_dup` 이 없어 복원용이 아니다.
- 구글 드라이브 데스크톱 앱이 시트와 같은 계정으로 이미 동기화 중이다. 장부를 gzip 하면 약 3.6MB.

## 2. 설계 결정 (대표님·Cowork 확정 — 바꾸지 말 것)

| 항목 | 결정 |
|---|---|
| 방식 | 대표님 결정(10-12): **구글 드라이브 폴더에 매일 스냅샷** + 로컬 `data/backups/`. 새 스크립트 `backup_library.py`(레포 루트, Python). 드라이브 API·OAuth 는 쓰지 않는다 — 데스크톱 앱이 동기화하는 로컬 폴더에 파일만 쓴다. |
| 보관 | 대표님 결정: **최신 7개(일별) + 주별 4개 = 최대 11개**. 주별 = 일별이 대표하지 않는 옛 ISO 주마다 가장 최근 1개(보통 일요일). 정리는 **그 실행에 새로 쓴 폴더에서만**, 이름이 정확히 `library-YYYYMMDD.db.gz` 인 파일만. |
| 실행 시점 | 대표님 결정: **스케줄러 안에서 하루 1회**. `scheduler.js:runLibraryBackup()` 을 시트 미러 뒤·Obsidian 동기화 앞에 부른다. 하루 1회 판단 = 오늘(KST) 이름의 파일이 그 폴더에 있느냐(**상태 파일·meta 기록 없음**). 00시 실행이 만들고 06·12·18시는 `skipped`. 드라이브만 빠졌으면 다음 실행이 드라이브에만 다시 쓴다. launchd 데몬은 늘리지 않는다. |
| 만드는 법 | SQLite **온라인 백업 API**(장부는 `mode=ro` 로만 연다 — 장부에 아무것도 쓰지 않는다) → 사본 `integrity_check = ok` · `user_version = 1` · `videos ≥ 1` → gzip → 압축을 다시 풀어 sha256 대조 → 각 폴더에 `.tmp` 로 쓰고 `os.replace`. `cp` 로 복사하지 않는다(journal_mode=DELETE). |
| 검사 실패 | 사본 검사에 걸리면 **아무것도 만들지 않고 기존 백업도 지우지 않는다**(exit 1, `snapshot:<사유>`). |
| 드라이브 경로 | `.env` `LIBRARY_BACKUP_DIR`. 없으면 로컬에만(`drive: not_configured`, 오류 아님). **부모 폴더가 없으면 만들지 않고** `drive: unavailable`, exit 1 — 앱이 꺼졌을 때 로컬 디스크에 가짜 드라이브 경로가 생기지 않게. 마지막 폴더 하나만 만든다. |
| 스케줄러 훅 | `runLibraryBackup` 은 **reject 하지 않고 네트워크를 쓰지 않는다**(시트 미러 훅과 같은 원칙). 실패하면 main 이 `⚠️ [장부 백업 실패]` 텔레그램을 **따로** 보낸다(저장 0건 실행에도). |
| 문서 | README v4.1(요약 행 + 상세 1절 + 기능·사이클 표·구조·환경변수·「5. 장부 백업」 절 신설, 복원 절차 포함). CLAUDE.md: 머리 버전, 명령, 테스트 7종, 파이프라인, 파일 표, 「장부 백업 (v4.1)」 절 신설, v4.0 절의 복원 문구, 외부 서비스, 이력. AGENTS.md = 머리글 5줄 + CLAUDE.md 4행부터(규칙 그대로). |

## 3. 파일 — 패치 1개

`docs/tasks/patches/2026-10-12-library-backup.patch` (기준 = `9e272be`)

```
sha256  4244324c1cbf4cacc0d552f7413c00b0c50bc3e36a43e2debf8d6e562f1fc0bc
```

| 파일 | 변경 |
|---|---|
| `backup_library.py` | 신규 (2절). `--dry-run`·`--status`·`--force`. 마지막 줄 `RESULT_JSON:` |
| `scripts/test_backup_library.py` | 신규 **50**건. 임시 장부·임시 폴더(가짜 드라이브 경로 포함), 실제 장부·`.env`·드라이브 무관 |
| `scheduler.js` | `runLibraryBackup()` + 호출(시트 미러 뒤) + 실패 텔레그램 + export(테스트용) |
| `scripts/test_scheduler_guards.js` | +3건(훅이 reject 하지 않음·skipped 는 오류 아님) → **22** |
| `README.md` · `CLAUDE.md` · `AGENTS.md` | 2절 "문서" |

### Cowork 사전 검증 (2026-10-12 01:28, 맥 네이티브 · 레포 무변경)

- `git apply --check` 통과(레포 작업 트리). `git archive 9e272be` 를 임시 폴더에 풀고 패치 적용.
- 회귀 테스트 7종(node v26.10.0 · Homebrew Python 3.14.8): `test_scheduler_guards.js` 22/22 · `test_backup_library.py` 50/50 · `test_notion_to_sqlite.py` 37/37 · `test_kakao_ingest.py` 18/18 · `test_sync_obsidian.py` 23/23 · `test_sheet_mirror.py` 45/45 · `test_build_wiki_index.py` 10/10.
- 실제 장부(읽기 전용) → 임시 로컬·임시 "드라이브" 폴더: `library-20261012.db.gz` 3,799,216바이트, 0.56초, 영상 2,988 · videos_dup 203 · 꿀팁 135 · meta 10. 두 번째 실행 `skipped already_done`. 압축 해제본 `integrity_check ok`, 행 수 동일. **장부 sha256·mtime 실행 전후 같음.**
- 실제 드라이브 부모 폴더: NFC·NFD 이름 모두 열림, 쓰기 권한 있음. 대상 하위 폴더는 아직 없음(첫 실행이 만든다).

## 4. 실행 — `[CC-1012-E]`

### 4-0. 시간

스케줄러가 00·06·12·18시에 돈다. **매시 50분 ~ 다음 시 20분(예: 05:50~06:20)에는 4-2 이후를 시작하지 않는다.**

### 4-1. 시작 상태 (읽기만)

```bash
cd <REPO_ROOT>
git --no-optional-locks rev-parse --short HEAD          # 9e272be
git --no-optional-locks status --porcelain
#   기대: 아래 두 줄만 (이 지시서와 패치)
#   ?? docs/tasks/2026-10-12-library-backup.md
#   ?? docs/tasks/patches/2026-10-12-library-backup.patch
shasum -a 256 docs/tasks/patches/2026-10-12-library-backup.patch   # 3절 값과 같아야 한다
grep -c '^LIBRARY_BACKUP_DIR=' .env                       # 0
ls data/backups 2>&1 | head -1                            # No such file or directory
```

어긋나면 **멈추고 보고**한다.

### 4-2. 패치 적용

```bash
git apply --check docs/tasks/patches/2026-10-12-library-backup.patch && git apply docs/tasks/patches/2026-10-12-library-backup.patch
git --no-optional-locks status --porcelain
#   기대: M AGENTS.md · M CLAUDE.md · M README.md · M scheduler.js · M scripts/test_scheduler_guards.js
#        ?? backup_library.py · ?? scripts/test_backup_library.py · ?? 지시서 · ?? 패치
git check-ignore -q data/backups/x.db.gz && echo IGNORED      # IGNORED
```

### 4-3. 회귀 테스트 7종 (네트워크 0회, 실제 장부·.env 무관)

```bash
/opt/homebrew/bin/node scripts/test_scheduler_guards.js      # 22/22 PASS
/opt/homebrew/bin/python3 scripts/test_backup_library.py     # 50/50 PASS
/opt/homebrew/bin/python3 scripts/test_notion_to_sqlite.py   # 37/37
/opt/homebrew/bin/python3 scripts/test_kakao_ingest.py       # 18/18
/opt/homebrew/bin/python3 scripts/test_sync_obsidian.py      # 23/23
/opt/homebrew/bin/python3 scripts/test_sheet_mirror.py       # 45/45
/opt/homebrew/bin/python3 scripts/test_build_wiki_index.py   # 10/10
```

하나라도 FAIL 이면 멈추고 보고(7절 롤백).

### 4-4. `.env` 에 드라이브 경로 추가

값은 지시문 본문에 있다. 한 줄만 덧붙이고, 다른 줄은 건드리지 않는다.

```bash
cp .env .env.bak.$(date +%Y%m%d_%H%M%S)
printf '\nLIBRARY_BACKUP_DIR=%s\n' '<LIBRARY_BACKUP_DIR 값>' >> .env
grep -c '^LIBRARY_BACKUP_DIR=' .env      # 1
grep '^LIBRARY_BACKUP_DIR=' .env         # 값 확인 (경로만 — 비밀값 아님)
```

### 4-5. 실데이터 dry-run (쓰기 0)

```bash
/opt/homebrew/bin/python3 backup_library.py --dry-run
#   기대: [dry-run] local: <REPO_ROOT>/data/backups/library-YYYYMMDD.db.gz 만들 예정 · 지울 것 0개 []
#         [dry-run] drive: <LIBRARY_BACKUP_DIR 값>/library-YYYYMMDD.db.gz 만들 예정 · 지울 것 0개 []
#         RESULT_JSON:{"dry_run": true, ..., "dests": {"local": "todo", "drive": "todo"}, "error": ""}
ls data/backups 2>&1 | head -1           # 여전히 No such file or directory
```

`drive` 가 `unavailable` 이면 드라이브 앱·경로 문제다 — 멈추고 보고.

### 4-6. 첫 백업 1회 + 확인

```bash
shasum -a 256 data/library.db > /tmp/ledger_before.txt
/opt/homebrew/bin/python3 backup_library.py; echo "exit=$?"
#   기대: 🗄  library-YYYYMMDD.db.gz 3.6MB · 영상 2,98x · 꿀팁 13x · local ok · drive ok · 정리 local 0개, drive 0개
#         RESULT_JSON:{... "dests": {"local": "ok", "drive": "ok"}, "error": ""}   exit=0
shasum -a 256 -c /tmp/ledger_before.txt                       # data/library.db: OK  (장부 무변경)
D=$(TZ=Asia/Seoul date +%Y%m%d)
ls -l data/backups/ "$(grep '^LIBRARY_BACKUP_DIR=' .env | cut -d= -f2- | sed "s|^~|$HOME|")"/
#   두 곳 모두 library-$D.db.gz 1개, 크기 같음. .tmp·.snap-* 없음
gunzip -c data/backups/library-$D.db.gz > /tmp/restore_test.db
/usr/bin/sqlite3 /tmp/restore_test.db "PRAGMA integrity_check; SELECT COUNT(*) FROM videos; SELECT COUNT(*) FROM tips;"
/usr/bin/sqlite3 -readonly data/library.db "SELECT COUNT(*) FROM videos; SELECT COUNT(*) FROM tips;"
#   ok · 두 쪽 행 수 같음
rm /tmp/restore_test.db /tmp/ledger_before.txt
```

### 4-7. 같은 날 두 번째 → 건너뜀

```bash
/opt/homebrew/bin/python3 backup_library.py; echo "exit=$?"
#   기대: ℹ️  오늘 백업 있음 (library-YYYYMMDD.db.gz)   RESULT_JSON:{"skipped": "already_done", ...}   exit=0
/opt/homebrew/bin/python3 backup_library.py --status
#   기대: local: 1개 · 3.6MB · 최근 library-YYYYMMDD.db.gz (0일 전) / drive: 1개 · 3.6MB · ... (0일 전)
```

스케줄러 수동 실행은 하지 않는다 — 훅은 다음 자동 실행(06시면 `ℹ️  장부 백업 건너뜀: already_done`)에서 Cowork 가 로그로 확인한다.

## 5. 커밋 (push 하지 않음)

```bash
git add backup_library.py scripts/test_backup_library.py scheduler.js scripts/test_scheduler_guards.js \
        README.md CLAUDE.md AGENTS.md \
        docs/tasks/2026-10-12-library-backup.md docs/tasks/patches/2026-10-12-library-backup.patch
git --no-optional-locks status --porcelain       # 기대: 빈 출력 (.env.bak.* 는 gitignore)
git commit -m "v4.1 장부 하루 1회 자동 백업 — backup_library.py (로컬 data/backups + 구글 드라이브, 최신 7 + 주별 4)"
git --no-optional-locks log --oneline -2
git --no-optional-locks show --stat HEAD | tail -12   # 9개 파일
```

**push 는 하지 않는다.** Cowork 가 커밋 diff 와 드라이브 업로드를 확인한 뒤 따로 지시한다.

## 6. 데몬

- 재기동 불필요. `scheduler.js` 는 launchd 가 실행마다 새로 띄운다(다음 실행부터 반영). `server.js`·`wiki_lan_server.js` 무변경.

## 7. 롤백

- 커밋 전: `git apply -R docs/tasks/patches/2026-10-12-library-backup.patch` 후 `.env` 를 4-4 의 `.env.bak.*` 로 되돌린다.
- 커밋 후: `git revert HEAD`(push 전이면 `git reset --hard 9e272be` 도 가능 — 지시서·패치 파일은 다시 untracked 로 둔다). `.env` 의 `LIBRARY_BACKUP_DIR` 줄 삭제.
- 이미 만든 `data/backups/`·드라이브 폴더의 백업 파일은 무해하니 남겨 둔다.

## 8. 범위 밖

- 타임머신 복구(외장 디스크) — 대표님 별건.
- 복원 스크립트 자동화(`--restore`) — README 의 손 절차로 둔다.
- 노션 정리(「Notion 데이터 이관」 종료 후), 실행 통째 실패 알림, Gemini 한도 방침.
- `git push`.

## 9. 보고 형식 (한국어)

```
[CC-1012-E] 결과
- 4-1 시작 상태: HEAD / porcelain / 패치 sha256 일치 여부 / .env 줄 수
- 4-2 적용: status 요약 / check-ignore
- 4-3 테스트: 7종 각 n/n
- 4-4 .env: 줄 수 1, 값
- 4-5 dry-run: RESULT_JSON 한 줄
- 4-6 첫 백업: RESULT_JSON 한 줄, exit, 장부 OK, 두 폴더 ls, integrity/행 수
- 4-7 두 번째: skipped 여부, --status 두 줄
- 5 커밋: 해시, show --stat
- 특이사항(멈춘 단계·기대와 다른 출력 원문)
```
