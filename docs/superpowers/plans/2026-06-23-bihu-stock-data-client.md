# bihu-stock-data-client Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个开源 Python 客户端 SDK，对接 `stock-data-server` 的 A 股数据 REST API，供人类用户与 AI 使用。

**Architecture:** 分层 SDK：`config`（配置）→ `registry`（声明式接口表，单一事实来源）→ `transport`（HTTP 会话 + 鉴权 + 重试 + 解包 `ResponseParam`）→ `decoder`（列式→`list[dict]`、snake/camel、`Records`）→ `client`（门面，26 个显式类型方法委托给注册表驱动的私有 `_call`）。返回 `Records`（`list[dict]` 子类，带分页元信息与可选 `to_pandas()`）。

**Tech Stack:** Python 3.10+、`requests`（唯一硬依赖）、`pandas`（可选，惰性导入）、`pytest` + `requests-mock`（测试）、`mypy`（类型）、`hatchling`（构建）。

## Global Constraints

（每个任务的需求都隐式包含以下全部约束，源自已确认的设计文档 `docs/superpowers/specs/2026-06-23-bihu-stock-data-client-design.md`）

- Python `>=3.10`；分发名 `bihu-stock-data-client`；导入名 `bihu_stock_data_client`；示例别名 `bsdc`。
- 硬依赖仅 `requests`；`pandas` 为可选依赖，仅 `.to_pandas()` 时惰性导入，未安装抛带安装提示的 `ImportError`。
- `src/` 布局；`hatchling` 构建；协议 **MIT**；`py.typed` 标记。
- API Key 认证**仅**经请求头 `X-API-Key`；**不做任何前缀假设**，原样透传。
- `base_url` 默认 `http://localhost:9800/stock/data`（rstrip 尾部 `/`）。
- 服务端 JSON 字段为 **camelCase**；方法参数对外用 **snake_case**，发请求前转 camelCase；返回字典的**键保留服务端原始 camelCase**（如 `stockCode`、`close`）。
- 统一响应 `ResponseParam{code,message,data,traceId}`；成功 `code == "0000"`；分页 `pageSize` 上限 `1000`；`quarterType` 取值 `1~4`（1=一季报 2=年中报 3=三季报 4=年报）。
- 环境变量兜底：`BIHU_STOCK_DATA_API_KEY`、`BIHU_STOCK_DATA_BASE_URL`。
- 测试用 `pytest` + `requests-mock`；源码全量类型注解，`mypy` 干净。
- 设计文档 §6.2 的"动态绑定方法"在实现中改为**显式类型包装方法 + 注册表驱动的 `_call`**，以同时满足 §11 的"完整类型注解 / mypy 干净 / IDE 自动补全"目标（见 Task 6 说明）。

---

## File Structure

| 文件 | 职责 | 创建任务 |
|---|---|---|
| `pyproject.toml` | 构建、元数据、依赖、pytest 配置 | Task 1 |
| `LICENSE` | MIT 全文 | Task 1 |
| `.gitignore` | Python 标准忽略 | Task 1 |
| `src/bihu_stock_data_client/py.typed` | PEP 561 类型标记（空文件） | Task 1 |
| `src/bihu_stock_data_client/__init__.py` | 包入口；逐步导出公开 API | Task 1 → Task 6 |
| `src/bihu_stock_data_client/errors.py` | 异常层次 | Task 1 |
| `src/bihu_stock_data_client/config.py` | `ClientConfig` + 环境变量 | Task 2 |
| `src/bihu_stock_data_client/decoder.py` | snake/camel、`Records`、列式解码 | Task 3 |
| `src/bihu_stock_data_client/registry.py` | `Endpoint` + 26 条 `ENDPOINTS` | Task 4 |
| `src/bihu_stock_data_client/transport.py` | `HttpClient`：会话/鉴权/重试/解包/错误映射 | Task 5 |
| `src/bihu_stock_data_client/client.py` | `StockDataClient` 门面 + 26 个方法 | Task 6 → Task 7 |
| `tests/unit/test_errors.py` 等 | 单元测试 | 各任务 |
| `tests/contract/test_contract.py` | 契约测试（requests-mock + 真实样本） | Task 8 |
| `tests/integration/test_integration.py` | opt-in 真机集成测试 | Task 9 |
| `examples/*.py`、`README.md`、`CHANGELOG.md` | 文档与示例 | Task 9 |

---

## Task 1: 项目脚手架与异常层次

**Files:**
- Create: `pyproject.toml`
- Create: `LICENSE`
- Create: `.gitignore`
- Create: `src/bihu_stock_data_client/__init__.py`
- Create: `src/bihu_stock_data_client/py.typed`
- Create: `src/bihu_stock_data_client/errors.py`
- Test: `tests/unit/test_errors.py`

**Interfaces:**
- Produces: 异常类 `StockDataError`, `ConfigurationError`, `AuthenticationError`, `RateLimitError`, `ApiError(message, *, code, status, trace_id)`, `PaginationLimitError`, `ConnectionError`, `ValidationError`。所有类均携带 `.trace_id`（服务端有返回时）；`ApiError` 额外携带 `.code` / `.status` / `.message`。

- [ ] **Step 1: 初始化 git 仓库与目录骨架**

Run:
```bash
cd D:/workspace/stock-data-client
git init
mkdir -p src/bihu_stock_data_client tests/unit tests/contract tests/integration examples
```

- [ ] **Step 2: 写 `pyproject.toml`**

Create `pyproject.toml`:
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "bihu-stock-data-client"
version = "0.1.0"
description = "Python 客户端 SDK，对接 stock-data-server 的 A 股数据 REST API"
readme = "README.md"
requires-python = ">=3.10"
license = { text = "MIT" }
authors = [{ name = "bihu" }]
keywords = ["stock", "a-share", "finance", "data", "sdk"]
classifiers = [
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]
dependencies = ["requests>=2.31"]

[project.optional-dependencies]
pandas = ["pandas>=2.0"]
dev = ["pytest>=7", "requests-mock>=1.11", "mypy>=1.8"]

[tool.hatch.build.targets.wheel]
packages = ["src/bihu_stock_data_client"]

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = ["integration: opt-in 真机集成测试（需服务端 + API Key）"]
```

- [ ] **Step 3: 写 `LICENSE`（MIT）**

Create `LICENSE`:
```
MIT License

Copyright (c) 2026 bihu

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 4: 写 `.gitignore`**

Create `.gitignore`:
```
__pycache__/
*.py[cod]
*.egg-info/
.eggs/
build/
dist/
.pytest_cache/
.mypy_cache/
.venv/
venv/
.idea/
.vscode/
```

- [ ] **Step 5: 写 `py.typed` 与最小 `__init__.py`**

Create empty `src/bihu_stock_data_client/py.typed` (no content).

Create `src/bihu_stock_data_client/__init__.py`:
```python
"""bihu-stock-data-client: 对接 stock-data-server 的 Python 客户端 SDK。"""

__version__ = "0.1.0"
```

- [ ] **Step 6: 写失败测试 `tests/unit/test_errors.py`**

Create `tests/unit/test_errors.py`:
```python
import pytest

from bihu_stock_data_client.errors import (
    ApiError,
    AuthenticationError,
    ConfigurationError,
    ConnectionError,
    PaginationLimitError,
    RateLimitError,
    StockDataError,
    ValidationError,
)


def test_all_subclass_base():
    for exc in (
        ConfigurationError,
        AuthenticationError,
        RateLimitError,
        ApiError,
        PaginationLimitError,
        ConnectionError,
        ValidationError,
    ):
        assert issubclass(exc, StockDataError)


def test_trace_id_carried():
    e = AuthenticationError("bad key", trace_id="abc123")
    assert e.trace_id == "abc123"
    assert str(e) == "bad key"


def test_api_error_fields():
    e = ApiError("oops", code="1001", status=None, trace_id="t-1")
    assert e.code == "1001"
    assert e.trace_id == "t-1"
    assert e.message == "oops"
```

- [ ] **Step 7: 运行测试，确认失败**

Run: `pytest tests/unit/test_errors.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'bihu_stock_data_client.errors'`

- [ ] **Step 8: 写实现 `src/bihu_stock_data_client/errors.py`**

