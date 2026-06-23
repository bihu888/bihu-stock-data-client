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
        **extra,
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
            **extra,
        )

    def kline_daily_stat(
        self, *, stock_code=None, start_date=None, end_date=None,
        page_num=1, page_size=DEFAULT_PAGE_SIZE, fetch_all=False, max_rows=DEFAULT_MAX_ROWS,
        **extra,
    ) -> Records:
        """每日统计指标。POST /kline-daily-stat/list（分页）。"""
        return self._call(
            "kline_daily_stat", fetch_all=fetch_all, max_rows=max_rows,
            page_num=page_num, page_size=page_size,
            stock_code=stock_code, start_date=start_date, end_date=end_date,
            **extra,
        )

    def kline_minute(self, *, stock_code, trade_date) -> Records:
        """按股票+日期查分钟K线。GET /kline-minute/{stock_code}/{trade_date}（不分页）。"""
        return self._call("kline_minute", stock_code=stock_code, trade_date=trade_date)

    def kline_minute_snapshot(
        self, *, stock_code=None,
        page_num=1, page_size=DEFAULT_PAGE_SIZE, fetch_all=False, max_rows=DEFAULT_MAX_ROWS,
        **extra,
    ) -> Records:
        """分钟K线快照。POST /kline-minute-snapshot/list（分页）。"""
        return self._call(
            "kline_minute_snapshot", fetch_all=fetch_all, max_rows=max_rows,
            page_num=page_num, page_size=page_size, stock_code=stock_code,
            **extra,
        )

    def index_basic(self) -> Records:
        """所有指数基础信息。GET /index-basic/list（不分页）。"""
        return self._call("index_basic")

    def index_kline_daily(
        self, *, index_code=None, start_date=None, end_date=None,
        page_num=1, page_size=DEFAULT_PAGE_SIZE, fetch_all=False, max_rows=DEFAULT_MAX_ROWS,
        **extra,
    ) -> Records:
        """指数日K线。POST /index-kline-daily/list（分页）。"""
        return self._call(
            "index_kline_daily", fetch_all=fetch_all, max_rows=max_rows,
            page_num=page_num, page_size=page_size,
            index_code=index_code, start_date=start_date, end_date=end_date,
            **extra,
        )

    def index_constituent(
        self, *, index_code=None, stock_code=None,
        page_num=1, page_size=DEFAULT_PAGE_SIZE, fetch_all=False, max_rows=DEFAULT_MAX_ROWS,
        **extra,
    ) -> Records:
        """指数成分股。POST /index-constituent/list（分页）。"""
        return self._call(
            "index_constituent", fetch_all=fetch_all, max_rows=max_rows,
            page_num=page_num, page_size=page_size,
            index_code=index_code, stock_code=stock_code,
            **extra,
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
        **extra,
    ) -> Records:
        """个股申万行业归属。POST /sw-stock-classify/list（分页）。"""
        return self._call(
            "sw_stock_classify", fetch_all=fetch_all, max_rows=max_rows,
            page_num=page_num, page_size=page_size, stock_code=stock_code,
            **extra,
        )

    def sw_industry_daily_stat(
        self, *, industry_code=None, start_date=None, end_date=None,
        page_num=1, page_size=DEFAULT_PAGE_SIZE, fetch_all=False, max_rows=DEFAULT_MAX_ROWS,
        **extra,
    ) -> Records:
        """申万行业日度统计。POST /sw-industry-daily-stat/list（分页）。"""
        return self._call(
            "sw_industry_daily_stat", fetch_all=fetch_all, max_rows=max_rows,
            page_num=page_num, page_size=page_size,
            industry_code=industry_code, start_date=start_date, end_date=end_date,
            **extra,
        )

    def sw_industry_capital_flow(
        self, *, industry_code=None, start_date=None, end_date=None,
        page_num=1, page_size=DEFAULT_PAGE_SIZE, fetch_all=False, max_rows=DEFAULT_MAX_ROWS,
        **extra,
    ) -> Records:
        """申万行业资金流。POST /sw-industry-capital-flow/list（分页）。"""
        return self._call(
            "sw_industry_capital_flow", fetch_all=fetch_all, max_rows=max_rows,
            page_num=page_num, page_size=page_size,
            industry_code=industry_code, start_date=start_date, end_date=end_date,
            **extra,
        )

    def capital_flow(
        self, *, stock_code=None, start_date=None, end_date=None,
        page_num=1, page_size=DEFAULT_PAGE_SIZE, fetch_all=False, max_rows=DEFAULT_MAX_ROWS,
        **extra,
    ) -> Records:
        """资金流向。POST /capital-flow/list（分页）。"""
        return self._call(
            "capital_flow", fetch_all=fetch_all, max_rows=max_rows,
            page_num=page_num, page_size=page_size,
            stock_code=stock_code, start_date=start_date, end_date=end_date,
            **extra,
        )

    def block_trade(
        self, *, stock_code=None, start_date=None, end_date=None,
        page_num=1, page_size=DEFAULT_PAGE_SIZE, fetch_all=False, max_rows=DEFAULT_MAX_ROWS,
        **extra,
    ) -> Records:
        """大宗交易。POST /block-trade/list（分页）。"""
        return self._call(
            "block_trade", fetch_all=fetch_all, max_rows=max_rows,
            page_num=page_num, page_size=page_size,
            stock_code=stock_code, start_date=start_date, end_date=end_date,
            **extra,
        )

    def margin_trading(
        self, *, stock_code=None, start_date=None, end_date=None,
        page_num=1, page_size=DEFAULT_PAGE_SIZE, fetch_all=False, max_rows=DEFAULT_MAX_ROWS,
        **extra,
    ) -> Records:
        """融资融券。POST /margin-trading/list（分页）。"""
        return self._call(
            "margin_trading", fetch_all=fetch_all, max_rows=max_rows,
            page_num=page_num, page_size=page_size,
            stock_code=stock_code, start_date=start_date, end_date=end_date,
            **extra,
        )

    def dragon_tiger(
        self, *, stock_code=None, start_date=None, end_date=None,
        page_num=1, page_size=DEFAULT_PAGE_SIZE, fetch_all=False, max_rows=DEFAULT_MAX_ROWS,
        **extra,
    ) -> Records:
        """龙虎榜。POST /dragon-tiger/list（分页）。"""
        return self._call(
            "dragon_tiger", fetch_all=fetch_all, max_rows=max_rows,
            page_num=page_num, page_size=page_size,
            stock_code=stock_code, start_date=start_date, end_date=end_date,
            **extra,
        )

    def pre_post_market(
        self, *, stock_code=None, start_date=None, end_date=None,
        page_num=1, page_size=DEFAULT_PAGE_SIZE, fetch_all=False, max_rows=DEFAULT_MAX_ROWS,
        **extra,
    ) -> Records:
        """盘前盘后成交。POST /pre-post-market/list（分页）。"""
        return self._call(
            "pre_post_market", fetch_all=fetch_all, max_rows=max_rows,
            page_num=page_num, page_size=page_size,
            stock_code=stock_code, start_date=start_date, end_date=end_date,
            **extra,
        )

    def share_capital(
        self, *, stock_code=None, start_date=None, end_date=None,
        page_num=1, page_size=DEFAULT_PAGE_SIZE, fetch_all=False, max_rows=DEFAULT_MAX_ROWS,
        **extra,
    ) -> Records:
        """股本数据。POST /share-capital/list（分页）。"""
        return self._call(
            "share_capital", fetch_all=fetch_all, max_rows=max_rows,
            page_num=page_num, page_size=page_size,
            stock_code=stock_code, start_date=start_date, end_date=end_date,
            **extra,
        )

    def share_trade(
        self, *, stock_code=None, start_date=None, end_date=None,
        page_num=1, page_size=DEFAULT_PAGE_SIZE, fetch_all=False, max_rows=DEFAULT_MAX_ROWS,
        **extra,
    ) -> Records:
        """增减持。POST /share-trade/list（分页）。"""
        return self._call(
            "share_trade", fetch_all=fetch_all, max_rows=max_rows,
            page_num=page_num, page_size=page_size,
            stock_code=stock_code, start_date=start_date, end_date=end_date,
            **extra,
        )

    def shareholder_stats(
        self, *, stock_code=None, report_year=None, quarter_type=None,
        page_num=1, page_size=DEFAULT_PAGE_SIZE, fetch_all=False, max_rows=DEFAULT_MAX_ROWS,
        **extra,
    ) -> Records:
        """股东统计。POST /shareholder-stats/list（分页）。quarter_type: 1~4。"""
        return self._call(
            "shareholder_stats", fetch_all=fetch_all, max_rows=max_rows,
            page_num=page_num, page_size=page_size,
            stock_code=stock_code, report_year=report_year, quarter_type=quarter_type,
            **extra,
        )

    def institutional_holding(
        self, *, stock_code=None, report_year=None, quarter_type=None,
        page_num=1, page_size=DEFAULT_PAGE_SIZE, fetch_all=False, max_rows=DEFAULT_MAX_ROWS,
        **extra,
    ) -> Records:
        """机构持股。POST /institutional-holding/list（分页）。quarter_type: 1~4。"""
        return self._call(
            "institutional_holding", fetch_all=fetch_all, max_rows=max_rows,
            page_num=page_num, page_size=page_size,
            stock_code=stock_code, report_year=report_year, quarter_type=quarter_type,
            **extra,
        )

    def financial_report(
        self, *, stock_code=None, report_year=None, quarter_type=None,
        page_num=1, page_size=DEFAULT_PAGE_SIZE, fetch_all=False, max_rows=DEFAULT_MAX_ROWS,
        **extra,
    ) -> Records:
        """财务报告。POST /financial-report/list（分页）。quarter_type: 1~4。"""
        return self._call(
            "financial_report", fetch_all=fetch_all, max_rows=max_rows,
            page_num=page_num, page_size=page_size,
            stock_code=stock_code, report_year=report_year, quarter_type=quarter_type,
            **extra,
        )

    def dividend_factor(
        self, *, stock_code=None, start_date=None, end_date=None,
        page_num=1, page_size=DEFAULT_PAGE_SIZE, fetch_all=False, max_rows=DEFAULT_MAX_ROWS,
        **extra,
    ) -> Records:
        """分红配送。POST /dividend-factor/list（分页）。"""
        return self._call(
            "dividend_factor", fetch_all=fetch_all, max_rows=max_rows,
            page_num=page_num, page_size=page_size,
            stock_code=stock_code, start_date=start_date, end_date=end_date,
            **extra,
        )

    def stock_limit_up_stats(
        self, *, stock_code=None, start_date=None, end_date=None,
        page_num=1, page_size=DEFAULT_PAGE_SIZE, fetch_all=False, max_rows=DEFAULT_MAX_ROWS,
        **extra,
    ) -> Records:
        """涨跌停统计。POST /stock-limit-up-stats/list（分页）。"""
        return self._call(
            "stock_limit_up_stats", fetch_all=fetch_all, max_rows=max_rows,
            page_num=page_num, page_size=page_size,
            stock_code=stock_code, start_date=start_date, end_date=end_date,
            **extra,
        )

    def trading_calendar(
        self, *, start_date=None, end_date=None,
        page_num=1, page_size=DEFAULT_PAGE_SIZE, fetch_all=False, max_rows=DEFAULT_MAX_ROWS,
        **extra,
    ) -> Records:
        """交易日历。POST /trading-calendar/list（分页）。"""
        return self._call(
            "trading_calendar", fetch_all=fetch_all, max_rows=max_rows,
            page_num=page_num, page_size=page_size,
            start_date=start_date, end_date=end_date,
            **extra,
        )

    def stock_realtime(self, *, stock_codes=None) -> Records:
        """股票实时快照（内存，不分页）。POST /stock-realtime/list。stock_codes 为空返回全部。"""
        return self._call("stock_realtime", stock_codes=stock_codes)
