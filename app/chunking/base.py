from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class Chunk:
    index: int
    text: str


class Chunker(Protocol):
    def chunk(self, text: str) -> list[Chunk]: ...