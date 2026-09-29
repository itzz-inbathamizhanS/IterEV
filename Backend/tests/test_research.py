"""
Comprehensive pytest test suite for IterEV research engines.

Covers:
  - Energy engine (temperature, traffic, SOH effects, edge cases)
  - Battery engine (SOC transition, SOH degradation, capacity, boundaries)
  - Feasibility engine (deterministic FMF, probabilistic FMR, day parsing)
  - Uncertainty engine (reproducibility, distribution validity)
  - Charging engine (energy, duration, cost, SOC transition)
  - Optimizer (feasible/infeasible, constraint enforcement)
  - Integration (end-to-end pipeline)

Run with:
    cd Backend
    python -m pytest tests/ -v
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import numpy as np


# ─── Energy Engine Tests ────────────────────────────────────────────────────

class TestEnergyEngine:
    def test_predict_energy_baseline(self):
        from engines.energy_engine import predict_energy
        # At baseline conditions, energy should equal base energy
        result = predict_energy(14.8, "Medium", 29.0, 94.0)
        assert isinstance(result, float)
        assert result > 0

    def test_traffic_effect(self):
        from engines.energy_engine import predict_energy
        low = predict_energy(14.8, "Low", 29.0, 94.0)
        med = predict_energy(14.8, "Medium", 29.0, 94.0)
        high = predict_energy(14.8, "High", 29.0, 94.0)
        assert low < med < high, "Higher traffic should increase energy"

    def test_temperature_effect(self):
        from engines.energy_engine import predict_energy
        cold = predict_energy(14.8, "Medium", 10.0, 94.0)
        normal = predict_energy(14.8, "Medium", 25.0, 94.0)
        hot = predict_energy(14.8, "Medium", 45.0, 94.0)
        # Both extremes should differ from normal
        assert cold != normal or hot != normal

    def test_soh_effect(self):
        from engines.energy_engine import predict_energy
        good = predict_energy(14.8, "Medium", 29.0, 100.0)
        poor = predict_energy(14.8, "Medium", 29.0, 70.0)
        assert poor >= good, "Lower SOH should increase energy consumption"

    def test_zero_base_energy(self):
        from engines.energy_engine import predict_energy
        result = predict_energy(0.0, "Medium", 29.0, 94.0)
        assert result >= 0.1, "Should return minimum positive energy"

    def test_compute_all_routes(self):
        from engines.energy_engine import compute_all_routes
        routes = compute_all_routes("Medium", 29.0, 94.0)
        assert len(routes) == 3
        for r in routes:
            assert "energy_kwh" in r
            assert "time_min" in r
            assert "cost_inr" in r
            assert r["energy_kwh"] > 0


# ─── Battery Engine Tests ───────────────────────────────────────────────────

class TestBatteryEngine:
    def test_soc_after_basic(self):
        from engines.battery_engine import compute_soc_after
        result = compute_soc_after(78.0, 14.8, 94.0, 80.0)
        assert 0 <= result <= 100
        assert result < 78.0, "SOC should decrease after trip"

    def test_soc_after_zero_energy(self):
        from engines.battery_engine import compute_soc_after
        result = compute_soc_after(78.0, 0.0, 94.0, 80.0)
        assert result == 78.0

    def test_soc_after_clamp_zero(self):
        from engines.battery_engine import compute_soc_after
        result = compute_soc_after(10.0, 100.0, 94.0, 80.0)
        assert result == 0.0

    def test_soc_after_clamp_hundred(self):
        from engines.battery_engine import compute_soc_after
        result = compute_soc_after(100.0, 0.0, 94.0, 80.0)
        assert result == 100.0

    def test_usable_capacity(self):
        from engines.battery_engine import compute_usable_capacity
        assert compute_usable_capacity(100.0, 80.0) == 80.0
        assert compute_usable_capacity(50.0, 80.0) == 40.0
        assert compute_usable_capacity(0.0, 80.0) == 0.0

    def test_tomorrow_soc(self):
        from engines.battery_engine import estimate_tomorrow_soc
        result = estimate_tomorrow_soc(78.0)
        assert result < 78.0, "Tomorrow SOC should be lower"
        assert result > 0

    def test_soh_degradation_positive(self):
        from engines.battery_engine import compute_soh_degradation
        loss = compute_soh_degradation(
            energy_throughput_kwh=15.0,
            temperature=35.0,
            soc_start=80.0,
            soc_end=60.0,
            soh=94.0,
        )
        assert loss > 0, "Degradation should be positive"
        assert loss < 1.0, "Single trip degradation should be small"

    def test_soh_degradation_zero_energy(self):
        from engines.battery_engine import compute_soh_degradation
        loss = compute_soh_degradation(0.0, 25.0, 78.0, 78.0)
        assert loss == 0.0

    def test_soh_degradation_temperature_effect(self):
        from engines.battery_engine import compute_soh_degradation
        cool = compute_soh_degradation(15.0, 20.0, 80.0, 60.0, soh=94.0)
        hot = compute_soh_degradation(15.0, 45.0, 80.0, 60.0, soh=94.0)
        assert hot > cool, "Higher temperature should increase degradation"

    def test_future_soc_projection(self):
        from engines.battery_engine import future_soc_projection
        proj = future_soc_projection(78.0, 5, soh=94.0)
        assert len(proj) == 5
        # Should be monotonically decreasing
        for i in range(1, len(proj)):
            assert proj[i] <= proj[i-1]

    def test_range_estimation(self):
        from engines.battery_engine import estimate_range_km
        r = estimate_range_km(100.0, 100.0, 80.0, 6.0)
        assert r == 480  # 80 * 6.0


# ─── Feasibility Engine Tests ──────────────────────────────────────────────

class TestFeasibilityEngine:
    def _make_trip(self, distance=100.0, day="TOMORROW", priority="NORMAL"):
        from models.schemas import FutureTrip
        return FutureTrip(
            id="test", day=day, origin="A", destination="B",
            distance_km=distance, priority=priority,
        )

    def test_day_parsing(self):
        from engines.feasibility_engine import _parse_day_index
        assert _parse_day_index("TODAY") == 0
        assert _parse_day_index("TOMORROW") == 1
        assert _parse_day_index("DAY 3") == 2
        assert _parse_day_index("DAY 5") == 4
        assert _parse_day_index("DAY 1") == 0

    def test_fmf_no_trips(self):
        from engines.feasibility_engine import compute_fmf
        fmf, fmr, details = compute_fmf(78.0, 94.0, [])
        assert fmf == 99.0
        assert fmr == 1.0
        assert details == []

    def test_fmf_easy_trip(self):
        from engines.feasibility_engine import compute_fmf
        trip = self._make_trip(distance=30.0)  # Short easy trip
        fmf, fmr, details = compute_fmf(80.0, 94.0, [trip])
        assert fmf > 50.0, "Easy trip should be mostly feasible"
        assert len(details) == 1

    def test_fmf_impossible_trip(self):
        from engines.feasibility_engine import compute_fmf
        trip = self._make_trip(distance=300.0)  # Very long trip
        fmf, fmr, details = compute_fmf(10.0, 94.0, [trip])
        assert fmr > 0, "Should have non-zero risk"

    def test_probabilistic_fmr_reproducible(self):
        from engines.feasibility_engine import compute_probabilistic_fmr
        trip = self._make_trip(distance=100.0)
        r1 = compute_probabilistic_fmr(60.0, 94.0, [trip], scenario_count=500, random_seed=42)
        r2 = compute_probabilistic_fmr(60.0, 94.0, [trip], scenario_count=500, random_seed=42)
        assert r1.fmr == r2.fmr, "Same seed should produce same FMR"
        assert r1.total_scenarios == 500

    def test_probabilistic_fmr_different_seeds(self):
        from engines.feasibility_engine import compute_probabilistic_fmr
        trip = self._make_trip(distance=100.0)
        r1 = compute_probabilistic_fmr(60.0, 94.0, [trip], scenario_count=1000, random_seed=42)
        r2 = compute_probabilistic_fmr(60.0, 94.0, [trip], scenario_count=1000, random_seed=99)
        # Different seeds may produce slightly different results
        # (but both should be valid estimates)
        assert r1.total_scenarios == 1000
        assert r2.total_scenarios == 1000

    def test_probabilistic_fmr_has_ci(self):
        from engines.feasibility_engine import compute_probabilistic_fmr
        trip = self._make_trip(distance=100.0)
        result = compute_probabilistic_fmr(60.0, 94.0, [trip], scenario_count=500, random_seed=42)
        assert result.confidence_interval is not None
        assert result.confidence_interval.lower <= result.fmr
        assert result.confidence_interval.upper >= result.fmr

    def test_probabilistic_fmr_no_trips(self):
        from engines.feasibility_engine import compute_probabilistic_fmr
        result = compute_probabilistic_fmr(78.0, 94.0, [], scenario_count=100)
        assert result.fmr <= 2.0
        assert result.failed_scenarios == 0

    def test_fmr_scenario_counts(self):
        from engines.feasibility_engine import compute_probabilistic_fmr
        trip = self._make_trip(distance=100.0)
        result = compute_probabilistic_fmr(60.0, 94.0, [trip], scenario_count=200, random_seed=42)
        assert result.total_scenarios == 200
        assert result.successful_scenarios + result.failed_scenarios == 200

    def test_soc_required_short_trip(self):
        from engines.feasibility_engine import _soc_required_for_trip
        req = _soc_required_for_trip(100.0, 94.0)
        assert req > 0
        assert req < 95

    def test_soc_required_long_trip(self):
        from engines.feasibility_engine import _soc_required_for_trip
        from models.constants import LONG_TRIP_DEPARTURE_SOC_MIN
        req = _soc_required_for_trip(500.0, 94.0)
        assert req == LONG_TRIP_DEPARTURE_SOC_MIN

    def test_different_vehicle_efficiency(self):
        from engines.feasibility_engine import _soc_required_for_trip
        efficient = _soc_required_for_trip(100.0, 94.0, efficiency_km_kwh=8.0)
        inefficient = _soc_required_for_trip(100.0, 94.0, efficiency_km_kwh=4.0)
        assert inefficient > efficient


# ─── Uncertainty Engine Tests ───────────────────────────────────────────────

class TestUncertaintyEngine:
    def test_reproducibility(self):
        from engines.uncertainty_engine import generate_scenarios
        s1 = generate_scenarios(n_scenarios=100, random_seed=42)
        s2 = generate_scenarios(n_scenarios=100, random_seed=42)
        np.testing.assert_array_equal(s1.energy_multipliers, s2.energy_multipliers)

    def test_different_seeds(self):
        from engines.uncertainty_engine import generate_scenarios
        s1 = generate_scenarios(n_scenarios=100, random_seed=42)
        s2 = generate_scenarios(n_scenarios=100, random_seed=99)
        assert not np.array_equal(s1.energy_multipliers, s2.energy_multipliers)

    def test_energy_multiplier_distribution(self):
        from engines.uncertainty_engine import generate_scenarios
        s = generate_scenarios(n_scenarios=10000, random_seed=42, uncertainty_level="Medium")
        mean = np.mean(s.energy_multipliers)
        assert abs(mean - 1.0) < 0.05, "Mean should be near 1.0"
        assert np.all(s.energy_multipliers >= 0.7)
        assert np.all(s.energy_multipliers <= 1.5)

    def test_charger_availability(self):
        from engines.uncertainty_engine import generate_scenarios
        s = generate_scenarios(n_scenarios=10000, random_seed=42, charging_availability=0.5)
        fraction = np.mean(s.charger_available)
        assert abs(fraction - 0.5) < 0.05, "Should be ~50% available"

    def test_scenario_shapes(self):
        from engines.uncertainty_engine import generate_scenarios
        s = generate_scenarios(n_scenarios=100, horizon_days=7)
        assert s.energy_multipliers.shape == (100, 7)
        assert s.temperature_offsets.shape == (100, 7)
        assert s.charger_available.shape == (100, 7)
        assert s.demand_multipliers.shape == (100, 7)
        assert s.degradation_noise.shape == (100, 7)


# ─── Charging Engine Tests ──────────────────────────────────────────────────

class TestChargingEngine:
    def test_charging_energy(self):
        from engines.charging_engine import compute_charging_energy
        energy = compute_charging_energy(20.0, 80.0, 94.0)
        assert energy > 0

    def test_charging_energy_no_change(self):
        from engines.charging_engine import compute_charging_energy
        energy = compute_charging_energy(80.0, 80.0, 94.0)
        assert energy == 0.0

    def test_charging_duration(self):
        from engines.charging_engine import compute_charging_duration
        duration = compute_charging_duration(25.0, 50.0)
        assert duration > 0
        assert duration == 30.0  # 25 kWh / 50 kW = 0.5 hr = 30 min

    def test_charging_cost(self):
        from engines.charging_engine import compute_charging_cost
        cost = compute_charging_cost(25.0, 15.0)
        assert cost == 375.0

    def test_soc_after_charging(self):
        from engines.charging_engine import compute_soc_after_charging
        soc = compute_soc_after_charging(20.0, 60.0, 94.0)
        assert soc > 20.0
        assert soc <= 95.0


# ─── Optimizer Tests ────────────────────────────────────────────────────────

class TestOptimizer:
    def _make_routes(self, fmrs=(2.0, 5.0, 8.0)):
        from models.schemas import RouteCandidate
        return [
            RouteCandidate(
                id=f"0{i+1}", name=f"Route{i+1}",
                time=40+i*5, cost=180-i*10, energy=15.0-i*0.5,
                feasibility=100-fmr, fmr=fmr, after=60+i*3,
                tomorrow=55+i*3, recommended=False,
            )
            for i, fmr in enumerate(fmrs)
        ]

    def test_selects_feasible(self):
        from engines.optimizer import select_recommended
        routes = self._make_routes(fmrs=(5.0, 3.0, 8.0))
        rec_id, scores, status = select_recommended(routes)
        assert status == "FEASIBLE"
        assert rec_id in [r.id for r in routes]

    def test_no_feasible_action(self):
        from engines.optimizer import select_recommended
        routes = self._make_routes(fmrs=(15.0, 20.0, 25.0))
        rec_id, scores, status = select_recommended(routes, epsilon_fmr=0.10)
        assert status == "NO_FEASIBLE_ACTION"

    def test_score_normalization(self):
        from engines.optimizer import score_routes
        routes = self._make_routes()
        scores = score_routes(routes)
        for s in scores:
            assert 0 <= s.current_cost <= 1.0
            assert 0 <= s.battery_consequence <= 1.0
            assert 0 <= s.fmr_term <= 1.0

    def test_empty_routes(self):
        from engines.optimizer import select_recommended
        rec_id, scores, status = select_recommended([])
        assert rec_id == ""
        assert scores == []


# ─── Integration Tests ─────────────────────────────────────────────────────

class TestIntegration:
    def test_full_pipeline(self):
        """End-to-end: energy → battery → feasibility → optimizer."""
        from engines.energy_engine import compute_all_routes
        from engines.battery_engine import compute_soc_after, estimate_tomorrow_soc
        from engines.feasibility_engine import compute_probabilistic_fmr
        from engines.optimizer import select_recommended
        from engines.explanation_engine import generate_explanation
        from models.schemas import RouteCandidate, FutureTrip

        routes_raw = compute_all_routes("Medium", 29.0, 94.0)
        assert len(routes_raw) == 3

        trips = [
            FutureTrip(id="1", day="TOMORROW", origin="A", destination="Chennai",
                      distance_km=500, priority="CRITICAL"),
        ]

        candidates = []
        for r in routes_raw:
            soc_after = compute_soc_after(78.0, r["energy_kwh"], 94.0, 80.0)
            fmr_result = compute_probabilistic_fmr(
                soc_after, 94.0, trips, scenario_count=200, random_seed=42,
            )
            candidates.append(RouteCandidate(
                id=r["id"], name=r["name"], time=r["time_min"], cost=r["cost_inr"],
                energy=r["energy_kwh"], feasibility=fmr_result.fmf, fmr=fmr_result.fmr,
                after=soc_after, tomorrow=estimate_tomorrow_soc(soc_after),
                recommended=False,
            ))

        rec_id, scores, status = select_recommended(candidates)
        assert rec_id in ["01", "02", "03"]

        rec = next(c for c in candidates if c.id == rec_id)
        exp = generate_explanation(rec, candidates)
        assert "reason_text" in exp
        assert len(exp["reason_text"]) > 0


# ─── Edge Case Tests ───────────────────────────────────────────────────────

class TestEdgeCases:
    def test_soc_zero(self):
        from engines.battery_engine import compute_soc_after
        result = compute_soc_after(0.0, 10.0, 94.0)
        assert result == 0.0

    def test_soc_hundred(self):
        from engines.battery_engine import compute_soc_after
        result = compute_soc_after(100.0, 0.0, 94.0)
        assert result == 100.0

    def test_soh_zero(self):
        from engines.battery_engine import compute_soc_after
        result = compute_soc_after(78.0, 10.0, 0.0)
        assert result == 0.0

    def test_soh_hundred(self):
        from engines.battery_engine import compute_usable_capacity
        cap = compute_usable_capacity(100.0, 80.0)
        assert cap == 80.0

    def test_zero_distance_trip(self):
        from engines.feasibility_engine import _soc_required_for_trip
        req = _soc_required_for_trip(0.0, 94.0)
        assert req >= 0

    def test_very_long_distance(self):
        from engines.feasibility_engine import _soc_required_for_trip
        from models.constants import LONG_TRIP_DEPARTURE_SOC_MIN
        req = _soc_required_for_trip(1000.0, 94.0)
        assert req == LONG_TRIP_DEPARTURE_SOC_MIN

    def test_no_future_trips(self):
        from engines.feasibility_engine import compute_probabilistic_fmr
        result = compute_probabilistic_fmr(78.0, 94.0, [], scenario_count=100)
        assert result.fmr <= 2.0

    def test_scenario_count_minimum(self):
        from engines.feasibility_engine import compute_probabilistic_fmr
        from models.schemas import FutureTrip
        trip = FutureTrip(id="t", day="TOMORROW", origin="A", destination="B",
                         distance_km=100, priority="NORMAL")
        result = compute_probabilistic_fmr(60.0, 94.0, [trip], scenario_count=100)
        assert result.total_scenarios == 100


# ─── Causal Sanity Tests (Bug Fix Verification) ────────────────────────────

class TestFutureSOCConsumption:
    """Bug #1: Future trips MUST consume SOC."""

    def test_two_trips_lower_soc_for_second(self):
        """Two trips on consecutive days: second trip starts with lower SOC."""
        from engines.feasibility_engine import compute_probabilistic_fmr
        from models.schemas import FutureTrip

        # One trip
        trip1 = FutureTrip(id="t1", day="TOMORROW", origin="A", destination="B",
                           distance_km=50, priority="NORMAL")
        r1 = compute_probabilistic_fmr(80.0, 94.0, [trip1], scenario_count=500,
                                       random_seed=42, charging_availability=0.0)

        # Two trips: second on DAY 3
        trip2 = FutureTrip(id="t2", day="DAY 3", origin="B", destination="C",
                           distance_km=50, priority="NORMAL")
        r2 = compute_probabilistic_fmr(80.0, 94.0, [trip1, trip2], scenario_count=500,
                                       random_seed=42, charging_availability=0.0)

        # More trips with no charging → higher FMR
        assert r2.fmr >= r1.fmr, "Two trips should have >= FMR than one trip"

    def test_trip_reduces_soc_measurably(self):
        """A 200km trip should cause measurable future risk even from high SOC."""
        from engines.feasibility_engine import compute_probabilistic_fmr
        from models.schemas import FutureTrip

        trip_big = FutureTrip(id="t1", day="TOMORROW", origin="A", destination="B",
                              distance_km=200, priority="CRITICAL")
        trip_small = FutureTrip(id="t2", day="TOMORROW", origin="A", destination="B",
                                distance_km=20, priority="NORMAL")

        r_big = compute_probabilistic_fmr(50.0, 94.0, [trip_big], scenario_count=500, random_seed=42)
        r_small = compute_probabilistic_fmr(50.0, 94.0, [trip_small], scenario_count=500, random_seed=42)

        assert r_big.fmr > r_small.fmr, "Longer trip should have higher FMR"


