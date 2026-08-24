"""RAG-09: Reciprocal Rank Fusion over the semantic and lexical rankings.

RRF combines positions, never the raw scores: cosine distance and ts_rank_cd live on
incompatible scales, and summing them would need an arbitrary normalization RRF avoids
entirely by only ever looking at where a candidate sits in each ranking.
"""

import psycopg

from rag.chunking import ChunkProfile
from rag.retrieval import Candidate
from rag.retrieval import lexical as lexical_mode
from rag.retrieval import semantic as semantic_mode

__all__ = ["search"]

_RRF_K = 60
_CANDIDATE_POOL_SIZE = 50


def search(
    conn: psycopg.Connection, query: str, top_k: int, profile: ChunkProfile
) -> list[Candidate]:
    semantic_results = semantic_mode.search(conn, query, _CANDIDATE_POOL_SIZE, profile)
    lexical_results = lexical_mode.search(conn, query, _CANDIDATE_POOL_SIZE, profile)

    semantic_positions = {c.chunk_id: c.position for c in semantic_results}
    lexical_positions = {c.chunk_id: c.position for c in lexical_results}
    texts = {c.chunk_id: c.text for c in semantic_results}
    documents = {c.chunk_id: c.document_id for c in semantic_results}
    for c in lexical_results:
        texts.setdefault(c.chunk_id, c.text)
        documents.setdefault(c.chunk_id, c.document_id)

    fused_scores: dict[str, float] = {}
    for chunk_id in set(semantic_positions) | set(lexical_positions):
        score = 0.0
        if chunk_id in semantic_positions:
            score += 1.0 / (_RRF_K + semantic_positions[chunk_id])
        if chunk_id in lexical_positions:
            score += 1.0 / (_RRF_K + lexical_positions[chunk_id])
        fused_scores[chunk_id] = score

    ranked_ids = sorted(fused_scores, key=lambda cid: fused_scores[cid], reverse=True)[:top_k]
    return [
        Candidate(
            chunk_id=chunk_id,
            document_id=documents[chunk_id],
            text=texts[chunk_id],
            score=fused_scores[chunk_id],
            position=i + 1,
        )
        for i, chunk_id in enumerate(ranked_ids)
    ]
