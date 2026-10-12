# 작업지시서 — 레포 이름 변경: Youtube_Notion_Grap → AI_Wiki_Pipeline (2026-10-13)

> 실행: Claude Code · 보고는 한국어로 · **git push 는 하지 않는다**(검증 후 별도 지시)
> 패치: `docs/tasks/patches/2026-10-13-rename-ai-wiki-pipeline.patch`
> sha256 `e6ba2d5d20f25b59bd5312b0e663c3d75cc722bdafe2c7d6ea5571e2a7b68c23`

## 1. 배경

v4.0(2026-10-11)에서 노션을 뺐는데 이름에는 Notion 이 남아 있다. 폴더는 `Youtube_Notion_Grap`, GitHub 은 `YouTube_Notion_Grab` 으로 철자도 서로 다르다.
폴더와 GitHub 을 둘 다 **`AI_Wiki_Pipeline`** 으로 바꾼다.

- 코드에는 레포 절대경로가 없다(상대 경로·`__dirname`). 코드 안의 절대경로는 Vault 경로뿐이고 이번에 바꾸지 않는다.
- 바꿀 대상은 레포 밖 맥 설정 4종 + 레포 안 문서·스크립트 13개 파일이다.
- GitHub 저장소 이름은 대표님이 웹에서 **먼저** 바꿔 둔다(옛 주소는 GitHub 이 새 주소로 넘겨 준다).
- 같이 정리: crontab 의 죽은 줄. 08-17 이전 경로(`~/Documents/Claude/Youtube_Notion_Grap`, 지금 없음)에서 은퇴한 `migrate_classify.js` 를 매일 09:00 에 돌리게 돼 있어 두 달째 매일 실패하고 있다.

## 2. 범위

| 구분 | 대상 | 방법 |
|---|---|---|
| 레포 밖 | `~/Library/LaunchAgents/com.irichgreen.{server,ytsummarizer,wiki-ingest,wiki-lan}.plist` (각 2곳 = 8곳) | sed 치환 + `plutil -lint` + 레포 원본과 대조 |
| | `~/Library/Scripts/rotate_extra_logs.sh` 의 `YTDIR` (1곳) | sed 치환 + `bash -n` |
| | Claude Code MCP `wiki-search` (사용자 범위, `~/.claude.json`) | `claude mcp remove` → `claude mcp add -s user` |
| | crontab 의 `migrate_classify.js` 줄 (1줄) | 그 줄만 빼고 다시 등록 |
| | `<REPO_ROOT>/.claude/settings.local.json` (gitignore, 권한 규칙 1줄) | sed 치환 |
| 레포 안 | 패치 13개 파일: plist 원본 4 · `install-server.sh`·`install-scheduler.sh` sed 패턴 · `package.json` 이름 · `wiki_mcp.js`·`gas/sheet_mirror.gs` 주석 · `README.md`(머리 안내·구조도·상세 이력 1행) · `CLAUDE.md`·`AGENTS.md`(경로·이력 + 낡은 줄 3곳) · `docs/cowork-project-instructions.md`(v2.5 사본 → 안내문) | `git apply` 후 커밋 1건 |
| 원격 | `git remote` | `set-url` 만. push 없음 |

## 3. 바꾸지 않는 것 (범위 밖)

- `docs/tasks/` 의 옛 지시서·패치(기록, 패치를 고치면 sha256 이 깨진다), `legacy_scripts/`.
- Vault 경로, 장부 `data/`, `.env`(레포 이름 0건), launchd 라벨(`com.irichgreen.*`), 로그 위치(`~/Library/Logs/irichgreen/`).
- 프론트매터 키 `notion_id`, `VALID_NOTION_TAGS` — 이름에 notion 이 있어도 wiki_ingest·검색 인덱스 상태가 묶여 있다.
- 구글 시트 미러 웹앱(배포본) — 주석만 바뀌므로 재배포하지 않는다.
- 다른 프로젝트(`2nd_Brain`·`Notion_Archive` 등)의 옛 이름 언급.
- 스킬 `kakao-tips-update` 의 경로 — Cowork 가 이동 판정 뒤 따로 고친다.

## 4. 사전 조건 (게이트 — 하나라도 어긋나면 아무것도 바꾸지 말고 멈춰서 보고)

