import subprocess

import pytest

from rag import context_block
from rag.retrieval import Candidate


def _candidate(chunk_id, document_id, text, position, score=1.0):
    return Candidate(
        chunk_id=chunk_id, document_id=document_id, text=text, score=score, position=position
    )


class TestBuildBlock:
    def test_includes_question_and_single_candidate_cited_by_document_and_position(self):
        candidates = [_candidate("c1", "doc-1", "conteúdo do chunk", 0)]

        block = context_block.build_block("qual é a resposta?", candidates)

        assert "qual é a resposta?" in block
        assert "doc-1" in block
        assert "0" in block
        assert "conteúdo do chunk" in block

    def test_includes_every_candidate_when_multiple(self):
        candidates = [
            _candidate("c1", "doc-1", "primeiro chunk", 0),
            _candidate("c2", "doc-2", "segundo chunk", 3),
        ]

        block = context_block.build_block("pergunta", candidates)

        assert "primeiro chunk" in block
        assert "segundo chunk" in block
        assert "doc-1" in block
        assert "doc-2" in block

    def test_lists_both_chunks_from_same_document_without_deduplicating(self):
        candidates = [
            _candidate("c1", "doc-1", "primeiro chunk", 0),
            _candidate("c2", "doc-1", "segundo chunk", 1),
        ]

        block = context_block.build_block("pergunta", candidates)

        assert "primeiro chunk" in block
        assert "segundo chunk" in block
        assert block.count("doc-1") == 2

    def test_includes_grounding_instruction(self):
        block = context_block.build_block("pergunta", [_candidate("c1", "doc-1", "texto", 0)])
        assert "somente com base no conteúdo" in block


class TestEstimateTokens:
    def test_grows_with_text_length(self):
        short = context_block.estimate_tokens("a" * 40)
        long = context_block.estimate_tokens("a" * 400)
        assert long > short

    def test_deterministic_for_same_input(self):
        text = "mesmo texto repetido" * 5
        assert context_block.estimate_tokens(text) == context_block.estimate_tokens(text)


class TestCopyToClipboard:
    def test_returns_false_when_pbcopy_absent(self, monkeypatch):
        monkeypatch.setattr(context_block.shutil, "which", lambda name: None)
        assert context_block.copy_to_clipboard("texto") is False

    def test_returns_true_when_pbcopy_succeeds(self, monkeypatch):
        monkeypatch.setattr(context_block.shutil, "which", lambda name: "/usr/bin/pbcopy")
        monkeypatch.setattr(context_block.subprocess, "run", lambda *a, **k: None)
        assert context_block.copy_to_clipboard("texto") is True

    def test_returns_false_when_subprocess_fails(self, monkeypatch):
        monkeypatch.setattr(context_block.shutil, "which", lambda name: "/usr/bin/pbcopy")

        def raise_error(*args, **kwargs):
            raise subprocess.CalledProcessError(1, ["pbcopy"])

        monkeypatch.setattr(context_block.subprocess, "run", raise_error)
        assert context_block.copy_to_clipboard("texto") is False
