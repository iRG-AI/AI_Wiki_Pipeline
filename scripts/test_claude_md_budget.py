#!/usr/bin/env python3
"""CLAUDE.md 크기·구조 가드 (v4.19.6). 읽기만 · 네트워크 0.

    /opt/homebrew/bin/python3 scripts/test_claude_md_budget.py
    CLAUDE_MD_TEST_ROOT=<사본 폴더> ...   # 저장소 대신 사본을 검사 (시험용)
"""
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get('CLAUDE_MD_TEST_ROOT') or Path(__file__).resolve().parent.parent)
CLAUDE = ROOT / 'CLAUDE.md'
BG = ROOT / 'docs' / 'claude_md_background.md'
HIST = ROOT / 'docs' / 'claude_history.md'

# 2026-11-08: 이 커밋의 CLAUDE.md 92,733B + 3,000B. 올리지 말고 경위·이력은 배경·이력 파일로 보낸다.
ROOT_LIMIT = 95733

# 다른 파일이 이름으로 가리키는 절 (CLAUDE.md 「…」 인용: README·scripts·.claude 를 grep 해 찾음).
#  - 산출물 규칙 / 중요한 제약사항 : .claude/agents·README·docs/changelog/README.md 가 인용
#  - 보안·launchd·운영 체계·변경 이력·핵심 파일 역할 : 훅·PM_ROLE·scribe 등이 가리킨다
#  - 「정시 실행 창」 「회귀 15종」 은 제목이 아니라 훅의 옛 표현이라 넣지 않는다 (훅 문구 정정은 별건)
REQUIRED = [
    '## 🚨 보안 및 안전 최우선 개발 원칙 (Security & Safety Guidelines)',
    '### 중요한 제약사항',
    '### launchd 데몬',
    '## 운영 체계 — pm-wiki · 워커 · Cowork (2026-10-31~)',
    '## 산출물 규칙',
    '## 변경 이력',
    '### 핵심 파일 역할',
]
V_LINES = ['> v4.10:', '> v4.12:', '> v4.18:', '> v4.19:']
results = []


def check(name, errs):
    ok = not errs
    results.append(ok)
    print(f"  {'✅' if ok else '❌'} {name}")
    for e in errs[:8]:
        print(f'      - {e}')


print('CLAUDE.md 크기 가드')
raw = CLAUDE.read_bytes() if CLAUDE.is_file() else b''
text = raw.decode('utf-8', 'replace')
lines = text.splitlines()
bg = BG.read_text(encoding='utf-8') if BG.is_file() else ''

check('D1 루트 크기 ≤ 상한', [] if raw and len(raw) <= ROOT_LIMIT else [
    f'루트가 커졌습니다 — 경위는 docs/claude_md_background.md, 운영 이력은 docs/claude_history.md 로 ({len(raw)} > {ROOT_LIMIT})'])

check('D2 필수 제목', [f'제목 없음: {t}' for t in REQUIRED if t not in lines])

anchors = re.findall(r'<a id="(bg-[^"]+)"></a>', bg)
links = set(re.findall(r'claude_md_background\.md#(bg-[\w-]+)', text))
e = [f'배경 파일에 앵커 없음: {a}' for a in sorted(links) if a not in anchors]
e += [f'앵커 중복: {a}' for a in sorted({a for a in anchors if anchors.count(a) > 1})]
check('D3 배경 앵커 링크 · 중복 0', e)

e = []
if not HIST.is_file() or HIST.read_text(encoding='utf-8').split('\n', 1)[0] != '# CLAUDE.md 운영 이력':
    e.append('docs/claude_history.md 없음 또는 첫 줄이 「# CLAUDE.md 운영 이력」 아님')
if '## 변경 이력' in lines:
    tail = [l for l in lines[lines.index('## 변경 이력') + 1:] if l.strip()]
    if len(tail) != 1:
        e.append(f'「## 변경 이력」 아래 비어 있지 않은 줄 {len(tail)}개 (포인터 1줄만): ' + ' / '.join(l[:30] for l in tail[:3]))
check('D4 운영 이력은 history 파일 · 루트엔 포인터만', e)

e = []
# gitignore 된 사본(Claude outputs/ 등)은 대상이 아니다 — 11-08 PM 결정. git 이 아니면(시험 사본) 폴더를 걷는다.
g = subprocess.run(['git', '-C', str(ROOT), 'ls-files', '--', '*CLAUDE.md'], capture_output=True, text=True)
if g.returncode == 0 and (ROOT / '.git').exists():
    subs = [ROOT / f for f in g.stdout.splitlines()]
else:
    subs = [Path(d) / f for d, ds, fs in os.walk(ROOT) if not ds.__setitem__(slice(None), [x for x in ds if x not in ('node_modules', '.git')]) for f in fs if f == 'CLAUDE.md']
for p in subs:
    rel = p.relative_to(ROOT)
    if p == CLAUDE or p.name != 'CLAUDE.md':
        continue
    first = p.read_text(encoding='utf-8').split('\n', 1)[0]
    if first != f'# {rel.parent.name} 지침 — 루트 CLAUDE.md 와 함께 읽힌다':
        e.append(f'{rel}: 첫 줄 형식 틀림')
check('D5 하위 CLAUDE.md 첫 줄', e)

head = []
for l in lines:
    if l.startswith('## '):
        break
    if l.startswith('> v'):
        head.append(l)
got = [next((v for v in V_LINES if l.startswith(v)), l[:20]) for l in head]
check('D6 머리 버전 요약 인용 줄 고정', [] if got == V_LINES else [
    f'버전 요약 인용 줄은 docs/claude_md_background.md#bg-versions 맨 아래에 (지금 {got})'])

print(f'\n{sum(results)}/{len(results)}')
sys.exit(0 if all(results) else 1)
