"""RAG-11, RAG-12, RAG-13, RAG-16, RAG-17, RAG-21, RAG-22: the MCP server bootstrap
and the search tool's validation contract."""

import asyncio
from contextlib import asynccontextmanager

import psycopg
import pytest
from mcp import ClientSession
from mcp.client._memory import InMemoryTransport
from mcp.server.mcpserver.exceptions import ToolError

from rag import server


@pytest.fixture(autouse=True)
def _active_tenant(monkeypatch):
    monkeypatch.setattr(server, "_active_tenant", "meridian")


def _list_tools():
    return asyncio.run(server.mcp.list_tools())


@asynccontextmanager
async def _client_session():
    """A real MCP client talking to ``server.mcp`` over the SDK's own wire protocol.

    Calling ``server.search(...)`` directly (as most tests below do) exercises the
    Python function, not what a client actually receives: an exception raised inside
    a tool body that reaches this session is what a real client like Claude Desktop
    or LM Studio would see, including the wrapping the SDK applies to it.
    """
    async with InMemoryTransport(server.mcp) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


def _call_tool(name: str, arguments: dict):
    async def go():
        async with _client_session() as session:
            return await session.call_tool(name, arguments)

    return asyncio.run(go())


def test_handshake_announces_tools_with_schemas():
    tools = _list_tools()
    assert len(tools) >= 1
    names = {t.name for t in tools}
    assert "search" in names
    for tool in tools:
        assert tool.input_schema.get("properties") is not None


def test_rejects_top_k_below_range():
    with pytest.raises(ValueError, match="top_k"):
        server.search("erro de login", top_k=0)


def test_rejects_top_k_above_range():
    with pytest.raises(ValueError, match="top_k"):
        server.search("erro de login", top_k=51)


def test_rejects_empty_query():
    with pytest.raises(ValueError, match="query"):
        server.search("   ")


def test_rejects_invalid_mode():
    with pytest.raises(ValueError, match="mode"):
        server.search("erro de login", mode="fulltext")


def test_rejects_query_over_2000_chars():
    with pytest.raises(ValueError, match="2000"):
        server.search("a" * 2001)


def test_search_validation_errors_are_specific_over_the_real_mcp_protocol():
    """A direct call to server.search() proves the function's own logic; a real MCP
    client only sees what survives the SDK's argument validation and its wrapping of
    exceptions raised from inside a tool body - only the ``Query``/``TopK`` schema
    constraints, not the manual checks alone, keep the specific reason on that path."""
    top_k_result = _call_tool("search", {"query": "erro de login", "top_k": 51})
    assert top_k_result.is_error is True
    assert "top_k" in top_k_result.content[0].text

    query_result = _call_tool("search", {"query": "   "})
    assert query_result.is_error is True
    assert "query" in query_result.content[0].text

    long_query_result = _call_tool("search", {"query": "a" * 2001})
    assert long_query_result.is_error is True
    assert "2000" in long_query_result.content[0].text


def test_no_tool_accepts_scope_parameter():
    forbidden = {"tenant", "tenant_id", "scope", "scope_id"}
    for tool in _list_tools():
        params = set(tool.input_schema.get("properties", {}))
        leaked = params & forbidden
        assert not leaked, f"{tool.name} exposes a scope parameter: {leaked}"


def test_missing_tenant_env_exits_before_announcing_tools(monkeypatch):
    monkeypatch.delenv("RAG_TENANT_ID", raising=False)
    monkeypatch.setattr(server, "_active_tenant", None)

    def _fail_if_called(*args, **kwargs):
        raise AssertionError("mcp.run must not be reached when the tenant is unresolved")

    monkeypatch.setattr(server.mcp, "run", _fail_if_called)

    with pytest.raises(SystemExit):
        server.main()


def test_db_unavailable_returns_error_and_server_stays_alive():
    def _broken_connection(tenant_id):
        raise psycopg.OperationalError("connection to server failed: simulated outage")

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(server.db, "scoped_connection", _broken_connection)
        # search() wraps the connection failure as ToolError so a real MCP client sees
        # "database is unreachable", not the generic "Error executing tool search" a
        # bare psycopg.OperationalError would produce once it crosses the SDK boundary.
        with pytest.raises(ToolError, match="unreachable"):
            server.search("erro de login")

        tool_result = _call_tool("search", {"query": "erro de login"})
        assert tool_result.is_error is True
        assert "unreachable" in tool_result.content[0].text

    # RAG-22: a connection failure on one call must not take the process down - the
    # next call, once the database is reachable again, still succeeds, and so does a
    # fresh handshake against the same running server.
    result = server.search("erro de login")
    assert isinstance(result, list)
    assert {t.name for t in _list_tools()} >= {"search", "get_document"}
