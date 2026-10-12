# v4.2 — 실행 실패 알림 (통째 실패 · 치명적 오류 · 못 보낸 알림 · 빠진 정시 실행)

> 지시 번호는 발행할 때 채팅으로 준다(`[CC-1012-G]`). 보고는 한국어로.
> 선행: v4.1 `582ef8e`(원격 main 과 같음). 스케줄러는 내리지 않는다(4-0 의 시간 창만 피한다).
> `.env` 변경 없음.

## 1. 배경

10-04 06:00 ~ 10-12 06:00 실행 35회를 `scheduler.log` 로 다시 셌다(Cowork, 10-12).

| 구분 | 건수 | 텔레그램 |
|---|---|---|
| 프로세스가 죽은 실행(`❌ 치명적 오류` → exit 1) | 0 | 가지 않음(`main().catch` 는 로그만) |
| 마스터 인제스트가 통째 실패해 "저장 0 · Skip 0 · 오류 1" 로 끝난 실행(10-04 06:00, 10-05 00:00 — 둘 다 `ENOTFOUND www.googleapis.com`) | 2 | **가지 않음** — 완료 알림 조건 `hasNewOrUpdated` 에 안 걸린다 |
| 아예 돌지 않은 정시 실행(10-09 12:00. 10-07 18:00 은 18:32 에 늦게 시작) | 1 | 가지 않음 — 감지 장치 없음. 원인 미확인 |

- v3.2.1(10-05) 재시도 이후 통째 실패는 다시 나오지 않았지만, 나와도 모르는 구조는 그대로다.
- 네트워크가 죽은 실행은 **그 자리에서 텔레그램도 못 보낸다**(같은 DNS). 그래서 "다음 실행이 알리는" 길이 함께 있어야 한다.
- 같이 발견한 잠복 결함: `sendTelegram` 이 응답 본문을 `JSON.parse` 하는데, 텔레그램 쪽이 JSON 이 아닌 응답(게이트웨이 502 HTML 등)을 주면 이벤트 핸들러에서 던져 **프로세스가 죽는다**. 무응답에는 끝없이 기다린다.

## 2. 설계 결정 (대표님 B안 확정, 10-12 — 바꾸지 말 것)

| 항목 | 결정 |
|---|---|
| 통째 실패 판정 | `isWholeRunFailure` = 저장 0 · Skip 0 · 오류 ≥ 1. "0 · 1537 · 2" 같은 일부 오류, "0 · 0 · 0"(빈 목록)은 실패가 아니다. |
| 그 자리 알림 | 통째 실패면 `🚨 [실행 실패]`(원인 = 마지막 오류의 첫 줄, 300자). **장부 로드 실패는 기존 `[장부 로드 실패]` 하나만** — 두 번 보내지 않는다. `main().catch` 도 상태를 먼저 기록한 뒤 `🚨 [실행 실패]`. |
| 다음 실행 알림 | 실행 상태 파일 `.run_state.json`(레포 루트, gitignore). main 이 시작할 때 직전 기록을 읽어 `runNotices` 로 문구를 만들고 `⚠️ [직전 실행 점검]` 한 통으로 보낸다. ① 직전이 `running` 이고 3시간 이상 = 끝을 기록하지 못한 실행(3시간 미만은 겹친 실행일 수 있어 알리지 않음) ② 직전이 `fail` 이고 `notified=false` = 그때 못 보낸 실패 ③ 직전 시작부터 9시간 이상 = 정시 실행이 빠짐(6시간 + 지연 3시간 허용). |
| 못 보낸 점검 문구 | 시작 기록의 `pending` 에 먼저 써 두고, 보내면 비운다. 못 보내면 다음 실행이 앞에 붙여 다시 보낸다. 최대 10줄. |
| 상태 파일 | `{ v, started_at, finished_at, outcome: running/ok/fail, reason, notified, pending }`. `.tmp` 로 쓰고 이름 바꾸기. 읽기·쓰기 실패는 실행을 막지 않는다(로그만). 지워도 무해 — 다음 실행이 처음처럼 시작. |
| `sendTelegram` | reject 없이 **보냈으면 true, 꺼짐·실패면 false**. JSON 아닌 응답 → false(던지지 않음). `req.setTimeout(20000)`. 기존 호출부는 반환값을 안 쓰므로 동작 동일. |
| 범위 밖으로 둔 것 | Gemini 401/403 경로의 `process.exit(1)` 은 자체 텔레그램을 보내고 상태를 `running` 으로 남긴다 → 다음 실행이 "끝을 기록하지 못했습니다" 를 한 번 더 알린다(의도). `.env`·OAuth 모듈 로드 실패로 마스터 인제스트를 건너뛰는 "0 · 0 · 0" 은 잡지 않는다. 빠진 실행의 원인 조사. |

## 3. 파일 — 패치 1개

`docs/tasks/patches/2026-10-12-run-failure-alert.patch` (기준 = `582ef8e`)

```
sha256  a9c13d65f0e774380ac662a0d629ad24e6e872a042fc51ebcbd28315a070815a
```

