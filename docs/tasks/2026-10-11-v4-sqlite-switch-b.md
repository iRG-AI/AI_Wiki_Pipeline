# v4.0 2단계-b — 읽기 전환 (sync_obsidian → 로컬 장부) + 노션 프록시 제거 + 은퇴 스크립트 이동

> 지시 번호는 발행할 때 채팅으로 준다(예: `[CC-1012-A]`). 보고는 한국어로.
> 선행: 2-a `docs/tasks/2026-10-11-v4-sqlite-switch-a.md` 커밋 + Cowork 판정. **스케줄러(`ytsummarizer`)는 2-a 부터 내려가 있다.**
> 이 지시서 끝(4-10)에서 스케줄러를 다시 올린다.

## 1. 배경

2-a 로 쓰기가 장부(`data/library.db`)로 옮겨졌다. 남은 노션 의존은 읽기다.

- `sync_obsidian.py` 가 노션 DB 를 전량 조회해 노트를 만들고, tags 를 맞추고, 고아를 격리한다.
- `server.js` 의 `/notion-proxy`·`/test-notion` 과 `index.html` 의 「▶ 선택 실행」(브라우저가 직접 요약해 노션에 저장)이 남아 있다.
- 노션 전제 일회성 스크립트 5개가 레포 루트에 있다.

## 2. 설계 결정 (Cowork 확정 — 바꾸지 말 것)

| 항목 | 결정 |
|---|---|
| 원본 | `sync_obsidian.py` 는 `lib/library_db.open_existing(readonly=True)` 로 장부를 **읽기 전용**으로 연다. 못 열면(없음·버전 다름) Vault 를 하나도 건드리지 않고 `RESULT_JSON.error` 를 찍고 exit 1. 노션 호출 0. |
| 노트 모양 | 노션 시절 노트와 같다: 프론트매터(키·순서 동일) + 빈 줄 2개 + `**▶ 영상 보기: **URL` + `---` + 장부 `summary`(Gemini 요약 원문 마크다운). 파일명·폴더 규칙 동일(`채널_제목_YYYYMMDD.md`, 첫 topic 폴더). `channel` 의 큰따옴표만 작은따옴표로 바꾼다(title 과 같은 처리, 새 노트에만 영향). |
| 프론트매터 한정 | `notion_id`·`video_url` 은 **맨 앞 프론트매터 안의 것만** 센다(`fm_value`). `schema.md` 본문 예시를 영상 노트로 오인하던 문제를 원천 차단. tags 교체도 프론트매터 안에서만. |
| tags | 장부 `topics` 와 맞춘다. 1단계 중복 그룹의 topics 합집합 때문에 첫 실행에서 몇 건 바뀐다(10-11 스냅샷 실측 6). |
| 영상 고아 | 살아 있는 id = 장부 `videos`. `videos_dup` 을 가리키던 노트는 고아로 격리된다(의도, 10-11 실측 0). **3중 안전장치 그대로**(0건·50% 미만·40% 초과). |
| 꿀팁 고아 | 장부 `tips` 에 없는 꿀팁 노트는 **옮기지 않고 보고만**(`RESULT_JSON.tips_orphans`). 꿀팁 삭제는 장부를 직접 고칠 때만 생기는 드문 일이고, 꿀팁 폴더는 영상 고아 안전장치의 분모 밖이다. |
| `--dry-run` | 신설. Vault·장부·log.md 를 하나도 쓰지 않고 할 일(tags·신규·고아 후보·건너뜀·꿀팁)만 센다. 재구성·인제스트·인덱스도 건너뜀. |
| `RESULT_JSON` | 기존 키(`added`·`tips_added`·`tags_updated`·`orphans_removed`·`rebuilt`·`elapsed`·`error`) 그대로 + `orphans_candidates`·`orphans_blocked`·`tips_orphans`·`skipped_same_path`·`skipped_same_url`. scheduler.js 파싱 무변경. |
| 노션 헬퍼 | `block_to_md`·`rich_to_md` 는 남긴다 — `scripts/notion_to_sqlite.py`(은퇴 대기)가 import 한다. 지시서 3 에서 함께 정리. |
| `server.js` | `/notion-proxy/*`·`/test-notion`·`callNotion`·경로 화이트리스트·`x-notion-token` CORS 헤더 제거. `/api/config` 에서 `ntToken`·`ntDb` 제거. `PATCH` 메서드 허용 제거. |
| `index.html` | 「▶ 선택 실행」은 숨김(다른 코드가 버튼을 참조) + 누르면 안내 alert. 노션 캐시·저장·토큰 테스트·브라우저 재생목록 처리 함수 삭제. 설정 화면의 노션 토큰·DB 칸 삭제. 제목·안내 문구에서 Notion → 로컬 장부. localStorage 키 `yt2notion` 은 그대로(저장된 설정 보존). |
| 은퇴 | `migrate_classify.js`·`check_duplicates.py`·`cleanup_duplicates.py`·`fix_nfc_topics.js`·`notion_to_obsidian.js` → `legacy_scripts/` (`git mv`, 내용 무변경) + `legacy_scripts/README.md`. |
| 기타 | `build_obsidian_wiki.py` 가 만드는 `schema.md` 에 `notion_id` 의미 설명 2줄, 수동 명령어 `cleanup_duplicates.py` → `sync_obsidian.py --dry-run`. `scheduler.js` 주석 1줄. `CLAUDE.md`·`AGENTS.md` 해당 절. |