Create `src/bihu_stock_data_client/errors.py`:
```python
"""异常层次。所有异常都携带 trace_id（服务端有返回时）。"""

from __future__ import annotations

from typing import Optional


class StockDataError(Exception):
    """所有客户端异常的基类。"""

    def __init__(self, message: str = "", *, trace_id: Optional[str] = None) -> None:
        super().__init__(message)
        self.message = message
        self.trace_id = trace_id


class ConfigurationError(StockDataError):
    """初始化配置缺失或非法（如未提供 api_key）。"""


class AuthenticationError(StockDataError):
    """认证失败（HTTP 401）：API Key 无效/失效。"""


class RateLimitError(StockDataError):
    """触发服务端限流。"""


class ApiError(StockDataError):
    """服务端业务错误（code != '0000'）或非 2xx HTTP。"""

    def __init__(
        self,
        message: str = "",
        *,
        code: Optional[str] = None,
        status: Optional[int] = None,
        trace_id: Optional[str] = None,
    ) -> None:
        super().__init__(message, trace_id=trace_id)
        self.code = code
        self.status = status


class PaginationLimitError(StockDataError):
    """fetch_all 结果超过 max_rows 护栏。"""


class ConnectionError(StockDataError):  # noqa: A001 限定在包命名空间内，与服务端/设计文档保持一致
    """网络/超时错误（包装 requests 异常）。"""


class ValidationError(StockDataError):
    """客户端参数校验失败。"""
```

- [ ] **Step 9: 以可编辑模式安装并运行测试，确认通过**

Run:
```bash
pip install -e ".[dev]"
pytest tests/unit/test_errors.py -v
```
Expected: PASS（3 passed）。

- [ ] **Step 10: 提交**

Run:
```bash
git add pyproject.toml LICENSE .gitignore src tests
git commit -m "chore: scaffold project + add error hierarchy"
```

---

## Task 2: 配置模块

**Files:**
- Create: `src/bihu_stock_data_client/config.py`
- Test: `tests/unit/test_config.py`

**Interfaces:**
- Consumes: `errors.ConfigurationError`（Task 1）
- Produces: `ClientConfig`（frozen dataclass，字段 `api_key:str`、`base_url:str`、`timeout:float`、`max_retries:int`）；类方法 `ClientConfig.from_env(*, api_key=None, base_url=None, timeout=30.0, max_retries=2) -> ClientConfig`。

- [ ] **Step 1: 写失败测试 `tests/unit/test_config.py`**

Create `tests/unit/test_config.py`:
```python
import pytest

from bihu_stock_data_client.config import ClientConfig
from bihu_stock_data_client.errors import ConfigurationError


def test_explicit_args(monkeypatch):
    monkeypatch.delenv("BIHU_STOCK_DATA_API_KEY", raising=False)
    cfg = ClientConfig.from_env(api_key="k1", base_url="http://h:1/stock/data/")
    assert cfg.api_key == "k1"
    assert cfg.base_url == "http://h:1/stock/data"  # rstrip 尾部 /
    assert cfg.timeout == 30.0
    assert cfg.max_retries == 2


def test_env_fallback(monkeypatch):
    monkeypatch.setenv("BIHU_STOCK_DATA_API_KEY", "envkey")
    monkeypatch.setenv("BIHU_STOCK_DATA_BASE_URL", "http://envhost:9800/stock/data")
    cfg = ClientConfig.from_env()
    assert cfg.api_key == "envkey"
    assert cfg.base_url == "http://envhost:9800/stock/data"


def test_missing_key_raises(monkeypatch):
    monkeypatch.delenv("BIHU_STOCK_DATA_API_KEY", raising=False)
    with pytest.raises(ConfigurationError):
        ClientConfig.from_env()


def test_frozen(monkeypatch):
    monkeypatch.delenv("BIHU_STOCK_DATA_API_KEY", raising=False)
    cfg = ClientConfig.from_env(api_key="k")
    with pytest.raises(Exception):
        cfg.api_key = "x"  # type: ignore[misc]
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `pytest tests/unit/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: ...config`

- [ ] **Step 3: 写实现 `src/bihu_stock_data_client/config.py`**

Create `src/bihu_stock_data_client/config.py`:
```python
"""客户端配置：参数 + 环境变量兜底。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from .errors import ConfigurationError

ENV_API_KEY = "BIHU_STOCK_DATA_API_KEY"
ENV_BASE_URL = "BIHU_STOCK_DATA_BASE_URL"
DEFAULT_BASE_URL = "http://localhost:9800/stock/data"
DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_RETRIES = 2


@dataclass(frozen=True)
class ClientConfig:
    api_key: str
    base_url: str = DEFAULT_BASE_URL
    timeout: float = DEFAULT_TIMEOUT
    max_retries: int = DEFAULT_MAX_RETRIES

    @classmethod
    def from_env(
        cls,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> "ClientConfig":
        key = api_key if api_key is not None else os.environ.get(ENV_API_KEY)
        if not key:
            raise ConfigurationError(
                f"未提供 api_key，请传入参数或设置环境变量 {ENV_API_KEY}"
            )
        url = (
            base_url
            if base_url is not None
            else (os.environ.get(ENV_BASE_URL) or DEFAULT_BASE_URL)
        )
        return cls(
            api_key=key,
            base_url=url.rstrip("/"),
            timeout=timeout,
            max_retries=max_retries,
        )
```

- [ ] **Step 4: 运行测试，确认通过**

Run: `pytest tests/unit/test_config.py -v`
Expected: PASS（4 passed）。

- [ ] **Step 5: 提交**

Run:
```bash
git add src/bihu_stock_data_client/config.py tests/unit/test_config.py
git commit -m "feat(config): add ClientConfig with env-var fallback"
```

---

## Task 3: 解码器与 Records 类型

**Files:**
- Create: `src/bihu_stock_data_client/decoder.py`
- Test: `tests/unit/test_decoder.py`

**Interfaces:**
- Produces:
  - `snake_to_camel(s: str) -> str`（`stock_code`→`stockCode`）
  - `Records`（`list` 子类）：构造 `Records(items=None, *, total_count=None, total_pages=None, page_num=None, page_size=None)`；属性 `.total_count/.total_pages/.page_num/.page_size`；方法 `.to_pandas()`
  - `decode_columnar(data) -> Records`（非分页，元信息为 `None`）
  - `decode_columnar_page(data) -> Records`（分页，带元信息）

- [ ] **Step 1: 写失败测试 `tests/unit/test_decoder.py`**

Create `tests/unit/test_decoder.py`:
```python
import builtins

import pytest

from bihu_stock_data_client.decoder import (
    Records,
    decode_columnar,
    decode_columnar_page,
    snake_to_camel,
)


def test_snake_to_camel():
    assert snake_to_camel("stock_code") == "stockCode"
    assert snake_to_camel("start_date") == "startDate"
    assert snake_to_camel("page_num") == "pageNum"
    assert snake_to_camel("stock_codes") == "stockCodes"


def test_decode_columnar():
    data = {
        "column": ["stockCode", "close"],
        "item": [["000001", 10.5], ["000001", 10.8]],
    }
    rows = decode_columnar(data)
    assert isinstance(rows, list)
    assert len(rows) == 2
    assert rows[0] == {"stockCode": "000001", "close": 10.5}
    assert rows.total_count is None  # 非分页


def test_decode_columnar_empty():
    assert decode_columnar(None) == []
    assert decode_columnar({}) == []


def test_decode_columnar_page_metadata():
    data = {
        "column": ["a"],
        "item": [[1], [2]],
        "pageNum": 1,
        "pageSize": 2,
        "totalCount": 5,
        "totalPage": 3,
    }
    rows = decode_columnar_page(data)
    assert len(rows) == 2
    assert rows.total_count == 5
    assert rows.total_pages == 3
    assert rows.page_num == 1
    assert rows.page_size == 2


def test_records_behaves_as_list():
    r = Records([{"a": 1}], total_count=10, total_pages=2, page_num=1, page_size=5)
    assert r[0] == {"a": 1}
    assert len(r) == 1
    assert list(r) == [{"a": 1}]


def test_to_pandas_requires_pandas(monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "pandas":
            raise ImportError("no pandas")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    r = Records([{"a": 1}])
    with pytest.raises(ImportError):
        r.to_pandas()
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `pytest tests/unit/test_decoder.py -v`
Expected: FAIL — `ModuleNotFoundError: ...decoder`

- [ ] **Step 3: 写实现 `src/bihu_stock_data_client/decoder.py`**

Create `src/bihu_stock_data_client/decoder.py`:
```python
"""列式解码、snake/camel 转换、Records 返回类型。"""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Optional


def snake_to_camel(s: str) -> str:
    """stock_code -> stockCode。"""
    parts = s.split("_")
    return parts[0] + "".join(p.title() for p in parts[1:])


def _row_to_dict(columns: list, row: list) -> dict:
    return dict(zip(columns, row))


class Records(list):
    """list[dict] 子类：手感同 list[dict]，附带分页元信息与可选 pandas 转换。

    字典键保留服务端原始 camelCase 列名（如 'stockCode'、'close'）。
    """

    def __init__(
        self,
        items: Optional[Iterable[Mapping[str, Any]]] = None,
        *,
        total_count: Optional[int] = None,
        total_pages: Optional[int] = None,
        page_num: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> None:
        super().__init__(items or [])
        self.total_count = total_count
        self.total_pages = total_pages
        self.page_num = page_num
        self.page_size = page_size

    def to_pandas(self):  # pragma: no cover - exercised when pandas present/absent
        try:
            import pandas as pd  # type: ignore
        except ImportError as e:
            raise ImportError(
                "to_pandas() 需要安装 pandas：pip install bihu-stock-data-client[pandas]"
            ) from e
        return pd.DataFrame(list(self))

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        n = len(self)
        if self.total_pages is not None:
            return f"Records({n} rows, page {self.page_num}/{self.total_pages})"
        return f"Records({n} rows)"


def decode_columnar(data: Optional[Mapping[str, Any]]) -> Records:
    """ColumnarData {column, item} -> Records（非分页）。"""
    if not data:
        return Records()
    columns = data.get("column") or []
    items = data.get("item") or []
    return Records(_row_to_dict(columns, row) for row in items)


def decode_columnar_page(data: Optional[Mapping[str, Any]]) -> Records:
    """ColumnarPageData -> Records（带分页元信息）。"""
    if not data:
        return Records(total_count=0, total_pages=0, page_num=0, page_size=0)
    columns = data.get("column") or []
    items = data.get("item") or []
    return Records(
        (_row_to_dict(columns, row) for row in items),
        total_count=data.get("totalCount"),
        total_pages=data.get("totalPage"),
        page_num=data.get("pageNum"),
        page_size=data.get("pageSize"),
    )
```

- [ ] **Step 4: 运行测试，确认通过**

Run: `pytest tests/unit/test_decoder.py -v`
Expected: PASS（6 passed）。

- [ ] **Step 5: 提交**

Run:
```bash
git add src/bihu_stock_data_client/decoder.py tests/unit/test_decoder.py
git commit -m "feat(decoder): columnar decode, snake/camel, Records type"
```

---

## Task 4: 接口注册表

**Files:**
- Create: `src/bihu_stock_data_client/registry.py`
- Test: `tests/unit/test_registry.py`

**Interfaces:**
- Produces:
  - `HttpMethod` 枚举（`GET`、`POST`）
  - `Endpoint`（frozen dataclass，字段 `name`、`method: HttpMethod`、`path`、`params: tuple[str,...]=()`、`paginated: bool=False`、`path_params: tuple[str,...]=()`、`summary: str=""`）；`__post_init__` 校验每个 `path_params` 在 `path` 中以 `{name}` 出现
  - `ENDPOINTS: tuple[Endpoint, ...]`（26 条）

- [ ] **Step 1: 写失败测试 `tests/unit/test_registry.py`**

Create `tests/unit/test_registry.py`:
```python
import pytest

from bihu_stock_data_client.registry import ENDPOINTS


def test_unique_names():
    names = [e.name for e in ENDPOINTS]
    assert len(names) == len(set(names))


def test_count():
    assert len(ENDPOINTS) == 26


def test_required_fields():
    for e in ENDPOINTS:
        assert e.name and e.path and e.method
        assert e.summary
        for p in e.path_params:
            assert "{" + p + "}" in e.path


def test_paginated_marked():
    by_name = {e.name: e for e in ENDPOINTS}
    assert by_name["kline_daily"].paginated is True
    assert by_name["stock_basic"].paginated is False
    assert by_name["kline_minute"].paginated is False
    assert by_name["stock_realtime"].paginated is False


def test_known_params():
    by_name = {e.name: e for e in ENDPOINTS}
    assert by_name["kline_daily"].params == ("stock_code", "start_date", "end_date")
    assert by_name["financial_report"].params == (
        "stock_code",
        "report_year",
        "quarter_type",
    )
    assert by_name["kline_minute"].path_params == ("stock_code", "trade_date")
    assert by_name["stock_realtime"].params == ("stock_codes",)
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `pytest tests/unit/test_registry.py -v`
Expected: FAIL — `ModuleNotFoundError: ...registry`

- [ ] **Step 3: 写实现 `src/bihu_stock_data_client/registry.py`**

Create `src/bihu_stock_data_client/registry.py`:
```python
"""声明式接口注册表：所有查询接口的元数据（单一事实来源）。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class HttpMethod(Enum):
    GET = "GET"
    POST = "POST"


