"""
Second backtest: time the BEST strategy (Top-1 equal-weight equity curve) with
two simple, well-documented equity techniques.

Approach 1 -- TREND FOLLOWING: 200-day SMA rule (Meb Faber, "A Quantitative
    Approach to Tactical Asset Allocation", 2007). Hold when price is above its
    200-day simple moving average, otherwise move to cash. This is THE canonical
    long-only trend filter for equities: it captures the momentum/trend premium
    and sidesteps the worst drawdowns. Parameters: lookback = 200. (1 param)

Approach 2 -- MEAN REVERSION: RSI(2) rule (Larry Connors & Cesar Alvarez,
    "Short Term Trading Strategies That Work", 2008). Equity indices mean-revert
    at SHORT horizons: buy oversold, exit on the bounce. Buy when RSI(2) < 10,
    exit when close > 5-day SMA. Parameters: rsi_period = 2, buy_threshold = 10,
    exit_sma = 5. (3 params)

Both signals are LAGGED one day (trade on next day's return) to avoid lookahead.
When out of the market, return = 0 (cash, no interest assumed -> conservative).
"""

import os
import pandas as pd
import matplotlib.pyplot as plt

BEST = "results/top1_equalweight.csv"   # best strategy by CAGR/total return
OUTDIR = "results"

# --- Trend following param ---
SMA_TREND = 200
# --- Mean reversion params ---
RSI_PERIOD = 2
RSI_BUY = 10
EXIT_SMA = 5


def rsi(series, period):
    """Wilder's RSI."""
    delta = series.diff()
    up = delta.clip(lower=0.0)
    down = -delta.clip(upper=0.0)
    roll_up = up.ewm(alpha=1 / period, adjust=False).mean()
    roll_down = down.ewm(alpha=1 / period, adjust=False).mean()
    rs = roll_up / roll_down.replace(0.0, 1e-12)
    return 100.0 - 100.0 / (1.0 + rs)


def trend_following(price):
    """Long when price > SMA(200), else cash. Returns a 0/1 position series."""
    sma = price.rolling(SMA_TREND).mean()
    pos = (price > sma).astype(float)
    return pos


def mean_reversion(price):
    """Connors RSI(2): enter when RSI(2)<threshold, exit when close>SMA(5)."""
    r = rsi(price, RSI_PERIOD)
    exit_ma = price.rolling(EXIT_SMA).mean()
    pos = pd.Series(0.0, index=price.index)
    in_pos = False
    for i in range(len(price)):
        if not in_pos:
            if r.iloc[i] < RSI_BUY:
                in_pos = True
        else:
            if price.iloc[i] > exit_ma.iloc[i]:
                in_pos = False
        pos.iloc[i] = 1.0 if in_pos else 0.0
    return pos


def apply_timing(price, position):
    """Equity of trading `price` with a lagged position (0/1)."""
    underlying_ret = price.pct_change().fillna(0.0)
    pos = position.shift(1).fillna(0.0)          # trade next day -> no lookahead
    strat_ret = pos * underlying_ret
    equity = (1.0 + strat_ret).cumprod()
    return equity, pos


def stats(equity, label):
    total = equity.iloc[-1] / equity.iloc[0] - 1
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    cagr = (equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1
    ret = equity.pct_change().dropna()
    sharpe = (ret.mean() / ret.std()) * (252 ** 0.5) if ret.std() > 0 else float("nan")
    mdd = (equity / equity.cummax() - 1).min()
    print(f"{label:26s} total:{total:>10.1%}  CAGR:{cagr:>6.2%}  "
          f"Sharpe:{sharpe:>5.2f}  maxDD:{mdd:>7.1%}")
    return dict(total=total, cagr=cagr, sharpe=sharpe, mdd=mdd)


def main():
    df = pd.read_csv(BEST, parse_dates=["date"]).set_index("date")
    price = df["equity"]
    print(f"Best strategy underlying: {BEST}  ({len(price)} days, "
          f"{price.index.min().date()} -> {price.index.max().date()})")

    buyhold = price / price.iloc[0]
    trend_eq, trend_pos = apply_timing(price, trend_following(price))
    mr_eq, mr_pos = apply_timing(price, mean_reversion(price))
    trend_eq /= trend_eq.iloc[0]
    mr_eq /= mr_eq.iloc[0]

    print("\n--- Timing the best strategy (Top-1) ---")
    stats(buyhold, "Buy & Hold (Top-1)")
    r_tr = stats(trend_eq, "Trend following (SMA200)")
    r_mr = stats(mr_eq, "Mean reversion (RSI2)")
    print(f"\nTime in market -> trend: {trend_pos.mean():.0%}   "
          f"mean-reversion: {mr_pos.mean():.0%}")

    # Export daily time series
    os.makedirs(OUTDIR, exist_ok=True)
    for eq, pos, name in [(buyhold, None, "top1_buyhold"),
                          (trend_eq, trend_pos, "top1_trend_sma200"),
                          (mr_eq, mr_pos, "top1_meanrev_rsi2")]:
        out = pd.DataFrame({"equity": eq, "daily_return": eq.pct_change()})
        if pos is not None:
            out["position"] = pos.shift(1).fillna(0.0)
        path = os.path.join(OUTDIR, f"{name}.csv")
        out.to_csv(path, index_label="date")
        print(f"  wrote {path}")

    # Plot
    fig, ax = plt.subplots(figsize=(13, 7))
    ax.plot(buyhold.index, buyhold, label="Top-1 Buy & Hold", color="black", lw=1.6, alpha=0.8)
    ax.plot(trend_eq.index, trend_eq,
            label=f"Trend following (SMA{SMA_TREND})", lw=1.6)
    ax.plot(mr_eq.index, mr_eq,
            label=f"Mean reversion (RSI{RSI_PERIOD}<{RSI_BUY})", lw=1.6)
    ax.set_yscale("log")
    ax.set_title("Timing the best strategy (Top-1): Trend Following vs Mean Reversion (log)")
    ax.set_ylabel("Growth of $1 (log)")
    ax.set_xlabel("Date")
    ax.grid(True, which="both", ls=":", alpha=0.4)
    ax.legend(loc="upper left")
    fig.tight_layout()
    out = "second_backtest_timing.png"
    fig.savefig(out, dpi=130)
    print(f"\nSaved plot -> {out}")


if __name__ == "__main__":
    main()
