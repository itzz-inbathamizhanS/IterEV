"""
Experiment Runner — Executes all research experiments.

Usage:
    cd Backend
    python -m experiments.runner [--experiment NAME] [--quick]

Experiments:
    baseline_comparison     — Compare 4 methods across standard scenario
    soc_sensitivity         — FMR vs SOC sweep
    soh_sensitivity         — FMR vs SOH sweep
    temperature_sensitivity — FMR vs temperature sweep
    demand_sensitivity      — FMR vs demand level sweep
    charging_sensitivity    — FMR vs charging availability sweep
    horizon_sensitivity     — FMR vs planning horizon sweep
    uncertainty_sensitivity — FMR vs uncertainty level sweep
    ablation                — Component ablation study
    calibration             — FMR calibration / reliability assessment
    mc_convergence          — Monte Carlo convergence analysis

    all                     — Run everything

Outputs:
    experiments/results/*.csv
    experiments/results/*.json (metadata)
"""

import sys
import os
import json
import time
import argparse
from pathlib import Path
from datetime import datetime

# Add parent to path for module imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from experiments.config import (
    ExperimentConfig,
    SOC_VALUES,
    SOH_VALUES,
    TEMPERATURE_VALUES,
    DEMAND_LEVELS,
    CHARGING_AVAILABILITIES,
    PLANNING_HORIZONS,
    UNCERTAINTY_LEVELS,
    MC_SAMPLE_SIZES,
)
from experiments.baselines import run_baseline, METHODS
from experiments.metrics import compute_metrics

RESULTS_DIR = Path(__file__).resolve().parent / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def _save_results(df: pd.DataFrame, name: str, config_info: dict):
    """Save CSV results and JSON metadata."""
    csv_path = RESULTS_DIR / f"{name}.csv"
    df.to_csv(csv_path, index=False)

    meta = {
        "experiment": name,
        "timestamp": datetime.now().isoformat(),
        "config": config_info,
        "rows": len(df),
        "columns": list(df.columns),
    }
    meta_path = RESULTS_DIR / f"{name}_metadata.json"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2, default=str)

    print(f"  Saved: {csv_path.name} ({len(df)} rows)")


def run_baseline_comparison(quick: bool = False):
    """Experiment 1: Compare all 4 methods on the standard scenario."""
    print("\n=== Experiment 1: Baseline Comparison ===")
    config = ExperimentConfig(
        name="baseline_comparison",
        scenario_count=1000 if quick else 5000,
    )

    rows = []
    for method in METHODS:
        print(f"  Running {method}...", end=" ", flush=True)
        result = run_baseline(method, config)
        metrics = compute_metrics(result)
        metrics["method"] = method
        metrics["route_name"] = result["route_name"]
        rows.append(metrics)
        print(f"FMR={result['fmr']:.2f}%, time={result['computation_time_s']:.2f}s")

    df = pd.DataFrame(rows)
    _save_results(df, "baseline_comparison", config.to_dict())
    return df


def run_sensitivity(
    param_name: str,
    param_values: list,
    config_field: str,
    quick: bool = False,
):
    """Generic sensitivity analysis runner."""
    print(f"\n=== Sensitivity: {param_name} ===")
    config = ExperimentConfig(
        name=f"{param_name}_sensitivity",
        scenario_count=500 if quick else 5000,
    )

    rows = []
    for val in param_values:
        setattr(config, config_field, val)
        for method in METHODS:
            result = run_baseline(method, config)
            metrics = compute_metrics(result)
            metrics["method"] = method
            metrics[param_name] = val
            rows.append(metrics)
        print(f"  {param_name}={val}: done")

    df = pd.DataFrame(rows)
    _save_results(df, f"{param_name}_sensitivity", config.to_dict())
    return df


def run_soc_sensitivity(quick: bool = False):
    """Experiment 2: FMR vs SOC."""
    return run_sensitivity("soc", SOC_VALUES, "soc_initial", quick)


