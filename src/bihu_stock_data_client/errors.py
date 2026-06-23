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
