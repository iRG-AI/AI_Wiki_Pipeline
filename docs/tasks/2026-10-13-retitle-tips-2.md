# 꿀팁 제목 보완 2차 — 「원문 확인 필요」 43건 (v4.4 도구 적용, 코드 무변경)

> 지시 번호는 발행할 때 채팅으로 준다(`[CC-1013-E]`). 보고는 한국어로.
> 선행: `dc94e29`(원격 main 과 같음). 스케줄러는 내리지 않는다(4-0 의 시간 창만 피한다).
> **장부·Vault 를 고친다**(tips 43행 · 노트 43개 · 링크 약 92곳). 앱 코드·`.env` 변경 없음, 데몬 재기동 없음.

## 1. 배경

- `kakao_ingest.py` 는 링크를 열지 않고 URL 로 제목을 추정한다. 「원문 확인 필요」 메모가 붙은 꿀팁이 44건 남아 있었다(10-12 1차 5건 적용 뒤 41건 + 그 사이 카톡 인제스트분).
- Cowork 가 원문 제목을 조회했다(10-13 14:30, 노션 공개 페이지 API `syncRecordValuesMain` · 일반 페이지 `og:title`/`<title>`). 44건 중 43건 확인.
  - 제목만으로 뜻이 모호한 7건은 본문 첫 줄을 보고 괄호로 주제를 덧붙였다(예: 「gpt api」 → 「Higgsfield에서 GPT API 연결하는 법」).
  - 원문의 `|`(「하네스 A to Z 02 | 내 업무를…」)는 금지 문자라 ` — ` 로 바꿨다. 제목 앞 이모지(🎬·🎁)는 파일명 정리를 위해 뺐다.
  - **제외 1건** `3bca3cbc-…-e78edaad2a09`(`app.notion.com/p/39a28466…`) — 비공개 페이지라 제목을 확인할 수 없다. 장부·노트 그대로 두고 「원문 확인 필요」로 남긴다.
- 도구는 v4.4 `scripts/retitle_tips.py` 그대로다(장부 title·memo·updated_at + 노트 제자리 수정·파일명 변경 + Vault 링크 치환, 쓰기 전 백업). 이번 지시서는 CSV 를 적용하고 CSV·지시서를 커밋할 뿐이다.

## 2. 파일

| 파일 | 내용 |
|---|---|
| `docs/tasks/2026-10-13-retitle-tips-2.csv` | 43행 + 머리글(`record_id,old_title,new_title`) |
| `docs/tasks/2026-10-13-retitle-tips-2.md` | 이 지시서 |

```
sha256  0671982081158eb3d2d2d9659edeb35e270f7ec36b93853eb168333795d61f03  docs/tasks/2026-10-13-retitle-tips-2.csv
```

### Cowork 사전 검증 (2026-10-13 14:40, 맥 · 레포 무변경)

- 실데이터 dry-run(실제 장부 읽기 전용 + 실제 Vault 읽기): exit 0, `RESULT_JSON:{"ok": true, "dry_run": true, "rows": 43, "notes": 43, "renamed": 43, "memo_cleared": 43, "link_files": 6, "links": 92}`.
  모든 노트의 편집 지점(title·memo·H1·메모 줄)이 1곳씩 잡혔다. 새 백업 폴더 안 생김.
- 장부 사본 apply 는 하지 않았다 — 도구는 v4.4 회귀 49/49 + 10-12 실적용 5건으로 검증됐고, 이번은 같은 경로에 행만 늘었다.

## 3. 적용 목록

