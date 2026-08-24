"""RAG-07, RAG-10: cosine-distance search over the profile's partial HNSW index."""

import psycopg
from pgvector import Vector
from pgvector.psycopg import register_vector

from rag.chunking import ChunkProfile
from rag.embedding import embed_query
from rag.retrieval import Candidate

__all__ = ["search"]


def search(
    conn: psycopg.Connection, query: str, top_k: int, profile: ChunkProfile
) -> list[Candidate]:
    register_vector(conn)
    vector = Vector(embed_query(query))
    rows = conn.execute(
        """
        SELECT id, document_id, texto, embedding <=> %s AS distance
        FROM chunks
        WHERE profile = %s
        ORDER BY embedding <=> %s
        LIMIT %s
        """,
        (vector, profile.value, vector, top_k),
    ).fetchall()
    return [
        Candidate(
            chunk_id=str(row[0]),
            document_id=str(row[1]),
            text=row[2],
            score=float(row[3]),
            position=i + 1,
        )
        for i, row in enumerate(rows)
    ]
