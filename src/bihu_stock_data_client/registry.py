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
