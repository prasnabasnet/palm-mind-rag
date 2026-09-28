from app.chunking.base import Chunker
from app.chunking.fixed import FixedSizeChunker
from app.chunking.sentence import SentenceChunker
from app.core.enums import ChunkingStrategy

_CHUNKERS: dict[ChunkingStrategy, Chunker] = {
    ChunkingStrategy.FIXED: FixedSizeChunker(),
    ChunkingStrategy.SENTENCE: SentenceChunker(),
}


def get_chunker(strategy: ChunkingStrategy) -> Chunker:
    return _CHUNKERS[strategy]