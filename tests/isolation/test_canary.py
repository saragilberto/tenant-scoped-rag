"""RAG-19: a disposable database proves the isolation suite has teeth. Disabling row
level security on it must turn the same leak check the isolation suite relies on
red - otherwise "zero cross-tenant leakage" would be true by accident, not by proof.
The main database is never touched: everything here runs against a throwaway
database created and dropped by this test, on the same Postgres server."""

import os
import uuid
from pathlib import Path

import psycopg
import pytest

from rag import server

REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = REPO_ROOT / "migrations"

_DB_HOST = os.environ.get("RAG_DB_HOST", "localhost")
_DB_PORT = os.environ.get("RAG_DB_PORT", "55432")
_ADMIN_PASSWORD = os.environ.get("RAG_DB_ADMIN_PASSWORD", "postgres")


def _admin_dsn(dbname: str) -> str:
    return (
        f"host={_DB_HOST} port={_DB_PORT} dbname={dbname} user=postgres password={_ADMIN_PASSWORD}"
    )


def _zero_vector_literal() -> str:
    return "[" + ",".join(["0"] * 768) + "]"


@pytest.fixture
def canary_db(monkeypatch):
    """A throwaway database, migrated fresh, seeded with one document per tenant."""
    canary_name = f"rag_canary_{uuid.uuid4().hex[:8]}"
    with psycopg.connect(_admin_dsn("postgres"), autocommit=True) as maintenance_conn:
        maintenance_conn.execute(f'CREATE DATABASE "{canary_name}"')
    try:
        with psycopg.connect(_admin_dsn(canary_name), autocommit=True) as admin_conn:
            for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
                admin_conn.execute(path.read_text())

            doc_ids = {}
            for tenant_id in ("meridian", "halcyon"):
                doc_id = str(uuid.uuid4())
                chunk_id = str(uuid.uuid4())
                doc_ids[tenant_id] = doc_id
                admin_conn.execute(
                    """
                    INSERT INTO documents
                        (id, tenant_id, source_path, titulo, categoria, versao,
                         visibilidade, content_hash, texto_original)
                    VALUES
                        (%s, %s, 'canary.md', 'Canary', 'canary', '1', 'empresa', 'hash', 'texto')
                    """,
                    (doc_id, tenant_id),
                )
                admin_conn.execute(
                    f"""
                    INSERT INTO chunks (id, document_id, tenant_id, profile, ord, texto, embedding)
                    VALUES (%s, %s, %s, 'P512', 0, 'texto', '{_zero_vector_literal()}')
                    """,
                    (chunk_id, doc_id, tenant_id),
                )

        monkeypatch.setenv("RAG_DB_NAME", canary_name)
        monkeypatch.setattr(server, "_active_tenant", "meridian")
        yield {"name": canary_name, "doc_ids": doc_ids}
    finally:
        with psycopg.connect(_admin_dsn("postgres"), autocommit=True) as maintenance_conn:
            maintenance_conn.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = %s AND pid <> pg_backend_pid()",
                (canary_name,),
            )
            maintenance_conn.execute(f'DROP DATABASE IF EXISTS "{canary_name}"')


def _leak_check(expected_doc_id: str) -> None:
    """The same shape of assertion the cross-tenant isolation suite makes: the active
    tenant's scope must contain exactly its own document, nothing from the other one."""
    visible_doc_ids = {entry["doc_id"] for entry in server.list_sources()}
    assert visible_doc_ids == {expected_doc_id}, (
        f"expected only {expected_doc_id!r} in scope, got {visible_doc_ids!r}"
    )


def test_isolation_check_passes_on_the_canary_with_rls_enabled(canary_db):
    _leak_check(canary_db["doc_ids"]["meridian"])


def test_canary_disabling_rls_turns_the_isolation_check_red(canary_db):
    with psycopg.connect(_admin_dsn(canary_db["name"]), autocommit=True) as admin_conn:
        admin_conn.execute("ALTER TABLE documents DISABLE ROW LEVEL SECURITY")
        admin_conn.execute("ALTER TABLE chunks DISABLE ROW LEVEL SECURITY")
        try:
            with pytest.raises(AssertionError, match="expected only"):
                _leak_check(canary_db["doc_ids"]["meridian"])
        finally:
            # RAG-19 / "a política é restaurada ao fim": re-enable enforcement before
            # the fixture drops this disposable database.
            admin_conn.execute("ALTER TABLE documents ENABLE ROW LEVEL SECURITY")
            admin_conn.execute("ALTER TABLE chunks ENABLE ROW LEVEL SECURITY")
