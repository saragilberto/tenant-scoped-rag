"""RAG-32, RAG-33, RAG-34: optional cross-encoder reranking, off by default.

Only measures what reranking adds to the ablation study when it is actually invoked - so a
caller checks ``is_enabled()`` and, if true, reorders candidates with ``apply`` before cutting
to ``top_k``. There is no silent fallback: a caller that turns the flag on and finds the model
missing gets a loud failure, never the untouched ranking pretending to be reranked.
"""

import os
from functools import lru_cache

from rag.retrieval import Candidate

__all__ = ["is_enabled", "apply"]

_ENV_FLAG = "RAG_RERANK_ENABLED"
_MODEL_NAME = "BAAI/bge-reranker-v2-m3"
_MODEL_REVISION = "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e"


def is_enabled() -> bool:
    return os.environ.get(_ENV_FLAG, "").strip().lower() in {"1", "true", "yes"}


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import CrossEncoder

    try:
        return CrossEncoder(_MODEL_NAME, revision=_MODEL_REVISION)
    except Exception as exc:
        raise RuntimeError(
            f"Reranking is enabled but the model {_MODEL_NAME!r} (revision {_MODEL_REVISION}) "
            "is not cached locally and no network connection is available to download it."
        ) from exc


def apply(query: str, candidates: list[Candidate]) -> list[Candidate]:
    if not candidates:
        return []

    pairs = [(query, c.text) for c in candidates]
    scores = _model().predict(pairs)
    order = sorted(range(len(candidates)), key=lambda i: scores[i], reverse=True)
    return [
        Candidate(
            chunk_id=candidates[i].chunk_id,
            document_id=candidates[i].document_id,
            text=candidates[i].text,
            score=float(scores[i]),
            position=position + 1,
        )
        for position, i in enumerate(order)
    ]