| 저장일 | 옛 제목 | 새 제목 |
|---|---|---|
| 03-08 | 노션 자료 (제목 미확인 · 2편) | 클로드코드 기초 총정리 시리즈 2편 |
| 03-09 | 노션 자료 (제목 미확인) | 믿지 마세요, 이제 우리는 의심해야 합니다 (Higgsfield 이미지 프롬프트) |
| 03-14 | 노션 자료 (제목 미확인) | 저화질 → 고화질 시네마틱 사진으로 만드는 프롬프트 |
| 03-17 | 노션 자료 (제목 미확인) | 클로드 in 크롬: 반복 업무 0시간 만들기 가이드 |
| 03-20 | 노션 자료 (제목 미확인) | 만세력 캡처로 사주 분석하는 제미나이 프롬프트 |
| 03-20 | 3분 10선 (제목 일부 확인) | 이건 찐이다! 클로드 코드 완전정복, 3~10시간 무료 강의 모음 |
| 04-01 | 노션 자료 (제목 미확인) | 리얼리티 프롬프트 올인원 팩 (이미지 + 영상) |
| 04-03 | 15선 정리 (제목 일부 확인) | 15초 영상 프롬프트 클로드 스킬 |
| 04-03 | TOP 8 정리 (제목 일부 확인) | 해외에서 난리난 6만개 클로드스킬 중 TOP 8 |
| 04-04 | 노션 자료 (제목 미확인) | 콘텐츠 기획과 제작에 활용할 수 있는 클로드 프롬프트 모음 |
| 04-07 | 노션 자료 (제목 미확인) | 클로드 시크릿코드 — 프롬프트 단축 명령어 100개 |
| 04-07 | 노션 자료 (제목 미확인) | 클로드코드 스킬 실전 활용 플레이북 |
| 06-05 | 5선 정리 (제목 일부 확인) | [호시절] 투자 고수들의 황금 프롬프트 5가지 |
| 07-18 | 6선 정리 (제목 일부 확인) | 원본 하나로, 6가지 마법 가이드 (AI 영상) |
| 07-31 | 노션 자료 (제목 미확인) | 클로드로 내 인스타그램 분석 |
| 07-31 | 노션 자료 (제목 미확인) | 클로드 코드 토큰 3배로 오래 쓰는 무료 도구 3개 |
| 08-11 | 노션 자료 (제목 미확인) | 바이브코딩하는데 이걸 이제 알아버림 (UI 애니메이션·컴포넌트 라이브러리) |
| 09-01 | 노션 자료 (제목 미확인) | 클로드 코드 끊김 없이 쓰는 무료 도구 3종 설치 가이드 |
| 09-02 | 개인 아카이브 페이지 (제목 미확인) | 클로드 토큰 20분의 1로 줄이는 법 |
| 09-03 | 5선 정리 (제목 미확인) | 클로드코드 필수 플러그인 5가지 — 설치 가이드 |
| 09-03 | 노션 자료 (제목 미확인) | 딱 이 3가지만 보고 그대로 설정하세요 (클로드 튜토리얼·Firecrawl MCP·원격 제어) |
| 09-03 | 개인 아카이브 페이지 (제목 미확인) | 클로드 화면이 촌스러운 진짜 이유 |
| 09-03 | 5선 정리 (제목 미확인) | 초보자용 배포자료 — 클로드코드 프론트엔드 디자인 플러그인 5개 |
| 09-03 | 노션 자료 (제목 미확인) | 클로드 한도 끝까지 쥐어짜기 |
| 09-04 | 노션 자료 (제목 미확인) | 클로드 토큰절약가이드 |
| 09-05 | 개인 아카이브 페이지 (제목 미확인) | 이 3개 없이 쓰면 클로드 반만 쓰는 겁니다 |
| 09-06 | 노션 자료 (제목 미확인) | 애플 디자인 스킬 — 설치부터 검토까지 |
| 09-18 | 노션 자료 (AI) | AI 둘을 붙여 한 팀으로 — 화면은 페이블, 생각은 아스트라 |
| 09-18 | 노션 자료 (AI) | AI로 숏폼(릴스) 영상 편집·발행 자동화하기 |
| 09-18 | 노션 자료 (Claude Code) | Claude Code로 개인 투자 리서치 자동화한 방법 |
| 09-21 | 노션 자료 (제목 미확인) | 클로드 코드에서 코덱스 사용하기 |
| 09-26 | 노션 자료 (10 7) | 클로드로 10분 만에 직원 7명 만드는 법 — 클로드 활용 가이드 (풀버전) |
| 09-27 | 노션 자료 (24 AI GPT 6) | 24시간 도는 AI 트레이더 만들기 — GPT-6 아스트라 |
| 09-28 | 노션 자료 (gpt api) | Higgsfield에서 GPT API 연결하는 법 |
| 09-28 | 노션 자료 (AI) | 머더디핀 설치 가이드: 클로드로 AI 직원 사무실 차리기 |
| 10-05 | 노션 자료 (Opus 5 5) | Opus 5.5 모션그래픽 프롬프트 모음 |
| 10-05 | 노션 자료 (PDF MarkItDown) | 클로드에 PDF 올리기 전에 — 마크잇다운(MarkItDown) 설치·연결 가이드 |
| 10-05 | 노션 자료 (제목 미확인) | 클로드코드로 광고 영상 만들기 |
| 10-07 | 노션 자료 (A to Z 02) | 하네스 A to Z 02 — 내 업무를 학습시키는 법 |
| 10-08 | 노션 자료 (35) | 클로드 확장팩 35개 설치 링크, 자리별로 모음 |
| 10-09 | hongikman-dashboard.pages.dev | 홍익인간 — AI 빌드 아카이브 |
| 10-10 | 노션 자료 (AI) | [가이드] AI로 나만의 노션 대시보드 만들고 자동화하기 — 전체 워크플로우 |
| 10-10 | 노션 자료 (4) | 클로드 코드로 비싼 사이트 화면 효과 내는 4가지 |

