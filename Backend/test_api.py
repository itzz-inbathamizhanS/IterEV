"""Live API test — tests health and consumer routes endpoints."""
from fastapi.testclient import TestClient
import pytest
from main import app

client = TestClient(app)

@pytest.mark.integration
def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    print("Health:", data)

@pytest.mark.integration
def test_consumer_routes():
    payload = {
        "evState": {"vehicle_id": "EV-001", "soc": 78, "soh": 94, "temperature": 29, "capacity_kwh": 80, "efficiency": 6.0},
        "origin": "Coimbatore",
        "destination": "Ooty",
        "distance_km": 88,
        "traffic": "Medium",
        "futureTrips": [
            {"id": "1", "day": "TOMORROW", "origin": "Coimbatore", "destination": "Trichy", "distance_km": 300, "priority": "CRITICAL"},
            {"id": "2", "day": "DAY 5", "origin": "Coimbatore", "destination": "Bangalore", "distance_km": 330, "priority": "HIGH"},
        ],
    }

    response = client.post("/api/consumer/routes", json=payload)
    assert response.status_code == 200
    routes = response.json()
    print(f"\\nRoutes computed ({len(routes)}):")
    for r in routes:
        rec = "** RECOMMENDED" if r["recommended"] else ""
        print(f"  {r['name']}: energy={r['energy']} kWh, SOC_after={r['after']}%, FMF={r['feasibility']}%, FMR={r['fmr']}%  {rec}")

    rec_route = next(r for r in routes if r["recommended"])
    print(f"\\nChosen: {rec_route['name']}")
    print(f"Explanation: {rec_route['explanation']}")
    print(f"Risk change: {rec_route['risk_change']}")
    print(f"\\nAll values computed by engine (is_computed={rec_route['is_computed']})")

