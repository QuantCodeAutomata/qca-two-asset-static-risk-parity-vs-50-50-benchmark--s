import pytest
import numpy as np
import pandas as pd
import sys
sys.path.insert(0, '/workspace/project')
from src.portfolio_five_asset import (
    compute_risk_contributions,
    erc_objective,
    compute_inverse_vol_weights,
    solve_erc_portfolio,
    build_static_erc_portfolio,
    compute_equal_weight_portfolio,
    compute_portfolio_returns_array
)

def make_sample_cov(n=5, seed=42):
    np.random.seed(seed)
    A = np.random.randn(n, n)
    return A @ A.T / n + np.eye(n) * 0.001

def test_risk_contributions_sum_to_portfolio_variance():
    """Sum of risk contributions should equal portfolio variance."""
    cov = make_sample_cov()
    w = np.ones(5) / 5
    rc = compute_risk_contributions(w, cov)
    port_var = w @ cov @ w
    assert abs(rc.sum() - port_var) < 1e-10

def test_erc_objective_zero_at_equal_risk():
    """ERC objective should be near zero when all risk contributions are equal."""
    # Diagonal covariance with equal variances -> equal weights give equal RC
    cov = np.eye(5) * 0.01
    w = np.ones(5) / 5
    obj = erc_objective(w, cov)
    assert obj < 1e-20

def test_inverse_vol_weights_sum_to_one():
    """Inverse vol weights must sum to 1."""
    cov = make_sample_cov()
    w = compute_inverse_vol_weights(cov)
    assert abs(w.sum() - 1.0) < 1e-10

def test_inverse_vol_weights_higher_vol_lower_weight():
    """Higher variance asset should get lower weight."""
    cov = np.diag([0.01, 0.04, 0.09, 0.0025, 0.0016])
    w = compute_inverse_vol_weights(cov)
    # Asset 2 (var=0.09) should have lower weight than asset 4 (var=0.0016)
    assert w[2] < w[4]

def test_solve_erc_weights_sum_to_one():
    """ERC weights must sum to 1."""
    cov = make_sample_cov()
    result = solve_erc_portfolio(cov)
    assert abs(result['weights'].sum() - 1.0) < 1e-6

def test_solve_erc_weights_non_negative():
    """ERC weights must be non-negative (long-only)."""
    cov = make_sample_cov()
    result = solve_erc_portfolio(cov)
    assert np.all(result['weights'] >= -1e-8)

def test_solve_erc_equal_risk_contributions():
    """ERC solution should have approximately equal risk contributions."""
    cov = make_sample_cov()
    result = solve_erc_portfolio(cov)
    rc = result['risk_contributions']
    rc_norm = rc / rc.sum()
    # Each normalized RC should be close to 1/5 = 0.2
    np.testing.assert_allclose(rc_norm, np.ones(5)/5, atol=0.05)

def test_equal_weight_portfolio():
    """Equal weight portfolio should have all weights = 1/N."""
    w = compute_equal_weight_portfolio(5)
    np.testing.assert_allclose(w, np.ones(5)/5)
    assert abs(w.sum() - 1.0) < 1e-10

def test_portfolio_returns_array_shape():
    """Portfolio returns should have correct shape."""
    dates = pd.date_range('2019-01-31', periods=48, freq='ME')
    returns = pd.DataFrame(np.random.randn(48, 5)*0.03, index=dates,
                           columns=['ACWI','TLT','DBC','RWR','TIP'])
    w = np.ones(5)/5
    port_ret = compute_portfolio_returns_array(returns, w)
    assert len(port_ret) == 48

def test_build_static_erc_portfolio_weights():
    """Static ERC portfolio should return valid weights."""
    np.random.seed(42)
    dates = pd.date_range('2009-01-31', periods=120, freq='ME')
    returns = pd.DataFrame(np.random.randn(120, 5)*0.03, index=dates,
                           columns=['ACWI','TLT','DBC','RWR','TIP'])
    result = build_static_erc_portfolio(returns)
    assert abs(sum(result['weights']) - 1.0) < 1e-6
    assert all(w >= -1e-8 for w in result['weights'])
