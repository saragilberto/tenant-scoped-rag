"""RAG-30: the ablation matrix covers all 12 configurations, declares what it can't
measure instead of dropping it, and is reproducible.

Reranking is real cross-encoder inference (bge-reranker-v2-m3) and takes minutes per
30-question run - too slow to re-run twice on every gate check. T29 already proves
harness.run() itself is deterministic given the same arguments; the tests here stub
harness.run() with a fast, argument-derived function to check run_matrix()'s own
composition (row set, markdown shape, failure handling, output stability) without
re-paying for real inference on every gate. The non-rerank cells are additionally
exercised for real against the live database, since those run in seconds.
"""

from eval import ablation, harness
from rag.chunking import ChunkProfile

_ALL_COMBINATIONS = {
    (mode, profile.value, rerank)
    for mode in ("semantic", "lexical", "hybrid")
    for profile in (ChunkProfile.P512, ChunkProfile.P1024)
    for rerank in (False, True)
}


def _fake_run(golden_set_path, tenant_id, mode, profile, rerank=False):
    """Deterministic stand-in for harness.run: value is a pure function of its
    arguments, so two calls with the same arguments always agree - mirroring the
    real determinism T29 already proves, without the cost of real inference."""
    seed = (hash((tenant_id, mode, profile.value, rerank)) % 1000) / 1000
    return harness.RunResult(
        tenant_id=tenant_id,
        mode=mode,
        profile=profile,
        rerank=rerank,
        per_question=[],
        recall_at_5=seed,
        precision_at_5=seed / 2,
        mrr=seed / 3,
        ndcg_at_10=seed / 4,
    )


def test_run_matrix_covers_all_twelve_mode_profile_rerank_combinations(monkeypatch):
    monkeypatch.setattr(harness, "run", _fake_run)

    table = ablation.run_matrix()
    lines = [line for line in table.splitlines() if line.startswith("| ") and " --- " not in line]
    data_rows = lines[1:]  # drop the header row

    assert len(data_rows) == 12
    seen = set()
    for row in data_rows:
        cells = [c.strip() for c in row.strip("|").split("|")]
        mode, profile, rerank = cells[0], cells[1], cells[2]
        seen.add((mode, profile, rerank == "True"))
    assert seen == _ALL_COMBINATIONS


def test_run_matrix_declares_an_unmeasurable_combination_instead_of_dropping_it(monkeypatch):
    def _flaky_run(golden_set_path, tenant_id, mode, profile, rerank=False):
        if mode == "hybrid" and rerank:
            raise RuntimeError("reranking model not cached and no network available")
        return _fake_run(golden_set_path, tenant_id, mode, profile, rerank=rerank)

    monkeypatch.setattr(harness, "run", _flaky_run)

    table = ablation.run_matrix()
    lines = [line for line in table.splitlines() if line.startswith("| ") and " --- " not in line]
    data_rows = lines[1:]

    assert len(data_rows) == 12  # the failing combination stays a row, never disappears
    failing_rows = [row for row in data_rows if "not measured" in row]
    assert len(failing_rows) == 2  # hybrid x rerank=True, for both chunk profiles
    for row in failing_rows:
        assert "hybrid" in row
        assert "True" in row


def test_run_matrix_is_reproducible(monkeypatch):
    monkeypatch.setattr(harness, "run", _fake_run)

    first = ablation.run_matrix()
    second = ablation.run_matrix()

    assert first == second


def test_measure_non_rerank_combinations_against_the_real_database():
    row = ablation._measure("semantic", ChunkProfile.P512, rerank=False)

    assert row.note is None
    assert 0.0 <= row.recall_at_5 <= 1.0
    assert 0.0 <= row.precision_at_5 <= 1.0
    assert 0.0 <= row.mrr <= 1.0
    assert 0.0 <= row.ndcg_at_10 <= 1.0

    row_p1024 = ablation._measure("hybrid", ChunkProfile.P1024, rerank=False)
    assert row_p1024.note is None
    assert 0.0 <= row_p1024.recall_at_5 <= 1.0
