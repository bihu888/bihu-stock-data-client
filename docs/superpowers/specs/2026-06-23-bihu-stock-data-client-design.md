# bihu-stock-data-client 设计文档

- **日期**：2026-06-23
- **状态**：草案，待评审
- **目标产物**：开源 Python 客户端 SDK，对接 `stock-data-server` 提供的 A 股数据 REST API
- **受众**：普通开发者、数据分析人员、AI / LLM Agent

---

## 1. 背景与目标

`stock-data-server`（Java / Spring Boot，context-path `/stock/data`，默认端口 9800）已提供约 30 个 A 股数据查询接口，返回统一的 `ResponseParam` 信封与列式（columnar）数据格式。本项目为其开发一个 **Python 客户端**，提交到 GitHub 开源，供人类用户和 AI 使用。

**核心目标**：

1. **接口简单易用** —— 几行代码即可取数，分页等复杂度由客户端承担。
2. **对 AI 友好** —— 显式方法名、完整类型注解、富含中文语义的 docstring，便于 LLM 发现与调用。
3. **极简依赖** —— 仅依赖 `requests`，`pandas` 按需。
4. **可维护** —— 用声明式接口注册表让 ~26 个接口的实现高度复用，新增接口只加一行表项。

---

## 2. 范围

### 2.1 v1 包含

- 全部数据查询接口（GET 全量、GET 单点、POST 分页、POST 内存快照查询），共 **26 个方法**。
- API Key 认证（仅请求头 `X-API-Key`）。
- 列式数据 → `list[dict]` 解码，分页元信息随返回值携带。
- 自动分页（`fetch_all`）、可选惰性迭代器、可选 `pandas` 转换。
- 完整异常层次、可选重试、标准库日志。

### 2.2 v1 不包含（留待后续版本）

- 实时 WebSocket 行情订阅（`/realtime/*` 桥接快照接口、WebSocket 推送）。
- 登录与账号管理流程（短信 / 密码 / 微信登录、API Key 的增删查）。
  - 用户通过其它途径（控制台 / 手动）取得 API Key 后，传入 SDK 使用。
- 异步（async）客户端。

### 2.3 假设与约束

- 服务端可达，地址由用户通过 `base_url` 指定（默认 `http://localhost:9800/stock/data`，便于本地联调，线上部署时显式覆盖）。
- 用户已持有有效的 API Key。
- Python 3.10+。

---

## 3. 服务端契约（设计依据）

以下事实来自服务端 `AuthFilter`、`UserConstants` 与 OpenAPI 规范（`/stock/data/v3/api-docs`），客户端必须严格遵循。

### 3.1 认证

| 方式 | 传输 | 说明 |
|---|---|---|
| API Key | 请求头 `X-API-Key` | **客户端唯一支持的方式**；客户端不做前缀假设，原样透传用户提供的 Key |
| JWT | 请求头 `Authorization` | 仅服务端登录用，客户端 v1 不涉及 |

公开路径（无需认证）：`/auth/*` 登录类、Swagger / Knife4j 文档、`/stock-realtime/receive`（crawler 内部推送）。客户端使用的查询接口**均需认证**。

### 3.2 统一响应信封 `ResponseParam<T>`

```json
{ "code": "0000", "message": "成功", "data": <T>, "traceId": "..." }
```

- `code` 为字符串：`"0000"` = 成功，其它（如 `"1001"`）= 业务失败。
- HTTP 状态码：业务失败通常仍为 200（`code != "0000"`）；认证失败为 **401**。
- `traceId` 用于服务端排障，客户端异常中应保留。

### 3.3 数据格式

- **列式 `ColumnarData`**：`{ "column": ["stockCode", ...], "item": [["000001", ...], ...] }`
  - `column` 为列名列表；`item` 为行列表，每行是与 `column` 一一对应的值数组。
- **分页 `ColumnarPageData`**：在 `ColumnarData` 基础上增加 `pageNum` / `pageSize` / `totalCount` / `totalPage`。
- 单页 `pageSize` 上限 **1000**。

### 3.4 字段命名

服务端**请求体**字段使用 **camelCase**：`stockCode`、`startDate`、`endDate`、`pageNum`、`pageSize`、`indexCode`、`industryCode`、`reportYear`、`quarterType`；**响应列式数据的列名**为 **snake_case**（如 `stock_code`、`trade_date`、`close`），客户端原样保留为字典键、不做转换。