class TestFutureSOHPropagation:
    """Bug #2: SOH MUST propagate across future days."""

    def test_soh_degrades_over_horizon(self):
        """Multiple trips should cause measurable SOH change across days."""
        from engines.feasibility_engine import compute_probabilistic_fmr
        from models.schemas import FutureTrip

        trips = [
            FutureTrip(id="t1", day="TOMORROW", origin="A", destination="B",
                       distance_km=150, priority="NORMAL"),
            FutureTrip(id="t2", day="DAY 3", origin="B", destination="C",
                       distance_km=150, priority="NORMAL"),
            FutureTrip(id="t3", day="DAY 5", origin="C", destination="D",
                       distance_km=150, priority="NORMAL"),
        ]
        # Low SOH should produce higher FMR than high SOH
        r_low = compute_probabilistic_fmr(80.0, 75.0, trips, scenario_count=500, random_seed=42)
        r_high = compute_probabilistic_fmr(80.0, 100.0, trips, scenario_count=500, random_seed=42)

        assert r_low.fmr >= r_high.fmr, "Lower SOH should not improve feasibility"


class TestDegradationNoise:
    """Bug #10: Degradation noise MUST be applied."""

    def test_same_seed_same_degradation(self):
        from engines.uncertainty_engine import generate_scenarios
        s1 = generate_scenarios(n_scenarios=100, random_seed=42)
        s2 = generate_scenarios(n_scenarios=100, random_seed=42)
        assert np.array_equal(s1.degradation_noise, s2.degradation_noise)

    def test_different_seed_different_degradation(self):
        from engines.uncertainty_engine import generate_scenarios
        s1 = generate_scenarios(n_scenarios=100, random_seed=42)
        s2 = generate_scenarios(n_scenarios=100, random_seed=99)
        assert not np.array_equal(s1.degradation_noise, s2.degradation_noise)


