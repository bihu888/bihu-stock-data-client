"""离线契约测试（requests-mock + 贴近服务端真实样本）。

约定（经真机验证）：
- 请求体键为 **camelCase**（stockCode / pageNum，服务端要求），客户端对外用 snake_case，
  发送前转换；本文件断言发出的请求体键。
- 响应列式数据的列名为 **snake_case**（stock_code / trade_date，服务端原样返回），
  客户端不做转换、原样保留为字典键；本文件断言解码后的字典键与值。
"""
import requests_mock

from bihu_stock_data_client import StockDataClient

BASE = "http://localhost:9800/stock/data"


def client():
    return StockDataClient(api_key="key", base_url=BASE, max_retries=0)


def _envelope(data):
    return {"code": "0000", "message": "成功", "data": data, "traceId": "trace-xyz"}


def test_contract_post_date_range_pagination_shape():
    """股票日期范围分页：kline_daily（含 totalCount/totalPage）。"""
    with requests_mock.Mocker() as m:
        m.post(
            f"{BASE}/kline-daily/list",
            json=_envelope({
                "column": ["stock_code", "trade_date", "open", "close"],
                "item": [["000001.SZ", "2025-01-02", 10.0, 10.5]],
                "pageNum": 1, "pageSize": 1000, "totalCount": 1, "totalPage": 1,
            }),
        )
        rows = client().kline_daily(stock_code="000001")
        assert rows[0]["trade_date"] == "2025-01-02"
        assert rows[0]["close"] == 10.5
        assert rows.total_count == 1
        body = m.last_request.json()
        assert set(body.keys()) >= {"stockCode", "pageNum", "pageSize"}


def test_contract_report_style_with_quarter():
    """报告型分页：financial_report（请求 reportYear/quarterType）。"""
    with requests_mock.Mocker() as m:
        m.post(
            f"{BASE}/financial-report/list",
            json=_envelope({
                "column": ["stock_code", "report_year", "quarter_type", "roe"],
                "item": [["000001.SZ", 2024, 4, 0.1234]],
                "pageNum": 1, "pageSize": 1000, "totalCount": 1, "totalPage": 1,
            }),
        )
        rows = client().financial_report(stock_code="000001", report_year=2024, quarter_type=4)
        assert rows[0]["roe"] == 0.1234
        body = m.last_request.json()
        assert body["reportYear"] == 2024
        assert body["quarterType"] == 4


def test_contract_index_date_range():
    """指数日期范围：index_kline_daily（请求 indexCode）。"""
    with requests_mock.Mocker() as m:
        m.post(
            f"{BASE}/index-kline-daily/list",
            json=_envelope({
                "column": ["index_code", "trade_date", "close"],
                "item": [["000300", "2025-01-02", 4000.1]],
                "pageNum": 1, "pageSize": 1000, "totalCount": 1, "totalPage": 1,
            }),
        )
        rows = client().index_kline_daily(index_code="000300")
        assert rows[0]["index_code"] == "000300"
        assert m.last_request.json()["indexCode"] == "000300"


def test_contract_sw_industry_capital_flow():
    """申万行业日期范围：sw_industry_capital_flow（请求 industryCode）。"""
    with requests_mock.Mocker() as m:
        m.post(
            f"{BASE}/sw-industry-capital-flow/list",
            json=_envelope({
                "column": ["industry_code", "trade_date", "net_inflow"],
                "item": [["801010", "2025-01-02", -1.0e7]],
                "pageNum": 1, "pageSize": 1000, "totalCount": 1, "totalPage": 1,
            }),
        )
        rows = client().sw_industry_capital_flow(industry_code="801010")
        assert m.last_request.json()["industryCode"] == "801010"
        assert rows[0]["net_inflow"] == -1.0e7


def test_contract_get_list_all_no_pagination():
    """GET 全量（不分页）：stock_basic，返回 ColumnarData 无分页字段。"""
    with requests_mock.Mocker() as m:
        m.get(
            f"{BASE}/stock-basic/list",
            json=_envelope({
                "column": ["stock_code", "stock_name"],
                "item": [["000001.SZ", "平安银行"], ["600000.SH", "浦发银行"]],
            }),
        )
        rows = client().stock_basic()
        assert len(rows) == 2
        assert rows[0]["stock_name"] == "平安银行"
        assert rows.total_count is None
        assert m.last_request.method == "GET"


def test_contract_get_list_all_index_basic_no_pagination():
    """GET 全量（不分页）：index_basic，返回 ColumnarData 无分页字段。"""
    with requests_mock.Mocker() as m:
        m.get(
            f"{BASE}/index-basic/list",
            json=_envelope({
                "column": ["index_code", "index_name"],
                "item": [["000300", "沪深300"], ["000905", "中证500"]],
            }),
        )
        rows = client().index_basic()
        assert len(rows) == 2
        assert rows[0]["index_name"] == "沪深300"
        assert rows.total_count is None
        assert m.last_request.method == "GET"


