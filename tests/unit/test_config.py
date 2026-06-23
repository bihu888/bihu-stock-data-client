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
