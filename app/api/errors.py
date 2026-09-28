from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    AppError,
    DocumentNotFoundError,
    EmptyDocumentError,
    ExtractionError,
    FileTooLargeError,
    UnsupportedFileTypeError,
)

_STATUS_BY_ERROR: dict[type[Exception], int] = {
    UnsupportedFileTypeError: 415,
    FileTooLargeError: 413,
    EmptyDocumentError: 422,
    ExtractionError: 422,
    DocumentNotFoundError: 404,
}


async def app_error_handler(_: Request, exc: Exception) -> JSONResponse:
    status_code = _STATUS_BY_ERROR.get(type(exc), 500)
    return JSONResponse(status_code=status_code, content={"detail": str(exc)})


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)