@dataclass(frozen=True)
class Endpoint:
    name: str
    method: "HttpMethod"
    path: str
    params: tuple[str, ...] = ()
    paginated: bool = False
    path_params: tuple[str, ...] = ()
    summary: str = ""

    def __post_init__(self) -> None:
        for p in self.path_params:
            if "{" + p + "}" not in self.path:
                raise ValueError(
                    f"Endpoint '{self.name}': 路径 {self.path} 缺少占位符 {{{p}}}"
                )


ENDPOINTS: tuple[Endpoint, ...] = (
    # K线行情
    Endpoint("kline_daily", HttpMethod.POST, "/kline-daily/list",
             params=("stock_code", "start_date", "end_date"), paginated=True, summary="日K线行情"),
    Endpoint("kline_daily_stat", HttpMethod.POST, "/kline-daily-stat/list",
             params=("stock_code", "start_date", "end_date"), paginated=True, summary="每日统计指标"),
    Endpoint("kline_minute", HttpMethod.GET, "/kline-minute/{stock_code}/{trade_date}",
             path_params=("stock_code", "trade_date"), summary="按股票+日期查分钟K线"),
    Endpoint("kline_minute_snapshot", HttpMethod.POST, "/kline-minute-snapshot/list",
             params=("stock_code",), paginated=True, summary="分钟K线快照"),
    # 指数
    Endpoint("index_basic", HttpMethod.GET, "/index-basic/list", summary="所有指数基础信息"),
    Endpoint("index_kline_daily", HttpMethod.POST, "/index-kline-daily/list",
             params=("index_code", "start_date", "end_date"), paginated=True, summary="指数日K线"),
    Endpoint("index_constituent", HttpMethod.POST, "/index-constituent/list",
             params=("index_code", "stock_code"), paginated=True, summary="指数成分股"),
    # 股票基础
    Endpoint("stock_basic", HttpMethod.GET, "/stock-basic/list", summary="所有股票基本信息"),
    # 申万行业
    Endpoint("sw_industry", HttpMethod.GET, "/sw-industry/list", summary="所有申万行业分类"),
    Endpoint("sw_stock_classify", HttpMethod.POST, "/sw-stock-classify/list",
             params=("stock_code",), paginated=True, summary="个股申万行业归属"),
    Endpoint("sw_industry_daily_stat", HttpMethod.POST, "/sw-industry-daily-stat/list",
             params=("industry_code", "start_date", "end_date"), paginated=True, summary="申万行业日度统计"),
    Endpoint("sw_industry_capital_flow", HttpMethod.POST, "/sw-industry-capital-flow/list",
             params=("industry_code", "start_date", "end_date"), paginated=True, summary="申万行业资金流"),
    # 资金/成交
    Endpoint("capital_flow", HttpMethod.POST, "/capital-flow/list",
             params=("stock_code", "start_date", "end_date"), paginated=True, summary="资金流向"),
    Endpoint("block_trade", HttpMethod.POST, "/block-trade/list",
             params=("stock_code", "start_date", "end_date"), paginated=True, summary="大宗交易"),
    Endpoint("margin_trading", HttpMethod.POST, "/margin-trading/list",
             params=("stock_code", "start_date", "end_date"), paginated=True, summary="融资融券"),
    Endpoint("dragon_tiger", HttpMethod.POST, "/dragon-tiger/list",
             params=("stock_code", "start_date", "end_date"), paginated=True, summary="龙虎榜"),
    Endpoint("pre_post_market", HttpMethod.POST, "/pre-post-market/list",
             params=("stock_code", "start_date", "end_date"), paginated=True, summary="盘前盘后成交"),
    # 股本/股东
    Endpoint("share_capital", HttpMethod.POST, "/share-capital/list",
             params=("stock_code", "start_date", "end_date"), paginated=True, summary="股本数据"),
    Endpoint("share_trade", HttpMethod.POST, "/share-trade/list",
             params=("stock_code", "start_date", "end_date"), paginated=True, summary="增减持"),
    Endpoint("shareholder_stats", HttpMethod.POST, "/shareholder-stats/list",
             params=("stock_code", "report_year", "quarter_type"), paginated=True, summary="股东统计"),
    Endpoint("institutional_holding", HttpMethod.POST, "/institutional-holding/list",
             params=("stock_code", "report_year", "quarter_type"), paginated=True, summary="机构持股"),
    # 财务/分红
    Endpoint("financial_report", HttpMethod.POST, "/financial-report/list",
             params=("stock_code", "report_year", "quarter_type"), paginated=True, summary="财务报告"),
    Endpoint("dividend_factor", HttpMethod.POST, "/dividend-factor/list",
             params=("stock_code", "start_date", "end_date"), paginated=True, summary="分红配送"),
    # 统计
    Endpoint("stock_limit_up_stats", HttpMethod.POST, "/stock-limit-up-stats/list",
             params=("stock_code", "start_date", "end_date"), paginated=True, summary="涨跌停统计"),
    # 交易日历
    Endpoint("trading_calendar", HttpMethod.POST, "/trading-calendar/list",
             params=("start_date", "end_date"), paginated=True, summary="交易日历"),
    # 实时快照（内存查询，不分页）
    Endpoint("stock_realtime", HttpMethod.POST, "/stock-realtime/list",
             params=("stock_codes",), summary="股票实时快照（内存，不分页）"),
)
```

- [ ] **Step 4: 运行测试，确认通过**

Run: `pytest tests/unit/test_registry.py -v`
Expected: PASS（5 passed）。

- [ ] **Step 5: 提交**

Run:
```bash
git add src/bihu_stock_data_client/registry.py tests/unit/test_registry.py
git commit -m "feat(registry): declarative endpoint table (26 endpoints)"
```

---

## Task 5: HTTP 传输层

**Files:**
- Create: `src/bihu_stock_data_client/transport.py`
- Test: `tests/unit/test_transport.py`

**Interfaces:**
- Consumes: `config.ClientConfig`（Task 2）、`errors.{ApiError, AuthenticationError, ConnectionError, RateLimitError}`（Task 1）
- Produces: `HttpClient(config: ClientConfig, *, session=None)`；方法 `request(method: str, path: str, *, json=None) -> Any`（返回解包后的 `data`，失败抛对应异常）。`session` 参数供测试注入。

- [ ] **Step 1: 写失败测试 `tests/unit/test_transport.py`**

Create `tests/unit/test_transport.py`:
```python
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
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `pytest tests/unit/test_transport.py -v`
Expected: FAIL — `ModuleNotFoundError: ...transport`

