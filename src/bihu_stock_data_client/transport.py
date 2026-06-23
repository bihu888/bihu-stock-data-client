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
