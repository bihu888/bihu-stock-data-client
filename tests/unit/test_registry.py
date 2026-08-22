import pytest

from bihu_stock_data_client.registry import ENDPOINTS


def test_unique_names():
    names = [e.name for e in ENDPOINTS]
    assert len(names) == len(set(names))


def test_count():
    assert len(ENDPOINTS) == 28


def test_required_fields():
    for e in ENDPOINTS:
        assert e.name and e.path and e.method
        assert e.summary
        for p in e.path_params:
            assert "{" + p + "}" in e.path


def test_paginated_marked():
    by_name = {e.name: e for e in ENDPOINTS}
    assert by_name["kline_daily"].paginated is True
    assert by_name["stock_basic"].paginated is False
    assert by_name["kline_minute"].paginated is False
    assert by_name["market_quote"].paginated is False
    assert by_name["market_kline_minute"].paginated is False
    assert by_name["market_transaction"].paginated is False


def test_known_params():
    by_name = {e.name: e for e in ENDPOINTS}
    assert by_name["kline_daily"].params == ("stock_code", "start_date", "end_date")
    assert by_name["financial_report"].params == (
        "stock_code",
        "report_year",
        "quarter_type",
    )
    assert by_name["kline_minute"].path_params == ("stock_code", "trade_date")
    assert by_name["market_quote"].path_params == ("stock_code",)
    assert by_name["market_transaction"].params == ("max_count",)
    assert by_name["market_transaction"].path_params == ("stock_code",)
