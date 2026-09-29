"""
Experiment Runner — CLI for running all IterEV research experiments.

Usage:
    python -m experiments.runner              # All experiments (full)
    python -m experiments.runner --quick      # All experiments (fast)
    python -m experiments.runner -e ablation  # Single experiment

All results are saved to experiments/results/ as CSV + metadata JSON.
"""

import json
import time
import argparse
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

from experiments.config import (
    ExperimentConfig,
    SOC_VALUES, SOH_VALUES, TEMPERATURE_VALUES,
    DEMAND_LEVELS, CHARGING_AVAILABILITIES, PLANNING_HORIZONS,
    UNCERTAINTY_LEVELS, MC_SAMPLE_SIZES,
)
from experiments.baselines import (
    run_baseline, run_independent_validation, METHODS,
)
from experiments.metrics import compute_metrics
from engines.uncertainty_engine import AblationFlags

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)


def _save_results(df: pd.DataFrame, name: str, metadata: dict):
    """Save experiment results as CSV + metadata JSON."""
    csv_path = RESULTS_DIR / f"{name}.csv"
    df.to_csv(csv_path, index=False)

    meta_path = RESULTS_DIR / f"{name}_metadata.json"
    metadata.update({
        "timestamp": datetime.now().isoformat(),
        "rows": len(df),
        "columns": list(df.columns),
        "model_version": "2.0.0-research",
    })
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2, default=str)

    print(f"  Saved: {name}.csv ({len(df)} rows)")


def run_baseline_comparison(quick: bool = False):
    """Experiment 1: Compare all 4 methods on two distinct scenarios."""
    print("\n=== Experiment 1: Baseline Comparison ===")
    
    scenarios = {
        "STRESS_BASELINE": ExperimentConfig(
            name="STRESS_BASELINE",
            scenario_count=500 if quick else 5000,
            # Inherits tough defaults: soc=80, soh=100, demand=Medium, charging=1.0, uncertainty=Medium
        ),
        "CONSTRAINT_FEASIBLE": ExperimentConfig(
            name="CONSTRAINT_FEASIBLE",
            scenario_count=500 if quick else 5000,
            soc_initial=100,         # Max SOC
            soh=100,                 # Perfect SOH
            demand="Low",            # Lower future demand
            charging_availability=1.0,
            uncertainty="Low",       # Less noise
            planning_horizon=3,      # Shorter horizon
        )
    }

    for scenario_name, config in scenarios.items():
        print(f"\n  -- Scenario: {scenario_name} --")
        rows = []
        for method in METHODS:
            result = run_baseline(method, config)
            metrics = compute_metrics(result)
            metrics["scenario_type"] = scenario_name
            # The metrics output automatically includes optimizer_status, constraint_relaxed, num_feasible_candidates, selected_route_fmr
            rows.append(metrics)
            print(f"    Running {method}...")
            print(f"      Selected Route FMR: {result['fmr']:.2f}%")
            print(f"      Optimizer Status: {result.get('optimizer_status', 'N/A')}")
            print(f"      Constraint Relaxed: {result.get('constraint_relaxed', 'N/A')}")
            print(f"      Num Feasible Cands: {result.get('num_feasible_candidates', 'N/A')}")
        
        df = pd.DataFrame(rows)
        _save_results(df, f"baseline_comparison_{scenario_name.lower()}", config.to_dict())


def run_sensitivity(param_name: str, values: list, config_key: str, quick: bool = False):
    """Generic sensitivity experiment: sweep one parameter, run all methods."""
    print(f"\n=== Sensitivity: {param_name} ===")
    rows = []
    base = ExperimentConfig(
        name=f"{param_name}_sensitivity",
        scenario_count=500 if quick else 5000,
    )

    for val in values:
        config = ExperimentConfig(**{**base.to_dict(), config_key: val})
        for method in METHODS:
            result = run_baseline(method, config)
            metrics = compute_metrics(result)
            metrics[param_name] = val
            rows.append(metrics)
        print(f"  {param_name}={val}: done")

    df = pd.DataFrame(rows)
    _save_results(df, f"{param_name}_sensitivity", base.to_dict())
    return df


def run_soc_sensitivity(quick: bool = False):
    return run_sensitivity("soc", SOC_VALUES, "soc_initial", quick)

