"""RAG-30: the ablation study - 3 search modes x 2 rerank settings x 2 chunk profiles,
each cell averaged over both tenants' golden sets, emitted as a markdown table.

A cell that cannot be measured (e.g. the rerank model can't be loaded) is reported as
such in its own row rather than silently dropped - an omitted row reads as "not part of
the study", which is a different and false claim than "we tried and it failed".
"""

import statistics
from dataclasses import dataclass

from eval import harness
from rag.chunking import ChunkProfile

__all__ = ["AblationRow", "run_matrix"]

_MODES = ("semantic", "lexical", "hybrid")
_PROFILES = (ChunkProfile.P512, ChunkProfile.P1024)
_RERANK_OPTIONS = (False, True)
_TENANTS = ("meridian", "halcyon")


@dataclass(frozen=True)
class AblationRow:
    mode: str
    profile: str
    rerank: bool
    recall_at_5: float | None
    precision_at_5: float | None
    mrr: float | None
    ndcg_at_10: float | None
    note: str | None = None


def _measure(mode: str, profile: ChunkProfile, rerank: bool) -> AblationRow:
    try:
        results = [
            harness.run(harness.GOLDEN_DIR / f"{tenant}.yaml", tenant, mode, profile, rerank=rerank)
            for tenant in _TENANTS
        ]
    except Exception as exc:
        return AblationRow(
            mode, profile.value, rerank, None, None, None, None, note=f"not measured: {exc}"
        )

    return AblationRow(
        mode=mode,
        profile=profile.value,
        rerank=rerank,
        recall_at_5=statistics.fmean(r.recall_at_5 for r in results),
        precision_at_5=statistics.fmean(r.precision_at_5 for r in results),
        mrr=statistics.fmean(r.mrr for r in results),
        ndcg_at_10=statistics.fmean(r.ndcg_at_10 for r in results),
    )


def _format_cell(value: float | None) -> str:
    return f"{value:.3f}" if value is not None else "-"


def _to_markdown(rows: list[AblationRow]) -> str:
    lines = [
        "| Mode | Chunk profile | Rerank | recall@5 | precision@5 | MRR | nDCG@10 | Note |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        note = row.note or ""
        lines.append(
            f"| {row.mode} | {row.profile} | {row.rerank} | {_format_cell(row.recall_at_5)} | "
            f"{_format_cell(row.precision_at_5)} | {_format_cell(row.mrr)} | "
            f"{_format_cell(row.ndcg_at_10)} | {note} |"
        )
    return "\n".join(lines) + "\n"


def run_matrix() -> str:
    rows = [
        _measure(mode, profile, rerank)
        for mode in _MODES
        for profile in _PROFILES
        for rerank in _RERANK_OPTIONS
    ]
    return _to_markdown(rows)
