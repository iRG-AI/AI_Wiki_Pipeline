# [CC-1101-C] v4.17 — not_ai 제외는 토픽 분류도 비었을 때만

- 작성: 2026-11-01 · pm-wiki (XP-1101-B 작업 2 · 설계 CW 추천안 C · 확인 investigator 11-01 08:52~08:56)
- 실행: `implementer`(Sonnet · medium) → 검수 `verifier`(Opus · high)
- 승인 범위: 코드 4파일 · 테스트 2파일 · 문서 3개 · 커밋 1건. **`git push` 는 별도 승인.** 장부·`.env`·launchd 무변경.
- 선행: `[CC-1101-B]` 커밋(같은 날 등급 되돌림). B 가 아직이면 멈추고 보고.

## 배경

- 실제 영상 요약 중 모델 신호 `ai_related=false` 5편, 진짜 비 AI 는 `68zimAoOTcM`(작가용 워드프로세서) 1편뿐이다(정밀도 1/5). 오판 4건 `r98qvQYlrMc`·`5k0tCrXdIIM`·`VoqXu3oFsk4`·`0Ef6MaFg6b0` 은 모두 대표님이 손으로 keep 으로 되돌렸다 — 바이브코더 대상 개발·운영 정보, AI 로 만든 결과물 공유였다.
- 같은 5편에서 토픽 분류기는 사람 판정과 5/5 맞았다: 진짜 비 AI 만 토픽 `[]`, 오판 4건은 AI 토픽이 붙었다.
- 대표님 결정 11-01 08:49: 추천안 C — 코드 규칙만 좁힌다(v4.12 promo 의 AND 와 같은 방향, 지금보다 좁기만 함). 프롬프트·응답 스키마는 그대로.
- investigator 확인(사실):
  1. 신규 경로는 등급이 분류보다 먼저 정해진다 — `scheduler.js:938` `summarizer.summarize(v)` 안 `lib/video_summary.js:309` `computeGrade(p.signals)` → `scheduler.js:958` `classifyTopics` → `:1008` `saveToLibrary(…, sumMeta)`. 그래서 분류 뒤·저장 앞에 다시 매긴다.
  2. 분류가 실패(재시도 소진·401/403·깨진 JSON)하면 그 영상은 `❌ 오류` 로 저장되지 않는다(`scheduler.js:972`·`:994`·`:1060`). 빈 토픽은 모델이 `[]` 를 줬거나 allowedSet 이 전부 걸렀을 때뿐 — "분류 실패 → 빈 토픽 → not_ai 제외" 경로는 없다. 신뢰도 0.6 미만이어도 토픽은 저장된다(YouTube 추가만 건너뜀) → 신뢰도와 상관없이 저장되는 토픽이 있으면 "토픽 있음".
  3. 재요약 경로는 `lib/resummarize.js:93` `summarize(v)` 에서 등급이 정해지고, 후보 쿼리 `lib/library.js:122` 는 `topics` 를 읽지 않는다 → 후보에 장부 topics 를 실어 넘긴다(재분류 안 함).
  4. `computeGrade` 호출처는 코드 `video_summary.js:309` 1곳 + 테스트. 두 번째 인자를 선택으로 붙이면 기존 호출은 그대로(topics 를 안 넘기면 지금 규칙).
  5. 장부 `topics` 는 `TEXT NOT NULL DEFAULT '[]'`, JSON 간격이 행마다 다르다 — 판정은 `parseTopics`/배열 길이로, 문자열 비교 금지.

## 범위

- 바꿀 파일: `lib/video_summary.js` · `scheduler.js` · `lib/library.js` · `lib/resummarize.js` · `scripts/test_video_summary.js` · `scripts/test_resummarize.js` · `README.md` · `CLAUDE.md` · `AGENTS.md`
- 바꾸면 안 되는 것: `PROMPT`·`responseSchema`·`parseResponse`·promo 규칙(v4.12 AND)·`PROMO_SHARE_MIN` · 장부 스키마·기존 장부 등급(소급하지 않음) · 재시도·분량 규칙 · 분류기(`lib/classifier.js`) · 그 밖의 파일 · `.env` · launchd

## 확인(먼저) — 하나라도 다르면 멈추고 보고

