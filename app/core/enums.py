from enum import StrEnum


class ChunkingStrategy(StrEnum):
    FIXED = "fixed"
    SENTENCE = "sentence"


class DocumentStatus(StrEnum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"