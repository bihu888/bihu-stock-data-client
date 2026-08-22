# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概览

`bihu-stock-data-client` 是对接 `stock-data-server`（A 股数据 REST API）的 Python 客户端 SDK，对外暴露 28 个查询接口：显式方法名、完整类型注解、内置分页自动化。Python ≥ 3.10，src layout，hatchling 构建，依赖 `requests` + `python-dotenv`。另导出别名 `Client = StockDataClient`（设计文档用 `bsdc.Client(...)` 形式）。

实例**非线程安全**（内部共享单个 `requests.Session`）：多线程请每线程独立实例，或经 `session=` 注入自定义 Session。

## 常用命令

```bash
# 安装（[dev] = pytest / requests-mock / mypy / types-requests；[pandas] 启用 to_pandas）
pip install -e ".[dev]"

# 测试
python -m pytest                                          # 全量（集成测试默认 skip）
python -m pytest tests/unit tests/contract                # 仅离线测试
python -m pytest tests/unit/test_config.py::test_dotenv_loaded -q   # 单个测试

python -m mypy src                                        # 类型检查

# 真机集成测试（opt-in，需本地服务端 + 真实环境变量；无 key 时自动 skip）
python -m pytest tests/integration
```

> 注意：集成测试直接 `os.environ.get(...)` 读取，**不经过 `from_env()`**，因此必须设置真实环境变量，`.env` 对它无效。

## 架构

### 声明式注册表 + 门面方法（双写约束）
`registry.py` 的 `ENDPOINTS` 元组是全部接口的**单一事实来源**（method / path / params / 是否分页 / 路径参数）。`client.py` 的 `StockDataClient` 是门面，每个公开方法薄包装一次 `_call()`。

**新增一个接口必须同步改两处（最容易漏）**：
1. `registry.py`：加一条 `Endpoint(...)` 声明；
2. `client.py`：加公开方法；分页接口还要加对应的 `xxx_iter()` 流式方法。

公共调度逻辑集中在 `_call` / `_call_page` / `_call_all` / `_iter_pages`，新方法直接复用。客户端参数校验集中在 `_validate`：拒绝注册表之外的参数名、`quarter_type` 限 1~4、分页接口 `page_size` 限 1~1000（超限抛 `ValidationError`，不发请求）。

### 请求/响应的 case 契约（最容易出错）
分散在三处，改动编解码时务必同步并跑 `tests/contract/`：
- **对外 Python API**：snake_case（`stock_code`、`page_num`、`quarter_type`）；
- **发出的请求体键**：camelCase（`stockCode`、`pageNum`），由 `decoder.snake_to_camel` 在 `_call_page` 发送前转换；分页接口自动附加 `pageNum`/`pageSize`；GET 请求的查询参数同样走 camelCase（如 `market_transaction` 的 `max_count` → `?maxCount=N`），由 `_call_page` 的 GET 分支生成并经 `HttpClient.request(params=...)` 透传；
- **响应列式数据的列名**：snake_case 原样保留为字典键（`stock_code`、`trade_date`），decoder **不**转换。

### 列式响应解码（decoder.py）
服务端统一信封 `{code, message, data, traceId}`；`code != "0000"` → 抛 `ApiError`。`data` 为列式结构：
- 非分页：`{column: [...], item: [[...]]}` → `decode_columnar`；
- 分页：再含 `pageNum/pageSize/totalCount/totalPage` → `decode_columnar_page`。

`Records` 是 `list[dict]` 子类，额外携带 `.total_count/.total_pages/.page_num/.page_size`，并提供 `.to_pandas()`（依赖可选 `pandas`）。

### 分页
默认取第一页；`page_num=`/`page_size=` 手动翻页（`page_size` 上限 1000）；`fetch_all=True` 自动翻页，`max_rows`（默认 1_000_000）护栏超限抛 `PaginationLimitError`；分页接口另有 `xxx_iter()` 生成器逐页 yield，适合流式处理大数据集。

### 错误映射（transport.py）
所有异常继承 `StockDataError`（携带 `trace_id`）：HTTP 401→`AuthenticationError`、429→`RateLimitError`、其他非 2xx 或业务 code 错→`ApiError`、网络/超时→`ConnectionError`、参数校验→`ValidationError`、配置缺失→`ConfigurationError`。
- `ConnectionError` 是**包内自定义**，遮蔽内置同名异常，故 `errors.py` 标注 `# noqa: A001`。
- 传输层用 `requests.Session` + urllib3 `Retry`（对 429/5xx 退避重试，`backoff_factor=0.5`），鉴权经 `X-API-Key` 请求头。

### 配置（config.py）
`ClientConfig.from_env()` 是唯一构造入口（`StockDataClient.__init__` 也走它）。优先级：**显式参数 > 已有环境变量 > `.env`**。环境变量：`BIHU_STOCK_DATA_API_KEY`、`BIHU_STOCK_DATA_BASE_URL`（默认 `http://localhost:9800/stock/data`，即本地 Java 服务的 context-path）。
`.env` 由 `load_dotenv(find_dotenv(usecwd=True))` 在构造时从**当前工作目录**向上查找——库不能用默认的 `load_dotenv()`（其 `find_dotenv()` 默认 `usecwd=False`，会从库源码目录查找，永远找不到用户的 `.env`）。

## 测试约定
- `tests/unit/`：单元测试，用 `requests_mock.Mocker()` 桩掉 HTTP，不触网；
- `tests/contract/`：离线契约测试，样本贴近真实服务端，断言 case 契约与列式解码形状；
- `tests/integration/`：opt-in 真机测试，未设 `BIHU_STOCK_DATA_API_KEY` 时自动 skip。

更详细的接口设计与字段语义背景见 `docs/superpowers/specs/2026-06-23-bihu-stock-data-client-design.md`。
