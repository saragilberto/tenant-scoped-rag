-- One HNSW index per chunk profile (partial), so the profile filter is resolved by the
-- index itself instead of stacking as a second post-scan filter on top of the RLS
-- predicate. That leaves tenant_id as the only filter left after the index scan, which
-- is exactly what hnsw.iterative_scan is for (RAG-10).

CREATE INDEX IF NOT EXISTS chunks_hnsw_p512  ON chunks USING hnsw (embedding vector_cosine_ops) WHERE profile = 'P512';
CREATE INDEX IF NOT EXISTS chunks_hnsw_p1024 ON chunks USING hnsw (embedding vector_cosine_ops) WHERE profile = 'P1024';
CREATE INDEX IF NOT EXISTS chunks_fts_gin    ON chunks USING gin (fts);
CREATE INDEX IF NOT EXISTS chunks_tenant     ON chunks (tenant_id, profile);

-- Database-level default so a brand new connection already sees strict_order, without
-- relying on every caller to set it. Written with dynamic SQL because ALTER DATABASE
-- does not accept current_database() as its target.
DO $$
BEGIN
    EXECUTE format('ALTER DATABASE %I SET hnsw.iterative_scan = %L', current_database(), 'strict_order');
END
$$;