## 3. 파일 — 패치 1개

`docs/tasks/patches/2026-10-11-v4-sqlite-switch-b.patch` (기준 = 2-a 패치 적용 후)

```
sha256  e14f662bd7840cadf5491c9e67152c734523291be3be049d9de6c1f4fbb2735e
```

| 파일 | 변경 |
|---|---|
| `sync_obsidian.py` | 노션 조회 → 장부 읽기, 노트 생성·tags·고아·꿀팁을 장부 기준으로, 프론트매터 한정, `--dry-run`, `main()` 함수화(테스트용) |
| `scripts/test_sync_obsidian.py` | 신규 **23**건 (임시 Vault·임시 장부, 하위 단계는 가짜 — 실제 Vault 안 건드림) |
| `scripts/test_notion_to_sqlite.py` | `vault_ignored` 기대값 1 → 0 (프론트매터 한정의 결과) — 37/37 유지 |
| `server.js` · `index.html` | 노션 프록시·브라우저 직접 처리 제거 |
| `legacy_scripts/*` | 5개 이동 + README |
| `build_obsidian_wiki.py` · `scheduler.js` · `CLAUDE.md` · `AGENTS.md` | 위 표 |

패치의 문맥 줄에 `sync_obsidian.py` 의 기존 `VAULT = …` 줄(개인 절대경로)이 들어 있다 — 이미 레포에 있는 줄이며 새로 쓰는 경로는 없다.

### Cowork 사전 검증 (2026-10-11 22:50)

- 샌드박스: `c1025dc` 사본 + 2-a 패치 + 이 패치 → `git apply --check` 통과, 테스트 16/16 · 37/37 · 17/17 · 23/23. 결과 트리가 Cowork 작업본과 바이트 동일.
- 변이 시험(`test_sync_obsidian.py`): 프론트매터 한정 제거 · 안전장치 2 제거 · 안전장치 3 제거 · dry-run 에서 tags 실제로 쓰기 · 노트 첫 빈 줄 제거 — 각각 FAIL 확인.
- **맥 네이티브**(23:00, `/tmp` 임시 사본): 2-a + 2-b 패치 적용 후 데몬 node v26.10.0 · `/opt/homebrew/bin/python3` 로 16/16 · 37/37 · 17/17 · 23/23.
- **실데이터 dry-run**(맥, 10-11 18:21 장부 사본 + 실제 Vault 읽기만, `Claude outputs/` 의 임시 사본에서 실행):
  `videos 2,986 · tips 135 · tags_updated 6 · 신규 영상 1(우석지니 10-11 영상) · 고아 후보 0 · 건너뜀 0/0 · 신규 꿀팁 0 · 꿀팁 고아 0 · 2초`.

## 4. 실행

### 4-0. 시간

17:15~17:45(wiki-ingest 가 Vault 를 읽는 중) 은 피한다. 스케줄러가 내려가 있으므로 00·06·12·18시는 상관없다. 단 4-9 수동 실행이 그 시각에 걸리면 4-10 을 그 뒤로 미룬다.

