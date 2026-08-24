"""Reference-integrity checks for the versioned golden set (RAG-31).

A golden set entry pointing at a missing or wrong-tenant document would silently invert the
result of the isolation suite, so these checks run as unit tests rather than manual review.
"""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLDEN_DIR = REPO_ROOT / "eval" / "golden"

EXPECTED_QUESTION_COUNT = 30

OVERLAP_SUBJECT_FILENAMES = {
    "login-error.md",
    "csv-import.md",
    "two-factor-auth.md",
    "api-rate-limits.md",
    "invoice-export.md",
    "webhooks.md",
    "sso-setup.md",
    "log-retention.md",
}
MIN_OVERLAP_QUESTIONS = 10


def _load(tenant: str) -> list[dict]:
    with (GOLDEN_DIR / f"{tenant}.yaml").open() as f:
        return yaml.safe_load(f)


def _relevant_doc_paths(questions: list[dict]) -> list[str]:
    return [doc for q in questions for doc in q["relevant_docs"]]


def test_meridian_has_exactly_30_questions():
    questions = _load("meridian")
    assert len(questions) == EXPECTED_QUESTION_COUNT, (
        f"expected exactly {EXPECTED_QUESTION_COUNT} meridian questions, found {len(questions)}"
    )
    for question in questions:
        assert question["relevant_docs"], f"{question['id']} has no relevant documents annotated"


def test_meridian_references_resolve_to_existing_documents():
    questions = _load("meridian")
    for doc_path in _relevant_doc_paths(questions):
        assert (REPO_ROOT / doc_path).is_file(), (
            f"golden set references missing document: {doc_path}"
        )


def test_meridian_overlap_coverage_at_least_10():
    questions = _load("meridian")
    overlap_question_count = sum(
        1
        for q in questions
        if any(Path(doc).name in OVERLAP_SUBJECT_FILENAMES for doc in q["relevant_docs"])
    )
    assert overlap_question_count >= MIN_OVERLAP_QUESTIONS, (
        f"expected >= {MIN_OVERLAP_QUESTIONS} meridian questions on overlap subjects, "
        f"found {overlap_question_count}"
    )
