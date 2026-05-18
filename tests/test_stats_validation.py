import pytest
import numpy as np
import pandas as pd
import sys
sys.path.insert(0, '/workspace/project')
from src.stats_validation import (
    compute_descriptive_stats,
    compute_covariance_matrix,
    compute_correlation_matrix,
    validate_estimation_stats
)

def make_sample_returns(n=120, seed=42):
    np.random.seed(seed)
    dates = pd.date_range('2009-01-31', periods=n, freq='ME')
    return pd.DataFrame({
        'SPY': np.random.randn(n)*0.04 + 0.01,
        'AGG': np.random.randn(n)*0.01 + 0.002
    }, index=dates)

def test_descriptive_stats_shape():
    """Descriptive stats should have correct shape."""
    returns = make_sample_returns()
    stats = compute_descriptive_stats(returns)
    assert 'mean' in stats.index
    assert 'std' in stats.index
    assert 'skewness' in stats.index
    assert 'kurtosis' in stats.index
    assert 'serial_corr' in stats.index

def test_descriptive_stats_std_positive():
    """Standard deviation must be positive."""
    returns = make_sample_returns()
    stats = compute_descriptive_stats(returns)
    assert all(stats.loc['std'] > 0)

def test_covariance_matrix_symmetric():
    """Covariance matrix must be symmetric."""
    returns = make_sample_returns()
    cov = compute_covariance_matrix(returns)
    np.testing.assert_allclose(cov.values, cov.values.T, rtol=1e-10)

def test_covariance_matrix_positive_diagonal():
    """Diagonal of covariance matrix must be positive."""
    returns = make_sample_returns()
    cov = compute_covariance_matrix(returns)
    assert all(np.diag(cov.values) > 0)

def test_correlation_matrix_diagonal_ones():
    """Diagonal of correlation matrix must be 1."""
    returns = make_sample_returns()
    corr = compute_correlation_matrix(returns)
    np.testing.assert_allclose(np.diag(corr.values), np.ones(2), rtol=1e-10)

def test_correlation_matrix_range():
    """Correlation values must be in [-1, 1]."""
    returns = make_sample_returns()
    corr = compute_correlation_matrix(returns)
    assert np.all(corr.values >= -1.0 - 1e-10)
    assert np.all(corr.values <= 1.0 + 1e-10)

def test_validate_estimation_stats_returns_dict():
    """Validation function should return a dict."""
    returns = make_sample_returns()
    stats = compute_descriptive_stats(returns)
    targets = {'SPY_mean': 0.01, 'AGG_mean': 0.002}
    result = validate_estimation_stats(stats, targets)
    assert isinstance(result, dict)

def test_descriptive_stats_single_asset():
    """Should work with single asset."""
    np.random.seed(0)
    dates = pd.date_range('2009-01-31', periods=60, freq='ME')
    returns = pd.DataFrame({'SPY': np.random.randn(60)*0.04}, index=dates)
    stats = compute_descriptive_stats(returns)
    assert stats.shape[1] == 1

def test_descriptive_stats_extreme_values():
    """Should handle extreme values without error."""
    dates = pd.date_range('2009-01-31', periods=10, freq='ME')
    returns = pd.DataFrame({'A': [1e6, -1e6, 1e6, -1e6, 1e6, -1e6, 1e6, -1e6, 1e6, -1e6]}, index=dates)
    stats = compute_descriptive_stats(returns)
    assert np.isfinite(stats.loc['mean', 'A'])
