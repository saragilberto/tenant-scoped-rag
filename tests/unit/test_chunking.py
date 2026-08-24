"""RAG-03, RAG-04 and the fixed-size boundary edge case for src/rag/chunking.py."""

from rag.chunking import ChunkProfile, has_structure, split

HEADED_DOC = """## Preparing the file

Meridian accepts UTF-8 encoded CSV files up to 50,000 rows per upload.

## Field mapping

After upload, Meridian shows a mapping screen that guesses column purposes.

## Duplicate handling

During import, a row is treated as a duplicate when the company name matches.
"""


def _long_unheaded_doc(word_count: int) -> str:
    return " ".join(f"word{i:05d}" for i in range(word_count))


def test_has_structure_true_when_document_has_markdown_headings():
    assert has_structure(HEADED_DOC) is True


def test_has_structure_false_when_document_has_no_markdown_headings():
    assert has_structure(_long_unheaded_doc(50)) is False


def test_split_with_headings_divides_at_section_boundaries_without_overlap():
    chunks = split(HEADED_DOC, ChunkProfile.P512)

    assert [c.text.splitlines()[0] for c in chunks] == [
        "## Preparing the file",
        "## Field mapping",
        "## Duplicate handling",
    ]
    # No overlap: each section's body text appears in exactly one chunk.
    assert sum(c.text.count("50,000 rows") for c in chunks) == 1
    assert sum(c.text.count("mapping screen") for c in chunks) == 1
    assert sum(c.text.count("company name matches") for c in chunks) == 1


def test_split_without_headings_uses_fixed_size_windows_with_15_percent_overlap():
    doc = _long_unheaded_doc(1500)
    chunks = split(doc, ChunkProfile.P512)

    assert len(chunks) > 1
    # Consecutive chunks overlap: the tail of one reappears at the head of the next.
    first_words = chunks[0].text.split()
    second_words = chunks[1].text.split()
    overlap_words = [w for w in first_words if w in second_words]
    assert len(overlap_words) > 0
    ratio = len(overlap_words) / len(first_words)
    assert 0.05 < ratio < 0.30


def test_split_without_headings_larger_than_one_chunk_loses_no_text_at_boundaries():
    word_count = 1500
    doc = _long_unheaded_doc(word_count)
    chunks = split(doc, ChunkProfile.P512)

    assert len(chunks) > 1
    seen_words: set[str] = set()
    for chunk in chunks:
        seen_words.update(chunk.text.split())
    expected_words = set(doc.split())
    assert expected_words <= seen_words


def test_split_profiles_p512_and_p1024_produce_different_chunk_counts_on_same_document():
    doc = _long_unheaded_doc(1500)

    count_512 = len(split(doc, ChunkProfile.P512))
    count_1024 = len(split(doc, ChunkProfile.P1024))

    assert count_512 != count_1024
