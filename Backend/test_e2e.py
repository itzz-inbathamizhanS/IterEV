"""End-to-end verification test for all API endpoints."""
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

@pytest.mark.integration
def test_routes():
    payload = {
        "evState": {"vehicle_id": "EV-001", "soc": 78, "soh": 94, "temperature": 29, "capacity_kwh": 80, "efficiency": 6.0},
        "origin": "Coimbatore",
        "destination": "Ooty",
        "distance_km": 88,
        "traffic": "Medium",
        "futureTrips": [
            {"id": "1", "day": "TOMORROW", "origin": "Coimbatore", "destination": "Trichy", "distance_km": 300, "priority": "CRITICAL"},
            {"id": "2", "day": "DAY 3", "origin": "Local", "destination": "Mobility", "distance_km": 60, "priority": "NORMAL"},
            {"id": "3", "day": "DAY 5", "origin": "Coimbatore", "destination": "Bangalore", "distance_km": 330, "priority": "HIGH"},
        ],
    }
    response = client.post("/api/consumer/routes", json=payload)
    assert response.status_code == 200
    routes = response.json()
    print("=== Consumer Routes ===")
    for r in routes:
        rec = " ** RECOMMENDED" if r["recommended"] else ""
        print(f"  {r['name']}: energy={r['energy']} kWh, SOC_after={r['after']}%, FMF={r['feasibility']}%, FMR={r['fmr']}%{rec}")

@pytest.mark.integration
def test_feasibility():
    payload = {
        "evState": {"vehicle_id": "EV-001", "soc": 78, "soh": 94, "temperature": 29, "capacity_kwh": 80, "efficiency": 6.0},
        "futureTrips": [
            {"id": "1", "day": "TOMORROW", "origin": "Coimbatore", "destination": "Trichy", "distance_km": 300, "priority": "CRITICAL"},
            {"id": "2", "day": "DAY 3", "origin": "Local", "destination": "Mobility", "distance_km": 60, "priority": "NORMAL"},
            {"id": "3", "day": "DAY 5", "origin": "Coimbatore", "destination": "Bangalore", "distance_km": 330, "priority": "HIGH"},
        ],
    }
    response = client.post("/api/consumer/feasibility", json=payload)
    assert response.status_code == 200
    feas = response.json()
    print("\\n=== Feasibility (RiskPage / FuturePage) ===")
    print(f"  FMF: {feas['fmf']}%")
    print(f"  FMR: {feas['fmr']}%")
    print(f"  is_computed: {feas['is_computed']}")

@pytest.mark.integration
def test_simulation():
    payload = {
        "mode": "Consumer", "horizon": 5, "soh": 94, "temperature": 29,
        "traffic": "Medium", "demand": "Medium", "charging": "Normal", "uncertainty": "Low",
    }
    response = client.post("/api/simulation/run", json=payload)
    assert response.status_code == 200
    sim = response.json()
    print("\\n=== Simulation ===")
    print(f"  Primary: feasibility={sim['primary']['feasibility']}%, risk={sim['primary']['risk']}%, energy={sim['primary']['energy']} kWh")
    print(f"  is_computed: {sim['is_computed']}")

