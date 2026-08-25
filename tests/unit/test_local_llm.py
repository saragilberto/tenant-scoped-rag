import json
from urllib.error import URLError

import pytest

from rag import local_llm


class _FakeResponse:
    def __init__(self, payload: dict):
        self._body = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def read(self):
        return self._body


class TestResolveBaseUrl:
    def test_returns_default_when_env_unset(self, monkeypatch):
        monkeypatch.delenv("LOCAL_LLM_BASE_URL", raising=False)
        assert local_llm.resolve_base_url() == "http://127.0.0.1:8080"

    def test_returns_custom_valid_url_from_env(self, monkeypatch):
        monkeypatch.setenv("LOCAL_LLM_BASE_URL", "https://192.168.1.5:9000")
        assert local_llm.resolve_base_url() == "https://192.168.1.5:9000"

    def test_rejects_non_http_scheme(self, monkeypatch):
        monkeypatch.setenv("LOCAL_LLM_BASE_URL", "ftp://example.com")
        with pytest.raises(ValueError, match="ftp://example.com"):
            local_llm.resolve_base_url()


class TestCheckHealth:
    def test_healthy_with_context_window(self, monkeypatch):
        payload = {"data": [{"id": "qwen", "meta": {"n_ctx": 16384}}]}
        monkeypatch.setattr(local_llm, "urlopen", lambda url, timeout: _FakeResponse(payload))

        status = local_llm.check_health("http://127.0.0.1:8080")

        assert status == local_llm.HealthStatus(reachable=True, detail="ok", context_window=16384)

    def test_healthy_without_context_window(self, monkeypatch):
        payload = {"data": [{"id": "qwen"}]}
        monkeypatch.setattr(local_llm, "urlopen", lambda url, timeout: _FakeResponse(payload))

        status = local_llm.check_health("http://127.0.0.1:8080")

        assert status.reachable is True
        assert status.context_window is None

    def test_unreachable_returns_status_without_raising(self, monkeypatch):
        def raise_url_error(url, timeout):
            raise URLError("connection refused")

        monkeypatch.setattr(local_llm, "urlopen", raise_url_error)

        status = local_llm.check_health("http://127.0.0.1:8080")

        assert status.reachable is False
        assert status.context_window is None

    def test_timeout_returns_status_without_raising(self, monkeypatch):
        def raise_timeout(url, timeout):
            raise TimeoutError("timed out")

        monkeypatch.setattr(local_llm, "urlopen", raise_timeout)

        status = local_llm.check_health("http://127.0.0.1:8080", timeout=2.0)

        assert status.reachable is False
        assert status.context_window is None

    def test_malformed_response_returns_status_without_raising(self, monkeypatch):
        class _BadResponse(_FakeResponse):
            def __init__(self):
                self._body = b"not json"

        monkeypatch.setattr(local_llm, "urlopen", lambda url, timeout: _BadResponse())

        status = local_llm.check_health("http://127.0.0.1:8080")

        assert status.reachable is False
        assert status.context_window is None


class TestOpenBrowser:
    def test_returns_true_when_browser_opens(self, monkeypatch):
        monkeypatch.setattr(local_llm.webbrowser, "open", lambda url: True)
        assert local_llm.open_browser("http://127.0.0.1:8080") is True

    def test_returns_false_when_browser_open_fails(self, monkeypatch):
        def raise_error(url):
            raise RuntimeError("no display")

        monkeypatch.setattr(local_llm.webbrowser, "open", raise_error)
        assert local_llm.open_browser("http://127.0.0.1:8080") is False
