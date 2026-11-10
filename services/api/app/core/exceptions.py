from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import request_id_ctx
from app.core.schemas import ErrorDetail, ErrorPayload, ErrorResponse, ResponseMeta
from app.core.security import SECURITY_HEADERS

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Application exception mapped safely to the standard NEX-DOC-009 error envelope."""

    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        details: list[ErrorDetail] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or []


def _get_request_id(request: Request) -> str:
    state_rid = getattr(request.state, "request_id", None)
    if isinstance(state_rid, str) and state_rid:
        return state_rid
    ctx_rid = request_id_ctx.get()
    if ctx_rid:
        return ctx_rid
    return "req_unknown"


def _error_response(
    *,
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: list[ErrorDetail] | None = None,
) -> JSONResponse:
    request_id = _get_request_id(request)
    body = ErrorResponse(
        error=ErrorPayload(
            code=code,
            message=message,
            details=details or [],
        ),
        meta=ResponseMeta(request_id=request_id),
    )
    response = JSONResponse(
        status_code=status_code,
        content=body.model_dump(mode="json"),
    )
    response.headers["X-Request-ID"] = request_id
    for header_name, header_value in SECURITY_HEADERS:
        response.headers.setdefault(header_name, header_value)
    response.headers.setdefault("Cache-Control", "no-store")
    return response


def _status_to_error_code(status_code: int) -> str:
    mapping = {
        status.HTTP_400_BAD_REQUEST: "BAD_REQUEST",
        status.HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
        status.HTTP_403_FORBIDDEN: "FORBIDDEN",
        status.HTTP_404_NOT_FOUND: "NOT_FOUND",
        status.HTTP_405_METHOD_NOT_ALLOWED: "METHOD_NOT_ALLOWED",
        status.HTTP_409_CONFLICT: "CONFLICT",
        status.HTTP_422_UNPROCESSABLE_CONTENT: "VALIDATION_ERROR",
        status.HTTP_429_TOO_MANY_REQUESTS: "RATE_LIMITED",
        status.HTTP_503_SERVICE_UNAVAILABLE: "SERVICE_UNAVAILABLE",
    }
    return mapping.get(status_code, f"HTTP_{status_code}")


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers adhering to NEX-DOC-009 & NEX-DOC-018."""

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return _error_response(
            request=request,
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            details=exc.details,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details: list[ErrorDetail] = []
        for err in exc.errors():
            loc_parts = [str(part) for part in err.get("loc", ()) if part != "body"]
            field_path = ".".join(loc_parts) if loc_parts else None
            reason = str(err.get("msg", "Invalid value."))
            details.append(ErrorDetail(field=field_path, reason=reason))

        return _error_response(
            request=request,
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="VALIDATION_ERROR",
            message="The request could not be processed.",
            details=details,
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        detail: Any = exc.detail
        safe_message = (
            detail if isinstance(detail, str) and detail else "Request could not be completed."
        )
        return _error_response(
            request=request,
            status_code=exc.status_code,
            code=_status_to_error_code(exc.status_code),
            message=safe_message,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "Unhandled server exception",
            extra={
                "method": request.method,
                "path": request.url.path,
            },
        )
        return _error_response(
            request=request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="INTERNAL_ERROR",
            message="An unexpected internal error occurred.",
        )
