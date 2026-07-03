"""
Backtest: "Hold an equal-weighted basket of the N largest S&P 500 companies."

Strategy
--------
At any time, hold an EQUAL-WEIGHTED portfolio of the top-N constituents of the
S&P 500 by index weight (~= largest market caps). Rebalance to equal weight and
rotate names whenever the top-N ranking changes. N is a parameter (`--tops`),
so N=1 reduces to "always hold the single #1 company".

Compare against buying and holding the S&P 500 index.

Data / honesty note
-------------------
Real S&P 500 composition (daily membership, 1996-present) is loaded from the
fja05680/sp500 dataset (`sp500_historical_components.csv`) and used to VALIDATE
that every name we hold was a genuine index member on its date.

That dataset gives membership only, not index *weights*, and no free source
exposes historical weights. So the *ranking* of the largest companies cannot be
derived purely from free data. The ranking below (`TOP_RANKING`) is a curated,
membership-validated timeline of the largest S&P 500 companies by market cap
through history (well documented). The backtest runs on real yfinance prices
(split/dividend adjusted, so segment returns approximate total return).

Benchmark defaults to ^SP500TR (total-return index) for a fair, dividend-
inclusive comparison; falls back to ^GSPC (price only) if unavailable.

Usage
-----
    python sp500_top_constituent_backtest.py                 # plots Top-1 & Top-5
    python sp500_top_constituent_backtest.py --tops 1 3 5 10 # any set of N
"""

import argparse
import sys
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf

START = "1990-01-01"
END = None  # today
MEMBERSHIP_CSV = "sp500_historical_components.csv"  # fja05680/sp500 (since 1996)

# Curated timeline of the LARGEST S&P 500 companies by market cap, ranked.
# (start_date, [ticker1, ticker2, ...]) -- ordered #1, #2, #3, ...
# Each entry is in effect until the next entry's start_date. Provide >= the max
# N you intend to test. Approximate era rankings based on documented market-cap
# history; edit freely to refine.
TOP_RANKING = [
    ("1990-01-01", ["XOM", "IBM", "GE",   "MO",   "MRK",  "KO",   "WMT",  "T"]),
    ("1993-01-01", ["GE",  "XOM", "KO",   "MRK",  "WMT",  "MO",   "IBM",  "PG"]),
    ("1998-06-01", ["MSFT","GE",  "INTC", "WMT",  "XOM",  "CSCO", "KO",   "IBM"]),
    ("2000-06-01", ["GE",  "MSFT","CSCO", "INTC", "XOM",  "WMT",  "ORCL", "IBM"]),
    ("2005-11-01", ["XOM", "GE",  "MSFT", "C",    "WMT",  "PFE",  "BAC",  "JNJ"]),
    ("2010-06-01", ["XOM", "AAPL","MSFT", "GE",   "WMT",  "PG",   "JPM",  "JNJ"]),
    ("2012-06-01", ["AAPL","XOM", "MSFT", "GOOGL","GE",   "WMT",  "BRK-B","JNJ"]),
    ("2016-06-01", ["AAPL","GOOGL","MSFT","AMZN", "XOM",  "BRK-B","JNJ",  "GE"]),
    ("2018-11-01", ["MSFT","AAPL","AMZN", "GOOGL","BRK-B","JPM",  "JNJ",  "XOM"]),
    ("2020-06-01", ["AAPL","MSFT","AMZN", "GOOGL","META", "BRK-B","JNJ",  "V"]),
    ("2021-06-01", ["AAPL","MSFT","GOOGL","AMZN", "TSLA", "META", "NVDA", "BRK-B"]),
    ("2023-06-01", ["AAPL","MSFT","GOOGL","AMZN", "NVDA", "META", "TSLA", "BRK-B"]),
    ("2024-06-18", ["NVDA","AAPL","MSFT", "GOOGL","AMZN", "META", "BRK-B","TSLA"]),
]


# ---------------------------------------------------------------- composition
def load_membership(path=MEMBERSHIP_CSV):
    """Load real S&P 500 historical composition (date -> set of tickers)."""
    m = pd.read_csv(path)
    m["date"] = pd.to_datetime(m["date"])
    m = m.sort_values("date").set_index("date")
    m["members"] = m["tickers"].apply(lambda s: set(s.split(",")))
    return m


# yfinance ticker -> possible spellings in the composition dataset
TICKER_ALIASES = {
    "BRK-B": ["BRK.B", "BRK-B"],
    "META":  ["META", "FB"],   # Facebook renamed to Meta in 2022
    "GOOGL": ["GOOGL", "GOOG"],
}


def was_member(membership, ticker, when):
    when = pd.Timestamp(when)
    prior = membership.index[membership.index <= when]
    if len(prior) == 0:
        return None  # before dataset coverage (pre-1996)
    members = membership.loc[prior[-1], "members"]
    return any(sp in members for sp in TICKER_ALIASES.get(ticker, [ticker]))


def validate_ranking(ranking, membership, max_n):
    print("\n--- Validating top picks against real composition data ---")
    for d, names in ranking:
        checked = names[:max_n]
        bad = [t for t in checked if was_member(membership, t, d) is False]
        pre = was_member(membership, checked[0], d) is None
        status = "n/a (pre-1996)" if pre else ("OK" if not bad else f"NOT MEMBERS: {bad}")
        print(f"  {d}  top{max_n}: {status}")


