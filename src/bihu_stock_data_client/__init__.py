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

__version__ = "0.3.0"

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
