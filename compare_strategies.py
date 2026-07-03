"""
Relative PnL comparison across strategies.

Takes any number of strategy CSVs (each with columns `date, equity`) as
parameters and plots their relative evolution against a baseline strategy --
by default the simple "buy only the #1 company" strategy (top1_equalweight).

Two panels:
  (top)    Growth of 100, all strategies normalized to 100 at the common start.
  (bottom) RELATIVE performance vs baseline = equity_strat / equity_baseline.
           Above 1.0 = outperforming the simple buy-the-biggest-company strat,
           below 1.0 = underperforming. This is the "relative PnL" view.

Usage
-----
    python compare_strategies.py results/top1_buyhold.csv \
        results/top1_trend_sma200.csv results/top1_meanrev_rsi2.csv

    # custom baseline:
    python compare_strategies.py A.csv B.csv --baseline results/top1_equalweight.csv
"""

import argparse
import os
import pandas as pd
import matplotlib.pyplot as plt

DEFAULT_BASELINE = "results/top1_equalweight.csv"   # buy only the biggest company


def load_equity(path):
    df = pd.read_csv(path, parse_dates=["date"]).set_index("date")
    return df["equity"]


def label_of(path):
    return os.path.splitext(os.path.basename(path))[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+", help="Strategy CSVs (date, equity)")
    ap.add_argument("--baseline", default=DEFAULT_BASELINE,
                    help="Baseline CSV to measure relative performance against")
    ap.add_argument("--out", default="strategy_relative_comparison.png")
    args = ap.parse_args()

    # Load everything, including baseline (avoid duplicate if user passed it too)
    series = {label_of(f): load_equity(f) for f in args.files}
    base_label = label_of(args.baseline) + " (baseline)"
    series[base_label] = load_equity(args.baseline)

    # Align on common dates
    aligned = pd.DataFrame(series).dropna()
    if aligned.empty:
        raise SystemExit("No overlapping dates across the provided files.")

    normalized = aligned / aligned.iloc[0] * 100.0
    baseline = aligned[base_label]
    relative = aligned.div(baseline, axis=0)

    # Stats
    print(f"Common window: {aligned.index.min().date()} -> {aligned.index.max().date()} "
          f"({len(aligned)} days)\n")
    print(f"{'strategy':32s} {'total':>10s} {'vs baseline':>12s}")
    base_total = baseline.iloc[-1] / baseline.iloc[0] - 1
    for col in aligned.columns:
        tot = aligned[col].iloc[-1] / aligned[col].iloc[0] - 1
        rel = relative[col].iloc[-1] - 1.0
        print(f"{col:32s} {tot:>9.1%} {rel:>+11.1%}")
    print(f"\nBaseline total return: {base_total:.1%}")

    # Plot
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 9), sharex=True,
                                   gridspec_kw={"height_ratios": [2, 1]})
    for col in normalized.columns:
        style = dict(lw=1.6)
        if col == base_label:
            style.update(color="black", alpha=0.8, ls="--")
        ax1.plot(normalized.index, normalized[col], label=col, **style)
    ax1.set_yscale("log")
    ax1.set_ylabel("Growth of 100 (log)")
    ax1.set_title("Strategy comparison — absolute (top) and relative to baseline (bottom)")
    ax1.grid(True, which="both", ls=":", alpha=0.4)
    ax1.legend(loc="upper left", fontsize=9)

    for col in relative.columns:
        if col == base_label:
            continue
        ax2.plot(relative.index, relative[col], label=col, lw=1.4)
    ax2.axhline(1.0, color="black", ls="--", alpha=0.7, label=base_label)
    ax2.set_ylabel(f"Relative to\n{base_label}")
    ax2.set_xlabel("Date")
    ax2.grid(True, which="both", ls=":", alpha=0.4)
    ax2.legend(loc="upper left", fontsize=8)

    fig.tight_layout()
    fig.savefig(args.out, dpi=130)
    print(f"\nSaved plot -> {args.out}")


if __name__ == "__main__":
    main()
