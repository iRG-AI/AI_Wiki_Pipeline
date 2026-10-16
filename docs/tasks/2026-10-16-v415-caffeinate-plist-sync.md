# v4.15 — 정시 실행 중 잠자기 방지(caffeinate) · plist 원본 경로 맞춤

- 작성: 2026-10-16 (Cowork) · 기준 커밋 `fe71d64` · 실행: Claude Code
- 패치: `docs/tasks/patches/2026-10-16-v415-caffeinate-plist-sync.patch` (10파일 +41 −17)
  sha256 `add005f14baf51332ca9c789b256194e00947c4bb2091189f22914d4fa97ac63`
- 보고는 한국어로.

## 1. 배경

- 10-15 12:00 실행이 `ENOTFOUND` 로 통째 실패했다(v4.2 `[실행 실패]` 알림 정상, 놓친 신규 0).
  `pmset -g log`: 11:54 `Clamshell Sleep`(덮개 닫힘, 배터리 36%) → 12:01 DarkWake 6초 사이에 실행 시작 → 다시 `Maintenance Sleep`.
  **덮개를 닫은 잠자기는 이 변경으로 막지 못한다**(`pmset disablesleep` 은 가방 속 발열 위험이라 쓰지 않는다).
- 대신 `pmset -g custom` 배터리 `sleep 1`(1분) — 덮개를 연 채 자리를 비우면 15분 안팎의 실행 도중 유휴 잠자기에 들 수 있다.
  이 경우만 `caffeinate -i` 로 막는다. 맥 실측(10-16): `caffeinate -i` 아래에서 `pmset -g assertions` 에 caffeinate 단언이 생기고, 감싼 프로그램의 종료 코드(3)를 그대로 돌려준다.
- 함께: 10-16 레포 이관(`~/Documents/Claude/Projects/AI_Wiki_Pipeline` → `~/Dev/AI_Wiki_Pipeline`, 옛 자리 링크) 때 **설치본 plist 4개만** 새 경로로 바뀌어,
  레포 원본 4개가 설치본과 다르다(「원본 = 설치본」 규칙 위반). `install-server.sh`·`install-scheduler.sh` 의 sed 패턴, `wiki_mcp.js` 주석, `AGENTS.md` 레포 경로도 옛 경로다.

## 2. AS-IS → TO-BE

| 파일 | AS-IS | TO-BE |
|---|---|---|
| `com.irichgreen.ytsummarizer.plist` | `node scheduler.js`, 옛 경로 | `/usr/bin/caffeinate -i /opt/homebrew/bin/node <REPO_ROOT>/scheduler.js`, 새 경로 |
| `com.irichgreen.server.plist` · `wiki-lan` · `wiki-ingest` | 옛 경로(각 2곳) | 새 경로 — 설치본과 같아짐 |
| `install-server.sh` · `install-scheduler.sh` | sed 패턴 옛 경로 | 새 경로 |
| `wiki_mcp.js` | 등록 주석 옛 경로 | 새 경로(주석만) |
| `CLAUDE.md` · `AGENTS.md` · `README.md` | v4.14 | v4.15 머리·launchd 표·주의 1줄·이력 |

코드 동작·장부·`.env`·스케줄 무변경. 회귀 테스트 대상 코드 변경 없음(주석 1줄) — 15종은 돌리지 않는다.

## 3. 시간 창

분이 50~59 또는 00~20 이면 창 안(매시). 창 안이면 분 21 까지 `sleep` 으로 기다렸다 진행한다(9분씩).
`pgrep -f scheduler.js` 가 출력이 있으면 실행 중 — 끝날 때까지 기다린다.

## 4. 단계

