-- library.db, schema version 1. Shipped: never edit this file; add a new numbered migration instead.
-- Everything here can be rebuilt from config, the ROM folders, media/ and scraped/ (ARCHITECTURE.md A4).

CREATE TABLE systems (
  system_id   TEXT PRIMARY KEY,               -- config id, e.g. 'megadrive'
  scanned_at  INTEGER,                        -- unix ms; NULL = never scanned
  game_count  INTEGER NOT NULL DEFAULT 0      -- denormalised for the boot query
) STRICT;

CREATE TABLE rom_dirs (
  dir_id      INTEGER PRIMARY KEY,
  system_id   TEXT NOT NULL REFERENCES systems(system_id) ON DELETE CASCADE,
  position    INTEGER NOT NULL,               -- order in the system's folder list; earlier folders win path_key collisions
  path        TEXT NOT NULL,                  -- resolved absolute folder at last scan
  UNIQUE (system_id, path)
) STRICT;

CREATE TABLE games (
  game_id     INTEGER PRIMARY KEY,
  system_id   TEXT NOT NULL REFERENCES systems(system_id) ON DELETE CASCADE,
  dir_id      INTEGER NOT NULL REFERENCES rom_dirs(dir_id) ON DELETE CASCADE,
  rel_path    TEXT NOT NULL,                  -- as on disk: relative to its ROM folder, '/' separators, NFC
  path_key    TEXT NOT NULL,                  -- lower-invariant rel_path: the stable identity
  size_bytes  INTEGER NOT NULL,
  mtime_ms    INTEGER NOT NULL,
  crc32 TEXT, md5 TEXT, sha1 TEXT,            -- NULL until hash matching lands
  title       TEXT NOT NULL,                  -- scraped title, else cleaned file name (user overrides live in userdata)
  sort_title  TEXT NOT NULL,                  -- internal sort key (TitleParser.SortKey)
  region      TEXT,                           -- file name tags, as written: 'USA, Europe'
  languages   TEXT,                           -- 'En,Fr,De'
  revision    TEXT,                           -- 'Rev 1', 'v1.1'
  disc        INTEGER,                        -- '(Disc 2)' on a disc that no .m3u groups
  tags        TEXT,                           -- every other tag, as written: '(Beta) [b1]'
  UNIQUE (system_id, path_key)
) STRICT;
-- The games grid: one system, in title order.
CREATE INDEX games_by_system ON games(system_id, sort_title);
-- For ON DELETE CASCADE from rom_dirs.
CREATE INDEX games_by_dir ON games(dir_id);

-- .m3u, .cue and .gdi files the scanner parsed, including ones an .m3u hides, so unchanged ones aren't re-read.
CREATE TABLE playlists (
  system_id   TEXT NOT NULL REFERENCES systems(system_id) ON DELETE CASCADE,
  path_key    TEXT NOT NULL,
  size_bytes  INTEGER NOT NULL,
  mtime_ms    INTEGER NOT NULL,
  refs        TEXT NOT NULL,                  -- referenced path_keys, '\n'-separated
  PRIMARY KEY (system_id, path_key)
) STRICT, WITHOUT ROWID;

CREATE TABLE metadata (
  game_id      INTEGER PRIMARY KEY REFERENCES games(game_id) ON DELETE CASCADE,
  description  TEXT, release_date TEXT,       -- ISO 8601, partial allowed ('1991', '1991-06')
  developer TEXT, publisher TEXT, genre TEXT, players TEXT,
  rating       REAL,                          -- 0..1
  source       TEXT NOT NULL                  -- scraper id
) STRICT;

CREATE TABLE scraper_matches (
  game_id          INTEGER NOT NULL REFERENCES games(game_id) ON DELETE CASCADE,
  scraper          TEXT NOT NULL,             -- 'screenscraper' | 'steamgriddb'
  scraper_game_id  TEXT NOT NULL,
  method           TEXT NOT NULL,             -- 'filename' | 'hash' | 'manual'
  matched_at       INTEGER NOT NULL,
  PRIMARY KEY (game_id, scraper)
) STRICT;

CREATE TABLE media (                          -- one row per kind: the effective file (user override beats scraped)
  game_id  INTEGER NOT NULL REFERENCES games(game_id) ON DELETE CASCADE,
  kind     TEXT NOT NULL,                     -- cover | back | spine | box_texture | label | screenshot | logo | hero | model
  path     TEXT NOT NULL,                     -- relative to the root named by source
  width INTEGER, height INTEGER,
  source   TEXT NOT NULL,                     -- 'screenscraper' | 'steamgriddb' (DataDir/media) | 'user' (ConfigDir)
  PRIMARY KEY (game_id, kind)
) STRICT;

CREATE TABLE scrape_log (
  game_id       INTEGER NOT NULL REFERENCES games(game_id) ON DELETE CASCADE,
  scraper       TEXT NOT NULL,
  status        TEXT NOT NULL,                -- 'ok' | 'not_found' | 'error'
  attempted_at  INTEGER NOT NULL,
  detail        TEXT,
  PRIMARY KEY (game_id, scraper)
) STRICT;
