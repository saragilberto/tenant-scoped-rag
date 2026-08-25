import pytest

from rag.context_cli import build_parser


class TestBuildParser:
    def test_defaults(self):
        args = build_parser().parse_args(["pergunta"])
        assert args.question == "pergunta"
        assert args.mode == "hybrid"
        assert args.top_k == 5
        assert args.profile == "P512"
        assert args.open is False

    def test_rejects_mode_outside_closed_set(self):
        with pytest.raises(SystemExit):
            build_parser().parse_args(["pergunta", "--mode", "invalid"])

    def test_rejects_profile_outside_closed_set(self):
        with pytest.raises(SystemExit):
            build_parser().parse_args(["pergunta", "--profile", "invalid"])

    def test_accepts_explicit_values(self):
        args = build_parser().parse_args(
            ["pergunta", "--mode", "lexical", "--top-k", "3", "--profile", "P1024", "--open"]
        )
        assert args.mode == "lexical"
        assert args.top_k == 3
        assert args.profile == "P1024"
        assert args.open is True
