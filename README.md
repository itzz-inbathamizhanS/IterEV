# IterEV — Future-Mobility-Aware EV Decision System

> IterEV evaluates present EV routing and charging decisions according to both immediate mobility cost and their probabilistic impact on future mobility feasibility under uncertainty in energy consumption, battery state, future demand, environmental conditions, and charging availability.

## Overview

IterEV bridges the gap between single-trip routing and long-term battery capability management through **Future Mobility Risk (FMR)** — the estimated probability that future mobility requirements cannot be satisfied after taking the current decision.

### Core Engines

| Engine | Module | Function |
|--------|--------|----------|
| Energy | `engines/energy_engine.py` | Route-specific energy consumption under traffic, temperature, SOH |
| Battery | `engines/battery_engine.py` | SOC/SOH state transitions with degradation model |
| Uncertainty | `engines/uncertainty_engine.py` | Monte Carlo scenario sampling (energy, traffic, temperature, demand, charging) |
| Feasibility | `engines/feasibility_engine.py` | Probabilistic FMR via scenario-based simulation |
| Charging | `engines/charging_engine.py` | Charging as explicit state transition |
| Optimizer | `engines/optimizer.py` | Risk-constrained multi-objective optimization |
| Explanation | `engines/explanation_engine.py` | Human-readable decision reasoning |

### Mathematical Formulation

**Optimization objective:**
```
min J(a) = CurrentCost(a) + λ·BatteryConsequence(a) + μ·FMR(a)
subject to: FMR(a) ≤ ε
```

**Probabilistic FMR:**
```
FMR(a) = number_of_failed_scenarios / number_of_total_scenarios
```

where each scenario samples uncertain future conditions (energy, traffic, temperature, demand, charging availability) and propagates battery state through the planning horizon.

## Project Structure

```
Backend/
├── main.py                      # FastAPI application
├── api/
│   ├── consumer.py              # Consumer routing endpoints
│   ├── simulation.py            # Simulation/comparison endpoints
│   └── fleet.py                 # Fleet endpoints (demo)
├── engines/
│   ├── energy_engine.py         # Energy prediction
│   ├── battery_engine.py        # Battery state + degradation
│   ├── uncertainty_engine.py    # Scenario sampling
│   ├── feasibility_engine.py    # Probabilistic FMR
│   ├── charging_engine.py       # Charging model
│   ├── optimizer.py             # Risk-constrained optimization
│   └── explanation_engine.py    # Decision explanation
├── models/
│   ├── constants.py             # All physical constants (centralized)
│   └── schemas.py               # Pydantic data models
├── experiments/
│   ├── config.py                # Experiment configurations
│   ├── scenarios.py             # Standard trip scenarios
│   ├── baselines.py             # Baseline algorithms (4 methods)
│   ├── metrics.py               # Centralized metric computation
│   ├── runner.py                # Experiment runner (CLI)
│   ├── visualize.py             # Figure generation
│   └── results/                 # CSV/JSON results + figures/
├── tests/
│   └── test_research.py         # 52 pytest tests
└── requirements.txt

Frontend/                        # React + Vite + TanStack Router
├── src/
│   ├── components/future-mobility/
│   ├── services/                # API services with local fallbacks
│   ├── hooks/                   # State management
│   └── routes/                  # Page routes
```

## Getting Started

### Backend

```bash
cd Backend
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd Frontend
npm install
npm run dev
```

### Run Tests

```bash
cd Backend
python -m pytest tests/ -v
```

### Run Experiments

```bash
cd Backend

# All experiments (quick mode — ~2 seconds)
python -m experiments.runner --quick

# All experiments (full mode — ~60 seconds with 5000 scenarios)
python -m experiments.runner

# Single experiment
python -m experiments.runner -e baseline_comparison
python -m experiments.runner -e soc_sensitivity
python -m experiments.runner -e ablation
python -m experiments.runner -e calibration
python -m experiments.runner -e mc_convergence

# Generate research figures
python -m experiments.visualize
```

### Experiment Outputs

Results are saved to `Backend/experiments/results/`:

| File | Description |
|------|-------------|
| `baseline_comparison.csv` | 4-method comparison |
| `soc_sensitivity.csv` | FMR vs SOC sweep (20–90%) |
| `soh_sensitivity.csv` | FMR vs SOH sweep (70–100%) |
| `temperature_sensitivity.csv` | FMR vs temperature (15–45°C) |
| `demand_sensitivity.csv` | FMR vs demand level |
| `charging_availability_sensitivity.csv` | FMR vs charger availability |
| `planning_horizon_sensitivity.csv` | FMR vs horizon (1–14 days) |
| `uncertainty_sensitivity.csv` | FMR vs uncertainty level |
| `ablation.csv` | Component ablation study |
| `calibration.csv` | FMR calibration assessment |
| `monte_carlo_convergence.csv` | MC convergence analysis |

Each CSV has a corresponding `_metadata.json` with experiment configuration.

## Reproducibility

Every experiment supports a `random_seed` parameter (default: 42). The same input + seed + model parameters + scenario count will produce identical results.

Seeds are stored in experiment output metadata.

## Research Assumptions & Limitations

1. **Route profiles are scenario-specific** — Coimbatore→Ooty research scenario, not real-time routing
2. **Battery degradation is a reduced-order proxy model** — not an electrochemical model
3. **Overnight SOC loss is aggregate standby consumption** (5%) — not pure self-discharge
4. **Charging model is energy-balance, not CC/CV curve** — suitable for planning, not real-time
5. **Fleet module is prototype / future work** — demo data only
6. **No real-time traffic data integration** — uses configurable distributions
7. **Uncertainty distributions use documented but not vehicle-specific parameters**

## License

MIT License — see [LICENSE](LICENSE) for details.
