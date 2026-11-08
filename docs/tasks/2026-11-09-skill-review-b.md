# [CC-1109-B] 매일 Wiki 검토 2단계 — 제안함 화면 (`lib/proposals.js` · server.js 라우트 2개 · wiki.html 「제안함」)

- 작성: pm-wiki · 2026-11-09 · 승인: 대표님 11-09 「2단계 진행」(계획 `mellow-mixing-scott.md` 승인 범위)
- 실행: implementer · 검수: verifier
- 앞 단계: [CC-1109-A] `skill_review.py`(미커밋). 이 단계도 커밋하지 않는다 — C 단계(launchd·문서)에서 한꺼번에 v4.20.0.

## 목적

`http://localhost:3000/wiki` 머리줄의 [제안함 N] 을 누르면 제안 카드가 나온다. 대표님은 카드에서 근거 노트를 열어 보고 [승인]·[보류]·[거절]·[되돌리기] 중 하나를 누른다.
- 스킬 제안을 승인하면 `~/.claude/skills/wiki-<slug>/SKILL.md` 가 바로 설치된다.
- 적용 아이디어를 승인하면 붙여 넣을 프롬프트가 [복사] 버튼과 함께 남는다.

## 범위

- 만들 것: `<REPO_ROOT>/lib/proposals.js`, `<REPO_ROOT>/scripts/test_proposals.js`
- 고칠 것: `<REPO_ROOT>/server.js`(라우트 2개만), `<REPO_ROOT>/wiki.html`(제안함 화면), `<REPO_ROOT>/skill_review.py` · `<REPO_ROOT>/scripts/test_skill_review.py`(아래 「1단계 보완」만)
- 바꾸면 안 되는 것:
  - **`wiki_lan_server.js`** — 한 글자도 바꾸지 않는다. 집 안 서버에는 쓰기 경로를 두지 않는다.
  - 장부 · `.env` · launchd · `scripts/run_all_tests.sh`(C 단계) · README/CLAUDE.md/AGENTS.md(C 단계) · 실제 `~/.claude/skills/` · 실제 `data/proposals/decisions.json`
  - 커밋·push
- 서버 재기동·브라우저 확인은 PM 이 한다. implementer 는 하지 않는다.

## 저장 형식

- 제안 파일: `skill_review.py` 만 쓴다. `lib/proposals.js` 는 읽기만 한다.
  - `data/proposals/YYYYMMDD.json`
  - `data/proposals/trial/<YYYYMMDD-HHMMSS>.json`(시험분도 목록에 띄우고 `trial: true` 로 표시)
- 결정 파일: `data/proposals/decisions.json` 은 `lib/proposals.js` 만 쓴다(tmp → `fs.renameSync`).
  ```json
  {"version":1,"decisions":{"<id>":{"id":"…","title":"…","kind":"skill|action","decision":"approved|held|rejected","reason":"…","at":"ISO UTC","installed":"<설치 경로 또는 null>","history":[{"decision":"…","at":"…","reason":"…"}]}}}
  ```
  [되돌리기]를 누르면 그 id 의 항목을 지운다. 그 결과 상태가 `new` 로 돌아가고, 지운 항목은 `history` 꼴로 `undone` 배열에 남긴다(파일 최상위 `undone: []`).
- 휴지통: `data/proposals/_trash/<YYYYMMDD-HHMMSS>-wiki-<slug>/`. 스킬 폴더 **밖**에 둬서 휴지통에 든 스킬이 다시 읽히지 않게 한다.

## `lib/proposals.js` (의존성 0, 경로 주입 가능)

`module.exports = { list, decide, writeAllowed, ID_RE, SLUG_RE }`

공통 옵션 `opts = { dir, skillsDir, now }`:
- `dir` 기본값: `<REPO_ROOT>/data/proposals`
- `skillsDir` 기본값: 환경변수 `SKILL_REVIEW_SKILLS_DIR`, 없으면 `~/.claude/skills`
- `now`: 테스트용

**정규식**
- `ID_RE = /^(trial-\d{8}-\d{6}|\d{8})-\d{1,2}$/`
- `SLUG_RE = /^[a-z0-9-]{3,40}$/`
- slug 가 `wiki-` 로 시작하면 거부한다.

**`list(opts)`**
1. 제안 파일 두 종류를 읽는다. 이름이 정확히 `^\d{8}\.json$`, `^\d{8}-\d{6}\.json$` 인 파일만 읽는다. 깨진 파일은 건너뛰고 `errors` 에 파일 이름을 넣는다.
2. 각 제안에 `decisions` 를 합친다 → `status` · `reason` · `at` · `installed`.
3. 각 제안에 `date`(파일의 `created_at`), `trial` 을 붙인다.
4. 최신 파일부터 정렬해 `{ items, errors, counts:{new, held, approved, rejected} }` 를 돌려준다.

