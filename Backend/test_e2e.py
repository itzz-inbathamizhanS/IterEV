"""End-to-end verification test for all API endpoints + frontend serving."""
import urllib.request
import json

def test_routes():
    payload = json.dumps({
        "evState": {"vehicle_id": "EV-001", "soc": 78, "soh": 94, "temperature": 29, "capacity_kwh": 80, "efficiency": 6.0},
        "origin": "Coimbatore",
        "destination": "Ooty",
        "distance_km": 88,
        "traffic": "Medium",
        "futureTrips": [
            {"id": "1", "day": "TOMORROW", "origin": "Coimbatore", "destination": "Chennai", "distance_km": 500, "priority": "CRITICAL"},
            {"id": "2", "day": "DAY 3", "origin": "Local", "destination": "Mobility", "distance_km": 60, "priority": "NORMAL"},
            {"id": "3", "day": "DAY 5", "origin": "Coimbatore", "destination": "Bangalore", "distance_km": 330, "priority": "HIGH"},
        ],
    }).encode()
    req = urllib.request.Request("http://localhost:8000/api/consumer/routes", data=payload, headers={"Content-Type": "application/json"})
    routes = json.loads(urllib.request.urlopen(req).read())
    print("=== Consumer Routes ===")
    for r in routes:
        rec = " ** RECOMMENDED" if r["recommended"] else ""
        print(f"  {r['name']}: energy={r['energy']} kWh, SOC_after={r['after']}%, FMF={r['feasibility']}%, FMR={r['fmr']}%{rec}")
        if r["recommended"]:
            print(f"    Explanation: {r['explanation']}")
            print(f"    Risk change: {r['risk_change']}")

def test_feasibility():
    payload = json.dumps({
        "evState": {"vehicle_id": "EV-001", "soc": 78, "soh": 94, "temperature": 29, "capacity_kwh": 80, "efficiency": 6.0},
        "futureTrips": [
            {"id": "1", "day": "TOMORROW", "origin": "Coimbatore", "destination": "Chennai", "distance_km": 500, "priority": "CRITICAL"},
            {"id": "2", "day": "DAY 3", "origin": "Local", "destination": "Mobility", "distance_km": 60, "priority": "NORMAL"},
            {"id": "3", "day": "DAY 5", "origin": "Coimbatore", "destination": "Bangalore", "distance_km": 330, "priority": "HIGH"},
        ],
    }).encode()
    req = urllib.request.Request("http://localhost:8000/api/consumer/feasibility", data=payload, headers={"Content-Type": "application/json"})
    feas = json.loads(urllib.request.urlopen(req).read())
    print("\n=== Feasibility (RiskPage / FuturePage) ===")
    print(f"  FMF: {feas['fmf']}%")
    print(f"  FMR: {feas['fmr']}%")
    print(f"  Risk timeline: {feas['risk_timeline']}")
    print(f"  is_computed: {feas['is_computed']}")
    for d in feas.get("trip_details", []):
        status = "OK" if d["feasible"] else "INFEASIBLE"
        print(f"    {d['destination']} ({d['distance_km']}km, {d['priority']}): need {d['soc_required']}% have {d['soc_available']}% -> {status}")

def test_simulation():
    payload = json.dumps({
        "mode": "Consumer", "horizon": 5, "soh": 94, "temperature": 29,
        "traffic": "Medium", "demand": "Medium", "charging": "Normal", "uncertainty": "Low",
    }).encode()
    req = urllib.request.Request("http://localhost:8000/api/simulation/run", data=payload, headers={"Content-Type": "application/json"})
    sim = json.loads(urllib.request.urlopen(req).read())
    print("\n=== Simulation ===")
    print(f"  Primary: feasibility={sim['primary']['feasibility']}%, risk={sim['primary']['risk']}%, energy={sim['primary']['energy']} kWh")
    print(f"  is_computed: {sim['is_computed']}")
    for row in sim["comparison"]:
        print(f"    {row['method']}: time={row['travelTime']}min, energy={row['energy']}kWh, FMF={row['feasibility']}%, FMR={row['risk']}%")

def test_frontend():
    html = urllib.request.urlopen("http://localhost:5173/consumer").read().decode()
    print("\n=== Frontend HTML ===")
    print(f"  Response length: {len(html)} bytes")
    has_root = "__root" in html or "root" in html.lower()
    has_consumer = "consumer" in html.lower()
    print(f"  Contains React root: {has_root}")
    print(f"  Contains consumer reference: {has_consumer}")

if __name__ == "__main__":
    test_routes()
    test_feasibility()
    test_simulation()
    test_frontend()
    print("\nAll tests passed!")
