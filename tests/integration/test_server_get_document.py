"""RAG-24, RAG-25: get_document returns the full document in scope, and produces a
response indistinguishable between a nonexistent id and one from another tenant."""

import pytest

from rag import server


@pytest.fixture(autouse=True)
def _active_tenant(monkeypatch):
    monkeypatch.setattr(server, "_active_tenant", "meridian")


def _first_doc_id(admin_conn, tenant_id: str) -> str:
    row = admin_conn.execute(
        "SELECT id FROM documents WHERE tenant_id = %s ORDER BY id LIMIT 1", (tenant_id,)
    ).fetchone()
    return str(row[0])


def test_get_document_returns_full_text_and_metadata_for_scope(admin_conn):
    doc_id = _first_doc_id(admin_conn, "meridian")
    result = server.get_document(doc_id)
    assert result["found"] is True
    assert result["doc_id"] == doc_id
    assert result["texto"]
    assert result["titulo"]
    assert result["categoria"]
    assert result["visibilidade"]


def test_nonexistent_doc_id_is_not_found():
    result = server.get_document("00000000-0000-0000-0000-000000000000")
    assert result == {"found": False}


def test_cross_tenant_doc_id_is_not_found(admin_conn):
    doc_id = _first_doc_id(admin_conn, "halcyon")
    result = server.get_document(doc_id)
    assert result == {"found": False}


def test_nonexistent_and_cross_tenant_responses_are_byte_identical(admin_conn):
    halcyon_doc_id = _first_doc_id(admin_conn, "halcyon")
    nonexistent = server.get_document("00000000-0000-0000-0000-000000000000")
    cross_tenant = server.get_document(halcyon_doc_id)
    assert nonexistent == cross_tenant