| 파일 | 변경 |
|---|---|
| `scheduler.js` | `sendTelegram` 반환값·JSON 가드·20초 타임아웃. 상태 파일 헬퍼(`readRunState`·`writeRunState`·`runNotices`·`isWholeRunFailure`·`escapeHtml`·`shortReason`, 상수 3개). main: 시작 기록 + `[직전 실행 점검]`, 장부 로드 실패·마스터/레거시 오류 원인 기록, "완료!" 뒤 통째 실패 알림 + 결과 기록. `main().catch` 기록 + 알림. export(테스트용) |
| `scripts/test_scheduler_guards.js` | +7건 → **29**. 가짜 https 에 `setTimeout`·비JSON 응답(`raw`) 추가, `TELEGRAM_*` 는 테스트 값(실제 봇 무관) |
| `.gitignore` | `.run_state.json*` |
| `README.md` · `CLAUDE.md` · `AGENTS.md` | v4.2(요약 행 + 상세 1절 · 머리 버전 · 「실행 실패 알림 (v4.2)」 절 · 테스트 수 · gitignore 목록 · 이력). AGENTS.md = 머리글 5줄 + CLAUDE.md 4행부터 |

### Cowork 사전 검증 (2026-10-12 11:15, 맥 네이티브 · 레포 무변경)

- 레포 작업 트리에서 `git apply --check` 통과. 임시 폴더에 `git archive 582ef8e` + 패치 적용: `git check-ignore` 로 `.run_state.json`·`.run_state.json.tmp` 무시 확인.
- 회귀 테스트 7종(node v26.10.0 · Homebrew Python 3.14.8): `test_scheduler_guards.js` 29/29 · `test_notion_to_sqlite.py` 37/37 · `test_kakao_ingest.py` 18/18 · `test_sync_obsidian.py` 23/23 · `test_sheet_mirror.py` 45/45 · `test_build_wiki_index.py` 10/10 · `test_backup_library.py` 50/50.
- `main()` 모의 실행 10종 — 사본 폴더(가짜 `.env`·임시 장부 1행), `https.request`·`child_process.execFile` 을 가짜로 바꿔 실제 네트워크·Vault·장부 무관. 실행 사이에 상태 파일의 `started_at` 을 앞당겨 시간 경과를 흉내.

| # | 상황 | 결과 |
|---|---|---|
| 1 | 네트워크 전부 다운(텔레그램도) | `[실행 실패]` 시도·실패 → `outcome fail · notified false · reason 마스터 인제스트 오류: getaddrinfo ENOTFOUND www.googleapis.com` |
| 2 | 6시간 뒤 텔레그램만 복구 | `[직전 실행 점검]`(1의 실패) + 이번 `[실행 실패]` 두 통 → `notified true · pending []` |
| 3 | 12시간 간격 | `⏰ … 12.0시간 — 그 사이 정시 실행이 빠졌습니다` 한 줄 |
| 4 | 직전 `running` 6시간 | `🛑 … 실행이 끝을 기록하지 못했습니다` |
| 5 | 직전 `running` 1시간(겹친 실행) | 알림 없음 |
| 6 | 장부 파일 없음 | `[장부 로드 실패]` 한 통만, `reason 장부 로드 실패: …` · `notified true` |
| 7 | 실패 → 실패(둘 다 못 보냄) → 복구 | 2회차가 `pending` 에 1줄 보관 → 3회차가 보관분 + 2회차 실패 2줄을 한 통으로 → `pending []` |
| 8 | 치명적 오류 + 텔레그램 다운 | exit 1, `reason 치명적 오류: …` · `notified false` |
| 9 | 그다음 실행 | `[직전 실행 점검]` 에 8의 원인(`<` `>` 이스케이프) |
| 10 | 치명적 오류 + 텔레그램 정상 | `[실행 실패]` 전송 · `notified true` |

## 4. 실행 — `[CC-1012-G]`

### 4-0. 시간

스케줄러가 00·06·12·18시에 돈다. **매시 50분 ~ 다음 시 20분(예: 11:50~12:20)에는 4-2 이후를 시작하지 않는다.**

### 4-1. 시작 상태 (읽기만)

```bash
cd <REPO_ROOT>
git --no-optional-locks rev-parse --short HEAD          # 582ef8e
git --no-optional-locks status --porcelain
#   기대: 아래 두 줄만 (이 지시서와 패치)
#   ?? docs/tasks/2026-10-12-run-failure-alert.md
#   ?? docs/tasks/patches/2026-10-12-run-failure-alert.patch
shasum -a 256 docs/tasks/patches/2026-10-12-run-failure-alert.patch   # 3절 값과 같아야 한다
[ -e .run_state.json ] && echo PRESENT || echo ABSENT   # ABSENT
```

어긋나면 **멈추고 보고**한다.

### 4-2. 패치 적용

