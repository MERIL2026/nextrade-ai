from __future__ import annotations

import logging
import re
import time
import uuid

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.logging import correlation_id_ctx, request_id_ctx

logger = logging.getLogger("app.http")

REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{8,64}$")

SECURITY_HEADERS: tuple[tuple[str, str], ...] = (
    ("X-Content-Type-Options", "nosniff"),
    ("Referrer-Policy", "strict-origin-when-cross-origin"),
    ("X-Frame-Options", "DENY"),
    ("Permissions-Policy", "camera=(), microphone=(), geolocation=()"),
)

_SECURITY_HEADERS: tuple[tuple[bytes, bytes], ...] = tuple(
    (name.lower().encode("ascii"), value.encode("ascii")) for name, value in SECURITY_HEADERS
)


def resolve_request_id(raw_header: str | None) -> str:
    """Validate client-supplied X-Request-ID or generate a safe correlation ID."""
    if raw_header:
        candidate = raw_header.strip()
        if REQUEST_ID_PATTERN.fullmatch(candidate):
            return candidate
    return f"req_{uuid.uuid4().hex}"


class RequestContextMiddleware:
    """ASGI middleware assigning X-Request-ID, logging HTTP metrics, and setting security headers."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers_dict = {
            k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])
        }
        request_id = resolve_request_id(headers_dict.get("x-request-id"))
        correlation_id = resolve_request_id(headers_dict.get("x-correlation-id"))
        if not headers_dict.get("x-correlation-id"):
            correlation_id = request_id

        state = scope.setdefault("state", {})
        state["request_id"] = request_id
        state["correlation_id"] = correlation_id

        rid_token = request_id_ctx.set(request_id)
        cid_token = correlation_id_ctx.set(correlation_id)
        started = time.perf_counter()
        status_code = 500
        method = str(scope.get("method", "UNKNOWN"))
        path = str(scope.get("path", "/"))

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
                raw_headers: list[tuple[bytes, bytes]] = list(message.get("headers", []))
                existing_keys = {k.lower() for k, _ in raw_headers}

                if b"x-request-id" not in existing_keys:
                    raw_headers.append((b"x-request-id", request_id.encode("ascii")))
                for header_name, header_val in _SECURITY_HEADERS:
                    if header_name not in existing_keys:
                        raw_headers.append((header_name, header_val))
                if (path.startswith("/api/") or path == "/health") and (
                    b"cache-control" not in existing_keys
                ):
                    raw_headers.append((b"cache-control", b"no-store"))

                message["headers"] = raw_headers
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000.0, 2)
            logger.info(
                "HTTP request completed",
                extra={
                    "method": method,
                    "path": path,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                },
            )
            correlation_id_ctx.reset(cid_token)
            request_id_ctx.reset(rid_token)
