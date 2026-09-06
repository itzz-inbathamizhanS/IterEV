# Future-Mobility-Aware EV Decision System — Task Tracker

## Phase 1A — Backend Foundation
- [x] requirements.txt
- [x] main.py (FastAPI + CORS)
- [x] models/__init__.py
- [x] models/schemas.py (Pydantic v2)
- [x] models/constants.py
- [x] engines/__init__.py
- [x] engines/energy_engine.py
- [x] engines/battery_engine.py
- [x] engines/feasibility_engine.py
- [x] engines/optimizer.py
- [x] engines/explanation_engine.py
- [x] api/__init__.py
- [x] api/consumer.py
- [x] api/fleet.py (stub)
- [x] api/simulation.py

## Phase 1B — Frontend Hooks & Services
- [x] src/hooks/useEvState.ts (NEW)
- [x] src/hooks/useFutureTrips.ts (NEW)
- [x] .env.local (API URL)
- [x] src/services/routeService.ts (wired to API + local fallback)
- [x] src/services/futureMobilityService.ts (wired to API)
- [x] src/services/simulationService.ts (API + existing formula fallback)

## Phase 1C — Frontend Wiring (Pages.tsx)
- [x] ConsumerPage: EVState inputs + useQuery routes + computed BatteryMemory + DecisionTrace
- [x] FuturePage: useFutureTrips + wired Add Trip form + computed FMF display
- [ ] RiskPage: wire risk timeline to computed values
- [ ] SimulationPage: replace static table with API comparison

## Phase 2 — Fleet Flow
- [ ] engines/fleet_state_engine.py
- [ ] engines/demand_engine.py
- [ ] engines/fleet_feasibility_engine.py
- [ ] engines/fleet_optimizer.py
- [ ] api/fleet.py (full implementation)
- [ ] FleetPage frontend wiring

## Phase 3 — Simulation Engine
- [ ] Real baseline comparisons (Fastest, Energy-Aware, Battery-Aware, Proposed)
- [ ] Multi-scenario sweep
- [ ] Ablation studies
- [ ] SimulationPage full wiring
