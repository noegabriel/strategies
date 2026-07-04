# S&P 500 / Nasdaq leveraged strategies — interactive backtest

Live page: **https://noegabriel.github.io/strategies/**

Interactive backtest of 8 equity strategies with editable parameters, initial
capital, monthly DCA, investment horizon and Interactive-Brokers-style fees.
Curves recompute live in the browser. Past performance is not indicative of
future results — this is educational, not investment advice.

- `index.html` — the app (no build step, no dependencies)
- `data.js` — underlying daily series exported from the Python backtests
- `*.py` — the backtests that generate the data

## Research notebooks

Signals are always computed on the **underlying index** (`^NDX` for the leveraged
ETFs), never on the leveraged ETF price, and strictly **without look-ahead**.

- `qld_trend_research.ipynb` — search for the final QLD trend-following rule
  (SMA sweep, hysteresis band, dual-MA, slope filter, out-of-sample split, fee
  sensitivity). Retained rule: **SMA(200) + 1% hysteresis band** on `^NDX`.
- `tqqq_bottom_model.ipynb` — two **causal, out-of-sample calibrated** gradient-
  boosting models: *P(bottom)* and *P(top)* (features from SMA, VIX, rolling std
  and their expanding historical percentiles; 70/30 chronological split). They
  are fused into a single **continuous position-sizing signal** (0 = top → fully
  out, 0.9 = crash bottom → fully in, 0.1 steps, smoothed) driven by a state
  machine: **accumulate at the bottom, hold the whole recovery until the top,
  exit on trend break / strong top**. Out-of-sample on TQQQ: ~19% CAGR, ~-38%
  maxDD vs -82% buy & hold.
- `strategies.ipynb` — earlier exploration (trend following + SMA/VIX signal).
- `data_cache/` — cached price series so notebooks run offline / in Jupyter.
