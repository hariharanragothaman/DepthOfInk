"""Tests for structured logging and request ID propagation."""
import json
import logging

from app.logging_config import JSONFormatter, RequestIDFilter, request_id_var


class TestRequestIDFilter:
    def test_injects_request_id(self):
        filt = RequestIDFilter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="hello", args=(), exc_info=None,
        )
        token = request_id_var.set("abc123")
        try:
            filt.filter(record)
            assert record.request_id == "abc123"  # type: ignore[attr-defined]
        finally:
            request_id_var.reset(token)

    def test_default_dash(self):
        filt = RequestIDFilter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="hello", args=(), exc_info=None,
        )
        filt.filter(record)
        assert record.request_id == "-"  # type: ignore[attr-defined]


class TestJSONFormatter:
    def test_output_is_valid_json(self):
        fmt = JSONFormatter()
        record = logging.LogRecord(
            name="app.test", level=logging.INFO, pathname="", lineno=0,
            msg="test message", args=(), exc_info=None,
        )
        record.request_id = "req-42"  # type: ignore[attr-defined]
        line = fmt.format(record)
        parsed = json.loads(line)
        assert parsed["level"] == "INFO"
        assert parsed["message"] == "test message"
        assert parsed["request_id"] == "req-42"
        assert parsed["logger"] == "app.test"
        assert "timestamp" in parsed

    def test_exception_included(self):
        fmt = JSONFormatter()
        try:
            raise ValueError("boom")
        except ValueError:
            import sys
            record = logging.LogRecord(
                name="app.test", level=logging.ERROR, pathname="", lineno=0,
                msg="fail", args=(), exc_info=sys.exc_info(),
            )
        record.request_id = "-"  # type: ignore[attr-defined]
        line = fmt.format(record)
        parsed = json.loads(line)
        assert "exception" in parsed
        assert "ValueError" in parsed["exception"]


class TestRequestIDMiddleware:
    def test_response_has_request_id(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert "X-Request-ID" in r.headers
        assert len(r.headers["X-Request-ID"]) > 0

    def test_custom_request_id_forwarded(self, client):
        r = client.get("/health", headers={"X-Request-ID": "my-custom-id"})
        assert r.headers["X-Request-ID"] == "my-custom-id"

    def test_auto_generated_when_not_provided(self, client):
        r1 = client.get("/health")
        r2 = client.get("/health")
        assert r1.headers["X-Request-ID"] != r2.headers["X-Request-ID"]