- [ ] **Step 3: 写实现 `src/bihu_stock_data_client/transport.py`**

Create `src/bihu_stock_data_client/transport.py`:
```python
"""HTTP 传输层：会话、鉴权、重试、解包 ResponseParam、错误映射。"""

from __future__ import annotations

import logging
from typing import Any, Mapping, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import ClientConfig
from .errors import ApiError, AuthenticationError, ConnectionError, RateLimitError

logger = logging.getLogger("bihu_stock_data_client")
_SUCCESS_CODE = "0000"


class HttpClient:
    def __init__(
        self,
        config: ClientConfig,
        *,
        session: Optional[requests.Session] = None,
    ) -> None:
        self._config = config
        self._session = session or self._build_session()

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=self._config.max_retries,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(["GET", "POST"]),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def request(
        self,
        method: str,
        path: str,
        *,
        json: Optional[Mapping[str, Any]] = None,
    ) -> Any:
        url = self._config.base_url + path
        headers = {"X-API-Key": self._config.api_key}
        logger.debug("%s %s", method, path)
        try:
            resp = self._session.request(
                method, url, json=json, headers=headers, timeout=self._config.timeout
            )
        except requests.exceptions.Timeout as e:
            raise ConnectionError(f"请求超时: {e}") from e
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f"连接服务端失败: {e}") from e
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"请求异常: {e}") from e
        self._raise_for_status(resp)
        return self._unwrap(resp.json())

    def _raise_for_status(self, resp: requests.Response) -> None:
        if resp.status_code == 401:
            raise AuthenticationError("认证失败（HTTP 401）：请检查 API Key 是否正确")
        if resp.status_code == 429:
            raise RateLimitError("请求过于频繁，已触发服务端限流（HTTP 429）")
        if not (200 <= resp.status_code < 300):
            raise ApiError(f"服务端返回 HTTP {resp.status_code}", status=resp.status_code)

    def _unwrap(self, payload: Mapping[str, Any]) -> Any:
        code = payload.get("code")
        if code != _SUCCESS_CODE:
            raise ApiError(
                str(payload.get("message") or "未知服务端错误"),
                code=code,
                status=None,
                trace_id=payload.get("traceId"),
            )
        return payload.get("data")
```

- [ ] **Step 4: 运行测试，确认通过**

Run: `pytest tests/unit/test_transport.py -v`
Expected: PASS（6 passed）。

- [ ] **Step 5: 提交**

Run:
```bash
git add src/bihu_stock_data_client/transport.py tests/unit/test_transport.py
git commit -m "feat(transport): HTTP client with auth, retry, envelope unwrap, error mapping"
```

---

## Task 6: 客户端门面与 26 个公开方法（单页）

**说明（设计细化）：** 设计文档 §6.2 写的是"动态绑定方法"。为同时满足 §11 的"完整类型注解 / mypy 干净 / IDE 自动补全"，这里改用**显式类型包装方法 + 注册表驱动的私有 `_call`**：注册表仍是请求构造（路径/方法/分页/编码）的单一事实来源，每个公开方法是 2~5 行的薄委托。新增接口 = 注册表加一行 + 加一个薄方法。本任务实现**单页查询**；`fetch_all` 在 Task 7 实现。

**Files:**
- Create: `src/bihu_stock_data_client/client.py`
- Modify: `src/bihu_stock_data_client/__init__.py`（导出公开 API）
- Test: `tests/unit/test_client.py`

**Interfaces:**
- Consumes: `config.ClientConfig`、`transport.HttpClient`、`decoder.{Records, decode_columnar, decode_columnar_page, snake_to_camel}`、`errors.{PaginationLimitError, ValidationError}`、`registry.{ENDPOINTS, Endpoint, HttpMethod}`
- Produces: `StockDataClient(api_key=None, base_url=None, *, timeout=30.0, max_retries=2, session=None)`；私有 `_call(name, *, fetch_all=False, max_rows=..., page_num=1, page_size=1000, **biz) -> Records`、`_call_page`、`_call_all`（Task 7 填充）、`_validate`、`_build_path`；26 个公开方法（签名见实现）。`session` 参数供测试注入。
- `__init__` 导出：`StockDataClient`（别名 `Client`）、`Records`、全部异常、`ClientConfig`、`__version__`。

- [ ] **Step 1: 写失败测试 `tests/unit/test_client.py`**

Create `tests/unit/test_client.py`:
```python
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


def test_stock_realtime_post_body():
    with requests_mock.Mocker() as m:
        m.post(
            f"{BASE}/stock-realtime/list",
            json={"code": "0000",
                  "data": {"column": ["stockCode"], "item": [["000001"]]}, "traceId": "t"},
        )
        client().stock_realtime(stock_codes=["000001", "600000"])
        body = m.last_request.json()
        assert body["stockCodes"] == ["000001", "600000"]
        assert "pageNum" not in body  # 非分页不带分页字段


def test_unknown_param_rejected():
    with pytest.raises(ValidationError):
        client().kline_daily(foo="bar")


def test_quarter_type_validated():
    with pytest.raises(ValidationError):
        client().financial_report(stock_code="000001", report_year=2024, quarter_type=9)


def test_page_size_validated():
    with pytest.raises(ValidationError):
        client().kline_daily(stock_code="000001", page_size=5000)
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `pytest tests/unit/test_client.py -v`
Expected: FAIL — `ImportError: cannot import name 'StockDataClient'`

- [ ] **Step 3: 写实现 `src/bihu_stock_data_client/client.py`**

Create `src/bihu_stock_data_client/client.py`:
```python
"""StockDataClient：门面，组合 transport + registry + decoder，暴露 26 个查询方法。"""

from __future__ import annotations

from typing import Any, Optional

from .config import ClientConfig
from .decoder import Records, decode_columnar, decode_columnar_page, snake_to_camel
from .errors import PaginationLimitError, ValidationError
from .registry import ENDPOINTS, Endpoint, HttpMethod
from .transport import HttpClient

DEFAULT_PAGE_SIZE = 1000
DEFAULT_MAX_ROWS = 1_000_000
_MAX_PAGE_SIZE = 1000
_VALID_QUARTER_TYPES = (1, 2, 3, 4)


class StockDataClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        *,
        timeout: float = 30.0,
        max_retries: int = 2,
        session: Optional[Any] = None,
    ) -> None:
        self._config = ClientConfig.from_env(
            api_key=api_key, base_url=base_url, timeout=timeout, max_retries=max_retries
        )
        self._http = HttpClient(self._config, session=session)
        self._by_name: dict[str, Endpoint] = {ep.name: ep for ep in ENDPOINTS}

    # ---------------- 私有机制 ----------------
    def _call(
        self,
        name: str,
        *,
        fetch_all: bool = False,
        max_rows: int = DEFAULT_MAX_ROWS,
        page_num: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
        **biz: Any,
    ) -> Records:
        ep = self._by_name[name]
        self._validate(ep, biz, page_size=page_size)
        if fetch_all and ep.paginated:
            return self._call_all(ep, max_rows=max_rows, page_size=page_size, **biz)
        return self._call_page(ep, page_num=page_num, page_size=page_size, **biz)

    def _validate(self, ep: Endpoint, biz: dict, *, page_size: int) -> None:
        allowed = set(ep.params) | set(ep.path_params)
        for k in biz:
            if k not in allowed:
                raise ValidationError(
                    f"'{ep.name}' 不支持参数 '{k}'，支持: {sorted(allowed)}"
                )
        if (
            "quarter_type" in biz
            and biz["quarter_type"] is not None
            and biz["quarter_type"] not in _VALID_QUARTER_TYPES
        ):
            raise ValidationError(
                f"'{ep.name}' 的 quarter_type 必须为 1~4（1=一季报 2=年中报 3=三季报 4=年报）"
            )
        if ep.paginated and page_size is not None and not (1 <= page_size <= _MAX_PAGE_SIZE):
            raise ValidationError(
                f"'{ep.name}' 的 page_size 必须在 1~{_MAX_PAGE_SIZE} 之间"
            )

    def _build_path(self, ep: Endpoint, biz: dict) -> str:
        path = ep.path
        for p in ep.path_params:
            val = biz.get(p)
            if val is None:
                raise ValidationError(f"'{ep.name}' 缺少必填路径参数 '{p}'")
            path = path.replace("{" + p + "}", str(val))
        return path

    def _call_page(
        self, ep: Endpoint, *, page_num: int, page_size: int, **biz: Any
    ) -> Records:
        body: dict[str, Any] = {}
        if ep.paginated:
            body["pageNum"] = page_num
            body["pageSize"] = page_size
        for p in ep.params:
            if biz.get(p) is not None:
                body[snake_to_camel(p)] = biz[p]
        if ep.method is HttpMethod.GET:
            data = self._http.request("GET", self._build_path(ep, biz))
        else:
            data = self._http.request("POST", ep.path, json=body)
        if ep.paginated:
            return decode_columnar_page(data)
        return decode_columnar(data)

    def _call_all(
        self, ep: Endpoint, *, max_rows: int, page_size: int, **biz: Any
    ) -> Records:
        # Task 7 实现
        raise NotImplementedError  # pragma: no cover

    # ---------------- 公开 API：26 个方法 ----------------
    def kline_daily(
        self, *, stock_code=None, start_date=None, end_date=None,
        page_num=1, page_size=DEFAULT_PAGE_SIZE, fetch_all=False, max_rows=DEFAULT_MAX_ROWS,
    ) -> Records:
        """日K线行情。POST /kline-daily/list（分页）。

        筛选: stock_code, start_date(yyyy-MM-dd), end_date(yyyy-MM-dd)，均可选。
        分页: page_num(默认1), page_size(默认1000, 上限1000); fetch_all=True 自动全量; max_rows 全量护栏。
        返回: Records（list[dict]，键为服务端 camelCase 列名）。
        """
        return self._call(
            "kline_daily", fetch_all=fetch_all, max_rows=max_rows,
            page_num=page_num, page_size=page_size,
            stock_code=stock_code, start_date=start_date, end_date=end_date,
        )

    def kline_daily_stat(
        self, *, stock_code=None, start_date=None, end_date=None,
        page_num=1, page_size=DEFAULT_PAGE_SIZE, fetch_all=False, max_rows=DEFAULT_MAX_ROWS,
    ) -> Records:
        """每日统计指标。POST /kline-daily-stat/list（分页）。"""
        return self._call(
            "kline_daily_stat", fetch_all=fetch_all, max_rows=max_rows,
            page_num=page_num, page_size=page_size,
            stock_code=stock_code, start_date=start_date, end_date=end_date,
        )

    def kline_minute(self, *, stock_code, trade_date) -> Records:
        """按股票+日期查分钟K线。GET /kline-minute/{stock_code}/{trade_date}（不分页）。"""
        return self._call("kline_minute", stock_code=stock_code, trade_date=trade_date)

    def kline_minute_snapshot(
        self, *, stock_code=None,
        page_num=1, page_size=DEFAULT_PAGE_SIZE, fetch_all=False, max_rows=DEFAULT_MAX_ROWS,
    ) -> Records:
        """分钟K线快照。POST /kline-minute-snapshot/list（分页）。"""
        return self._call(
            "kline_minute_snapshot", fetch_all=fetch_all, max_rows=max_rows,
            page_num=page_num, page_size=page_size, stock_code=stock_code,
        )

    def index_basic(self) -> Records:
        """所有指数基础信息。GET /index-basic/list（不分页）。"""
        return self._call("index_basic")

    def index_kline_daily(
        self, *, index_code=None, start_date=None, end_date=None,
        page_num=1, page_size=DEFAULT_PAGE_SIZE, fetch_all=False, max_rows=DEFAULT_MAX_ROWS,
    ) -> Records:
        """指数日K线。POST /index-kline-daily/list（分页）。"""
        return self._call(
            "index_kline_daily", fetch_all=fetch_all, max_rows=max_rows,
            page_num=page_num, page_size=page_size,
            index_code=index_code, start_date=start_date, end_date=end_date,
        )

    def index_constituent(
        self, *, index_code=None, stock_code=None,
        page_num=1, page_size=DEFAULT_PAGE_SIZE, fetch_all=False, max_rows=DEFAULT_MAX_ROWS,
    ) -> Records:
        """指数成分股。POST /index-constituent/list（分页）。"""
        return self._call(
            "index_constituent", fetch_all=fetch_all, max_rows=max_rows,
            page_num=page_num, page_size=page_size,
            index_code=index_code, stock_code=stock_code,
        )

    def stock_basic(self) -> Records:
        """所有股票基本信息。GET /stock-basic/list（不分页）。"""
        return self._call("stock_basic")

    def sw_industry(self) -> Records:
        """所有申万行业分类。GET /sw-industry/list（不分页）。"""
        return self._call("sw_industry")

    def sw_stock_classify(
        self, *, stock_code=None,
        page_num=1, page_size=DEFAULT_PAGE_SIZE, fetch_all=False, max_rows=DEFAULT_MAX_ROWS,
    ) -> Records:
        """个股申万行业归属。POST /sw-stock-classify/list（分页）。"""
        return self._call(
            "sw_stock_classify", fetch_all=fetch_all, max_rows=max_rows,
            page_num=page_num, page_size=page_size, stock_code=stock_code,
        )

    def sw_industry_daily_stat(
        self, *, industry_code=None, start_date=None, end_date=None,
        page_num=1, page_size=DEFAULT_PAGE_SIZE, fetch_all=False, max_rows=DEFAULT_MAX_ROWS,
    ) -> Records:
        """申万行业日度统计。POST /sw-industry-daily-stat/list（分页）。"""
        return self._call(
            "sw_industry_daily_stat", fetch_all=fetch_all, max_rows=max_rows,
            page_num=page_num, page_size=page_size,
            industry_code=industry_code, start_date=start_date, end_date=end_date,
        )

    def sw_industry_capital_flow(
        self, *, industry_code=None, start_date=None, end_date=None,
        page_num=1, page_size=DEFAULT_PAGE_SIZE, fetch_all=False, max_rows=DEFAULT_MAX_ROWS,
    ) -> Records:
        """申万行业资金流。POST /sw-industry-capital-flow/list（分页）。"""
        return self._call(
            "sw_industry_capital_flow", fetch_all=fetch_all, max_rows=max_rows,
            page_num=page_num, page_size=page_size,
            industry_code=industry_code, start_date=start_date, end_date=end_date,
        )

    def capital_flow(
        self, *, stock_code=None, start_date=None, end_date=None,
        page_num=1, page_size=DEFAULT_PAGE_SIZE, fetch_all=False, max_rows=DEFAULT_MAX_ROWS,
    ) -> Records:
        """资金流向。POST /capital-flow/list（分页）。"""
        return self._call(
            "capital_flow", fetch_all=fetch_all, max_rows=max_rows,
            page_num=page_num, page_size=page_size,
            stock_code=stock_code, start_date=start_date, end_date=end_date,
        )

    def block_trade(
        self, *, stock_code=None, start_date=None, end_date=None,
        page_num=1, page_size=DEFAULT_PAGE_SIZE, fetch_all=False, max_rows=DEFAULT_MAX_ROWS,
    ) -> Records:
        """大宗交易。POST /block-trade/list（分页）。"""
        return self._call(
            "block_trade", fetch_all=fetch_all, max_rows=max_rows,
            page_num=page_num, page_size=page_size,
            stock_code=stock_code, start_date=start_date, end_date=end_date,
        )

    def margin_trading(
        self, *, stock_code=None, start_date=None, end_date=None,
        page_num=1, page_size=DEFAULT_PAGE_SIZE, fetch_all=False, max_rows=DEFAULT_MAX_ROWS,
    ) -> Records:
        """融资融券。POST /margin-trading/list（分页）。"""
        return self._call(
            "margin_trading", fetch_all=fetch_all, max_rows=max_rows,
            page_num=page_num, page_size=page_size,
            stock_code=stock_code, start_date=start_date, end_date=end_date,
        )

    def dragon_tiger(
        self, *, stock_code=None, start_date=None, end_date=None,
        page_num=1, page_size=DEFAULT_PAGE_SIZE, fetch_all=False, max_rows=DEFAULT_MAX_ROWS,
    ) -> Records:
        """龙虎榜。POST /dragon-tiger/list（分页）。"""
        return self._call(
            "dragon_tiger", fetch_all=fetch_all, max_rows=max_rows,
            page_num=page_num, page_size=page_size,
            stock_code=stock_code, start_date=start_date, end_date=end_date,
        )

    def pre_post_market(
        self, *, stock_code=None, start_date=None, end_date=None,
        page_num=1, page_size=DEFAULT_PAGE_SIZE, fetch_all=False, max_rows=DEFAULT_MAX_ROWS,
    ) -> Records:
        """盘前盘后成交。POST /pre-post-market/list（分页）。"""
        return self._call(
            "pre_post_market", fetch_all=fetch_all, max_rows=max_rows,
            page_num=page_num, page_size=page_size,
            stock_code=stock_code, start_date=start_date, end_date=end_date,
        )

    def share_capital(
        self, *, stock_code=None, start_date=None, end_date=None,
        page_num=1, page_size=DEFAULT_PAGE_SIZE, fetch_all=False, max_rows=DEFAULT_MAX_ROWS,
    ) -> Records:
        """股本数据。POST /share-capital/list（分页）。"""
        return self._call(
            "share_capital", fetch_all=fetch_all, max_rows=max_rows,
            page_num=page_num, page_size=page_size,
            stock_code=stock_code, start_date=start_date, end_date=end_date,
        )

    def share_trade(
        self, *, stock_code=None, start_date=None, end_date=None,
        page_num=1, page_size=DEFAULT_PAGE_SIZE, fetch_all=False, max_rows=DEFAULT_MAX_ROWS,
    ) -> Records:
        """增减持。POST /share-trade/list（分页）。"""
        return self._call(
            "share_trade", fetch_all=fetch_all, max_rows=max_rows,
            page_num=page_num, page_size=page_size,
            stock_code=stock_code, start_date=start_date, end_date=end_date,
        )

    def shareholder_stats(
        self, *, stock_code=None, report_year=None, quarter_type=None,
        page_num=1, page_size=DEFAULT_PAGE_SIZE, fetch_all=False, max_rows=DEFAULT_MAX_ROWS,
    ) -> Records:
        """股东统计。POST /shareholder-stats/list（分页）。quarter_type: 1~4。"""
        return self._call(
            "shareholder_stats", fetch_all=fetch_all, max_rows=max_rows,
            page_num=page_num, page_size=page_size,
            stock_code=stock_code, report_year=report_year, quarter_type=quarter_type,
        )

    def institutional_holding(
        self, *, stock_code=None, report_year=None, quarter_type=None,
        page_num=1, page_size=DEFAULT_PAGE_SIZE, fetch_all=False, max_rows=DEFAULT_MAX_ROWS,
    ) -> Records:
        """机构持股。POST /institutional-holding/list（分页）。quarter_type: 1~4。"""
        return self._call(
            "institutional_holding", fetch_all=fetch_all, max_rows=max_rows,
            page_num=page_num, page_size=page_size,
            stock_code=stock_code, report_year=report_year, quarter_type=quarter_type,
        )

    def financial_report(
        self, *, stock_code=None, report_year=None, quarter_type=None,
        page_num=1, page_size=DEFAULT_PAGE_SIZE, fetch_all=False, max_rows=DEFAULT_MAX_ROWS,
    ) -> Records:
        """财务报告。POST /financial-report/list（分页）。quarter_type: 1~4。"""
        return self._call(
            "financial_report", fetch_all=fetch_all, max_rows=max_rows,
            page_num=page_num, page_size=page_size,
            stock_code=stock_code, report_year=report_year, quarter_type=quarter_type,
        )

    def dividend_factor(
        self, *, stock_code=None, start_date=None, end_date=None,
        page_num=1, page_size=DEFAULT_PAGE_SIZE, fetch_all=False, max_rows=DEFAULT_MAX_ROWS,
    ) -> Records:
        """分红配送。POST /dividend-factor/list（分页）。"""
        return self._call(
            "dividend_factor", fetch_all=fetch_all, max_rows=max_rows,
            page_num=page_num, page_size=page_size,
            stock_code=stock_code, start_date=start_date, end_date=end_date,
        )

    def stock_limit_up_stats(
        self, *, stock_code=None, start_date=None, end_date=None,
        page_num=1, page_size=DEFAULT_PAGE_SIZE, fetch_all=False, max_rows=DEFAULT_MAX_ROWS,
    ) -> Records:
        """涨跌停统计。POST /stock-limit-up-stats/list（分页）。"""
        return self._call(
            "stock_limit_up_stats", fetch_all=fetch_all, max_rows=max_rows,
            page_num=page_num, page_size=page_size,
            stock_code=stock_code, start_date=start_date, end_date=end_date,
        )

    def trading_calendar(
        self, *, start_date=None, end_date=None,
        page_num=1, page_size=DEFAULT_PAGE_SIZE, fetch_all=False, max_rows=DEFAULT_MAX_ROWS,
    ) -> Records:
        """交易日历。POST /trading-calendar/list（分页）。"""
        return self._call(
            "trading_calendar", fetch_all=fetch_all, max_rows=max_rows,
            page_num=page_num, page_size=page_size,
            start_date=start_date, end_date=end_date,
        )

    def stock_realtime(self, *, stock_codes=None) -> Records:
        """股票实时快照（内存，不分页）。POST /stock-realtime/list。stock_codes 为空返回全部。"""
        return self._call("stock_realtime", stock_codes=stock_codes)
