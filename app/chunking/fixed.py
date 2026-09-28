from app.chunking.base import Chunk
from app.chunking.utils import normalize_whitespace


class FixedSizeChunker:
    """Slides a fixed-length character window over the text with overlap."""

    def __init__(self, chunk_size: int = 800, overlap: int = 100) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if not 0 <= overlap < chunk_size:
            raise ValueError("overlap must be >= 0 and smaller than chunk_size")
        self._chunk_size = chunk_size
        self._overlap = overlap

    def chunk(self, text: str) -> list[Chunk]:
        text = normalize_whitespace(text)
        chunks: list[Chunk] = []
        start = 0
        while start < len(text):
            end = start + self._chunk_size
            piece = text[start:end].strip()
            if piece:
                chunks.append(Chunk(index=len(chunks), text=piece))
            if end >= len(text):
                break
            start = end - self._overlap
        return chunks