def run_soh_sensitivity(quick: bool = False):
    """Experiment 3: FMR vs SOH."""
    return run_sensitivity("soh", SOH_VALUES, "soh", quick)


def run_temperature_sensitivity(quick: bool = False):
    """Experiment 4: FMR vs temperature."""
    return run_sensitivity("temperature", TEMPERATURE_VALUES, "temperature", quick)


def run_demand_sensitivity(quick: bool = False):
    """Experiment 5: FMR vs future demand."""
    return run_sensitivity("demand", DEMAND_LEVELS, "demand", quick)


def run_charging_sensitivity(quick: bool = False):
    """Experiment 6: FMR vs charging availability."""
    return run_sensitivity("charging_availability", CHARGING_AVAILABILITIES, "charging_availability", quick)


def run_horizon_sensitivity(quick: bool = False):
    """Experiment 7: FMR vs planning horizon."""
    return run_sensitivity("planning_horizon", PLANNING_HORIZONS, "planning_horizon", quick)


def run_uncertainty_sensitivity(quick: bool = False):
    """Experiment 8: FMR vs uncertainty level."""
    return run_sensitivity("uncertainty", UNCERTAINTY_LEVELS, "uncertainty", quick)


def run_ablation(quick: bool = False):
    """
    Experiment 9: Ablation study.

    Compare full IterEV against variants with components removed:
      - Full IterEV (all components)
      - Without future risk (mu_fmr = 0)
      - Without battery consequence (lambda_battery = 0)
      - Without uncertainty (uncertainty = "Low", charging_availability = 1.0)
      - Without charging uncertainty (charging_availability = 1.0)
      - Without demand uncertainty (demand = "Medium", fixed)
      - Without SOH (soh = 100, no degradation effect)
    """
    print("\n=== Experiment 9: Ablation Study ===")
    base = ExperimentConfig(
        name="ablation",
        scenario_count=500 if quick else 5000,
    )

    variants = {
        "Full IterEV": {},
        "No Future Risk": {"mu_fmr": 0.0},
        "No Battery Term": {"lambda_battery": 0.0},
        "No Uncertainty": {"uncertainty": "Low", "charging_availability": 1.0},
        "No Charging Uncertainty": {"charging_availability": 1.0},
        "No Demand Variation": {"demand": "Medium"},
        "No SOH Effect": {"soh": 100.0},
    }

    rows = []
    for variant_name, overrides in variants.items():
        config = ExperimentConfig(**{**base.to_dict(), **overrides, "name": variant_name})
        result = run_baseline("ITEREV", config)
        metrics = compute_metrics(result)
        metrics["variant"] = variant_name
        metrics["route_name"] = result["route_name"]
        rows.append(metrics)
        print(f"  {variant_name}: FMR={result['fmr']:.2f}%")

    df = pd.DataFrame(rows)
    _save_results(df, "ablation", base.to_dict())
    return df


def run_calibration(quick: bool = False):
    """
    Experiment 10: Risk calibration.

    Compare predicted FMR against empirical failure frequency from
    independent simulation runs.

    Method:
      1. For a range of SOC values, compute predicted FMR
      2. For each SOC, run N independent simulations to observe actual failure
      3. Compare predicted vs observed
    """
    print("\n=== Experiment 10: Calibration ===")
    n_sims = 20 if quick else 100
    config = ExperimentConfig(
        name="calibration",
        scenario_count=500 if quick else 2000,
    )

    rows = []
    for soc in SOC_VALUES:
        config.soc_initial = soc

        # Predicted FMR
        result = run_baseline("ITEREV", config)
        predicted_fmr = result["fmr"]

        # Observed failure: run N independent experiments with different seeds
        failures = 0
        for trial in range(n_sims):
            trial_config = ExperimentConfig(
                **{**config.to_dict(),
                   "random_seed": 1000 + trial,
                   "scenario_count": 200 if quick else 1000}
            )
            trial_result = run_baseline("ITEREV", trial_config)
            # Consider it a "failure" if FMR > epsilon (constraint violated)
            if trial_result["fmr"] / 100.0 > config.epsilon_fmr:
                failures += 1

        observed_failure_rate = failures / n_sims * 100.0
        calibration_error = abs(predicted_fmr - observed_failure_rate)

        rows.append({
            "soc": soc,
            "predicted_fmr": round(predicted_fmr, 2),
            "observed_failure_rate": round(observed_failure_rate, 2),
            "calibration_error": round(calibration_error, 2),
            "n_simulations": n_sims,
        })
        print(f"  SOC={soc}: predicted={predicted_fmr:.2f}%, observed={observed_failure_rate:.2f}%")

    df = pd.DataFrame(rows)
    _save_results(df, "calibration", config.to_dict())
    return df


