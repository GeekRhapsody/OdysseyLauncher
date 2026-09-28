-- userdata.db, schema version 1. Shipped: never edit this file; add a new numbered migration instead.
-- This DB can't be rebuilt. It's keyed by (system_id, path_key), never by library.db ids (ARCHITECTURE.md A4).

CREATE TABLE favourites (
  system_id  TEXT NOT NULL,
  path_key   TEXT NOT NULL,
  added_at   INTEGER NOT NULL,
  PRIMARY KEY (system_id, path_key)
) STRICT, WITHOUT ROWID;

CREATE TABLE play_stats (
  system_id       TEXT NOT NULL,
  path_key        TEXT NOT NULL,
  play_count      INTEGER NOT NULL DEFAULT 0,
  total_seconds   INTEGER NOT NULL DEFAULT 0,
  last_played_at  INTEGER,
  PRIMARY KEY (system_id, path_key)
) STRICT, WITHOUT ROWID;
-- The Recently played grid: newest first.
CREATE INDEX play_stats_recent ON play_stats(last_played_at DESC) WHERE last_played_at IS NOT NULL;

CREATE TABLE play_sessions (
  session_id  INTEGER PRIMARY KEY,
  system_id   TEXT NOT NULL,
  path_key    TEXT NOT NULL,
  emulator    TEXT NOT NULL,
  started_at  INTEGER NOT NULL,
  ended_at    INTEGER,                        -- NULL = the launcher died; closed on the next start
  exit_code   INTEGER
) STRICT;
CREATE INDEX play_sessions_open ON play_sessions(session_id) WHERE ended_at IS NULL;

CREATE TABLE manual_matches (
  system_id        TEXT NOT NULL,
  path_key         TEXT NOT NULL,
  scraper          TEXT NOT NULL,
  scraper_game_id  TEXT NOT NULL,
  matched_at       INTEGER NOT NULL,
  PRIMARY KEY (system_id, path_key, scraper)
) STRICT, WITHOUT ROWID;

CREATE TABLE game_overrides (
  system_id   TEXT NOT NULL,
  path_key    TEXT NOT NULL,
  title       TEXT,                           -- NULL = use the scraped or file-name title
  sort_title  TEXT,                           -- sort key for title, written with it
  emulator    TEXT,                           -- NULL = the system default
  hidden      INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (system_id, path_key)
) STRICT, WITHOUT ROWID;
