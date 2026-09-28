-- M4: the user's metadata overrides, and the scrape queue. Shipped: never edit this file.

-- Per-game metadata the user typed. NULL = use the scraped value. Scraping never writes these.
ALTER TABLE game_overrides ADD COLUMN description TEXT;
ALTER TABLE game_overrides ADD COLUMN release_date TEXT;
ALTER TABLE game_overrides ADD COLUMN developer TEXT;
ALTER TABLE game_overrides ADD COLUMN publisher TEXT;
ALTER TABLE game_overrides ADD COLUMN genre TEXT;
ALTER TABLE game_overrides ADD COLUMN players TEXT;
ALTER TABLE game_overrides ADD COLUMN rating REAL;

-- Scrape requests, so a batch resumes after the app closes. Keyed by (system_id, path_key) like everything here,
-- so a library rebuild doesn't lose them.
CREATE TABLE scrape_batches (
  batch_id     INTEGER PRIMARY KEY,
  kind         TEXT NOT NULL,                 -- 'game' | 'system' | 'missing'
  target       TEXT,                          -- the system id, or '<system>/<path_key>'
  priority     INTEGER NOT NULL,              -- lower runs first: a single game jumps a long batch
  total        INTEGER NOT NULL,
  done         INTEGER NOT NULL DEFAULT 0,
  failed       INTEGER NOT NULL DEFAULT 0,
  created_at   INTEGER NOT NULL,
  finished_at  INTEGER,                       -- NULL = unfinished: resumed on the next start
  cancelled    INTEGER NOT NULL DEFAULT 0
) STRICT;

CREATE TABLE scrape_jobs (
  batch_id   INTEGER NOT NULL REFERENCES scrape_batches(batch_id) ON DELETE CASCADE,
  seq        INTEGER NOT NULL,                -- order within the batch
  system_id  TEXT NOT NULL,
  path_key   TEXT NOT NULL,
  PRIMARY KEY (batch_id, seq)
) STRICT, WITHOUT ROWID;
