import pytest

from rag import query
from rag.chunking import ChunkProfile


class TestValidateQuery:
    def test_rejects_empty_string(self):
        with pytest.raises(ValueError, match="query must not be empty"):
            query.validate_query("")

    def test_rejects_whitespace_only(self):
        with pytest.raises(ValueError, match="query must not be empty"):
            query.validate_query("   \t\n  ")

    def test_accepts_query_at_max_length(self):
        text = "a" * query.MAX_QUERY_CHARS
        assert query.validate_query(text) == text

    def test_rejects_query_above_max_length(self):
        text = "a" * (query.MAX_QUERY_CHARS + 1)
        with pytest.raises(ValueError, match=str(query.MAX_QUERY_CHARS)):
            query.validate_query(text)


class TestValidateTopK:
    def test_rejects_below_min(self):
        with pytest.raises(ValueError, match="top_k"):
            query.validate_top_k(query.MIN_TOP_K - 1)

    def test_rejects_above_max(self):
        with pytest.raises(ValueError, match="top_k"):
            query.validate_top_k(query.MAX_TOP_K + 1)

    def test_accepts_lower_boundary(self):
        assert query.validate_top_k(query.MIN_TOP_K) == query.MIN_TOP_K

    def test_accepts_upper_boundary(self):
        assert query.validate_top_k(query.MAX_TOP_K) == query.MAX_TOP_K


class TestValidateMode:
    def test_rejects_unknown_mode(self):
        with pytest.raises(ValueError, match="mode"):
            query.validate_mode("unknown")

    @pytest.mark.parametrize("mode", ["semantic", "lexical", "hybrid"])
    def test_accepts_known_modes(self, mode):
        assert query.validate_mode(mode) == mode


class TestRunSearch:
    @pytest.mark.parametrize("mode", ["semantic", "lexical", "hybrid"])
    def test_dispatches_to_matching_module(self, monkeypatch, mode):
        calls = []
        for name, module in query.SEARCH_MODULES.items():
            monkeypatch.setattr(
                module,
                "search",
                lambda conn, q, top_k, profile, name=name: (
                    calls.append((name, conn, q, top_k, profile)) or []
                ),
            )

        conn = object()
        result = query.run_search(conn, "pergunta", mode, 5, ChunkProfile.P512)

        assert result == []
        assert calls == [(mode, conn, "pergunta", 5, ChunkProfile.P512)]
