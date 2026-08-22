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

    字典键保留服务端原始列名（本服务端为 snake_case，如 'stock_code'、'close'）。
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
