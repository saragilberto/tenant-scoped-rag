"""RAG-29, RAG-31: run a tenant's golden set through a retrieval configuration and
compute recall@5, precision@5, MRR and nDCG@10 - deterministically, with every call
scoped to the question's own tenant (never the opposite identity RAG-18/T26 exercises).
"""

import statistics
from dataclasses import dataclass
from pathlib import Path

import psycopg
import yaml

from eval.metrics import mrr as mrr_metric
from eval.metrics import ndcg_at_k, precision_at_k, recall_at_k
from rag.chunking import ChunkProfile
from rag.db import scoped_connection
from rag.retrieval import hybrid, lexical, semantic
from rag.retrieval.rerank import apply as apply_rerank

__all__ = ["QuestionResult", "RunResult", "run", "main"]

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLDEN_DIR = REPO_ROOT / "eval" / "golden"

_SEARCH_MODULES = {"semantic": semantic, "lexical": lexical, "hybrid": hybrid}
_POOL_SIZE = 10
_RECALL_K = 5
_NDCG_K = 10


@dataclass(frozen=True)
class QuestionResult:
    id: str
    recall_at_5: float
    precision_at_5: float
    reciprocal_rank: float
    ndcg_at_10: float


@dataclass(frozen=True)
class RunResult:
    tenant_id: str
    mode: str
    profile: ChunkProfile
    rerank: bool
    per_question: list[QuestionResult]
    recall_at_5: float
    precision_at_5: float
    mrr: float
    ndcg_at_10: float


def _document_source_paths(conn: psycopg.Connection) -> dict[str, str]:
    rows = conn.execute("SELECT id, source_path FROM documents").fetchall()
    return {str(row[0]): row[1] for row in rows}


def _ranked_unique_documents(candidates, doc_paths: dict[str, str]) -> list[str]:
    """Collapse ranked chunk candidates to their documents, one entry each, keeping
    the rank of a document's best-placed chunk. A metric over ids assumes each
    position holds a distinct item; several chunks from the same document would
    otherwise inflate recall/precision past 1.0 by counting one document as many."""
    seen: set[str] = set()
    ranked: list[str] = []
    for candidate in candidates:
        path = doc_paths[candidate.document_id]
        if path not in seen:
            seen.add(path)
            ranked.append(path)
    return ranked


def run(
    golden_set_path: Path,
    tenant_id: str,
    mode: str,
    profile: ChunkProfile,
    rerank: bool = False,
) -> RunResult:
    questions = yaml.safe_load(golden_set_path.read_text())
    search = _SEARCH_MODULES[mode].search

    per_question: list[QuestionResult] = []
    with scoped_connection(tenant_id) as conn:
        doc_paths = _document_source_paths(conn)
        for question in questions:
            candidates = search(conn, question["question"], _POOL_SIZE, profile)
            if rerank:
                candidates = apply_rerank(question["question"], candidates)
            retrieved = _ranked_unique_documents(candidates, doc_paths)
            relevant = question["relevant_docs"]
            per_question.append(
                QuestionResult(
                    id=question["id"],
                    recall_at_5=recall_at_k(retrieved, relevant, _RECALL_K),
                    precision_at_5=precision_at_k(retrieved, relevant, _RECALL_K),
                    reciprocal_rank=mrr_metric(retrieved, relevant),
                    ndcg_at_10=ndcg_at_k(retrieved, relevant, _NDCG_K),
                )
            )

    return RunResult(
        tenant_id=tenant_id,
        mode=mode,
        profile=profile,
        rerank=rerank,
        per_question=per_question,
        recall_at_5=statistics.fmean(r.recall_at_5 for r in per_question),
        precision_at_5=statistics.fmean(r.precision_at_5 for r in per_question),
        mrr=statistics.fmean(r.reciprocal_rank for r in per_question),
        ndcg_at_10=statistics.fmean(r.ndcg_at_10 for r in per_question),
    )


def main() -> None:
    for tenant_id in ("meridian", "halcyon"):
        result = run(
            GOLDEN_DIR / f"{tenant_id}.yaml",
            tenant_id,
            mode="hybrid",
            profile=ChunkProfile.P512,
        )
        print(
            f"{tenant_id}: recall@5={result.recall_at_5:.3f} "
            f"precision@5={result.precision_at_5:.3f} mrr={result.mrr:.3f} "
            f"ndcg@10={result.ndcg_at_10:.3f}"
        )


if __name__ == "__main__":
    main()
