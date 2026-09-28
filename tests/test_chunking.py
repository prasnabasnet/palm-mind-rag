import pytest

from app.chunking.fixed import FixedSizeChunker
from app.chunking.sentence import SentenceChunker


def test_fixed_chunker_respects_size_and_overlap() -> None:
    chunks = FixedSizeChunker(chunk_size=10, overlap=3).chunk("a" * 25)
    assert all(len(c.text) <= 10 for c in chunks)
    assert [c.index for c in chunks] == list(range(len(chunks)))
    assert len(chunks) == 4


def test_fixed_chunker_rejects_bad_overlap() -> None:
    with pytest.raises(ValueError):
        FixedSizeChunker(chunk_size=10, overlap=10)


def test_sentence_chunker_keeps_sentences_whole() -> None:
    text = "First one. Second one. Third one. Fourth one."
    chunks = SentenceChunker(max_chars=25, overlap_sentences=0).chunk(text)
    assert all(c.text.endswith(".") for c in chunks)
    assert " ".join(c.text for c in chunks) == text


def test_sentence_chunker_overlaps_previous_sentence() -> None:
    text = "Alpha one. Beta two. Gamma three."
    chunks = SentenceChunker(max_chars=25, overlap_sentences=1).chunk(text)
    assert chunks[0].text.split(". ")[-1] in chunks[1].text