### 4-1. 시작 상태 (읽기만)

```bash
cd <REPO_ROOT>
git log -2 --format='%h %s'          # 맨 위가 2-a 커밋 (v4.0 2단계-a: …)
git status --short                    # ?? 2-b 지시서·패치만
launchctl list | grep ytsummarizer || echo "ytsummarizer 내려감"
pgrep -fl 'scheduler\.js|sync_obsidian\.py|wiki_ingest\.py|kakao_ingest\.py'
shasum -a 256 docs/tasks/patches/2026-10-11-v4-sqlite-switch-b.patch
git apply --check docs/tasks/patches/2026-10-11-v4-sqlite-switch-b.patch && echo APPLY-OK
/opt/homebrew/bin/python3 scripts/notion_to_sqlite.py --verify > /tmp/v4b-verify0.log 2>&1; echo "exit=$?"; grep RESULT_JSON /tmp/v4b-verify0.log
```

멈춤 조건: HEAD 가 2-a 커밋이 아님 · ytsummarizer 가 올라가 있음 · pgrep 출력 있음 · sha 불일치 · APPLY-OK 없음 · verify `ok` 가 true 아님 또는 `switched_at` 이 null.
verify 에서 `videos`·`vault_in_videos` 를 적어 둔다 → **D = videos − vault_in_videos** (장부에만 있는 영상).

### 4-2. 패치 적용

```bash
git apply docs/tasks/patches/2026-10-11-v4-sqlite-switch-b.patch
git status --short
```

기대: `M` AGENTS.md · CLAUDE.md · build_obsidian_wiki.py · index.html · scheduler.js · scripts/test_notion_to_sqlite.py · server.js · sync_obsidian.py,
`D` 루트의 5개 + `??` `legacy_scripts/` 의 같은 5개·README.md · scripts/test_sync_obsidian.py.
(`git apply` 는 이름 바꾸기를 삭제+생성으로 둔다. 커밋 때 `git add -A` 범위로 rename 이 잡힌다 — 5절.)

### 4-3. 회귀 테스트 (네트워크 0회, 실제 Vault 무관)

```bash
/opt/homebrew/bin/node scripts/test_scheduler_guards.js | tail -1      # 16/16
/opt/homebrew/bin/python3 scripts/test_notion_to_sqlite.py | tail -1   # 37/37
/opt/homebrew/bin/python3 scripts/test_kakao_ingest.py | tail -1       # 17/17
/opt/homebrew/bin/python3 scripts/test_sync_obsidian.py | tail -1      # 23/23
grep -c "api.notion.com\|notion_call\|load_all_notion_pages" sync_obsidian.py server.js index.html   # 0 / 0 / 0
```

### 4-4. 실데이터 dry-run (Vault·장부 무변경)

```bash
/opt/homebrew/bin/python3 sync_obsidian.py --dry-run > /tmp/v4b-dry.log 2>&1; echo "exit=$?"
tail -40 /tmp/v4b-dry.log
```

게이트 (`RESULT_JSON`):

| 값 | 기대 | 근거 |
|---|---|---|
| exit | 0 | |
| `videos` | = 4-1 verify `videos` | |
| `orphans_candidates` · `orphans_blocked` | 0 · `""` | verify `vault_in_dup` 0 |
| `tips_orphans` | 0 | 1단계에서 잔여 꿀팁 격리함 |
| `added − tips_added` + `skipped_same_path` + `skipped_same_url` | = **D** | 장부에만 있는 영상 = 새 노트 + 건너뜀 |
| `skipped_same_path + skipped_same_url` | ≤ 3 | |
| `tags_updated` | ≤ 30 | 10-11 실측 6 |
| `tips_added` | ≤ 20 | 2-a 4-7 카톡 신규분 |

하나라도 벗어나면 **멈추고 보고**(실행하지 않는다). Cowork 가 Opus 조사 지시를 따로 낸다.

### 4-5. 실행

```bash
nohup /opt/homebrew/bin/python3 sync_obsidian.py > /tmp/v4b-sync.log 2>&1 &
echo "pid=$!"
```