- `quarterType` 枚举：`1`=一季报、`2`=年中报、`3`=三季报、`4`=年报。
- 日期统一为 `yyyy-MM-dd` 字符串。

---

## 4. 项目结构与打包

**包名**

- 分发名（PyPI）：`bihu-stock-data-client`
- 导入名：`bihu_stock_data_client`
- 示例约定：`import bihu_stock_data_client as bsdc`

**目录结构**（`src/` 布局）

```
bihu-stock-data-client/
├── pyproject.toml              # hatchling 构建 + 元数据 + 依赖
├── README.md
├── LICENSE                     # MIT
├── CHANGELOG.md
├── src/bihu_stock_data_client/
│   ├── __init__.py             # 导出 Client、Records、全部异常、__version__
│   ├── client.py               # StockDataClient 门面
│   ├── registry.py             # 声明式接口注册表
│   ├── transport.py            # HTTP 会话：鉴权、重试、解包 ResponseParam
│   ├── decoder.py              # 列式解码、snake/camel、Records 类型
│   ├── errors.py               # 异常层次
│   └── config.py               # ClientConfig + 环境变量读取
├── tests/
│   ├── unit/                   # 单元测试
│   ├── contract/               # 契约测试（requests-mock 打桩）
│   └── integration/            # opt-in 真机集成测试
└── examples/                   # 快速上手脚本
```

**依赖**

- 硬依赖：`requests`
- 可选依赖：`pandas`（仅调用 `.to_pandas()` 时惰性导入，未安装则抛出友好错误）
- 开发依赖：`pytest`、`requests-mock`、`mypy`

**构建后端**：`hatchling`

**Python 版本**：3.10+

**开源协议**：MIT

---

## 5. 配置与初始化

```python
import bihu_stock_data_client as bsdc

client = bsdc.Client(
    api_key="你的 API Key",                       # 必填，或由环境变量提供
    base_url="http://localhost:9800/stock/data",  # 默认即此值
    timeout=30,                                    # 单请求超时（秒）
    max_retries=2,                                 # 瞬时错误重试次数
)
```

**环境变量兜底**（方便脚本 / CI 不硬编码）：

- `BIHU_STOCK_DATA_API_KEY` → `api_key`
- `BIHU_STOCK_DATA_BASE_URL` → `base_url`

参数优先级：显式传参 > 环境变量 > 默认值。

`ClientConfig` 用 `@dataclass(frozen=True)` 表达；构造时校验 `api_key` 非空（缺失抛 `ConfigurationError`）。

---

## 6. 核心架构

### 6.1 组件职责

| 组件 | 职责 |
|---|---|
| `config.ClientConfig` | 不可变配置 + 环境变量解析 + 基本校验 |
| `transport.HttpClient` | 持有 `requests.Session`；注入 `X-API-Key`；按 `max_retries` 做指数退避重试；解析 `ResponseParam`，失败转异常 |
| `registry.ENDPOINTS` | 声明式接口表，每接口一行：方法名 / HTTP 方法 / 路径 / 参数键 / 是否分页 / 是否路径参数 / 中文摘要 |
| `decoder` | 列式 → `list[dict]`；`snake_case` ↔ `camelCase`；`Records` 类型 |
| `client.StockDataClient` | 门面：读注册表，为每个接口动态生成显式方法（含签名与 docstring），串联上述组件、实现分页 |
| `errors` | 异常层次（见 §10） |

### 6.2 声明式接口注册表

```python
# registry.py
from enum import Enum

class Method(Enum):
    GET = "GET"
    POST = "POST"

@dataclass(frozen=True)
class Endpoint:
    name: str            # 方法名，如 "kline_daily"
    method: Method
    path: str            # 如 "/kline-daily/list"
    params: tuple[str, ...] = ()      # 业务参数（snake_case），如 ("stock_code", "start_date", "end_date")
    paginated: bool = False           # 是否分页接口
    path_params: tuple[str, ...] = () # 路径参数，如 ("stock_code", "trade_date")
    summary: str = ""                 # 中文摘要，写入 docstring

ENDPOINTS = [
    Endpoint("kline_daily", Method.POST, "/kline-daily/list",
             params=("stock_code", "start_date", "end_date"),
             paginated=True, summary="日K线行情"),
    Endpoint("financial_report", Method.POST, "/financial-report/list",
             params=("stock_code", "report_year", "quarter_type"),
             paginated=True, summary="财务报告"),
    Endpoint("stock_basic", Method.GET, "/stock-basic/list",
             summary="所有股票基本信息"),
    Endpoint("kline_minute", Method.GET, "/kline-minute/{stock_code}/{trade_date}",
             path_params=("stock_code", "trade_date"), summary="按股票+日期查分钟K线"),
    # ... 其余接口
]
```

