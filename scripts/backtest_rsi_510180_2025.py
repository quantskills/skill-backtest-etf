from __future__ import annotations

import os
from pathlib import Path

import duckdb
import pandas as pd


SYMBOL = "510180.SH"
INITIAL_CAPITAL = 1_000_000.0


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    return 100 - 100 / (1 + gain / loss)


def main() -> None:
    env = Path(__file__).parents[1] / ".env"
    root = next((x.split("=", 1)[1].strip() for x in env.read_text(encoding="utf-8").splitlines()
                 if x.startswith("PARQUET_ROOT_PATH=")), "")
    patterns = [os.path.join(root, "fund_daily_post", "month=2024*", "part-0.parquet"),
                os.path.join(root, "fund_daily_post", "month=2025*", "part-0.parquet")]
    df = duckdb.connect().execute("""
        SELECT strptime(CAST(date AS VARCHAR), '%Y%m%d')::DATE AS date, close
        FROM read_parquet(?, union_by_name=true)
        WHERE symbol = ? AND CAST(date AS VARCHAR) BETWEEN '20241201' AND '20251231'
        ORDER BY date
    """, [patterns, SYMBOL]).df()
    if df.empty:
        raise RuntimeError(f"no data for {SYMBOL}")
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df = df.dropna(subset=["close"]).drop_duplicates("date").sort_values("date")
    df["rsi14"] = rsi(df.close)
    test = df[df.date.between("2025-01-01", "2025-12-31")].reset_index(drop=True)

    cash, units, position = INITIAL_CAPITAL, 0.0, 0
    equity, trades = [], []
    for _, row in test.iterrows():
        if position == 0 and row.rsi14 < 30:
            units, cash, position = cash / row.close, 0.0, 1
            trades.append((row.date.date(), "BUY", row.close, row.rsi14))
        elif position == 1 and row.rsi14 > 70:
            cash, units, position = units * row.close, 0.0, 0
            trades.append((row.date.date(), "SELL", row.close, row.rsi14))
        equity.append(cash + units * row.close)

    test["equity"] = equity
    if position:
        trades.append((test.iloc[-1].date.date(), "MARK", test.iloc[-1].close, test.iloc[-1].rsi14))
    test["drawdown"] = test.equity / test.equity.cummax() - 1
    total = test.equity.iloc[-1] / INITIAL_CAPITAL - 1
    years = (test.date.iloc[-1] - test.date.iloc[0]).days / 365.25
    annual = (1 + total) ** (1 / years) - 1
    returns = test.equity.pct_change().fillna(0)
    sharpe = returns.mean() / returns.std() * (252**0.5) if returns.std() else 0.0
    print(f"rows={len(test)} data_start={df.date.min().date()} data_end={df.date.max().date()}")
    print(f"initial={INITIAL_CAPITAL:.2f} final={test.equity.iloc[-1]:.2f}")
    print(f"total_return={total:.6%} annual_return={annual:.6%} max_drawdown={test.drawdown.min():.6%} sharpe={sharpe:.4f}")
    print(f"buys={sum(x[1] == 'BUY' for x in trades)} sells={sum(x[1] == 'SELL' for x in trades)} position_end={position}")
    for date, side, price, value in trades:
        print(f"trade {date} {side} price={price:.6f} rsi14={value:.4f}")


if __name__ == "__main__":
    main()