모든 명령은 맥 네이티브 셸. git 은 `--no-optional-locks`.
`OLD`·`NEW` 는 지시문 본문에서 받은 실제 절대경로다(`OLD = <Projects 폴더>/Youtube_Notion_Grap`, `NEW = <Projects 폴더>/AI_Wiki_Pipeline`).
**셸 변수는 명령 사이에 유지되지 않을 수 있으니, 아래 모든 코드 블록은 맨 앞에 `OLD=…; NEW=…; BK=~/rename_backup_20261013` 을 다시 정의하고 실행한다.**
**Claude Code 는 레포 밖(Projects 폴더)에서 띄운 세션으로 실행한다.** 레포 안에서 띄운 세션이면 S3(이동) 뒤 셸이 사라진 폴더를 물고 있어 명령·롤백이 실패할 수 있다 — 그 경우 G0 에서 멈추고 보고한다.

```bash
pwd                                          # G0 기대: Projects 폴더 또는 ~ (레포 안이면 멈춤)
date +%H%M                                   # G1 기대: 0625~1030 · 1225~1600 · 1825~2230 안 (다음 정시까지 60분 이상 남김 — 데몬이 내려간 동안의 정시 실행·17:30 wiki-ingest 는 그냥 빠진다)
pgrep -fl 'scheduler\.js|wiki_ingest\.py|sync_obsidian\.py|kakao_ingest\.py|sheet_mirror\.py|backup_library\.py'   # G2 기대: 출력 없음
cd "$OLD" && git --no-optional-locks rev-parse --short HEAD          # G3 기대: e56f620
git --no-optional-locks status --porcelain                           # G4 기대: 정확히 두 줄
#   ?? docs/tasks/2026-10-13-rename-ai-wiki-pipeline.md
#   ?? docs/tasks/patches/2026-10-13-rename-ai-wiki-pipeline.patch
shasum -a 256 docs/tasks/patches/2026-10-13-rename-ai-wiki-pipeline.patch   # G5 기대: 머리의 sha256 과 같음
git --no-optional-locks apply --check docs/tasks/patches/2026-10-13-rename-ai-wiki-pipeline.patch && echo "G6 OK"
git ls-remote https://github.com/iRG-AI/AI_Wiki_Pipeline.git refs/heads/main   # G7 기대: e56f620… (= 대표님이 GitHub 이름을 바꿔 둠)
[ -e "$NEW" ] && echo "G8 있음(멈춤)" || echo "G8 없음"                       # G8 기대: 없음
for n in server ytsummarizer wiki-ingest wiki-lan; do echo "$n $(grep -c "$OLD" ~/Library/LaunchAgents/com.irichgreen.$n.plist)"; done   # G9 기대: 각 2
crontab -l | grep -c 'migrate_classify.js'; crontab -l | grep -vc '^[[:space:]]*#'   # G10 기대: 1 · 2
grep -l Youtube_Notion_Grap ~/Library/LaunchAgents/*.plist ~/Library/Scripts/* ~/.zshrc ~/.zprofile ~/.claude/settings.json 2>/dev/null
#   G11 기대: 정확히 5개 — com.irichgreen.{server,wiki-ingest,wiki-lan,ytsummarizer}.plist + rotate_extra_logs.sh
#   (다른 파일이 나오면 멈추고 보고. com.irichgreen.log_rotate 는 03:50 실행이라 G1 시간대와 겹치지 않는다)
```

### 실패 규칙 (모든 단계 공통)

- **G0~G11 실패** → 아무것도 바꾸지 않은 상태이므로 그대로 멈추고 보고.
- **S2~S10 중 기대와 다른 줄** → 데몬을 내려 둔 채 멈추지 말고 **즉시 7절 롤백** 후 보고(롤백 결과 포함).
- **S11 이후 기대와 다른 줄** → 데몬은 올라와 있으므로 그 자리에서 멈추고 보고(추측으로 고치지 않는다).

## 5. 실행 순서

### S1. 백업 (레포 밖에 둔다)

