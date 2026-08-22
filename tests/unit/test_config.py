import pytest

from bihu_stock_data_client.config import ClientConfig
from bihu_stock_data_client.errors import ConfigurationError


@pytest.fixture(autouse=True)
def _isolate_cwd(tmp_path, monkeypatch):
    """切到空 tmp_path，避免本地/项目根的 .env 污染配置测试。"""
    monkeypatch.chdir(tmp_path)
    yield


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


def test_dotenv_loaded(tmp_path, monkeypatch):
    """from_env() 自动加载工作目录下的 .env 文件。"""
    monkeypatch.delenv("BIHU_STOCK_DATA_API_KEY", raising=False)
    monkeypatch.delenv("BIHU_STOCK_DATA_BASE_URL", raising=False)
    (tmp_path / ".env").write_text(
        "BIHU_STOCK_DATA_API_KEY=fromfile\n"
        "BIHU_STOCK_DATA_BASE_URL=http://file:9800/stock/data\n",
        encoding="utf-8",
    )
    cfg = ClientConfig.from_env()
    assert cfg.api_key == "fromfile"
    assert cfg.base_url == "http://file:9800/stock/data"


def test_env_overrides_dotenv(tmp_path, monkeypatch):
    """已存在的环境变量优先级高于 .env（load_dotenv 默认 override=False）。"""
    monkeypatch.delenv("BIHU_STOCK_DATA_API_KEY", raising=False)
    monkeypatch.setenv("BIHU_STOCK_DATA_API_KEY", "envkey")
    (tmp_path / ".env").write_text(
        "BIHU_STOCK_DATA_API_KEY=fromfile\n",
        encoding="utf-8",
    )
    cfg = ClientConfig.from_env()
    assert cfg.api_key == "envkey"
