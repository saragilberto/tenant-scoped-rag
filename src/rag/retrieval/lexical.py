"""RAG-08: lexical search by ts_rank_cd over the generated tsvector column."""

import psycopg

from rag.chunking import ChunkProfile
from rag.retrieval import Candidate

__all__ = ["search"]


def search(
    conn: psycopg.Connection, query: str, top_k: int, profile: ChunkProfile
) -> list[Candidate]:
    rows = conn.execute(
        """
        SELECT id, document_id, texto,
               ts_rank_cd(fts, plainto_tsquery('english', immutable_unaccent(%s))) AS rank
        FROM chunks
        WHERE profile = %s
          AND fts @@ plainto_tsquery('english', immutable_unaccent(%s))
        ORDER BY rank DESC
        LIMIT %s
        """,
        (query, profile.value, query, top_k),
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
