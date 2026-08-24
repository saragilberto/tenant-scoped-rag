"""RAG-11, RAG-12, RAG-13, RAG-16, RAG-17, RAG-21, RAG-22: the MCP server bootstrap
and the search tool's validation contract."""

import asyncio

import psycopg
import pytest

from rag import server


@pytest.fixture(autouse=True)
def _active_tenant(monkeypatch):
    monkeypatch.setattr(server, "_active_tenant", "meridian")


def _list_tools():
    return asyncio.run(server.mcp.list_tools())


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
        with pytest.raises(psycopg.OperationalError, match="simulated outage"):
            server.search("erro de login")

    # RAG-22: a connection failure on one call must not take the process down - the
    # next call, once the database is reachable again, still succeeds.
    result = server.search("erro de login")
    assert isinstance(result, list)
