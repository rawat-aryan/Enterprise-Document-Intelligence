from __future__ import annotations

from fastapi import Request, status
from fastapi.responses import JSONResponse


class AppException(Exception):
    def __init__(self, message: str, status_code: int = 400, detail: str = ""):
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(self.message)


class DocumentNotFoundException(AppException):
    def __init__(self, document_id: str):
        super().__init__(
            message=f"Document {document_id} not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class InvoiceNotFoundException(AppException):
    def __init__(self, invoice_id: str):
        super().__init__(
            message=f"Invoice {invoice_id} not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class ExtractionException(AppException):
    def __init__(self, message: str):
        super().__init__(message=message, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


class StorageException(AppException):
    def __init__(self, message: str):
        super().__init__(message=message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ValidationException(AppException):
    def __init__(self, message: str, errors: list = None):
        self.errors = errors or []
        super().__init__(message=message, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message, "error": exc.detail or exc.message},
    )
