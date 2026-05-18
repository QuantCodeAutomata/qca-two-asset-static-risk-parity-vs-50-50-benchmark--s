"""Estimation-window statistics and validation for the Risk Parity experiment."""

import numpy as np
import pandas as pd
from scipy import stats


def compute_descriptive_stats(returns: pd.DataFrame) -> pd.DataFrame:
    """Compute descriptive statistics for each asset over the estimation window.

    Statistics computed per asset (column):

    * ``mean``        – arithmetic mean of monthly returns
    * ``std``         – sample standard deviation of monthly returns
    * ``skewness``    – Fisher skewness (bias-corrected via scipy)
    * ``excess_kurt`` – excess kurtosis (Fisher definition, bias-corrected)
    * ``autocorr_1``  – lag-1 serial (auto-)correlation

    Parameters
    ----------
    returns:
        DataFrame of monthly simple returns with assets as columns.

    Returns
    -------
    pd.DataFrame
        DataFrame with statistics as the row index and assets as columns.
    """
    result: dict[str, pd.Series] = {}

    result['mean'] = returns.mean()
    result['std'] = returns.std(ddof=1)
    result['skewness'] = returns.apply(lambda col: stats.skew(col.dropna(), bias=False))
    result['kurtosis'] = returns.apply(
        lambda col: stats.kurtosis(col.dropna(), fisher=True, bias=False)
    )
    result['serial_corr'] = returns.apply(lambda col: col.dropna().autocorr(lag=1))

    return pd.DataFrame(result).T


def compute_covariance_matrix(returns: pd.DataFrame) -> pd.DataFrame:
    """Compute the sample covariance matrix of monthly returns.

    Uses the standard unbiased estimator (ddof=1, i.e. pandas default).

    Parameters
    ----------
    returns:
        DataFrame of monthly simple returns with assets as columns.

    Returns
    -------
    pd.DataFrame
        Square covariance matrix with assets as both row and column labels.
    """
    return returns.cov()


def compute_correlation_matrix(returns: pd.DataFrame) -> pd.DataFrame:
    """Compute the sample Pearson correlation matrix of monthly returns.

    Parameters
    ----------
    returns:
        DataFrame of monthly simple returns with assets as columns.

    Returns
    -------
    pd.DataFrame
        Square correlation matrix with assets as both row and column labels.
    """
    return returns.corr()


def validate_estimation_stats(
    computed: pd.DataFrame,
    thesis_targets: dict,
) -> dict:
    """Compare computed estimation-window statistics to thesis target values.

    For each statistic and asset present in *thesis_targets*, the function
    calculates the absolute difference ``computed - target`` and flags whether
    the discrepancy exceeds a tolerance of 1 × 10⁻⁴.

    Parameters
    ----------
    computed:
        DataFrame returned by :func:`compute_descriptive_stats`, with
        statistics as rows and assets as columns.
    thesis_targets:
        Nested dict of the form ``{stat_name: {asset: target_value}}``.
        Example::

            {
                'mean': {'^GSPC': 0.0082, 'AGG': 0.0031},
                'std':  {'^GSPC': 0.0412, 'AGG': 0.0098},
            }

    Returns
    -------
    dict
        Nested dict with the same structure as *thesis_targets* where each
        leaf value is itself a dict::

            {
                'computed': <float>,
                'target':   <float>,
                'diff':     <float>,          # computed - target
                'within_tolerance': <bool>,   # |diff| <= 1e-4
            }
    """
    tolerance = 1e-4
    results: dict = {}

    for key, value in thesis_targets.items():
        if not isinstance(value, dict):
            results[key] = {'target': float(value)}
            continue
        results[key] = {}
        for asset, target in value.items():
            try:
                computed_val = float(computed.loc[key, asset])
            except KeyError:
                computed_val = float('nan')
            diff = computed_val - target
            results[key][asset] = {
                'computed': computed_val,
                'target': float(target),
                'diff': diff,
                'within_tolerance': abs(diff) <= tolerance,
            }

    return results
