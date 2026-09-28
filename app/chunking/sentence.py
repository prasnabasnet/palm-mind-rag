import re

from app.chunking.base import Chunk
from app.chunking.utils import normalize_whitespace

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")


class SentenceChunker:
    """Packs whole sentences into chunks up to max_chars, repeating the last
    `overlap_sentences` sentences at the start of the next chunk."""

    def __init__(self, max_chars: int = 800, overlap_sentences: int = 1) -> None:
        if max_chars <= 0:
            raise ValueError("max_chars must be positive")
        if overlap_sentences < 0:
            raise ValueError("overlap_sentences must be >= 0")
        self._max_chars = max_chars
        self._overlap = overlap_sentences

    def chunk(self, text: str) -> list[Chunk]:
        sentences = [
            s for s in _SENTENCE_BOUNDARY.split(normalize_whitespace(text)) if s
        ]
        chunks: list[Chunk] = []
        current: list[str] = []
        length = 0

        for sentence in sentences:
            if current and length + len(sentence) + 1 > self._max_chars:
                chunks.append(Chunk(index=len(chunks), text=" ".join(current)))
                current = current[-self._overlap :] if self._overlap else []
                length = sum(len(s) + 1 for s in current)
            current.append(sentence)
            length += len(sentence) + 1

        if current:
            chunks.append(Chunk(index=len(chunks), text=" ".join(current)))
        return chunks