def run_soh_sensitivity(quick: bool = False):
    return run_sensitivity("soh", SOH_VALUES, "soh", quick)

def run_temperature_sensitivity(quick: bool = False):
    return run_sensitivity("temperature", TEMPERATURE_VALUES, "temperature", quick)

def run_demand_sensitivity(quick: bool = False):
    return run_sensitivity("demand", DEMAND_LEVELS, "demand", quick)

def run_charging_sensitivity(quick: bool = False):
    return run_sensitivity("charging_availability", CHARGING_AVAILABILITIES, "charging_availability", quick)

def run_horizon_sensitivity(quick: bool = False):
    return run_sensitivity("planning_horizon", PLANNING_HORIZONS, "planning_horizon", quick)

def run_uncertainty_sensitivity(quick: bool = False):
    return run_sensitivity("uncertainty", UNCERTAINTY_LEVELS, "uncertainty", quick)


def run_ablation(quick: bool = False):
    """
    Experiment 9: Ablation study.

    Each variant EXPLICITLY DISABLES a component via AblationFlags.
    This is NOT the same as reducing uncertainty level or setting SOH=100.
    The flag prevents the stochastic component from being sampled at all.

    All variants use the SAME seed, SAME scenario base, SAME routes.
    Only the intended component changes.
    """
    print("\n=== Experiment 9: Ablation Study ===")
    base_config = ExperimentConfig(
        name="ablation",
        scenario_count=500 if quick else 5000,
    )

    # A0-A6: explicit ablation variants
    variants = {
        "A0: Full IterEV": AblationFlags(),  # All enabled
        "A1: No Future Risk": AblationFlags(use_future_risk=False),
        "A2: No Battery Degradation": AblationFlags(use_battery_degradation=False),
        "A3: No Energy/Env Uncertainty": AblationFlags(
            use_energy_uncertainty=False,
            use_temperature_uncertainty=False,
            use_traffic_uncertainty=False,
        ),
        "A4: No Demand Uncertainty": AblationFlags(use_demand_uncertainty=False),
        "A5: No Charging Uncertainty": AblationFlags(use_charging_uncertainty=False),
        "A6: No Degradation Uncertainty": AblationFlags(use_degradation_uncertainty=False),
    }

    conditions = [
        {"name": "High Stress", "demand": "High", "soc_initial": 50.0, "charging_availability": 0.5},
        {"name": "Moderate", "demand": "Medium", "soc_initial": 80.0, "charging_availability": 0.9}
    ]

    rows = []
    
    for condition in conditions:
        print(f"\n  Condition: {condition['name']}")
        base_fmr = None
        for variant_name, ablation_flags in variants.items():
            config = ExperimentConfig(**{**base_config.to_dict()})
            config.ablation = ablation_flags
            config.demand = condition["demand"]
            config.soc_initial = condition["soc_initial"]
            config.charging_availability = condition["charging_availability"]
            config.name = f"ablation_{condition['name'].lower().replace(' ', '_')}"

            # For "No Future Risk", set mu_fmr=0 so optimizer ignores FMR
            if not ablation_flags.use_future_risk:
                config.mu_fmr = 0.0

            result = run_baseline("ITEREV", config)
            metrics = compute_metrics(result)
            metrics["condition"] = condition["name"]
            metrics["variant"] = variant_name
            metrics["route_name"] = result["route_name"]
            
            if variant_name == "A0: Full IterEV":
                base_fmr = result['fmr']
                print(f"    {variant_name}: FMR={result['fmr']:.2f}%")
            else:
                if abs(result['fmr'] - base_fmr) < 0.01:
                    print(f"    {variant_name}: FMR={result['fmr']:.2f}% (effect not detectable under this scenario)")
                else:
                    print(f"    {variant_name}: FMR={result['fmr']:.2f}%")
                    
            rows.append(metrics)

    df = pd.DataFrame(rows)
    _save_results(df, "ablation", base_config.to_dict())
    return df


