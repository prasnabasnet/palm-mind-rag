import pytest

from app.core.exceptions import EmptyDocumentError, UnsupportedFileTypeError
from app.extraction.factory import extract_text


def test_extracts_txt() -> None:
    assert extract_text("notes.txt", b"hello world") == "hello world"


def test_rejects_unsupported_type() -> None:
    with pytest.raises(UnsupportedFileTypeError):
        extract_text("image.png", b"...")


def test_rejects_empty_text() -> None:
    with pytest.raises(EmptyDocumentError):
        extract_text("blank.txt", b"   \n  ")
        