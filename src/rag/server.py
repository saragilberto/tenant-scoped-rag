"""MCP stdio server exposing read-only tools, scoped to one tenant per process.

RAG-16 / AD-003: tenant identity is resolved once from the environment at startup and
cached for the life of the process. No tool accepts a parameter that could change,
widen or disable that scope - a client has no argument to forge because none exists.
"""

from typing import Literal

from mcp.server import MCPServer

from rag import db
from rag.chunking import ChunkProfile
from rag.retrieval import Candidate, hybrid, lexical, semantic

__all__ = ["mcp", "main"]

Mode = Literal["semantic", "lexical", "hybrid"]
_SEARCH_MODULES = {"semantic": semantic, "lexical": lexical, "hybrid": hybrid}
_PROFILE = ChunkProfile.P512
_MAX_QUERY_CHARS = 2000
_MIN_TOP_K = 1
_MAX_TOP_K = 50

_active_tenant: str | None = None

mcp = MCPServer("rag")


def _tenant() -> str:
    if _active_tenant is None:
        raise RuntimeError(
            "server not started: call main() so the tenant is resolved before serving requests"
        )
    return _active_tenant


def _validate_query(query: str) -> str:
    if not query or not query.strip():
        raise ValueError("query must not be empty")
    if len(query) > _MAX_QUERY_CHARS:
        raise ValueError(f"query must be at most {_MAX_QUERY_CHARS} characters")
    return query


def _validate_top_k(top_k: int) -> int:
    if not (_MIN_TOP_K <= top_k <= _MAX_TOP_K):
        raise ValueError(f"top_k must be between {_MIN_TOP_K} and {_MAX_TOP_K}")
    return top_k


def _validate_mode(mode: str) -> Mode:
    if mode not in _SEARCH_MODULES:
        raise ValueError(f"mode must be one of {sorted(_SEARCH_MODULES)}")
    return mode  # type: ignore[return-value]


def _candidate_to_dict(candidate: Candidate) -> dict:
    return {
        "chunk_id": candidate.chunk_id,
        "document_id": candidate.document_id,
        "text": candidate.text,
        "score": candidate.score,
        "position": candidate.position,
    }


@mcp.tool()
def search(query: str, mode: Mode = "hybrid", top_k: int = 5) -> list[dict]:
    """Search the active tenant's corpus. Never accepts a scope parameter (RAG-16)."""
    query = _validate_query(query)
    top_k = _validate_top_k(top_k)
    mode = _validate_mode(mode)
    with db.scoped_connection(_tenant()) as conn:
        candidates = _SEARCH_MODULES[mode].search(conn, query, top_k, _PROFILE)
    return [_candidate_to_dict(c) for c in candidates]


def main() -> None:
    """Resolve the tenant and start serving. RAG-17: exits here, before any tool is
    ever announced, if the tenant environment variable is missing/empty/unknown."""
    global _active_tenant
    _active_tenant = db.resolve_tenant_from_env()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