```bash
git apply --check docs/tasks/patches/2026-10-12-run-failure-alert.patch && git apply docs/tasks/patches/2026-10-12-run-failure-alert.patch
git --no-optional-locks status --porcelain
#   기대: M .gitignore · M AGENTS.md · M CLAUDE.md · M README.md · M scheduler.js · M scripts/test_scheduler_guards.js
#        ?? 지시서 · ?? 패치
git check-ignore -q .run_state.json && git check-ignore -q .run_state.json.tmp && echo IGNORED      # IGNORED
/opt/homebrew/bin/node --check scheduler.js && echo SYNTAX_OK
{ head -5 AGENTS.md; tail -n +4 CLAUDE.md; } | cmp - AGENTS.md && echo AGENTS_OK
```

### 4-3. 회귀 테스트 7종 (네트워크 0회, 실제 장부·.env·텔레그램 무관)

```bash
/opt/homebrew/bin/node scripts/test_scheduler_guards.js      # 29/29 PASS
/opt/homebrew/bin/python3 scripts/test_notion_to_sqlite.py   # 37/37
/opt/homebrew/bin/python3 scripts/test_kakao_ingest.py       # 18/18
/opt/homebrew/bin/python3 scripts/test_sync_obsidian.py      # 23/23
/opt/homebrew/bin/python3 scripts/test_sheet_mirror.py       # 45/45
/opt/homebrew/bin/python3 scripts/test_build_wiki_index.py   # 10/10
/opt/homebrew/bin/python3 scripts/test_backup_library.py     # 50/50
[ -e .run_state.json ] && echo PRESENT || echo ABSENT   # ABSENT (테스트는 임시 폴더에만 쓴다)
```

하나라도 FAIL 이면 멈추고 보고(7절 롤백).

### 4-4. 실데이터 확인 (읽기만, 네트워크 0)

`scheduler.js` 를 `require` 해 판정 함수만 부른다(가드 때문에 main 은 돌지 않는다).

```bash
/opt/homebrew/bin/node -e "
const s=require('./scheduler.js');
console.log('state', s.readRunState());
console.log('fail?', s.isWholeRunFailure({saved:0,skip:0,error:1}), s.isWholeRunFailure({saved:0,skip:1539,error:0}));
console.log('gap12', s.runNotices({started_at:new Date(Date.now()-12*3600e3).toISOString(),outcome:'ok'}, Date.now()).length);
" 2>&1 | grep -v ExperimentalWarning
#   기대: state null · fail? true false · gap12 1
[ -e .run_state.json ] && echo PRESENT || echo ABSENT   # ABSENT
```

스케줄러 수동 실행은 하지 않는다 — 첫 기록은 다음 자동 실행이 만든다(Cowork 가 로그·상태 파일로 확인).

## 5. 커밋 (push 하지 않음)

```bash
git add .gitignore scheduler.js scripts/test_scheduler_guards.js README.md CLAUDE.md AGENTS.md \
        docs/tasks/2026-10-12-run-failure-alert.md docs/tasks/patches/2026-10-12-run-failure-alert.patch
git --no-optional-locks status --porcelain       # 기대: 빈 출력
git commit -m "v4.2 실행 실패 알림 — 통째 실패·치명적 오류는 바로, 못 보낸 알림·끝나지 못한 실행·빠진 정시 실행은 다음 실행이 (.run_state.json)"
git --no-optional-locks log --oneline -2
git --no-optional-locks show --stat HEAD | tail -10   # 8개 파일
```

**push 는 하지 않는다.** Cowork 가 커밋 diff 와 다음 자동 실행 결과를 확인한 뒤 따로 지시한다.

## 6. 데몬

- 재기동 불필요. `scheduler.js` 는 launchd 가 실행마다 새로 띄운다(다음 실행부터 반영). `server.js`·`wiki_lan_server.js` 무변경.
- `server.js` 의 `/api/master-ingest` 도 `scheduler.js` 를 새 프로세스로 띄우므로 같은 상태 파일을 쓴다(의도).

## 7. 롤백

- 커밋 전: `git apply -R docs/tasks/patches/2026-10-12-run-failure-alert.patch`.
- 커밋 후: `git revert HEAD`(push 전이면 `git reset --hard 582ef8e` 도 가능 — 지시서·패치 파일은 다시 untracked 로 둔다).
- 이미 생긴 `.run_state.json` 은 무해하니 남겨 두거나 지운다.

## 8. 범위 밖

- 빠진 실행(10-09 12:00)의 원인 조사 — 알림이 쌓이면 그때 본다.
- `.env`·OAuth 모듈 로드 실패의 "0 · 0 · 0" 판정, Gemini 401/403 exit 경로 정리.
- 노션 정리(「Notion 데이터 이관」 종료 후), Gemini 한도 방침, 야간 DNS.
- `git push`.

## 9. 보고 형식 (한국어)

```
[CC-1012-G] 결과
- 4-1 시작 상태: HEAD / porcelain / 패치 sha256 일치 여부 / .run_state.json 없음 여부
- 4-2 적용: status 요약 / IGNORED / SYNTAX_OK / AGENTS_OK
- 4-3 테스트: 7종 각 n/n, 상태 파일 없음 여부
- 4-4 실데이터: 출력 3줄, 상태 파일 없음 여부
- 5 커밋: 해시, show --stat
- 특이사항(멈춘 단계·기대와 다른 출력 원문)
```
