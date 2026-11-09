-- 2026-11-09: the sort title the user typed for one game (its "Edit the title and metadata"), or one an ES-DE gamelist
-- import brought (<sortname>). NULL = it sorts by its title. sort_title is the key of this, else of title
-- (TitleParser.SortKey), so the grid queries are unchanged. Shipped: never edit this file.
ALTER TABLE game_overrides ADD COLUMN sort_name TEXT;
