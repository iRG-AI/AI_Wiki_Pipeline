# [CC-1101-D] 재요약 실행당 상한 10 → 20 (`.env` 한 줄, 하루 40 유지 · 코드 무변경)

- 작성: 2026-11-01 11:45 KST (pm-wiki)
- 승인: 대표님 2026-11-01 「A로 진행하자」(investigator 조사 보고의 4-A안)
- 실행: implementer · 검수: verifier
- 버전: 유지(운영 값 + 문서). README 무변경.

## 배경
investigator 조사(11-01, 읽기 전용) — PT 10-16~10-30 재요약 합계 335편(장부 `quality.resummary_day` 와 로그 일치), 하루 평균 22.3편.
- 실제 천장: 3.5 Flash-Lite 모델 누계 28,800초 ÷ 편당 평균 858초 ≈ 하루 33.6편. `RESUMMARY_DAILY_MAX` 40 에는 구조상 닿지 않는다.
- 40 대비 부족 265편 = 503 한 번에 그 실행 재요약 중단 138(52%) · 통째 실패(ENOTFOUND, 잠자기 추정) 70(26%) · 실행 누락 30(11%) · 분량 상한 27(10%). 429·건너뜀/실패로 빠진 편수 0.
- 실행당 몫(10)이 하루 몫(40)의 1/4 이라, 앞 실행이 빠지거나 503 으로 멈춘 날은 다음 실행이 채울 수 없다. 실행당 20 이면 같은 PT 하루의 다음 실행이 남은 몫을 채운다(이월 코드 불필요). 추정 효과 하루 약 22 → 26~27편.
- 실행당 몫은 성공 편수(`res.done`)만 센다(`lib/resummarize.js`). 하루 요청 총량은 40 그대로.

## 수행 범위
- 바꿔도 되는 것: `.env` 의 `RESUMMARY_PER_RUN` 줄 값 하나 · `CLAUDE.md`·`AGENTS.md` 의 아래 지정 줄 · 이 지시서.
- 바꾸면 안 되는 것: 코드·장부·launchd·다른 `.env` 키·README. `.env` 의 다른 줄 값을 출력하지 말 것(키 이름만).

## 단계
1. 사전 확인 — 지금 시각이 매시 분 21~49 이고 `pgrep -f scheduler.js` 가 비어 있어야 한다. 아니면 멈추고 보고.
2. 백업 — `cp -p .env .env.bak.20261101`
3. 변경 — `.env` 의 `RESUMMARY_PER_RUN=` 줄 값만 `20` 으로(줄 끝 주석이 있으면 유지). 다른 줄 무변경.
4. 확인 —
   - `diff .env.bak.20261101 .env` 가 `RESUMMARY_PER_RUN` 한 줄만(10 → 20).
   - `node -e "const fs=require('fs');const e={};for(const l of fs.readFileSync('.env','utf8').split('\n')){const m=l.match(/^\s*(RESUMMARY[A-Z_]*)\s*=\s*([^#\s]*)/);if(m)e[m[1]]=m[2]}const s=require('./lib/resummarize').settings(e);console.log(JSON.stringify({enabled:s.enabled,perRun:s.perRun,dailyMax:s.dailyMax}))"` → `perRun` 20 · `dailyMax` 40 · `enabled` true.
   - `git check-ignore -q .env.bak.20261101` 통과(커밋되지 않음).
5. 문서 — `CLAUDE.md`·`AGENTS.md` 두 곳 모두 같은 내용으로:
   - 「기존분 재요약」 절의 `- 처리량: 하루 약 19편 …` 한 줄을 아래 줄로 바꾼다.
     ```
     - 처리량: (11-01 실측, PT 10-16~10-30) 하루 평균 22.3편. 실제 천장은 3.5 Flash-Lite 모델 누계 8시간 ÷ 편당 약 858초 ≈ 하루 33.6편이라 `RESUMMARY_DAILY_MAX` 40 에는 닿지 않는다. 부족분은 503 중단 52% · 통째 실패(잠자기·ENOTFOUND) 26% · 실행 누락 11% · 분량 상한 10%. `.env` 는 실행당 20 · 하루 40(11-01~) — 실행당 몫을 하루 몫의 절반으로 둬 앞 실행이 빠지거나 503 으로 멈춘 날 같은 PT 하루의 다음 실행이 채운다. 천장을 넘기려면 모델 누계 상한(v4.13)을 건드려야 한다 — 대표님 결정 사항(시험 필요).
     ```
   - 「변경 이력」 맨 위(v4.17 항목 앞)에 한 줄:
     ```
     - **2026-11-01 (운영 값, 버전 유지)** — `.env RESUMMARY_PER_RUN` 10 → 20(하루 `RESUMMARY_DAILY_MAX` 40 유지). 배경: 재요약 하루 평균 22.3편(PT 10-16~10-30, 장부·로그 일치) — 천장 약 33.6편(3.5 Flash-Lite 8시간 ÷ 편당 858초), 부족분 503 중단 52% · 통째 실패 26% · 누락 11% · 분량 상한 10%. 실행당 몫을 키워 빠진 실행의 몫을 같은 하루 다음 실행이 채운다(추정 하루 26~27편). 코드·장부 무변경. 백업 `.env.bak.20261101`. 지시서 `docs/tasks/2026-11-01-resummary-per-run-20.md`.
     ```
   - 「운영 체계 전환」 항목과 「v4.15」 항목 사이의 빈 줄 1개 삭제(현재 CLAUDE.md 639행 · AGENTS.md 641행 — 줄 번호는 위 추가로 1 밀린다).
6. 커밋 — `git add docs/tasks/2026-11-01-resummary-per-run-20.md CLAUDE.md AGENTS.md` → 메시지 `[CC-1101-D] 재요약 실행당 상한 10 → 20 (.env 운영 값 · 하루 40 유지 · 코드·장부 무변경)`. push 하지 않는다.

## 완료 기준 (verifier)
| # | 기준 | 확인 방법 |
|---|---|---|
| 1 | 사전 확인을 지켰다 | implementer 보고의 시각·`pgrep` 출력 |
| 2 | `.env` 는 `RESUMMARY_PER_RUN` 한 줄만 10 → 20 | `diff .env.bak.20261101 .env` (그 한 줄만 보일 것) |
| 3 | 설정값 perRun 20 · dailyMax 40 · enabled true | 단계 4 의 node 명령 |
| 4 | 백업이 gitignore | `git check-ignore -q .env.bak.20261101` |
| 5 | 문서 두 곳이 지시 문구대로, 두 문서의 변경 diff 동일 | `git show HEAD -- CLAUDE.md` · `-- AGENTS.md` 비교 |
| 6 | 빈 줄 1개 삭제, 그 밖 문서 변경 없음 | `git show --stat HEAD` = 3파일 |
| 7 | 회귀 15종 | `scripts/run_all_tests.sh` 마지막 줄 `RESULT: 15/15 통과` |
| 8 | 커밋 1건, push 안 함 | `git status -sb` ahead 1 |

## 운영 확인 (CW, 다음 정시 실행 뒤)
- 18시 실행 `🔁 재요약: N편 … 오늘 N/40` 에서 N 이 10 을 넘을 수 있는지(앞 실행이 덜 했으면 최대 20).
- 7일 관찰: 하루 편수(장부 `resummary_day`) · `daily_video_cap` 빈도 · 429 줄 수 · 실행 시간.

## 되돌리기
`.env.bak.20261101` 를 `.env` 로 복사(정시 실행 창 밖). 재기동 불필요 — 매 실행이 `.env` 를 새로 읽는다.