| # | 명령 | 기대값 |
|---|---|---|
| 0-1 | `git log --oneline -2` | 맨 위 `[CC-1101-B] …`, 그 아래 `12eb52a [CC-1101-A] …` |
| 0-2 | `git status --porcelain -uall` | `?? docs/tasks/2026-11-01-v417-not-ai-topics.md` 한 줄 |
| 0-3 | `grep -n "^function computeGrade\|computeGrade(p.signals)\|if (!signals.ai_related) why.push('not_ai')" lib/video_summary.js` | `function computeGrade(signals) {` · `if (!signals.ai_related) why.push('not_ai');` · `const g = computeGrade(p.signals);` 세 줄 |
| 0-4 | `grep -n "const pageId = saveToLibrary(v, summary, allTopics, sumMeta)" scheduler.js` | 한 줄 |
| 0-5 | `grep -n "SELECT record_id, video_id, title, channel, quality FROM videos" lib/library.js` | 한 줄 (`resummaryCandidates`) |
| 0-6 | `scripts/run_all_tests.sh \| tail -1` | `RESULT: 15/15 통과` (video_summary 32/32 · resummarize 11/11) |

## 단계

코드 편집은 정시 실행·wiki-ingest 창(11:50~12:20 · 17:25~17:50 · 17:50~18:20)과 실행 중(`pgrep -f "scheduler.js|wiki_ingest.py|sync_obsidian.py"`)을 피한다. 훅이 막으면 시각을 보고하고 멈춘다.

### 1. `lib/video_summary.js` — `computeGrade` 에 선택 인자 `topics`

AS-IS
```js
function computeGrade(signals) {
  if (!signals) return { grade: null, why: [], note: '' };
  const why = [];
  let note = '';
  if (signals.promo_main) {
    const share = Number.isFinite(signals.promo_share) ? signals.promo_share : 0;
    if (share >= PROMO_SHARE_MIN || signals.promo_subject === true) why.push('promo_main');
    else note = `promo_minor ${share}`;
  }
  if (signals.generic) why.push('generic');
  if (!signals.ai_related) why.push('not_ai');
  return { grade: why.length ? 'exclude' : 'keep', why, note };
}
```
TO-BE
```js
function computeGrade(signals, topics) {
  if (!signals) return { grade: null, why: [], note: '' };
  const why = [];
  const notes = [];
  if (signals.promo_main) {
    const share = Number.isFinite(signals.promo_share) ? signals.promo_share : 0;
    if (share >= PROMO_SHARE_MIN || signals.promo_subject === true) why.push('promo_main');
    else notes.push(`promo_minor ${share}`);
  }
  if (signals.generic) why.push('generic');
  if (!signals.ai_related) {
    if (Array.isArray(topics) && topics.length) notes.push('not_ai_minor');
    else why.push('not_ai');
  }
  return { grade: why.length ? 'exclude' : 'keep', why, note: notes.join(', ') };
}
```
- 함수 위 주석 블록 끝에 한 줄: `// (v4.17) not_ai 는 토픽 분류도 비었을 때만 제외 사유다(오판 4/5 는 AI 토픽이 붙은 영상). topics 를 안 넘기면(모름) 지금처럼 제외 — 토픽이 있는데 ai_related=false 면 not_ai_minor 로 알린다.`
- `:309` `const g = computeGrade(p.signals);` → `const g = computeGrade(p.signals, v.topics);`
- 같은 파일에 헬퍼 1개(`computeGrade` 바로 아래) + `module.exports` 에 `regrade` 추가:
```js
// (v4.17) 신규 영상은 요약 시점에 토픽이 없다 — 분류 뒤 토픽으로 다시 매긴다. 영상 요약이 아니면 그대로
function regrade(meta, topics) {
  if (!meta || meta.src !== 'video' || !meta.quality) return { meta, note: '' };
  const q = JSON.parse(meta.quality);
  const g = computeGrade(q, topics);
  return { meta: { ...meta, grade: g.grade, quality: JSON.stringify({ ...q, why: g.why }) }, note: g.note };
}
```

### 2. `scheduler.js` — 분류 뒤·저장 앞에 다시 매김

AS-IS
```js
        // 장부 저장
        const pageId = saveToLibrary(v, summary, allTopics, sumMeta);
        log(`    ✓ 장부 저장 완료 (주제: ${allTopics.join(', ') || '(분류 없음)'} · 요약 ${sumMeta.src}${sumMeta.grade ? ` · ${sumMeta.grade}` : ''})`);
```
TO-BE
```js
        // (v4.17) 등급을 토픽으로 다시 매긴다 — not_ai 는 토픽도 비었을 때만
        const rg = videoSummary.regrade(sumMeta, topics);
        if (sumMeta.grade === 'exclude' && rg.meta.grade === 'keep') summarizer.stats.exclude--;
        if (rg.meta.grade !== sumMeta.grade || rg.note.includes('not_ai_minor')) {
          log(`    🎚  등급(토픽 반영): ${sumMeta.grade} → ${rg.meta.grade}${rg.note ? ` (${rg.note})` : ''}`);
        }

        // 장부 저장
        const pageId = saveToLibrary(v, summary, allTopics, rg.meta);
        log(`    ✓ 장부 저장 완료 (주제: ${allTopics.join(', ') || '(분류 없음)'} · 요약 ${rg.meta.src}${rg.meta.grade ? ` · ${rg.meta.grade}` : ''})`);
```
- 이 블록 아래에서 `sumMeta` 를 더 쓰는 곳이 있으면(grep) 같은 이유로 `rg.meta` 로 바꿀지 판단해 보고에 적는다 — 등급·quality 를 쓰는 곳만 바꾸고, 아니면 그대로.

