# bihu-stock-data-client

Python 客户端 SDK，对接 stock-data-server 的 A 股数据 REST API。
专为人类用户与 AI 设计：显式方法名、完整类型注解、内置分页自动化。

## 安装

```bash
pip install bihu-stock-data-client
# 可选：启用 pandas 转换
pip install "bihu-stock-data-client[pandas]"
```

## 快速上手

```python
import bihu_stock_data_client as bsdc

client = bsdc.Client(api_key="你的 API Key")  # base_url 默认 localhost，可显式传入

# 单页查询（默认最多 1000 条）
rows = client.kline_daily(stock_code="000001", start_date="2025-01-01")
print(rows[0])            # {'stockCode':'000001','tradeDate':'2025-01-02','close':...}
print(rows.total_count)   # 总条数

# 自动全量（客户端自动翻页）
all_rows = client.kline_daily(stock_code="000001", start_date="2020-01-01", fetch_all=True)

# 转 pandas（需安装 pandas）
df = rows.to_pandas()
```

## 配置

| 参数 | 说明 | 环境变量 |
|---|---|---|
| `api_key` | API Key（经请求头 `X-API-Key` 透传） | `BIHU_STOCK_DATA_API_KEY` |
| `base_url` | 服务端地址，默认 `http://localhost:9800/stock/data` | `BIHU_STOCK_DATA_BASE_URL` |

> 注意：`StockDataClient` 实例非线程安全；多线程请每线程使用独立实例，或通过 `session=` 注入自定义 `requests.Session`。

## 支持的接口（26 个）

K线行情：`kline_daily`、`kline_daily_stat`、`kline_minute`、`kline_minute_snapshot`
指数：`index_basic`、`index_kline_daily`、`index_constituent`
股票基础：`stock_basic`；申万行业：`sw_industry`、`sw_stock_classify`、`sw_industry_daily_stat`、`sw_industry_capital_flow`
资金/成交：`capital_flow`、`block_trade`、`margin_trading`、`dragon_tiger`、`pre_post_market`
股本/股东：`share_capital`、`share_trade`、`shareholder_stats`、`institutional_holding`
财务/分红：`financial_report`、`dividend_factor`；统计：`stock_limit_up_stats`
交易日历：`trading_calendar`；实时快照：`stock_realtime`

## 分页

分页接口的 `pageNum`/`pageSize` 为服务端必填（`pageSize` 上限 1000）。SDK 提供三种用法：

- 默认取第一页：`client.kline_daily(stock_code="000001")`
- 手动翻页：`page_num=2, page_size=500`
- 自动全量：`fetch_all=True`（默认 `max_rows=1_000_000` 护栏，可调）

## 错误处理

所有异常继承 `bsdc.StockDataError`：`ConfigurationError`（未配置 API Key）、`AuthenticationError`（401）、`RateLimitError`（限流）、`ApiError`（业务错误，带 `code`/`trace_id`）、`PaginationLimitError`、`ConnectionError`、`ValidationError`。

## License

MIT