```bash
BK=~/rename_backup_20261013; mkdir -p "$BK" ~/Library/LaunchAgents/_disabled
sqlite3 "$OLD/data/library.db" ".backup '$BK/library.db'" && sqlite3 "$BK/library.db" "pragma integrity_check"   # 기대: ok (이동 전 장부 스냅샷)
cp -p ~/.claude.json "$BK/claude.json"
for n in server ytsummarizer wiki-ingest wiki-lan; do cp -p ~/Library/LaunchAgents/com.irichgreen.$n.plist ~/Library/LaunchAgents/_disabled/com.irichgreen.$n.plist.bak.20261013; done
cp -p ~/Library/Scripts/rotate_extra_logs.sh "$BK/rotate_extra_logs.sh"
crontab -l > "$BK/crontab.txt"
claude mcp get wiki-search > "$BK/mcp-wiki-search.txt" 2>&1
ls -la ~/Library/LaunchAgents/_disabled/*.bak.20261013 "$BK"
```

### S2. 데몬 4개 내리기

```bash
date +%H%M        # 다시 확인: G1 시간대 안이어야 한다(백업·확인에 시간이 걸렸을 수 있다). 벗어났으면 여기서 멈추고 보고
for n in server ytsummarizer wiki-ingest wiki-lan; do launchctl unload ~/Library/LaunchAgents/com.irichgreen.$n.plist; done
launchctl list | grep -E 'com\.irichgreen\.(server|ytsummarizer|wiki-ingest|wiki-lan)$'   # 기대: 출력 없음
lsof -nP -iTCP:3000 -sTCP:LISTEN; lsof -nP -iTCP:3100 -sTCP:LISTEN                      # 기대: 출력 없음
```

### S3. 폴더 이동

```bash
cd "$(dirname "$OLD")" && mv Youtube_Notion_Grap AI_Wiki_Pipeline
[ -d "$NEW" ] && [ ! -e "$OLD" ] && echo "이동 OK"
cd "$NEW" && sqlite3 "file:data/library.db?mode=ro" "select count(*) from videos; select count(*) from tips;"   # 기대: 2999 이상 · 135 이상
```

- 이 뒤로는 **모든 명령을 `cd "$NEW" && …` 로 시작한다**(셸의 현재 폴더가 옛 이름을 가리킬 수 있다).
- 같은 디스크 안의 이동이라 하드링크·장부·`.env` 가 그대로 따라간다.

### S4. 패치 적용 + 회귀 테스트

```bash
cd "$NEW" && git --no-optional-locks apply docs/tasks/patches/2026-10-13-rename-ai-wiki-pipeline.patch
git --no-optional-locks diff --stat | tail -1     # 기대: 13 files changed, 36 insertions(+), 250 deletions(-)
for n in server ytsummarizer wiki-ingest wiki-lan; do plutil -lint com.irichgreen.$n.plist; done
/opt/homebrew/bin/node scripts/test_scheduler_guards.js | tail -1        # 29/29 PASS
/opt/homebrew/bin/python3 scripts/test_notion_to_sqlite.py | tail -1     # 37/37 PASS
/opt/homebrew/bin/python3 scripts/test_kakao_ingest.py | tail -1         # 18/18 PASS
/opt/homebrew/bin/python3 scripts/test_sync_obsidian.py | tail -1        # 23/23 PASS
/opt/homebrew/bin/python3 scripts/test_sheet_mirror.py | tail -1         # 45/45 PASS
/opt/homebrew/bin/python3 scripts/test_build_wiki_index.py | tail -1     # 10/10 PASS
/opt/homebrew/bin/python3 scripts/test_backup_library.py | tail -1       # 50/50 PASS
```

하나라도 기대와 다르면 **S2 상태(데몬 내려간 채)에서 멈추지 말고 7절 롤백** 후 보고한다.

### S5. 설치된 plist 4개

```bash
for n in server ytsummarizer wiki-ingest wiki-lan; do
  f=~/Library/LaunchAgents/com.irichgreen.$n.plist
  sed -i '' "s|$OLD|$NEW|g" "$f"
  echo "$n NEW=$(grep -c "$NEW" "$f") OLD=$(grep -c "$OLD" "$f")"     # 기대: NEW=2 OLD=0
  plutil -lint "$f"
done
cd "$NEW" && for n in server ytsummarizer wiki-lan wiki-ingest; do diff <(plutil -convert xml1 -o - ~/Library/LaunchAgents/com.irichgreen.$n.plist) <(plutil -convert xml1 -o - com.irichgreen.$n.plist) >/dev/null && echo "$n 같음" || echo "$n 다름"; done   # 기대: 4개 모두 같음
```

### S6. 로그 회전 스크립트

