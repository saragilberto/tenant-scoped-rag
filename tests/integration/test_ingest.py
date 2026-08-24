"""RAG-01, RAG-02, RAG-05 and the tenant-write guard for src/rag/ingest.py."""

import subprocess
import sys
import uuid
from pathlib import Path

import psycopg
import pytest

from conftest import ADMIN_DSN, dsn_for, set_tenant
from rag.chunking import ChunkProfile
from rag.ingest import ingest

VALID_DOC = """---
title: "Resetting a Forgotten Password"
category: "Account"
version: "1.0"
visibility: empresa
---

## Requesting a reset link

A reset link is emailed to the address on file and expires after 30 minutes.
"""

INVALID_DOC = "no front matter here, just plain text\n"


def _write(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


@pytest.fixture
def cleanup_documents(admin_conn_autocommit):
    written_source_paths: list[str] = []
    yield written_source_paths
    if written_source_paths:
        admin_conn_autocommit.execute(
            "DELETE FROM documents WHERE source_path = ANY(%s)",
            (written_source_paths,),
        )


def test_first_ingest_writes_document_metadata_and_preserves_original_text(
    tmp_path, admin_conn, cleanup_documents
):
    doc_path = _write(tmp_path, "password-reset.md", VALID_DOC)
    cleanup_documents.append(str(doc_path))

    report = ingest(tmp_path, "meridian", ChunkProfile.P512)

    assert report.documents_written == 1
    set_tenant(admin_conn, "meridian")
    row = admin_conn.execute(
        "SELECT tenant_id, source_path, titulo, categoria, versao, visibilidade, texto_original "
        "FROM documents WHERE source_path = %s",
        (str(doc_path),),
    ).fetchone()
    assert row is not None
    tenant_id, source_path, titulo, categoria, versao, visibilidade, texto_original = row
    assert tenant_id == "meridian"
    assert source_path == str(doc_path)
    assert titulo == "Resetting a Forgotten Password"
    assert categoria == "Account"
    assert versao == "1.0"
    assert visibilidade == "empresa"
    assert "expires after 30 minutes" in texto_original


def test_first_ingest_writes_chunks_with_768_dim_embeddings_and_fts(
    tmp_path, admin_conn, cleanup_documents
):
    doc_path = _write(tmp_path, "password-reset.md", VALID_DOC)
    cleanup_documents.append(str(doc_path))

    report = ingest(tmp_path, "meridian", ChunkProfile.P512)

    assert report.chunks_written >= 1
    set_tenant(admin_conn, "meridian")
    row = admin_conn.execute(
        """
        SELECT array_length(c.embedding::real[], 1), c.fts IS NOT NULL
        FROM chunks c JOIN documents d ON d.id = c.document_id
        WHERE d.source_path = %s
        LIMIT 1
        """,
        (str(doc_path),),
    ).fetchone()
    assert row is not None
    dimensions, has_fts = row
    assert dimensions == 768
    assert has_fts is True


def test_second_ingest_without_changes_leaves_counts_identical(tmp_path, cleanup_documents):
    doc_path = _write(tmp_path, "password-reset.md", VALID_DOC)
    cleanup_documents.append(str(doc_path))

    first = ingest(tmp_path, "meridian", ChunkProfile.P512)
    second = ingest(tmp_path, "meridian", ChunkProfile.P512)

    assert second.documents_written == 0
    assert second.chunks_written == 0
    assert first.documents_written == 1


def test_failed_file_is_reported_and_ingestion_continues_with_other_files(
    tmp_path, cleanup_documents
):
    good_path = _write(tmp_path, "good.md", VALID_DOC)
    bad_path = _write(tmp_path, "bad.md", INVALID_DOC)
    cleanup_documents.append(str(good_path))

    report = ingest(tmp_path, "meridian", ChunkProfile.P512)

    assert report.documents_written == 1
    assert len(report.failed_files) == 1
    failed_path, reason = report.failed_files[0]
    assert failed_path == bad_path
    assert reason


def test_cli_exits_nonzero_when_a_file_fails(tmp_path, cleanup_documents):
    good_path = _write(tmp_path, "good.md", VALID_DOC)
    _write(tmp_path, "bad.md", INVALID_DOC)
    cleanup_documents.append(str(good_path))

    result = subprocess.run(
        [sys.executable, "-m", "rag.ingest", str(tmp_path), "--tenant", "meridian", "--profile", "512"],
        cwd=Path(__file__).resolve().parents[2] / "src",
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0


def test_ingest_connects_to_the_database_as_rag_ingest_role():
    from rag.ingest import _ingest_dsn

    assert "user=rag_ingest" in _ingest_dsn()


def test_database_rejects_document_write_under_a_different_tenant_than_the_guc():
    conn = psycopg.connect(dsn_for("rag_ingest"))
    try:
        set_tenant(conn, "meridian")
        with pytest.raises(psycopg.errors.Error):
            conn.execute(
                """
                INSERT INTO documents
                    (id, tenant_id, source_path, titulo, categoria, versao, visibilidade,
                     content_hash, texto_original)
                VALUES (%s, 'halcyon', 'tests/rogue.md', 'x', 'x', 'x', 'empresa', 'deadbeef', 'x')
                """,
                (uuid.uuid4(),),
            )
    finally:
        conn.rollback()
        conn.close()
