"""End-to-end coverage for the `rag-context` command (LLM-01..LLM-10, LLM-12/13)."""

import subprocess

import psycopg
import pytest

from rag import context_cli
from rag.chunking import ChunkProfile
from rag.local_llm import HealthStatus
from rag.retrieval import Candidate

_MERIDIAN_QUESTION = (
    "Why would someone keep seeing a workspace-not-found error after their company rebranded?"
)


def _set_argv(monkeypatch, question, **flags):
    argv = ["rag-context", question]
    for name, value in flags.items():
        if value is True:
            argv.append(f"--{name.replace('_', '-')}")
        elif value is not None:
            argv.extend([f"--{name.replace('_', '-')}", str(value)])
    monkeypatch.setattr("sys.argv", argv)


def _fail_if_called(*args, **kwargs):
    raise AssertionError("must not be reached")


@pytest.fixture
def unreachable_local_llm(monkeypatch):
    """The local LLM is not running in this test environment - health checks must
    never depend on a real llamafile process being up."""
    monkeypatch.setattr(
        context_cli.local_llm,
        "check_health",
        lambda base_url, timeout=2.0: HealthStatus(
            reachable=False, detail="connection refused", context_window=None
        ),
    )


def test_happy_path_prints_block_and_copies_to_clipboard(monkeypatch, capsys):
    monkeypatch.setenv("RAG_TENANT_ID", "meridian")
    monkeypatch.setattr(
        context_cli.local_llm,
        "check_health",
        lambda base_url, timeout=2.0: HealthStatus(
            reachable=False, detail="connection refused", context_window=None
        ),
    )
    _set_argv(monkeypatch, _MERIDIAN_QUESTION)

    context_cli.main()

    out = capsys.readouterr().out
    assert _MERIDIAN_QUESTION in out
    assert "login-error" in out or "workspace" in out.lower()

    clipboard = subprocess.run(["pbpaste"], capture_output=True, text=True, check=True).stdout
    assert clipboard.strip() == out.strip()


@pytest.mark.parametrize("tenant_env", [{}, {"RAG_TENANT_ID": "not-a-real-tenant"}])
def test_missing_or_unknown_tenant_exits_before_health_check_or_retrieval(monkeypatch, tenant_env):
    monkeypatch.delenv("RAG_TENANT_ID", raising=False)
    for key, value in tenant_env.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(context_cli.local_llm, "check_health", _fail_if_called)
    monkeypatch.setattr(context_cli.db, "scoped_connection", _fail_if_called)
    _set_argv(monkeypatch, "qualquer pergunta")

    with pytest.raises(SystemExit) as exc_info:
        context_cli.main()

    assert "RAG_TENANT_ID" in str(exc_info.value)


def test_rejects_empty_question_before_touching_database(monkeypatch):
    monkeypatch.setenv("RAG_TENANT_ID", "meridian")
    monkeypatch.setattr(context_cli.db, "scoped_connection", _fail_if_called)
    _set_argv(monkeypatch, "   ")

    with pytest.raises(SystemExit, match="query"):
        context_cli.main()


def test_rejects_question_above_char_limit_before_touching_database(monkeypatch):
    monkeypatch.setenv("RAG_TENANT_ID", "meridian")
    monkeypatch.setattr(context_cli.db, "scoped_connection", _fail_if_called)
    _set_argv(monkeypatch, "a" * (context_cli.query.MAX_QUERY_CHARS + 1))

    with pytest.raises(SystemExit, match="query"):
        context_cli.main()


def test_local_llm_unreachable_warns_but_still_delivers_block(
    monkeypatch, capsys, unreachable_local_llm
):
    monkeypatch.setenv("RAG_TENANT_ID", "meridian")
    candidate = Candidate(
        chunk_id="c1", document_id="doc-1", text="conteúdo do chunk", score=1.0, position=1
    )
    monkeypatch.setattr(
        context_cli.query, "run_search", lambda conn, q, mode, top_k, profile: [candidate]
    )
    _set_argv(monkeypatch, "pergunta qualquer")

    context_cli.main()

    captured = capsys.readouterr()
    assert "127.0.0.1:8080" in captured.err
    assert "pergunta qualquer" in captured.out
    assert "conteúdo do chunk" in captured.out


def test_zero_chunks_does_not_copy_or_print_block(monkeypatch, capsys, unreachable_local_llm):
    monkeypatch.setenv("RAG_TENANT_ID", "meridian")
    monkeypatch.setattr(context_cli.query, "run_search", lambda conn, q, mode, top_k, profile: [])
    monkeypatch.setattr(context_cli.context_block, "copy_to_clipboard", _fail_if_called)
    _set_argv(monkeypatch, "pergunta sem resultado")

    context_cli.main()

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "no context found" in captured.err


def test_database_unavailable_exits_with_clear_message(monkeypatch, unreachable_local_llm):
    monkeypatch.setenv("RAG_TENANT_ID", "meridian")

    def _broken_connection(tenant_id):
        raise psycopg.OperationalError("connection to server failed: simulated outage")

    monkeypatch.setattr(context_cli.db, "scoped_connection", _broken_connection)
    _set_argv(monkeypatch, "pergunta qualquer")

    with pytest.raises(SystemExit, match="unreachable"):
        context_cli.main()


