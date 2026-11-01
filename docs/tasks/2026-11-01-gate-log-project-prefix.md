# [CC-1101-E] 게이트 로그 경로에 프로젝트 이름 넣기 · verifier 의 `ls -t` 대체 규칙 삭제 (훅·문서만)

- 작성: 2026-11-01 16:35 KST (pm-wiki)
- 승인: 대표님 2026-11-01 「승인」
- 실행: implementer · 검수: verifier
- 버전: 유지(운영 체계). README 무변경.

## 배경
pm-cnc 알림(11-01): 게이트 로그 이름 `/tmp/cc-gate-<세션ID>.*` 가 여러 프로젝트에서 같은 꼴이라, CNC verifier 가 다른 프로젝트(asset_manage) 세션 로그를 자기 것으로 읽었다(CNC 커밋 54a14ef 에서 수정). 이 레포도 같은 훅을 쓰고, `.claude/agents/verifier.md:31` 에 "없으면 `ls -t /tmp/cc-gate-*.log | head -1`" 대체 규칙이 있어 같은 오독이 날 수 있다.

## 수행 범위
- 바꿔도 되는 것: `.claude/hooks/record_base.sh` · `.claude/hooks/gate_subagent_stop.sh` · `.claude/agents/verifier.md` · `.claude/pm/PM_ROLE.md` · `CLAUDE.md` · `AGENTS.md` 의 아래 지정 자리 · 이 지시서.
- 바꾸면 안 되는 것: 코드·장부·`.env`·launchd·`.claude/settings.json`·훅의 검사 논리. `/tmp` 의 옛 파일은 지우지 않는다.

## 단계
1. 사전 확인 — 지금 시각이 17:25 전이어야 한다(17:25~ wiki-ingest·18시 실행 창에 훅이 편집을 막는다). 아니면 멈추고 보고.
2. `record_base.sh` — 11행 `base_file="/tmp/cc-gate-${sid}.base"` → `base_file="/tmp/cc-gate-AI_Wiki_Pipeline-${sid}.base"`.
3. `gate_subagent_stop.sh` — `/tmp/cc-gate-${sid}` 로 시작하는 경로 4곳(16·24·34·93행)을 모두 `/tmp/cc-gate-AI_Wiki_Pipeline-${sid}` 로. 5행 머리 주석 `/tmp/cc-gate-<세션>.log` → `/tmp/cc-gate-AI_Wiki_Pipeline-<세션>.log`. 이력 주석(7행) 아래에 한 줄: `# 2026-11-01 — 로그·기준점·카운터 경로에 프로젝트 이름(다른 프로젝트 세션 로그 오독 방지, pm-cnc 알림)`. 그 밖 무변경.
4. `verifier.md` 31행 — 게이트 로그 항목 첫 부분을 아래로 바꾼다(뒤 문장 "implementer 가 보고한 …" 부터는 그대로):
   `- **게이트 로그:** `/tmp/cc-gate-AI_Wiki_Pipeline-<세션ID>.log` — PM 이 넘긴 세션 ID 로 정확히 연다. `ls -t` 등으로 최근 파일을 고르지 않는다(다른 프로젝트·세션 로그일 수 있다). 세션 ID 를 못 받았으면 ⚠️ 로 표시하고 PM 에 요청.`
   그리고 "파일이 없으면 \"차단 없음\"." 은 유지.
5. `PM_ROLE.md` 81행 — `/tmp/cc-gate-<세션ID>.log` → `/tmp/cc-gate-AI_Wiki_Pipeline-<세션ID>.log`(verifier 호출 때 세션 ID 를 넘긴다는 말이 없으면 문장 끝에 `— verifier 에 세션 ID 를 넘긴다` 추가).
6. `CLAUDE.md`·`AGENTS.md` 두 곳 같은 내용으로:
   - 「운영 체계」 절 훅 줄의 `(/tmp/cc-gate-<세션>.log)` → `(/tmp/cc-gate-AI_Wiki_Pipeline-<세션>.log)`.
   - 「변경 이력」 맨 위(`2026-11-01 (운영 값, 버전 유지)` 항목 앞)에 한 줄:
     ```
     - **2026-11-01 (운영 체계, 버전 유지)** — 게이트 로그·기준점·카운터 경로를 `/tmp/cc-gate-<세션>` → `/tmp/cc-gate-AI_Wiki_Pipeline-<세션>`(`record_base.sh`·`gate_subagent_stop.sh`), verifier 의 `ls -t /tmp/cc-gate-*.log` 대체 규칙 삭제(세션 ID 로만 연다). 배경: 같은 꼴의 이름을 쓰는 다른 프로젝트에서 verifier 가 남의 세션 로그를 읽은 일(pm-cnc 알림, CNC 54a14ef). 코드·장부 무변경. 지시서 `docs/tasks/2026-11-01-gate-log-project-prefix.md`.
     ```
7. 확인 — `bash -n` 두 훅 · `grep -rn 'cc-gate-\${sid}\|cc-gate-<세션\|cc-gate-\*' .claude CLAUDE.md AGENTS.md` 가 0줄(이 지시서·`docs/tasks/` 제외) · `grep -c 'cc-gate-AI_Wiki_Pipeline-' .claude/hooks/gate_subagent_stop.sh` = 5(주석 1 + 경로 4).
   - 모의 실행: `echo '{"session_id":"cc1101e-test"}' | .claude/hooks/record_base.sh && ls /tmp/cc-gate-AI_Wiki_Pipeline-cc1101e-test.base && rm /tmp/cc-gate-AI_Wiki_Pipeline-cc1101e-test.base`.
8. 커밋 — `git add` 위 6파일 + 이 지시서 → 메시지 `[CC-1101-E] 게이트 로그 경로에 프로젝트 이름 · verifier ls -t 대체 규칙 삭제 (훅·문서만, 코드·장부 무변경)`. push 하지 않는다.

※ 이번 세션 안에서는 implementer 시작 때 옛 경로 기준점이 이미 있어(같은 세션의 앞 워커) 새 게이트가 기준점을 못 찾고 HEAD 로 떨어진다 — 커밋한 뒤 멈추면 게이트 검사가 비어 통과한다. 그래서 verifier 가 `bash -n`·공개 레포 규칙을 직접 본다(기준 3·5).

## 완료 기준 (verifier)
| # | 기준 | 확인 방법 |
|---|---|---|
| 1 | 사전 확인(17:25 전) | implementer 보고 시각 · `git log -1 --format=%cd` |
| 2 | 옛 경로 표기 0, 새 경로가 훅 2개 전부 | 단계 7 grep 두 줄 |
| 3 | 두 훅 문법 · 모의 실행에서 새 경로에 기준점 생성 | `bash -n` · 단계 7 모의 실행 재현 |
| 4 | verifier.md 에 `ls -t` 없음, "세션 ID 로 정확히" 문구 | `grep -n 'ls -t\|세션 ID' .claude/agents/verifier.md` |
| 5 | 공개 레포 규칙(개인 절대경로·맥 이름 없음) | `git show HEAD` 의 `+` 줄 |
| 6 | CLAUDE.md·AGENTS.md diff 동일, 지정 2자리만 | `git show HEAD -- CLAUDE.md` · `-- AGENTS.md` 비교 |
| 7 | 훅 검사 논리 무변경(경로 문자열·주석만) | `git show HEAD -- .claude/hooks/` |
| 8 | 커밋 1건 7파일, push 안 함 | `git show --stat HEAD` · `git status -sb` ahead 1 |

## 되돌리기
`git revert <커밋>`. `/tmp` 옛 파일은 그대로라 되돌린 뒤에도 동작한다.