## 4. 실행 — `[CC-1013-E]`

### 4-0. 시간

스케줄러가 00·06·12·18시, wiki-ingest 가 17:30 에 돈다. **매시 50분 ~ 다음 시 20분, 17:25~17:45 에는 4-3 이후를 시작하지 않는다.**

### 4-1. 시작 상태 (읽기만)

```bash
cd <REPO_ROOT>
git --no-optional-locks rev-parse --short HEAD          # dc94e29
git --no-optional-locks status --porcelain
#   기대: 아래 두 줄만
#   ?? docs/tasks/2026-10-13-retitle-tips-2.csv
#   ?? docs/tasks/2026-10-13-retitle-tips-2.md
shasum -a 256 docs/tasks/2026-10-13-retitle-tips-2.csv              # 2절 값과 같아야 한다
grep -o '"outcome": "[a-z]*"' .run_state.json                       # "ok" (running 이면 멈춤 — 스케줄러 실행 중)
ls data/retitle_backup/                                              # 20261012-174732 하나 (1차 백업)
sqlite3 "file:data/library.db?mode=ro" "select count(*) from tips; select count(*) from tips where memo like '%원문 확인 필요%' or title like '%제목 미확인%';"
#   기대: 148 · 44 (카톡 인제스트로 tips 가 늘었으면 첫 값은 보고만)
```

어긋나면 **멈추고 보고**한다.

### 4-2. 실데이터 dry-run (무변경)

```bash
/opt/homebrew/bin/python3 scripts/retitle_tips.py docs/tasks/2026-10-13-retitle-tips-2.csv > /tmp/rt2_dry.txt; echo "exit $?"; grep -c ' → ' /tmp/rt2_dry.txt; tail -1 /tmp/rt2_dry.txt
ls data/retitle_backup/ | wc -l                                      # 1 (새 폴더 없음)
```

기대: exit 0, `RESULT_JSON` 의 `ok true · dry_run true · rows 43 · notes 43 · renamed 43 · memo_cleared 43`.
`link_files`·`links` 는 사전 검증 때 6·92 였다. 그 사이 정시 실행·wiki-ingest 가 MOC·Wiki 페이지를 다시 그렸으면 달라질 수 있다 — **숫자는 보고만 하고 멈추지 않는다.** `ok false` 면 멈추고 출력 전체를 보고.

### 4-3. 반영 (대표님 승인 — 장부·Vault 쓰기)

```bash
/opt/homebrew/bin/python3 scripts/retitle_tips.py docs/tasks/2026-10-13-retitle-tips-2.csv --apply > /tmp/rt2_apply.txt 2>&1; echo "exit $?"; tail -6 /tmp/rt2_apply.txt
```

기대: exit 0, `RESULT_JSON` 의 `ok true · rows 43 · notes 43 · renamed 43 · memo_cleared 43`, `rebuild` 의 `build_obsidian_wiki.py 0 · build_search_index.py 0`, `backup` 경로. `links`·`link_files` 는 4-2 와 같아야 한다.
exit 1 이면 그 자리에서 멈추고 `/tmp/rt2_apply.txt` 전체를 보고한다(롤백은 Cowork 판단 후 — 7절).

### 4-4. 확인 (읽기만)

```bash
sqlite3 "file:data/library.db?mode=ro" "select count(*) from tips where updated_at = (select max(updated_at) from tips);"   # 43
sqlite3 "file:data/library.db?mode=ro" "select record_id, title, memo from tips where memo like '%원문 확인 필요%' or title like '%제목 미확인%';"
#   기대: 1행 — 3bca3cbc-5c7a-80b9-aa34-e78edaad2a09 (제외분)
/opt/homebrew/bin/python3 scripts/verify_library.py | grep RESULT_JSON   # ok true · vault_missing 0 · tips_missing 0
ls ~/Documents/Obsidian/"AI LLM Wiki"/"AI LLM Wiki"/"AI 꿀팁" | grep -c '\.md$'    # 4-1 의 tips 수와 같음(늘거나 줄지 않음)
B=$(ls -d data/retitle_backup/*/ | tail -1); echo "$B"
/opt/homebrew/bin/python3 - "$B" <<'EOF'
import json, os, sys, unicodedata as u
m = json.load(open(os.path.join(sys.argv[1], 'manifest.json'), encoding='utf-8'))
olds = [u.normalize('NFC', os.path.splitext(os.path.basename(r['from']))[0]) for r in m['renamed']]
print('RENAMED', len(olds))                                            # RENAMED 43
left = 0
for root, ds, fs in os.walk(m['vault']):
    ds[:] = [d for d in ds if not d.startswith('.') and d != '_trash']
    for f in fs:
        if f.endswith('.md'):
            t = u.normalize('NFC', open(os.path.join(root, f), encoding='utf-8', errors='ignore').read())
            left += sum(t.count('[[' + s + e) for s in olds for e in (']]', '|', '#'))
print('OLD_LINKS', left)                                               # OLD_LINKS 0
EOF
grep -c '클로드 확장팩 35개 설치 링크' wiki_index.json                 # ≥ 1 (검색 인덱스에 새 제목)
/opt/homebrew/bin/python3 sheet_mirror.py --dry-run | tail -1        # error "" · tips_sent ≥ 43 (다음 정시 실행이 보낼 몫)
```

