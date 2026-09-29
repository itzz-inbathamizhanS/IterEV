"""Quick API verification test."""
import urllib.request, json

payload = json.dumps({
    "evState": {"vehicle_id": "EV-001", "soc": 78, "soh": 94, "temperature": 29, "capacity_kwh": 80, "efficiency": 6.0},
    "origin": "Coimbatore", "destination": "Ooty", "distance_km": 88, "traffic": "Medium",
    "futureTrips": [
        {"id": "1", "day": "TOMORROW", "origin": "Coimbatore", "destination": "Chennai", "distance_km": 500, "priority": "CRITICAL"},
        {"id": "2", "day": "DAY 5", "origin": "Coimbatore", "destination": "Bangalore", "distance_km": 330, "priority": "HIGH"},
    ],
    "scenario_count": 1000, "random_seed": 42, "uncertainty_level": "Medium",
}).encode()
req = urllib.request.Request("http://localhost:8000/api/consumer/routes", data=payload, headers={"Content-Type": "application/json"})
routes = json.loads(urllib.request.urlopen(req).read())
print("=== Consumer Routes (Probabilistic FMR) ===")
for r in routes:
    rec = " ** RECOMMENDED" if r["recommended"] else ""
    print(f"  {r['name']}: energy={r['energy']}kWh, SOC_after={r['after']}%, "
          f"FMR={r['fmr']}%, CI=[{r['fmr_ci_lower']:.1f},{r['fmr_ci_upper']:.1f}] "
          f"scenarios={r['total_scenarios']}{rec}")
    if r["recommended"]:
        print(f"    Explanation: {r['explanation'][:150]}...")
        print(f"    SOH after: {r['soh_after']}")
        print(f"    Constraint relaxed: {r['constraint_relaxed']}")

# Test simulation
sim_payload = json.dumps({
    "mode": "Consumer", "horizon": 5, "soh": 94, "temperature": 29,
    "traffic": "Medium", "demand": "Medium", "charging": "Normal",
    "uncertainty": "Medium", "scenario_count": 1000, "random_seed": 42,
}).encode()
req2 = urllib.request.Request("http://localhost:8000/api/simulation/run", data=sim_payload, headers={"Content-Type": "application/json"})
sim = json.loads(urllib.request.urlopen(req2).read())
print("\n=== Simulation ===")
print(f"  Primary: FMF={sim['primary']['feasibility']}%, FMR={sim['primary']['risk']}%, "
      f"CI=[{sim['primary']['fmr_ci_lower']:.1f},{sim['primary']['fmr_ci_upper']:.1f}]")
print(f"  Scenarios: {sim['primary']['total_scenarios']}, Seed: {sim['random_seed']}")
for row in sim["comparison"]:
    print(f"    {row['method']}: time={row['travelTime']}min, energy={row['energy']}kWh, "
          f"FMR={row['risk']}%, success={row['future_success_rate']}%")

print("\nAll API tests passed!")
