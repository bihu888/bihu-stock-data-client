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
