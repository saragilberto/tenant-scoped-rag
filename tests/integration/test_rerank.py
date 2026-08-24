"""RAG-32, RAG-33, RAG-34 for src/rag/retrieval/rerank.py."""

import pytest

import rag.retrieval.rerank as rerank
from rag.retrieval import Candidate


@pytest.fixture(autouse=True)
def _clear_model_cache():
    rerank._model.cache_clear()
    yield
    rerank._model.cache_clear()


def _candidate(chunk_id: str, text: str, position: int) -> Candidate:
    return Candidate(
        chunk_id=chunk_id, document_id="doc-1", text=text, score=0.0, position=position
    )


def test_is_enabled_defaults_to_false_without_the_env_var(monkeypatch):
    monkeypatch.delenv("RAG_RERANK_ENABLED", raising=False)

    assert rerank.is_enabled() is False


def test_is_enabled_true_when_env_var_is_set(monkeypatch):
    monkeypatch.setenv("RAG_RERANK_ENABLED", "1")

    assert rerank.is_enabled() is True


def test_apply_reorders_candidates_by_model_score(monkeypatch):
    candidates = [
        _candidate("worst", "irrelevant text", position=1),
        _candidate("best", "highly relevant text", position=2),
        _candidate("middle", "somewhat relevant text", position=3),
    ]

    class _StubCrossEncoder:
        def __init__(self, *args, **kwargs):
            pass

        def predict(self, pairs):
            score_by_text = {
                "irrelevant text": 0.1,
                "highly relevant text": 0.9,
                "somewhat relevant text": 0.5,
            }
            return [score_by_text[text] for _query, text in pairs]

    monkeypatch.setattr("sentence_transformers.CrossEncoder", _StubCrossEncoder)

    reordered = rerank.apply("some query", candidates)

    assert [c.chunk_id for c in reordered] == ["best", "middle", "worst"]
    assert [c.position for c in reordered] == [1, 2, 3]


def test_apply_raises_explicit_error_when_model_unavailable(monkeypatch):
    candidates = [_candidate("a", "text a", position=1)]

    def _raise_network_error(*args, **kwargs):
        raise OSError("could not connect to huggingface.co")

    monkeypatch.setattr("sentence_transformers.CrossEncoder", _raise_network_error)

    with pytest.raises(RuntimeError, match="bge-reranker-v2-m3"):
        rerank.apply("some query", candidates)
