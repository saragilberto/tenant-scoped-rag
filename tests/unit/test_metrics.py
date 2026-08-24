"""RAG-29: recall@k, precision@k, MRR and nDCG@k are pure, deterministic, network-free."""

import math
import socket

from eval.metrics import mrr, ndcg_at_k, precision_at_k, recall_at_k


def test_recall_at_k_hand_calculated():
    retrieved = ["a", "b", "c"]
    relevant = ["b", "d"]
    assert recall_at_k(retrieved, relevant, 3) == 0.5


def test_precision_at_k_hand_calculated():
    retrieved = ["a", "b", "c"]
    relevant = ["b", "d"]
    assert precision_at_k(retrieved, relevant, 3) == 1 / 3


def test_mrr_hand_calculated():
    retrieved = ["a", "b", "c"]
    relevant = ["b"]
    assert mrr(retrieved, relevant) == 0.5


def test_ndcg_at_k_hand_calculated():
    retrieved = ["a", "b", "c"]
    relevant = ["a", "c"]
    dcg = 1.0 / math.log2(2) + 1.0 / math.log2(4)  # hits at positions 1 and 3
    idcg = 1.0 / math.log2(2) + 1.0 / math.log2(3)  # best case: both hits up front
    expected = dcg / idcg
    assert ndcg_at_k(retrieved, relevant, 3) == expected


def test_recall_at_k_empty_relevant_is_zero():
    assert recall_at_k([], [], 5) == 0.0
    assert recall_at_k(["a"], [], 5) == 0.0


def test_recall_at_k_empty_retrieved_is_zero():
    assert recall_at_k([], ["a"], 5) == 0.0


def test_precision_at_k_empty_retrieved_is_zero():
    assert precision_at_k([], ["a"], 5) == 0.0
    assert precision_at_k([], [], 5) == 0.0


def test_mrr_no_match_is_zero():
    assert mrr(["a", "b"], ["z"]) == 0.0
    assert mrr([], []) == 0.0


def test_ndcg_at_k_empty_retrieved_is_zero():
    assert ndcg_at_k([], ["a"], 5) == 0.0
    assert ndcg_at_k([], [], 5) == 0.0


def test_metrics_never_touch_the_network(monkeypatch):
    def _forbidden(*args, **kwargs):
        raise AssertionError("a metrics function attempted to open a network socket")

    monkeypatch.setattr(socket, "socket", _forbidden)

    retrieved = ["a", "b", "c"]
    relevant = ["b"]
    assert recall_at_k(retrieved, relevant, 3) == 1.0
    assert precision_at_k(retrieved, relevant, 3) == 1 / 3
    assert mrr(retrieved, relevant) == 0.5
    assert ndcg_at_k(retrieved, relevant, 3) > 0.0
