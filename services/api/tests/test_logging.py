from __future__ import annotations

import json
import logging

import pytest

from app.core.logging import (
    JsonLogFormatter,
    correlation_id_ctx,
    job_id_ctx,
    redact_text,
    redact_value,
    request_id_ctx,
)


@pytest.mark.unit
def test_redact_text_scrubs_uri_credentials_and_tokens() -> None:
    raw = (
        "Failed connecting postgresql+psycopg://nextrade_app:super_secret_pw@postgres:5432/nextrade "
        "and redis://:redis_secret@redis:6379/0 with Authorization Bearer eyJhbGciOiJIUzI1NiJ9 "
        "and api_key=my_secret_key_123"
    )
    redacted = redact_text(raw)
    assert "super_secret_pw" not in redacted
    assert "redis_secret" not in redacted
    assert "eyJhbGciOiJIUzI1NiJ9" not in redacted
    assert "my_secret_key_123" not in redacted
    assert "[REDACTED]" in redacted


@pytest.mark.unit
def test_redact_value_scrubs_sensitive_mapping_keys() -> None:
    payload = {
        "user": "alice",
        "password": "my-password",
        "nested": {"database_url": "postgresql://u:p@host:5432/db", "safe": "ok"},
    }
    cleaned = redact_value(None, payload)
    assert cleaned["user"] == "alice"
    assert cleaned["password"] == "[REDACTED]"
    assert cleaned["nested"]["database_url"] == "[REDACTED]"
    assert cleaned["nested"]["safe"] == "ok"


@pytest.mark.unit
def test_json_log_formatter_emits_structured_utc_json_without_secrets() -> None:
    formatter = JsonLogFormatter(service="nextrade-api", environment="test")
    rid_tok = request_id_ctx.set("req_12345678")
    cid_tok = correlation_id_ctx.set("corr_12345678")
    jid_tok = job_id_ctx.set("job_98765432")
    try:
        try:
            raise RuntimeError("broken connection redis://:topsecretpw@redis:6379/0")
        except RuntimeError as exc:
            record = logging.LogRecord(
                name="app.test",
                level=logging.ERROR,
                pathname=__file__,
                lineno=42,
                msg="Connecting with secret=abc123",
                args=(),
                exc_info=(type(exc), exc, exc.__traceback__),
            )
            record.app_secret = "never-log-me"
            record.safe_field = "visible"

        rendered = formatter.format(record)
        parsed = json.loads(rendered)
    finally:
        job_id_ctx.reset(jid_tok)
        correlation_id_ctx.reset(cid_tok)
        request_id_ctx.reset(rid_tok)

    assert parsed["timestamp"].endswith("Z")
    assert parsed["severity"] == "ERROR"
    assert parsed["service"] == "nextrade-api"
    assert parsed["environment"] == "test"
    assert parsed["request_id"] == "req_12345678"
    assert parsed["correlation_id"] == "corr_12345678"
    assert parsed["job_id"] == "job_98765432"
    assert "abc123" not in parsed["message"]
    assert "topsecretpw" not in parsed["exception"]
    assert parsed["app_secret"] == "[REDACTED]"
    assert parsed["safe_field"] == "visible"
