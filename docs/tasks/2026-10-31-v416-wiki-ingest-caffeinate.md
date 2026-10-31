# [CC-1031-B] v4.16 — wiki-ingest(17:30)도 caffeinate · brew 업그레이드 뒤 점검 순서

- 작성: 2026-10-31 · Cowork(CW) 초안 → pm-wiki 실행
- 실행: `implementer`(Sonnet · medium) → 검수 `verifier`(Opus · high)
- 승인 범위: 레포 plist 원본 1개 수정 · 설치본 교체 + `launchctl` 재로드 1회(시간 창 밖) · 문서 3개 · 커밋 1건. **`git push` 는 별도 승인.**
- 선행: `[CC-1031-A]` 커밋

## 배경

- v4.15 는 정시 실행(`com.irichgreen.ytsummarizer`)만 `/usr/bin/caffeinate -i` 로 감쌌다. 17:30 `com.irichgreen.wiki-ingest` 도 증분 + backfill(20개 묶음, 하루 최대 30회 호출)로 몇 분씩 도는데, 배터리 설정이 `sleep 1`(1분)이라 덮개를 연 채 자리를 비우면 도중에 잠들 수 있다. 같은 방법으로 감싼다.
- 2026-10-30 저녁 `brew upgrade` 로 simdjson 이 올라가 node 26.10.0 이 `dyld: Library not loaded: …libsimdjson.33.dylib` 로 기동 즉시 죽었다. 정시 실행 2회(10-30 18시·10-31 00시)가 `scheduler.log` 에 한 줄도 남기지 않았고(`~/Library/Logs/irichgreen/ytsummarizer-err.log` 에만), 상주 데몬 `server`·`wiki-lan` 은 node 26.13.0 설치(00:19)까지 재시작 실패를 반복했다. 다음 실행의 `[직전 실행 점검]` 간격 경고로만 드러났다 — 점검 순서를 문서로 남긴다.
- 레포 밖 옛 경로 두 곳(`~/Library/Scripts/rotate_extra_logs.sh` 의 `YTDIR`, Claude Code MCP `wiki-search` 등록)은 설치 스크립트(`setup-pm-wiki.sh`)가 대표님 터미널에서 이미 고쳤다 — 이 지시서는 **확인만** 한다.

## 범위

- 바꿀 파일: `com.irichgreen.wiki-ingest.plist`(레포 원본) · `~/Library/LaunchAgents/com.irichgreen.wiki-ingest.plist`(설치본, 레포 밖) · `CLAUDE.md` · `AGENTS.md` · `README.md`
- 바꾸면 안 되는 것: 코드, 다른 plist 3개, `install-*.sh`(wiki-ingest 설치 스크립트는 치환 없이 복사한다 — 그대로 둔다), `.env`, 장부

## 확인(먼저) — 하나라도 다르면 멈추고 보고

| # | 명령 | 기대값 |
|---|---|---|
| 0-1 | `git log --oneline -1` | `[CC-1031-A] …` 커밋 |
| 0-2 | `git status --porcelain -uall` | `?? docs/tasks/2026-10-31-v416-wiki-ingest-caffeinate.md` 한 줄 |
| 0-3 | `diff <(plutil -convert xml1 -o - ~/Library/LaunchAgents/com.irichgreen.wiki-ingest.plist) <(plutil -convert xml1 -o - com.irichgreen.wiki-ingest.plist) && echo same` | `same` |
| 0-4 | `grep -c caffeinate com.irichgreen.wiki-ingest.plist` | `0` |
| 0-5 | `grep -n '^YTDIR=' ~/Library/Scripts/rotate_extra_logs.sh` | `YTDIR="$HOME/Dev/AI_Wiki_Pipeline"` |
| 0-6 | `/opt/homebrew/bin/python3 -c "import json,os;print(json.load(open(os.path.expanduser('~/.claude.json')))['mcpServers']['wiki-search']['args'])"` | `~/Dev/AI_Wiki_Pipeline/wiki_mcp.js` 의 절대경로 한 개 |

0-5·0-6 이 다르면 설치 스크립트의 레포 밖 단계가 안 된 것 — 고치지 말고 보고(대표님 몫).

## 단계

### 1. 레포 plist 원본 — `ProgramArguments` 앞에 caffeinate

