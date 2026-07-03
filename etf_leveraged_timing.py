"""
Fetch leveraged Nasdaq-100 ETFs (QLD 2x, TQQQ 3x) and build, for each:
  - buy & hold
  - trend following (SMA200)   -- Faber
  - mean reversion (RSI2)      -- Connors
Exports daily equity CSVs into results/ so compare_strategies.py can plot them.

Reuses the exact timing logic from second_backtest_timing.py.
"""

import os
import yfinance as yf
import pandas as pd
from second_backtest_timing import (
    trend_following, mean_reversion, apply_timing, stats, OUTDIR,
)

ETFS = ["QLD", "TQQQ"]
START = "1990-01-01"


def get_price(ticker):
    s = yf.download(ticker, start=START, auto_adjust=True, progress=False)["Close"]
    if isinstance(s, pd.DataFrame):
        s = s.iloc[:, 0]
    return s.dropna()


def export(equity, pos, name):
    equity = equity / equity.iloc[0]
    out = pd.DataFrame({"equity": equity, "daily_return": equity.pct_change()})
    if pos is not None:
        out["position"] = pos.shift(1).fillna(0.0)
    path = os.path.join(OUTDIR, f"{name}.csv")
    out.to_csv(path, index_label="date")
    print(f"  wrote {path}")


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    for etf in ETFS:
        price = get_price(etf)
        print(f"\n{etf}: {len(price)} days, {price.index.min().date()} -> {price.index.max().date()}")

        bh = price / price.iloc[0]
        tr_eq, tr_pos = apply_timing(price, trend_following(price))
        mr_eq, mr_pos = apply_timing(price, mean_reversion(price))

        stats(bh, f"{etf} Buy & Hold")
        stats(tr_eq / tr_eq.iloc[0], f"{etf} Trend (SMA200)")
        stats(mr_eq / mr_eq.iloc[0], f"{etf} MeanRev (RSI2)")

        low = etf.lower()
        export(bh, None, f"{low}_buyhold")
        export(tr_eq, tr_pos, f"{low}_trend_sma200")
        export(mr_eq, mr_pos, f"{low}_meanrev_rsi2")


if __name__ == "__main__":
    main()
