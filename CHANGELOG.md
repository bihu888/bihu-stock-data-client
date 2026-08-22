# Changelog

## 0.2.0

- **破坏性变更**：跟随 stock-data-server 更新，替换两个旧接口并新增一个（均位于服务端 `/market` 控制器）：
  - `stock_realtime`（POST `/stock-realtime/list`，按 `stock_codes` 批量）→ `market_quote`（GET `/market/quote/{stock_code}`，实时五档行情）。
  - `kline_minute_snapshot`（POST 分页）→ `market_kline_minute`（GET `/market/kline-minute/{stock_code}`，当日分钟K线）。
  - 新增 `market_transaction`（GET `/market/transaction/{stock_code}?max_count=N`，当日分笔成交，服务端自动分页）。
- 新增 `chip_distribution`（POST `/chip-distribution/list`，按价格区间查筹码分布，分页）。
- 三个 `/market` 接口均为 GET 路径参数、非分页，返回标准列式 `{column, item}`，复用 `decode_columnar` 解码。
- `HttpClient.request` 新增 `params` 关键字参数；`_call_page` 对 GET 请求将 `Endpoint.params` 以 camelCase 查询参数发出（与 POST 请求体键的 case 约定一致）。
- 接口总数 26 → 28。
- 新增 `.env` 支持：构造时经 `load_dotenv(find_dotenv(usecwd=True))` 从当前目录向上查找，已有环境变量优先；依赖新增 `python-dotenv`。

## 0.1.0

- 首个版本。
- 26 个数据查询接口（日K、分钟K、财务、龙虎榜、资金流、交易日历、实时快照等）。
- API Key 认证（请求头 `X-API-Key`）。
- 列式数据解码为 `Records`（`list[dict]` 子类，带分页元信息）。
- 自动分页 `fetch_all` + `max_rows` 护栏。
- 可选 `to_pandas()` 转换（pandas 惰性导入）。
- 完整异常层次、可选重试、标准库日志。
