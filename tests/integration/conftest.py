"""Shared fixtures for integration tests: applies migrations against a live Postgres and
hands out connections scoped to each database role."""

import os
from pathlib import Path

import psycopg
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = REPO_ROOT / "migrations"

DB_HOST = os.environ.get("RAG_DB_HOST", "localhost")
DB_PORT = os.environ.get("RAG_DB_PORT", "55432")
DB_NAME = os.environ.get("RAG_DB_NAME", "rag")

ROLE_PASSWORDS = {
    "postgres": os.environ.get("RAG_DB_ADMIN_PASSWORD", "postgres"),
    "rag_owner": os.environ.get("RAG_OWNER_PASSWORD", "rag_owner"),
    "rag_ingest": os.environ.get("RAG_INGEST_PASSWORD", "rag_ingest"),
    "rag_app": os.environ.get("RAG_APP_PASSWORD", "rag_app"),
}


def dsn_for(role: str) -> str:
    return (
        f"host={DB_HOST} port={DB_PORT} dbname={DB_NAME} "
        f"user={role} password={ROLE_PASSWORDS[role]}"
    )


ADMIN_DSN = dsn_for("postgres")


def _migration_files() -> list[Path]:
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


@pytest.fixture(scope="session", autouse=True)
def _migrated_database():
    """Apply every migration twice, proving idempotency, before any integration test runs."""
    for _ in range(2):
        with psycopg.connect(ADMIN_DSN, autocommit=True) as conn:
            for path in _migration_files():
                conn.execute(path.read_text())
    yield


@pytest.fixture
def admin_conn():
    """Postgres superuser connection, rolled back after the test (schema-only checks)."""
    conn = psycopg.connect(ADMIN_DSN)
    try:
        yield conn
    finally:
        conn.rollback()
        conn.close()


@pytest.fixture
def admin_conn_autocommit():
    """Postgres superuser connection whose writes are visible to other connections."""
    conn = psycopg.connect(ADMIN_DSN, autocommit=True)
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def rag_app_conn():
    conn = psycopg.connect(dsn_for("rag_app"))
    try:
        yield conn
    finally:
        conn.rollback()
        conn.close()


@pytest.fixture
def rag_ingest_conn():
    conn = psycopg.connect(dsn_for("rag_ingest"))
    try:
        yield conn
    finally:
        conn.rollback()
        conn.close()


def set_tenant(conn: psycopg.Connection, tenant_id: str) -> None:
    """Scope a role connection the same way rag.db.scoped_connection does: SET LOCAL."""
    conn.execute("SELECT set_config('app.tenant_id', %s, true)", (tenant_id,))


def zero_vector_literal() -> str:
    return "[" + ",".join(["0"] * 768) + "]"
