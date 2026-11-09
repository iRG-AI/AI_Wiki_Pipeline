# [CC-1109-E] 제안함에 꿀팁 판정 표시 · 매일 검토가 시험 제안도 봄

- 발주: pm-wiki (대표님 11-09 「네, 붙여줘」)
- 버전: v4.21.2 (PATCH — 화면 표시 추가 · 중복 방지, 실행 경로·예약 무변경)
- 장부·`.env`·launchd·운영 상태 파일 무변경. `wiki_lan_server.js` 무변경.

## 왜
1. `skill_review.py` 가 제안 파일에 `tip_review`(꿀팁마다 `{id, verdict: proposed|skipped, reason}`)를 남기지만 화면에 안 보인다. 대표님이 직접 남긴 꿀팁이 왜 빠졌는지 확인할 길이 없다.
2. `recent_context()` 가 `data/proposals/YYYYMMDD.json` 만 읽고 `trial/` 은 안 읽는다. 11-09 의 1개월 훑기(시험 파일 15건)와 같은 제안이 매일 검토에서 다시 나올 수 있다.

## 할 일

### 1. `lib/proposals.js` — `list()` 에 `reviews` 추가
- `loadProposals` 가 이미 읽는 파일마다(날짜 파일 + `trial/`) `tip_review` 가 배열이면 `{ file: <파일명>, date: created_at|null, trial: bool, items: [{id, verdict, reason}] }` 를 모은다. 항목은 `id`·`verdict`·`reason` 이 문자열인 것만, `verdict` 는 `proposed`·`skipped` 만.
- `tip_review` 가 비었거나 없는 파일은 넣지 않는다. 정렬은 제안과 같게(파일명 내림차순 — 최신 먼저).
- 반환: `{ items, errors, counts, reviews }`. 기존 필드 모양은 그대로.

### 2. `wiki.html` — 제안함에 「꿀팁 판정」 접기
- `renderProposals()` 의 `.pnote` 다음, 카드 목록 앞에 `PROP.reviews` 가 있으면 파일마다 `<details class="card prv">` 1개:
  - summary: `꿀팁 판정 · <날짜(propDate)> [시험] — <전체>건 중 제안 근거 <proposed>건 · 제외 <skipped>건`
  - 본문: **제외 먼저**, 그다음 제안. 줄마다 `[제외]`/`[제안]` 표지(`.st bad`/`.st done` 재사용) + 제목 + 이유.
  - 제목은 근거 노트처럼 `BY_ID.has(id)` 면 `<a href="#" data-note="id">` (기존 클릭 처리로 노트 패널이 열려야 한다), 없으면 `(목록에 없는 꿀팁)`.
  - 모든 글자는 `esc()`. 새 색·크기 없이 기존 CSS 변수만(필요하면 `.prv` 몇 줄).
- 다시 그릴 때 펼친 상태 유지: 기존 `openIds` 처리가 `details[data-did]` 를 쓰므로 `data-did="rv-<file>"` 를 붙여 같은 방식으로 유지되게 한다.
- `IS_LOCAL` 조건·탭·버튼 동작 무변경.

### 3. `skill_review.py:recent_context` — 시험 파일 제목도
- 날짜 파일과 함께 `trial/YYYYMMDD-HHMMSS.json` 도 읽는다(파일명 앞 8자리 = KST 날짜, 같은 0~6일 규칙).
- 프롬프트 제목 「## 최근 7일 제안 제목」 그대로. 중복 제목은 한 번만(순서 유지).

### 4. 테스트
- `scripts/test_proposals.js`: ㉠ `reviews` — 날짜 파일·trial 파일 각 1개, 최신 먼저, 잘못된 항목(verdict 이상·id 배열)은 빠짐, `tip_review` 없는 파일은 안 나옴, 기존 `items`·`counts` 불변.
- `scripts/test_skill_review.py`: ㉡ `recent_context` 가 `trial/` 의 6일 안 파일 제목은 넣고 7일 전 것은 빼며, 날짜 파일과 같은 제목은 한 번만.
- 이름 줄 숫자(`31/31` → N/N 등)는 CLAUDE.md·AGENTS.md 「Commands」 의 해당 두 줄만 고친다.

### 5. 문서 (scribe 몫이 아님 — implementer 가 같이)
- README 요약표 맨 위 `v4.21.2` 행 + `docs/changelog/2026-11.md` 맨 위 항목(앵커 `v4-21-2`) + `docs/changelog/README.md` 색인 줄(항목 수·범위·크기) + CLAUDE.md·AGENTS.md 「현재 버전」 · `docs/claude_history.md` 맨 위 1줄.
- README 「매일 Wiki 검토」 절에 한 줄: 제안함 위쪽 「꿀팁 판정」에서 꿀팁마다 제안 근거·제외와 이유를 본다 · 매일 검토는 시험 파일 제안도 겹침 판단에 쓴다.
- CLAUDE.md 는 크기 상한(약 358B 여유)이 빠듯하다 — 「매일 Wiki 검토」 절은 고치지 말고 버전 줄·테스트 숫자만.

## 확인 (verifier 기준표)
| # | 기준 |
|---|---|
| 1 | `node scripts/test_proposals.js` · `python3 scripts/test_skill_review.py` 전부 통과, 새 검사 ㉠·㉡ 포함 |
| 2 | `scripts/run_all_tests.sh` → `RESULT: 20/20` |
| 3 | 실제 `data/proposals` 로 `node -e "console.log(require('./lib/proposals').list().reviews.map(r=>[r.file,r.items.length]))"` → `20261109.json` 4 · `20261109-071502.json` 51 (trial 파일이 더 있으면 그것도) |
| 4 | `wiki.html` 새 코드의 모든 삽입 글자가 `esc()` 를 거침 · `wiki_lan_server.js` diff 0 · 장부 sha256 전후 동일 |
| 5 | `recent_context` 실데이터: 오늘 기준 titles 에 시험 제안 15건 제목이 들어감(4 + 15, 중복 제외) |
| 6 | `test_readme_changelog.py` 9/9 · `test_claude_md_budget.py` 6/6 |
| 7 | 지시서 밖 파일 변경 0 · 개인 절대경로·맥 이름 새로 쓰지 않음 |