# --------------------------------------------------------------------- prices
def load_prices(tickers, start, end):
    print(f"Downloading prices for {len(tickers)} tickers: {', '.join(tickers)}")
    df = yf.download(tickers, start=start, end=end, auto_adjust=True,
                     progress=False)["Close"]
    if isinstance(df, pd.Series):
        df = df.to_frame(tickers[0])
    return df.sort_index()


def benchmark_series(start, end):
    for tk in ("^SP500TR", "^GSPC"):
        s = yf.download(tk, start=start, end=end, auto_adjust=True,
                        progress=False)["Close"]
        if isinstance(s, pd.DataFrame):
            s = s.iloc[:, 0]
        if s.dropna().shape[0] > 100:
            print(f"Benchmark: {tk}")
            return s.dropna(), tk
    raise RuntimeError("Could not fetch a benchmark series")


# ------------------------------------------------------------------- strategy
def build_topn(prices, ranking, n):
    """Equal-weighted top-N portfolio, rebalanced daily to equal weight,
    rotating names at each ranking change. Daily portfolio return = mean of the
    held names' daily returns (equal allocation)."""
    segs = sorted((pd.Timestamp(d), names) for d, names in ranking)
    daily_ret = prices.pct_change()
    strat_ret = pd.Series(0.0, index=prices.index)
    holdings = pd.Series(index=prices.index, dtype=object)

    for i, (start_d, names) in enumerate(segs):
        end_d = segs[i + 1][0] if i + 1 < len(segs) else prices.index[-1] + pd.Timedelta(days=1)
        held = [t for t in names[:n] if t in daily_ret.columns]
        mask = (prices.index >= start_d) & (prices.index < end_d)
        if not held:
            continue
        strat_ret.loc[mask] = daily_ret.loc[mask, held].mean(axis=1).fillna(0.0)
        holdings.loc[mask] = ",".join(held)

    equity = (1.0 + strat_ret).cumprod()
    return equity, holdings


def stats(equity, label):
    total = equity.iloc[-1] / equity.iloc[0] - 1
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    cagr = (equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1
    mdd = (equity / equity.cummax() - 1).min()
    print(f"{label:22s}  total: {total:>10.1%}   CAGR: {cagr:>6.2%}   maxDD: {mdd:>7.1%}")


# ----------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tops", type=int, nargs="+", default=[1, 5],
                    help="Which top-N baskets to backtest (default: 1 5)")
    args = ap.parse_args()
    tops = sorted(set(args.tops))
    max_n = max(tops)

    membership = load_membership()
    print(f"Loaded real S&P 500 composition: {len(membership)} snapshots, "
          f"{membership.index.min().date()} -> {membership.index.max().date()}")
    validate_ranking(TOP_RANKING, membership, max_n)

    tickers = sorted({t for _, names in TOP_RANKING for t in names[:max_n]})
    prices = load_prices(tickers, START, END)
    bench, bench_name = benchmark_series(START, END)

    curves = {n: build_topn(prices, TOP_RANKING, n)[0] for n in tops}

    # Normalize everyone to 1.0 at the common start date
    start = max([c.first_valid_index() for c in curves.values()] + [bench.first_valid_index()])
    bench = (bench.loc[start:] / bench.loc[start:].iloc[0])
    for n in tops:
        c = curves[n].loc[start:]
        curves[n] = c / c.iloc[0]

    print("\n--- Performance (normalized, start = 1.0) ---")
    stats(bench, f"Buy & Hold ({bench_name})")
    for n in tops:
        stats(curves[n], f"Equal-weight Top-{n}")

    # Export daily time series: one CSV per strategy (equity + daily return)
    import os
    outdir = "results"
    os.makedirs(outdir, exist_ok=True)

    def export(series, name):
        df = pd.DataFrame({"equity": series})
        df["daily_return"] = series.pct_change()
        path = os.path.join(outdir, f"{name}.csv")
        df.to_csv(path, index_label="date")
        print(f"  wrote {path}  ({len(df)} rows)")

    print(f"\n--- Exporting daily series to ./{outdir}/ ---")
    export(bench, "sp500_buyhold")
    for n in tops:
        export(curves[n], f"top{n}_equalweight")

    # Plot
    fig, ax = plt.subplots(figsize=(13, 7))
    ax.plot(bench.index, bench.values, label=f"S&P 500 Buy & Hold ({bench_name})",
            lw=1.8, color="black", alpha=0.8)
    for n in tops:
        ax.plot(curves[n].index, curves[n].values,
                label=(f"Top-{n} equal-weight" if n > 1 else "Top-1 (#1 only)"), lw=1.8)
    ax.set_yscale("log")
    ax.set_title("Equal-weighted Top-N largest S&P 500 companies vs. Buy & Hold (log)")
    ax.set_ylabel("Growth of $1 (log)")
    ax.set_xlabel("Date")
    ax.grid(True, which="both", ls=":", alpha=0.4)
    ax.legend(loc="upper left")
    fig.tight_layout()
    out = "sp500_topN_backtest.png"
    fig.savefig(out, dpi=130)
    print(f"\nSaved plot -> {out}")
    try:
        plt.show()
    except Exception:
        pass


if __name__ == "__main__":
    sys.exit(main())