### 3. `lib/library.js` · `lib/resummarize.js` — 재요약 후보에 장부 토픽

- `resummaryCandidates` 의 SELECT 에 `, topics` 를 더하고 `.all(limit)` → `.all(limit).map(r => ({ ...r, topics: parseTopics(r.topics) }))` (같은 파일의 기존 `parseTopics` 재사용).
- `lib/resummarize.js` 의 `const v = { videoId: c.video_id, … durationSec: d.durationSec };` 에 `topics: c.topics` 를 더한다. 재분류하지 않는다.

### 4. 테스트

- `scripts/test_video_summary.js` — 기존 v4.12 promo_minor 케이스 다음에 3개(통과 32 → 35):
  1. `(v4.17) computeGrade: not_ai 는 토픽이 비었을 때만` — `ai_related:false` 신호로: topics `[]` → exclude · why `['not_ai']`(68zimAoOTcM 꼴) / topics 미전달 → exclude · why `['not_ai']` / topics 있음 4꼴(`['AI 영상','AI 음악.음원','AI 자동화','AI 생산성 향상']`·`['AI 바이브코딩']`·`['AI 바이브코딩']`·`['AI 바이브코딩','AI 여행계획']`) → keep · why `[]` · note `not_ai_minor` / generic + 토픽 있음 → exclude · why `['generic']` · note `not_ai_minor` / promo_minor 와 함께 → note `promo_minor 0.03, not_ai_minor`.
  2. `(v4.17) regrade` — video exclude[not_ai] + 토픽 있음 → keep · quality 의 다른 키(promo_main·ai_related·model 등) 보존 · why `[]` / `src:'app'` 은 그대로 / 토픽 `[]` 면 exclude 그대로.
  3. `(v4.17) summarize 로그` — `V({…, topics:['AI 바이브코딩']})` + `ai_related:false` 신호 → 로그 끝 `→ keep (not_ai_minor)` · 결과 grade keep.
- `scripts/test_resummarize.js` — 1개(11 → 12): 임시 장부 행에 topics `["AI 바이브코딩"]` 를 넣고 가짜 요약기가 받은 `v.topics` 가 `['AI 바이브코딩']` 인지, topics 기본값 행이면 `[]` 인지. 기존 행 넣기 헬퍼에 topics 열을 선택으로 더하는 정도로.
- 기존 케이스 기대값은 바꾸지 않는다.

### 5. 문서

- `README.md`: 버전 이력 요약표 1행 + 상세 1절 `#### [v4.17] - 2026-11-01 (🎚 …)` — 배경(정밀도 1/5 · 토픽 분류 5/5)·규칙(`!ai_related && 토픽 0개`)·`not_ai_minor`·신규 경로 재판정 자리·재요약은 장부 토픽·장부 무변경·소급 안 함·테스트 수. 기존 표기 꼴을 따른다.
- `CLAUDE.md`·`AGENTS.md`(같은 내용):
  - 머리 `**현재 버전: v4.16** (2026-10-31)` → `**현재 버전: v4.17** (2026-11-01)`, 버전 요약 블록 끝에 `> v4.17: …` 한 줄.
  - 「실제 영상 요약·품질 필터」 절 `computeGrade` 문단에 v4.17 규칙 한두 문장 — 「`!ai_related` 하나라도면 exclude」 표현을 고치고, 신규 경로는 `🎬 … → exclude [not_ai]` 가 요약 시점의 임시 값이며 최종 등급은 `🎚 등급(토픽 반영)`·`✓ 장부 저장 완료 … · keep` 줄로 본다는 것, 분야형 토픽(「AI 여행계획」 등)이 비 AI 영상에 붙으면 keep 이 되므로 `not_ai_minor` 로 관찰한다는 것. "이 조건을 OR 로 되돌리거나 토픽 없이 not_ai 를 끄지 말 것".
  - 「Commands」 회귀 테스트 줄의 `test_video_summary.js` `32/32` → `35/35`, `test_resummarize.js` `11/11` → `12/12`(설명 끝에 `· (v4.17) not_ai 토픽 조건`·`· (v4.17) 후보 토픽`).
  - 「변경 이력」 맨 위에 1항목(날짜·배경·수정·테스트·지시서 경로). 그리고 지금 맨 위 두 항목(v4.16 · 운영 체계 전환) 사이에 남아 있는 빈 줄 1개를 지운다([CC-1031-A] 잔여 — 변경 이력 항목 사이에는 빈 줄이 없다).
