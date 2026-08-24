-- Three roles with disjoint powers. The boundary between them is itself part of the
-- isolation proof: rag_owner ignores RLS by default (table owners always do), so it
-- must never be used at request time; rag_app has to be unable to bypass RLS even if
-- every WHERE clause in the codebase were wrong.

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'rag_owner') THEN
        CREATE ROLE rag_owner LOGIN PASSWORD 'rag_owner';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'rag_ingest') THEN
        CREATE ROLE rag_ingest LOGIN PASSWORD 'rag_ingest';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'rag_app') THEN
        CREATE ROLE rag_app LOGIN PASSWORD 'rag_app' NOBYPASSRLS NOSUPERUSER;
    END IF;
END
$$;

ALTER TABLE tenants   OWNER TO rag_owner;
ALTER TABLE documents OWNER TO rag_owner;
ALTER TABLE chunks    OWNER TO rag_owner;

GRANT USAGE ON SCHEMA public TO rag_app, rag_ingest;

GRANT SELECT ON tenants, documents, chunks TO rag_app;

GRANT SELECT ON tenants TO rag_ingest;
GRANT SELECT, INSERT, UPDATE, DELETE ON documents, chunks TO rag_ingest;
