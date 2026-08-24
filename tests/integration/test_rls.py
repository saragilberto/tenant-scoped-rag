"""RAG-14: row level security policies enforcing tenant isolation at the database."""

import uuid

import psycopg
import pytest
from conftest import set_tenant, zero_vector_literal


@pytest.fixture
def seeded_chunk_pair(admin_conn_autocommit):
    """One committed chunk per tenant, visible across connections, cleaned up after."""
    doc_m, doc_h = uuid.uuid4(), uuid.uuid4()
    chunk_m, chunk_h = uuid.uuid4(), uuid.uuid4()
    vec = zero_vector_literal()
    admin_conn_autocommit.execute(
        """
        INSERT INTO documents
            (id, tenant_id, source_path, titulo, categoria, versao, visibilidade,
             content_hash, texto_original)
        VALUES (%s, 'meridian', 'rls-test-m.md', 't', 'c', '1', 'empresa', 'rls-hash-m', 'x')
        """,
        (doc_m,),
    )
    admin_conn_autocommit.execute(
        """
        INSERT INTO documents
            (id, tenant_id, source_path, titulo, categoria, versao, visibilidade,
             content_hash, texto_original)
        VALUES (%s, 'halcyon', 'rls-test-h.md', 't', 'c', '1', 'empresa', 'rls-hash-h', 'x')
        """,
        (doc_h,),
    )
    admin_conn_autocommit.execute(
        f"""
        INSERT INTO chunks (id, document_id, tenant_id, profile, ord, texto, embedding)
        VALUES (%s, %s, 'meridian', 'P512', 0, 'texto meridian', '{vec}'::vector)
        """,
        (chunk_m, doc_m),
    )
    admin_conn_autocommit.execute(
        f"""
        INSERT INTO chunks (id, document_id, tenant_id, profile, ord, texto, embedding)
        VALUES (%s, %s, 'halcyon', 'P512', 0, 'texto halcyon', '{vec}'::vector)
        """,
        (chunk_h, doc_h),
    )
    try:
        yield {"meridian_chunk": chunk_m, "halcyon_chunk": chunk_h}
    finally:
        admin_conn_autocommit.execute("DELETE FROM chunks WHERE id IN (%s, %s)", (chunk_m, chunk_h))
        admin_conn_autocommit.execute("DELETE FROM documents WHERE id IN (%s, %s)", (doc_m, doc_h))


def test_rls_enabled_on_documents(admin_conn):
    row = admin_conn.execute(
        "SELECT relrowsecurity FROM pg_class WHERE relname = 'documents'"
    ).fetchone()
    assert row[0] is True


def test_rls_enabled_on_chunks(admin_conn):
    row = admin_conn.execute(
        "SELECT relrowsecurity FROM pg_class WHERE relname = 'chunks'"
    ).fetchone()
    assert row[0] is True


def test_rag_app_scoped_select_excludes_other_tenant(rag_app_conn, seeded_chunk_pair):
    set_tenant(rag_app_conn, "meridian")
    rows = rag_app_conn.execute("SELECT id FROM chunks").fetchall()
    ids = {row[0] for row in rows}
    assert seeded_chunk_pair["meridian_chunk"] in ids
    assert seeded_chunk_pair["halcyon_chunk"] not in ids


def test_rag_ingest_insert_rejected_for_mismatched_tenant(rag_ingest_conn, seeded_chunk_pair):
    set_tenant(rag_ingest_conn, "meridian")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        rag_ingest_conn.execute(
            f"""
            INSERT INTO chunks (id, document_id, tenant_id, profile, ord, texto, embedding)
            VALUES (%s, (SELECT document_id FROM chunks WHERE id = %s),
                    'halcyon', 'P512', 1, 'forjado', '{zero_vector_literal()}'::vector)
            """,
            (uuid.uuid4(), seeded_chunk_pair["meridian_chunk"]),
        )


def test_select_without_tenant_guc_returns_zero_rows(rag_app_conn, seeded_chunk_pair):
    row = rag_app_conn.execute("SELECT count(*) FROM chunks").fetchone()
    assert row[0] == 0