- 문서에 개인 절대경로·맥 이름을 쓰지 않는다.

### 6. 확인

```bash
scripts/run_all_tests.sh | tail -3          # RESULT: 15/15 통과
/opt/homebrew/bin/node scripts/test_video_summary.js | tail -1   # 35/35
/opt/homebrew/bin/node scripts/test_resummarize.js | tail -1     # 12/12
node -e "const g=require('./lib/video_summary').computeGrade;for(const t of [[],['AI 바이브코딩']])console.log(JSON.stringify(g({ai_related:false,promo_main:false,generic:false},t)))"
```
마지막 줄 기대: `{"grade":"exclude","why":["not_ai"],"note":""}` · `{"grade":"keep","why":[],"note":"not_ai_minor"}`.

### 7. 커밋

```bash
git add lib/video_summary.js scheduler.js lib/library.js lib/resummarize.js scripts/test_video_summary.js scripts/test_resummarize.js README.md CLAUDE.md AGENTS.md docs/tasks/2026-11-01-v417-not-ai-topics.md
git commit -m "[CC-1101-C] v4.17 not_ai 제외는 토픽 분류도 비었을 때만 — 신규는 분류 뒤 재판정, 재요약은 장부 토픽 (장부 무변경)"
```

## 기준표

| # | 기준 |
|---|---|
| 1 | 0-1~0-6 기대값 일치 |
| 2 | `computeGrade(signals, topics)`: `!ai_related` 이고 토픽 배열이 비었거나 없을 때만 why `not_ai`. 토픽 있음 + `!ai_related` → why 에 not_ai 없음 · note `not_ai_minor`. promo·generic 규칙 무변경 |
| 3 | 신규 경로: 분류 뒤 `regrade` → `saveToLibrary` 에 `rg.meta` · exclude→keep 이면 `stats.exclude` −1 · 바뀌었거나 not_ai_minor 면 `🎚 등급(토픽 반영)` 로그 |
| 4 | 재요약 경로: 후보에 장부 topics(parseTopics) → `summarize(v)` 의 `v.topics` · 재분류 없음 |
| 5 | 표본 5건 단위 테스트: 토픽 `[]` exclude · 토픽 있는 4꼴 keep. 기존 케이스 기대값 무변경 |
| 6 | `scripts/run_all_tests.sh` → `RESULT: 15/15 통과` · video_summary 35/35 · resummarize 12/12 · 6단계 node 두 줄 기대값 |
| 7 | 범위 밖 파일 변경 없음 · PROMPT·responseSchema·parseResponse·promo 규칙·장부 스키마 diff 없음 · 장부 쓰기 0 |
| 8 | README 요약표 1행 + 상세 1절 · CLAUDE.md·AGENTS.md v4.17 동기(머리 버전·요약 줄·품질 필터 문단·테스트 수·이력 1항목·빈 줄 정리) · 개인 경로·맥 이름 추가 없음 · README.html 없음 |
| 9 | 커밋 1건(위 10파일) · push 안 함 |

## 하지 말 것

- 프롬프트·응답 스키마·신호 이름 변경, promo 규칙 변경, `lib/classifier.js` 변경
- 기존 장부 등급 소급(재판정 스크립트·UPDATE), 장부 쓰기
- 토픽 없이 not_ai 를 끄거나(예: summarize 에서 topics 가 없으면 not_ai 생략) 규칙을 scheduler 에 따로 두기 — 규칙은 `computeGrade` 한 곳
- 실제 Gemini 호출·`node scheduler.js` 실행, `.env`·launchd 변경, `git push`

## 롤백

`git revert <커밋>` — 장부 무변경이라 코드만 되돌리면 된다. 그 사이 새 규칙으로 keep 이 된 영상은 장부에 남는다(필요하면 `grade` 를 지시서로 되돌림).

## 범위 밖

- 다음 정시 실행들에서 `🎚 등급(토픽 반영)`·`(not_ai_minor)` 빈도, 분야형 토픽이 비 AI 영상을 살리는지 — CW 관찰(XP 요청서로).
- 대안 B(새 신호 `ai_context`)·A(프롬프트 문구) — C 로 부족할 때만.
