"""Preprocessing utilities for the Risk Parity experiment."""

import pandas as pd


def align_month_end(prices: pd.DataFrame) -> pd.DataFrame:
    """Align all price series to common month-end dates.

    Snaps every index entry to the last calendar day of its month, forward-fills
    missing values by at most one period, then drops any row that still contains
    a NaN (i.e. assets with no overlapping history are removed row-wise).

    Parameters
    ----------
    prices:
        DataFrame of raw prices with a DatetimeIndex.

    Returns
    -------
    pd.DataFrame
        Prices re-indexed to month-end dates with no NaN values.
    """
    df = prices.copy()
    df.index = df.index + pd.offsets.MonthEnd(0)
    df = df[~df.index.duplicated(keep='last')]
    df.sort_index(inplace=True)
    df = df.ffill(limit=1)
    df.dropna(how='any', inplace=True)
    return df


def compute_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Compute simple monthly returns from a price DataFrame.

    Returns are defined as r_t = P_t / P_{t-1} - 1.  The first row (which
    would be NaN) is dropped.

    Parameters
    ----------
    prices:
        DataFrame of adjusted close prices with a DatetimeIndex.

    Returns
    -------
    pd.DataFrame
        Monthly simple returns with the same columns as *prices* and one fewer
        row (the first observation is consumed as the lagged price).
    """
    returns = prices.pct_change()
    return returns.iloc[1:].copy()


def get_estimation_window(returns: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    """Slice a returns DataFrame to the estimation window.

    Parameters
    ----------
    returns:
        DataFrame of monthly returns with a DatetimeIndex.
    start:
        Start date of the estimation window (inclusive), in YYYY-MM-DD format.
    end:
        End date of the estimation window (inclusive), in YYYY-MM-DD format.

    Returns
    -------
    pd.DataFrame
        Returns restricted to [start, end].
    """
    return returns.loc[start:end].copy()


def get_testing_window(returns: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    """Slice a returns DataFrame to the testing (out-of-sample) window.

    Parameters
    ----------
    returns:
        DataFrame of monthly returns with a DatetimeIndex.
    start:
        Start date of the testing window (inclusive), in YYYY-MM-DD format.
    end:
        End date of the testing window (inclusive), in YYYY-MM-DD format.

    Returns
    -------
    pd.DataFrame
        Returns restricted to [start, end].
    """
    return returns.loc[start:end].copy()


def convert_rf_to_monthly(rf_annual: pd.Series) -> pd.Series:
    """Convert an annualised T-bill rate series to a monthly rate.

    Uses the simple approximation: rf_month = annual_yield / 12.
    Rates are assumed to be expressed as decimals (e.g. 0.05 for 5 %).

    Parameters
    ----------
    rf_annual:
        Series of annualised risk-free rates with a DatetimeIndex.

    Returns
    -------
    pd.Series
        Monthly risk-free rates with the same index as *rf_annual*.
    """
    return rf_annual / 12
