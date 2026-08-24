"""RAG-29: deterministic retrieval metrics over lists of document identifiers.

Pure functions, no I/O and no network call anywhere in this module - the only way a
metric published in the README can be reproduced by a stranger running the same
golden set is if computing it never depends on anything outside its arguments.

Every metric treats an empty ``relevant`` set as vacuous (nothing to find, so nothing
counted) rather than raising - a golden-set question with no annotated document would
otherwise crash the whole harness run instead of just contributing a defined zero.
"""

import math

__all__ = ["recall_at_k", "precision_at_k", "mrr", "ndcg_at_k"]


def recall_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    if not relevant:
        return 0.0
    relevant_set = set(relevant)
    top_k = retrieved[:k]
    found = sum(1 for doc_id in top_k if doc_id in relevant_set)
    return found / len(relevant_set)


def precision_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    top_k = retrieved[:k]
    if not top_k:
        return 0.0
    relevant_set = set(relevant)
    found = sum(1 for doc_id in top_k if doc_id in relevant_set)
    return found / len(top_k)


def mrr(retrieved: list[str], relevant: list[str]) -> float:
    if not retrieved or not relevant:
        return 0.0
    relevant_set = set(relevant)
    for position, doc_id in enumerate(retrieved, start=1):
        if doc_id in relevant_set:
            return 1.0 / position
    return 0.0


def ndcg_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    if not relevant:
        return 0.0
    relevant_set = set(relevant)
    top_k = retrieved[:k]

    dcg = sum(
        1.0 / math.log2(position + 1)
        for position, doc_id in enumerate(top_k, start=1)
        if doc_id in relevant_set
    )
    ideal_hits = min(len(relevant_set), k)
    idcg = sum(1.0 / math.log2(position + 1) for position in range(1, ideal_hits + 1))
    if idcg == 0.0:
        return 0.0
    return dcg / idcg
