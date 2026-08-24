"""Retrieval candidates: recover, never generate.

Every search mode returns the same shape so the caller (and ``explain_retrieval``) can treat
semantic, lexical and hybrid results uniformly.
"""

from dataclasses import dataclass

__all__ = ["Candidate"]


@dataclass(frozen=True)
class Candidate:
    chunk_id: str
    document_id: str
    text: str
    score: float
    position: int
