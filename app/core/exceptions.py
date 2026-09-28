class AppError(Exception):
    """Base class for domain errors raised by our own code."""


class UnsupportedFileTypeError(AppError):
    """The uploaded file is not a .pdf or .txt."""


class ExtractionError(AppError):
    """The file could not be parsed."""


class EmptyDocumentError(AppError):
    """No text could be extracted (e.g. a scanned PDF)."""