"""
Visualization — Generate paper-ready figures from experiment results.

Usage:
    cd Backend
    python -m experiments.visualize

Reads CSV results from experiments/results/ and produces figures
in experiments/results/figures/.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np

RESULTS_DIR = Path(__file__).resolve().parent / "results"
FIGURES_DIR = RESULTS_DIR / "figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

# Consistent style
plt.rcParams.update({
    "figure.figsize": (8, 5),
    "font.size": 11,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "axes.spines.top": False,
    "axes.spines.right": False,
})

METHOD_COLORS = {
    "FASTEST": "#e74c3c",
    "ENERGY_MIN": "#3498db",
    "BATTERY_AWARE": "#2ecc71",
    "ITEREV": "#9b59b6",
}


def _load(name: str) -> pd.DataFrame | None:
    path = RESULTS_DIR / f"{name}.csv"
    if path.exists():
        return pd.read_csv(path)
    print(f"  Skipping {name}: {path.name} not found")
    return None


def plot_baseline_comparison():
    for scenario in ["stress_baseline", "constraint_feasible"]:
        df = _load(f"baseline_comparison_{scenario}")
        if df is None:
            continue
        fig, axes = plt.subplots(1, 4, figsize=(16, 4.5))
        metrics = [("travel_time", "Travel Time (min)"), ("energy_consumption", "Energy (kWh)"),
                   ("fmr", "FMR (%)"), ("future_success_rate", "Future Success (%)")]
        for ax, (col, label) in zip(axes, metrics):
            colors = [METHOD_COLORS.get(m, "#666") for m in df["method"]]
            ax.bar(df["method"], df[col], color=colors, edgecolor="white", linewidth=0.5)
            ax.set_ylabel(label)
            ax.tick_params(axis="x", rotation=25)
        fig.suptitle(f"Baseline Method Comparison - {scenario.upper()}", fontweight="bold", y=1.02)
        fig.tight_layout()
        fig.savefig(FIGURES_DIR / f"baseline_comparison_{scenario}.png", dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"  ✓ baseline_comparison_{scenario}.png")


def plot_sensitivity(name: str, x_col: str, x_label: str, title: str):
    df = _load(f"{name}_sensitivity")
    if df is None:
        return
    fig, ax = plt.subplots(figsize=(8, 5))
    for method in df["method"].unique():
        subset = df[df["method"] == method]
        color = METHOD_COLORS.get(method, "#666")
        ax.plot(subset[x_col], subset["fmr"], "o-", label=method, color=color, markersize=5)
    ax.set_xlabel(x_label)
    ax.set_ylabel("FMR (%)")
    ax.set_title(title, fontweight="bold")
    ax.legend(framealpha=0.9)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / f"{name}_sensitivity.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓ {name}_sensitivity.png")


def plot_ablation():
    df = _load("ablation")
    if df is None:
        return
    fig, ax = plt.subplots(figsize=(10, 5))
    colors = plt.cm.Set2(np.linspace(0, 1, len(df)))
    bars = ax.barh(df["variant"], df["fmr"], color=colors, edgecolor="white")
    ax.set_xlabel("FMR (%)")
    ax.set_title("Ablation Study — Component Contribution to FMR", fontweight="bold")
    for bar, val in zip(bars, df["fmr"]):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
                f"{val:.1f}%", va="center", fontsize=9)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "ablation.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  ✓ ablation.png")


def plot_independent_replication():
    df = _load("independent_replication")
    if df is None:
        return
    fig, ax = plt.subplots(figsize=(7, 6))
    max_val = max(df["predicted_fmr"].max(), df["observed_failure_rate"].max(), 10)
    ax.plot([0, max_val], [0, max_val], "k--", alpha=0.4, label="Perfect replication")
    ax.scatter(df["predicted_fmr"], df["observed_failure_rate"],
               c="#9b59b6", s=80, zorder=5, edgecolors="white")
    for _, row in df.iterrows():
        ax.annotate(f'SOC={int(row["soc"])}', (row["predicted_fmr"], row["observed_failure_rate"]),
                    textcoords="offset points", xytext=(5, 5), fontsize=8)
    ax.set_xlabel("Predicted FMR (%)")
    ax.set_ylabel("Observed Failure Rate (%)")
    ax.set_title("FMR Independent Replication / Reliability", fontweight="bold")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "independent_replication.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  ✓ independent_replication.png")


def plot_mc_convergence():
    df = _load("monte_carlo_convergence")
    if df is None:
        return
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    ax1.errorbar(df["N"], df["fmr"], yerr=df["ci_width"] / 2,
                 fmt="o-", color="#9b59b6", capsize=4, markersize=6)
    ax1.set_xlabel("Number of Scenarios (N)")
    ax1.set_ylabel("FMR Estimate (%)")
    ax1.set_title("FMR Convergence", fontweight="bold")
    ax1.set_xscale("log")

    ax2.plot(df["N"], df["computation_time_s"], "s-", color="#e74c3c", markersize=6)
    ax2.set_xlabel("Number of Scenarios (N)")
    ax2.set_ylabel("Runtime (seconds)")
    ax2.set_title("Computation Time", fontweight="bold")
    ax2.set_xscale("log")

    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "mc_convergence.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  ✓ mc_convergence.png")


def generate_all():
    print("\nGenerating research figures...")
    plot_baseline_comparison()

    plot_sensitivity("soc", "soc", "State of Charge (%)", "FMR vs SOC")
    plot_sensitivity("soh", "soh", "State of Health (%)", "FMR vs SOH")
    plot_sensitivity("temperature", "temperature", "Temperature (°C)", "FMR vs Temperature")
    plot_sensitivity("charging_availability", "charging_availability",
                     "Charging Availability", "FMR vs Charging Availability")
    plot_sensitivity("planning_horizon", "planning_horizon",
                     "Planning Horizon (days)", "FMR vs Planning Horizon")

    # Demand and uncertainty have string x-axis
    df_demand = _load("demand_sensitivity")
    if df_demand is not None:
        fig, ax = plt.subplots(figsize=(8, 5))
        for method in df_demand["method"].unique():
            subset = df_demand[df_demand["method"] == method]
            color = METHOD_COLORS.get(method, "#666")
            ax.plot(range(len(subset)), subset["fmr"], "o-", label=method, color=color)
        ax.set_xticks(range(len(df_demand["demand"].unique())))
        ax.set_xticklabels(df_demand["demand"].unique())
        ax.set_xlabel("Demand Level")
        ax.set_ylabel("FMR (%)")
        ax.set_title("FMR vs Future Demand", fontweight="bold")
        ax.legend()
        fig.tight_layout()
        fig.savefig(FIGURES_DIR / "demand_sensitivity.png", dpi=150, bbox_inches="tight")
        plt.close(fig)
        print("  ✓ demand_sensitivity.png")

    df_unc = _load("uncertainty_sensitivity")
    if df_unc is not None:
        fig, ax = plt.subplots(figsize=(8, 5))
        for method in df_unc["method"].unique():
            subset = df_unc[df_unc["method"] == method]
            color = METHOD_COLORS.get(method, "#666")
            ax.plot(range(len(subset)), subset["fmr"], "o-", label=method, color=color)
        ax.set_xticks(range(len(df_unc["uncertainty"].unique())))
        ax.set_xticklabels(df_unc["uncertainty"].unique())
        ax.set_xlabel("Uncertainty Level")
        ax.set_ylabel("FMR (%)")
        ax.set_title("FMR vs Uncertainty", fontweight="bold")
        ax.legend()
        fig.tight_layout()
        fig.savefig(FIGURES_DIR / "uncertainty_sensitivity.png", dpi=150, bbox_inches="tight")
        plt.close(fig)
        print("  ✓ uncertainty_sensitivity.png")

    plot_ablation()
    plot_independent_replication()
    plot_mc_convergence()

    print(f"\nFigures saved to: {FIGURES_DIR}")


if __name__ == "__main__":
    generate_all()