`skill_md` 와 `action_prompt` 도 그대로 담는다. 화면 미리보기에 쓰인다.

**`decide(id, decision, reason, opts)`** — `decision ∈ {approve, hold, reject, undo}`. 그 밖의 값은 `{ok:false, code:400}`.

- **공통 확인**
  - `ID_RE` 에 맞지 않으면 400
  - 제안 파일에 없는 id 면 404
  - `reason` 은 문자열로 바꾸고 앞뒤 공백을 잘라 300자까지만 둔다(넘으면 400)
- **approve · 스킬 제안**
  - 내용은 **저장된 제안 파일에서만** 가져온다. 함수 인자에 내용을 받는 자리를 만들지 않는다.
  - 검증(어기면 400, 아무것도 쓰지 않음): `SLUG_RE` · `wiki-` 접두 금지 · `skill_md` 가 `---\n` 으로 시작 · 프론트매터 안에 `name: wiki-<slug>` 줄
  - `skillsDir` 가 없으면 만들지 않고 409 `skills_dir_missing`
  - 대상 `skillsDir/wiki-<slug>` 가 이미 있으면 409 `exists`. **덮어쓰지 않는다.**
  - 설치: `fs.mkdirSync(대상)`(recursive 없이) → `fs.writeFileSync(대상/SKILL.md, skill_md, {flag:'wx'})`
  - 결정 기록에 `installed` = 설치 경로
  - 이미 `approved` 인 id 는 409 `already`
- **approve · 적용 아이디어 제안**: 기록만 한다.
- **hold · reject**: 기록만 한다(`reject` 는 사유를 권장할 뿐 필수가 아니다). 이미 같은 결정이면 409 `already`.
- **undo**
  - 결정 기록이 없으면 409 `nothing`
  - `installed` 가 있으면 그 폴더를 휴지통으로 옮긴다(`fs.renameSync`).
    - 폴더가 이미 없으면 옮기지 않고 그대로 진행하되 결과에 `missing:true`
    - 옮기기 전 확인: 경로가 `skillsDir/wiki-` 로 시작하는지 `path.resolve` 결과로 본다. 이 확인이 실패하면 아무것도 하지 않고 500.
  - 그다음 결정 기록을 지운다.
- **반환값**: `{ok, code, error?, status, installed?, trashed?}`
- **쓰기 순서**: 스킬 파일 → `decisions.json`. `decisions.json` 쓰기가 실패했는데 스킬을 이미 설치했다면 설치한 폴더를 지워 되돌린다.

**`writeAllowed(headers, port)`**(순수 함수). 셋을 모두 만족할 때만 true다. 이 셋이 다른 사이트 브라우저를 통한 요청과 DNS 리바인딩을 막는다.
- `host` 가 정확히 `localhost:<port>` 또는 `127.0.0.1:<port>`
- `origin` 이 있고 `http://localhost:<port>` 또는 `http://127.0.0.1:<port>`
- `content-type` 이 `application/json` 으로 시작

## `server.js` — 라우트 2개 (다른 라우트는 손대지 않는다)

`/api/wiki-ask` 블록 다음, `/` 블록 앞에 넣는다. `const proposals = require('./lib/proposals');`

- **`GET /api/proposals`**
  - host 가 `localhost:3000`·`127.0.0.1:3000` 이 아니면 403
  - `proposals.list()` 결과를 200 으로 돌려준다. `Cache-Control: no-store`
- **`POST /api/proposals/decide`**
  - `writeAllowed(req.headers, PORT)` 가 false 면 403 `{error:'허용되지 않은 요청입니다.'}`
  - 본문은 `collectBody` 로 읽되 4KB 를 넘으면 413
  - JSON 에서 `id`·`decision`·`reason` **만** 꺼낸다
  - `proposals.decide()` 결과의 `code` 를 HTTP 상태로 돌려준다
  - 성공하면 서버 로그 한 줄: `[proposals] <id> <decision> <installed 경로 또는 ->`. 사유는 찍지 않는다.

## `wiki.html` — 「제안함」

DS 1.1.23 의 CSS 변수만 쓴다(새 색 값을 쓰지 않는다). **`IS_LOCAL` 이 false 면 버튼·화면을 아예 그리지 않는다**(가족 PC). 모든 글자는 `esc()` 를 거치거나 `textContent` 로 넣는다(`skill_md`·`action_prompt`·`why` 포함).

**머리줄**
- `.actions` 의 [필터] 앞에 `<button class="btn btn-secondary" id="btnProposals" hidden>제안함 <span id="propCount"></span></button>`
- 시작할 때 `IS_LOCAL` 이면 `/api/proposals` 를 한 번 부르고 버튼을 보인다
- N = `counts.new`. 0 이면 숫자를 숨긴다.

