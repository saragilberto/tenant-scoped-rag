"""RAG-09: Reciprocal Rank Fusion (k=60) for src/rag/retrieval/hybrid.py.

The fixture below seeds ten synthetic chunks with fully controlled semantic and lexical
ranks (via hand-picked embeddings and term repetition counts) so the RRF math can be
checked exactly, instead of relying on the real corpus where nobody controls the ranks.

Layout (semantic rank is by construction 1..10 in this order; lexical rank only exists for
the four chunks that contain "rrftestterm", most repetitions first): A, B, C (semantic
top-3, no lexical match) - G (semantic #4, weakest lexical match among the four) - H, I, J
(filler, no lexical match, push the lexical specialists' semantic rank down) - D, E, F
(semantic #8-10, but the three best lexical matches). RRF is expected to rank G first: it
is outside the individual top-3 on both sides, but F/E/D's semantic rank is bad enough
that G's balanced rank-4-and-4 wins.
"""

import uuid

import pytest

from rag.chunking import ChunkProfile
from rag.db import scoped_connection
from rag.retrieval import hybrid

_LABELS = ["A", "B", "C", "G", "H", "I", "J", "D", "E", "F"]
_TERM_COUNTS = {"G": 2, "D": 4, "E": 6, "F": 8}  # only these four contain "rrftestterm"


def _embedding_for_rank(i: int) -> list[float]:
    # Steps are large enough (0.02 per rank) to stay well clear of the vector column's
    # float4 precision and of any residual approximation in the HNSW index, so the ten
    # ranks never collapse into a tie the way a much smaller step did in practice.
    vector = [0.0] * 768
    vector[0] = 1.0 - i * 0.02
    vector[1] = i * 0.02
    return vector


def _text_for(label: str) -> str:
    filler = "unrelated filler content about nothing in particular. "
    count = _TERM_COUNTS.get(label, 0)
    return filler + "rrftestterm " * count


@pytest.fixture
def rrf_fixture(admin_conn_autocommit):
    document_id = admin_conn_autocommit.execute(
        "SELECT id FROM documents WHERE tenant_id = 'meridian' LIMIT 1"
    ).fetchone()[0]

    chunk_ids: dict[str, str] = {}
    for i, label in enumerate(_LABELS):
        chunk_id = uuid.uuid4()
        chunk_ids[label] = str(chunk_id)
        admin_conn_autocommit.execute(
            """
            INSERT INTO chunks (id, document_id, tenant_id, profile, ord, texto, embedding)
            VALUES (%s, %s, 'meridian', 'P512', %s, %s, %s)
            """,
            (chunk_id, document_id, 9000 + i, _text_for(label), _embedding_for_rank(i)),
        )
    yield chunk_ids
    admin_conn_autocommit.execute(
        "DELETE FROM chunks WHERE id = ANY(%s)", (list(chunk_ids.values()),)
    )


def _probe_query_embedding(*_args, **_kwargs):
    vector = [0.0] * 768
    vector[0] = 1.0
    return vector


def test_fusion_score_equals_reciprocal_rank_sum_of_positions(monkeypatch, rrf_fixture):
    monkeypatch.setattr("rag.retrieval.semantic.embed_query", _probe_query_embedding)

    with scoped_connection("meridian") as conn:
        results = hybrid.search(conn, "rrftestterm", top_k=10, profile=ChunkProfile.P512)

    by_id = {c.chunk_id: c for c in results}
    g_candidate = by_id[rrf_fixture["G"]]
    # G is semantic rank 4 (index 3 among the 10 synthetic chunks) and lexical rank 4
    # (weakest of the four "rrftestterm" chunks): 1/(60+4) + 1/(60+4).
    assert g_candidate.score == pytest.approx(1 / 64 + 1 / 64)

    a_candidate = by_id[rrf_fixture["A"]]
    # A is semantic rank 1 and has no lexical match at all: 1/(60+1) + 0.
    assert a_candidate.score == pytest.approx(1 / 61)


def test_document_outside_top3_of_both_individual_rankings_appears_in_top3_fused(
    monkeypatch, rrf_fixture
):
    monkeypatch.setattr("rag.retrieval.semantic.embed_query", _probe_query_embedding)

    with scoped_connection("meridian") as conn:
        results = hybrid.search(conn, "rrftestterm", top_k=3, profile=ChunkProfile.P512)

    top3_ids = [c.chunk_id for c in results]
    assert rrf_fixture["G"] in top3_ids


def test_hybrid_search_result_positions_are_sequential_and_score_descending(
    monkeypatch, rrf_fixture
):
    monkeypatch.setattr("rag.retrieval.semantic.embed_query", _probe_query_embedding)

    with scoped_connection("meridian") as conn:
        results = hybrid.search(conn, "rrftestterm", top_k=5, profile=ChunkProfile.P512)

    assert [c.position for c in results] == [1, 2, 3, 4, 5]
    scores = [c.score for c in results]
    assert scores == sorted(scores, reverse=True)


def test_hybrid_search_respects_tenant_scope_in_both_source_rankings(admin_conn):
    with scoped_connection("meridian") as conn:
        results = hybrid.search(conn, "factor authentication", top_k=10, profile=ChunkProfile.P512)

    assert results
    chunk_ids = [c.chunk_id for c in results]
    tenant_ids = admin_conn.execute(
        "SELECT DISTINCT tenant_id FROM chunks WHERE id = ANY(%s)",
        (chunk_ids,),
    ).fetchall()
    assert tenant_ids == [("meridian",)]


def test_hybrid_search_caps_results_at_top_k():
    with scoped_connection("meridian") as conn:
        results = hybrid.search(conn, "factor authentication", top_k=2, profile=ChunkProfile.P512)

    assert len(results) == 2
