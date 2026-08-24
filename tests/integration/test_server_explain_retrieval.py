"""RAG-27, RAG-28: explain_retrieval exposes per-ranking scores/positions, the fused
position and the cutoff reason for every candidate - and never a hint of what RLS
already removed from the other tenant's scope."""

import pytest

from rag import server

_SHARED_SUBJECT_QUERY = "erro de login"


@pytest.fixture(autouse=True)
def _active_tenant(monkeypatch):
    monkeypatch.setattr(server, "_active_tenant", "meridian")


def test_explain_retrieval_reports_scores_positions_fused_and_cutoff_per_candidate():
    result = server.explain_retrieval(_SHARED_SUBJECT_QUERY, mode="hybrid", top_k=5)
    assert result
    for i, candidate in enumerate(result, start=1):
        assert candidate["chunk_id"]
        assert candidate["document_id"]
        assert candidate["fused_position"] == i
        assert candidate["cutoff_reason"]
        assert candidate["semantic_score"] is not None or candidate["lexical_score"] is not None


def test_explain_retrieval_semantic_and_lexical_modes_populate_only_their_own_ranking():
    semantic_only = server.explain_retrieval(_SHARED_SUBJECT_QUERY, mode="semantic", top_k=5)
    for candidate in semantic_only:
        assert candidate["semantic_position"] is not None
        assert candidate["lexical_score"] is None
        assert candidate["lexical_position"] is None

    lexical_only = server.explain_retrieval(_SHARED_SUBJECT_QUERY, mode="lexical", top_k=5)
    for candidate in lexical_only:
        assert candidate["lexical_position"] is not None
        assert candidate["semantic_score"] is None
        assert candidate["semantic_position"] is None


def test_explain_retrieval_omits_out_of_scope_candidates(admin_conn, monkeypatch):
    monkeypatch.setattr(server, "_active_tenant", "meridian")
    result = server.explain_retrieval(_SHARED_SUBJECT_QUERY, mode="hybrid", top_k=50)
    result_chunk_ids = {c["chunk_id"] for c in result}

    halcyon_chunk_ids = {
        str(r[0])
        for r in admin_conn.execute("SELECT id FROM chunks WHERE tenant_id = 'halcyon'").fetchall()
    }
    assert result_chunk_ids.isdisjoint(halcyon_chunk_ids)
    for candidate in result:
        assert "out_of_scope_count" not in candidate
        assert "total_candidates" not in candidate


def test_explain_retrieval_on_shared_subject_reveals_nothing_about_the_other_tenant(monkeypatch):
    monkeypatch.setattr(server, "_active_tenant", "meridian")
    meridian_result = server.explain_retrieval(_SHARED_SUBJECT_QUERY, mode="hybrid", top_k=5)

    monkeypatch.setattr(server, "_active_tenant", "halcyon")
    halcyon_result = server.explain_retrieval(_SHARED_SUBJECT_QUERY, mode="hybrid", top_k=5)

    assert meridian_result
    assert halcyon_result
    meridian_ids = {c["chunk_id"] for c in meridian_result}
    meridian_ids |= {c["document_id"] for c in meridian_result}
    halcyon_ids = {c["chunk_id"] for c in halcyon_result}
    halcyon_ids |= {c["document_id"] for c in halcyon_result}
    assert meridian_ids.isdisjoint(halcyon_ids)
