-- Extensions and the IMMUTABLE unaccent wrapper the generated fts column requires.
--
-- unaccent(text) is STABLE, not IMMUTABLE, because it resolves its dictionary through
-- search_path. A generated column requires an IMMUTABLE expression, so we wrap the call
-- with an explicit dictionary name, which makes the result independent of search_path.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS unaccent;

CREATE OR REPLACE FUNCTION immutable_unaccent(text)
RETURNS text
LANGUAGE sql
IMMUTABLE
PARALLEL SAFE
STRICT
AS $$
    SELECT unaccent('unaccent', $1)
$$;
