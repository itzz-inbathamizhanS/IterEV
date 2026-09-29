"""Quick API verification test."""
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

@pytest.mark.integration
def test_consumer_routes():
    payload = {
        "evState": {"vehicle_id": "EV-001", "soc": 78, "soh": 94, "temperature": 29, "capacity_kwh": 80, "efficiency": 6.0},
        "origin": "Coimbatore", "destination": "Ooty", "distance_km": 88, "traffic": "Medium",
        "futureTrips": [
            {"id": "1", "day": "TOMORROW", "origin": "Coimbatore", "destination": "Trichy", "distance_km": 300, "priority": "CRITICAL"},
            {"id": "2", "day": "DAY 5", "origin": "Coimbatore", "destination": "Bangalore", "distance_km": 330, "priority": "HIGH"},
        ],
        "scenario_count": 100, "random_seed": 42, "uncertainty_level": "Medium",
    }
    
    response = client.post("/api/consumer/routes", json=payload)
    assert response.status_code == 200
    routes = response.json()
    assert isinstance(routes, list)
    assert len(routes) > 0
    assert "fmr" in routes[0]

@pytest.mark.integration
def test_simulation_run():
    sim_payload = {
        "mode": "Consumer", "horizon": 5, "soh": 94, "temperature": 29,
        "traffic": "Medium", "demand": "Medium", "charging": "Normal",
        "uncertainty": "Medium", "scenario_count": 100, "random_seed": 42,
    }
    
    response = client.post("/api/simulation/run", json=sim_payload)
    assert response.status_code == 200
    sim = response.json()
    assert "primary" in sim
    assert "comparison" in sim
