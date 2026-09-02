from __future__ import annotations

import os
from pathlib import Path

import duckdb
import pandas as pd


SYMBOL = "510180.SH"
START = "2026-01-01"
END = "2026-06-30"
INITIAL_CAPITAL = 1_000_000.0
WINDOW = 20
STD_MULTIPLIER = 2.0


def main() -> None:
    env_path = Path(__file__).parents[1] / ".env"
    root = next(
        (line.split("=", 1)[1].strip() for line in env_path.read_text(encoding="utf-8").splitlines()
         if line.startswith("PARQUET_ROOT_PATH=")),
        "",
    )
    if not root:
        raise RuntimeError("PARQUET_ROOT_PATH is missing")

    patterns = [
        os.path.join(root, "fund_daily_post", "month=2025*", "part-0.parquet"),
        os.path.join(root, "fund_daily_post", "month=2026*", "part-0.parquet"),
    ]
    sql = """
        SELECT strptime(CAST(date AS VARCHAR), '%Y%m%d')::DATE AS date, close
        FROM read_parquet(?, union_by_name=true)
        WHERE symbol = ? AND CAST(date AS VARCHAR) BETWEEN '20251201' AND '20260630'
        ORDER BY date
    """
    con = duckdb.connect()
    df = con.execute(sql, [patterns, SYMBOL]).df()
    if df.empty:
        raise RuntimeError(f"no data for {SYMBOL}")
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df = df.dropna(subset=["close"]).drop_duplicates("date").sort_values("date")
    df["middle"] = df["close"].rolling(WINDOW).mean()
    df["std"] = df["close"].rolling(WINDOW).std(ddof=0)
    df["upper"] = df["middle"] + STD_MULTIPLIER * df["std"]
    df["lower"] = df["middle"] - STD_MULTIPLIER * df["std"]

    test = df[df["date"].between(START, END)].copy().reset_index(drop=True)
    position = 0
    cash = INITIAL_CAPITAL
    units = 0.0
    equity = []
    trades = []

    for _, row in test.iterrows():
        if position == 0 and row.close < row.lower:
            units = cash / row.close
            cash = 0.0
            position = 1
            trades.append((row.date.date(), "BUY", row.close, row.lower, row.upper))
        elif position == 1 and row.close > row.upper:
            cash = units * row.close
            units = 0.0
            position = 0
            trades.append((row.date.date(), "SELL", row.close, row.lower, row.upper))
        equity.append(cash + units * row.close)

    test["equity"] = equity
    if position:
        trades.append((test.iloc[-1].date.date(), "MARK", test.iloc[-1].close, test.iloc[-1].lower, test.iloc[-1].upper))
    test["peak"] = test.equity.cummax()
    test["drawdown"] = test.equity / test.peak - 1
    total_return = test.equity.iloc[-1] / INITIAL_CAPITAL - 1
    years = (test.date.iloc[-1] - test.date.iloc[0]).days / 365.25
    annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0.0
    daily_return = test.equity.pct_change().fillna(0)
    sharpe = daily_return.mean() / daily_return.std() * (252**0.5) if daily_return.std() else 0.0
    print(f"rows={len(test)} data_start={df.date.min().date()} data_end={df.date.max().date()}")
    print(f"initial={INITIAL_CAPITAL:.2f} final={test.equity.iloc[-1]:.2f}")
    print(f"total_return={total_return:.6%} annual_return={annual_return:.6%} max_drawdown={test.drawdown.min():.6%} sharpe={sharpe:.4f}")
    print(f"buys={sum(t[1] == 'BUY' for t in trades)} sells={sum(t[1] == 'SELL' for t in trades)} position_end={position}")
    for date, side, price, lower, upper in trades:
        print(f"trade {date} {side} price={price:.6f} lower={lower:.6f} upper={upper:.6f}")


if __name__ == "__main__":
    main()
