from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PyPdfError

from app.core.exceptions import ExtractionError


class PdfExtractor:
    def extract(self, data: bytes) -> str:
        try:
            reader = PdfReader(BytesIO(data))
            pages = [page.extract_text() or "" for page in reader.pages]
        except PyPdfError as exc:
            raise ExtractionError("Could not read the PDF file.") from exc
        return "\n\n".join(pages)