"""RAG-23: the server is startable with a single command and no manual step beyond
having the database up and the corpus ingested - proven here by actually running that
command as a real subprocess, not by inspecting the entry point declaration."""

import asyncio
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run_handshake_over_subprocess() -> set[str]:
    async def go() -> set[str]:
        params = StdioServerParameters(
            command="uv",
            args=["run", "--directory", str(REPO_ROOT), "rag-server"],
            env={"RAG_TENANT_ID": "meridian"},
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await asyncio.wait_for(session.initialize(), timeout=30)
                result = await asyncio.wait_for(session.list_tools(), timeout=10)
                return {tool.name for tool in result.tools}

    return asyncio.run(go())


def test_rag_server_entry_point_starts_and_announces_tools_with_no_manual_step():
    names = _run_handshake_over_subprocess()
    assert names == {"search", "get_document", "list_sources", "explain_retrieval"}
