import pytest
import numpy as np
import pandas as pd
import sys
sys.path.insert(0, '/workspace/project')
from src.metrics import (
    compute_downside_risk,
    compute_beta,
    compute_covariance_with_market,
    compute_sharpe,
    compute_sortino,
    compute_treynor,
    compute_portfolio_metrics
)

def make_returns(n=48, seed=42):
    np.random.seed(seed)
    dates = pd.date_range('2019-01-31', periods=n, freq='ME')
    port = pd.Series(np.random.randn(n)*0.03 + 0.003, index=dates)
    market = pd.Series(np.random.randn(n)*0.04 + 0.005, index=dates)
    return port, market

def test_downside_risk_non_negative():
    """Downside risk must be non-negative."""
    port, _ = make_returns()
    dr = compute_downside_risk(port)
    assert dr >= 0

def test_downside_risk_zero_for_positive_returns():
    """Downside risk should be 0 when all returns are positive."""
    returns = pd.Series([0.01, 0.02, 0.03, 0.005])
    dr = compute_downside_risk(returns, target=0.0)
    assert dr == 0.0

def test_downside_risk_formula():
    """Verify downside risk formula: sqrt(mean(min(r,0)^2))."""
    returns = pd.Series([-0.02, 0.01, -0.03, 0.02])
    expected = np.sqrt(np.mean([0.02**2, 0, 0.03**2, 0]))
    dr = compute_downside_risk(returns, target=0.0)
    assert abs(dr - expected) < 1e-12

def test_beta_market_vs_itself():
    """Beta of market vs itself should be 1."""
    _, market = make_returns()
    beta = compute_beta(market, market)
    assert abs(beta - 1.0) < 1e-10

def test_beta_range():
    """Beta should be a finite number."""
    port, market = make_returns()
    beta = compute_beta(port, market)
    assert np.isfinite(beta)

def test_sharpe_no_rf():
    """Sharpe without rf = mean/std."""
    port, _ = make_returns()
    sharpe = compute_sharpe(port)
    expected = port.mean() / port.std()
    assert abs(sharpe - expected) < 1e-10

def test_sortino_no_rf():
    """Sortino without rf = mean/downside_risk."""
    port, _ = make_returns()
    sortino = compute_sortino(port)
    dr = compute_downside_risk(port)
    expected = port.mean() / dr
    assert abs(sortino - expected) < 1e-10

def test_treynor_no_rf():
    """Treynor without rf = mean/beta."""
    port, market = make_returns()
    treynor = compute_treynor(port, market)
    beta = compute_beta(port, market)
    expected = port.mean() / beta
    assert abs(treynor - expected) < 1e-10

def test_portfolio_metrics_keys():
    """compute_portfolio_metrics should return all required keys."""
    port, market = make_returns()
    metrics = compute_portfolio_metrics(port, market)
    required_keys = ['mean', 'std', 'covariance', 'beta', 'downside_risk', 'sharpe', 'sortino', 'treynor']
    for key in required_keys:
        assert key in metrics, f'Missing key: {key}'

def test_portfolio_metrics_std_positive():
    """Standard deviation must be positive."""
    port, market = make_returns()
    metrics = compute_portfolio_metrics(port, market)
    assert metrics['std'] > 0

def test_portfolio_metrics_with_rf():
    """Metrics with rf should use excess returns in numerator."""
    port, market = make_returns()
    rf = pd.Series(0.001, index=port.index)
    metrics_no_rf = compute_portfolio_metrics(port, market)
    metrics_with_rf = compute_portfolio_metrics(port, market, rf)
    # Sharpe with rf should be lower than without (rf reduces numerator)
    assert metrics_with_rf['sharpe'] < metrics_no_rf['sharpe']
