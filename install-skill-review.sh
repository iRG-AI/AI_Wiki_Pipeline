#!/bin/bash
# 매일 Wiki 검토 — launchd 설치 스크립트 (매일 08:30 skill_review.py)
# plist 는 레포 원본을 그대로 복사한다(절대경로 포함)

set -e

PLIST_NAME="com.irichgreen.skill-review"
PLIST_SRC="$(cd "$(dirname "$0")" && pwd)/${PLIST_NAME}.plist"
PLIST_DST="$HOME/Library/LaunchAgents/${PLIST_NAME}.plist"

echo "🧭 매일 Wiki 검토 스케줄러 설치"
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
echo "  📅 실행 시간: 매일 08:30 (지난 검토 이후 들어온 영상·꿀팁 → 제안 0~3건)"
echo "  🐍 인터프리터: /opt/homebrew/bin/python3"
echo "  📁 로그: ~/Library/Logs/irichgreen/skill-review.log (판정 지표: RESULT_JSON 줄)"
echo "  🖥  제안함: http://localhost:3000/wiki#tab=proposals"
echo ""
echo "  수동 실행: launchctl start $PLIST_NAME"
echo "  제거:      launchctl unload $PLIST_DST"