AS-IS
```xml
	<key>ProgramArguments</key>
	<array>
		<string>/opt/homebrew/bin/python3</string>
```
TO-BE
```xml
	<key>ProgramArguments</key>
	<array>
		<string>/usr/bin/caffeinate</string>
		<string>-i</string>
		<string>/opt/homebrew/bin/python3</string>
```
나머지 줄은 그대로. `plutil -lint com.irichgreen.wiki-ingest.plist` → OK.

### 2. 설치본 교체 + 재로드 — 시간 창 밖에서만

조건(셋 다): 분이 21~49 · 17:25~17:50 아님 · `pgrep -f wiki_ingest.py` 출력 없음. 아니면 분 21 까지 9분씩 sleep 후 다시 본다.

```bash
mkdir -p ~/Library/LaunchAgents/_disabled
cp -p ~/Library/LaunchAgents/com.irichgreen.wiki-ingest.plist ~/Library/LaunchAgents/_disabled/com.irichgreen.wiki-ingest.plist.bak.v416
launchctl unload ~/Library/LaunchAgents/com.irichgreen.wiki-ingest.plist
cp com.irichgreen.wiki-ingest.plist ~/Library/LaunchAgents/com.irichgreen.wiki-ingest.plist
plutil -lint ~/Library/LaunchAgents/com.irichgreen.wiki-ingest.plist
launchctl load ~/Library/LaunchAgents/com.irichgreen.wiki-ingest.plist
launchctl print gui/$(id -u)/com.irichgreen.wiki-ingest | sed -n '/arguments = {/,/}/p'
```
기대: arguments 가 `/usr/bin/caffeinate` · `-i` · `/opt/homebrew/bin/python3` · `<REPO_ROOT>/wiki_ingest.py` 4줄. `launchctl list | grep wiki-ingest` 한 줄. **실행(`launchctl start`)은 하지 않는다** — 첫 실제 실행은 다음 17:30.

### 3. `CLAUDE.md`

