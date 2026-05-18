"""
Experiment 3: Static Five-Asset ERC Risk Parity vs Equal-Weight Benchmark

Replicates the five-asset static ERC Risk Parity vs equal-weight benchmark.
Assets: ACWI, TLT, DBC, RWR, TIP.
Estimation window: 2009-01 to 2018-12 (10 years).
Testing window: 2019-01 to 2022-12 (4 years).
Risk-free rate: 3-month T-bill (TB3MS from FRED) used in Sharpe/Sortino/Treynor numerators.
Market benchmark for beta/covariance: ACWI.
"""

import sys
import os

sys.path.insert(0, '/workspace/project')

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from src.data_loader import download_prices
from src.preprocessing import (
    align_month_end,
    compute_returns,
    get_estimation_window,
    get_testing_window,
    convert_rf_to_monthly,
)
from src.stats_validation import (
    compute_descriptive_stats,
    compute_covariance_matrix,
    compute_correlation_matrix,
)
from src.portfolio_five_asset import (
    build_static_erc_portfolio,
    compute_equal_weight_portfolio,
    compute_portfolio_returns_array,
)
from src.metrics import compute_portfolio_metrics

RESULTS_DIR = '/workspace/project/results'
TICKERS = ['ACWI', 'TLT', 'DBC', 'RWR', 'TIP']
START_DATE = '2008-12-01'
END_DATE = '2022-12-31'
EST_START = '2009-01'
EST_END = '2018-12'
TEST_START = '2019-01'
TEST_END = '2022-12'

THESIS_WEIGHTS = {
    'ACWI': 0.1959, 'TLT': 0.2338, 'DBC': 0.1737, 'RWR': 0.1493, 'TIP': 0.2473
}
THESIS_TARGETS = {
    'RP': {'mean': 0.004335, 'std': 0.0267, 'covariance': 0.0012, 'beta': 0.4399,
           'downside_risk': 0.0228, 'sharpe': 0.1271, 'sortino': 0.1493, 'treynor': 0.0077},
    'EW': {'mean': 0.005581, 'std': 0.0339, 'covariance': 0.0016, 'beta': 0.5842,
           'downside_risk': 0.0279, 'sharpe': 0.1370, 'sortino': 0.1663, 'treynor': 0.0079},
}


def _load_rf(test_index: pd.DatetimeIndex) -> pd.Series:
    """Load 3-month T-bill rate as monthly risk-free rate, with fallback."""
    try:
        import pandas_datareader.data as web
        tb3ms = web.DataReader('TB3MS', 'fred', '2019-01-01', '2022-12-31')
        rf_annual = tb3ms['TB3MS'] / 100
        rf_monthly = convert_rf_to_monthly(rf_annual)
        rf_monthly = rf_monthly.resample('ME').last().reindex(test_index, method='ffill')
        print("Risk-free rate loaded from FRED (TB3MS).")
        return rf_monthly
    except Exception as e:
        print(f"FRED TB3MS unavailable ({e}); using fallback rf = 0.15% per month.")
        return pd.Series(0.0015, index=test_index)


