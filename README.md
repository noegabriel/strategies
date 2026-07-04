# S&P 500 / Nasdaq leveraged strategies — interactive backtest

Live page: **https://noegabriel.github.io/strategies/**

Interactive backtest of 8 equity strategies with editable parameters, initial
capital, monthly DCA, investment horizon and Interactive-Brokers-style fees.
Curves recompute live in the browser. Past performance is not indicative of
future results — this is educational, not investment advice.

- `index.html` — the app (no build step, no dependencies)
- `data.js` — underlying daily series exported from the Python backtests
- `*.py` — the backtests that generate the data