```

- [ ] **Step 4: 更新 `__init__.py` 导出公开 API**

Replace contents of `src/bihu_stock_data_client/__init__.py` with:
```python
"""bihu-stock-data-client: 对接 stock-data-server 的 Python 客户端 SDK。"""

from __future__ import annotations

from .client import StockDataClient
from .config import ClientConfig
from .decoder import Records
from .errors import (
    ApiError,
    AuthenticationError,
    ConfigurationError,
    ConnectionError,
    PaginationLimitError,
    RateLimitError,
    StockDataError,
    ValidationError,
)

__version__ = "0.1.0"

# 设计文档使用 bsdc.Client(...) 形式
Client = StockDataClient

__all__ = [
    "StockDataClient",
    "Client",
    "ClientConfig",
    "Records",
    "StockDataError",
    "ConfigurationError",
    "AuthenticationError",
    "RateLimitError",
    "ApiError",
    "PaginationLimitError",
    "ConnectionError",
    "ValidationError",
    "__version__",
]
```

- [ ] **Step 5: 运行测试，确认通过**

Run: `pytest tests/unit/test_client.py -v`
Expected: PASS（7 passed）。

- [ ] **Step 6: 提交**

Run:
```bash
git add src/bihu_stock_data_client/client.py src/bihu_stock_data_client/__init__.py tests/unit/test_client.py
git commit -m "feat(client): StockDataClient facade with 26 typed query methods (single-page)"
```

---

## Task 7: 自动分页（fetch_all + 流式迭代器 + max_rows 护栏）

**Files:**
- Modify: `src/bihu_stock_data_client/client.py`（填充 `_call_all`、新增 `_iter_pages` 与 21 个 `<name>_iter` 方法、补 `Iterator` 导入）
- Test: `tests/unit/test_pagination.py`

**Interfaces:**
- Consumes: Task 6 的 `_call_page`、`_validate`、`PaginationLimitError`、`Endpoint`
- Produces:
  - `_call_all(ep, *, max_rows, page_size, **biz) -> Records`：按 `total_page` 翻页聚合，超过 `max_rows` 抛 `PaginationLimitError`，返回 `Records`（`total_count/total_pages` 取末页，`page_num=1`，`page_size=len(rows)`）。
  - `_iter_pages(name, *, max_rows=DEFAULT_MAX_ROWS, page_size=DEFAULT_PAGE_SIZE, **biz) -> Iterator[Records]`：逐页 `yield`，超过 `max_rows` 抛 `PaginationLimitError`。
  - 21 个公开 `<name>_iter` 方法（仅分页接口），签名 = 各查询方法的业务参数 + `page_size` + `max_rows`，返回 `Iterator[Records]`。

- [ ] **Step 1: 写失败测试 `tests/unit/test_pagination.py`**

Create `tests/unit/test_pagination.py`:
```python
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
    responses = [{"code": "0000", "data": p, "traceId": "t"} for p in pages]
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
    responses = [{"code": "0000", "data": p, "traceId": "t"} for p in pages]
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
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `pytest tests/unit/test_pagination.py -v`
Expected: FAIL — `NotImplementedError`（`_call_all` 桩）；其余 `AttributeError`（`kline_daily_iter` 尚未实现）

