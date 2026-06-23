import pytest

from bihu_stock_data_client.errors import (
    ApiError,
    AuthenticationError,
    ConfigurationError,
    ConnectionError,
    PaginationLimitError,
    RateLimitError,
    StockDataError,
    ValidationError,
)


def test_all_subclass_base():
    for exc in (
        ConfigurationError,
        AuthenticationError,
        RateLimitError,
        ApiError,
        PaginationLimitError,
        ConnectionError,
        ValidationError,
    ):
        assert issubclass(exc, StockDataError)


def test_trace_id_carried():
    e = AuthenticationError("bad key", trace_id="abc123")
    assert e.trace_id == "abc123"
    assert str(e) == "bad key"


def test_api_error_fields():
    e = ApiError("oops", code="1001", status=None, trace_id="t-1")
    assert e.code == "1001"
    assert e.trace_id == "t-1"
    assert e.message == "oops"
