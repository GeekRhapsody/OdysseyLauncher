-- 2026-10-07: the template the user chose for one game (its options), a template id in the active theme, else the
-- base theme. NULL = its system's template. Shipped: never edit this file.
ALTER TABLE game_overrides ADD COLUMN template TEXT;
