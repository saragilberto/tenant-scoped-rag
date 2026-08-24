"""Structural integrity checks for the versioned corpus (RAG-01).

A golden set referencing a corrupted or incomplete corpus would silently invalidate every
published metric, so these checks run as unit tests rather than being left to manual review.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CORPUS_DIR = REPO_ROOT / "corpus"

VISIBILITY_VOCAB = {"empresa", "departamentos", "equipes", "restrito"}
REQUIRED_FRONT_MATTER_FIELDS = {"title", "category", "version", "visibility"}

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

EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_PATTERN = re.compile(r"\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}\b")
CPF_PATTERN = re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}")
WORD_PATTERN = re.compile(r"[A-Za-z0-9']+")


def _split_front_matter(text: str) -> tuple[dict[str, str], str]:
    assert text.startswith("---\n"), "article must start with a YAML front-matter block"
    _, front_matter_block, body = text.split("---\n", 2)
    front_matter: dict[str, str] = {}
    for line in front_matter_block.splitlines():
        if not line.strip():
            continue
        key, _, value = line.partition(":")
        front_matter[key.strip()] = value.strip().strip('"')
    return front_matter, body


def _articles(tenant_dir: Path) -> list[Path]:
    return sorted(tenant_dir.glob("*.md"))


def _all_articles() -> list[Path]:
    return sorted(CORPUS_DIR.glob("*/*.md"))


def test_meridian_has_at_least_20_articles():
    meridian_dir = CORPUS_DIR / "meridian"
    articles = _articles(meridian_dir)
    assert len(articles) >= 20, f"expected >= 20 meridian articles, found {len(articles)}"


def test_meridian_has_at_least_5_articles_without_internal_headings():
    meridian_dir = CORPUS_DIR / "meridian"
    no_heading_count = 0
    for article in _articles(meridian_dir):
        _, body = _split_front_matter(article.read_text())
        if not any(line.lstrip().startswith("#") for line in body.splitlines()):
            no_heading_count += 1
    assert no_heading_count >= 5, (
        f"expected >= 5 meridian articles with no internal markdown headings, found {no_heading_count}"
    )


def test_all_corpus_articles_have_complete_valid_front_matter():
    for article in _all_articles():
        front_matter, _ = _split_front_matter(article.read_text())
        missing = REQUIRED_FRONT_MATTER_FIELDS - front_matter.keys()
        assert not missing, f"{article} is missing front-matter fields: {missing}"
        visibility = front_matter["visibility"]
        assert visibility in VISIBILITY_VOCAB, (
            f"{article} has visibility {visibility!r} outside the allowed vocabulary {VISIBILITY_VOCAB}"
        )


def test_no_real_pii_patterns_in_corpus_articles():
    for article in _all_articles():
        content = article.read_text()
        assert not EMAIL_PATTERN.search(content), f"{article} contains an email-like pattern"
        assert not PHONE_PATTERN.search(content), f"{article} contains a phone-like pattern"
        assert not CPF_PATTERN.search(content), f"{article} contains a CPF-like pattern"


def test_halcyon_has_at_least_20_articles():
    halcyon_dir = CORPUS_DIR / "halcyon"
    articles = _articles(halcyon_dir)
    assert len(articles) >= 20, f"expected >= 20 halcyon articles, found {len(articles)}"


def test_all_8_overlap_subjects_present_in_both_tenants():
    meridian_filenames = {a.name for a in _articles(CORPUS_DIR / "meridian")}
    halcyon_filenames = {a.name for a in _articles(CORPUS_DIR / "halcyon")}
    missing_in_meridian = OVERLAP_SUBJECT_FILENAMES - meridian_filenames
    missing_in_halcyon = OVERLAP_SUBJECT_FILENAMES - halcyon_filenames
    assert not missing_in_meridian, f"meridian is missing overlap subjects: {missing_in_meridian}"
    assert not missing_in_halcyon, f"halcyon is missing overlap subjects: {missing_in_halcyon}"


def _twelve_grams(tenant_dir: Path) -> set[tuple[str, ...]]:
    grams: set[tuple[str, ...]] = set()
    for article in _articles(tenant_dir):
        _, body = _split_front_matter(article.read_text())
        words = tuple(w.lower() for w in WORD_PATTERN.findall(body))
        for i in range(len(words) - 11):
            grams.add(words[i : i + 12])
    return grams


def test_no_12_word_identical_span_between_corpora():
    meridian_grams = _twelve_grams(CORPUS_DIR / "meridian")
    halcyon_grams = _twelve_grams(CORPUS_DIR / "halcyon")
    shared = meridian_grams & halcyon_grams
    assert not shared, f"meridian and halcyon share identical 12-word spans: {shared}"
