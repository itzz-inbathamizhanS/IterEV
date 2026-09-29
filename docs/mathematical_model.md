# IterEV — Mathematical Model & Experimental Protocol

## 1. State Variables

The EV state at time t:

```
x_t = [SOC_t, SOH_t, T_t, C_t]
```

Where SOC = state of charge (%), SOH = state of health (%), T = temperature (°C), C = usable capacity (kWh).

## 2. Energy Model

Energy consumption for route r under conditions:

```
E(r) = E_base(r) × f_traffic × f_temperature × f_SOH × ε_energy
```

- `f_traffic = TRAFFIC_FACTORS[traffic]` — {Low: 0.88, Medium: 1.00, High: 1.20}
- `f_temperature = 1.0 + |T - 29°C| × 0.008`
- `f_SOH = 1.0 + max(0, 94 - SOH) × 0.002`
- `ε_energy ~ Normal(1.0, σ)` — prediction uncertainty

## 3. SOC State Transition

After a trip consuming E kWh:

```
SOC_{t+1} = SOC_t - (E / C_usable) × 100
```

After charging:

```
SOC_{t+1} = min(95, SOC_t + (E_charged / C_usable) × 100)
```

After standby (per day):

```
SOC_{t+1} = SOC_t - 5.0
```

Where `C_usable = C_nominal × (SOH / 100)`.

## 4. SOH Degradation Model

Reduced-order proxy (NOT electrochemical):

```
ΔSOH = base_rate × throughput × temp_factor × dod_factor × crate_factor × ε_degradation
```

- `throughput = E / C_usable`
- `temp_factor = 1.0 + 0.06 × |T - 25°C|`
- `dod_factor = max(DoD, 0.01)^1.2`
- `crate_factor = 1.0 + 0.3 × max(0, C_rate - 1.0)`
- `ε_degradation ~ Normal(1.0, 0.05)` — degradation uncertainty

```
SOH_{t+1} = SOH_t - ΔSOH_t
```

SOH degradation → usable capacity decreases → same trip requires larger SOC fraction → future feasibility changes. This causal chain is explicitly implemented.

## 5. Future Mobility Risk (FMR)

### Definition

```
FMR(a) = P[at least one future trip infeasible | action a]
```

### Monte Carlo Estimation

For each candidate action a, generate N scenarios (ω₁...ωₙ):

**Day-by-day state propagation (corrected implementation):**

```
For each scenario s = 1..N:
  For each day d = 0..horizon:
    1. If trip scheduled on day d:
       a. Compute trip energy: E = (distance × demand_mult × combined_factor) / efficiency
       b. Compute SOC required: SOC_req = (E / C_usable) × 100 + buffer
       c. Check feasibility: SOC_available ≥ SOC_req
       d. If feasible → SOC = SOC - (E / C_usable) × 100  [STATE CHANGE]
       e. If infeasible → scenario_failed = True, continue for diagnostics
       f. Compute ΔSOH from trip, update SOH                [STATE CHANGE]
    2. If charger available (Bernoulli(p)):
       a. Compute charging energy: E_charge = P_charger × t × η
       b. SOC = min(95, SOC + (E_charge / C_usable) × 100) [STATE CHANGE]
       c. Compute ΔSOH from charging, update SOH            [STATE CHANGE]
    3. Apply standby loss: SOC = SOC - 5%
    4. Clamp SOC to [0, 100]
```

```
FMR(a) = N_failed / N_total
```

### Failure Definition

A scenario fails if at least one mandatory future trip cannot be completed while respecting the minimum SOC reserve (5%).

### Confidence Interval

Wilson score interval for binomial proportion p = k/n:

```
center = (p̂ + z²/2n) / (1 + z²/n)
spread = z × √(p̂(1-p̂)/n + z²/4n²) / (1 + z²/n)
CI = [center - spread, center + spread]
```

## 6. Optimization

```
min_a J(a) = Cost_norm(a) + 0.30·Battery_norm(a) + 0.50·FMR_norm(a)
Cost_norm(a) = 0.5·time_norm + 0.5·monetary_cost_norm
```

All objectives min-max normalized to [0, 1].

**No-feasible-action fallback:** If all candidates have FMR > ε, select the one with minimum FMR and return `constraint_relaxed = true`.

## 7. Uncertainty Sources

| Variable | Distribution | Ablation Flag |
|----------|-------------|---------------|
| Energy consumption | Normal(1.0, σ) | `use_energy_uncertainty` |
| Temperature | Normal(0, σ_T) | `use_temperature_uncertainty` |
| Traffic | Categorical(p_low, p_med, p_high) | `use_traffic_uncertainty` |
| Future demand | Normal(base_mult, 0.10) per day | `use_demand_uncertainty` |
| Charger availability | Bernoulli(p) per day | `use_charging_uncertainty` |
| Degradation | Normal(1.0, 0.05) per event | `use_degradation_uncertainty` |

## 8. Baseline Methods

| Method | Objective | Same scenarios? |
|--------|-----------|----------------|
| FASTEST | min travel_time | Yes (common RNG) |
| ENERGY_MIN | min energy | Yes |
| BATTERY_AWARE | max SOC_after | Yes |
| ITEREV | min J(a) s.t. FMR ≤ ε | Yes |

All methods receive equivalent information. Only the decision criterion changes.

## 9. Experimental Protocol

### Estimation Phase
- Seed: 42, N: 5000
- Used for FMR estimation and decision making

### Independent Validation Phase
- Seed: 4242, N: 20000
- NEVER used for estimation
- Used to compute observed failure rate
- Comparison: predicted FMR vs observed failure rate

### Ablation Design
Each variant uses `AblationFlags` to EXPLICITLY DISABLE (not reduce) the component:

| Variant | What is disabled |
|---------|-----------------|
| A0: Full IterEV | Nothing |
| A1: No Future Risk | FMR weight = 0 in optimizer |
| A2: No Battery Degradation | SOH does not change |
| A3: No Energy/Env Uncertainty | Energy, temperature, traffic deterministic |
| A4: No Demand Uncertainty | Demand multipliers fixed |
| A5: No Charging Uncertainty | Charger always/never available |
| A6: No Degradation Uncertainty | Degradation noise = 1.0 |

All variants use same seed, same scenario base, same routes. Only intended component changes.

## 10. Limitations

1. Route profiles are research-scenario-specific (Coimbatore→Ooty), not real-time routing
2. Battery degradation is a reduced-order proxy, not electrochemical simulation
3. Charging model is energy-balance, not CC/CV curve
4. Overnight SOC loss (5%) is aggregate standby consumption, not pure self-discharge
5. No real-time traffic/weather API — uses statistical distributions
6. Fleet module is prototype only
7. Uncertainty distribution parameters are documented but not vehicle-specific
