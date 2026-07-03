"""Export the underlying daily equity series (already computed & normalized in
results/) into a compact JS data file consumed by index.html.

Underlyings (the 'price' each strategy trades):
  sp500 -> results/sp500_buyhold.csv
  top1  -> results/top1_equalweight.csv
  qld   -> results/qld_buyhold.csv
  tqqq  -> results/tqqq_buyhold.csv

The web page recomputes trend/mean-reversion signals in JS from these prices,
so parameters stay fully editable client-side.
"""
import json
import pandas as pd

SRC = {
    "sp500": "results/sp500_buyhold.csv",
    "top1":  "results/top1_equalweight.csv",
    "qld":   "results/qld_buyhold.csv",
    "tqqq":  "results/tqqq_buyhold.csv",
}

data = {}
for key, path in SRC.items():
    df = pd.read_csv(path, parse_dates=["date"])
    eq = df["equity"].astype(float)
    data[key] = {
        "dates": df["date"].dt.strftime("%Y-%m-%d").tolist(),
        "prices": [round(float(x), 5) for x in eq],
    }
    print(f"{key:6s} {len(eq):5d} pts  {df['date'].min().date()} -> {df['date'].max().date()}")

with open("data.js", "w") as f:
    f.write("window.DATA = ")
    json.dump(data, f, separators=(",", ":"))
    f.write(";\n")

import os
print(f"\nWrote data.js ({os.path.getsize('data.js')/1e6:.2f} MB)")
