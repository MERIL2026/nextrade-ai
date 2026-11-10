from datetime import UTC, datetime

from pydantic import BaseModel, Field


class ResponseMeta(BaseModel):
    """Standard metadata block attached to every /api/v1 response (NEX-DOC-009 §6.2)."""

    request_id: str
    api_version: str = "v1"
    as_of: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SuccessResponse[T](BaseModel):
    """Standard versioned success response envelope (NEX-DOC-009 §6.2)."""

    data: T
    meta: ResponseMeta


class ErrorDetail(BaseModel):
    """Safe field-level or contextual error item."""

    field: str | None = None
    reason: str


class ErrorPayload(BaseModel):
    """Structured error body without internal traces or secrets."""

    code: str
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    """Standard versioned error response envelope (NEX-DOC-009 §6.3)."""

    error: ErrorPayload
    meta: ResponseMeta
