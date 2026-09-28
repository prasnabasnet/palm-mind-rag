from typing import Protocol


class TextExtractor(Protocol):
    def extract(self, data: bytes) -> str: ...