"""RAG-15, RAG-17: rag.db as the single door to the database."""

import pytest

import rag.db as db


def _defined_in(obj, module_name: str) -> bool:
    return getattr(obj, "__module__", None) == module_name


def test_scoped_connection_applies_tenant_scope_and_uses_rag_app_role():
    with db.scoped_connection("meridian") as conn:
        tenant = conn.execute("SELECT current_setting('app.tenant_id')").fetchone()[0]
        role = conn.execute("SELECT current_user").fetchone()[0]
        assert tenant == "meridian"
        assert role == "rag_app"


def test_resolve_tenant_from_env_exits_when_missing(monkeypatch):
    monkeypatch.delenv("RAG_TENANT_ID", raising=False)
    with pytest.raises(SystemExit) as exc_info:
        db.resolve_tenant_from_env()
    assert "RAG_TENANT_ID" in str(exc_info.value)


def test_resolve_tenant_from_env_exits_when_empty(monkeypatch):
    monkeypatch.setenv("RAG_TENANT_ID", "   ")
    with pytest.raises(SystemExit) as exc_info:
        db.resolve_tenant_from_env()
    assert "RAG_TENANT_ID" in str(exc_info.value)


def test_resolve_tenant_from_env_exits_when_unknown(monkeypatch):
    monkeypatch.setenv("RAG_TENANT_ID", "ghost-tenant")
    with pytest.raises(SystemExit) as exc_info:
        db.resolve_tenant_from_env()
    assert "ghost-tenant" in str(exc_info.value)


def test_module_exports_no_other_connection_constructor():
    assert set(db.__all__) == {"scoped_connection", "resolve_tenant_from_env"}
    public_callables = {
        name
        for name, obj in vars(db).items()
        if callable(obj) and not name.startswith("_") and _defined_in(obj, "rag.db")
    }
    assert public_callables == {"scoped_connection", "resolve_tenant_from_env"}
