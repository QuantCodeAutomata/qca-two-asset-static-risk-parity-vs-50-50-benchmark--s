# Risk Parity vs Benchmark — Quantitative Replication

Replication of four Risk Parity portfolio experiments from a quantitative finance thesis, comparing static and annually rebalanced Risk Parity portfolios against traditional benchmarks over the 2019–2022 out-of-sample period.

## Experiments

| # | Title | Assets | Benchmark |
|---|-------|--------|-----------|
| 1 | Static Two-Asset RP | SPY, AGG | 50/50 |
| 2 | Annually Rebalanced Two-Asset RP | SPY, AGG | 50/50 |
| 3 | Static Five-Asset ERC RP | ACWI, TLT, DBC, RWR, TIP | Equal-Weight (20% each) |
| 4 | Annually Rebalanced Five-Asset ERC RP | ACWI, TLT, DBC, RWR, TIP | Equal-Weight (20% each) |

**Estimation window:** 2009/01–2018/12 (10 years of monthly data)  
**Testing window:** 2019/01–2022/12 (4 years out-of-sample)

## Repository Structure

```
project/
├── data/
│   └── raw_prices.csv          # Monthly adjusted close prices
├── exp/
│   ├── exp_1_static_two_asset.py
│   ├── exp_2_rebalanced_two_asset.py
│   ├── exp_3_static_five_asset.py
│   └── exp_4_rebalanced_five_asset.py
├── results/
│   ├── RESULTS.md              # Summary of all experiment findings
│   ├── exp1_results.csv        # Exp 1 metrics vs thesis targets
│   ├── exp2_results.csv
│   ├── exp3_results.csv
│   ├── exp4_results.csv
│   ├── exp1_cumulative_returns.png
│   ├── exp2_cumulative_returns.png
│   ├── exp2_annual_weights.png
│   ├── exp3_cumulative_returns.png
│   ├── exp4_cumulative_returns.png
│   └── exp4_annual_weights.png
├── src/
│   ├── __init__.py
│   ├── data_loader.py          # Price download (massive → yfinance fallback)
│   ├── preprocessing.py        # Month-end alignment, returns, rf conversion
│   ├── stats_validation.py     # Descriptive stats, covariance, correlation
│   ├── portfolio_two_asset.py  # Analytical inverse-vol RP weights
│   ├── portfolio_five_asset.py # ERC optimization (SLSQP)
│   └── metrics.py              # Sharpe, Sortino, Treynor, beta, downside risk
├── tests/
│   ├── test_metrics.py
│   ├── test_portfolio_two_asset.py
│   ├── test_portfolio_five_asset.py
│   └── test_stats_validation.py
├── run_all.py                  # Run all four experiments sequentially
├── requirements.txt
├── AGENTS.md
└── .gitignore
```

## Methodology

### Two-Asset Risk Parity (Experiments 1 & 2)

The two-asset RP weight is computed analytically using the inverse-volatility formula:

```
w_equity = σ_bond / (σ_equity + σ_bond)
w_bond   = σ_equity / (σ_equity + σ_bond)
```

Volatilities are estimated from the 10-year rolling window ending December of the prior year. Weights are held constant within each year (static for Exp 1, annually rebalanced for Exp 2).

### Five-Asset Equal Risk Contribution (Experiments 3 & 4)

The ERC portfolio minimizes the sum of squared deviations of risk contributions from their mean:

```
RC_i = w_i · (Σw)_i
Objective: minimize 0.5 · Σ_i (RC_i − mean(RC))²
Subject to: Σ w_i = 1,  w_i ≥ 0
```

Solved numerically with `scipy.optimize.minimize` (SLSQP), initialized with inverse-volatility weights.

### Performance Metrics

| Metric | Formula |
|--------|---------|
| Sharpe | `mean(R_p) / std(R_p)` (two-asset, no rf); `mean(R_p − rf) / std(R_p)` (five-asset) |
| Sortino | `mean(R_p) / downside_risk` (two-asset); `mean(R_p − rf) / downside_risk` (five-asset) |
| Treynor | `mean(R_p) / β` (two-asset); `mean(R_p − rf) / β` (five-asset) |
| Downside Risk | `sqrt(mean(min(R_p,t, 0)²))` — target = 0% monthly |
| Beta | `Cov(R_p, R_market) / Var(R_market)` |

## Quick Start

### Install dependencies

```bash
pip install -r requirements.txt
```

### Download data and run all experiments

```bash
python run_all.py
```

Results are saved to `results/`.

### Run individual experiments

```bash
python exp/exp_1_static_two_asset.py
python exp/exp_2_rebalanced_two_asset.py
python exp/exp_3_static_five_asset.py
python exp/exp_4_rebalanced_five_asset.py
```

### Run tests

```bash
python -m pytest tests/ -v
```

## Data Sources

- **Primary:** [Massive/Polygon.io](https://polygon.io/) REST API (requires `MASSIVE_TOKEN` env var)
- **Fallback:** [yfinance](https://github.com/ranaroussi/yfinance) (auto-used if `MASSIVE_TOKEN` is absent)
- **Risk-free rate:** FRED TB3MS (3-month T-bill), via `pandas_datareader`

Tickers used:
- Two-asset: `SPY` (S&P 500 ETF proxy), `AGG` (US Aggregate Bond ETF)
- Five-asset: `ACWI`, `TLT`, `DBC`, `RWR`, `TIP`

## Key Findings

All four experiments confirm the thesis's central conclusion: **Risk Parity portfolios consistently deliver lower volatility, lower beta, and lower downside risk than their benchmarks, but also lower mean returns and weaker risk-adjusted ratios (Sharpe, Sortino, Treynor) over the 2019–2022 out-of-sample period.**

See [`results/RESULTS.md`](results/RESULTS.md) for detailed metrics and comparison tables.

## Library Attribution

- `scipy.optimize.minimize` (SLSQP) — ERC optimization
- `pandas_datareader` — FRED TB3MS risk-free rate
- `yfinance` — price data fallback
- Custom implementations for all portfolio construction and metrics (thesis-faithful conventions)
