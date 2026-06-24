"""opt-in 真机集成测试：需本地运行的服务端 + 环境变量 BIHU_STOCK_DATA_API_KEY。

运行: pytest -m integration
未配置时自动跳过。
"""
import os

import pytest

API_KEY = os.environ.get("BIHU_STOCK_DATA_API_KEY")
BASE_URL = os.environ.get("BIHU_STOCK_DATA_BASE_URL", "http://localhost:9800/stock/data")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not API_KEY, reason="未设置 BIHU_STOCK_DATA_API_KEY，跳过集成测试"
    ),
]


@pytest.fixture(scope="module")
def client():
    from bihu_stock_data_client import StockDataClient

    return StockDataClient(api_key=API_KEY, base_url=BASE_URL)


def test_stock_basic(client):
    rows = client.stock_basic()
    assert len(rows) > 0
    assert "stockCode" in rows[0]


def test_kline_daily_single_page(client):
    rows = client.kline_daily(stock_code="000001", page_size=10)
    assert rows.total_count is not None


def test_trading_calendar(client):
    rows = client.trading_calendar(start_date="2025-01-01", end_date="2025-01-31", page_size=10)
    assert rows.total_count is not None