## 5. 커밋 (push 하지 않음)

```bash
git add docs/tasks/2026-10-13-retitle-tips-2.csv docs/tasks/2026-10-13-retitle-tips-2.md
git commit -m "꿀팁 제목 보완 2차 — 원문 확인 필요 43건 (retitle_tips.py 적용, 코드 무변경)"
git --no-optional-locks status --porcelain       # 커밋 뒤 기대: 빈 출력
git --no-optional-locks log --oneline -2
git --no-optional-locks show --stat HEAD | tail -4   # 2개 파일
```

**push 는 하지 않는다.** Cowork 가 장부·Vault 를 확인한 뒤 따로 지시한다.

## 6. 데몬

- 재기동 불필요. 앱 코드 무변경. 검색 서버들은 `wiki_index.json` mtime 이 바뀌면 다시 읽는다.

## 7. 롤백

- 4-3 이후(장부·Vault 되돌리기 — 정시 실행 창 밖에서). v4.4 지시서(`docs/tasks/2026-10-12-retitle-tips.md`) 7절과 같은 절차, `B` = 4-3 `RESULT_JSON` 의 `backup` 경로:

```bash
B=<4-3 RESULT_JSON 의 backup 경로>
/opt/homebrew/bin/python3 - "$B" <<'EOF'
import json, os, shutil, sys
b = sys.argv[1]; m = json.load(open(os.path.join(b, 'manifest.json'), encoding='utf-8')); v = m['vault']
for r in m['renamed']:
    p = os.path.join(v, r['to'])
    if os.path.exists(p): os.remove(p)
for rel in m['edited']:
    shutil.copy2(os.path.join(b, 'vault', rel), os.path.join(v, rel))
shutil.copy2(os.path.join(b, 'library.db'), m['db'])
print('restored', len(m['edited']), 'files + db')
EOF
/opt/homebrew/bin/python3 build_obsidian_wiki.py && /opt/homebrew/bin/python3 build_search_index.py
/opt/homebrew/bin/python3 scripts/verify_library.py | grep RESULT_JSON
```

  시트가 이미 새 제목을 받았다면(정시 실행 뒤) `sheet_mirror.py --full`. **복원 장부는 4-3 직전 것이라 그 사이 정시 실행분이 있으면 되돌리지 말고 Cowork 에 보고**한다.
- 커밋 후: `git revert HEAD`(push 전이면 `git reset --soft HEAD~1` 도 가능).

## 8. 범위 밖

- `git push`.
- 제외 1건(비공개 노션 페이지) — 대표님이 원문을 아시면 다음 CSV 로.
- `kakao_ingest` 가 인제스트 때 제목을 직접 가져오게 하는 개선(노션 공개 API·`og:title`) — 다음에 쌓이는 「원문 확인 필요」를 없애는 근본책.
- `data/retitle_backup/` 정리(10-19 이후 Cowork 제안).

## 9. 보고 형식 (한국어)

```
[CC-1013-E] 결과
- 4-1 시작 상태: HEAD / porcelain / CSV sha256 일치 여부 / outcome / retitle_backup 목록 / tips 수 · 대상 수
- 4-2 dry-run: exit, ' → ' 줄 수, RESULT_JSON 원문, 백업 폴더 수
- 4-3 반영: exit, RESULT_JSON 원문
- 4-4 확인: 최신 updated_at 행 수 / 남은 1행 원문 / verify_library RESULT_JSON / 꿀팁 노트 수 / RENAMED · OLD_LINKS / 인덱스 grep / sheet_mirror --dry-run 마지막 줄
- 5 커밋: 해시, show --stat
- 특이사항(멈춘 단계·기대와 다른 출력 원문)
```
