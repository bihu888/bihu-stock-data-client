"""客户端配置：参数 + 环境变量兜底。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import find_dotenv, load_dotenv

from .errors import ConfigurationError

ENV_API_KEY = "BIHU_STOCK_DATA_API_KEY"
ENV_BASE_URL = "BIHU_STOCK_DATA_BASE_URL"
DEFAULT_BASE_URL = "https://stock.bihu888.cn/stock/data"
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
        load_dotenv(find_dotenv(usecwd=True))  # 从 cwd 向上查找 .env；已存在的环境变量优先级更高
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
