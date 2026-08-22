"""快速上手：单页查询、自动全量、错误处理。"""
import bihu_stock_data_client as bsdc


def main() -> None:
    client = bsdc.Client(api_key="你的 API Key")

    rows = client.kline_daily(stock_code="000001.SZ", start_date="2025-01-01")
    print(f"共 {rows.total_count} 条，本页 {len(rows)} 条")
    print(rows[0])

    all_rows = client.kline_daily(
        stock_code="000001.SZ", start_date="2024-01-01", fetch_all=True
    )
    print(f"全量 {len(all_rows)} 条")


if __name__ == "__main__":
    main()
