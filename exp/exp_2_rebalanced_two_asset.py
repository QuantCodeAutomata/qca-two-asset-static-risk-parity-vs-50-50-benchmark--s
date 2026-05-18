"""
Experiment 2: Annually Rebalanced Two-Asset Risk Parity vs 50/50 Benchmark

Replicates the two-asset annually rebalanced Risk Parity vs 50/50 benchmark.
Assets: SPY (S&P 500 proxy) and AGG (US Aggregate Bond ETF).
For each year in {2019, 2020, 2021, 2022}, uses 10-year rolling window ending
Dec of the prior year to compute RP weights.
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
    build_annual_rp_portfolios,
    apply_annual_weights,
    compute_portfolio_returns,
    compute_benchmark_weights_two_asset,
)
from src.metrics import compute_portfolio_metrics

RESULTS_DIR = '/workspace/project/results'
TICKERS = ['SPY', 'AGG']
START_DATE = '2008-12-01'
END_DATE = '2022-12-31'
TEST_YEARS = [2019, 2020, 2021, 2022]
TEST_START = '2019-01'
TEST_END = '2022-12'

THESIS_TARGETS = {
    'RP':   {'mean': 0.001979, 'std': 0.0201, 'covariance': 0.0009, 'beta': 0.2870,
             'downside_risk': 0.0150, 'sharpe': 0.0987, 'sortino': 0.1319, 'treynor': 0.0069},
    '50/50': {'mean': 0.003522, 'std': 0.0322, 'covariance': 0.0018, 'beta': 0.5587,
              'downside_risk': 0.0199, 'sharpe': 0.1630, 'sortino': 0.2636, 'treynor': 0.0094},
}


def run_exp2() -> dict:
    """Run annually rebalanced two-asset Risk Parity experiment. Returns results dict."""
    os.makedirs(RESULTS_DIR, exist_ok=True)

    # ── 1. Load and preprocess data ──────────────────────────────────────────
    print("=" * 70)
    print("Experiment 2: Annually Rebalanced Two-Asset Risk Parity vs 50/50")
    print("=" * 70)
    print(f"\nLoading data for {TICKERS} from {START_DATE} to {END_DATE}...")
    prices = download_prices(TICKERS, START_DATE, END_DATE)
    prices_aligned = align_month_end(prices)
    returns = compute_returns(prices_aligned)
    print(f"Total monthly returns: {len(returns)} observations")

    # ── 2. Descriptive stats on full estimation base (2009-01 to 2018-12) ───
    est_base = get_estimation_window(returns, '2009-01', '2018-12')
    desc_stats = compute_descriptive_stats(est_base)
    print("\nDescriptive Statistics (Base Estimation Window 2009-01 to 2018-12):")
    print(desc_stats.to_string(float_format=lambda x: f"{x:.6f}"))

    # ── 3. Build annually rebalanced RP portfolios ───────────────────────────
    annual_weights = build_annual_rp_portfolios(returns, 'SPY', 'AGG', TEST_YEARS)

    print("\nAnnual RP Weights:")
    print(f"{'Year':<8} {'w_SPY':>10} {'w_AGG':>10} {'sigma_SPY':>12} {'sigma_AGG':>12}")
    print("-" * 54)
    for y in TEST_YEARS:
        info = annual_weights[y]
        print(f"{y:<8} {info['w_equity']:>10.4f} {info['w_bond']:>10.4f} "
              f"{info['sigma_equity']:>12.6f} {info['sigma_bond']:>12.6f}")

    # ── 4. Testing window ────────────────────────────────────────────────────
    test_returns = get_testing_window(returns, TEST_START, TEST_END)
    print(f"\nTesting window: {TEST_START} to {TEST_END} ({len(test_returns)} months)")

    rp_returns = apply_annual_weights(test_returns, annual_weights)
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
    csv_path = os.path.join(RESULTS_DIR, 'exp2_results.csv')
    results_df.to_csv(csv_path)
    print(f"\nResults saved to {csv_path}")

    # ── 8. Plot cumulative returns ───────────────────────────────────────────
    cum_rp = (1 + rp_returns).cumprod()
    cum_bm = (1 + bm_returns).cumprod()
    cum_spy = (1 + market_returns).cumprod()

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(cum_rp.index, cum_rp.values, label='Risk Parity (RP, Annual Rebal.)',
            linewidth=2, color='steelblue')
    ax.plot(cum_bm.index, cum_bm.values, label='50/50 Benchmark',
            linewidth=2, color='darkorange', linestyle='--')
    ax.plot(cum_spy.index, cum_spy.values, label='SPY (Market)',
            linewidth=1.5, color='gray', linestyle=':')
    ax.set_title('Exp 2: Annually Rebalanced Two-Asset RP vs 50/50 Benchmark\n'
                 'Cumulative Returns (2019–2022)', fontsize=13)
    ax.set_xlabel('Date')
    ax.set_ylabel('Cumulative Return (Base = 1)')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plot_path = os.path.join(RESULTS_DIR, 'exp2_cumulative_returns.png')
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Cumulative returns plot saved to {plot_path}")

    # ── 9. Plot annual weights bar chart ─────────────────────────────────────
    years = TEST_YEARS
    w_spy_vals = [annual_weights[y]['w_equity'] * 100 for y in years]
    w_agg_vals = [annual_weights[y]['w_bond'] * 100 for y in years]

    x = np.arange(len(years))
    width = 0.35

    fig, ax = plt.subplots(figsize=(8, 5))
    bars1 = ax.bar(x - width / 2, w_spy_vals, width, label='SPY (Equity)', color='steelblue')
    bars2 = ax.bar(x + width / 2, w_agg_vals, width, label='AGG (Bond)', color='darkorange')
    ax.set_title('Exp 2: Annual RP Weights (SPY vs AGG)', fontsize=13)
    ax.set_xlabel('Year')
    ax.set_ylabel('Weight (%)')
    ax.set_xticks(x)
    ax.set_xticklabels([str(y) for y in years])
    ax.legend()
    ax.grid(True, axis='y', alpha=0.3)
    for bar in bars1:
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                f'{bar.get_height():.1f}%', ha='center', va='bottom', fontsize=9)
    for bar in bars2:
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                f'{bar.get_height():.1f}%', ha='center', va='bottom', fontsize=9)
    plt.tight_layout()
    weights_plot_path = os.path.join(RESULTS_DIR, 'exp2_annual_weights.png')
    plt.savefig(weights_plot_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Annual weights plot saved to {weights_plot_path}")

    return {
        'annual_weights': annual_weights,
        'rp_metrics': rp_metrics,
        'bm_metrics': bm_metrics,
        'rp_returns': rp_returns,
        'bm_returns': bm_returns,
    }


if __name__ == '__main__':
    run_exp2()
