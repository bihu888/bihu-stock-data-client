import pytest
import requests_mock

from bihu_stock_data_client import StockDataClient
from bihu_stock_data_client.decoder import Records
from bihu_stock_data_client.errors import ValidationError

BASE = "http://localhost:9800/stock/data"


def client():
    return StockDataClient(api_key="key", base_url=BASE, max_retries=0)


def test_post_paginated_single_page():
    with requests_mock.Mocker() as m:
        m.post(
            f"{BASE}/kline-daily/list",
            json={
                "code": "0000",
                "data": {
                    "column": ["stockCode", "close"],
                    "item": [["000001", 10.5]],
                    "pageNum": 1, "pageSize": 1000, "totalCount": 1, "totalPage": 1,
                },
                "traceId": "t",
            },
        )
        rows = client().kline_daily(stock_code="000001", start_date="2025-01-01")
        assert isinstance(rows, Records)
        assert rows[0] == {"stockCode": "000001", "close": 10.5}
        assert rows.total_count == 1
        body = m.last_request.json()
        assert body["stockCode"] == "000001"          # snake -> camel
        assert body["startDate"] == "2025-01-01"
        assert body["pageNum"] == 1
        assert body["pageSize"] == 1000


def test_get_list_all():
    with requests_mock.Mocker() as m:
        m.get(
            f"{BASE}/stock-basic/list",
            json={"code": "0000",
                  "data": {"column": ["code"], "item": [["000001"]]}, "traceId": "t"},
        )
        rows = client().stock_basic()
        assert rows[0] == {"code": "000001"}
        assert rows.total_count is None  # 非分页


def test_get_path_param():
    with requests_mock.Mocker() as m:
        m.get(
            f"{BASE}/kline-minute/000001/2025-06-20",
            json={"code": "0000",
                  "data": {"column": ["t"], "item": [[1]]}, "traceId": "t"},
        )
        rows = client().kline_minute(stock_code="000001", trade_date="2025-06-20")
        assert rows[0] == {"t": 1}
        assert "kline-minute/000001/2025-06-20" in m.last_request.path


def test_market_quote_get_path():
    with requests_mock.Mocker() as m:
        m.get(
            f"{BASE}/market/quote/000001",
            json={"code": "0000",
                  "data": {"column": ["stock_code", "last_price"],
                           "item": [["000001.SZ", 10.5]]},
                  "traceId": "t"},
        )
        rows = client().market_quote(stock_code="000001")
        assert rows[0]["last_price"] == 10.5
        assert rows.total_count is None  # 非分页
        assert m.last_request.method == "GET"
        assert "/market/quote/000001" in m.last_request.path


def test_market_kline_minute_get_path():
    with requests_mock.Mocker() as m:
        m.get(
            f"{BASE}/market/kline-minute/000001",
            json={"code": "0000",
                  "data": {"column": ["trade_time", "close"], "item": [["093100", 10.5]]},
                  "traceId": "t"},
        )
        rows = client().market_kline_minute(stock_code="000001")
        assert rows[0]["close"] == 10.5
        assert m.last_request.method == "GET"


def test_market_transaction_query_param_camelcase():
    with requests_mock.Mocker() as m:
        m.get(
            f"{BASE}/market/transaction/000001",
            json={"code": "0000",
                  "data": {"column": ["price", "volume"], "item": [[10.5, 100]]},
                  "traceId": "t"},
        )
        client().market_transaction(stock_code="000001", max_count=5000)
        assert m.last_request.method == "GET"
        # 查询参数走 camelCase，与服务端 @RequestParam maxCount 对齐
        assert "maxCount=5000" in m.last_request.url
        assert m.last_request.qs["maxcount"] == ["5000"]


def test_market_transaction_default_no_query():
    with requests_mock.Mocker() as m:
        m.get(
            f"{BASE}/market/transaction/000001",
            json={"code": "0000",
                  "data": {"column": ["price"], "item": [[10.5]]}, "traceId": "t"},
        )
        client().market_transaction(stock_code="000001")
        assert m.last_request.qs == {}  # max_count 缺省时不带查询参数


def test_unknown_param_rejected():
    with pytest.raises(TypeError):
        client().kline_daily(foo="bar")


def test_quarter_type_validated():
    with pytest.raises(ValidationError):
        client().financial_report(stock_code="000001", report_year=2024, quarter_type=9)


def test_page_size_validated():
    with pytest.raises(ValidationError):
        client().kline_daily(stock_code="000001", page_size=5000)