class TestChargingIntegration:
    """Bug #3: Charging engine MUST be used in future simulation."""

    def test_charging_available_improves_feasibility(self):
        from engines.feasibility_engine import compute_probabilistic_fmr
        from models.schemas import FutureTrip

        trip = FutureTrip(id="t1", day="DAY 3", origin="A", destination="B",
                          distance_km=200, priority="NORMAL")

        r_no_charge = compute_probabilistic_fmr(
            40.0, 94.0, [trip], scenario_count=500, random_seed=42,
            charging_availability=0.0)
        r_charge = compute_probabilistic_fmr(
            40.0, 94.0, [trip], scenario_count=500, random_seed=42,
            charging_availability=1.0)

        assert r_charge.fmr <= r_no_charge.fmr, \
            "Charging availability should not increase FMR"

    def test_charging_boundary_zero(self):
        """availability=0 means no charging ever."""
        from engines.uncertainty_engine import generate_scenarios
        s = generate_scenarios(n_scenarios=100, random_seed=42, charging_availability=0.0)
        assert not np.any(s.charger_available), "No charger should be available with p=0"

    def test_charging_boundary_one(self):
        """availability=1 means always available."""
        from engines.uncertainty_engine import generate_scenarios
        s = generate_scenarios(n_scenarios=100, random_seed=42, charging_availability=1.0)
        assert np.all(s.charger_available), "All chargers should be available with p=1"