- [ ] **Step 3: 实现 `_call_all`（替换桩）**

In `src/bihu_stock_data_client/client.py`, replace the `_call_all` stub body:
```python
    def _call_all(
        self, ep: Endpoint, *, max_rows: int, page_size: int, **biz: Any
    ) -> Records:
        # Task 7 实现
        raise NotImplementedError  # pragma: no cover
```
with:
```python
    def _call_all(
        self, ep: Endpoint, *, max_rows: int, page_size: int, **biz: Any
    ) -> Records:
        rows: list = []
        page_num = 1
        total_count: Optional[int] = None
        total_pages: Optional[int] = None
        while True:
            page = self._call_page(ep, page_num=page_num, page_size=page_size, **biz)
            rows.extend(page)
            total_count = page.total_count
            total_pages = page.total_pages
            if len(rows) > max_rows:
                raise PaginationLimitError(
                    f"'{ep.name}' 结果已达 {len(rows)} 行，超过 max_rows={max_rows}；"
                    f"请缩小查询范围或显式调高 max_rows"
                )
            if total_pages is not None and page_num >= total_pages:
                break
            if len(page) == 0:  # 兜底：空页即止
                break
            page_num += 1
        return Records(
            rows,
            total_count=total_count,
            total_pages=total_pages,
            page_num=1,
            page_size=len(rows),
        )
```

- [ ] **Step 4: 运行 fetch_all 测试，确认通过（迭代器测试仍失败）**

Run: `pytest tests/unit/test_pagination.py::test_fetch_all_aggregates_pages tests/unit/test_pagination.py::test_fetch_all_max_rows_guard -v`
Expected: 2 PASS。

- [ ] **Step 5: 实现 `_iter_pages` 与 21 个 `<name>_iter` 方法**

In `src/bihu_stock_data_client/client.py`:

(a) 将导入行 `from typing import Any, Optional` 改为：
```python
from typing import Any, Iterator, Optional
```

(b) 在 `_call_all` 方法之后、`# ---------------- 公开 API` 注释之前，新增私有生成器：
```python
    def _iter_pages(
        self,
        name: str,
        *,
        max_rows: int = DEFAULT_MAX_ROWS,
        page_size: int = DEFAULT_PAGE_SIZE,
        **biz: Any,
    ) -> Iterator[Records]:
        ep = self._by_name[name]
        self._validate(ep, biz, page_size=page_size)
        page_num = 1
        seen = 0
        while True:
            page = self._call_page(ep, page_num=page_num, page_size=page_size, **biz)
            if len(page) == 0:
                break
            yield page
            seen += len(page)
            if seen > max_rows:
                raise PaginationLimitError(
                    f"'{ep.name}' 已迭代 {seen} 行，超过 max_rows={max_rows}；"
                    f"请缩小查询范围或显式调高 max_rows"
                )
            if page.total_pages is not None and page_num >= page.total_pages:
                break
            page_num += 1
```

(c) 在 `client.py` 末尾（`stock_realtime` 方法之后）新增 21 个流式迭代方法：
```python
    # ---------------- 流式迭代（仅分页接口）----------------
    def kline_daily_iter(self, *, stock_code=None, start_date=None, end_date=None,
                         page_size=DEFAULT_PAGE_SIZE, max_rows=DEFAULT_MAX_ROWS) -> Iterator[Records]:
        """日K线行情，逐页 yield Records（流式，适合大数据集）。"""
        yield from self._iter_pages("kline_daily", max_rows=max_rows, page_size=page_size,
                                    stock_code=stock_code, start_date=start_date, end_date=end_date)

    def kline_daily_stat_iter(self, *, stock_code=None, start_date=None, end_date=None,
                              page_size=DEFAULT_PAGE_SIZE, max_rows=DEFAULT_MAX_ROWS) -> Iterator[Records]:
        """每日统计指标，逐页 yield。"""
        yield from self._iter_pages("kline_daily_stat", max_rows=max_rows, page_size=page_size,
                                    stock_code=stock_code, start_date=start_date, end_date=end_date)

    def kline_minute_snapshot_iter(self, *, stock_code=None,
                                   page_size=DEFAULT_PAGE_SIZE, max_rows=DEFAULT_MAX_ROWS) -> Iterator[Records]:
        """分钟K线快照，逐页 yield。"""
        yield from self._iter_pages("kline_minute_snapshot", max_rows=max_rows,
                                    page_size=page_size, stock_code=stock_code)

    def index_kline_daily_iter(self, *, index_code=None, start_date=None, end_date=None,
                               page_size=DEFAULT_PAGE_SIZE, max_rows=DEFAULT_MAX_ROWS) -> Iterator[Records]:
        """指数日K线，逐页 yield。"""
        yield from self._iter_pages("index_kline_daily", max_rows=max_rows, page_size=page_size,
                                    index_code=index_code, start_date=start_date, end_date=end_date)

    def index_constituent_iter(self, *, index_code=None, stock_code=None,
                               page_size=DEFAULT_PAGE_SIZE, max_rows=DEFAULT_MAX_ROWS) -> Iterator[Records]:
        """指数成分股，逐页 yield。"""
        yield from self._iter_pages("index_constituent", max_rows=max_rows, page_size=page_size,
                                    index_code=index_code, stock_code=stock_code)

    def sw_stock_classify_iter(self, *, stock_code=None,
                               page_size=DEFAULT_PAGE_SIZE, max_rows=DEFAULT_MAX_ROWS) -> Iterator[Records]:
        """个股申万行业归属，逐页 yield。"""
        yield from self._iter_pages("sw_stock_classify", max_rows=max_rows,
                                    page_size=page_size, stock_code=stock_code)

    def sw_industry_daily_stat_iter(self, *, industry_code=None, start_date=None, end_date=None,
                                    page_size=DEFAULT_PAGE_SIZE, max_rows=DEFAULT_MAX_ROWS) -> Iterator[Records]:
        """申万行业日度统计，逐页 yield。"""
        yield from self._iter_pages("sw_industry_daily_stat", max_rows=max_rows, page_size=page_size,
                                    industry_code=industry_code, start_date=start_date, end_date=end_date)

    def sw_industry_capital_flow_iter(self, *, industry_code=None, start_date=None, end_date=None,
                                      page_size=DEFAULT_PAGE_SIZE, max_rows=DEFAULT_MAX_ROWS) -> Iterator[Records]:
        """申万行业资金流，逐页 yield。"""
        yield from self._iter_pages("sw_industry_capital_flow", max_rows=max_rows, page_size=page_size,
                                    industry_code=industry_code, start_date=start_date, end_date=end_date)

    def capital_flow_iter(self, *, stock_code=None, start_date=None, end_date=None,
                          page_size=DEFAULT_PAGE_SIZE, max_rows=DEFAULT_MAX_ROWS) -> Iterator[Records]:
        """资金流向，逐页 yield。"""
        yield from self._iter_pages("capital_flow", max_rows=max_rows, page_size=page_size,
                                    stock_code=stock_code, start_date=start_date, end_date=end_date)

    def block_trade_iter(self, *, stock_code=None, start_date=None, end_date=None,
                         page_size=DEFAULT_PAGE_SIZE, max_rows=DEFAULT_MAX_ROWS) -> Iterator[Records]:
        """大宗交易，逐页 yield。"""
        yield from self._iter_pages("block_trade", max_rows=max_rows, page_size=page_size,
                                    stock_code=stock_code, start_date=start_date, end_date=end_date)

    def margin_trading_iter(self, *, stock_code=None, start_date=None, end_date=None,
                            page_size=DEFAULT_PAGE_SIZE, max_rows=DEFAULT_MAX_ROWS) -> Iterator[Records]:
        """融资融券，逐页 yield。"""
        yield from self._iter_pages("margin_trading", max_rows=max_rows, page_size=page_size,
                                    stock_code=stock_code, start_date=start_date, end_date=end_date)

    def dragon_tiger_iter(self, *, stock_code=None, start_date=None, end_date=None,
                          page_size=DEFAULT_PAGE_SIZE, max_rows=DEFAULT_MAX_ROWS) -> Iterator[Records]:
        """龙虎榜，逐页 yield。"""
        yield from self._iter_pages("dragon_tiger", max_rows=max_rows, page_size=page_size,
                                    stock_code=stock_code, start_date=start_date, end_date=end_date)

    def pre_post_market_iter(self, *, stock_code=None, start_date=None, end_date=None,
                             page_size=DEFAULT_PAGE_SIZE, max_rows=DEFAULT_MAX_ROWS) -> Iterator[Records]:
        """盘前盘后成交，逐页 yield。"""
        yield from self._iter_pages("pre_post_market", max_rows=max_rows, page_size=page_size,
                                    stock_code=stock_code, start_date=start_date, end_date=end_date)

    def share_capital_iter(self, *, stock_code=None, start_date=None, end_date=None,
                           page_size=DEFAULT_PAGE_SIZE, max_rows=DEFAULT_MAX_ROWS) -> Iterator[Records]:
        """股本数据，逐页 yield。"""
        yield from self._iter_pages("share_capital", max_rows=max_rows, page_size=page_size,
                                    stock_code=stock_code, start_date=start_date, end_date=end_date)

    def share_trade_iter(self, *, stock_code=None, start_date=None, end_date=None,
                         page_size=DEFAULT_PAGE_SIZE, max_rows=DEFAULT_MAX_ROWS) -> Iterator[Records]:
        """增减持，逐页 yield。"""
        yield from self._iter_pages("share_trade", max_rows=max_rows, page_size=page_size,
                                    stock_code=stock_code, start_date=start_date, end_date=end_date)

    def shareholder_stats_iter(self, *, stock_code=None, report_year=None, quarter_type=None,
                               page_size=DEFAULT_PAGE_SIZE, max_rows=DEFAULT_MAX_ROWS) -> Iterator[Records]:
        """股东统计，逐页 yield。quarter_type: 1~4。"""
        yield from self._iter_pages("shareholder_stats", max_rows=max_rows, page_size=page_size,
                                    stock_code=stock_code, report_year=report_year, quarter_type=quarter_type)

    def institutional_holding_iter(self, *, stock_code=None, report_year=None, quarter_type=None,
                                   page_size=DEFAULT_PAGE_SIZE, max_rows=DEFAULT_MAX_ROWS) -> Iterator[Records]:
        """机构持股，逐页 yield。quarter_type: 1~4。"""
        yield from self._iter_pages("institutional_holding", max_rows=max_rows, page_size=page_size,
                                    stock_code=stock_code, report_year=report_year, quarter_type=quarter_type)

    def financial_report_iter(self, *, stock_code=None, report_year=None, quarter_type=None,
                              page_size=DEFAULT_PAGE_SIZE, max_rows=DEFAULT_MAX_ROWS) -> Iterator[Records]:
        """财务报告，逐页 yield。quarter_type: 1~4。"""
        yield from self._iter_pages("financial_report", max_rows=max_rows, page_size=page_size,
                                    stock_code=stock_code, report_year=report_year, quarter_type=quarter_type)

    def dividend_factor_iter(self, *, stock_code=None, start_date=None, end_date=None,
                             page_size=DEFAULT_PAGE_SIZE, max_rows=DEFAULT_MAX_ROWS) -> Iterator[Records]:
        """分红配送，逐页 yield。"""
        yield from self._iter_pages("dividend_factor", max_rows=max_rows, page_size=page_size,
                                    stock_code=stock_code, start_date=start_date, end_date=end_date)

    def stock_limit_up_stats_iter(self, *, stock_code=None, start_date=None, end_date=None,
                                  page_size=DEFAULT_PAGE_SIZE, max_rows=DEFAULT_MAX_ROWS) -> Iterator[Records]:
        """涨跌停统计，逐页 yield。"""
        yield from self._iter_pages("stock_limit_up_stats", max_rows=max_rows, page_size=page_size,
                                    stock_code=stock_code, start_date=start_date, end_date=end_date)

    def trading_calendar_iter(self, *, start_date=None, end_date=None,
                              page_size=DEFAULT_PAGE_SIZE, max_rows=DEFAULT_MAX_ROWS) -> Iterator[Records]:
        """交易日历，逐页 yield。"""
        yield from self._iter_pages("trading_calendar", max_rows=max_rows, page_size=page_size,
                                    start_date=start_date, end_date=end_date)
```

