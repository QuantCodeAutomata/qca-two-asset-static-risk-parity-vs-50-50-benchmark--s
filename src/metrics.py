import numpy as np
import pandas as pd
from typing import Optional


def compute_downside_risk(returns: pd.Series, target: float = 0.0) -> float:
    """
    Compute downside deviation relative to target (default 0%).
    Formula: sqrt(mean(min(R_t - target, 0)^2))
    # Custom — Context7 found no library equivalent matching exact thesis convention
    """
    downside = np.minimum(returns.values - target, 0.0)
    return np.sqrt(np.mean(downside ** 2))


def compute_beta(portfolio_returns: pd.Series, market_returns: pd.Series) -> float:
    """
    Compute portfolio beta: Cov(R_p, R_m) / Var(R_m)
    """
    cov_matrix = np.cov(portfolio_returns.values, market_returns.values)
    return cov_matrix[0, 1] / cov_matrix[1, 1]


def compute_covariance_with_market(portfolio_returns: pd.Series, market_returns: pd.Series) -> float:
    """Compute covariance of portfolio with market."""
    return np.cov(portfolio_returns.values, market_returns.values)[0, 1]


def compute_sharpe(returns: pd.Series, rf: Optional[pd.Series] = None) -> float:
    """
    Compute Sharpe ratio.
    If rf is None: Sharpe = mean(R_p) / std(R_p) (thesis two-asset convention)
    If rf provided: Sharpe = mean(R_p - rf) / std(R_p) (thesis five-asset convention)
    """
    if rf is None:
        return returns.mean() / returns.std()
    excess = returns.values - rf.values
    return excess.mean() / returns.std()


def compute_sortino(returns: pd.Series, rf: Optional[pd.Series] = None, target: float = 0.0) -> float:
    """
    Compute Sortino ratio.
    If rf is None: Sortino = mean(R_p) / downside_risk (thesis two-asset convention)
    If rf provided: Sortino = mean(R_p - rf) / downside_risk (thesis five-asset convention)
    """
    dr = compute_downside_risk(returns, target)
    if rf is None:
        return returns.mean() / dr
    excess = returns.values - rf.values
    return excess.mean() / dr


def compute_treynor(returns: pd.Series, market_returns: pd.Series, rf: Optional[pd.Series] = None) -> float:
    """
    Compute Treynor ratio.
    If rf is None: Treynor = mean(R_p) / beta (thesis two-asset convention)
    If rf provided: Treynor = mean(R_p - rf) / beta (thesis five-asset convention)
    """
    beta = compute_beta(returns, market_returns)
    if rf is None:
        return returns.mean() / beta
    excess = returns.values - rf.values
    return excess.mean() / beta


def compute_portfolio_metrics(portfolio_returns: pd.Series, market_returns: pd.Series,
                               rf: Optional[pd.Series] = None) -> dict:
    """
    Compute all portfolio performance metrics.
    Returns dict with mean, std, covariance, beta, downside_risk, sharpe, sortino, treynor.
    """
    aligned = pd.concat([portfolio_returns, market_returns], axis=1).dropna()
    p = aligned.iloc[:, 0]
    m = aligned.iloc[:, 1]
    rf_aligned = rf.reindex(p.index) if rf is not None else None
    return {
        'mean': p.mean(),
        'std': p.std(),
        'covariance': compute_covariance_with_market(p, m),
        'beta': compute_beta(p, m),
        'downside_risk': compute_downside_risk(p),
        'sharpe': compute_sharpe(p, rf_aligned),
        'sortino': compute_sortino(p, rf_aligned),
        'treynor': compute_treynor(p, m, rf_aligned)
    }