class TestAblationFlags:
    """Bug #5: Ablation MUST truly disable components."""

    def test_no_energy_uncertainty_deterministic(self):
        from engines.uncertainty_engine import generate_scenarios, AblationFlags
        abl = AblationFlags(use_energy_uncertainty=False)
        s = generate_scenarios(n_scenarios=100, random_seed=42, ablation=abl)
        assert np.all(s.energy_multipliers == 1.0), "Energy should be deterministic"

    def test_no_demand_uncertainty_deterministic(self):
        from engines.uncertainty_engine import generate_scenarios, AblationFlags
        abl = AblationFlags(use_demand_uncertainty=False)
        s = generate_scenarios(n_scenarios=100, random_seed=42, ablation=abl)
        # All values should be the same (the base demand multiplier)
        assert np.all(s.demand_multipliers == s.demand_multipliers[0, 0]), \
            "Demand should be deterministic when disabled"

    def test_no_degradation_uncertainty(self):
        from engines.uncertainty_engine import generate_scenarios, AblationFlags
        abl = AblationFlags(use_degradation_uncertainty=False)
        s = generate_scenarios(n_scenarios=100, random_seed=42, ablation=abl)
        assert np.all(s.degradation_noise == 1.0), "Degradation noise should be 1.0"


class TestCausalMonotonicity:
    """§54: Causal direction checks — verify expected monotonicity."""

    def test_lower_soc_higher_risk(self):
        """Lower initial SOC should not improve feasibility."""
        from engines.feasibility_engine import compute_probabilistic_fmr
        from models.schemas import FutureTrip

        trip = FutureTrip(id="t", day="TOMORROW", origin="A", destination="B",
                          distance_km=100, priority="NORMAL")
        r_low = compute_probabilistic_fmr(30.0, 94.0, [trip], scenario_count=500, random_seed=42)
        r_high = compute_probabilistic_fmr(80.0, 94.0, [trip], scenario_count=500, random_seed=42)
        assert r_low.fmr >= r_high.fmr, "Lower SOC should not reduce FMR"

    def test_lower_soh_higher_risk(self):
        """Lower SOH → less usable capacity → should not improve feasibility."""
        from engines.feasibility_engine import compute_probabilistic_fmr
        from models.schemas import FutureTrip

        trip = FutureTrip(id="t", day="TOMORROW", origin="A", destination="B",
                          distance_km=100, priority="NORMAL")
        r_low = compute_probabilistic_fmr(60.0, 70.0, [trip], scenario_count=500, random_seed=42)
        r_high = compute_probabilistic_fmr(60.0, 100.0, [trip], scenario_count=500, random_seed=42)
        assert r_low.fmr >= r_high.fmr, "Lower SOH should not reduce FMR"

    def test_lower_charging_higher_risk(self):
        """Lower charging availability should not systematically improve feasibility."""
        from engines.feasibility_engine import compute_probabilistic_fmr
        from models.schemas import FutureTrip

        trip = FutureTrip(id="t", day="DAY 3", origin="A", destination="B",
                          distance_km=150, priority="NORMAL")
        r_none = compute_probabilistic_fmr(
            40.0, 94.0, [trip], scenario_count=500, random_seed=42,
            charging_availability=0.0)
        r_full = compute_probabilistic_fmr(
            40.0, 94.0, [trip], scenario_count=500, random_seed=42,
            charging_availability=1.0)
        assert r_none.fmr >= r_full.fmr, \
            "No charging should not reduce FMR vs full charging"

    def test_fmr_plus_fmf_near_100(self):
        """FMR + FMF should approximately equal 100."""
        from engines.feasibility_engine import compute_probabilistic_fmr
        from models.schemas import FutureTrip

        trip = FutureTrip(id="t", day="TOMORROW", origin="A", destination="B",
                          distance_km=100, priority="NORMAL")
        r = compute_probabilistic_fmr(60.0, 94.0, [trip], scenario_count=500, random_seed=42)
        assert abs(r.fmr + r.fmf - 100.0) < 0.1, f"FMR + FMF = {r.fmr + r.fmf}, expected ~100"

    def test_ci_bounds(self):
        """CI lower <= FMR <= CI upper."""
        from engines.feasibility_engine import compute_probabilistic_fmr
        from models.schemas import FutureTrip

        trip = FutureTrip(id="t", day="TOMORROW", origin="A", destination="B",
                          distance_km=100, priority="NORMAL")
        r = compute_probabilistic_fmr(60.0, 94.0, [trip], scenario_count=500, random_seed=42)
        assert r.confidence_interval.lower <= r.fmr <= r.confidence_interval.upper


class TestMultiDayPropagation:
    """Verify cumulative state propagation across days."""

    def test_three_day_cumulative(self):
        """Day 1 → Day 2 → Day 3 state is cumulative."""
        from engines.feasibility_engine import compute_probabilistic_fmr
        from models.schemas import FutureTrip

        t1 = FutureTrip(id="t1", day="TOMORROW", origin="A", destination="B",
                        distance_km=80, priority="NORMAL")
        t2 = FutureTrip(id="t2", day="DAY 3", origin="B", destination="C",
                        distance_km=80, priority="NORMAL")
        t3 = FutureTrip(id="t3", day="DAY 5", origin="C", destination="D",
                        distance_km=80, priority="NORMAL")

        r1 = compute_probabilistic_fmr(60.0, 94.0, [t1], scenario_count=500,
                                       random_seed=42, charging_availability=0.0)
        r3 = compute_probabilistic_fmr(60.0, 94.0, [t1, t2, t3], scenario_count=500,
                                       random_seed=42, charging_availability=0.0)
        assert r3.fmr >= r1.fmr, "Three trips should have >= FMR than one trip"
