"""
Fetch leveraged Nasdaq-100 ETFs (QLD 2x, TQQQ 3x) and build, for each:
  - buy & hold
  - trend following (SMA200)   -- Faber
  - mean reversion (RSI2)      -- Connors
Exports daily equity CSVs into results/ so compare_strategies.py can plot them.

IMPORTANT (signal on the underlying index):
The timing SIGNAL for QLD/TQQQ is computed on the underlying Nasdaq-100 index
(^NDX), NOT on the leveraged ETF price itself. The daily leverage reset and path
dependency make the ETF price a noisy, distorted proxy for the trend; the clean
index is the right series to decide "in / out". The position derived from the
index is then applied to the ETF's own daily returns.

Reuses the exact timing logic from second_backtest_timing.py.
"""

import os
import yfinance as yf
import pandas as pd
from second_backtest_timing import (
    trend_following, mean_reversion, apply_timing, stats, OUTDIR,
)

ETFS = ["QLD", "TQQQ"]
INDEX = "^NDX"           # Nasdaq-100 -- underlying index for QLD & TQQQ
START = "1990-01-01"


def get_price(ticker):
    s = yf.download(ticker, start=START, auto_adjust=True, progress=False)["Close"]
    if isinstance(s, pd.DataFrame):
        s = s.iloc[:, 0]
    return s.dropna()


def signal_on_index(index_price, etf_index):
    """Align the underlying index onto the ETF's trading calendar (forward-fill)
    so signals computed on the index line up day-by-day with the ETF returns."""
    return index_price.reindex(etf_index, method="ffill")


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
    ndx = get_price(INDEX)
    print(f"{INDEX}: {len(ndx)} days, {ndx.index.min().date()} -> {ndx.index.max().date()}")

    for etf in ETFS:
        price = get_price(etf)
        print(f"\n{etf}: {len(price)} days, {price.index.min().date()} -> {price.index.max().date()}")

        # Signal series = underlying Nasdaq-100 aligned to the ETF calendar.
        idx = signal_on_index(ndx, price.index)

        bh = price / price.iloc[0]
        # Positions decided on the INDEX, returns taken on the ETF.
        tr_eq, tr_pos = apply_timing(price, trend_following(idx))
        mr_eq, mr_pos = apply_timing(price, mean_reversion(idx))

        stats(bh, f"{etf} Buy & Hold")
        stats(tr_eq / tr_eq.iloc[0], f"{etf} Trend (SMA200 on NDX)")
        stats(mr_eq / mr_eq.iloc[0], f"{etf} MeanRev (RSI2 on NDX)")

        low = etf.lower()
        export(bh, None, f"{low}_buyhold")
        export(tr_eq, tr_pos, f"{low}_trend_sma200")
        export(mr_eq, mr_pos, f"{low}_meanrev_rsi2")

        # Export the underlying index aligned to the ETF calendar (normalized),
        # so the web page can recompute signals on the index client-side.
        idx_norm = idx / idx.iloc[0]
        pd.DataFrame({"index": idx_norm}).to_csv(
            os.path.join(OUTDIR, f"{low}_index.csv"), index_label="date")
        print(f"  wrote {os.path.join(OUTDIR, f'{low}_index.csv')}")


if __name__ == "__main__":
    main()
