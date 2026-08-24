"""RAG-07, RAG-10 and the no-match edge case for src/rag/retrieval/semantic.py."""

from rag.chunking import ChunkProfile
from rag.db import scoped_connection
from rag.retrieval import semantic


def test_search_delegates_query_embedding_to_the_prefixing_function(monkeypatch):
    calls: list[str] = []

    def fake_embed_query(text: str):
        calls.append(text)
        return [0.0] * 768

    monkeypatch.setattr("rag.retrieval.semantic.embed_query", fake_embed_query)

    with scoped_connection("meridian") as conn:
        semantic.search(conn, "how do I reset my password?", top_k=1, profile=ChunkProfile.P512)

    assert calls == ["how do I reset my password?"]


def test_scoped_search_returns_exactly_top_k_when_scope_has_enough_chunks():
    with scoped_connection("meridian") as conn:
        results = semantic.search(conn, "password reset", top_k=5, profile=ChunkProfile.P512)

    assert len(results) == 5


def test_search_orders_results_by_ascending_cosine_distance():
    with scoped_connection("meridian") as conn:
        results = semantic.search(conn, "password reset", top_k=8, profile=ChunkProfile.P512)

    scores = [c.score for c in results]
    assert scores == sorted(scores)


def test_search_with_no_chunks_in_scope_returns_empty_list_not_worst_match():
    with scoped_connection("meridian") as conn:
        results = semantic.search(conn, "password reset", top_k=5, profile=ChunkProfile.P1024)

    assert results == []


def test_candidate_preserves_score_and_position_for_each_result():
    with scoped_connection("meridian") as conn:
        results = semantic.search(conn, "password reset", top_k=4, profile=ChunkProfile.P512)

    assert [c.position for c in results] == [1, 2, 3, 4]
    assert all(isinstance(c.score, float) for c in results)