`StockDataClient` 在 `__init__` 中遍历 `ENDPOINTS`，为每个 `Endpoint` 动态绑定一个方法。新增接口只需在表里加一行。

### 6.3 snake_case ↔ camelCase 约定

- 对外暴露 Python 风格 `snake_case`（`stock_code`、`start_date`、`page_num`）。
- 发送 JSON 请求体前，键名转回 `camelCase`（`stockCode`、`startDate`、`pageNum`）。
- 解码列式数据时，**保留服务端原始列名**作为字典键（本服务端列名为 `snake_case`，如 `stock_code`、`trade_date`；与服务端字段一致，避免双向映射歧义；用户取值 `row["close"]`、`row["stock_code"]`）。

### 6.4 数据流（一次调用）

```
client.kline_daily(stock_code="000001", start_date="2025-01-01")
  │ ① 校验参数 → 组装请求体：
  │     {stock_code,start_date} → camelCase {stockCode,startDate}
  │     分页接口追加 {pageNum, pageSize}（默认 1 / 1000）
  │ ② transport：POST {base_url}/kline-daily/list
  │     请求头 X-API-Key；失败按 max_retries 指数退避重试
  │ ③ 解包 ResponseParam：
  │     HTTP 非 2xx / 401 / 限流 → 对应异常
  │     code != "0000" → ApiError（携带 code/message/traceId）
  │ ④ decoder：ColumnarPageData{column,item,totalCount,...}
  │     → Records（list[dict] + 分页元信息）
  ▼
返回 Records
```

### 6.5 Records 返回类型

`Records` 是 `list` 的子类，**手感等同于 `list[dict]`**，同时携带分页元信息与可选 pandas 转换：

```python
rows = client.kline_daily(stock_code="000001", start_date="2025-01-01")

rows[0]            # {'stockCode':'000001','tradeDate':'2025-01-02','close':10.5,...}
len(rows)          # 本页行数
for r in rows: ... # 可迭代
rows.total_count   # 服务端总条数（不分页接口为 None）
rows.total_pages   # 总页数（不分页接口为 None）
rows.page_num      # 当前页码
rows.page_size
rows.to_pandas()   # 惰性导入 pandas 转 DataFrame；未安装抛带安装提示的 ImportError
repr(rows)         # Records(42 rows, page 1/1)
```

非分页接口返回的 `Records` 没有 `total_count` / `total_pages`（为 `None`）。

---

## 7. 分页模型

服务端分页接口的 `pageNum` / `pageSize` 为必填。客户端把它们作为方法签名的**可选参数**（带默认值），用户零成本取第一页，并提供三种进阶用法。

以 `kline_daily` 为例，生成的方法签名：

```python
def kline_daily(self, *,
                stock_code: str | None = None,
                start_date: str | None = None,
                end_date: str | None = None,
                page_num: int = 1,
                page_size: int = 1000,
                fetch_all: bool = False) -> Records: ...
```

### 7.1 四种用法

**① 默认取第一页**（不传分页参数；`page_size` 默认 1000，取满单页上限）

```python
rows = client.kline_daily(stock_code="000001", start_date="2025-01-01")
rows.total_count   # 判断要不要翻页
```

**② 手动翻页**（显式传 `page_num` / `page_size`）

```python
p1 = client.kline_daily(stock_code="000001", start_date="2020-01-01", page_size=500, page_num=1)
p2 = client.kline_daily(stock_code="000001", start_date="2020-01-01", page_size=500, page_num=2)
```

**③ 自动全量**（`fetch_all=True`，客户端按 `total_page` 自动翻到底，合并返回）

```python
all_rows = client.kline_daily(stock_code="000001", start_date="2020-01-01", fetch_all=True)
len(all_rows) == all_rows.total_count   # True
```

