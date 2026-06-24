"""自动全量拉取 + 转 pandas（需 pip install pandas）。"""
import bihu_stock_data_client as bsdc


def main() -> None:
    client = bsdc.Client(api_key="你的 API Key")
    rows = client.kline_daily(
        stock_code="000001", start_date="2023-01-01", fetch_all=True
    )
    df = rows.to_pandas()
    print(df.head())
    print(df.describe())


if __name__ == "__main__":
    main()