def run_mc_convergence(quick: bool = False):
    """
    Experiment 11: Monte Carlo convergence.

    Verify FMR estimate stability across different sample sizes.
    """
    print("\n=== Experiment 11: Monte Carlo Convergence ===")
    config = ExperimentConfig(name="mc_convergence")

    sample_sizes = [100, 500, 1000] if quick else MC_SAMPLE_SIZES

    rows = []
    for n in sample_sizes:
        config.scenario_count = n

        # Run multiple times with different seeds to measure variance
        fmr_values = []
        times = []
        for trial in range(5 if quick else 10):
            config.random_seed = 42 + trial
            result = run_baseline("ITEREV", config)
            fmr_values.append(result["fmr"])
            times.append(result["computation_time_s"])

        rows.append({
            "sample_size": n,
            "fmr_mean": round(float(np.mean(fmr_values)), 4),
            "fmr_std": round(float(np.std(fmr_values)), 4),
            "fmr_min": round(float(np.min(fmr_values)), 4),
            "fmr_max": round(float(np.max(fmr_values)), 4),
            "runtime_mean_s": round(float(np.mean(times)), 4),
            "runtime_std_s": round(float(np.std(times)), 4),
        })
        print(f"  N={n}: FMR={np.mean(fmr_values):.4f}% ± {np.std(fmr_values):.4f}%, "
              f"time={np.mean(times):.3f}s")

    df = pd.DataFrame(rows)
    _save_results(df, "monte_carlo_convergence", config.to_dict())
    return df


# ─── Experiment Registry ───────────────────────────────────────────────────

EXPERIMENTS = {
    "baseline_comparison": run_baseline_comparison,
    "soc_sensitivity": run_soc_sensitivity,
    "soh_sensitivity": run_soh_sensitivity,
    "temperature_sensitivity": run_temperature_sensitivity,
    "demand_sensitivity": run_demand_sensitivity,
    "charging_sensitivity": run_charging_sensitivity,
    "horizon_sensitivity": run_horizon_sensitivity,
    "uncertainty_sensitivity": run_uncertainty_sensitivity,
    "ablation": run_ablation,
    "calibration": run_calibration,
    "mc_convergence": run_mc_convergence,
}


def run_all(quick: bool = False):
    """Run all experiments."""
    print(f"\n{'='*60}")
    print(f"IterEV Research Experiments")
    print(f"Mode: {'QUICK' if quick else 'FULL'}")
    print(f"Time: {datetime.now().isoformat()}")
    print(f"{'='*60}")

    t_start = time.perf_counter()
    for name, fn in EXPERIMENTS.items():
        fn(quick=quick)
    t_total = time.perf_counter() - t_start

    print(f"\n{'='*60}")
    print(f"All experiments complete in {t_total:.1f}s")
    print(f"Results: {RESULTS_DIR}")
    print(f"{'='*60}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IterEV Experiment Runner")
    parser.add_argument("--experiment", "-e", default="all",
                       choices=list(EXPERIMENTS.keys()) + ["all"],
                       help="Which experiment to run")
    parser.add_argument("--quick", "-q", action="store_true",
                       help="Quick mode: fewer scenarios for fast iteration")
    args = parser.parse_args()

    if args.experiment == "all":
        run_all(quick=args.quick)
    else:
        EXPERIMENTS[args.experiment](quick=args.quick)
