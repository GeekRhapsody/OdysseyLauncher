-- M4: scraping. Everything here is rebuilt from scraped/responses/ when a game is (re)added (ARCHITECTURE.md A4).

-- The scraped title, kept apart from games.title (which holds it, or the cleaned file name, for the grid query), so
-- a case-only rename's new file-name title doesn't replace it.
ALTER TABLE metadata ADD COLUMN title TEXT;

-- Each game's last scrape: its outcome, the providers that supplied data (in the order used), and when.
-- No row = never scraped.
CREATE TABLE scrape_state (
  game_id     INTEGER PRIMARY KEY REFERENCES games(game_id) ON DELETE CASCADE,
  status      TEXT NOT NULL,                  -- 'ok' | 'partial' (a provider failed) | 'not_found' | 'error'
  providers   TEXT,                           -- 'screenscraper,igdb'; NULL when nothing was found
  scraped_at  INTEGER NOT NULL                -- unix ms
) STRICT;
