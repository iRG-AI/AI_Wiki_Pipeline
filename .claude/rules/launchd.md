---
paths:
  - "**/*.py"
  - "**/*.js"
  - "**/*.sh"
  - "**/*.plist"
  - "lib/**"
  - "scripts/**"
  - "gas/**"
  - "playlists.json"
---

# launchd 데몬 상세 (루트 CLAUDE.md 에서 이관 — 2026-11-11)

> 위 경로의 파일을 Read 하면 자동으로 읽힌다. 코드·plist·장부를 건드리기 전에는 직접 Read 해도 된다. launchd 조작 전에 읽는다. 루트 CLAUDE.md 와 어긋나면 **루트가 우선**한다. 아래는 옮기기 전 본문이다(글자 그대로).

| 라벨 | 실행 대상 | 스케줄 | 인터프리터 |
|------|-----------|--------|-----------|
| `com.irichgreen.server` | `server.js` (포트 3000) | `KeepAlive`, `RunAtLoad` — 상주 | `/opt/homebrew/bin/node` |
| `com.irichgreen.ytsummarizer` | `scheduler.js` (v4.15 `caffeinate -i` 로 감쌈) | 00 / 06 / 12 / 18시 | `/opt/homebrew/bin/node` |
| `com.irichgreen.wiki-ingest` | `wiki_ingest.py` (증분 + backfill + 재렌더, v4.16 `caffeinate -i` 로 감쌈) | 매일 17:30 | `/opt/homebrew/bin/python3` |
| `com.irichgreen.skill-review` | `skill_review.py` (v4.20 `caffeinate -i`) | 매일 08:30 | `/opt/homebrew/bin/python3` |
| `com.irichgreen.wiki-lan` | `wiki_lan_server.js` (포트 3100) | `KeepAlive`, `RunAtLoad`, `ThrottleInterval 60` — 상주 | `/opt/homebrew/bin/node` |

