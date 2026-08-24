"""RAG-10: scoped recall must not trail the single-tenant baseline beyond a declared margin.

The RLS predicate is not leakproof and does not get pushed inside the HNSW scan, so a scoped
search could in principle return fewer than top_k relevant chunks even though hnsw.iterative_scan
is set to strict_order to mitigate exactly that. This measures recall@5 of the scoped search
(against a database holding both tenants) against the same search run over a second database
that only ever held meridian's corpus - never by elevating a role's privileges, only by
comparing two databases.
"""

import os
from pathlib import Path

import psycopg
import pytest
import yaml

from rag.chunking import ChunkProfile
from rag.db import scoped_connection
from rag.ingest import ingest
from rag.retrieval import semantic

REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = REPO_ROOT / "migrations"
GOLDEN_SET_PATH = REPO_ROOT / "eval" / "golden" / "meridian.yaml"
CORPUS_DIR = Path("corpus/meridian")  # relative, to match the source_path already in the main db

SINGLE_TENANT_PORT = "55433"
SINGLE_TENANT_DBNAME = "rag_single_tenant"
SINGLE_TENANT_ADMIN_DSN = (
    f"host={os.environ.get('RAG_DB_HOST', 'localhost')} port={SINGLE_TENANT_PORT} "
    f"dbname={SINGLE_TENANT_DBNAME} user=postgres password=postgres"
)
SINGLE_TENANT_APP_DSN = (
    f"host={os.environ.get('RAG_DB_HOST', 'localhost')} port={SINGLE_TENANT_PORT} "
    f"dbname={SINGLE_TENANT_DBNAME} user=rag_app password=rag_app"
)

RECALL_MARGIN = 0.05
TOP_K = 5


def _apply_migrations(dsn: str) -> None:
    with psycopg.connect(dsn, autocommit=True) as conn:
        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            conn.execute(path.read_text())


@pytest.fixture(scope="module", autouse=True)
def _single_tenant_baseline_seeded():
    _apply_migrations(SINGLE_TENANT_ADMIN_DSN)

    previous = {name: os.environ.get(name) for name in ("RAG_DB_PORT", "RAG_DB_NAME")}
    os.environ["RAG_DB_PORT"] = SINGLE_TENANT_PORT
    os.environ["RAG_DB_NAME"] = SINGLE_TENANT_DBNAME
    try:
        ingest(CORPUS_DIR, "meridian", ChunkProfile.P512)
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


@pytest.fixture(scope="module")
def golden_questions() -> list[dict]:
    return yaml.safe_load(GOLDEN_SET_PATH.read_text())


def _document_source_paths(conn: psycopg.Connection) -> dict[str, str]:
    rows = conn.execute("SELECT id, source_path FROM documents").fetchall()
    return {str(row[0]): row[1] for row in rows}


def _recall_at_5(conn: psycopg.Connection, questions: list[dict]) -> float:
    doc_paths = _document_source_paths(conn)
    hits = 0
    for question in questions:
        candidates = semantic.search(conn, question["question"], TOP_K, ChunkProfile.P512)
        retrieved = {doc_paths[c.document_id] for c in candidates}
        if retrieved & set(question["relevant_docs"]):
            hits += 1
    return hits / len(questions)


def test_scoped_recall_is_within_margin_of_single_tenant_baseline(golden_questions):
    with scoped_connection("meridian") as scoped_conn:
        scoped_recall = _recall_at_5(scoped_conn, golden_questions)

    with psycopg.connect(SINGLE_TENANT_APP_DSN) as baseline_conn:
        baseline_conn.execute("SELECT set_config('app.tenant_id', 'meridian', true)")
        baseline_recall = _recall_at_5(baseline_conn, golden_questions)

    assert scoped_recall >= baseline_recall - RECALL_MARGIN, (
        f"scoped recall@5={scoped_recall:.3f} fell short of the single-tenant "
        f"baseline recall@5={baseline_recall:.3f} by more than the {RECALL_MARGIN} margin"
    )


def test_recall_measurement_uses_no_bypassrls_role():
    with scoped_connection("meridian") as scoped_conn:
        scoped_bypass = scoped_conn.execute(
            "SELECT rolbypassrls FROM pg_roles WHERE rolname = current_user"
        ).fetchone()[0]

    with psycopg.connect(SINGLE_TENANT_APP_DSN) as baseline_conn:
        baseline_bypass = baseline_conn.execute(
            "SELECT rolbypassrls FROM pg_roles WHERE rolname = current_user"
        ).fetchone()[0]

    assert scoped_bypass is False
    assert baseline_bypass is False


def test_single_tenant_baseline_holds_only_meridian_documents():
    with psycopg.connect(SINGLE_TENANT_ADMIN_DSN) as admin_conn:
        tenant_ids = admin_conn.execute("SELECT DISTINCT tenant_id FROM documents").fetchall()

    assert tenant_ids == [("meridian",)]
