"""RAG-29, RAG-31: the evaluation harness runs the 60 scoped golden-set questions
deterministically, without any external service call."""

import ast
from pathlib import Path

from eval.harness import GOLDEN_DIR, run
from rag.chunking import ChunkProfile

REPO_ROOT = Path(__file__).resolve().parents[2]
_FORBIDDEN_IMPORTS = {"requests", "httpx", "urllib", "openai", "anthropic"}


def test_harness_runs_all_scoped_questions_for_each_tenant():
    meridian = run(GOLDEN_DIR / "meridian.yaml", "meridian", "hybrid", ChunkProfile.P512)
    halcyon = run(GOLDEN_DIR / "halcyon.yaml", "halcyon", "hybrid", ChunkProfile.P512)

    assert len(meridian.per_question) == 30
    assert len(halcyon.per_question) == 30
    assert meridian.tenant_id == "meridian"
    assert halcyon.tenant_id == "halcyon"


def test_harness_computes_all_four_metrics_in_range():
    result = run(GOLDEN_DIR / "meridian.yaml", "meridian", "hybrid", ChunkProfile.P512)

    assert 0.0 <= result.recall_at_5 <= 1.0
    assert 0.0 <= result.precision_at_5 <= 1.0
    assert 0.0 <= result.mrr <= 1.0
    assert 0.0 <= result.ndcg_at_10 <= 1.0
    for question_result in result.per_question:
        assert 0.0 <= question_result.recall_at_5 <= 1.0
        assert 0.0 <= question_result.ndcg_at_10 <= 1.0


def test_harness_is_deterministic_across_two_runs():
    first = run(GOLDEN_DIR / "meridian.yaml", "meridian", "semantic", ChunkProfile.P512)
    second = run(GOLDEN_DIR / "meridian.yaml", "meridian", "semantic", ChunkProfile.P512)

    assert first.recall_at_5 == second.recall_at_5
    assert first.precision_at_5 == second.precision_at_5
    assert first.mrr == second.mrr
    assert first.ndcg_at_10 == second.ndcg_at_10
    assert [r.id for r in first.per_question] == [r.id for r in second.per_question]
    assert [r.recall_at_5 for r in first.per_question] == [
        r.recall_at_5 for r in second.per_question
    ]


def test_harness_module_imports_no_external_service_client():
    source = (REPO_ROOT / "src" / "eval" / "harness.py").read_text()
    tree = ast.parse(source)
    imported_roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])

    leaked = imported_roots & _FORBIDDEN_IMPORTS
    assert not leaked, f"harness.py imports an external-service client: {leaked}"
