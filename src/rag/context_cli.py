"""``rag-context``: retrieve tenant-scoped context and hand it to the local LLM's chat page.

The only module in this repository with ``argparse``/``print`` for this command - it never
calls a chat completion endpoint, it only prepares the text a person pastes into the chat
``llamafile`` already serves.
"""

import argparse
import sys

import psycopg

from rag import context_block, db, local_llm, query
from rag.chunking import ChunkProfile

__all__ = ["build_parser", "main"]


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


def main() -> None:
    args = build_parser().parse_args()

    tenant_id = db.resolve_tenant_from_env()

    try:
        question = query.validate_query(args.question)
        top_k = query.validate_top_k(args.top_k)
        mode = query.validate_mode(args.mode)
    except ValueError as exc:
        sys.exit(str(exc))

    try:
        base_url = local_llm.resolve_base_url()
    except ValueError as exc:
        sys.exit(str(exc))

    status = local_llm.check_health(base_url)
    if not status.reachable:
        print(
            f"warning: local LLM at {base_url} is not responding ({status.detail}). "
            "Start llamafile if you want to chat with the context.",
            file=sys.stderr,
        )

    profile = ChunkProfile(args.profile)
    try:
        with db.scoped_connection(tenant_id) as conn:
            candidates = query.run_search(conn, question, mode, top_k, profile)
    except psycopg.OperationalError as exc:
        sys.exit(f"database is unreachable: {exc}")

    if not candidates:
        print("no context found for this question.", file=sys.stderr)
        return

    block = context_block.build_block(question, candidates)

    if status.context_window is not None:
        estimated = context_block.estimate_tokens(block)
        if estimated > status.context_window:
            print(
                f"warning: context block is ~{estimated} tokens, larger than the local "
                f"LLM's context window ({status.context_window}).",
                file=sys.stderr,
            )

    print(block)

    if not context_block.copy_to_clipboard(block):
        print("note: could not copy the context block to the clipboard.", file=sys.stderr)

    if args.open and not local_llm.open_browser(base_url):
        print(f"warning: could not open the browser at {base_url}.", file=sys.stderr)
