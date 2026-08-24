"""The single door to the database.

Every connection is opened as ``rag_app`` and scoped to a tenant via ``SET LOCAL``
before it is handed back. No other module in this project is allowed to construct a
database connection - that is what makes tenant isolation a property of the system
instead of a discipline every caller has to remember.
"""

import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager

import psycopg

__all__ = ["scoped_connection", "resolve_tenant_from_env"]

_TENANT_ENV_VAR = "RAG_TENANT_ID"


def _dsn(user: str, password: str) -> str:
    host = os.environ.get("RAG_DB_HOST", "localhost")
    port = os.environ.get("RAG_DB_PORT", "55432")
    dbname = os.environ.get("RAG_DB_NAME", "rag")
    return f"host={host} port={port} dbname={dbname} user={user} password={password}"


def _rag_app_dsn() -> str:
    return _dsn("rag_app", os.environ.get("RAG_APP_PASSWORD", "rag_app"))


@contextmanager
def scoped_connection(tenant_id: str) -> Iterator[psycopg.Connection]:
    """Open a transaction as ``rag_app`` with ``app.tenant_id`` set for its duration."""
    conn = psycopg.connect(_rag_app_dsn())
    try:
        conn.execute("SELECT set_config('app.tenant_id', %s, true)", (tenant_id,))
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def resolve_tenant_from_env() -> str:
    """Read and validate the tenant id from the environment, or exit the process."""
    tenant_id = os.environ.get(_TENANT_ENV_VAR, "").strip()
    if not tenant_id:
        sys.exit(f"{_TENANT_ENV_VAR} is not set. Set it to a known tenant id before starting.")
    known_tenants = _known_tenant_ids()
    if tenant_id not in known_tenants:
        sys.exit(
            f"{_TENANT_ENV_VAR}={tenant_id!r} is not a known tenant. "
            f"Known tenants: {sorted(known_tenants)}"
        )
    return tenant_id


def _known_tenant_ids() -> set[str]:
    conn = psycopg.connect(_rag_app_dsn())
    try:
        rows = conn.execute("SELECT id FROM tenants").fetchall()
        return {row[0] for row in rows}
    finally:
        conn.close()