```bash
f=~/Library/Scripts/rotate_extra_logs.sh
sed -i '' 's|^YTDIR="$HOME/Documents/Claude/Projects/Youtube_Notion_Grap"$|YTDIR="$HOME/Documents/Claude/Projects/AI_Wiki_Pipeline"|' "$f"
grep -n '^YTDIR=' "$f"; bash -n "$f" && echo "문법 OK"     # 기대: AI_Wiki_Pipeline · 문법 OK
diff ~/rename_backup_20261013/rotate_extra_logs.sh "$f" | grep -c '^[<>]'     # 기대: 2 (YTDIR 한 줄만 바뀜)
```

6행 주석의 옛 이름은 그대로 둔다(설명문).

### S7. Claude Code MCP `wiki-search` 재등록

```bash
claude mcp remove wiki-search -s user
claude mcp add -s user wiki-search -- node "$NEW/wiki_mcp.js"     # 기존 등록과 같은 형태(command "node", env 없음) — 경로만 바뀐다
claude mcp get wiki-search        # 기대: Args 에 $NEW/wiki_mcp.js
```

- 이미 떠 있는 다른 Claude Code 세션의 `wiki-search` 는 옛 경로를 물고 있으니 그 세션들은 재시작해야 한다(보고에 한 줄).

### S8. crontab 죽은 줄 삭제

```bash
crontab -l | grep -v 'migrate_classify.js' | crontab -
crontab -l       # 기대: notion-schedule 의 run-monthly.sh 한 줄만 (매월 25일 09:00)
```

### S9. 레포 로컬 설정 (gitignore)

```bash
cd "$NEW" && sed -i '' "s|$OLD|$NEW|g" .claude/settings.local.json && grep -c "$OLD" .claude/settings.local.json   # 기대: 0
```

### S10. 데몬 4개 올리기 + 확인

```bash
for n in server ytsummarizer wiki-ingest wiki-lan; do launchctl load ~/Library/LaunchAgents/com.irichgreen.$n.plist; done
sleep 5
launchctl list | grep -E 'com\.irichgreen\.(server|ytsummarizer|wiki-ingest|wiki-lan)$'   # server·wiki-lan 은 PID 숫자, 나머지 둘은 '-'
pgrep -fl "$NEW/(server|wiki_lan_server)\.js"                                               # 기대: 두 줄(server.js · wiki_lan_server.js), 둘 다 $NEW 경로
pgrep -fl "$OLD/" | grep -v 'wiki_mcp\.js'                                                    # 기대: 출력 없음 (이미 떠 있던 Claude Code 세션의 옛 wiki_mcp.js 는 허용 — 재시작 대상)
curl -s -o /dev/null -w '3000 %{http_code}\n' http://127.0.0.1:3000/wiki                    # 기대: 200
curl -s -o /dev/null -w '3100 %{http_code}\n' http://127.0.0.1:3100/wiki                    # 기대: 200
lsof -nP -iTCP:3000 -sTCP:LISTEN | tail -1                                                   # 기대: 127.0.0.1:3000 (0.0.0.0 아님)
grep -nE '바인딩:|허용 대역:' ~/Library/Logs/irichgreen/wiki-lan.log | tail -2               # 기대: `바인딩: 0.0.0.0:3100` + `허용 대역: …/24 + 루프백` ('미설정'·127.0.0.1 전용 문구 없음)
stat -f '%Sm' ~/Library/Logs/irichgreen/wiki-lan.log                                         # 기대: 방금 시각(재기동 로그가 새로 찍힘)
```

### S11. 읽기 전용 상태 확인

```bash
cd "$NEW"
/opt/homebrew/bin/python3 sheet_mirror.py --check | tail -1            # match true
/opt/homebrew/bin/python3 backup_library.py --status | tail -1         # local·drive 둘 다 ok
/opt/homebrew/bin/python3 scripts/notion_to_sqlite.py --verify | grep RESULT_JSON   # vault_missing 0
```

### S12. 커밋

```bash
cd "$NEW" && git add AGENTS.md CLAUDE.md README.md com.irichgreen.server.plist com.irichgreen.ytsummarizer.plist com.irichgreen.wiki-ingest.plist com.irichgreen.wiki-lan.plist docs/cowork-project-instructions.md gas/sheet_mirror.gs install-scheduler.sh install-server.sh package.json wiki_mcp.js docs/tasks/2026-10-13-rename-ai-wiki-pipeline.md docs/tasks/patches/2026-10-13-rename-ai-wiki-pipeline.patch
git commit -m "chore: 레포 이름 변경 Youtube_Notion_Grap → AI_Wiki_Pipeline (버전 유지)"
git --no-optional-locks status --porcelain      # 기대: 빈 출력
git --no-optional-locks show --stat HEAD | tail -1   # 기대: 15 files changed
```