**화면 전환**
- 해시 키 `tab=proposals` 를 쓴다(기존 `view` 키는 표·카드 전환용이라 같이 쓰지 않는다)
- `writeHash`·`readHash` 에 `tab` 을 더한다
- 제안함일 때 `main` 의 기존 목록 영역(`.rhead`·`#chips`·`#answer`·`#results`)을 숨기고 `<section id="proposals">` 를 보인다. 버튼을 다시 누르거나 [목록으로] 를 누르면 돌아온다.
- 노트 패널(`openPanel`)은 제안함 화면에서도 그대로 동작한다.

**제안함 머리**
- 분류 단추 「새·보류」(기본) · 「승인」 · 「거절」 · 「전체」 + 건수
- 맨 위 안내 한 줄: "매일 Wiki 검토가 고른 제안입니다. 승인하면 스킬은 바로 설치되고, 적용 아이디어는 프롬프트가 남습니다."

**카드**(`.card` 계열 기존 스타일 재사용)
- 첫 줄
  - 종류 배지: `skill` = 「스킬」, `action` = 「적용 아이디어」
  - 분야: `dev` 개발 자동화 · `work` 회사 업무 · `knowledge` 지식관리 · `content` 콘텐츠·영상
  - 품: 낮음·중간·높음
  - 날짜
  - 시험분이면 「시험」
  - 상태 배지
- 제목(굵게) · 왜 도움이 되나(`why`)
- 근거: `evidence` id 마다
  - `BY_ID` 에 있으면 그 노트 제목으로 `data-note` 링크를 만든다 → 기존 패널이 열린다
  - 없으면 「(목록에 없는 노트)」를 흐린 글자로
- 펼치기(`<details>`)
  - 스킬: "설치 위치 `~/.claude/skills/wiki-<slug>/SKILL.md`" + `<pre>` 에 `skill_md`
  - 적용 아이디어: `<pre>` 에 `action_prompt` + [복사] (`navigator.clipboard.writeText`, 성공하면 "복사했습니다" 2초)
- 단추(상태별)
  - `new` · `held`
    - [승인·설치](스킬) 또는 [승인](적용 아이디어)
    - [보류](held 면 감춘다)
    - [거절] — 누르면 카드 안에 사유 입력칸(최대 300자)과 [거절 확정]·[취소]
  - `approved`: 스킬은 "설치됨: <경로>", 적용 아이디어는 [복사] + [되돌리기]
  - `rejected`: 사유 표시 + [되돌리기]
- [승인·설치]는 `confirm("~/.claude/skills/wiki-<slug>/ 에 설치합니다. 다음 Claude Code 세션부터 쓸 수 있습니다.")` 뒤에만 보낸다
- [되돌리기]가 설치된 스킬을 옮길 때는 `confirm("설치된 스킬을 휴지통(data/proposals/_trash)으로 옮깁니다.")`
- 요청: `fetch('/api/proposals/decide', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({id, decision, reason})})`
  - 응답 오류는 카드 안에 빨간 한 줄로: `exists` → "같은 이름 스킬이 이미 있어 설치하지 않았습니다"
  - 끝나면 목록을 다시 불러온다
- 제안이 없을 때: "아직 제안이 없습니다. 매일 아침 검토가 끝나면 여기에 나옵니다."

## 1단계 보완 (`skill_review.py` · `scripts/test_skill_review.py`) — 검수 지적 반영

1. **날짜는 한국 시각(KST)으로.** `ZoneInfo('Asia/Seoul')` 를 쓴다.
   - KST: 파일 이름 `YYYYMMDD`, trial 시각, id, 같은 날 두 번 실행 막기, `recent_context` 의 날짜 비교
   - UTC 그대로: `through`·`window`·`created_at`
   - 테스트: KST 08:30(UTC 전날 23:30)에 돌리면 파일 이름이 KST 날짜가 되는지 본다(시각 주입 방법은 기존 테스트 방식을 따른다)
2. **`recent_context` 정리**
   - 7일: 파일 날짜가 KST 오늘에서 0~6일 전인 것만
   - `decisions.json` 은 위 「저장 형식」(dict `decisions`)으로 읽는다. `decision == 'rejected'` 인 항목만, `at` 최신순 30개를 `"제목: 사유"`(사유가 없으면 `"제목: (사유 없음)"`) 꼴로
   - 테스트에 이 형식의 `decisions.json` 을 넣어 확인한다
3. `skill.slug` 가 `wiki-` 로 시작하면 그 제안을 버리고 `dropped` 에 사유를 넣는다(테스트 추가)
4. Claude 호출이 실패하면(종료 코드 ≠ 0 · 시간 초과) RESULT_JSON `error` 에 stderr 앞 200자를 붙인다(줄바꿈은 공백으로). 테스트 추가
5. 프로필 파일이 없으면 stderr 에 경고 한 줄을 남기고 결과 `note` 에 "프로필 없음" 을 붙인다. 테스트의 임시 폴더는 끝날 때 지운다(`try/finally` 또는 `tempfile.TemporaryDirectory`)

