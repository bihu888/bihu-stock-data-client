# bihu-stock-data-client

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

[壁虎量化](https://stock.bihu.cn) A 股数据服务的官方 Python SDK：28 个数据查询接口，显式方法名、完整类型注解、内置分页自动化，同为人类用户与 AI 助手设计。

## 特性

- **28 个数据接口**：日K/分钟K、指数、申万行业、资金流、龙虎榜、财务报告、股东与股本、筹码分布、实时行情等
- **分页自动化**：`fetch_all=True` 自动翻页全量拉取，`max_rows` 护栏防止失控；每个分页接口另有 `xxx_iter()` 生成器，逐页流式处理大数据集
- **列式数据自动解码**：服务端 `{column, item}` 列式响应解码为 `Records`（`list[dict]` 子类，手感同普通列表，附带 `total_count` 等分页元信息，可一键 `to_pandas()`）
- **三级配置**：显式参数 > 已有环境变量 > `.env` 文件
- **完善的异常层次**：所有异常携带 `trace_id`，可直接反馈给服务方定位问题
- **传输层自动重试**：429/5xx 指数退避重试；API Key 经 `X-API-Key` 请求头鉴权

## 安装

要求 Python ≥ 3.10。

```bash
pip install "bihu-stock-data-client @ git+https://github.com/<ORG>/bihu-stock-data-client.git"

# 启用 pandas 转换（可选）
pip install "bihu-stock-data-client[pandas] @ git+https://github.com/<ORG>/bihu-stock-data-client.git"
```

> 将 `<ORG>` 替换为实际的 GitHub 组织/用户名。

### 从源码安装

```bash
git clone https://github.com/<ORG>/bihu-stock-data-client.git
cd bihu-stock-data-client
pip install -e ".[dev]"   # dev = pytest / requests-mock / mypy 等开发依赖
```

## 快速上手

```python
import bihu_stock_data_client as bsdc

client = bsdc.Client(api_key="你的 API Key")  # base_url 默认本地服务，可显式传入

# 单页查询（默认第 1 页、每页最多 1000 条）
rows = client.kline_daily(stock_code="000001.SZ", start_date="2025-01-01")
print(rows[0])            # {'stock_code': '000001.SZ', 'trade_date': '2025-01-02', 'close': ...}
print(rows.total_count)   # 符合条件的总条数

# 自动全量（客户端自动翻页）
all_rows = client.kline_daily(stock_code="000001.SZ", start_date="2020-01-01", fetch_all=True)

# 转 pandas（需安装 [pandas] extra）
df = rows.to_pandas()
```

## 配置

| 参数 | 说明 | 环境变量 | 默认值 |
|---|---|---|---|
| `api_key` | API Key，经请求头 `X-API-Key` 透传 | `BIHU_STOCK_DATA_API_KEY` | 无（必填） |
| `base_url` | 服务端地址 | `BIHU_STOCK_DATA_BASE_URL` | `http://localhost:9800/stock/data` |
| `timeout` | 单次请求超时（秒） | — | `30` |
| `max_retries` | 429/5xx 自动重试次数 | — | `2` |

API Key 与服务地址由服务提供方分配，请前往 [壁虎量化](https://stock.bihu.cn) 获取。

以上环境变量也可写入项目根目录的 `.env` 文件，客户端构造时自动加载（依赖 `python-dotenv`）；**已存在的环境变量优先级更高**。可参考仓库内的 [`.env.example`](.env.example)。

> 注意：`StockDataClient` 实例非线程安全（内部共享一个 `requests.Session`）；多线程请每线程使用独立实例，或通过 `session=` 注入自定义 Session。

## 接口一览

共 28 个查询方法。筛选参数均可选（标注"必填"的除外）；日期格式 `yyyy-MM-dd`；`quarter_type`：1=一季报、2=年中报、3=三季报、4=年报。所有分页接口都有对应的 `xxx_iter()` 流式方法（如 `kline_daily_iter`）。

### K线行情

| 方法 | 说明 | 筛选参数 | 分页 |
|---|---|---|:---:|
| `kline_daily` | 日K线行情 | `stock_code`、`start_date`、`end_date` | ✔ |
| `kline_daily_stat` | 每日统计指标 | 同上 | ✔ |
| `kline_minute` | 按股票+日期查分钟K线 | `stock_code`、`trade_date`（路径参数） | — |

### 指数

| 方法 | 说明 | 筛选参数 | 分页 |
|---|---|---|:---:|
| `index_basic` | 所有指数基础信息 | — | — |
| `index_kline_daily` | 指数日K线 | `index_code`、`start_date`、`end_date` | ✔ |
| `index_constituent` | 指数成分股 | `index_code`、`stock_code` | ✔ |

### 股票与行业基础

| 方法 | 说明 | 筛选参数 | 分页 |
|---|---|---|:---:|
| `stock_basic` | 所有股票基本信息 | — | — |
| `sw_industry` | 所有申万行业分类 | — | — |
| `sw_stock_classify` | 个股申万行业归属 | `stock_code` | ✔ |

### 申万行业数据

| 方法 | 说明 | 筛选参数 | 分页 |
|---|---|---|:---:|
| `sw_industry_daily_stat` | 申万行业日度统计 | `industry_code`、`start_date`、`end_date` | ✔ |
| `sw_industry_capital_flow` | 申万行业资金流 | 同上 | ✔ |

### 资金与成交

| 方法 | 说明 | 筛选参数 | 分页 |
|---|---|---|:---:|
| `capital_flow` | 资金流向 | `stock_code`、`start_date`、`end_date` | ✔ |
| `block_trade` | 大宗交易 | 同上 | ✔ |
| `margin_trading` | 融资融券 | 同上 | ✔ |
| `dragon_tiger` | 龙虎榜 | 同上 | ✔ |
| `pre_post_market` | 盘前盘后成交 | 同上 | ✔ |

### 筹码

| 方法 | 说明 | 筛选参数 | 分页 |
|---|---|---|:---:|
| `chip_distribution` | 筹码分布（单股各价格档累计成交量快照） | `stock_code`（必填）、`min_price`、`max_price` | ✔ |

### 股本与股东

| 方法 | 说明 | 筛选参数 | 分页 |
|---|---|---|:---:|
| `share_capital` | 股本数据 | `stock_code`、`start_date`、`end_date` | ✔ |
| `share_trade` | 增减持 | 同上 | ✔ |
| `shareholder_stats` | 股东统计 | `stock_code`、`report_year`、`quarter_type` | ✔ |
| `institutional_holding` | 机构持股 | 同上 | ✔ |

### 财务与分红

| 方法 | 说明 | 筛选参数 | 分页 |
|---|---|---|:---:|
| `financial_report` | 财务报告 | `stock_code`、`report_year`、`quarter_type` | ✔ |
| `dividend_factor` | 分红配送 | `stock_code`、`start_date`、`end_date` | ✔ |

### 统计与日历

| 方法 | 说明 | 筛选参数 | 分页 |
|---|---|---|:---:|
| `stock_limit_up_stats` | 涨跌停统计 | `stock_code`、`start_date`、`end_date` | ✔ |
| `trading_calendar` | 交易日历 | `start_date`、`end_date` | ✔ |

### 实时行情（当日数据）

| 方法 | 说明 | 筛选参数 | 分页 |
|---|---|---|:---:|
| `market_quote` | 实时五档行情快照 | `stock_code`（路径参数，必填） | — |
| `market_kline_minute` | 当日分钟K线（1分钟 OHLC） | `stock_code`（路径参数，必填） | — |
| `market_transaction` | 当日分笔成交（Tick） | `stock_code`（路径参数，必填）、`max_count`（默认 8000，上限 50000） | — |

## 分页与流式

分页接口的 `pageNum`/`pageSize` 为服务端必填（`pageSize` 上限 1000），SDK 提供四种用法：

```python
# 1. 默认取第一页（page_num=1, page_size=1000）
rows = client.kline_daily(stock_code="000001.SZ")

# 2. 手动翻页
rows = client.kline_daily(stock_code="000001.SZ", page_num=2, page_size=500)

# 3. 自动全量：fetch_all=True，max_rows 护栏（默认 1_000_000）超限抛 PaginationLimitError
all_rows = client.kline_daily(stock_code="000001.SZ", start_date="2020-01-01",
                              fetch_all=True, max_rows=5_000_000)

# 4. 流式逐页（生成器，适合大数据集省内存）
for page in client.kline_daily_iter(stock_code="000001.SZ", start_date="2020-01-01"):
    ...  # 处理这一页，page 也是 Records
```

## 错误处理

所有异常继承 `bsdc.StockDataError`：

| 异常 | 触发条件 |
|---|---|
| `ConfigurationError` | 未提供 api_key |
| `ValidationError` | 客户端参数校验失败（不支持的参数名、`quarter_type` 非 1~4、`page_size` 越界） |
| `AuthenticationError` | HTTP 401，API Key 无效/失效 |
| `RateLimitError` | HTTP 429，触发服务端限流 |
| `ApiError` | 服务端业务错误（`code != "0000"`）或其他非 2xx，携带 `code`/`status`/`trace_id` |
| `PaginationLimitError` | `fetch_all` 结果超过 `max_rows` 护栏 |
| `ConnectionError` | 网络/超时错误（包内自定义异常，包装 requests 异常） |

```python
try:
    rows = client.kline_daily(stock_code="000001.SZ")
except bsdc.ApiError as e:
    print(f"服务端错误: {e.message}")  # e.code / e.status / e.trace_id 可直接反馈给服务方排查
except bsdc.StockDataError as e:
    print(f"其他错误: {e.message}")
```

## 更多示例

- [`examples/quickstart.py`](examples/quickstart.py)：单页查询、自动全量、错误处理
- [`examples/fetch_all_and_pandas.py`](examples/fetch_all_and_pandas.py)：自动全量拉取 + 转 pandas

## License

MIT