def run_independent_replication(quick: bool = False):
    """
    Experiment 10: Independent Monte Carlo Replication.

    CORRECT DESIGN (Bug #4 fix):
      Stage A: Estimate FMR using estimation seed (seed=42, N=5000)
      Stage B: Observe actual failure using INDEPENDENT validation seed
               (seed=4242, N=20000)

    The validation scenarios are NEVER used for FMR estimation.
    The observed failure rate comes from actual simulated future failures,
    NOT from checking if predicted_fmr > epsilon.
    """
    print("\n=== Experiment 10: Independent Monte Carlo Replication ===")
    n_estimation = 500 if quick else 5000
    n_validation = 2000 if quick else 20000

    rows = []
    cases = [
        # Low risk: High SOC, perfect SOH, low demand, full charging
        {"name": "LOW_RISK", "soc": 90, "soh": 100, "demand": "Low", "charging": 1.0},
        # Low-moderate: Good SOC, slight degradation, medium demand
        {"name": "LOW_MODERATE", "soc": 70, "soh": 95, "demand": "Medium", "charging": 0.95},
        # Moderate: Lower SOC, moderate degradation, high demand, limited charging
        {"name": "MODERATE", "soc": 50, "soh": 90, "demand": "High", "charging": 0.50},
        # High risk: Low SOC, bad degradation, very high demand, no charging
        {"name": "HIGH_RISK", "soc": 30, "soh": 80, "demand": "Very High", "charging": 0.10},
    ]

    for case in cases:
        config = ExperimentConfig(
            name=f"replication_{case['name']}",
            scenario_count=n_estimation,
            soc_initial=case["soc"],
            soh=case["soh"],
            demand=case["demand"],
            charging_availability=case["charging"],
            random_seed=42,  # Estimation seed
        )

        # Stage A: Predict FMR with estimation seed
        result = run_baseline("ITEREV", config)
        predicted_fmr = result["fmr"]

        # Stage B: Independent validation with different seed
        val = run_independent_validation(
            "ITEREV", config,
            validation_seed=4242,
            validation_count=n_validation,
        )
        observed_failure = val["observed_failure_rate"]
        rep_error = abs(predicted_fmr - observed_failure)

        rows.append({
            "case": case["name"],
            "soc": case["soc"],
            "soh": case["soh"],
            "demand": case["demand"],
            "charging": case["charging"],
            "predicted_fmr": round(predicted_fmr, 2),
            "observed_failure_rate": round(observed_failure, 2),
            "replication_error": round(rep_error, 2),
            "estimation_scenarios": n_estimation,
            "estimation_seed": 42,
            "validation_scenarios": n_validation,
            "validation_seed": 4242,
            "val_ci_lower": round(val["validation_ci_lower"], 2),
            "val_ci_upper": round(val["validation_ci_upper"], 2),
        })
        print(f"  {case['name']} (SOC={case['soc']}, SOH={case['soh']}, Dem={case['demand']}, Chg={case['charging']}): "
              f"predicted={predicted_fmr:.2f}%, observed={observed_failure:.2f}%, error={rep_error:.2f}pp")

    df = pd.DataFrame(rows)
    _save_results(df, "independent_replication", {"estimation_seed": 42, "validation_seed": 4242,
                                       "estimation_N": n_estimation, "validation_N": n_validation})
    return df


def run_mc_convergence(quick: bool = False):
    """
    Experiment 11: Monte Carlo convergence analysis.
    Measures FMR stability as N increases.
    """
    print("\n=== Experiment 11: Monte Carlo Convergence ===")
    sizes = [100, 500, 1000] if quick else MC_SAMPLE_SIZES

    rows = []
    # To compare against largest-N estimate, we do it in a first pass or track them,
    # but since it's sequential we can just compute it after.
    temp_results = []
    for n in sizes:
        config = ExperimentConfig(
            name="mc_convergence",
            scenario_count=n,
        )
        t0 = time.perf_counter()
        result = run_baseline("ITEREV", config)
        t1 = time.perf_counter()
        temp_results.append((n, result, t1 - t0))

    # Reference is the largest N
    ref_fmr = temp_results[-1][1]["fmr"]
    tolerance = 0.5  # percent

    for n, result, compute_time in temp_results:
        ci_width = result["fmr_ci_upper"] - result["fmr_ci_lower"]
        rel_ci_width = ci_width / result["fmr"] if result["fmr"] > 0 else 0.0
        abs_diff = abs(result["fmr"] - ref_fmr)
        converged = abs_diff < tolerance
        
        # We also need failures. "failed_scenarios" is returned inside SimulationOutput? No, result from run_baseline doesn't have it directly.
        # But we know FMR = failures / N -> failures = FMR / 100 * N
        failures = int(round(result["fmr"] / 100.0 * n))

        rows.append({
            "N": n,
            "fmr": round(result["fmr"], 4),
            "fmr_ci_lower": round(result["fmr_ci_lower"], 4),
            "fmr_ci_upper": round(result["fmr_ci_upper"], 4),
            "absolute_ci_width": round(ci_width, 4),
            "relative_ci_width": round(rel_ci_width, 4),
            "absolute_difference_from_ref": round(abs_diff, 4),
            "converged": converged,
            "failures": failures,
            "computation_time_s": round(compute_time, 3),
        })
        print(f"  N={n}: FMR={result['fmr']:.4f}% +/- {ci_width/2:.4f}%, time={compute_time:.3f}s")

    df = pd.DataFrame(rows)
    _save_results(df, "mc_convergence", {"seed": 42, "sample_sizes": sizes, "tolerance_pct": tolerance})
    return df


