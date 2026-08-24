"""Idempotent corpus ingestion: read markdown files, chunk, embed, and write once each.

Connects as ``rag_ingest`` - the only role allowed to write - scoped to the target tenant
by the same ``SET LOCAL`` mechanism as every other connection in this project. The database's
own write policy, not this script, is what makes it impossible to land a chunk under the
wrong tenant (see migrations/004_rls.sql).
"""

import hashlib
import os
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import psycopg
import yaml
from pgvector.psycopg import register_vector

from rag.chunking import ChunkProfile, split
from rag.embedding import embed_passages

__all__ = ["IngestReport", "ingest", "main"]

_VISIBILITY_VOCAB = {"empresa", "departamentos", "equipes", "restrito"}
_REQUIRED_FRONT_MATTER_FIELDS = ("title", "category", "version", "visibility")


@dataclass
class IngestReport:
    documents_written: int = 0
    chunks_written: int = 0
    failed_files: list[tuple[Path, str]] = field(default_factory=list)


def _ingest_dsn() -> str:
    host = os.environ.get("RAG_DB_HOST", "localhost")
    port = os.environ.get("RAG_DB_PORT", "55432")
    dbname = os.environ.get("RAG_DB_NAME", "rag")
    password = os.environ.get("RAG_INGEST_PASSWORD", "rag_ingest")
    return f"host={host} port={port} dbname={dbname} user=rag_ingest password={password}"


def _parse_front_matter(raw: str) -> tuple[dict, str]:
    if not raw.startswith("---"):
        raise ValueError("file is missing the leading YAML front matter block")
    _, fm_raw, body = raw.split("---", 2)
    front_matter = yaml.safe_load(fm_raw) or {}
    for field_name in _REQUIRED_FRONT_MATTER_FIELDS:
        if field_name not in front_matter:
            raise ValueError(f"front matter is missing required field: {field_name}")
    if front_matter["visibility"] not in _VISIBILITY_VOCAB:
        raise ValueError(f"front matter has invalid visibility: {front_matter['visibility']!r}")
    return front_matter, body.strip() + "\n"


def _content_hash(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def ingest(corpus_dir: Path, tenant_id: str, profile: ChunkProfile) -> IngestReport:
    report = IngestReport()
    files = sorted(corpus_dir.glob("*.md"))

    conn = psycopg.connect(_ingest_dsn())
    register_vector(conn)
    try:
        conn.execute("SELECT set_config('app.tenant_id', %s, true)", (tenant_id,))
        for path in files:
            try:
                _ingest_file(conn, path, tenant_id, profile, report)
            except Exception as exc:
                report.failed_files.append((path, str(exc)))
        conn.commit()
    finally:
        conn.close()
    return report


def _ingest_file(
    conn: psycopg.Connection,
    path: Path,
    tenant_id: str,
    profile: ChunkProfile,
    report: IngestReport,
) -> None:
    raw = path.read_text(encoding="utf-8")
    front_matter, body = _parse_front_matter(raw)

    source_path = str(path)
    content_hash = _content_hash(body)

    already_ingested = conn.execute(
        "SELECT id FROM documents WHERE tenant_id = %s AND source_path = %s AND content_hash = %s",
        (tenant_id, source_path, content_hash),
    ).fetchone()
    if already_ingested is not None:
        return

    document_id = uuid.uuid4()
    conn.execute(
        """
        INSERT INTO documents
            (id, tenant_id, source_path, titulo, categoria, versao, visibilidade,
             content_hash, texto_original)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            document_id,
            tenant_id,
            source_path,
            front_matter["title"],
            front_matter["category"],
            front_matter["version"],
            front_matter["visibility"],
            content_hash,
            body,
        ),
    )

    chunks = split(body, profile)
    if chunks:
        vectors = embed_passages([chunk.text for chunk in chunks])
        for chunk, vector in zip(chunks, vectors, strict=True):
            conn.execute(
                """
                INSERT INTO chunks (id, document_id, tenant_id, profile, ord, texto, embedding)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    uuid.uuid4(),
                    document_id,
                    tenant_id,
                    profile.value,
                    chunk.ord,
                    chunk.text,
                    vector,
                ),
            )

    report.documents_written += 1
    report.chunks_written += len(chunks)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Ingest a tenant's corpus into the RAG database.")
    parser.add_argument("corpus_dir", type=Path)
    parser.add_argument("--tenant", required=True)
    parser.add_argument("--profile", required=True, choices=["512", "1024"])
    args = parser.parse_args()

    profile = ChunkProfile.P512 if args.profile == "512" else ChunkProfile.P1024
    report = ingest(args.corpus_dir, args.tenant, profile)

    print(f"documents written: {report.documents_written}")
    print(f"chunks written: {report.chunks_written}")
    if report.failed_files:
        for path, reason in report.failed_files:
            print(f"FAILED {path}: {reason}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