**④ 惰性迭代器**（每页 `yield` 一个 `Records`，适合超大数据集）

```python
for page in client.kline_daily_iter(stock_code="000001", start_date="2010-01-01", page_size=1000):
    process(page)
```

### 7.2 行为与护栏

- `fetch_all=True` 时忽略 `page_num`（固定从第 1 页翻到底），尊重 `page_size`。
- **`max_rows` 护栏**：`fetch_all` 与迭代器接受可选 `max_rows`（默认 1,000,000）。累计行数超过即抛 `PaginationLimitError`，提示用户显式调高，避免误触全表拉爆服务端。
- 不分页接口（`stock_basic` 等）没有 `page_*` / `fetch_all` 参数，一次返回全部。

---

## 8. 接口目录（v1，26 个方法）

命名规则：路径转蛇形（`/kline-daily/list` → `kline_daily`）；路径参数进签名（`/kline-minute/{stockCode}/{tradeDate}` → `kline_minute(stock_code, trade_date)`）。下表按领域分组（仅用于文档，方法本身扁平）。

| 领域 | 方法 | 关键参数 |
|---|---|---|
| K线行情 | `kline_daily` | stock_code, start_date, end_date |
|  | `kline_daily_stat` | stock_code, start_date, end_date |
|  | `kline_minute` | stock_code, trade_date（GET 单点） |
|  | `kline_minute_snapshot` | stock_code |
| 指数 | `index_basic` | （GET 全量） |
|  | `index_kline_daily` | index_code, start_date, end_date |
|  | `index_constituent` | index_code, stock_code |
| 股票基础 | `stock_basic` | （GET 全量） |
| 申万行业 | `sw_industry` | （GET 全量） |
|  | `sw_stock_classify` | stock_code |
|  | `sw_industry_daily_stat` | industry_code, start_date, end_date |
|  | `sw_industry_capital_flow` | industry_code, start_date, end_date |
| 资金 / 成交 | `capital_flow` | stock_code, start_date, end_date |
|  | `block_trade` | stock_code, start_date, end_date |
|  | `margin_trading` | stock_code, start_date, end_date |
|  | `dragon_tiger` | stock_code, start_date, end_date |
|  | `pre_post_market` | stock_code, start_date, end_date |
| 股本 / 股东 | `share_capital` | stock_code, start_date, end_date |
|  | `share_trade` | stock_code, start_date, end_date |
|  | `shareholder_stats` | stock_code, report_year, quarter_type |
|  | `institutional_holding` | stock_code, report_year, quarter_type |
| 财务 / 分红 | `financial_report` | stock_code, report_year, quarter_type |
|  | `dividend_factor` | stock_code, start_date, end_date |
| 统计 | `stock_limit_up_stats` | stock_code, start_date, end_date |
| 交易日历 | `trading_calendar` | start_date, end_date |
| 实时快照 | `stock_realtime` | stock_codes（列表，空则全部；POST 内存查询，不分页） |

> 上表由 OpenAPI 规范推导。`quarter_type` 用 `Literal[1,2,3,4]` 类型提示并在 docstring 注明含义。`TickL1Controller` 等未出现在规范中的接口暂不纳入；实现期若发现遗漏的查询接口，往注册表加一行即可。

---

## 9. 公开 API 速览

```python
import bihu_stock_data_client as bsdc

client = bsdc.Client(api_key="你的 API Key")

client.kline_daily(stock_code="000001", start_date="2025-01-01")
client.kline_daily(stock_code="000001", start_date="2020-01-01", fetch_all=True)
client.financial_report(stock_code="000001", report_year=2024, quarter_type=4)
client.kline_minute(stock_code="000001", trade_date="2025-06-20")
client.stock_basic()
client.stock_realtime(stock_codes=["000001", "600000"])

rows = client.kline_daily(stock_code="000001", start_date="2025-01-01")
df = rows.to_pandas()
```

---

## 10. 错误处理

### 10.1 异常层次

```
StockDataError                        # 基类；均携带 .trace_id（服务端有返回时）
├── ConfigurationError                # 初始化配置缺失（如无 api_key）
├── AuthenticationError               # 401：API Key 无效 / 失效
├── RateLimitError                    # 触发限流（服务端 RateLimitFilter）
├── ApiError                          # HTTP 非 2xx 或 code != "0000"
│                                     #   携带 .code / .message / .status / .trace_id
├── PaginationLimitError              # fetch_all / 迭代器超过 max_rows 护栏
├── ConnectionError                   # 网络 / 超时（包装 requests 异常）
└── ValidationError                   # 客户端轻校验（如 quarter_type 越界）
```

