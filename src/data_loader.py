"""Download monthly adjusted close prices for Risk Parity experiment assets."""

import logging
import os
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

TICKERS = ['^GSPC', 'AGG', 'ACWI', 'TLT', 'DBC', 'RWR', 'TIP']
DEFAULT_START = '2008-12-01'
DEFAULT_END = '2022-12-31'
DEFAULT_SAVE_PATH = str(Path(__file__).resolve().parents[1] / 'data' / 'raw_prices.csv')

# Mapping from Yahoo-style tickers to Polygon.io-style tickers used by massive
_MASSIVE_TICKER_MAP = {
    '^GSPC': 'I:SPX',
}


def _fetch_via_massive(ticker: str, start: str, end: str) -> pd.Series:
    """Fetch monthly close prices for one ticker using the massive RESTClient.

    Parameters
    ----------
    ticker:
        Yahoo Finance-style ticker symbol.
    start:
        Start date string in YYYY-MM-DD format.
    end:
        End date string in YYYY-MM-DD format.

    Returns
    -------
    pd.Series
        Monthly close prices indexed by month-end dates, or empty Series on failure.
    """
    from massive import RESTClient  # noqa: PLC0415

    api_key = os.getenv('MASSIVE_TOKEN')
    if not api_key:
        raise EnvironmentError('MASSIVE_TOKEN environment variable is not set.')

    massive_ticker = _MASSIVE_TICKER_MAP.get(ticker, ticker)
    client = RESTClient(api_key=api_key)

    aggs = []
    for a in client.list_aggs(
        ticker=massive_ticker,
        multiplier=1,
        timespan='month',
        from_=start,
        to=end,
        limit=50000,
    ):
        aggs.append(a)

    if not aggs:
        return pd.Series(dtype=float, name=ticker)

    records = {
        pd.Timestamp(a.timestamp, unit='ms'): a.close
        for a in aggs
        if a.timestamp is not None and a.close is not None
    }
    series = pd.Series(records, name=ticker)
    series.index = series.index + pd.offsets.MonthEnd(0)
    series.index.name = 'date'
    return series.sort_index()


def _fetch_via_yfinance(ticker: str, start: str, end: str) -> pd.Series:
    """Fetch monthly adjusted close prices using yfinance.

    Parameters
    ----------
    ticker:
        Yahoo Finance-style ticker symbol.
    start:
        Start date string in YYYY-MM-DD format.
    end:
        End date string in YYYY-MM-DD format.

    Returns
    -------
    pd.Series
        Monthly close prices indexed by month-end dates, or empty Series on failure.
    """
    import yfinance as yf  # noqa: PLC0415

    # Extend end by one month so the final month is included
    end_extended = (pd.Timestamp(end) + pd.offsets.MonthEnd(1)).strftime('%Y-%m-%d')
    raw = yf.download(
        ticker,
        start=start,
        end=end_extended,
        interval='1mo',
        auto_adjust=True,
        progress=False,
    )
    if raw.empty:
        return pd.Series(dtype=float, name=ticker)

    # yfinance may return MultiIndex columns when downloading a single ticker
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)

    col = 'Close' if 'Close' in raw.columns else raw.columns[0]
    series = raw[col].dropna().rename(ticker)
    series.index = pd.DatetimeIndex(series.index) + pd.offsets.MonthEnd(0)
    series.index.name = 'date'
    # Clip to requested date range
    series = series.loc[start:end]
    return series.sort_index()


def _fetch_via_datareader(ticker: str, start: str, end: str) -> pd.Series:
    """Fetch monthly adjusted close prices using pandas_datareader (Yahoo).

    Parameters
    ----------
    ticker:
        Yahoo Finance-style ticker symbol.
    start:
        Start date string in YYYY-MM-DD format.
    end:
        End date string in YYYY-MM-DD format.

    Returns
    -------
    pd.Series
        Monthly close prices indexed by month-end dates, or empty Series on failure.
    """
    import pandas_datareader.data as web  # noqa: PLC0415

    raw = web.DataReader(ticker, 'yahoo', start=start, end=end)
    if raw.empty:
        return pd.Series(dtype=float, name=ticker)

    col = 'Adj Close' if 'Adj Close' in raw.columns else 'Close'
    daily = raw[col].dropna()
    # Resample to month-end
    series = daily.resample('ME').last().rename(ticker)
    series.index.name = 'date'
    return series.sort_index()


