import pytest
import numpy as np
import pandas as pd
import sys
sys.path.insert(0, '/workspace/project')
from src.portfolio_two_asset import (
    compute_rp_weights_two_asset,
    compute_benchmark_weights_two_asset,
    compute_portfolio_returns,
    build_static_rp_portfolio,
    build_annual_rp_portfolios,
    apply_annual_weights
)

def test_rp_weights_sum_to_one():
    """Weights must sum to 1."""
    w_e, w_b = compute_rp_weights_two_asset(0.0441, 0.0113)
    assert abs(w_e + w_b - 1.0) < 1e-10

def test_rp_weights_thesis_values():
    """Validate thesis-reported weights: ~20.40% equity, ~79.60% bond."""
    w_e, w_b = compute_rp_weights_two_asset(0.0441, 0.0113)
    assert abs(w_e - 0.2040) < 0.01, f'Expected ~0.2040, got {w_e:.4f}'
    assert abs(w_b - 0.7960) < 0.01, f'Expected ~0.7960, got {w_b:.4f}'

def test_rp_weights_inverse_vol_property():
    """Higher vol asset gets lower weight."""
    sigma_high, sigma_low = 0.05, 0.01
    w_high, w_low = compute_rp_weights_two_asset(sigma_high, sigma_low)
    assert w_high < w_low, 'Higher vol asset should have lower weight'

def test_rp_weights_equal_vol():
    """Equal volatility should give 50/50 weights."""
    w_e, w_b = compute_rp_weights_two_asset(0.05, 0.05)
    assert abs(w_e - 0.5) < 1e-10
    assert abs(w_b - 0.5) < 1e-10

def test_benchmark_weights():
    """Benchmark should be 50/50."""
    w_e, w_b = compute_benchmark_weights_two_asset()
    assert w_e == 0.5
    assert w_b == 0.5

def test_portfolio_returns_shape():
    """Portfolio returns should have same length as input."""
    dates = pd.date_range('2019-01-31', periods=48, freq='ME')
    returns = pd.DataFrame({'SPY': np.random.randn(48)*0.04, 'AGG': np.random.randn(48)*0.01}, index=dates)
    weights = {'SPY': 0.2, 'AGG': 0.8}
    port_ret = compute_portfolio_returns(returns, weights)
    assert len(port_ret) == 48

def test_portfolio_returns_weighted_sum():
    """Portfolio returns should equal weighted sum."""
    dates = pd.date_range('2019-01-31', periods=3, freq='ME')
    returns = pd.DataFrame({'SPY': [0.01, 0.02, -0.01], 'AGG': [0.005, -0.002, 0.003]}, index=dates)
    weights = {'SPY': 0.2, 'AGG': 0.8}
    port_ret = compute_portfolio_returns(returns, weights)
    expected = [0.2*0.01 + 0.8*0.005, 0.2*0.02 + 0.8*(-0.002), 0.2*(-0.01) + 0.8*0.003]
    np.testing.assert_allclose(port_ret.values, expected, rtol=1e-10)

def test_build_static_rp_portfolio():
    """Static RP portfolio should return valid weights."""
    np.random.seed(42)
    dates = pd.date_range('2009-01-31', periods=120, freq='ME')
    returns = pd.DataFrame({'SPY': np.random.randn(120)*0.04, 'AGG': np.random.randn(120)*0.01}, index=dates)
    result = build_static_rp_portfolio(returns, 'SPY', 'AGG')
    assert abs(result['w_equity'] + result['w_bond'] - 1.0) < 1e-10
    assert result['w_equity'] < result['w_bond']  # SPY more volatile

def test_annual_rp_no_lookahead():
    """Annual RP weights must use only data through prior December."""
    np.random.seed(42)
    dates = pd.date_range('2009-01-31', periods=168, freq='ME')  # through 2022-12
    returns = pd.DataFrame({'SPY': np.random.randn(168)*0.04, 'AGG': np.random.randn(168)*0.01}, index=dates)
    annual_weights = build_annual_rp_portfolios(returns, 'SPY', 'AGG', [2019, 2020, 2021, 2022])
    # 2020 weights should be based on data through 2019-12 only
    assert 2020 in annual_weights
    # Verify estimation window end
    est_end_2020 = '2019-12-31'
    est_returns_2020 = returns.loc['2010-01-01':est_end_2020]
    sigma_spy = est_returns_2020['SPY'].std()
    sigma_agg = est_returns_2020['AGG'].std()
    w_spy_expected = sigma_agg / (sigma_spy + sigma_agg)
    assert abs(annual_weights[2020]['w_equity'] - w_spy_expected) < 1e-10
