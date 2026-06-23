import pytest
import requests_mock

from bihu_stock_data_client import StockDataClient
from bihu_stock_data_client.errors import PaginationLimitError

BASE = "http://localhost:9800/stock/data"


def client():
    return StockDataClient(api_key="key", base_url=BASE, max_retries=0)


def test_fetch_all_aggregates_pages():
    pages = [
        {"column": ["x"], "item": [[1], [2]], "pageNum": 1, "pageSize": 2,
         "totalCount": 3, "totalPage": 2},
        {"column": ["x"], "item": [[3]], "pageNum": 2, "pageSize": 2,
         "totalCount": 3, "totalPage": 2},
    ]
    responses = [{"json": {"code": "0000", "data": p, "traceId": "t"}} for p in pages]
    with requests_mock.Mocker() as m:
        m.post(f"{BASE}/kline-daily/list", responses)
        rows = client().kline_daily(stock_code="000001", page_size=2, fetch_all=True)
        assert len(rows) == 3
        assert rows.total_count == 3
        assert [r["x"] for r in rows] == [1, 2, 3]


def test_fetch_all_max_rows_guard():
    big = {
        "column": ["x"], "item": [[i] for i in range(5)],
        "pageNum": 1, "pageSize": 5, "totalCount": 100, "totalPage": 20,
    }
    with requests_mock.Mocker() as m:
        m.post(f"{BASE}/kline-daily/list", json={"code": "0000", "data": big, "traceId": "t"})
        with pytest.raises(PaginationLimitError):
            client().kline_daily(stock_code="000001", page_size=5, fetch_all=True, max_rows=3)


def test_iter_yields_pages():
    pages = [
        {"column": ["x"], "item": [[1], [2]], "pageNum": 1, "pageSize": 2,
         "totalCount": 3, "totalPage": 2},
        {"column": ["x"], "item": [[3]], "pageNum": 2, "pageSize": 2,
         "totalCount": 3, "totalPage": 2},
    ]
    responses = [{"json": {"code": "0000", "data": p, "traceId": "t"}} for p in pages]
    with requests_mock.Mocker() as m:
        m.post(f"{BASE}/kline-daily/list", responses)
        collected = []
        for page in client().kline_daily_iter(stock_code="000001", page_size=2):
            collected.extend(page)
        assert [r["x"] for r in collected] == [1, 2, 3]


def test_iter_max_rows_guard():
    big = {
        "column": ["x"], "item": [[i] for i in range(5)],
        "pageNum": 1, "pageSize": 5, "totalCount": 100, "totalPage": 20,
    }
    with requests_mock.Mocker() as m:
        m.post(f"{BASE}/kline-daily/list", json={"code": "0000", "data": big, "traceId": "t"})
        with pytest.raises(PaginationLimitError):
            for _ in client().kline_daily_iter(stock_code="000001", page_size=5, max_rows=3):
                pass
