"""Live API test — tests health and consumer routes endpoints."""
import urllib.request, json

# Test health endpoint
req = urllib.request.urlopen("http://localhost:8000/api/health")
data = json.loads(req.read())
print("Health:", data)

# Test consumer routes with default scenario
payload = json.dumps({
    "evState": {"vehicle_id": "EV-001", "soc": 78, "soh": 94, "temperature": 29, "capacity_kwh": 80, "efficiency": 6.0},
    "origin": "Coimbatore",
    "destination": "Ooty",
    "distance_km": 88,
    "traffic": "Medium",
    "futureTrips": [
        {"id": "1", "day": "TOMORROW", "origin": "Coimbatore", "destination": "Chennai", "distance_km": 500, "priority": "CRITICAL"},
        {"id": "2", "day": "DAY 5", "origin": "Coimbatore", "destination": "Bangalore", "distance_km": 330, "priority": "HIGH"},
    ],
}).encode()

req2 = urllib.request.Request(
    "http://localhost:8000/api/consumer/routes",
    data=payload,
    headers={"Content-Type": "application/json"},
)
routes = json.loads(urllib.request.urlopen(req2).read())
print(f"\nRoutes computed ({len(routes)}):")
for r in routes:
    rec = "** RECOMMENDED" if r["recommended"] else ""
    print(f"  {r['name']}: energy={r['energy']} kWh, SOC_after={r['after']}%, FMF={r['feasibility']}%, FMR={r['fmr']}%  {rec}")

rec_route = next(r for r in routes if r["recommended"])
print(f"\nChosen: {rec_route['name']}")
print(f"Explanation: {rec_route['explanation']}")
print(f"Risk change: {rec_route['risk_change']}")
print(f"\nAll values computed by engine (is_computed={rec_route['is_computed']})")
