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
- `tqqq_bottom_model.ipynb` — a **causal, out-of-sample calibrated** logistic
  model that outputs a *probability of being at a crash bottom* (features from
  SMA, VIX, rolling std and their expanding historical percentiles), used to
  **accumulate TQQQ in conviction-scaled tranches**.
- `strategies.ipynb` — earlier exploration (trend following + SMA/VIX signal).
- `data_cache/` — cached price series so notebooks run offline / in Jupyter.
