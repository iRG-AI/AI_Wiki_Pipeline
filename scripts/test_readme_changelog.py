#!/usr/bin/env python3
"""README 요약표 ↔ docs/changelog 월별 파일 구조 검사 (v4.19.2). 읽기만 · 네트워크 0.

    /opt/homebrew/bin/python3 scripts/test_readme_changelog.py
    CHANGELOG_TEST_ROOT=<사본 폴더> ...   # 저장소 대신 사본을 검사 (시험용)
"""
import os
import re
import sys
from pathlib import Path

ROOT = Path(os.environ.get('CHANGELOG_TEST_ROOT') or Path(__file__).resolve().parent.parent)
README = ROOT / 'README.md'
CL = ROOT / 'docs' / 'changelog'
VER = r'v\d+\.\d+\.\d+(?:-[a-z])?'
results = []


def key(v):
    m = re.fullmatch(r'v(\d+)\.(\d+)\.(\d+)(?:-([a-z]))?', v)
    return (int(m[1]), int(m[2]), int(m[3]), m[4] or '')


def anchor(v):
    return v.replace('.', '-')


def desc(seq):  # 엄격 내림차순 위반 지점 목록
    return [f'{a} → {b}' for a, b in zip(seq, seq[1:]) if not key(a) > key(b)]


def check(name, errs):
    ok = not errs
    results.append(ok)
    print(f"  {'✅' if ok else '❌'} {name}")
    for e in errs[:8]:
        print(f'      - {e}')


text = README.read_text(encoding='utf-8')
m = re.search(r'^### 🕒 요약 이력 \(Summary Table\)\n(.*?)(?=^### |\Z)', text, re.S | re.M)
table = m.group(1) if m else ''
rows = [l for l in table.splitlines() if l.startswith('|')][2:]  # 머리글·구분선 뒤
cells = [[c.strip() for c in re.split(r'(?<!\\)\|', l.strip()[1:-1])] if l.rstrip().endswith('|') else [] for l in rows]

heads = []  # (파일, 버전, 날짜, 윗줄)
files = sorted(p for p in CL.glob('*') if p.name != 'README.md') if CL.is_dir() else []
for p in files:
    lines = p.read_text(encoding='utf-8').splitlines()
    for i, l in enumerate(lines):
        h = re.match(rf'#### \[({VER})\] - (\d{{4}}-\d{{2}})-\d{{2}}', l)
        if h:
            heads.append((p, h[1], h[2], lines[i - 1] if i else ''))
        elif l.startswith('#### [v'):
            heads.append((p, 'BAD:' + l[:40], '', ''))

print('README 요약표 ↔ docs/changelog')
check('C1 README 에 상세 블록(#### [v) 0', [f'README 줄: {l[:50]}' for l in text.splitlines() if l.startswith('#### [v')])

e = [] if m else ['요약표 절 없음']
for r, c in zip(rows, cells):
    if len(c) != 3:
        e.append(f'3칸 아님({len(c)}): {r[:60]}')
    elif len(c[2]) > 120:
        e.append(f'제목 {len(c[2])}자: {c[0][:30]}')
check('C2 요약표 한 줄 3칸 · 제목 120자 이하', e)

tv = [re.match(rf'\*\*\[({VER})\]', c[0])[1] if len(c) == 3 and re.match(rf'\*\*\[({VER})\]', c[0]) else '?' + c[0][:20] for c in cells]
check('C3 요약표 버전 엄격 내림차순', [f'버전 아님: {v}' for v in tv if v[0] == '?'] or desc(tv))

e = []
for v, c in zip(tv, cells):
    lk = re.search(r'\]\(docs/changelog/(\d{4}-\d{2})\.md#([^)]+)\)', c[0]) if len(c) == 3 else None
    if not lk:
        e.append(f'{v}: 링크 형식 아님'); continue
    f = CL / f'{lk[1]}.md'
    base = anchor(v)
    if lk[2] not in (base, base + '-2'):
        e.append(f'{v}: 앵커 {lk[2]} ≠ {base}')
    if not f.is_file() or f'<a id="{lk[2]}"></a>' not in f.read_text(encoding='utf-8'):
        e.append(f'{v}: {f.name} 에 앵커 {lk[2]} 없음')
    if lk[1] != c[1][:7]:
        e.append(f'{v}: 링크 달 {lk[1]} ≠ 행 날짜 {c[1]}')
check('C4 요약표 링크 파일·앵커·달', e)

e = [f'{p.name}: 이름이 YYYY-MM.md 아님' for p in files if not re.fullmatch(r'\d{4}-\d{2}\.md', p.name)]
for p, v, mo, up in heads:
    if v.startswith('BAD:'):
        e.append(f'{p.name}: 헤딩 형식 {v[4:]}')
    elif not re.fullmatch(rf'<a id="{re.escape(anchor(v))}(-2)?"></a>', up.strip()):
        e.append(f'{p.name} {v}: 윗줄이 앵커 아님 ({up[:30]})')
check('C5 월 파일 이름 · 헤딩 윗줄 앵커', e)

ids = [a for p in files for a in re.findall(r'<a id="([^"]+)"></a>', p.read_text(encoding='utf-8'))]
check('C6 앵커 전체 중복 0', sorted({a for a in ids if ids.count(a) > 1}))

e = []
for p in files:
    hv = [(v, mo) for q, v, mo, _ in heads if q == p and not v.startswith('BAD:')]
    e += [f'{p.name} {v}: 날짜 달 {mo} ≠ 파일 달' for v, mo in hv if mo + '.md' != p.name]
    e += [f'{p.name}: {x}' for x in desc([v for v, _ in hv])]
check('C7 헤딩 날짜 = 파일 달 · 파일 안 내림차순', e)

hs = [v for _, v, _, _ in heads if not v.startswith('BAD:')]
e = [f'요약표에만 {v}' for v in sorted(set(tv) - set(hs))] + [f'월 파일에만 {v}' for v in sorted(set(hs) - set(tv))]
if files and tv and hs:
    first = next(v for p in reversed(files) for _, v, _, _ in [h for h in heads if h[0] == p][:1])
    if tv[0] != first:
        e.append(f'맨 위 행 {tv[0]} ≠ 최근 달 파일 맨 위 {first}')
check('C8 요약표 버전 집합 = 월 파일 · 맨 위 일치', e)

check('C9 README.html 없음', ['README.html 있음'] if (ROOT / 'README.html').exists() else [])

print(f'\n{sum(results)}/{len(results)}')
sys.exit(0 if all(results) else 1)
