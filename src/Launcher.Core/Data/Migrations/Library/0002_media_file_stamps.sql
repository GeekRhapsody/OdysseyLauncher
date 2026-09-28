-- The source file's size and modification time, for media the scanner indexes from disk (the user's own art,
-- source 'user'). A rescan compares them to skip re-reading the image header of an unchanged file.
-- NULL for rows that don't come from a scanned file.
ALTER TABLE media ADD COLUMN size_bytes INTEGER;
ALTER TABLE media ADD COLUMN mtime_ms INTEGER;
