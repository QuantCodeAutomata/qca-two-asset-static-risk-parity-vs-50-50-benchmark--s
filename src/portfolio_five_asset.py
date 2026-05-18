import numpy as np
import pandas as pd
from scipy.optimize import minimize
from typing import Tuple


def compute_risk_contributions(weights: np.ndarray, cov_matrix: np.ndarray) -> np.ndarray:
    """
    Compute risk contributions: RC_i = w_i * (Sigma @ w)_i
    # Custom — Context7 confirmed skfolio RiskBudgeting uses same formula internally
    """
    marginal_contrib = cov_matrix @ weights
    rc = weights * marginal_contrib
    return rc


def erc_objective(weights: np.ndarray, cov_matrix: np.ndarray) -> float:
    """
    ERC objective: minimize sum of squared deviations of risk contributions from their mean.
    Implements thesis formula: minimize 0.5 * sum_i (RC_i - mean_RC)^2
    # Custom — Context7 found no library equivalent for exact thesis ERC objective form
    """
    rc = compute_risk_contributions(weights, cov_matrix)
    mean_rc = rc.mean()
    return 0.5 * np.sum((rc - mean_rc) ** 2)


def compute_inverse_vol_weights(cov_matrix: np.ndarray) -> np.ndarray:
    """Compute normalized inverse-volatility weights as initialization."""
    sigmas = np.sqrt(np.diag(cov_matrix))
    inv_vol = 1.0 / sigmas
    return inv_vol / inv_vol.sum()


def solve_erc_portfolio(cov_matrix: np.ndarray, n_assets: int = 5,
                        ftol: float = 1e-12, maxiter: int = 1000) -> dict:
    """
    Solve Equal Risk Contribution portfolio using scipy SLSQP.
    Long-only, fully invested constraints.
    Returns dict with weights, convergence info, risk contributions.
    # Custom — Context7 confirmed scipy SLSQP is appropriate for this ERC formulation
    """
    x0 = compute_inverse_vol_weights(cov_matrix)
    constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}]
    bounds = [(0.0, 1.0)] * n_assets
    result = minimize(
        erc_objective,
        x0,
        args=(cov_matrix,),
        method='SLSQP',
        bounds=bounds,
        constraints=constraints,
        options={'ftol': ftol, 'maxiter': maxiter, 'disp': False}
    )
    weights = result.x
    rc = compute_risk_contributions(weights, cov_matrix)
    return {
        'weights': weights,
        'converged': result.success,
        'message': result.message,
        'objective': result.fun,
        'iterations': result.nit,
        'risk_contributions': rc,
        'rc_normalized': rc / rc.sum()
    }


def build_static_erc_portfolio(estimation_returns: pd.DataFrame) -> dict:
    """
    Build static five-asset ERC portfolio from estimation window returns.
    Returns dict with weights, asset names, and optimization diagnostics.
    """
    cov_matrix = estimation_returns.cov().values
    n = len(estimation_returns.columns)
    result = solve_erc_portfolio(cov_matrix, n_assets=n)
    result['asset_names'] = list(estimation_returns.columns)
    result['weights_dict'] = dict(zip(estimation_returns.columns, result['weights']))
    return result


def build_annual_erc_portfolios(returns: pd.DataFrame, test_years: list[int]) -> dict:
    """
    Build annually rebalanced five-asset ERC portfolios.
    For each test year y, uses 10-year estimation window ending Dec of y-1.
    Returns dict mapping year to optimization result dict.
    """
    annual_results = {}
    for y in test_years:
        est_start = f'{y-10}-01-01'
        est_end = f'{y-1}-12-31'
        est_returns = returns.loc[est_start:est_end]
        result = build_static_erc_portfolio(est_returns)
        annual_results[y] = result
    return annual_results


def compute_equal_weight_portfolio(n_assets: int) -> np.ndarray:
    """Return equal-weight portfolio weights."""
    return np.ones(n_assets) / n_assets


def compute_portfolio_returns_array(returns: pd.DataFrame, weights: np.ndarray) -> pd.Series:
    """Compute portfolio returns as weighted sum."""
    port_returns = returns.values @ weights
    return pd.Series(port_returns, index=returns.index, name='portfolio')


def apply_annual_erc_weights(returns: pd.DataFrame, annual_results: dict) -> pd.Series:
    """
    Apply annually rebalanced ERC weights to monthly returns.
    Returns concatenated monthly portfolio return series.
    """
    yearly_series = []
    for y, result in sorted(annual_results.items()):
        year_returns = returns.loc[str(y)]
        w = result['weights']
        port_ret = compute_portfolio_returns_array(year_returns, w)
        yearly_series.append(port_ret)
    return pd.concat(yearly_series)
