# IterEV — Mathematical Model Documentation

## 1. Energy Model

Energy consumption for route `r` under conditions `(traffic, temperature, SOH)`:

```
E(r) = E_base(r) × f_traffic × f_temperature × f_SOH
```

Where:
- `E_base(r)` — calibrated base energy at standard conditions (kWh)
- `f_traffic = TRAFFIC_FACTORS[traffic]` — {Low: 0.88, Medium: 1.00, High: 1.20}
- `f_temperature = 1.0 + (T - T_baseline) × 0.008`
- `f_SOH = 1.0 + max(0, SOH_baseline - SOH) × 0.002`

**Implementation:** `engines/energy_engine.py::predict_energy()`

## 2. Battery State Transition

### SOC Transition

```
SOC_{t+1} = SOC_t - (E_route / C_usable) × 100
C_usable = C_nominal × (SOH / 100)
```

### Overnight/Standby SOC Loss

```
SOC_{next_day} = SOC_current - DAILY_STANDBY_LOSS_PCT
```

Default: 5% aggregate standby consumption per day (self-discharge + vehicle standby + auxiliary loads).

**Implementation:** `engines/battery_engine.py::compute_soc_after()`, `estimate_tomorrow_soc()`

## 3. Battery Health Degradation

Reduced-order proxy model (NOT electrochemical):

```
ΔSOH = base_rate × throughput_factor × temp_factor × dod_factor × crate_factor × noise
```

Where:
- `throughput_factor = E_throughput / C_usable` — normalized energy throughput
- `temp_factor = 1.0 + 0.06 × |T - 25°C|` — Arrhenius-inspired temperature acceleration
- `dod_factor = max(DoD, 0.01)^1.2` — depth of discharge power-law
- `crate_factor = 1.0 + 0.3 × max(0, C_rate - 1.0)` — high-power charging penalty

Then: `SOH_{t+1} = SOH_t - ΔSOH`

**Literature basis:**
- Xu et al. (2018), Journal of Power Sources — throughput dependence
- Petit et al. (2016), Applied Energy — empirical aging model
- Pelletier et al. (2017), Transportation Research Part B — degradation review

**Implementation:** `engines/battery_engine.py::compute_soh_degradation()`

## 4. Future Mobility Risk (FMR)

### Definition

```
FMR(a) = P[I_future(a, ω) = 0]
```

Where `I_future(a, ω) = 1` if all required future trips can be completed under scenario `ω`, else 0.

### Monte Carlo Estimation

For each candidate action `a`:

1. Generate N future scenarios by sampling:
   - Energy multiplier: `ε ~ Normal(1.0, σ)`, clipped to [0.7, 1.5]
   - Temperature offset: `δT ~ Normal(0, σ_T)`
   - Traffic: categorical from `{Low, Medium, High}` with configurable probabilities
   - Demand multiplier: scaled by demand level with ±10% noise
   - Charging availability: `Bernoulli(p_charging)` per day
   - Degradation noise: `Normal(1.0, 0.05)`, clipped to [0.8, 1.2]

2. For each scenario, propagate battery state day-by-day through the planning horizon

3. For each future trip at its scheduled day, check:
   - Short trip: `SOC_available ≥ (distance / efficiency_effective) / C_usable × 100 + buffer`
   - Long trip: `SOC_available ≥ departure_minimum AND charger_available`

4. A scenario fails if ANY required trip is infeasible

5. Compute: `FMR(a) = failed_scenarios / total_scenarios`

### Confidence Interval

Wilson score interval (better coverage than Wald for extreme proportions):

```
p̂ ± z × √(p̂(1-p̂)/n + z²/4n²) / (1 + z²/n)
```

**Implementation:** `engines/feasibility_engine.py::compute_probabilistic_fmr()`

## 5. Optimization

```
min_a  J(a) = CurrentCost(a) + λ·BatteryConsequence(a) + μ·FMR(a)
subject to: FMR(a) ≤ ε
```

Where:
- `CurrentCost(a)` — normalized weighted sum of travel time and monetary cost
- `BatteryConsequence(a) = 1 - normalize(SOC_after)` — inverted SOC retention
- `FMR(a)` — normalized probabilistic future mobility risk
- `λ = 0.30` (default), `μ = 0.50` (default), `ε = 0.10` (default)

All objectives are min-max normalized to [0, 1] before weighting.

**No-feasible-action case:** If all candidates have FMR > ε, the optimizer returns `status = "NO_FEASIBLE_ACTION"` with the minimum-FMR candidate and `constraint_relaxed = true`.

**Implementation:** `engines/optimizer.py::select_recommended()`

## 6. Baseline Methods

All baselines use the same physical engines — only the selection criterion differs:

| Method | Objective |
|--------|-----------|
| FASTEST | `min travel_time` |
| ENERGY_MIN | `min energy_consumption` |
| BATTERY_AWARE | `max SOC_after` |
| ITEREV | `min J(a) s.t. FMR(a) ≤ ε` |

No data leakage: all methods receive equivalent information at decision time.

**Implementation:** `experiments/baselines.py`
