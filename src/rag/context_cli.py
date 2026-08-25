"""``rag-context``: retrieve tenant-scoped context and hand it to the local LLM's chat page.

The only module in this repository with ``argparse``/``print`` for this command - it never
calls a chat completion endpoint, it only prepares the text a person pastes into the chat
``llamafile`` already serves.
"""

import argparse

from rag.chunking import ChunkProfile

__all__ = ["build_parser"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rag-context",
        description="Retrieve tenant-scoped context for a question and deliver it "
        "ready to paste into the local LLM's chat.",
    )
    parser.add_argument("question", help="the question to retrieve context for")
    parser.add_argument(
        "--mode",
        choices=["semantic", "lexical", "hybrid"],
        default="hybrid",
        help="search mode (default: hybrid)",
    )
    parser.add_argument(
        "--top-k",
        dest="top_k",
        type=int,
        default=5,
        help="number of chunks to retrieve (default: 5)",
    )
    parser.add_argument(
        "--profile",
        choices=[p.value for p in ChunkProfile],
        default=ChunkProfile.P512.value,
        help="chunk profile (default: P512)",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="open the local LLM's chat page in the default browser",
    )
    return parser
