"""Export the underlying daily equity series (already computed & normalized in
results/) into a compact JS data file consumed by index.html.

Underlyings (the 'price' each strategy trades):
  sp500 -> results/sp500_buyhold.csv
  top1  -> results/top1_equalweight.csv
  qld   -> results/qld_buyhold.csv
  tqqq  -> results/tqqq_buyhold.csv

For QLD & TQQQ we ALSO export a separate 'signal' price series: the underlying
Nasdaq-100 index (results/{etf}_index.csv), aligned to the ETF calendar. The web
page computes trend / mean-reversion signals on THIS index series (not the
leveraged ETF price), then applies the resulting position to the ETF returns.
For sp500 / top1 the underlying IS the traded series, so signal == price.

The web page recomputes signals in JS from these prices, so parameters stay
fully editable client-side.
"""
import json
import pandas as pd

SRC = {
    "sp500": "results/sp500_buyhold.csv",
    "top1":  "results/top1_equalweight.csv",
    "qld":   "results/qld_buyhold.csv",
    "tqqq":  "results/tqqq_buyhold.csv",
}
# Separate signal series (underlying index) for the leveraged ETFs.
SIGNAL_SRC = {
    "qld":  "results/qld_index.csv",
    "tqqq": "results/tqqq_index.csv",
}

data = {}
for key, path in SRC.items():
    df = pd.read_csv(path, parse_dates=["date"])
    eq = df["equity"].astype(float)
    entry = {
        "dates": df["date"].dt.strftime("%Y-%m-%d").tolist(),
        "prices": [round(float(x), 5) for x in eq],
    }
    if key in SIGNAL_SRC:
        sig = pd.read_csv(SIGNAL_SRC[key], parse_dates=["date"]).set_index("date")["index"]
        sig = sig.reindex(df["date"].values)  # align to price calendar
        entry["signal"] = [round(float(x), 5) for x in sig.astype(float)]
        print(f"{key:6s} {len(eq):5d} pts  + index signal series")
    else:
        print(f"{key:6s} {len(eq):5d} pts  {df['date'].min().date()} -> {df['date'].max().date()}")
    data[key] = entry

with open("data.js", "w") as f:
    f.write("window.DATA = ")
    json.dump(data, f, separators=(",", ":"))
    f.write(";\n")

import os
print(f"\nWrote data.js ({os.path.getsize('data.js')/1e6:.2f} MB)")
