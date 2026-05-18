# Risk Parity vs Benchmark – Repository Notes

## Project Layout

```
project/
├── data/               # raw_prices.csv written here by data_loader
├── exp/                # experiment scripts / notebooks
├── results/            # output artefacts
├── src/                # core library modules
│   ├── __init__.py
│   ├── data_loader.py
│   ├── metrics.py
│   ├── portfolio_five_asset.py
│   ├── portfolio_two_asset.py
│   ├── preprocessing.py
│   └── stats_validation.py
└── tests/
    ├── test_metrics.py
    ├── test_portfolio_five_asset.py
    ├── test_portfolio_two_asset.py
    └── test_stats_validation.py
```

## Key Modules

### `src/data_loader.py`
- **`download_prices(tickers, start, end, save_path=None) -> pd.DataFrame`**
  - Downloads monthly adjusted close prices for the 7 experiment assets:
    `['^GSPC', 'AGG', 'ACWI', 'TLT', 'DBC', 'RWR', 'TIP']`
  - Date range: `2008-12-01` → `2022-12-31`
  - Source priority: **massive RESTClient** → **yfinance** → **pandas_datareader**
  - `'^GSPC'` maps to `'I:SPX'` for the massive/Polygon API; falls back to `'SPY'`
    as ETF proxy if the index is unavailable from all sources.
  - Requires `MASSIVE_TOKEN` env var for the massive path (silently skipped if absent).
  - Saves CSV to `data/raw_prices.csv` (or `save_path`).
  - Returns DataFrame with month-end `DatetimeIndex` and ticker columns.

### `src/preprocessing.py`
- **`align_month_end(prices)`** – snaps index to month-end, ffill limit=1, dropna.
- **`compute_returns(prices)`** – simple returns `P_t/P_{t-1} - 1`, drops first row.
- **`get_estimation_window(returns, start, end)`** – `.loc[start:end]` slice.
- **`get_testing_window(returns, start, end)`** – `.loc[start:end]` slice.
- **`convert_rf_to_monthly(rf_annual)`** – `annual_yield / 12` (simple approximation).

### `src/stats_validation.py`
- **`compute_descriptive_stats(returns)`** – returns (5 × n_assets) DataFrame with
  rows: `mean`, `std`, `skewness`, `kurtosis`, `serial_corr`.
  Uses `scipy.stats.skew/kurtosis` with `bias=False` (bias-corrected).
- **`compute_covariance_matrix(returns)`** – sample covariance (ddof=1).
- **`compute_correlation_matrix(returns)`** – Pearson correlation.
- **`validate_estimation_stats(computed, thesis_targets)`** – accepts either a flat
  `{key: scalar}` dict or a nested `{stat: {asset: value}}` dict; returns a dict
  (flat keys get `{'target': value}`, nested keys get full diff/tolerance info).

### `src/portfolio_two_asset.py`
- **`compute_rp_weights_two_asset(sigma_equity, sigma_bond)`** – inverse-vol RP:
  `w_e = sigma_b / (sigma_e + sigma_b)`, `w_b = sigma_e / (sigma_e + sigma_b)`.
- **`compute_benchmark_weights_two_asset()`** – returns `(0.5, 0.5)`.
- **`compute_portfolio_returns(returns, weights)`** – weighted sum; `weights` is a
  `{col: weight}` dict; iterates over `returns.columns` order.
- **`build_static_rp_portfolio(returns, equity_col, bond_col)`** – uses full history
  std to compute RP weights; returns dict with `w_equity`, `w_bond`, `weights`, etc.
- **`build_annual_rp_portfolios(returns, equity_col, bond_col, test_years)`** – for
  year Y uses a **10-year** expanding window: `{Y-10}-01-01` → `{Y-1}-12-31`.
- **`apply_annual_weights(returns, annual_weights)`** – applies year-keyed weights
  to produce a monthly portfolio return Series.

### `src/portfolio_five_asset.py`
- **`compute_risk_contributions(w, cov)`** – `RC_i = w_i * (Cov @ w)_i`; sum equals
  portfolio variance.
- **`erc_objective(w, cov)`** – `0.5 * sum((RC_i - mean_RC)^2)`; zero when all RC equal.
- **`compute_inverse_vol_weights(cov)`** – normalized `1/sigma_i` weights.
- **`solve_erc_portfolio(cov, n_assets=5)`** – SLSQP with sum=1 and long-only bounds;
  returns dict with `weights`, `risk_contributions`, `rc_normalized`, convergence info.
- **`build_static_erc_portfolio(returns)`** – wraps `solve_erc_portfolio` on `returns.cov()`.
- **`compute_equal_weight_portfolio(n)`** – `np.ones(n)/n`.
- **`compute_portfolio_returns_array(returns, w)`** – `returns.values @ w` as Series.

### `src/metrics.py`
- **`compute_downside_risk(returns, target=0.0)`** – `sqrt(mean(min(r-target, 0)^2))`.
- **`compute_beta(port, market)`** – `np.cov(port, market)[0,1] / np.cov(port, market)[1,1]`.
- **`compute_covariance_with_market(port, market)`** – `np.cov(port, market)[0,1]`.
- **`compute_sharpe(returns, rf=None)`** – no rf: `mean/std`; with rf: `(mean-rf_mean)/std`.
- **`compute_sortino(returns, rf=None)`** – no rf: `mean/downside_risk`; with rf uses excess mean.
- **`compute_treynor(returns, market, rf=None)`** – no rf: `mean/beta`; with rf uses excess mean.
- **`compute_portfolio_metrics(port, market, rf=None)`** – returns dict with keys:
  `mean`, `std`, `covariance`, `beta`, `downside_risk`, `sharpe`, `sortino`, `treynor`.

## Test Suite
Run with: `python -m pytest tests/ -v` (39 tests, ~1 s).
All tests use `sys.path.insert(0, '/workspace/project')` for imports.

## Dependencies (installed)
- `massive==0.10.0` (Polygon.io REST client)
- `pandas_datareader==0.10.0`
- `yfinance==1.3.0`
- `scipy==1.14.1`
- `statsmodels==0.14.2`
- `pandas`, `numpy`

## Conventions
- All DatetimeIndex values are snapped to **month-end** (`pd.offsets.MonthEnd(0)`).
- Rates (risk-free) are expressed as **decimals** (0.05 = 5 %).
- `compute_returns` consumes the first price row; estimation/testing windows are
  sliced from the returns DataFrame, not the prices DataFrame.
