"""Local e5 embeddings with the query/passage prefixes the model requires.

``embed_passages`` and ``embed_query`` are separate functions on purpose: a single function
with a mode parameter is exactly the shape of bug where someone forgets the prefix and
nothing breaks loudly - it just quietly loses recall.
"""

from functools import lru_cache

__all__ = ["embed_passages", "embed_query", "EMBEDDING_DIMENSIONS"]

_MODEL_NAME = "intfloat/multilingual-e5-base"
_MODEL_REVISION = "d128750597153bb5987e10b1c3493a34e5a4502a"

EMBEDDING_DIMENSIONS = 768


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer

    try:
        return SentenceTransformer(_MODEL_NAME, revision=_MODEL_REVISION)
    except Exception as exc:
        raise RuntimeError(
            f"Could not load embedding model {_MODEL_NAME!r} (revision {_MODEL_REVISION}). "
            "It is not cached locally and no network connection is available to download it."
        ) from exc


def embed_passages(texts: list[str]) -> list[list[float]]:
    prefixed = [f"passage: {text}" for text in texts]
    vectors = _model().encode(prefixed, convert_to_numpy=True)
    return [vector.tolist() for vector in vectors]


def embed_query(text: str) -> list[float]:
    vector = _model().encode(f"query: {text}", convert_to_numpy=True)
    return vector.tolist()