def _fetch_ticker(ticker: str, start: str, end: str) -> pd.Series:
    """Fetch monthly close prices for one ticker, trying multiple sources.

    Attempt order:
    1. massive RESTClient
    2. yfinance
    3. pandas_datareader (Yahoo)

    For '^GSPC', if all attempts fail, retry yfinance and pandas_datareader
    with 'SPY' as an ETF proxy.

    Parameters
    ----------
    ticker:
        Yahoo Finance-style ticker symbol.
    start:
        Start date string in YYYY-MM-DD format.
    end:
        End date string in YYYY-MM-DD format.

    Returns
    -------
    pd.Series
        Monthly close prices indexed by month-end dates.

    Raises
    ------
    RuntimeError
        If all data sources fail to return data for the ticker.
    """
    # 1. Try massive
    try:
        series = _fetch_via_massive(ticker, start, end)
        if not series.empty:
            logger.info('Fetched %s via massive (%d rows).', ticker, len(series))
            return series
        logger.warning('massive returned no data for %s.', ticker)
    except Exception as exc:
        logger.warning('massive failed for %s: %s', ticker, exc)

    # 2. Try yfinance
    try:
        series = _fetch_via_yfinance(ticker, start, end)
        if not series.empty:
            logger.info('Fetched %s via yfinance (%d rows).', ticker, len(series))
            return series
        logger.warning('yfinance returned no data for %s.', ticker)
    except Exception as exc:
        logger.warning('yfinance failed for %s: %s', ticker, exc)

    # 3. Try pandas_datareader
    try:
        series = _fetch_via_datareader(ticker, start, end)
        if not series.empty:
            logger.info('Fetched %s via pandas_datareader (%d rows).', ticker, len(series))
            return series
        logger.warning('pandas_datareader returned no data for %s.', ticker)
    except Exception as exc:
        logger.warning('pandas_datareader failed for %s: %s', ticker, exc)

    # 4. For '^GSPC', fall back to SPY as ETF proxy
    if ticker == '^GSPC':
        logger.warning("All sources failed for '^GSPC'; retrying with 'SPY' as ETF proxy.")
        proxy = 'SPY'
        try:
            series = _fetch_via_yfinance(proxy, start, end).rename(ticker)
            if not series.empty:
                logger.info("Fetched '%s' proxy via yfinance (%d rows).", proxy, len(series))
                return series
        except Exception as exc:
            logger.warning('yfinance failed for %s proxy: %s', proxy, exc)

        try:
            series = _fetch_via_datareader(proxy, start, end).rename(ticker)
            if not series.empty:
                logger.info("Fetched '%s' proxy via pandas_datareader (%d rows).", proxy, len(series))
                return series
        except Exception as exc:
            logger.warning('pandas_datareader failed for %s proxy: %s', proxy, exc)

    raise RuntimeError(f'All data sources failed to return data for ticker: {ticker}')


def download_prices(
    tickers: list[str],
    start: str,
    end: str,
    save_path: str | None = None,
) -> pd.DataFrame:
    """Download monthly adjusted close prices for a list of tickers.

    Attempts to fetch data from the massive RESTClient first, then falls back
    to yfinance and pandas_datareader (Yahoo Finance) if massive is unavailable
    or returns no data.

    Parameters
    ----------
    tickers:
        List of ticker symbols (Yahoo Finance format, e.g. '^GSPC', 'AGG').
    start:
        Start date in YYYY-MM-DD format (inclusive).
    end:
        End date in YYYY-MM-DD format (inclusive).
    save_path:
        Optional file path to save the resulting CSV. If ``None``, the file is
        saved to ``<project_root>/data/raw_prices.csv``.

    Returns
    -------
    pd.DataFrame
        DataFrame with a DatetimeIndex of month-end dates and one column per
        ticker containing adjusted close prices.

    Raises
    ------
    RuntimeError
        If data cannot be retrieved for any ticker from any source.
    """
    if save_path is None:
        save_path = DEFAULT_SAVE_PATH

    series_list: list[pd.Series] = []
    failed: list[str] = []

    for ticker in tickers:
        try:
            s = _fetch_ticker(ticker, start, end)
            series_list.append(s)
        except RuntimeError as exc:
            logger.error(str(exc))
            failed.append(ticker)

    if failed:
        raise RuntimeError(f'Failed to download data for tickers: {failed}')

    prices = pd.concat(series_list, axis=1)
    prices.index = pd.DatetimeIndex(prices.index)
    prices.index.name = 'date'
    prices.sort_index(inplace=True)

    # Persist raw prices
    out_path = Path(save_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    prices.to_csv(out_path)
    logger.info('Raw prices saved to %s', out_path)

    return prices
