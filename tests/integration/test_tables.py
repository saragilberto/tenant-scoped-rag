"""RAG-01: tenants, documents and chunks tables."""

import uuid

from conftest import zero_vector_literal

EXPECTED_COLUMNS = {
    "tenants": {"id", "nome"},
    "documents": {
        "id",
        "tenant_id",
        "source_path",
        "titulo",
        "categoria",
        "versao",
        "visibilidade",
        "content_hash",
        "texto_original",
        "created_at",
    },
    "chunks": {
        "id",
        "document_id",
        "tenant_id",
        "profile",
        "ord",
        "texto",
        "embedding",
        "fts",
    },
}


def test_core_tables_exist_with_expected_columns(admin_conn):
    for table, expected in EXPECTED_COLUMNS.items():
        rows = admin_conn.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = %s",
            (table,),
        ).fetchall()
        actual = {row[0] for row in rows}
        assert expected.issubset(actual), f"{table} missing columns: {expected - actual}"


def test_documents_has_unique_tenant_source_hash_constraint(admin_conn):
    rows = admin_conn.execute(
        """
        SELECT array_agg(a.attname ORDER BY a.attname)
        FROM pg_constraint c
        JOIN unnest(c.conkey) AS k(attnum) ON true
        JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = k.attnum
        WHERE c.conrelid = 'documents'::regclass AND c.contype = 'u'
        GROUP BY c.conname
        """
    ).fetchall()
    unique_column_sets = {tuple(row[0]) for row in rows}
    assert tuple(sorted(["content_hash", "source_path", "tenant_id"])) in unique_column_sets


def test_chunks_fts_populates_automatically_and_normalizes_accents(admin_conn):
    doc_id = uuid.uuid4()
    chunk_id = uuid.uuid4()
    admin_conn.execute(
        """
        INSERT INTO documents
            (id, tenant_id, source_path, titulo, categoria, versao, visibilidade,
             content_hash, texto_original)
        VALUES (%s, 'meridian', 'test-tables.md', 'Título', 'geral', '1', 'empresa',
                'test-tables-hash', 'texto original')
        """,
        (doc_id,),
    )
    admin_conn.execute(
        f"""
        INSERT INTO chunks (id, document_id, tenant_id, profile, ord, texto, embedding)
        VALUES (%s, %s, 'meridian', 'P512', 0, %s, '{zero_vector_literal()}'::vector)
        """,
        (chunk_id, doc_id, "Configuração do órgão de suporte"),
    )
    row = admin_conn.execute("SELECT fts::text FROM chunks WHERE id = %s", (chunk_id,)).fetchone()
    assert "orgao" in row[0]
