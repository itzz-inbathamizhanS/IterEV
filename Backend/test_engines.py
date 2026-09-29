"""Quick end-to-end engine verification test."""
from engines.energy_engine import compute_all_routes
from engines.battery_engine import compute_soc_after, estimate_tomorrow_soc
from engines.feasibility_engine import compute_fmf
from engines.optimizer import select_recommended
from engines.explanation_engine import generate_explanation
from models.schemas import RouteCandidate, FutureTrip

# --- Test 1: Energy + Battery at default conditions (SOC=78, SOH=94, temp=29, traffic=Medium) ---
routes_raw = compute_all_routes("Medium", 29, 94)
print("Route profiles (SOC=78, SOH=94, temp=29, traffic=Medium):")
for r in routes_raw:
    soc_after = compute_soc_after(78, r["energy_kwh"], 94, 80)
    tomorrow = estimate_tomorrow_soc(soc_after)
    print(f"  {r['name']}: energy={r['energy_kwh']} kWh, time={r['time_min']} min, SOC_after={soc_after}%, tomorrow={tomorrow}%")

# --- Test 2: FMF with realistic future trips ---
trips = [
    FutureTrip(id="1", day="TOMORROW",  origin="Coimbatore", destination="Trichy",   distance_km=300, priority="CRITICAL"),
    FutureTrip(id="2", day="DAY 5",     origin="Coimbatore", destination="Bangalore", distance_km=330, priority="HIGH"),
]

candidates = []
for r in routes_raw:
    soc_after = compute_soc_after(78, r["energy_kwh"], 94, 80)
    fmf, fmr, _ = compute_fmf(soc_after, 94, trips, 80)
    candidates.append(RouteCandidate(
        id=r["id"], name=r["name"], time=r["time_min"], cost=r["cost_inr"],
        energy=r["energy_kwh"], feasibility=fmf, fmr=fmr,
        after=soc_after, tomorrow=estimate_tomorrow_soc(soc_after),
        recommended=False,
    ))

print("\nFMF/FMR per route:")
for c in candidates:
    print(f"  {c.name}: FMF={c.feasibility}%, FMR={c.fmr}%, SOC_after={c.after}%")

# --- Test 3: Optimizer ---
rec_id, scores, status = select_recommended(candidates)
print(f"\nOptimizer selected: {rec_id}")
for s in scores:
    print(f"  {s.route_name}: J={s.total_J:.4f}  feasible={s.feasible}")

# --- Test 4: Explanation ---
rec = next(c for c in candidates if c.id == rec_id)
exp = generate_explanation(rec, candidates)
print(f"\nExplanation: {exp['reason_text']}")
print(f"Battery effect: {exp['battery_effect']}")
print(f"Risk change: {exp['risk_change']}")
