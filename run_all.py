"""
run_all.py — Execute all four Risk Parity experiments sequentially.

Experiments:
  1. Static two-asset RP vs 50/50 benchmark (S&P 500 & AGG)
  2. Annually rebalanced two-asset RP vs 50/50 benchmark
  3. Static five-asset ERC RP vs equal-weight benchmark (ACWI, TLT, DBC, RWR, TIP)
  4. Annually rebalanced five-asset ERC RP vs equal-weight benchmark

All results (CSVs and plots) are written to results/.
"""

import sys
import os
import time

sys.path.insert(0, '/workspace/project')


def run_all() -> None:
    """Run all four experiments and report elapsed time."""
    from exp.exp_1_static_two_asset import run_exp1
    from exp.exp_2_rebalanced_two_asset import run_exp2
    from exp.exp_3_static_five_asset import run_exp3
    from exp.exp_4_rebalanced_five_asset import run_exp4

    experiments = [
        ("Exp 1 – Static Two-Asset RP vs 50/50", run_exp1),
        ("Exp 2 – Rebalanced Two-Asset RP vs 50/50", run_exp2),
        ("Exp 3 – Static Five-Asset ERC RP vs EW", run_exp3),
        ("Exp 4 – Rebalanced Five-Asset ERC RP vs EW", run_exp4),
    ]

    total_start = time.time()
    results = {}

    for name, fn in experiments:
        print(f"\n{'#' * 70}")
        print(f"# {name}")
        print(f"{'#' * 70}")
        t0 = time.time()
        try:
            res = fn()
            elapsed = time.time() - t0
            print(f"\n✓ {name} completed in {elapsed:.1f}s")
            results[name] = res
        except Exception as exc:
            elapsed = time.time() - t0
            print(f"\n✗ {name} FAILED after {elapsed:.1f}s: {exc}")
            raise

    total_elapsed = time.time() - total_start
    print(f"\n{'=' * 70}")
    print(f"All experiments completed in {total_elapsed:.1f}s")
    print(f"Results saved to: /workspace/project/results/")
    print(f"{'=' * 70}")
    return results


if __name__ == '__main__':
    run_all()