### 10.2 映射规则

- `requests` 超时 / 连接失败 → `ConnectionError`
- HTTP 401 → `AuthenticationError`（错误信息明示"检查 API Key"）
- 触发限流（HTTP 429 或服务端限流码）→ `RateLimitError`
- 其它非 2xx，或 2xx 但 `code != "0000"` → `ApiError`（携带服务端 `code` / `message` / `traceId`）
- 客户端仅做极少量校验（`quarter_type ∈ {1,2,3,4}`、日期格式、`page_size ≤ 1000` 等），其余交给服务端，避免与服务端规则脱节。

### 10.3 重试

- 仅对**瞬时错误**重试：网络错误、超时、HTTP 5xx、`RateLimitError`。
- 指数退避；次数由 `max_retries` 控制（默认 2）；`RateLimitError` 重试时遵从更长退避。
- 业务错误（`code != "0000"`）、`AuthenticationError`、`ValidationError` **不重试**。

### 10.4 日志

- 使用标准库 `logging`，logger 名 `bihu_stock_data_client`。
- DEBUG 级别输出请求方法 / 路径 / 状态码（不输出 api_key 明文）。

---

## 11. 测试

| 层 | 内容 | 工具 |
|---|---|---|
| 单元测试 | 列式解码、snake↔camel、分页数学（`fetch_all` 翻页循环）、`Records` 行为、异常映射、`max_rows` 护栏、重试策略 | pytest |
| 契约测试（离线） | 用 `requests-mock` 打桩，按**真实服务端响应样本**逐接口验证请求体 / 响应解码；每种请求 schema 至少一例 + 若干真实样本 | pytest + requests-mock |
| 集成测试（opt-in） | 直连本地运行的服务端真跑，端到端验证 | pytest 标记 `@pytest.mark.integration`；无 key / 服务未启动自动 skip |

契约测试是关键防线：保证客户端对列式格式与 `ResponseParam` 的解析与服务端实际输出严格一致，不依赖服务端在线。

**质量门禁**：全量类型注解，`mypy` 干净。

---

## 12. 文档与示例

- `README.md`：30 秒上手（安装、初始化、第一个查询、`fetch_all`、`to_pandas`、错误处理）。
- `examples/`：单股日K全量拉取、财务报告查询、`to_pandas` 落地分析、错误处理示例。
- 注册表生成的每个方法自带 docstring（中文摘要 + 参数说明 + 对应路径），`dir(client)` / 自动补全即可发现。
- `CHANGELOG.md` 记录版本变更。

---

## 13. 关键设计决策小结

| 决策点 | 选择 | 理由 |
|---|---|---|
| 返回形式 | `list[dict]`（`Records`）+ 可选 `.to_pandas()` | 零强制依赖、对人和 AI 最友好；量化用户按需启用 pandas |
| 范围 | v1 仅 REST 查询 | 先交付核心价值，实时 / 登录留后续 |
| 认证 | 仅 API Key | 程序 / AI 用的主力方式，范围最小最简单 |
| 同步模型 | 同步（`requests`） | 简单易用 |
| API 风格 | 扁平显式方法 + 声明式注册表 | 自动补全 + docstring 最强；实现 DRY 易维护 |
| 分页 | 默认首页 + 手动翻页 + `fetch_all` + 迭代器 + `max_rows` 护栏 | 零成本起步，复杂度由客户端承担，且有防呆 |
| 列字典键 | 保留服务端 snake_case 原始列名 | 与服务端字段一致，避免双向映射歧义 |
| Python 版本 | 3.10+ | 3.9 已 EOL |
| 协议 | MIT | 宽松、流行 |

---

## 14. 后续（非 v1）

- 实时 WebSocket 行情订阅（`/realtime/*` 快照、推送流），将引入 `async` + `websockets` 依赖。
- 登录与 API Key 管理（短信 / 密码 / 微信登录，Key 增删查）。
- 异步客户端（`httpx.AsyncClient`）。
- 由 OpenAPI 规范自动生成注册表（进一步降低维护成本）。
