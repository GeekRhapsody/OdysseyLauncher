-- When each game's file arrived in its ROM folder (2026-10-03): the file's creation time, unix ms, from the folder
-- listing the scan already reads, for sorting a system's games by "added" ([display] games_sort). It comes from disk,
-- so a rebuild keeps it. NULL until a scan reads it: every system is marked never scanned, so the app rescans them
-- all in the background once.
ALTER TABLE games ADD COLUMN added_ms INTEGER;
UPDATE systems SET scanned_at = NULL;
