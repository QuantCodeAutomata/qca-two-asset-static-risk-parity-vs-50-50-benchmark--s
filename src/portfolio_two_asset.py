import numpy as np
import pandas as pd
from typing import Tuple


def compute_rp_weights_two_asset(sigma_equity: float, sigma_bond: float) -> Tuple[float, float]:
    """
    Compute two-asset Risk Parity weights using analytical inverse-volatility formula.
    w_equity = sigma_bond / (sigma_equity + sigma_bond)
    w_bond = sigma_equity / (sigma_equity + sigma_bond)
    # Custom — Context7 found no library equivalent for this exact two-asset analytical formula
    Returns (w_equity, w_bond)
    """
    w_equity = sigma_bond / (sigma_equity + sigma_bond)
    w_bond = sigma_equity / (sigma_equity + sigma_bond)
    assert abs(w_equity + w_bond - 1.0) < 1e-10, 'Weights must sum to 1'
    return w_equity, w_bond


def compute_benchmark_weights_two_asset() -> Tuple[float, float]:
    """Return fixed 50/50 benchmark weights."""
    return 0.5, 0.5


def compute_portfolio_returns(returns: pd.DataFrame, weights: dict) -> pd.Series:
    """
    Compute portfolio returns as weighted sum of asset returns.
    weights: dict mapping column names to weights
    """
    w = np.array([weights[col] for col in returns.columns])
    port_returns = returns.values @ w
    return pd.Series(port_returns, index=returns.index, name='portfolio')


def build_static_rp_portfolio(estimation_returns: pd.DataFrame, equity_col: str, bond_col: str) -> dict:
    """
    Build static two-asset RP portfolio from estimation window returns.
    Returns dict with weights and estimation stats.
    """
    sigma_equity = estimation_returns[equity_col].std()
    sigma_bond = estimation_returns[bond_col].std()
    w_equity, w_bond = compute_rp_weights_two_asset(sigma_equity, sigma_bond)
    return {
        'sigma_equity': sigma_equity,
        'sigma_bond': sigma_bond,
        'w_equity': w_equity,
        'w_bond': w_bond,
        'weights': {equity_col: w_equity, bond_col: w_bond}
    }


def build_annual_rp_portfolios(returns: pd.DataFrame, equity_col: str, bond_col: str,
                                test_years: list[int]) -> dict:
    """
    Build annually rebalanced two-asset RP portfolios.
    For each test year y, uses 10-year estimation window ending Dec of y-1.
    Returns dict mapping year to weights dict.
    """
    annual_weights = {}
    for y in test_years:
        est_start = f'{y-10}-01-01'
        est_end = f'{y-1}-12-31'
        est_returns = returns.loc[est_start:est_end]
        sigma_equity = est_returns[equity_col].std()
        sigma_bond = est_returns[bond_col].std()
        w_equity, w_bond = compute_rp_weights_two_asset(sigma_equity, sigma_bond)
        annual_weights[y] = {
            'sigma_equity': sigma_equity,
            'sigma_bond': sigma_bond,
            'w_equity': w_equity,
            'w_bond': w_bond,
            'weights': {equity_col: w_equity, bond_col: w_bond}
        }
    return annual_weights


def apply_annual_weights(returns: pd.DataFrame, annual_weights: dict) -> pd.Series:
    """
    Apply annually rebalanced weights to monthly returns.
    Returns concatenated monthly portfolio return series.
    """
    yearly_series = []
    for y, info in sorted(annual_weights.items()):
        year_returns = returns.loc[str(y)]
        w = info['weights']
        port_ret = compute_portfolio_returns(year_returns, w)
        yearly_series.append(port_ret)
    return pd.concat(yearly_series)
