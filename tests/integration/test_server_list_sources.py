"""RAG-26: list_sources lists only the active tenant's documents, with chunk counts,
and never hints that another tenant has content."""

import uuid

import pytest

from rag import server


@pytest.fixture(autouse=True)
def _active_tenant(monkeypatch):
    monkeypatch.setattr(server, "_active_tenant", "meridian")


def test_list_sources_returns_only_active_tenant_documents_with_correct_chunk_counts(admin_conn):
    result = server.list_sources()
    admin_ids = {
        str(r[0])
        for r in admin_conn.execute(
            "SELECT id FROM documents WHERE tenant_id = 'meridian'"
        ).fetchall()
    }
    assert {entry["doc_id"] for entry in result} == admin_ids
    for entry in result:
        assert set(entry) == {"doc_id", "titulo", "chunk_count"}
        expected = admin_conn.execute(
            "SELECT count(*) FROM chunks WHERE document_id = %s", (entry["doc_id"],)
        ).fetchone()[0]
        assert entry["chunk_count"] == expected


def test_list_sources_excludes_other_tenant_documents(admin_conn):
    halcyon_ids = {
        str(r[0])
        for r in admin_conn.execute(
            "SELECT id FROM documents WHERE tenant_id = 'halcyon'"
        ).fetchall()
    }
    result_ids = {entry["doc_id"] for entry in server.list_sources()}
    assert result_ids.isdisjoint(halcyon_ids)


def test_list_sources_on_tenant_without_documents_returns_empty_list(
    admin_conn_autocommit, monkeypatch
):
    empty_tenant_id = f"empty-{uuid.uuid4().hex[:8]}"
    admin_conn_autocommit.execute(
        "INSERT INTO tenants (id, nome) VALUES (%s, %s)", (empty_tenant_id, "Empty")
    )
    try:
        monkeypatch.setattr(server, "_active_tenant", empty_tenant_id)
        assert server.list_sources() == []
    finally:
        admin_conn_autocommit.execute("DELETE FROM tenants WHERE id = %s", (empty_tenant_id,))
