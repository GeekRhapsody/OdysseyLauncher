-- One media folder (2026-10-02): every media row indexes a file in DataDir/media/<system>/<kind>/, scraped or the
-- user's own alike, so a row no longer records where its file came from. Rows pointing at the old folders
-- (scraped/media/, ConfigDir's media/ and models/games/) are left for the next scan to drop; every system is marked
-- never scanned, so the app rescans them all in the background once.
ALTER TABLE media DROP COLUMN source;
UPDATE systems SET scanned_at = NULL;
