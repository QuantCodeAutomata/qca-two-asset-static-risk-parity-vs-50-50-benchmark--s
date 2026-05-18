"""
Experiment 1: Static Two-Asset Risk Parity vs 50/50 Benchmark

Replicates the two-asset static Risk Parity vs 50/50 benchmark from the thesis.
Assets: SPY (S&P 500 proxy) and AGG (US Aggregate Bond ETF).
Estimation window: 2009-01 to 2018-12 (10 years).
Testing window: 2019-01 to 2022-12 (4 years).
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
)
from src.stats_validation import compute_descriptive_stats, compute_covariance_matrix
from src.portfolio_two_asset import (
    build_static_rp_portfolio,
    compute_portfolio_returns,
    compute_benchmark_weights_two_asset,
)
from src.metrics import compute_portfolio_metrics

RESULTS_DIR = '/workspace/project/results'
TICKERS = ['SPY', 'AGG']
START_DATE = '2008-12-01'
END_DATE = '2022-12-31'
EST_START = '2009-01'
EST_END = '2018-12'
TEST_START = '2019-01'
TEST_END = '2022-12'

THESIS_TARGETS = {
    'RP':   {'mean': 0.001001, 'std': 0.0212, 'covariance': 0.0010, 'beta': 0.3188,
             'downside_risk': 0.0161, 'sharpe': 0.0473, 'sortino': 0.0623, 'treynor': 0.0031},
    '50/50': {'mean': 0.003522, 'std': 0.0322, 'covariance': 0.0018, 'beta': 0.5605,
              'downside_risk': 0.0204, 'sharpe': 0.1094, 'sortino': 0.1729, 'treynor': 0.0063},
}


def run_exp1() -> dict:
    """Run static two-asset Risk Parity experiment. Returns results dict."""
    os.makedirs(RESULTS_DIR, exist_ok=True)

    # ── 1. Load and preprocess data ──────────────────────────────────────────
    print("=" * 70)
    print("Experiment 1: Static Two-Asset Risk Parity vs 50/50 Benchmark")
    print("=" * 70)
    print(f"\nLoading data for {TICKERS} from {START_DATE} to {END_DATE}...")
    prices = download_prices(TICKERS, START_DATE, END_DATE)
    prices_aligned = align_month_end(prices)
    returns = compute_returns(prices_aligned)
    print(f"Total monthly returns: {len(returns)} observations")

    # ── 2. Estimation window ─────────────────────────────────────────────────
    est_returns = get_estimation_window(returns, EST_START, EST_END)
    print(f"\nEstimation window: {EST_START} to {EST_END} ({len(est_returns)} months)")

    desc_stats = compute_descriptive_stats(est_returns)
    print("\nDescriptive Statistics (Estimation Window):")
    print(desc_stats.to_string(float_format=lambda x: f"{x:.6f}"))

    cov_matrix = compute_covariance_matrix(est_returns)
    print("\nCovariance Matrix (Estimation Window):")
    print(cov_matrix.to_string(float_format=lambda x: f"{x:.8f}"))

    # ── 3. Build static RP portfolio ─────────────────────────────────────────
    rp_info = build_static_rp_portfolio(est_returns, 'SPY', 'AGG')
    w_spy = rp_info['w_equity']
    w_agg = rp_info['w_bond']

    print(f"\nStatic RP Weights:")
    print(f"  SPY (equity): {w_spy:.4f} ({w_spy*100:.2f}%)  [thesis target: ~20.40%]")
    print(f"  AGG (bond):   {w_agg:.4f} ({w_agg*100:.2f}%)  [thesis target: ~79.60%]")
    print(f"  sigma_SPY = {rp_info['sigma_equity']:.6f}, sigma_AGG = {rp_info['sigma_bond']:.6f}")

    # ── 4. Testing window ────────────────────────────────────────────────────
    test_returns = get_testing_window(returns, TEST_START, TEST_END)
    print(f"\nTesting window: {TEST_START} to {TEST_END} ({len(test_returns)} months)")

    rp_returns = compute_portfolio_returns(test_returns, rp_info['weights'])
    rp_returns.name = 'RP'

    bm_w_eq, bm_w_bond = compute_benchmark_weights_two_asset()
    bm_weights = {'SPY': bm_w_eq, 'AGG': bm_w_bond}
    bm_returns = compute_portfolio_returns(test_returns, bm_weights)
    bm_returns.name = '50/50'

    market_returns = test_returns['SPY']

    # ── 5. Compute metrics ───────────────────────────────────────────────────
    rp_metrics = compute_portfolio_metrics(rp_returns, market_returns, rf=None)
    bm_metrics = compute_portfolio_metrics(bm_returns, market_returns, rf=None)

    # ── 6. Print comparison table ────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("Performance Metrics (Testing Window 2019-01 to 2022-12)")
    print("=" * 70)
    metrics_order = ['mean', 'std', 'covariance', 'beta', 'downside_risk',
                     'sharpe', 'sortino', 'treynor']
    header = f"{'Metric':<18} {'RP Computed':>14} {'RP Thesis':>12} {'50/50 Computed':>16} {'50/50 Thesis':>14}"
    print(header)
    print("-" * 76)
    for m in metrics_order:
        rp_val = rp_metrics[m]
        bm_val = bm_metrics[m]
        rp_tgt = THESIS_TARGETS['RP'].get(m, float('nan'))
        bm_tgt = THESIS_TARGETS['50/50'].get(m, float('nan'))
        print(f"{m:<18} {rp_val:>14.6f} {rp_tgt:>12.4f} {bm_val:>16.6f} {bm_tgt:>14.4f}")

    # ── 7. Save results to CSV ───────────────────────────────────────────────
    results_df = pd.DataFrame({
        'RP': rp_metrics,
        'RP_thesis': THESIS_TARGETS['RP'],
        '50/50': bm_metrics,
        '50/50_thesis': THESIS_TARGETS['50/50'],
    })
    csv_path = os.path.join(RESULTS_DIR, 'exp1_results.csv')
    results_df.to_csv(csv_path)
    print(f"\nResults saved to {csv_path}")

    # ── 8. Plot cumulative returns ───────────────────────────────────────────
    cum_rp = (1 + rp_returns).cumprod()
    cum_bm = (1 + bm_returns).cumprod()
    cum_spy = (1 + market_returns).cumprod()

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(cum_rp.index, cum_rp.values, label='Risk Parity (RP)', linewidth=2, color='steelblue')
    ax.plot(cum_bm.index, cum_bm.values, label='50/50 Benchmark', linewidth=2,
            color='darkorange', linestyle='--')
    ax.plot(cum_spy.index, cum_spy.values, label='SPY (Market)', linewidth=1.5,
            color='gray', linestyle=':')
    ax.set_title('Exp 1: Static Two-Asset RP vs 50/50 Benchmark\nCumulative Returns (2019–2022)',
                 fontsize=13)
    ax.set_xlabel('Date')
    ax.set_ylabel('Cumulative Return (Base = 1)')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plot_path = os.path.join(RESULTS_DIR, 'exp1_cumulative_returns.png')
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Plot saved to {plot_path}")

    return {
        'rp_weights': rp_info['weights'],
        'rp_metrics': rp_metrics,
        'bm_metrics': bm_metrics,
        'rp_returns': rp_returns,
        'bm_returns': bm_returns,
    }


if __name__ == '__main__':
    run_exp1()
