"""RAG-08: ts_rank_cd lexical search over the generated tsvector column."""

import uuid

import pytest

from rag.chunking import ChunkProfile
from rag.db import scoped_connection
from rag.retrieval import lexical


def test_search_caps_results_at_top_k_when_more_matches_exist():
    # meridian has 5 chunks matching "factor authentication" at P512 (see test_indexes.py /
    # test_lexical_search_uses_gin_index for the underlying GIN-index-is-usable proof).
    with scoped_connection("meridian") as conn:
        results = lexical.search(conn, "factor authentication", top_k=3, profile=ChunkProfile.P512)

    assert len(results) == 3


def test_search_orders_results_by_descending_ts_rank_cd():
    with scoped_connection("meridian") as conn:
        results = lexical.search(conn, "factor authentication", top_k=8, profile=ChunkProfile.P512)

    assert len(results) >= 2
    scores = [c.score for c in results]
    assert scores == sorted(scores, reverse=True)


@pytest.fixture
def accented_chunk(admin_conn_autocommit):
    document_id = admin_conn_autocommit.execute(
        "SELECT id FROM documents WHERE tenant_id = 'meridian' LIMIT 1"
    ).fetchone()[0]
    chunk_id = uuid.uuid4()
    admin_conn_autocommit.execute(
        """
        INSERT INTO chunks (id, document_id, tenant_id, profile, ord, texto, embedding)
        VALUES (%s, %s, 'meridian', 'P512', 999, %s, %s)
        """,
        (chunk_id, document_id, "The café loyalty program tracks visits.", [0.0] * 768),
    )
    yield chunk_id
    admin_conn_autocommit.execute("DELETE FROM chunks WHERE id = %s", (chunk_id,))


def test_accented_and_unaccented_queries_match_each_other(accented_chunk):
    with scoped_connection("meridian") as conn:
        unaccented_hit = lexical.search(conn, "cafe", top_k=20, profile=ChunkProfile.P512)
        accented_hit = lexical.search(conn, "café", top_k=20, profile=ChunkProfile.P512)

    unaccented_ids = {c.chunk_id for c in unaccented_hit}
    accented_ids = {c.chunk_id for c in accented_hit}
    assert str(accented_chunk) in unaccented_ids
    assert str(accented_chunk) in accented_ids


def test_search_scope_never_returns_chunks_from_another_tenant(admin_conn):
    # "factor authentication" (2FA) is one of the topics deliberately covered by both
    # tenants' corpora (see corpus/*/two-factor-auth.md), so halcyon has real matches too -
    # a scope leak here would actually surface halcyon chunks, not just return nothing.
    with scoped_connection("meridian") as conn:
        results = lexical.search(conn, "factor authentication", top_k=20, profile=ChunkProfile.P512)

    assert results
    chunk_ids = [c.chunk_id for c in results]
    tenant_ids = admin_conn.execute(
        "SELECT DISTINCT tenant_id FROM chunks WHERE id = ANY(%s)",
        (chunk_ids,),
    ).fetchall()
    assert tenant_ids == [("meridian",)]
