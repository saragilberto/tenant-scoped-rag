"""Query validation and search-mode dispatch, shared by the MCP server and the CLI.

Extracted from ``rag.server`` (RAG-11/12/13/16 behavior, unchanged) so a second caller
(the ``rag-context`` command) can validate and run a search without importing the MCP
server module.
"""

from typing import Literal

import psycopg

from rag.chunking import ChunkProfile
from rag.retrieval import Candidate, hybrid, lexical, semantic

__all__ = [
    "MAX_QUERY_CHARS",
    "MIN_TOP_K",
    "MAX_TOP_K",
    "SEARCH_MODULES",
    "Mode",
    "validate_query",
    "validate_top_k",
    "validate_mode",
    "run_search",
]

Mode = Literal["semantic", "lexical", "hybrid"]
SEARCH_MODULES = {"semantic": semantic, "lexical": lexical, "hybrid": hybrid}
MAX_QUERY_CHARS = 2000
MIN_TOP_K = 1
MAX_TOP_K = 50


def validate_query(query: str) -> str:
    if not query or not query.strip():
        raise ValueError("query must not be empty")
    if len(query) > MAX_QUERY_CHARS:
        raise ValueError(f"query must be at most {MAX_QUERY_CHARS} characters")
    return query


def validate_top_k(top_k: int) -> int:
    if not (MIN_TOP_K <= top_k <= MAX_TOP_K):
        raise ValueError(f"top_k must be between {MIN_TOP_K} and {MAX_TOP_K}")
    return top_k


def validate_mode(mode: str) -> Mode:
    if mode not in SEARCH_MODULES:
        raise ValueError(f"mode must be one of {sorted(SEARCH_MODULES)}")
    return mode  # type: ignore[return-value]


def run_search(
    conn: psycopg.Connection, query: str, mode: Mode, top_k: int, profile: ChunkProfile
) -> list[Candidate]:
    return SEARCH_MODULES[mode].search(conn, query, top_k, profile)