60초 간격으로 `pgrep -f 'sync_obsidian\.py' || echo 끝남` 확인, 최대 30분(신규 노트가 있으면 Wiki 재구성 → wiki_ingest(Gemini) → 검색 인덱스가 이어진다). 끝나면:

```bash
grep -E "장부:|tags 갱신|신규 영상:|고아|신규 꿀팁|Wiki 재구성|Wiki Ingest|검색 인덱스|❌|RESULT_JSON" /tmp/v4b-sync.log
```

게이트: `RESULT_JSON` 의 `added`·`tips_added`·`tags_updated` = 4-4 와 같음 · `orphans_removed` = 0 · `error` = `""` · `rebuilt` = true(변경이 있었다면).
`❌ Wiki Ingest 오류` 가 Gemini 429 때문이면 실패가 아니다(17:30 wiki-ingest 가 이어서 한다) — 그대로 보고.

### 4-6. 멱등 + 대조

```bash
/opt/homebrew/bin/python3 sync_obsidian.py --dry-run > /tmp/v4b-dry2.log 2>&1; echo "exit=$?"; grep RESULT_JSON /tmp/v4b-dry2.log
/opt/homebrew/bin/python3 scripts/notion_to_sqlite.py --verify > /tmp/v4b-verify1.log 2>&1; echo "exit=$?"; grep RESULT_JSON /tmp/v4b-verify1.log
```

기대: dry-run `added 0 · tags_updated 0 · orphans_candidates 0`. verify `ok true` · `vault_in_videos` = 4-1 값 + (4-5 `added − tips_added`) · `videos − vault_in_videos` = 4-4 의 건너뜀 합계.

### 4-7. 새 노트 모양 확인 (읽기만)

4-5 로그의 `[1/…] <폴더>/<파일>.md` 한 개를 골라:

```bash
head -16 "$HOME/Documents/Obsidian/AI LLM Wiki/AI LLM Wiki/<폴더>/<파일>.md"
```

기대: `title`·`channel`·`tags`·`upload_date`·`view_count`·`subscriber_count`·`video_url`·`thumbnail`·`status`·`notion_id` 순서, `---` 뒤 빈 줄 2개, `**▶ 영상 보기: **https://www.youtube.com/watch?v=…`, `---`, `## 영상 개요`. `notion_id` 는 노션에서 옮긴 영상이면 노션 page id, 2-a 이후 저장분이면 uuid4.
(경로는 보고에 적지 말고 출력만 붙인다.)

### 4-8. server 재기동 + 확인

```bash
launchctl kickstart -k gui/$(id -u)/com.irichgreen.server
sleep 3
curl -s -o /dev/null -w '/ %{http_code}\n' http://127.0.0.1:3000/
curl -s http://127.0.0.1:3000/ | grep -c 'notion-proxy\|testNotion\|ntToken'
curl -s -X POST -o /dev/null -w 'proxy %{http_code}\n' http://127.0.0.1:3000/notion-proxy/v1/pages -d '{}'
curl -s -o /dev/null -w 'test-notion %{http_code}\n' http://127.0.0.1:3000/test-notion
curl -s http://127.0.0.1:3000/api/config | /opt/homebrew/bin/python3 -c "import json,sys; print(sorted(json.load(sys.stdin)))"
curl -s -o /dev/null -w 'wiki %{http_code}\n' http://127.0.0.1:3000/wiki
```

기대: `/ 200` · `0` · `proxy 404` · `test-notion 404` · `['gmKey', 'telegram', 'ytKey']` · `wiki 200`. (`/api/config` 값은 출력하지 않는다 — 키 목록만.)

### 4-9. 스케줄러 1회 수동 실행 (전 구간: 장부 → 카톡 → 새 동기화)

```bash
nohup /opt/homebrew/bin/node scheduler.js > /tmp/v4b-run.log 2>&1 &
echo "pid=$!"
```

60초 간격으로 `pgrep -f 'node scheduler.js' || echo 끝남`, 최대 40분. 끝나면:

```bash
grep -E "장부 캐시 완료|장부 로드 실패|완료! 저장|카톡 인제스트|Obsidian 동기화|❌" /tmp/v4b-run.log
```

