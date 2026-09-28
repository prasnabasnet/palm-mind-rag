from pathlib import Path

from app.core.exceptions import EmptyDocumentError, UnsupportedFileTypeError
from app.extraction.base import TextExtractor
from app.extraction.pdf import PdfExtractor
from app.extraction.txt import TxtExtractor

_EXTRACTORS: dict[str, TextExtractor] = {
    ".pdf": PdfExtractor(),
    ".txt": TxtExtractor(),
}


def extract_text(filename: str, data: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    extractor = _EXTRACTORS.get(suffix)
    if extractor is None:
        raise UnsupportedFileTypeError(f"Unsupported file type: '{suffix}'. Use .pdf or .txt.")

    text = extractor.extract(data).strip()
    if not text:
        raise EmptyDocumentError("No extractable text found in the document.")
    return text