## 테스트 `scripts/test_proposals.js` (네트워크 0 · 실제 스킬 폴더·제안 폴더 무관 — 전부 `fs.mkdtempSync`)

최소 확인:
1. `list` 가 날짜 파일과 trial 파일을 합치고, 결정과 상태를 합치고, 깨진 파일을 `errors` 로 보낸다. 이름 꼴이 다른 파일(`notes.json`)은 무시한다.
2. 스킬 승인 → `skillsDir/wiki-<slug>/SKILL.md` 내용이 제안 파일의 `skill_md` 와 바이트 단위로 같고, `decisions.json` 에 `installed` 가 남는다.
3. 같은 id 를 다시 승인하면 409 `already`. 대상 폴더가 미리 있으면 409 `exists` 이고 그 폴더 안 파일이 바뀌지 않는다.
4. slug 위반 · `wiki-` 접두 · `name:` 불일치 · `---` 로 시작하지 않음 → 각각 400, 스킬 폴더와 `decisions.json` 에 변화 없음.
5. `skillsDir` 가 없으면 409 `skills_dir_missing`, 폴더를 만들지 않는다.
6. `decide` 에 다른 내용을 넘길 길이 없다(시그니처). 추가로 server 와 같은 방식으로 본문 JSON 에 `skill_md` 를 넣어도 설치 내용은 제안 파일 그대로다 — server 의 본문 처리 부분을 함수로 빼지 않았다면 이 항목은 `decide` 인자 4개 확인으로 갈음한다.
7. 되돌리기 → 스킬 폴더가 `dir/_trash/…-wiki-<slug>/` 로 옮겨지고, 상태가 `new`, `undone` 에 한 줄 남는다. 폴더가 이미 없으면 `missing:true`.
8. 보류·거절(사유 저장, 301자 → 400) · 잘못된 decision → 400 · 없는 id → 404 · `ID_RE` 위반 → 400.
9. `writeAllowed`: Origin 없음 · 다른 Origin · Host 다름(`evil.com:3000`) · Content-Type 이 `text/plain` → false, 정상 → true.
10. `wiki_lan_server.js` 에 `proposals` 라는 글자가 없다(파일을 읽어 확인).
11. `decisions.json` 쓰기 실패를 흉내 내면(예: `decisions.json` 자리를 폴더로 만들어 둠) 설치한 스킬 폴더가 남지 않는다.

출력 마지막 줄은 다른 JS 테스트와 같은 꼴(`N/N`)이다. `/opt/homebrew/bin/node scripts/test_proposals.js` 로 돈다.

## 기준표

| # | 기준 | 판정 근거 |
|---|---|---|
| 1 | `test_proposals.js` 1~11 통과 | 출력 N/N |
| 2 | `test_skill_review.py` 기존 + 보완 1~5 통과 | 출력 N/N |
| 3 | 기존 회귀 18종 통과 | `scripts/run_all_tests.sh` 마지막 줄 `RESULT: 18/18` |
| 4 | `wiki_lan_server.js` 무변경 | `git diff --stat wiki_lan_server.js` 빈 출력 |
| 5 | server.js 변경은 라우트 2개 + require 1줄뿐 | `git diff server.js` |
| 6 | 설치 내용은 저장된 제안에서만 · 덮어쓰기 없음 · 휴지통은 스킬 폴더 밖 | 코드 + 테스트 2·3·7 |
| 7 | POST 는 `writeAllowed` 통과 시에만 | 코드 + 테스트 9 |
| 8 | wiki.html: `IS_LOCAL` false 면 그리지 않음 · 사용자 글자는 모두 `esc`/`textContent` · 새 색 값 없음 | `git diff wiki.html` 검사(`#[0-9a-f]{3,6}`·`rgba(` 새로 생긴 줄 0) |
| 9 | 실제 `~/.claude/skills/`·`data/proposals/decisions.json`·장부 무변경 | 실행 전후 `ls ~/.claude/skills \| wc -l` · `ls data/proposals` |
| 10 | 범위 밖 변경 0 · 커밋 0 | `git status --porcelain` = A 단계 3개 + 이 지시서 + 새 2개 + 고친 4개 + 기존 `?? docs/tasks/2026-11-08-video-daily-seconds-trial.md` |

## 하지 말 것

- `wiki_lan_server.js` 수정 · 서버 재기동 · 실제 스킬 폴더에 쓰기 · 실제 `decisions.json` 만들기 · `claude` 실호출(이번 단계는 0회) · 커밋·push.
- 코드 편집은 정시 실행 창(00·06·12·18시 −10/+20분)을 피한다(훅이 막으면 기다렸다가 다시).
