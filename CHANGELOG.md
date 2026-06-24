# Changelog

## 0.1.0

- 首个版本。
- 26 个数据查询接口（日K、分钟K、财务、龙虎榜、资金流、交易日历、实时快照等）。
- API Key 认证（请求头 `X-API-Key`）。
- 列式数据解码为 `Records`（`list[dict]` 子类，带分页元信息）。
- 自动分页 `fetch_all` + `max_rows` 护栏。
- 可选 `to_pandas()` 转换（pandas 惰性导入）。
- 完整异常层次、可选重试、标准库日志。
