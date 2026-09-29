class AppError(Exception):
    """Base class for domain errors raised by our own code."""


class UnsupportedFileTypeError(AppError):
    """The uploaded file is not a .pdf or .txt."""


class ExtractionError(AppError):
    """The file could not be parsed."""


class EmptyDocumentError(AppError):
    """No text could be extracted (e.g. a scanned PDF)."""


class FileTooLargeError(AppError):
    """The uploaded file exceeds the size limit."""


class DocumentNotFoundError(AppError):
    """No document exists with the given id."""


class IngestionError(AppError):
    """Embedding or vector storage failed while ingesting a document."""

class LLMError(AppError):
    """The language model provider returned an error or was unreachable."""