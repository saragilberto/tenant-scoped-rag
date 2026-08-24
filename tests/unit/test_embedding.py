"""RAG-06, RAG-07 and the model-load-failure edge case for src/rag/embedding.py."""

import numpy as np
import pytest

import rag.embedding as embedding


class _StubModel:
    def __init__(self):
        self.encoded_inputs: list = []

    def encode(self, inputs, convert_to_numpy=True):
        self.encoded_inputs.append(inputs)
        if isinstance(inputs, str):
            return np.zeros(embedding.EMBEDDING_DIMENSIONS)
        return np.zeros((len(inputs), embedding.EMBEDDING_DIMENSIONS))


@pytest.fixture(autouse=True)
def _clear_model_cache():
    embedding._model.cache_clear()
    yield
    embedding._model.cache_clear()


def test_embed_passages_prefixes_every_text_with_passage(monkeypatch):
    stub = _StubModel()
    monkeypatch.setattr(
        "sentence_transformers.SentenceTransformer", lambda *a, **kw: stub
    )

    embedding.embed_passages(["reset your password", "import a CSV file"])

    assert stub.encoded_inputs == [["passage: reset your password", "passage: import a CSV file"]]


def test_embed_query_prefixes_text_with_query(monkeypatch):
    stub = _StubModel()
    monkeypatch.setattr(
        "sentence_transformers.SentenceTransformer", lambda *a, **kw: stub
    )

    embedding.embed_query("how do I reset my password?")

    assert stub.encoded_inputs == ["query: how do I reset my password?"]


def test_embed_query_returns_768_dimensional_vector():
    vector = embedding.embed_query("what is the API rate limit?")

    assert len(vector) == 768


def test_embed_passages_returns_768_dimensional_vector_per_text():
    vectors = embedding.embed_passages(["first passage", "second passage"])

    assert len(vectors) == 2
    assert all(len(vector) == 768 for vector in vectors)


def test_model_load_failure_raises_explicit_error_when_unavailable(monkeypatch):
    def _raise_network_error(*args, **kwargs):
        raise OSError("could not connect to huggingface.co")

    monkeypatch.setattr("sentence_transformers.SentenceTransformer", _raise_network_error)

    with pytest.raises(RuntimeError, match="multilingual-e5-base"):
        embedding.embed_query("anything")