커밋 메시지 끝에는 이 세션의 공동 작성자 표기 규칙을 따른다.

### S13. 원격 주소만 바꾸기 (push 없음)

```bash
cd "$NEW" && git remote set-url origin https://github.com/iRG-AI/AI_Wiki_Pipeline.git
git remote -v | head -1
git ls-remote origin refs/heads/main            # 기대: e56f620…
git --no-optional-locks status -sb | head -1     # 기대: ahead 1
```

### S14. (선택) Claude Code 대화 기록 이어가기

```bash
S=~/.claude/projects/-Users-<사용자>-Documents-Claude-Projects-Youtube-Notion-Grap
T=~/.claude/projects/-Users-<사용자>-Documents-Claude-Projects-AI-Wiki-Pipeline
[ -d "$S" ] && [ ! -e "$T" ] && cp -Rp "$S" "$T" && echo "복사 OK"
```

옛 폴더는 지우지 않는다. 실제 이름은 지시문 본문의 값을 쓴다. 이 세션은 Projects 폴더에서 떴으므로 복사 대상 폴더에 지금 쓰고 있는 세션은 없다.

## 6. 보고 (한국어)

게이트 G1~G10 결과, S2~S13 의 각 "기대" 줄에 대한 실제 출력, 커밋 해시, `git show --stat HEAD`, 백업 위치.
기대와 다른 줄이 있으면 4절 「실패 규칙」대로 한다(S2~S10 은 롤백 후, 그 밖은 그 자리에서 멈춰) — 추측으로 고치지 않는다.

## 7. 롤백

데몬이 내려간 뒤(S2 이후) 문제가 생기면 아래 순서로 원상 복구한다.

```bash
for n in server ytsummarizer wiki-ingest wiki-lan; do launchctl unload ~/Library/LaunchAgents/com.irichgreen.$n.plist 2>/dev/null; done
for n in server ytsummarizer wiki-ingest wiki-lan; do cp -p ~/Library/LaunchAgents/_disabled/com.irichgreen.$n.plist.bak.20261013 ~/Library/LaunchAgents/com.irichgreen.$n.plist; done
cd "$(dirname "$NEW")" && [ -d AI_Wiki_Pipeline ] && mv AI_Wiki_Pipeline Youtube_Notion_Grap
cd "$OLD" && git reset --mixed e56f620 && git checkout -- .   # 커밋·패치 적용을 되돌린다. 지시서·패치 파일은 untracked 로 남는다
git remote set-url origin https://github.com/iRG-AI/YouTube_Notion_Grab.git
cp -p ~/rename_backup_20261013/rotate_extra_logs.sh ~/Library/Scripts/rotate_extra_logs.sh
crontab ~/rename_backup_20261013/crontab.txt
claude mcp remove wiki-search -s user; claude mcp add -s user wiki-search -- node "$OLD/wiki_mcp.js"
sed -i '' "s|$NEW|$OLD|g" "$OLD/.claude/settings.local.json"
for n in server ytsummarizer wiki-ingest wiki-lan; do launchctl load ~/Library/LaunchAgents/com.irichgreen.$n.plist; done
```

GitHub 이름은 대표님이 웹에서 `YouTube_Notion_Grab` 으로 되돌린다(되돌리지 않아도 새 이름 주소로 push 가 된다).

## 8. 이후 (Cowork · 대표님)

- Cowork: 커밋 diff 대조 → push 지시(별도) → 첫 정시 실행 판정(`.run_state.json` 간격 6시간, `[직전 실행 점검]` 없음).
- 대표님: Cowork 연결 폴더를 새 경로로, claude.ai 프로젝트 이름·지침의 레포·GitHub 줄, 다른 Claude Code 세션 재시작.
- Cowork: 스킬 `kakao-tips-update` 경로 수정안, handoff 갱신. 백업 `~/rename_backup_20261013`·`_disabled/*.bak.20261013` 은 며칠 관찰 후 삭제.
