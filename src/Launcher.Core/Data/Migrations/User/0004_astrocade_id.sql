-- 2026-10-16: Bally Astrocade's id was spelt "astrocde" (MAME's name for the machine) and is now "astrocade". What
-- the user did to its games is kept under the new id. library.db is rebuilt from config and disk, so it needs
-- nothing. Shipped: never edit this file.
UPDATE favourites SET system_id = 'astrocade' WHERE system_id = 'astrocde';
UPDATE play_stats SET system_id = 'astrocade' WHERE system_id = 'astrocde';
UPDATE play_sessions SET system_id = 'astrocade' WHERE system_id = 'astrocde';
UPDATE manual_matches SET system_id = 'astrocade' WHERE system_id = 'astrocde';
UPDATE game_overrides SET system_id = 'astrocade' WHERE system_id = 'astrocde';
UPDATE scrape_jobs SET system_id = 'astrocade' WHERE system_id = 'astrocde';
UPDATE scrape_batches SET target = 'astrocade' WHERE target = 'astrocde';
UPDATE scrape_batches SET target = 'astrocade/' || substr(target, 10) WHERE target LIKE 'astrocde/%';