def run_exp3() -> dict:
    """Run static five-asset ERC Risk Parity experiment. Returns results dict."""
    os.makedirs(RESULTS_DIR, exist_ok=True)

    # ── 1. Load and preprocess data ──────────────────────────────────────────
    print("=" * 70)
    print("Experiment 3: Static Five-Asset ERC Risk Parity vs Equal-Weight")
    print("=" * 70)
    print(f"\nLoading data for {TICKERS} from {START_DATE} to {END_DATE}...")
    prices = download_prices(TICKERS, START_DATE, END_DATE)
    prices_aligned = align_month_end(prices)
    returns = compute_returns(prices_aligned)
    print(f"Total monthly returns: {len(returns)} observations")
    print(f"Columns: {list(returns.columns)}")

    # ── 2. Estimation window ─────────────────────────────────────────────────
    est_returns = get_estimation_window(returns, EST_START, EST_END)
    print(f"\nEstimation window: {EST_START} to {EST_END} ({len(est_returns)} months)")

    desc_stats = compute_descriptive_stats(est_returns)
    print("\nDescriptive Statistics (Estimation Window):")
    print(desc_stats.to_string(float_format=lambda x: f"{x:.6f}"))

    cov_matrix = compute_covariance_matrix(est_returns)
    print("\nCovariance Matrix (Estimation Window):")
    print(cov_matrix.to_string(float_format=lambda x: f"{x:.8f}"))

    corr_matrix = compute_correlation_matrix(est_returns)
    print("\nCorrelation Matrix (Estimation Window):")
    print(corr_matrix.to_string(float_format=lambda x: f"{x:.4f}"))

    # ── 3. Build static ERC portfolio ────────────────────────────────────────
    erc_result = build_static_erc_portfolio(est_returns)
    weights = erc_result['weights']
    asset_names = erc_result['asset_names']

    print(f"\nERC Optimization: converged={erc_result['converged']}, "
          f"objective={erc_result['objective']:.2e}, iterations={erc_result['iterations']}")
    print("\nStatic ERC Weights:")
    print(f"{'Asset':<8} {'Computed':>12} {'Thesis Target':>15}")
    print("-" * 37)
    for name, w in zip(asset_names, weights):
        tgt = THESIS_WEIGHTS.get(name, float('nan'))
        print(f"{name:<8} {w*100:>11.2f}%  {tgt*100:>13.2f}%")

    print("\nNormalized Risk Contributions (should be ~20% each):")
    for name, rc in zip(asset_names, erc_result['rc_normalized']):
        print(f"  {name}: {rc*100:.2f}%")

    # ── 4. Testing window ────────────────────────────────────────────────────
    test_returns = get_testing_window(returns, TEST_START, TEST_END)
    print(f"\nTesting window: {TEST_START} to {TEST_END} ({len(test_returns)} months)")

    rp_returns = compute_portfolio_returns_array(test_returns, weights)
    rp_returns.name = 'RP'

    ew_weights = compute_equal_weight_portfolio(len(TICKERS))
    ew_returns = compute_portfolio_returns_array(test_returns, ew_weights)
    ew_returns.name = 'EW'

    market_returns = test_returns['ACWI']

    # ── 5. Load risk-free rate ───────────────────────────────────────────────
    rf_monthly = _load_rf(test_returns.index)

    # ── 6. Compute metrics ───────────────────────────────────────────────────
    rp_metrics = compute_portfolio_metrics(rp_returns, market_returns, rf=rf_monthly)
    ew_metrics = compute_portfolio_metrics(ew_returns, market_returns, rf=rf_monthly)

    # ── 7. Print comparison table ────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("Performance Metrics (Testing Window 2019-01 to 2022-12)")
    print("=" * 70)
    metrics_order = ['mean', 'std', 'covariance', 'beta', 'downside_risk',
                     'sharpe', 'sortino', 'treynor']
    header = f"{'Metric':<18} {'RP Computed':>14} {'RP Thesis':>12} {'EW Computed':>14} {'EW Thesis':>12}"
    print(header)
    print("-" * 72)
    for m in metrics_order:
        rp_val = rp_metrics[m]
        ew_val = ew_metrics[m]
        rp_tgt = THESIS_TARGETS['RP'].get(m, float('nan'))
        ew_tgt = THESIS_TARGETS['EW'].get(m, float('nan'))
        print(f"{m:<18} {rp_val:>14.6f} {rp_tgt:>12.4f} {ew_val:>14.6f} {ew_tgt:>12.4f}")

    # ── 8. Save results to CSV ───────────────────────────────────────────────
    results_df = pd.DataFrame({
        'RP': rp_metrics,
        'RP_thesis': THESIS_TARGETS['RP'],
        'EW': ew_metrics,
        'EW_thesis': THESIS_TARGETS['EW'],
    })
    csv_path = os.path.join(RESULTS_DIR, 'exp3_results.csv')
    results_df.to_csv(csv_path)
    print(f"\nResults saved to {csv_path}")

    # ── 9. Plot cumulative returns ───────────────────────────────────────────
    cum_rp = (1 + rp_returns).cumprod()
    cum_ew = (1 + ew_returns).cumprod()
    cum_acwi = (1 + market_returns).cumprod()

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(cum_rp.index, cum_rp.values, label='ERC Risk Parity', linewidth=2, color='steelblue')
    ax.plot(cum_ew.index, cum_ew.values, label='Equal-Weight (EW)', linewidth=2,
            color='darkorange', linestyle='--')
    ax.plot(cum_acwi.index, cum_acwi.values, label='ACWI (Market)', linewidth=1.5,
            color='gray', linestyle=':')
    ax.set_title('Exp 3: Static Five-Asset ERC RP vs Equal-Weight Benchmark\n'
                 'Cumulative Returns (2019–2022)', fontsize=13)
    ax.set_xlabel('Date')
    ax.set_ylabel('Cumulative Return (Base = 1)')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plot_path = os.path.join(RESULTS_DIR, 'exp3_cumulative_returns.png')
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Plot saved to {plot_path}")

    return {
        'erc_weights': dict(zip(asset_names, weights)),
        'rp_metrics': rp_metrics,
        'ew_metrics': ew_metrics,
        'rp_returns': rp_returns,
        'ew_returns': ew_returns,
    }


if __name__ == '__main__':
    run_exp3()
