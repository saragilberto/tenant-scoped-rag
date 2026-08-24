-- Core schema: tenants, documents and chunks.
--
-- tenant_id is denormalized onto chunks on purpose: if the RLS policy on chunks needed a
-- join to documents to learn the tenant, the predicate would sit even further from the
-- index, which is exactly what the RAG-10 recall mitigation cannot afford.

CREATE TABLE IF NOT EXISTS tenants (
    id   text PRIMARY KEY,
    nome text NOT NULL
);

CREATE TABLE IF NOT EXISTS documents (
    id             uuid PRIMARY KEY,
    tenant_id      text NOT NULL REFERENCES tenants(id),
    source_path    text NOT NULL,
    titulo         text NOT NULL,
    categoria      text NOT NULL,
    versao         text NOT NULL,
    visibilidade   text NOT NULL,
    content_hash   text NOT NULL,
    texto_original text NOT NULL,
    created_at     timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, source_path, content_hash)
);

CREATE TABLE IF NOT EXISTS chunks (
    id          uuid PRIMARY KEY,
    document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    tenant_id   text NOT NULL REFERENCES tenants(id),
    profile     text NOT NULL,
    ord         int  NOT NULL,
    texto       text NOT NULL,
    embedding   vector(768) NOT NULL,
    fts         tsvector GENERATED ALWAYS AS (
                    to_tsvector('english', immutable_unaccent(texto))
                ) STORED
);

INSERT INTO tenants (id, nome) VALUES
    ('meridian', 'Meridian'),
    ('halcyon', 'Halcyon')
ON CONFLICT (id) DO NOTHING;