def test_contract_get_list_all_sw_industry_no_pagination():
    """GET 全量（不分页）：sw_industry，返回 ColumnarData 无分页字段。"""
    with requests_mock.Mocker() as m:
        m.get(
            f"{BASE}/sw-industry/list",
            json=_envelope({
                "column": ["industry_code", "industry_name"],
                "item": [["801010", "农林牧渔"], ["801020", "采掘"]],
            }),
        )
        rows = client().sw_industry()
        assert len(rows) == 2
        assert rows[0]["industry_name"] == "农林牧渔"
        assert rows.total_count is None
        assert m.last_request.method == "GET"


def test_contract_get_path_param():
    """GET 路径参数：kline_minute。"""
    with requests_mock.Mocker() as m:
        m.get(
            f"{BASE}/kline-minute/000001/2025-06-20",
            json=_envelope({
                "column": ["trade_time", "price"],
                "item": [[93000, 10.5]],
            }),
        )
        rows = client().kline_minute(stock_code="000001", trade_date="2025-06-20")
        assert rows[0]["trade_time"] == 93000


def test_contract_market_quote_get_columnar():
    """GET 路径参数 + 列式：market_quote（实时五档行情，单行）。"""
    with requests_mock.Mocker() as m:
        m.get(
            f"{BASE}/market/quote/000001",
            json=_envelope({
                "column": ["stock_code", "trade_time", "last_price", "ask_price1", "bid_price1"],
                "item": [["000001.SZ", "093100", 10.5, 10.51, 10.49]],
            }),
        )
        rows = client().market_quote(stock_code="000001")
        assert rows[0]["last_price"] == 10.5
        assert rows[0]["ask_price1"] == 10.51
        assert rows.total_count is None  # ColumnarData 无分页字段
        assert m.last_request.method == "GET"


def test_contract_market_kline_minute_get_columnar():
    """GET 路径参数 + 列式：market_kline_minute（当日分钟K线，多行）。"""
    with requests_mock.Mocker() as m:
        m.get(
            f"{BASE}/market/kline-minute/000001",
            json=_envelope({
                "column": ["stock_code", "trade_time", "open", "close", "volume", "amount"],
                "item": [
                    ["000001.SZ", "093100", 10.0, 10.1, 1000, 10100.0],
                    ["000001.SZ", "093200", 10.1, 10.2, 1500, 15300.0],
                ],
            }),
        )
        rows = client().market_kline_minute(stock_code="000001")
        assert len(rows) == 2
        assert rows[1]["close"] == 10.2
        assert m.last_request.method == "GET"


def test_contract_market_transaction_query_param():
    """GET 路径参数 + 查询参数（camelCase）+ 列式：market_transaction（当日分笔成交）。"""
    with requests_mock.Mocker() as m:
        m.get(
            f"{BASE}/market/transaction/000001",
            json=_envelope({
                "column": ["stock_code", "trade_time", "price", "volume", "num", "direction"],
                "item": [["000001.SZ", "093015", 10.5, 100, 1, 0]],
            }),
        )
        rows = client().market_transaction(stock_code="000001", max_count=8000)
        assert rows[0]["direction"] == 0
        assert m.last_request.method == "GET"
        assert "maxCount=8000" in m.last_request.url


def test_contract_chip_distribution():
    """筹码分布分页：chip_distribution（单股价格-成交量分布快照）。"""
    with requests_mock.Mocker() as m:
        m.post(
            f"{BASE}/chip-distribution/list",
            json=_envelope({
                "column": ["stock_code", "price", "volume", "last_date"],
                "item": [
                    ["600519.SH", "1308.0000", "7583960.78", "2026-08-13"],
                    ["600519.SH", "1308.0100", "10234.00", "2026-08-13"],
                ],
                "pageNum": 1, "pageSize": 50, "totalCount": 2, "totalPage": 1,
            }),
        )
        rows = client().chip_distribution(stock_code="600519.SH", min_price="1300", max_price="1320")
        assert rows[0]["price"] == "1308.0000"
        assert rows[0]["volume"] == "7583960.78"
        assert rows[0]["last_date"] == "2026-08-13"
        assert rows.total_count == 2
        body = m.last_request.json()
        assert body["stockCode"] == "600519.SH"
        assert body["minPrice"] == "1300"
        assert body["maxPrice"] == "1320"
        assert set(body.keys()) >= {"stockCode", "pageNum", "pageSize"}