- **실제 동작하는 plist는 `~/Library/LaunchAgents/`에 있다.** 레포 루트의 plist 5개는 그 원본이며 모두 실경로(`<REPO_ROOT>` 의 절대경로)가 들어 있다. **원본은 설치본과 같게 유지한다** — 2026-10-12 대조에서 `wiki-ingest` 원본만 옛 값(03:00 · `/usr/bin/python3` · `--full`)이라 설치본(17:30 · Homebrew python3 · 증분)으로 맞췄다. 확인: `diff <(plutil -convert xml1 -o - ~/Library/LaunchAgents/<라벨>.plist) <(plutil -convert xml1 -o - <라벨>.plist)`. 예전에 `server`·`ytsummarizer` 두 개에 있던 `/Users/사용자명/youtube-notion-app` 플레이스홀더는 제거했다.
- **(v4.15) `com.irichgreen.ytsummarizer` 의 `ProgramArguments` 는 `/usr/bin/caffeinate -i /opt/homebrew/bin/node <REPO_ROOT>/scheduler.js` 다.** caffeinate 가 node 를 자식으로 띄우고 node 가 끝날 때까지 유휴 잠자기 방지 단언(`PreventUserIdleSystemSleep`)을 쥔다 — 배터리 설정이 `sleep 1`(1분)이라 덮개를 연 채 자리를 비우면 실행 도중 잠들 수 있었다. 종료 코드는 node 것을 그대로 돌려준다(10-16 실측). **덮개를 닫은 잠자기(Clamshell)·이미 잠든 맥은 막지 못한다**(10-15 12:00 실패 = 11:54 Clamshell Sleep, 배터리 36%) — 그 경우는 v4.2 알림과 다음 실행의 이어 처리로 버틴다. 강제로 막는 `pmset disablesleep` 은 가방 속 발열 위험이라 쓰지 않는다. `launchctl list` 의 PID 는 caffeinate 이고 `pgrep -f scheduler.js` 는 두 줄(caffeinate·node)이 나온다. 실행 중 확인: `pmset -g assertions | grep caffeinate`. `server.js` `/api/master-ingest` 로 띄운 수동 실행은 감싸지 않는다(범위 밖). caffeinate 를 빼지 말 것.
- **(v4.16) `com.irichgreen.wiki-ingest` 도 같다** — `/usr/bin/caffeinate -i /opt/homebrew/bin/python3 <REPO_ROOT>/wiki_ingest.py`. 실행 중 확인 `pmset -g assertions | grep caffeinate`, 지난 실행은 `pmset -g log | grep "17:3.*caffeinate"`(macOS 로그에는 `Summary`·`ClientDied` 로 찍힌다 — 다른 앱도 caffeinate 를 수시로 띄우므로 시작 시각으로 가린다). caffeinate 를 빼지 말 것.
- 각 plist는 `ProgramArguments`·`WorkingDirectory` **2곳에 절대경로**가 박혀 있다. 경로 변경 시 10군데(5개 × 2) 동기화 + `plutil -lint` + unload/load.
- **레포 경로 자체를 바꿀 때 함께 고칠 맥 설정(레포 밖):** 설치된 plist 5개, `~/Library/Scripts/rotate_extra_logs.sh` 의 `YTDIR`, Claude Code MCP `wiki-search` 등록(`~/.claude.json` 사용자 범위 — `claude mcp remove`/`add -s user`), 스킬 `kakao-tips-update` 의 경로. 절차·검증은 `docs/tasks/2026-10-13-rename-ai-wiki-pipeline.md`.
- `install-server.sh`·`install-scheduler.sh`는 plist를 `~/Library/LaunchAgents/`로 복사하며 **sed로 이 실경로를 `$APP_DIR`로 치환**한다. 레포 경로를 바꾸면 두 스크립트의 sed 패턴도 같이 고쳐야 치환이 동작한다. `install-wiki-ingest.sh` 는 치환 없이 그대로 복사한다(원본 = 설치본). `deploy.sh` 는 옛 일괄 업로드 스크립트라 쓰지 않는다.
- `com.irichgreen.server`는 상주 프로세스라 **코드를 고쳐도 재기동 전까지 반영되지 않는다.**
- `com.irichgreen.wiki-lan`의 로그(`wiki-lan.log`)는 **`rotate_extra_logs.sh`에 넣지 않는다.** 상주형이라 rename 회전이 안전하지 않다. 대신 서버가 기동·차단·오류만 찍는다.
- **macOS 방화벽의 수신 허용은 node 실행 파일의 실제 경로(Cellar 버전 폴더)에 걸린다**(2026-10-03 실측: 허용 목록에 옛 버전 경로만 남아 있었다). `brew upgrade node` 후에는 경로가 바뀌므로 `wiki-lan`이 살아 있어도 가족 PC에서만 접속이 막힐 수 있다 — 이 맥에서의 `curl`은 정상으로 보일 수 있으니 판정은 다른 기기로 한다. 재기동 + 방화벽 재허용이 한 세트다.
- **`brew upgrade` 후에는 상주 데몬을 반드시 재기동한다.** 데몬은 기동 시점의 Cellar 경로를 물고 도는데, 업그레이드로 그 폴더가 삭제되면 이후 지연 import가 전부 실패한다. 이미 로드된 모듈은 멀쩡히 동작해 **부분 실패로 나타나므로 알아채기 어렵다.** (2026-08-17 자매 프로젝트 실장애)
- **`brew upgrade` 뒤 점검 순서 (2026-10-30 사건):** 의존 라이브러리(simdjson 등)만 올라가도 node 가 `dyld: Library not loaded` 로 기동 즉시 죽을 수 있다. 정시 실행은 `scheduler.log` 에 아무것도 남기지 않고(`~/Library/Logs/irichgreen/ytsummarizer-err.log` 에만) 다음 실행의 `[직전 실행 점검]` 간격 경고로만 드러나며, 상주 데몬은 KeepAlive 재시작 실패를 반복한다(`launchctl list` 종료 코드 -6·78). 순서: ① `grep -l dyld ~/Library/Logs/irichgreen/*-err.log` ② `/opt/homebrew/bin/node -v` · `/opt/homebrew/bin/python3 -V` ③ `launchctl list | grep irichgreen` ④ 상주 데몬 재기동 ⑤ 방화벽 node Cellar 경로 재허용(가족 PC 로 판정) ⑥ `scripts/run_all_tests.sh`. node 26.13 부터 로그 날짜가 `2026/10/31 오후 12:00:05` 꼴이다(이전 `2026. 10. 31. 오후 …`) — 날짜로 grep 하는 명령은 두 꼴을 다 쓴다.