```bash
cd <REPO_ROOT>

# 4-1 사전 확인
git --no-optional-locks log --oneline -1          # fe71d64
git --no-optional-locks status --porcelain        # ?? docs/tasks/2026-10-16-v415-caffeinate-plist-sync.md
                                                  # ?? docs/tasks/patches/2026-10-16-v415-caffeinate-plist-sync.patch  (이 둘만)
shasum -a 256 docs/tasks/patches/2026-10-16-v415-caffeinate-plist-sync.patch   # add005f1…ac63
git apply --check docs/tasks/patches/2026-10-16-v415-caffeinate-plist-sync.patch && echo CHECK_OK

# 4-2 설치본 백업 (스케줄러 plist 만 바꾼다)
mkdir -p ~/Library/LaunchAgents/_disabled
cp -p ~/Library/LaunchAgents/com.irichgreen.ytsummarizer.plist ~/Library/LaunchAgents/_disabled/com.irichgreen.ytsummarizer.plist.bak.v415

# 4-3 적용
git apply docs/tasks/patches/2026-10-16-v415-caffeinate-plist-sync.patch

# 4-4 검증 (설치 전)
for n in server ytsummarizer wiki-lan wiki-ingest; do plutil -lint com.irichgreen.$n.plist; done            # 4개 OK
for n in server wiki-lan wiki-ingest; do diff <(plutil -convert xml1 -o - ~/Library/LaunchAgents/com.irichgreen.$n.plist) <(plutil -convert xml1 -o - com.irichgreen.$n.plist) >/dev/null && echo "$n 같음" || echo "$n 다름"; done   # 3개 같음
diff <(plutil -convert xml1 -o - ~/Library/LaunchAgents/com.irichgreen.ytsummarizer.plist) <(plutil -convert xml1 -o - com.irichgreen.ytsummarizer.plist)
#   기대: 8a9,10 / > <string>/usr/bin/caffeinate</string> / > <string>-i</string> 만
bash -n install-server.sh && bash -n install-scheduler.sh && node --check wiki_mcp.js && echo SYNTAX_OK

# 4-5 설치 (대표님 승인 — launchd 재로드. RunAtLoad false 라 즉시 실행되지 않는다)
cp com.irichgreen.ytsummarizer.plist ~/Library/LaunchAgents/com.irichgreen.ytsummarizer.plist
launchctl unload ~/Library/LaunchAgents/com.irichgreen.ytsummarizer.plist
launchctl load ~/Library/LaunchAgents/com.irichgreen.ytsummarizer.plist
launchctl list | grep com.irichgreen.ytsummarizer                       # -  0  com.irichgreen.ytsummarizer
launchctl print gui/$(id -u)/com.irichgreen.ytsummarizer | grep -A5 "arguments = {"   # caffeinate · -i · node · scheduler.js
for n in server ytsummarizer wiki-lan wiki-ingest; do diff <(plutil -convert xml1 -o - ~/Library/LaunchAgents/com.irichgreen.$n.plist) <(plutil -convert xml1 -o - com.irichgreen.$n.plist) >/dev/null && echo "$n 같음" || echo "$n 다름"; done   # 4개 같음

# 4-6 caffeinate 동작 (읽기 전용)
/usr/bin/caffeinate -i /bin/sh -c 'pmset -g assertions | grep -c caffeinate; exit 3'; echo "exit=$?"   # 1 이상 · exit=3

# 4-7 커밋 (push 하지 않는다)
git add -A com.irichgreen.*.plist install-server.sh install-scheduler.sh wiki_mcp.js CLAUDE.md AGENTS.md README.md docs/tasks/2026-10-16-v415-caffeinate-plist-sync.md docs/tasks/patches/2026-10-16-v415-caffeinate-plist-sync.patch
git commit -m "v4.15 정시 실행을 caffeinate -i 로 감싸 실행 중 유휴 잠자기 방지 · plist 원본 4개·설치 스크립트를 ~/Dev 경로로 (코드 무변경)"
git --no-optional-locks status --porcelain        # 빈 출력
git --no-optional-locks show --stat --format="%h %s" HEAD | tail -3   # 12 files changed
```

## 5. 보고

4-1 ~ 4-7 각 출력(기대값과 다르면 그 자리에서 멈추고 보고), 커밋 해시.

## 6. 롤백

```bash
cp -p ~/Library/LaunchAgents/_disabled/com.irichgreen.ytsummarizer.plist.bak.v415 ~/Library/LaunchAgents/com.irichgreen.ytsummarizer.plist
launchctl unload ~/Library/LaunchAgents/com.irichgreen.ytsummarizer.plist && launchctl load ~/Library/LaunchAgents/com.irichgreen.ytsummarizer.plist
git revert <v4.15 커밋>          # 커밋 뒤라면
```

## 7. 범위 밖

- 덮개를 닫은 잠자기·정시에 이미 잠든 맥(소프트웨어로 안전하게 막을 수 없다 — v4.2 알림 + 다음 실행이 이어 받음).
- `com.irichgreen.wiki-ingest`(17:30) caffeinate, `server.js` `/api/master-ingest` 수동 실행.
- 레포 밖 옛 경로(링크로 동작): `~/Library/Scripts/rotate_extra_logs.sh` 의 `YTDIR`, Claude Code MCP `wiki-search` 등록.
- `~/Library/LaunchAgents/*.plist.bak.20261016`(이관 때 백업) 정리.