넣는 문구는 아래 코드 블록 안의 글자 그대로다(블록 표시 ``` 는 넣지 않는다).

3-1. 머리 버전 줄 교체 — AS-IS `**현재 버전: v4.15** (2026-10-16)` → TO-BE `**현재 버전: v4.16** (2026-10-31)` (같은 줄의 뒤쪽 레포 경로 표기는 그대로).

3-2. 버전 요약 인용의 `> v4.15:` 로 시작하는 줄 **바로 아래**에 한 줄:
```
> v4.16: 17:30 Wiki 인제스트(`com.irichgreen.wiki-ingest`)도 `/usr/bin/caffeinate -i` 로 감싼다(v4.15 와 같은 이유). `brew upgrade` 뒤 점검 순서를 「launchd 데몬」 절에 적었다(10-30 simdjson 업그레이드로 node 가 기동 즉시 죽어 정시 실행 2회가 로그 없이 빠진 사건). 코드·장부 무변경.
```

3-3. 「launchd 데몬」 표의 `com.irichgreen.wiki-ingest` 행, 실행 대상 칸:
AS-IS
```
`wiki_ingest.py` (증분 + backfill + 재렌더)
```
TO-BE
```
`wiki_ingest.py` (증분 + backfill + 재렌더, v4.16 `caffeinate -i` 로 감쌈)
```

3-4. 같은 절에서 `(v4.15)` 로 시작하고 `ytsummarizer` 의 `ProgramArguments` 를 설명하는 항목(caffeinate 설명) **바로 아래**에 새 항목:
```
- **(v4.16) `com.irichgreen.wiki-ingest` 도 같다** — `/usr/bin/caffeinate -i /opt/homebrew/bin/python3 <REPO_ROOT>/wiki_ingest.py`. 실행 중 확인 `pmset -g assertions | grep caffeinate`, 지난 실행은 `pmset -g log | grep "17:3.*caffeinate"`(macOS 로그에는 `Summary`·`ClientDied` 로 찍힌다 — 다른 앱도 caffeinate 를 수시로 띄우므로 시작 시각으로 가린다). caffeinate 를 빼지 말 것.
```

3-5. 같은 절에서 `후에는 상주 데몬을 반드시 재기동한다` 가 들어 있는 항목 **바로 아래**에 새 항목:
```
- **`brew upgrade` 뒤 점검 순서 (2026-10-30 사건):** 의존 라이브러리(simdjson 등)만 올라가도 node 가 `dyld: Library not loaded` 로 기동 즉시 죽을 수 있다. 정시 실행은 `scheduler.log` 에 아무것도 남기지 않고(`~/Library/Logs/irichgreen/ytsummarizer-err.log` 에만) 다음 실행의 `[직전 실행 점검]` 간격 경고로만 드러나며, 상주 데몬은 KeepAlive 재시작 실패를 반복한다(`launchctl list` 종료 코드 -6·78). 순서: ① `grep -l dyld ~/Library/Logs/irichgreen/*-err.log` ② `/opt/homebrew/bin/node -v` · `/opt/homebrew/bin/python3 -V` ③ `launchctl list | grep irichgreen` ④ 상주 데몬 재기동 ⑤ 방화벽 node Cellar 경로 재허용(가족 PC 로 판정) ⑥ `scripts/run_all_tests.sh`. node 26.13 부터 로그 날짜가 `2026/10/31 오후 12:00:05` 꼴이다(이전 `2026. 10. 31. 오후 …`) — 날짜로 grep 하는 명령은 두 꼴을 다 쓴다.
```

3-6. `## 변경 이력` 바로 아래 첫 항목으로:
```
- **2026-10-31 (v4.16 — wiki-ingest 잠자기 방지 · brew 업그레이드 뒤 점검 순서)** — `com.irichgreen.wiki-ingest` plist `ProgramArguments` 앞에 `/usr/bin/caffeinate -i`(원본·설치본, 재로드). 배경: 10-30 저녁 `brew upgrade`(simdjson) 뒤 node 26.10.0 이 dyld 오류로 기동 즉시 죽어 10-30 18시·10-31 00시 실행이 로그 없이 빠지고 상주 데몬이 00:19 node 26.13.0 설치까지 내려가 있었다 — 「launchd 데몬」 절에 점검 순서. 레포 밖 옛 경로(`rotate_extra_logs.sh` `YTDIR` · MCP `wiki-search`)는 설치 스크립트로 `~/Dev` 로 맞춤(v4.15 범위 밖이던 것). 코드·장부·`.env` 무변경. 지시서 `docs/tasks/2026-10-31-v416-wiki-ingest-caffeinate.md`.
```

### 4. `AGENTS.md` — 3 과 같은 변경

같은 기준 줄에 같은 문구. 기준 줄이 없으면 그 항목만 하지 말고 보고(어긋나면 CLAUDE.md 가 이긴다).

### 5. `README.md`

5-1. 머리 `**현재 버전: v4.15** (2026-10-16)` → `**현재 버전: v4.16** (2026-10-31)`. 머리 인용의 `> v4.15:` 줄 바로 아래에 한 줄:
```
> v4.16: 17:30 Wiki 인제스트도 `caffeinate -i` 로 감싸 실행 중 잠들지 않게 했습니다. `brew upgrade` 뒤 점검 순서를 CLAUDE.md 에 적었습니다(10-30 업그레이드로 정시 실행 2회가 빠진 일).
```

5-2. `### 📌 요약 이력 (Summary Table)` 표 **맨 위**(v4.15 행 위)에 한 행:
```
| **v4.16** | 2026-10-31 | **wiki-ingest 잠자기 방지 · brew 업그레이드 뒤 점검 순서**: `com.irichgreen.wiki-ingest`(17:30)도 `/usr/bin/caffeinate -i` 로 감싼다. 10-30 `brew upgrade`(simdjson)로 node 가 dyld 오류로 기동 즉시 죽어 정시 실행 2회가 로그 없이 빠진 일을 계기로 점검 순서를 CLAUDE.md 에. 레포 밖 옛 경로 2곳을 `~/Dev` 로. 코드·장부 무변경 |
```

5-3. `### 📝 상세 변경 내역` 의 맨 위(`#### [v4.15]` 위)에 절 하나. 헤딩:
```
#### [v4.16] — 2026-10-31 (☕ wiki-ingest 잠자기 방지 · brew 업그레이드 뒤 점검 순서)
```
불릿은 기존 v4.15 절 모양을 따라: 배경(이 지시서 「배경」 두 문단 요약) · 변경(plist 원본·설치본, 문서) · 레포 밖(`rotate_extra_logs.sh` `YTDIR`, MCP `wiki-search` — 설치 스크립트) · 검증(plutil · launchctl print · 설치본 = 원본) · 첫 실제 실행 11-01 17:30.

5-4. README 에 launchd 데몬 표가 있으면 wiki-ingest 행 실행 대상 끝에 ` (v4.16 caffeinate -i)` 를 덧붙인다. 없으면 건너뛴다.

### 6. 커밋

```bash
git add com.irichgreen.wiki-ingest.plist CLAUDE.md AGENTS.md README.md docs/tasks/2026-10-31-v416-wiki-ingest-caffeinate.md
git commit -m "[CC-1031-B] v4.16 wiki-ingest(17:30)도 caffeinate -i 로 감싼다 · brew 업그레이드 뒤 점검 순서 (코드·장부 무변경)"
```
(Co-Authored-By 줄.) `git push` 하지 않는다.

## 기준표

| # | 기준 | 확인 방법 |
|---|---|---|
| 1 | 확인(먼저) 0-1 ~ 0-6 기대값 | 출력 |
| 2 | 레포 plist 원본에 caffeinate·`-i` 가 python3 앞, lint OK | `plutil -lint` · `grep -n -A4 ProgramArguments com.irichgreen.wiki-ingest.plist` |
| 3 | 설치본 = 레포 원본 | 0-3 명령 → `same` |
| 4 | launchd arguments 4줄(caffeinate · -i · python3 · wiki_ingest.py), 목록에 있음 | `launchctl print …` · `launchctl list \| grep wiki-ingest` |
| 5 | 백업 `_disabled/com.irichgreen.wiki-ingest.plist.bak.v416` 있음 | `ls -l` |
| 6 | 재로드가 시간 창 밖에서 됐다 | 보고에 실행 시각(KST) · 게이트·가드 로그 |
| 7 | CLAUDE.md 3-1 ~ 3-6 | `grep -n "v4.16" CLAUDE.md` (머리·인용·표·launchd 항목·이력) · `grep -n "뒤 점검 순서 (2026-10-30" CLAUDE.md` |
| 8 | AGENTS.md 같은 변경(또는 기준 줄 없음 보고) | `grep -n "v4.16" AGENTS.md` |
| 9 | README 머리 v4.16 · 요약표 맨 위 v4.16 · 상세 맨 위 v4.16 · `README.html` 없음 | `grep -n "현재 버전\|v4.16" README.md \| head` · `ls README.html` 없음 |
| 10 | 커밋 1건 `[CC-1031-B]`, 파일 5개, 커밋 뒤 `git status --porcelain -uall` 비어 있음 | `git log --oneline -1` · `git show --stat HEAD \| tail -1` |
| 11 | 회귀 15종 (코드 무변경 확인용) | `scripts/run_all_tests.sh` → `RESULT: 15/15 통과` |
| 12 | 공개 레포 규칙 — 문서 추가 줄에 개인 절대경로·맥 이름·`.env` 값 없음 | 게이트 통과 + verifier |
| 13 | push 안 함 | `git status -sb` 에 `ahead` |

## 관찰 (verifier 범위 밖 — CW 판정)

- 11-01 17:30 첫 실제 실행: `pmset -g log` 에 17:30 시작 caffeinate `Summary`/`ClientDied` 한 쌍 · `wiki-ingest.log` 의 `WIKI_RESULT` 정상 · `wiki-ingest-err.log` 새 줄 없음.

## 하지 말 것

- `launchctl start`(수동 실행 — backfill 이 Gemini 무료 한도를 쓴다)
- 다른 plist 3개·`install-*.sh` 수정, `pmset` 설정 변경(`disablesleep` 금지)
- 시간 창 안·wiki-ingest 실행 중의 재로드
- `git add -A`, `git push`

## 롤백

```bash
launchctl unload ~/Library/LaunchAgents/com.irichgreen.wiki-ingest.plist
cp -p ~/Library/LaunchAgents/_disabled/com.irichgreen.wiki-ingest.plist.bak.v416 ~/Library/LaunchAgents/com.irichgreen.wiki-ingest.plist
launchctl load ~/Library/LaunchAgents/com.irichgreen.wiki-ingest.plist
git revert <CC-1031-B 커밋>     # push 뒤라면. push 전이면 git reset --soft HEAD~1
```

## 범위 밖

- 덮개를 닫은 잠자기(Clamshell) — 소프트웨어로 안전하게 막지 않는다(v4.15 와 같음)
- `server.js` `/api/master-ingest` 수동 실행 경로의 caffeinate
- brew 자동 업그레이드 차단·node 버전 고정 — 필요하면 대표님 결정 뒤 별도 지시서
