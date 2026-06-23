import pytest
import requests.exceptions
import requests_mock

from bihu_stock_data_client.config import ClientConfig
from bihu_stock_data_client.errors import (
    ApiError,
    AuthenticationError,
    ConnectionError,
    RateLimitError,
)
from bihu_stock_data_client.transport import HttpClient

BASE = "http://localhost:9800/stock/data"


def make_client():
    return HttpClient(ClientConfig.from_env(api_key="key123", base_url=BASE, max_retries=0))


def test_success_unwraps_data():
    with requests_mock.Mocker() as m:
        m.post(
            f"{BASE}/kline-daily/list",
            json={"code": "0000", "message": "ok",
                  "data": {"column": ["a"], "item": [[1]]}, "traceId": "t"},
        )
        data = make_client().request("POST", "/kline-daily/list", json={"stockCode": "000001"})
        assert data == {"column": ["a"], "item": [[1]]}


def test_api_key_header_sent():
    with requests_mock.Mocker() as m:
        m.get(f"{BASE}/stock-basic/list", json={"code": "0000", "data": None, "traceId": "t"})
        make_client().request("GET", "/stock-basic/list")
        assert m.last_request.headers["X-API-Key"] == "key123"


def test_401_raises_auth_error():
    with requests_mock.Mocker() as m:
        m.get(f"{BASE}/stock-basic/list", status_code=401,
              json={"code": "1001", "message": "unauthorized", "traceId": "t"})
        with pytest.raises(AuthenticationError):
            make_client().request("GET", "/stock-basic/list")


def test_429_raises_rate_limit():
    with requests_mock.Mocker() as m:
        m.post(f"{BASE}/kline-daily/list", status_code=429, json={})
        with pytest.raises(RateLimitError):
            make_client().request("POST", "/kline-daily/list", json={})


def test_business_error_raises_api_error_with_trace():
    with requests_mock.Mocker() as m:
        m.post(f"{BASE}/kline-daily/list",
               json={"code": "1001", "message": "参数错误", "traceId": "abc"})
        with pytest.raises(ApiError) as ei:
            make_client().request("POST", "/kline-daily/list", json={})
        assert ei.value.code == "1001"
        assert ei.value.trace_id == "abc"


def test_connection_error_wrapped():
    with requests_mock.Mocker() as m:
        m.post(f"{BASE}/kline-daily/list", exc=requests.exceptions.ConnectionError)
        with pytest.raises(ConnectionError):
            make_client().request("POST", "/kline-daily/list", json={})
