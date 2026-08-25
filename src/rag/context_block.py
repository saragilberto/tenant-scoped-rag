"""Build the grounded-prompt text block and deliver it to stdout/clipboard.

Never calls a chat completion endpoint - this only prepares the text a person pastes
into the chat `llamafile` already serves.
"""

import shutil
import subprocess

from rag.retrieval import Candidate

__all__ = ["build_block", "estimate_tokens", "copy_to_clipboard"]

_CHARS_PER_TOKEN = 4

_INSTRUCTION = "Responda somente com base no conteúdo apresentado acima."


def build_block(question: str, candidates: list[Candidate]) -> str:
    chunks = "\n\n".join(f"[{c.document_id} #{c.position}]\n{c.text}" for c in candidates)
    return f"Pergunta: {question}\n\n{chunks}\n\n{_INSTRUCTION}"


def estimate_tokens(text: str) -> int:
    return len(text) // _CHARS_PER_TOKEN


def copy_to_clipboard(text: str) -> bool:
    if shutil.which("pbcopy") is None:
        return False
    try:
        subprocess.run(["pbcopy"], input=text, text=True, check=True)
        return True
    except (OSError, subprocess.SubprocessError):
        return False