게이트: `장부 캐시 완료` 있음 · `오류: 0개` · `✅ Obsidian 동기화 완료! 추가: n개` 있음(n = 이번 저장 S + 카톡 신규) · `❌` 없음(Gemini 429 로 인한 Wiki Ingest 오류는 예외 — 보고만).

### 4-10. 스케줄러 다시 올림

```bash
plutil -lint ~/Library/LaunchAgents/com.irichgreen.ytsummarizer.plist
launchctl load ~/Library/LaunchAgents/com.irichgreen.ytsummarizer.plist
launchctl list | grep ytsummarizer
```

기대: `OK` · 목록에 `com.irichgreen.ytsummarizer`(PID 칸 `-`, 상태 0).

## 5. 커밋 (push 하지 않음)

```bash
git add -A sync_obsidian.py server.js index.html build_obsidian_wiki.py scheduler.js CLAUDE.md AGENTS.md \
           scripts/test_sync_obsidian.py scripts/test_notion_to_sqlite.py legacy_scripts \
           migrate_classify.js check_duplicates.py cleanup_duplicates.py fix_nfc_topics.js notion_to_obsidian.js \
           docs/tasks/2026-10-11-v4-sqlite-switch-b.md docs/tasks/patches/2026-10-11-v4-sqlite-switch-b.patch
git status --short            # 남는 것 없음 (data/ 는 ignore)
git commit -m "v4.0 2단계-b: 읽기 전환 — sync_obsidian 이 로컬 장부를 읽는다, 노션 프록시 제거, 노션 전제 스크립트 은퇴"
git show --stat -M HEAD       # 5개가 rename(100%) 으로 보여야 한다
```

README 는 건드리지 않는다(v4.0 행은 지시서 3). push 는 Cowork 판정 뒤 별도 지시.

## 6. 데몬

| 데몬 | 조치 |
|---|---|
| `com.irichgreen.server` | 4-8 에서 재기동 (코드 바뀜) |
| `com.irichgreen.ytsummarizer` | 4-10 에서 다시 올림 |
| `com.irichgreen.wiki-ingest` · `com.irichgreen.wiki-lan` | 그대로 (코드 무변경) |

## 7. 롤백

- 4-4 에서 멈춤: `git apply -R docs/tasks/patches/2026-10-11-v4-sqlite-switch-b.patch` (새 파일이 남으면 `rm -rf scripts/test_sync_obsidian.py legacy_scripts/README.md` 후 5개 원위치 확인). **스케줄러는 내린 채** 보고.
- 4-5 이후: 위와 같이 되돌리고 `launchctl kickstart -k gui/$(id -u)/com.irichgreen.server`. 커밋했다면 `git revert --no-edit HEAD`.
  - 이번에 만든 노트는 장부 기준으로 올바르므로 그대로 둔다. `_trash/<이번 시각>/` 이 생겼다면(기대 0) 원위치로 옮긴다.
  - **되돌린 상태(2-a 코드)로 스케줄러를 올리지 말 것** — 옛 sync 는 노션을 읽어 uuid 노트를 고아로 본다. 판정 전까지 내린 채 둔다.

## 8. 범위 밖

- 노션 코드(`lib/tips_notion.py`·`scripts/notion_to_sqlite.py`·`block_to_md`)·`.env` 노션 키 제거, README·CLAUDE 전면 갱신, 구글 시트 미러 — 지시서 3.
- `build_search_index.py` 의 notion_id 스캔(파일 전체) — `schema.md` 를 이미 건너뛰므로 무해. 지시서 3 에서 함께 본다.
- `/api/sync-obsidian` 엔드포인트(이제 호출하는 화면이 없다) — 지시서 3.
- `_trash/` 정리, 노션 쓰기·삭제, push, `kakao-tips-update` 스킬(Cowork).

## 9. 보고 형식 (한국어)

1. 4-1 출력(verify RESULT_JSON, D 값)
2. 4-3 마지막 줄 4개 + grep
3. 4-4 `RESULT_JSON` 전문 + 게이트 표 대조
4. 4-5 grep 결과, 소요 시간
5. 4-6 출력 2개
6. 4-7 `head -16` 출력
7. 4-8 출력
8. 4-9 grep 결과, 소요 시간
9. 4-10 출력, `git show --stat -M HEAD`
10. 기대와 다른 점 — 없으면 "없음"
