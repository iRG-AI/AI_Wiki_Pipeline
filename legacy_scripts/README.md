# legacy_scripts — 은퇴한 스크립트 보관

실행 대상이 아니다. 고칠 때 참고하거나 되돌릴 때만 연다. 상대 경로(`./lib/…`, `.env`)가 레포 루트 기준이라 이 폴더에서는 그대로 돌지 않는다.

| 파일 | 은퇴 시점 | 이유 |
|---|---|---|
| `sync_obsidian.py`, `build_obsidian_wiki.py` | v2.x | 구버전 사본 |
| `clean_pending_queue.js` | v3.x | 구버전 사본 (현행은 `scripts/clean_pending_queue.js`) |
| `migrate_classify.js` | v4.0 (2026-10) | 노션 DB 를 읽고 고치는 일괄 재분류. 원본이 로컬 장부(`data/library.db`)로 바뀜 |
| `check_duplicates.py`, `cleanup_duplicates.py` | v4.0 | 노션 중복 점검·정리. 장부는 `videos.video_id` UNIQUE 로 중복을 막고, 옛 중복은 `videos_dup` 에 보관 |
| `fix_nfc_topics.js` | v4.0 | 노션 주제 NFC 일괄 교정. 장부는 쓰는 순간 NFC |
| `notion_to_obsidian.js` | v4.0 | 노션 → Obsidian 일회성 이관. 지금은 `sync_obsidian.py` 가 장부에서 만든다 |
