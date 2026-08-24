"""Structure-aware document chunking.

Split at markdown section boundaries when a document has them; fall back to fixed-size
windows with 15% overlap when it does not. The fixed-size path counts tokens with the same
tokenizer the embedding model uses, so a chunk boundary means the same thing here as it does
at embedding time.
"""

import math
import re
from dataclasses import dataclass
from enum import StrEnum
from functools import lru_cache

_HEADING_RE = re.compile(r"(?m)^#{1,6}[ \t]+\S")
_EMBEDDING_MODEL_NAME = "intfloat/multilingual-e5-base"
_OVERLAP_RATIO = 0.15

__all__ = ["Chunk", "ChunkProfile", "has_structure", "split"]


class ChunkProfile(StrEnum):
    P512 = "P512"
    P1024 = "P1024"


_PROFILE_TOKENS = {ChunkProfile.P512: 512, ChunkProfile.P1024: 1024}


@dataclass(frozen=True)
class Chunk:
    text: str
    ord: int


@lru_cache(maxsize=1)
def _tokenizer():
    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained(_EMBEDDING_MODEL_NAME)


def has_structure(text: str) -> bool:
    """True when the document contains at least one markdown heading line."""
    return _HEADING_RE.search(text) is not None


def split(text: str, profile: ChunkProfile) -> list[Chunk]:
    if has_structure(text):
        return _split_by_headings(text)
    return _split_fixed_size(text, profile)


def _split_by_headings(text: str) -> list[Chunk]:
    heading_starts = [m.start() for m in _HEADING_RE.finditer(text)]
    sections: list[str] = []
    if heading_starts[0] > 0:
        preamble = text[: heading_starts[0]].strip()
        if preamble:
            sections.append(preamble)
    for i, start in enumerate(heading_starts):
        end = heading_starts[i + 1] if i + 1 < len(heading_starts) else len(text)
        section = text[start:end].strip()
        if section:
            sections.append(section)
    return [Chunk(text=section, ord=i) for i, section in enumerate(sections)]


def _split_fixed_size(text: str, profile: ChunkProfile) -> list[Chunk]:
    window = _PROFILE_TOKENS[profile]
    overlap = math.floor(window * _OVERLAP_RATIO)
    stride = window - overlap

    encoding = _tokenizer()(text, add_special_tokens=False, return_offsets_mapping=True)
    offsets = [pair for pair in encoding["offset_mapping"] if pair[1] > pair[0]]
    if not offsets:
        return []

    chunks: list[Chunk] = []
    start_idx = 0
    total = len(offsets)
    ord_ = 0
    while start_idx < total:
        end_idx = min(start_idx + window, total)
        char_start = offsets[start_idx][0]
        char_end = offsets[end_idx - 1][1]
        chunks.append(Chunk(text=text[char_start:char_end], ord=ord_))
        ord_ += 1
        if end_idx >= total:
            break
        start_idx += stride
    return chunks