def test_pbcopy_absent_does_not_fail_command(monkeypatch, capsys, unreachable_local_llm):
    monkeypatch.setenv("RAG_TENANT_ID", "meridian")
    candidate = Candidate(
        chunk_id="c1", document_id="doc-1", text="conteúdo do chunk", score=1.0, position=1
    )
    monkeypatch.setattr(
        context_cli.query, "run_search", lambda conn, q, mode, top_k, profile: [candidate]
    )
    monkeypatch.setattr(context_cli.context_block, "copy_to_clipboard", lambda text: False)
    _set_argv(monkeypatch, "pergunta qualquer")

    context_cli.main()

    captured = capsys.readouterr()
    assert "pergunta qualquer" in captured.out
    assert "could not copy" in captured.err


def test_explicit_mode_top_k_and_profile_reach_run_search(monkeypatch, unreachable_local_llm):
    monkeypatch.setenv("RAG_TENANT_ID", "meridian")
    calls = []

    def _fake_run_search(conn, q, mode, top_k, profile):
        calls.append((mode, top_k, profile))
        return [Candidate(chunk_id="c1", document_id="doc-1", text="texto", score=1.0, position=1)]

    monkeypatch.setattr(context_cli.query, "run_search", _fake_run_search)
    _set_argv(monkeypatch, "pergunta", mode="lexical", top_k=3, profile="P1024")

    context_cli.main()

    assert calls == [("lexical", 3, ChunkProfile.P1024)]


def test_open_flag_opens_browser_after_copying_to_clipboard(monkeypatch, unreachable_local_llm):
    monkeypatch.setenv("RAG_TENANT_ID", "meridian")
    candidate = Candidate(
        chunk_id="c1", document_id="doc-1", text="conteúdo do chunk", score=1.0, position=1
    )
    monkeypatch.setattr(
        context_cli.query, "run_search", lambda conn, q, mode, top_k, profile: [candidate]
    )
    order = []
    monkeypatch.setattr(
        context_cli.context_block,
        "copy_to_clipboard",
        lambda text: order.append("copy") or True,
    )
    opened = []
    monkeypatch.setattr(
        context_cli.local_llm,
        "open_browser",
        lambda base_url: order.append("open") or opened.append(base_url) or True,
    )
    _set_argv(monkeypatch, "pergunta qualquer", open=True)

    context_cli.main()

    assert opened == ["http://127.0.0.1:8080"]
    assert order == ["copy", "open"]


def test_open_flag_warns_but_continues_when_browser_fails(
    monkeypatch, capsys, unreachable_local_llm
):
    monkeypatch.setenv("RAG_TENANT_ID", "meridian")
    candidate = Candidate(
        chunk_id="c1", document_id="doc-1", text="conteúdo do chunk", score=1.0, position=1
    )
    monkeypatch.setattr(
        context_cli.query, "run_search", lambda conn, q, mode, top_k, profile: [candidate]
    )
    monkeypatch.setattr(context_cli.local_llm, "open_browser", lambda base_url: False)
    _set_argv(monkeypatch, "pergunta qualquer", open=True)

    context_cli.main()

    captured = capsys.readouterr()
    assert "pergunta qualquer" in captured.out
    assert "could not open the browser" in captured.err


def test_warns_when_block_exceeds_local_llm_context_window(monkeypatch, capsys):
    monkeypatch.setenv("RAG_TENANT_ID", "meridian")
    monkeypatch.setattr(
        context_cli.local_llm,
        "check_health",
        lambda base_url, timeout=2.0: HealthStatus(reachable=True, detail="ok", context_window=10),
    )
    candidate = Candidate(
        chunk_id="c1", document_id="doc-1", text="a" * 1000, score=1.0, position=1
    )
    monkeypatch.setattr(
        context_cli.query, "run_search", lambda conn, q, mode, top_k, profile: [candidate]
    )
    _set_argv(monkeypatch, "pergunta qualquer")

    context_cli.main()

    captured = capsys.readouterr()
    assert "warning: context block is" in captured.err
    assert "10" in captured.err


def test_no_warning_when_block_fits_local_llm_context_window(monkeypatch, capsys):
    monkeypatch.setenv("RAG_TENANT_ID", "meridian")
    monkeypatch.setattr(
        context_cli.local_llm,
        "check_health",
        lambda base_url, timeout=2.0: HealthStatus(
            reachable=True, detail="ok", context_window=16384
        ),
    )
    candidate = Candidate(
        chunk_id="c1", document_id="doc-1", text="texto curto", score=1.0, position=1
    )
    monkeypatch.setattr(
        context_cli.query, "run_search", lambda conn, q, mode, top_k, profile: [candidate]
    )
    _set_argv(monkeypatch, "pergunta qualquer")

    context_cli.main()

    captured = capsys.readouterr()
    assert "context block is" not in captured.err


def test_rejects_top_k_outside_range_before_touching_database(monkeypatch):
    monkeypatch.setenv("RAG_TENANT_ID", "meridian")
    monkeypatch.setattr(context_cli.db, "scoped_connection", _fail_if_called)
    _set_argv(monkeypatch, "pergunta qualquer", top_k=51)

    with pytest.raises(SystemExit, match="top_k"):
        context_cli.main()


def test_rejects_invalid_local_llm_base_url_before_health_check(monkeypatch):
    monkeypatch.setenv("RAG_TENANT_ID", "meridian")
    monkeypatch.setenv("LOCAL_LLM_BASE_URL", "ftp://example.com")
    monkeypatch.setattr(context_cli.local_llm, "check_health", _fail_if_called)
    monkeypatch.setattr(context_cli.db, "scoped_connection", _fail_if_called)
    _set_argv(monkeypatch, "pergunta qualquer")

    with pytest.raises(SystemExit, match="ftp://example.com"):
        context_cli.main()
