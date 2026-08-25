"""MCP stdio server exposing read-only tools, scoped to one tenant per process.

RAG-16 / AD-003: tenant identity is resolved once from the environment at startup and
cached for the life of the process. No tool accepts a parameter that could change,
widen or disable that scope - a client has no argument to forge because none exists.
"""

import uuid
from typing import Annotated

import psycopg
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field, StringConstraints

from rag import db
from rag import query as rag_query
from rag.chunking import ChunkProfile
from rag.query import Mode
from rag.retrieval import Candidate, lexical, semantic

__all__ = ["mcp", "main"]

_PROFILE = ChunkProfile.P512

# Schema-level constraints, not just the manual checks below: the SDK validates arguments
# against these before the tool body ever runs, and a rejection at that layer keeps the
# specific reason ("top_k must be...") in what the client sees. A bare exception raised
# from inside the tool body is treated as a crash and replaced with a generic message -
# `rag_query.validate_query`/`rag_query.validate_top_k` stay as a second line of defense for
# direct callers (this module's own tests included), who bypass argument validation entirely.
Query = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=rag_query.MAX_QUERY_CHARS),
]
TopK = Annotated[int, Field(ge=rag_query.MIN_TOP_K, le=rag_query.MAX_TOP_K)]

_EXPLAIN_POOL_SIZE = 50
_RRF_K = 60

_NOT_FOUND = {"found": False}

_active_tenant: str | None = None

mcp = MCPServer("rag")


def _tenant() -> str:
    if _active_tenant is None:
        raise RuntimeError(
            "server not started: call main() so the tenant is resolved before serving requests"
        )
    return _active_tenant


def _candidate_to_dict(candidate: Candidate) -> dict:
    return {
        "chunk_id": candidate.chunk_id,
        "document_id": candidate.document_id,
        "text": candidate.text,
        "score": candidate.score,
        "position": candidate.position,
    }


@mcp.tool()
def search(query: Query, mode: Mode = "hybrid", top_k: TopK = 5) -> list[dict]:
    """Search the active tenant's corpus. Never accepts a scope parameter (RAG-16)."""
    query = rag_query.validate_query(query)
    top_k = rag_query.validate_top_k(top_k)
    mode = rag_query.validate_mode(mode)
    try:
        with db.scoped_connection(_tenant()) as conn:
            candidates = rag_query.run_search(conn, query, mode, top_k, _PROFILE)
    except psycopg.OperationalError as exc:
        raise ToolError(f"database is unreachable: {exc}") from exc
    return [_candidate_to_dict(c) for c in candidates]


@mcp.tool()
def get_document(doc_id: str) -> dict:
    """Return the original document text and metadata, scoped to the active tenant.

    An unknown id and an id that belongs to another tenant produce the identical
    not-found response (RAG-25) - RLS already hides the other tenant's row, so both
    cases reach this function as "no matching row" and there is nothing left here
    that could tell them apart.
    """
    try:
        uuid.UUID(doc_id)
    except ValueError:
        return _NOT_FOUND
    with db.scoped_connection(_tenant()) as conn:
        row = conn.execute(
            """
            SELECT id, titulo, categoria, versao, visibilidade, texto_original
            FROM documents
            WHERE id = %s
            """,
            (doc_id,),
        ).fetchone()
    if row is None:
        return _NOT_FOUND
    return {
        "found": True,
        "doc_id": str(row[0]),
        "titulo": row[1],
        "categoria": row[2],
        "versao": row[3],
        "visibilidade": row[4],
        "texto": row[5],
    }


@mcp.tool()
def list_sources() -> list[dict]:
    """List the active tenant's documents with each one's chunk count (RAG-26)."""
    with db.scoped_connection(_tenant()) as conn:
        rows = conn.execute(
            """
            SELECT d.id, d.titulo, count(c.id)
            FROM documents d
            LEFT JOIN chunks c ON c.document_id = d.id
            GROUP BY d.id, d.titulo
            ORDER BY d.titulo
            """
        ).fetchall()
    return [{"doc_id": str(r[0]), "titulo": r[1], "chunk_count": r[2]} for r in rows]


@mcp.tool()
def explain_retrieval(query: Query, mode: Mode = "hybrid", top_k: TopK = 5) -> list[dict]:
    """Explain the fused ranking for a query: per-ranking score/position, fused
    position, and why each candidate made the cut (RAG-27).

    Only ever describes in-scope candidates: the semantic and lexical queries below
    run through ``scoped_connection``, so RLS has already removed every other
    tenant's row before either ranking is built - there is no out-of-scope candidate
    left to omit, count, or otherwise leak a hint about (RAG-28).
    """
    query = rag_query.validate_query(query)
    top_k = rag_query.validate_top_k(top_k)
    mode = rag_query.validate_mode(mode)

    try:
        with db.scoped_connection(_tenant()) as conn:
            semantic_results = semantic.search(conn, query, _EXPLAIN_POOL_SIZE, _PROFILE)
            lexical_results = lexical.search(conn, query, _EXPLAIN_POOL_SIZE, _PROFILE)
    except psycopg.OperationalError as exc:
        raise ToolError(f"database is unreachable: {exc}") from exc

    semantic_by_id = {c.chunk_id: c for c in semantic_results}
    lexical_by_id = {c.chunk_id: c for c in lexical_results}

    if mode == "semantic":
        candidate_ids = list(semantic_by_id)
    elif mode == "lexical":
        candidate_ids = list(lexical_by_id)
    else:
        fused_scores: dict[str, float] = {}
        for chunk_id in set(semantic_by_id) | set(lexical_by_id):
            score = 0.0
            if chunk_id in semantic_by_id:
                score += 1.0 / (_RRF_K + semantic_by_id[chunk_id].position)
            if chunk_id in lexical_by_id:
                score += 1.0 / (_RRF_K + lexical_by_id[chunk_id].position)
            fused_scores[chunk_id] = score
        candidate_ids = sorted(fused_scores, key=lambda cid: fused_scores[cid], reverse=True)

    explained = []
    for rank, chunk_id in enumerate(candidate_ids[:top_k], start=1):
        sem = semantic_by_id.get(chunk_id)
        lex = lexical_by_id.get(chunk_id)
        document_id = (sem or lex).document_id
        explained.append(
            {
                "chunk_id": chunk_id,
                "document_id": document_id,
                "semantic_score": sem.score if sem else None,
                "semantic_position": sem.position if sem else None,
                "lexical_score": lex.score if lex else None,
                "lexical_position": lex.position if lex else None,
                "fused_position": rank,
                "cutoff_reason": f"within top_k={top_k} of the {mode} ranking",
            }
        )
    return explained


def main() -> None:
    """Resolve the tenant and start serving. RAG-17: exits here, before any tool is
    ever announced, if the tenant environment variable is missing/empty/unknown."""
    global _active_tenant
    _active_tenant = db.resolve_tenant_from_env()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
