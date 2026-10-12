#!/bin/bash
# Karpathy LLM Wiki Ingest — launchd 설치 스크립트
# 매일 17:30(= 태평양시 01:30, Gemini 무료 일 한도 리셋 직후)에 증분 실행. 일일 한도에 걸리면 그날은 멈추고 다음 날 이어서 한다
# plist 는 레포 원본을 그대로 복사한다(절대경로 포함) — 원본은 실제 설치본과 같게 유지한다(2026-10-12 동기화)

set -e

PLIST_NAME="com.irichgreen.wiki-ingest"
PLIST_SRC="$(cd "$(dirname "$0")" && pwd)/${PLIST_NAME}.plist"
PLIST_DST="$HOME/Library/LaunchAgents/${PLIST_NAME}.plist"

echo "🧠 Karpathy Wiki Ingest 스케줄러 설치"
echo ""

# 기존 제거
if launchctl list | grep -q "$PLIST_NAME" 2>/dev/null; then
  echo "  ⏹  기존 스케줄 제거 중..."
  launchctl unload "$PLIST_DST" 2>/dev/null || true
fi

# 복사 및 등록
cp "$PLIST_SRC" "$PLIST_DST"
launchctl load "$PLIST_DST"

echo "  ✅ 설치 완료!"
echo ""
echo "  📅 실행 시간: 매일 17:30 (증분 — 미처리 노트만)"
echo "  🐍 인터프리터: /opt/homebrew/bin/python3"
echo "  📁 로그: ~/Library/Logs/irichgreen/wiki-ingest.log (판정 지표: WIKI_RESULT 줄)"
echo ""
echo "  수동 실행: launchctl start $PLIST_NAME"
echo "  상태 확인: cat .wiki_quota.json"
echo "  제거:      launchctl unload $PLIST_DST"
