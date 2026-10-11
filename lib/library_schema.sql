-- v4.0 로컬 원본 장부 (data/library.db) — 스키마 원본은 이 파일 하나다.
-- Python(sqlite3)·Node(node:sqlite) 양쪽이 이 파일을 그대로 실행한다. 열을 바꾸면 user_version 을 올린다.
--
-- record_id : 노션에서 옮긴 행 = 노션 page id(하이픈 포함, Obsidian 프론트매터 notion_id 와 같은 값)
--             v4.0 이후 새로 만든 행 = uuid4
-- 문자열은 전부 NFC. topics·tags 는 JSON 배열 문자열.
-- 시각(created_at·updated_at)은 ISO 8601 UTC ('2026-10-11T08:15:00.000Z').

PRAGMA user_version = 1;

CREATE TABLE IF NOT EXISTS videos (
  record_id        TEXT PRIMARY KEY,
  video_id         TEXT UNIQUE,                 -- 11자. URL 에서 못 뽑으면 NULL (NULL 은 UNIQUE 대상 아님)
  title            TEXT NOT NULL DEFAULT '',
  channel          TEXT NOT NULL DEFAULT '',
  topics           TEXT NOT NULL DEFAULT '[]',  -- JSON 배열
  upload_date      TEXT,                        -- YYYY-MM-DD
  view_count       INTEGER,
  subscriber_count INTEGER,
  video_url        TEXT,
  thumbnail_url    TEXT,
  status           TEXT,
  summary          TEXT NOT NULL DEFAULT '',    -- 원문 마크다운 (Gemini 요약 그대로)
  summary_src      TEXT NOT NULL DEFAULT 'app', -- property | blocks | empty | app
  created_at       TEXT NOT NULL,
  updated_at       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_videos_title ON videos(title);

-- 같은 video_id 로 중복 저장됐던 노션 페이지. 지우지 않고 보관만 한다(되돌림용).
CREATE TABLE IF NOT EXISTS videos_dup (
  record_id        TEXT PRIMARY KEY,
  keeper_record_id TEXT NOT NULL,               -- videos 에 남긴 행
  video_id         TEXT,
  title            TEXT NOT NULL DEFAULT '',
  channel          TEXT NOT NULL DEFAULT '',
  topics           TEXT NOT NULL DEFAULT '[]',
  upload_date      TEXT,
  view_count       INTEGER,
  subscriber_count INTEGER,
  video_url        TEXT,
  thumbnail_url    TEXT,
  status           TEXT,
  summary          TEXT NOT NULL DEFAULT '',
  summary_src      TEXT NOT NULL DEFAULT 'property',
  has_vault_note   INTEGER NOT NULL DEFAULT 0,  -- 1 = Obsidian 노트가 이 page 를 가리킨다 (2단계에서 고아 격리 대상)
  created_at       TEXT NOT NULL,
  updated_at       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_videos_dup_keeper ON videos_dup(keeper_record_id);

CREATE TABLE IF NOT EXISTS tips (
  record_id   TEXT PRIMARY KEY,
  title       TEXT NOT NULL DEFAULT '',
  url         TEXT NOT NULL DEFAULT '',
  url_key     TEXT NOT NULL DEFAULT '',          -- lib/kakao_parse.py:url_key(url). 중복 판정 근거
  source      TEXT NOT NULL DEFAULT '',          -- 호스트만 (github.com)
  tags        TEXT NOT NULL DEFAULT '[]',        -- JSON 배열
  category    TEXT NOT NULL DEFAULT '',
  status      TEXT NOT NULL DEFAULT '',
  importance  TEXT NOT NULL DEFAULT '',
  saved_date  TEXT,                              -- YYYY-MM-DD
  memo        TEXT NOT NULL DEFAULT '',
  body_md     TEXT NOT NULL DEFAULT '',          -- 노션 페이지 본문(사용자가 붙인 블록). 보통 비어 있음
  created_at  TEXT NOT NULL,
  updated_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tips_url_key ON tips(url_key);

CREATE TABLE IF NOT EXISTS meta (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