# ─── CLI ────────────────────────────────────────────────────────────────────

def run_failure_taxonomy(quick: bool = False):
    print("\n=== Experiment 15: Failure-Mode Taxonomy ===")
    config = ExperimentConfig(
        name="failure_taxonomy",
        scenario_count=1000 if quick else 10000,
        soc_initial=50.0,
        demand="High",
        charging_availability=0.2, # stress to generate failures
    )
    result = run_baseline("ITEREV", config)
    taxonomy = result.get("failure_taxonomy", {})
    
    out_path = RESULTS_DIR / "failure_taxonomy.json"
    with open(out_path, "w") as f:
        json.dump(taxonomy, f, indent=2)
    print(f"  Failure taxonomy saved to {out_path}")
    print(json.dumps(taxonomy, indent=2))
    return taxonomy

EXPERIMENTS = {
    "baseline_comparison": run_baseline_comparison,
    "soc_sensitivity": run_soc_sensitivity,
    "soh_sensitivity": run_soh_sensitivity,
    "temperature_sensitivity": run_temperature_sensitivity,
    "demand_sensitivity": run_demand_sensitivity,
    "charging_availability_sensitivity": run_charging_sensitivity,
    "planning_horizon_sensitivity": run_horizon_sensitivity,
    "uncertainty_sensitivity": run_uncertainty_sensitivity,
    "ablation": run_ablation,
    "independent_replication": run_independent_replication,
    "mc_convergence": run_mc_convergence,
    "failure_taxonomy": run_failure_taxonomy,
}


def main():
    parser = argparse.ArgumentParser(description="IterEV Research Experiments")
    parser.add_argument("--quick", action="store_true", help="Quick mode (fewer scenarios)")
    parser.add_argument("-e", "--experiment", choices=list(EXPERIMENTS.keys()),
                        help="Run a single experiment")
    parser.add_argument("--random-seed", type=int, default=42)
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"IterEV Research Experiments")
    print(f"Mode: {'QUICK' if args.quick else 'FULL'}")
    print(f"Time: {datetime.now().isoformat()}")
    print(f"{'='*60}")

    t_start = time.perf_counter()

    if args.experiment:
        EXPERIMENTS[args.experiment](args.quick)
    else:
        for name, func in EXPERIMENTS.items():
            func(args.quick)

    t_total = time.perf_counter() - t_start
    print(f"\n{'='*60}")
    print(f"All experiments complete in {t_total:.1f}s")
    print(f"Results: {RESULTS_DIR.resolve()}")
    print(f"{'='*60}")

    # 14. Reproducibility Manifest
    manifest = {
        "timestamp": datetime.now().isoformat(),
        "execution_mode": "QUICK" if args.quick else "FULL",
        "random_seed": args.random_seed,
        "experiments_run": list(EXPERIMENTS.keys()) if not args.experiment else [args.experiment],
        "hardware_time_s": round(t_total, 3),
        "dependency_versions": {
            "numpy": np.__version__,
            "pandas": pd.__version__,
        }
    }
    with open(RESULTS_DIR / "reproducibility_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

if __name__ == "__main__":
    main()