- [ ] **Step 6: 运行 Task 7 全部测试，确认通过**

Run: `pytest tests/unit/test_pagination.py -v`
Expected: PASS（4 passed）。

- [ ] **Step 7: 运行全量测试 + mypy**

Run:
```bash
pytest -v
mypy src/bihu_stock_data_client
```
Expected: 全部单元测试 PASS；mypy 无错误。

- [ ] **Step 8: 提交**

Run:
```bash
git add src/bihu_stock_data_client/client.py tests/unit/test_pagination.py
git commit -m "feat(client): fetch_all + streaming iterators with max_rows guard"
```

---

## Task 8: 契约测试（离线，requests-mock + 真实样本）

**说明：** 契约测试确保客户端对列式格式与 `ResponseParam` 的解析与服务端实际输出严格一致。为每种请求 schema 至少取一个接口，用贴近服务端字段的真实样本打桩。

**Files:**
- Create: `tests/contract/test_contract.py`

**Interfaces:**
- Consumes: Task 6/7 的全部公开方法。

- [ ] **Step 1: 写契约测试 `tests/contract/test_contract.py`**

Create `tests/contract/test_contract.py`:
```python
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
```

- [ ] **Step 2: 运行契约测试，确认通过**

Run: `pytest tests/contract/test_contract.py -v`
Expected: PASS（7 passed）。

- [ ] **Step 3: 提交**

Run:
```bash
git add tests/contract/test_contract.py
git commit -m "test(contract): offline contract tests with realistic server samples"
```

---

## Task 9: 集成测试、README、示例与打包校验

**Files:**
- Create: `tests/integration/test_integration.py`
- Create: `README.md`
- Create: `CHANGELOG.md`
- Create: `examples/quickstart.py`
- Create: `examples/fetch_all_and_pandas.py`

- [ ] **Step 1: 写 opt-in 集成测试 `tests/integration/test_integration.py`**

Create `tests/integration/test_integration.py`:
```python
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
```

- [ ] **Step 2: 写 `README.md`**

Create `README.md`:
```markdown
# bihu-stock-data-client

Python 客户端 SDK，对接 [stock-data-server](../stock-data-server) 的 A 股数据 REST API。
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

所有异常继承 `bsdc.StockDataError`：`AuthenticationError`（401）、`RateLimitError`（限流）、
`ApiError`（业务错误，带 `code`/`trace_id`）、`PaginationLimitError`、`ConnectionError`、`ValidationError`。

## License

MIT
```

- [ ] **Step 3: 写 `CHANGELOG.md`**

Create `CHANGELOG.md`:
```markdown
# Changelog

## 0.1.0

- 首个版本。
- 26 个数据查询接口（日K、分钟K、财务、龙虎榜、资金流、交易日历、实时快照等）。
- API Key 认证（请求头 `X-API-Key`）。
- 列式数据解码为 `Records`（`list[dict]` 子类，带分页元信息）。
- 自动分页 `fetch_all` + `max_rows` 护栏。
- 可选 `to_pandas()` 转换（pandas 惰性导入）。
- 完整异常层次、可选重试、标准库日志。
```

- [ ] **Step 4: 写示例 `examples/quickstart.py`**

Create `examples/quickstart.py`:
```python
"""快速上手：单页查询、自动全量、错误处理。"""
import bihu_stock_data_client as bsdc


def main() -> None:
    client = bsdc.Client(api_key="你的 API Key")

    rows = client.kline_daily(stock_code="000001", start_date="2025-01-01")
    print(f"共 {rows.total_count} 条，本页 {len(rows)} 条")
    print(rows[0])

    all_rows = client.kline_daily(
        stock_code="000001", start_date="2024-01-01", fetch_all=True
    )
    print(f"全量 {len(all_rows)} 条")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: 写示例 `examples/fetch_all_and_pandas.py`**

Create `examples/fetch_all_and_pandas.py`:
```python
"""自动全量拉取 + 转 pandas（需 pip install pandas）。"""
import bihu_stock_data_client as bsdc


def main() -> None:
    client = bsdc.Client(api_key="你的 API Key")
    rows = client.kline_daily(
        stock_code="000001", start_date="2023-01-01", fetch_all=True
    )
    df = rows.to_pandas()
    print(df.head())
    print(df.describe())


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: 全量校验**

Run:
```bash
pytest -v
mypy src/bihu_stock_data_client
python -c "import bihu_stock_data_client as bsdc; print(bsdc.__version__); print(len([m for m in dir(bsdc.Client('x', 'http://h')) if not m.startswith('_')]))"
```
Expected: 全部单元 + 契约测试 PASS（集成测试 skip）；mypy 无错误；最后一行打印 `47`（26 个查询方法 + 21 个流式迭代方法）。

- [ ] **Step 7: 提交**

Run:
```bash
git add tests/integration README.md CHANGELOG.md examples
git commit -m "docs: README, examples, CHANGELOG + opt-in integration tests"
```

---

## 完成标准（Definition of Done）

- 全部单元测试 + 契约测试通过；`mypy src` 无错误。
- 26 个查询方法 + 21 个流式迭代方法（`<name>_iter`）可在 `bsdc.Client(...)` 上自动补全。
- `pytest -m integration` 在本地服务端 + 有效 Key 下端到端通过。
- README / examples / LICENSE / CHANGELOG 齐备；`pip install -e .` 可正常导入。
