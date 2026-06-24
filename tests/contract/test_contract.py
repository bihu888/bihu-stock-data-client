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
                "column": ["stockCode", "tradeDate", "open", "close"],
                "item": [["000001", "2025-01-02", 10.0, 10.5]],
                "pageNum": 1, "pageSize": 1000, "totalCount": 1, "totalPage": 1,
            }),
        )
        rows = client().kline_daily(stock_code="000001")
        assert rows[0]["tradeDate"] == "2025-01-02"
        assert rows[0]["close"] == 10.5
        assert rows.total_count == 1
        body = m.last_request.json()
        assert set(body.keys()) >= {"stockCode", "pageNum", "pageSize"}


def test_contract_report_style_with_quarter():
    """报告型分页：financial_report（reportYear/quarterType）。"""
    with requests_mock.Mocker() as m:
        m.post(
            f"{BASE}/financial-report/list",
            json=_envelope({
                "column": ["stockCode", "reportYear", "quarterType", "revenue"],
                "item": [["000001", 2024, 4, 1.2e9]],
                "pageNum": 1, "pageSize": 1000, "totalCount": 1, "totalPage": 1,
            }),
        )
        rows = client().financial_report(stock_code="000001", report_year=2024, quarter_type=4)
        assert rows[0]["revenue"] == 1.2e9
        body = m.last_request.json()
        assert body["reportYear"] == 2024
        assert body["quarterType"] == 4


def test_contract_index_date_range():
    """指数日期范围：index_kline_daily（indexCode）。"""
    with requests_mock.Mocker() as m:
        m.post(
            f"{BASE}/index-kline-daily/list",
            json=_envelope({
                "column": ["indexCode", "tradeDate", "close"],
                "item": [["000300", "2025-01-02", 4000.1]],
                "pageNum": 1, "pageSize": 1000, "totalCount": 1, "totalPage": 1,
            }),
        )
        rows = client().index_kline_daily(index_code="000300")
        assert rows[0]["indexCode"] == "000300"
        assert m.last_request.json()["indexCode"] == "000300"


def test_contract_sw_industry_capital_flow():
    """申万行业日期范围：sw_industry_capital_flow（industryCode）。"""
    with requests_mock.Mocker() as m:
        m.post(
            f"{BASE}/sw-industry-capital-flow/list",
            json=_envelope({
                "column": ["industryCode", "tradeDate", "netInflow"],
                "item": [["801010", "2025-01-02", -1.0e7]],
                "pageNum": 1, "pageSize": 1000, "totalCount": 1, "totalPage": 1,
            }),
        )
        rows = client().sw_industry_capital_flow(industry_code="801010")
        assert m.last_request.json()["industryCode"] == "801010"
        assert rows[0]["netInflow"] == -1.0e7


def test_contract_get_list_all_no_pagination():
    """GET 全量（不分页）：stock_basic，返回 ColumnarData 无分页字段。"""
    with requests_mock.Mocker() as m:
        m.get(
            f"{BASE}/stock-basic/list",
            json=_envelope({
                "column": ["stockCode", "stockName"],
                "item": [["000001", "平安银行"], ["600000", "浦发银行"]],
            }),
        )
        rows = client().stock_basic()
        assert len(rows) == 2
        assert rows[0]["stockName"] == "平安银行"
        assert rows.total_count is None
        assert m.last_request.method == "GET"


def test_contract_get_list_all_index_basic_no_pagination():
    """GET 全量（不分页）：index_basic，返回 ColumnarData 无分页字段。"""
    with requests_mock.Mocker() as m:
        m.get(
            f"{BASE}/index-basic/list",
            json=_envelope({
                "column": ["indexCode", "indexName"],
                "item": [["000300", "沪深300"], ["000905", "中证500"]],
            }),
        )
        rows = client().index_basic()
        assert len(rows) == 2
        assert rows[0]["indexName"] == "沪深300"
        assert rows.total_count is None
        assert m.last_request.method == "GET"


def test_contract_get_list_all_sw_industry_no_pagination():
    """GET 全量（不分页）：sw_industry，返回 ColumnarData 无分页字段。"""
    with requests_mock.Mocker() as m:
        m.get(
            f"{BASE}/sw-industry/list",
            json=_envelope({
                "column": ["industryCode", "industryName"],
                "item": [["801010", "农林牧渔"], ["801020", "采掘"]],
            }),
        )
        rows = client().sw_industry()
        assert len(rows) == 2
        assert rows[0]["industryName"] == "农林牧渔"
        assert rows.total_count is None
        assert m.last_request.method == "GET"


def test_contract_get_path_param():
    """GET 路径参数：kline_minute。"""
    with requests_mock.Mocker() as m:
        m.get(
            f"{BASE}/kline-minute/000001/2025-06-20",
            json=_envelope({
                "column": ["tradeTime", "price"],
                "item": [[93000, 10.5]],
            }),
        )
        rows = client().kline_minute(stock_code="000001", trade_date="2025-06-20")
        assert rows[0]["tradeTime"] == 93000


def test_contract_stock_realtime_memory_query():
    """POST 内存查询（不分页）：stock_realtime（stockCodes 数组）。"""
    with requests_mock.Mocker() as m:
        m.post(
            f"{BASE}/stock-realtime/list",
            json=_envelope({
                "column": ["stockCode", "lastPrice"],
                "item": [["000001", 10.5], ["600000", 9.8]],
            }),
        )
        rows = client().stock_realtime(stock_codes=["000001", "600000"])
        body = m.last_request.json()
        assert body["stockCodes"] == ["000001", "600000"]
        assert "pageNum" not in body
        assert rows.total_count is None
