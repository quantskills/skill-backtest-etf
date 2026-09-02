"""调试 panda_data 0.1.0 的 ETF 数据口径。"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv


def call(api, name, **kwargs):
    fn = getattr(api, name, None)
    if fn is None:
        print(f"[{name}] unsupported")
        return None
    try:
        value = fn(**kwargs)
        df = value if isinstance(value, pd.DataFrame) else pd.DataFrame(value)
        print(f"[{name}] rows={len(df)} columns={list(df.columns)}")
        print(df.head(3).to_string(index=False) if not df.empty else "empty")
        return df
    except Exception as exc:
        print(f"[{name}] {type(exc).__name__}: {str(exc)[:300]}")
        return None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", default="510050.SH")
    p.add_argument("--start", default="20250101")
    p.add_argument("--end", default="20250110")
    a = p.parse_args()
    load_dotenv(Path(__file__).parents[1] / ".env")
    import panda_data
    common = dict(start_date=a.start, end_date=a.end, symbol=a.symbol)
    call(panda_data, "get_fund_detail", symbol=a.symbol, fields=["symbol", "name", "exchange", "etf_lof_type", "is_class_fund"])
    daily = call(panda_data, "get_fund_daily", **common)
    post = call(panda_data, "get_fund_daily_post", **common)
    pre = call(panda_data, "get_fund_daily_pre", **common)
    nav = call(panda_data, "get_fund_nav", **common)
    for df, col, label in [(daily, "close", "market_return"), (post, "close", "post_return"), (pre, "close", "pre_return"), (nav, "unit_nav", "nav_return"), (nav, "accumulated_nav", "total_return")]:
        if df is not None and {"symbol", col}.issubset(df.columns):
            x = df.sort_values(["symbol", "date"]).copy()
            x[label] = pd.to_numeric(x[col], errors="coerce").groupby(x["symbol"]).pct_change()
            print(f"{label}:\n{x[['symbol', 'date', label]].dropna().head().to_string(index=False)}")
    for name in ("get_fund_etf_dividend", "get_fund_etf_split", "get_fund_etf_cr", "get_fund_etf_cr_limits", "get_fund_etf_cr_net", "get_fund_etf_constituents"):
        call(panda_data, name, **common)


if __name__ == "__main__":
    main()
