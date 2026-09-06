# Future-Mobility-Aware EV Decision System — Full Implementation Plan

> Research PDF + Lovable Frontend → Complete Backend + Integration Plan

---

## 1. Existing Frontend Architecture

### Framework & Stack
| Layer | Technology |
|-------|-----------|
| Framework | **TanStack Start** (React 19 + SSR via Nitro/Cloudflare) |
| Router | **TanStack Router** (file-based, type-safe) |
| Styling | **Tailwind CSS v4** |
| UI Components | **Radix UI** (shadcn/ui) |
| Charts | **Recharts** (imported, not yet used in pages) |
| Icons | **Lucide React** |
| State | Local React `useState` only — no global store |
| HTTP | **TanStack Query** installed, but **no API calls made** |
| Build | Vite 8 + `@lovable.dev/vite-tanstack-config` |
| Runtime | Node.js + Nitro (SSR-capable) |

### Folder Structure
```
src/
├── routes/               # TanStack file-based routes
│   ├── __root.tsx        # Root layout + QueryClientProvider
│   ├── index.tsx         # / → HomePage
│   ├── consumer.tsx      # /consumer → ConsumerPage
│   ├── future.tsx        # /future → FuturePage
│   ├── fleet.tsx         # /fleet → FleetPage
│   ├── risk.tsx          # /risk → RiskPage
│   ├── simulation.tsx    # /simulation → SimulationPage
│   ├── research.tsx      # /research → ResearchPage
│   └── system.tsx        # /system → SystemPage
├── components/
│   └── future-mobility/
│       ├── Pages.tsx     # ALL page components (single file, ~700 lines)
│       ├── SiteShell.tsx # Nav + footer wrapper
│       └── Visuals.tsx   # Reusable visual components
├── data/                 # Hardcoded mock JSON
│   ├── routes.json       # 3 route options
│   ├── vehicles.json     # 6 fleet vehicles
│   ├── futureTrips.json  # 4 future trips
│   ├── futureDemand.json # 1 demand snapshot
│   ├── riskScenarios.json# 5 risk scenarios
│   ├── simulationResults.json # 4 method comparison rows
│   └── researchResults.json   # Equations + research years
├── services/             # Service stubs (all return hardcoded data)
│   ├── batteryService.ts
│   ├── fleetService.ts
│   ├── futureMobilityService.ts
│   ├── routeService.ts
│   ├── simulationService.ts   # Only file with real logic
│   └── vehicleService.ts
└── hooks/
    └── use-mobile.tsx
```

### All 8 Pages
| Route | Component | Status |
|-------|-----------|--------|
| `/` | `HomePage` | ✅ Complete UI |
| `/consumer` | `ConsumerPage` | ✅ UI, ❌ No real computation |
| `/future` | `FuturePage` | ✅ UI, ❌ Hardcoded values |
| `/fleet` | `FleetPage` | ✅ UI, ❌ Hardcoded values |
| `/risk` | `RiskPage` | ✅ UI, ❌ Hardcoded values |
| `/simulation` | `SimulationPage` | ✅ UI + mock logic |
| `/research` | `ResearchPage` | ✅ UI, ❌ Static content only |
| `/system` | `SystemPage` | ✅ UI, static |

### Reusable Visual Components (Visuals.tsx)
| Component | Purpose |
|-----------|---------|
| `Eyebrow` | Small caps label |
| `PageTitle` | Large display heading |
| `DemoLabel` | "SIMULATION EXAMPLE" badge |
| `MobilityThread` | Animated today→future line |
| `BatteryMemory` | Current → After → Tomorrow battery bars |
| `CapacityArc` | SVG ring showing future capacity |
| `VehicleSilhouette` | Minimal EV SVG |
| `DecisionTrace` | 5-column decision reason strip |
| `NodeDiagram` | Interactive architecture node list |

---

## 2. Existing Functionality (What Currently Works)

### ConsumerPage
- Displays hardcoded EV state: **SOC 78%, SOH 94%, 342 km, 29°C**
- Shows static SVG route map (Coimbatore → Ooty, 88 km)
- Route selector toggles between 3 hardcoded routes
- `BatteryMemory` shows animated battery bars per selected route
- `DecisionTrace` shows hardcoded "Why this decision?" explanation
- Route table shows time/cost/energy/feasibility — **all from `routes.json`**

### FuturePage
- Shows 4 hardcoded future trips from `futureTrips.json`
- "Add Trip" button reveals a form with inputs (no submission logic)
- FMF score is **hardcoded 97.4%**
- Risk dots are **hardcoded [2.1, 3.4, 4.1, 3.0, 2.6]**

### FleetPage
- Spatial vehicle map with clickable silhouettes
- Vehicle detail panel from `vehicles.json`
- Future demand from `futureDemand.json` — hardcoded
- Fleet stats (24/18/4/2) — all hardcoded

### RiskPage
- Risk score **hardcoded 2.6%**
- Timeline **hardcoded [2.1, 3.4, 4.1, 3.0, 2.6]**
- Scenario matrix from `riskScenarios.json`
- Decision comparison (42 min → 48 min) **hardcoded**

### SimulationPage
- **Only page with real computation** via `simulationService.ts`
- 8 parameter controls (mode, horizon, SOH, temp, traffic, demand, charging, uncertainty)
- Deterministic formula: `feasibility = 79 + healthGain - heatPenalty - demandPenalty - trafficPenalty - chargePenalty - horizonPenalty - uncertaintyPenalty`
- Animated progress stages (frontend only, 300ms per step)
- Method comparison table from `simulationResults.json` — **static**

### What is truly wired:
- Navigation between all 8 pages ✅
- Route selection changing `BatteryMemory` display ✅
- Simulation parameter controls changing outputs ✅
- "Add Trip" form appears/disappears ✅

---

## 3. Missing Functionality (Gap Analysis)

### Consumer Flow — Missing
| Step | Frontend State | Missing Backend |
|------|---------------|-----------------|
| **User enters EV state** | Hardcoded (78%, SOH 94%) | Input form → state capture |
| **User enters destination** | Hardcoded (Ooty) | Origin/destination input → geocoding |
| **Route generation** | 3 static routes from JSON | Real candidate route generation |
| **Energy prediction** | Hardcoded kWh values | Energy model: distance × efficiency × traffic × temp × gradient |
| **Battery consequence** | `batteryService` exists but unused in UI | Wire service: SOC_after = f(SOC, energy, SOH) |
| **Future trips** | Hardcoded JSON, add-form not wired | Store future trips in state/context |
| **FMF calculation** | Hardcoded 97.4% | Per-route FMF: P(all future trips feasible given battery_after) |
| **FMR calculation** | Hardcoded 2.6% | FMR = 1 - FMF |
| **Route recommendation** | Hardcoded `recommended:true` in JSON | Optimizer: select route minimizing J(a) |
| **Decision explanation** | Hardcoded text | Dynamic explanation from optimizer output |
| **Risk timeline** | Hardcoded [2.1...2.6] | Multi-day risk projection per route choice |

### Fleet Flow — Missing
| Step | Frontend State | Missing Backend |
|------|---------------|-----------------|
| **Fleet state** | 6 hardcoded vehicles | Dynamic vehicle state engine |
| **Task manager** | Not present | Current task list with priorities |
| **Future demand** | 1 hardcoded snapshot | Demand forecast engine |
| **Battery consequence per vehicle** | Not computed | Per-vehicle assignment cost |
| **Future fleet capacity** | Per-vehicle `capacity` field is static | Real fleet FMF/FMR across all vehicles |
| **Vehicle assignment optimizer** | Not present | Match vehicles to tasks, protect vulnerable ones |
| **Charging planner** | Not present | Which vehicles to charge now vs. later |

### Simulation Flow — Missing
| Step | Frontend State | Missing Backend |
|------|---------------|-----------------|
| **Method comparison** | Static JSON table | Real baseline computations |
| **Actual research baselines** | Fictional numbers | Fastest, Energy-Aware, Battery-Aware, Proposed |
| **Scenario sweep** | Single run | Multi-scenario evaluation |
| **Ablation results** | Not present | Sensitivity analysis outputs |

---

## 4. Required Backend Architecture

```
Backend/
├── api/                     # FastAPI HTTP layer
│   ├── consumer.py          # Consumer endpoints
│   ├── fleet.py             # Fleet endpoints
│   └── simulation.py        # Simulation endpoints
├── engines/
│   ├── state_engine.py      # Current vehicle/fleet state capture
│   ├── energy_engine.py     # Route energy prediction
│   ├── battery_engine.py    # SoC/SoH/degradation state transition
│   ├── future_state_engine.py # Project future state distribution
│   ├── future_demand_engine.py # Consumer trips + fleet task demand
│   ├── feasibility_engine.py   # FMF/FMR calculation
│   └── optimizer.py            # Multi-objective decision optimizer
├── models/
│   ├── schemas.py           # Pydantic data models
│   └── constants.py         # Physics constants, defaults
├── data/
│   ├── demo/                # Clearly labelled demo scenarios
│   └── results/             # Experiment outputs
└── main.py                  # FastAPI app entry point
```

**Technology stack (from research document, Section 20):**
- Python + FastAPI (API layer)
- NetworkX / A* (route graph)
- Pyomo or linear programming (optimizer)
- NumPy (deterministic physics models)
- Pandas (scenario management)
- Monte Carlo simulation (uncertainty)

---

## 5. Required APIs

### Consumer APIs
```
POST /api/consumer/routes
  Body: { evState: EVState, origin: Location, destination: Location, futureTrips: FutureTrip[] }
  Returns: RouteCandidate[] with energy, time, cost, battery_after, FMF, FMR per route

POST /api/consumer/decide
  Body: { routes: RouteCandidate[], userPreference: "fastest"|"future_ready"|"battery_care" }
  Returns: { recommended: RouteCandidate, explanation: DecisionExplanation }

POST /api/consumer/future-feasibility
  Body: { battery_after: number, soh: number, futureTrips: FutureTrip[] }
  Returns: { fmf: number, fmr: number, risk_timeline: number[], per_trip_feasibility: TripFeasibility[] }
```

### Fleet APIs
```
GET  /api/fleet/state
  Returns: Vehicle[] with SoC, SoH, temp, location, status, range, future_capacity

POST /api/fleet/assign
  Body: { vehicles: Vehicle[], tasks: Task[], futureDemand: DemandForecast }
  Returns: Assignment[] with vehicle_id, task_id, risk, explanation

POST /api/fleet/feasibility
  Body: { assignments: Assignment[], futureDemand: DemandForecast }
  Returns: { fleet_fmf: number, fleet_fmr: number, at_risk_vehicles: string[] }
```

### Simulation APIs
```
POST /api/simulation/run
  Body: SimulationInput (same as current frontend type)
  Returns: SimulationOutput with all 4 method comparison rows computed

POST /api/simulation/scenario-sweep
  Body: { parameters: SimulationInput, sweep_variable: string, sweep_range: number[] }
  Returns: SweepResult[]
```

---

## 6. Required Data Models

```typescript
// Vehicle state
type EVState = {
  vehicle_id: string;
  soc: number;          // State of Charge 0–100%
  soh: number;          // State of Health 0–100%
  temperature: number;  // Battery temperature °C
  capacity_kwh: number; // Usable capacity kWh
  efficiency: number;   // km/kWh at baseline
  location: [number, number]; // lat, lng
}

// Route candidate (generated, not hardcoded)
type RouteCandidate = {
  route_id: string;
  name: string;          // "FASTEST" | "FUTURE READY" | "BATTERY CARE"
  distance_km: number;
  time_min: number;
  cost_inr: number;
  energy_kwh: number;    // COMPUTED from energy engine
  soc_after: number;     // COMPUTED from battery engine
  soc_tomorrow: number;  // PROJECTED future state
  fmf: number;           // COMPUTED from feasibility engine
  fmr: number;           // = 1 - fmf (as probability)
  recommended: boolean;  // SET by optimizer
}

// Future trip requirement
type FutureTrip = {
  id: string;
  day: string;
  origin: string;
  destination: string;
  distance_km: number;
  priority: "NORMAL" | "HIGH" | "CRITICAL";
  required_soc_start: number; // minimum SOC needed
  deadline_hours: number;
}

// FMF/FMR result
type FeasibilityResult = {
  fmf: number;             // 0–1 probability
  fmr: number;             // 0–1 probability
  risk_timeline: number[]; // daily FMR across horizon
  per_trip_feasibility: {
    trip_id: string;
    feasible: boolean;
    soc_available: number;
    soc_required: number;
    margin: number;
  }[];
}

// Decision explanation
type DecisionExplanation = {
  chosen_route: string;
  reason: string;          // Human-readable sentence
  battery_effect: string;  // e.g., "61% after today"
  future_effect: string;   // e.g., "97.4% feasible"
  risk_change: string;     // e.g., "−15.6 points vs fastest"
  trade_off: string;       // e.g., "+6 min, −15.6% risk"
}

// Fleet vehicle
type Vehicle = {
  id: string;
  soc: number;
  soh: number;
  temp: number;
  capacity: number;      // Future capacity %
  status: "ACTIVE" | "CHARGING" | "AVAILABLE" | "PROTECT";
  location: [number, number];
  range_km: number;
}

// Simulation input (already exists in frontend — keep identical)
type SimulationInput = {
  mode: "Consumer" | "Fleet";
  horizon: number;
  soh: number;
  temperature: number;
  traffic: "Low" | "Medium" | "High";
  demand: "Low" | "Medium" | "High";
  charging: "Normal" | "Restricted";
  uncertainty: "Low" | "Medium" | "High";
}
```

---

## 7. Required Research-Engine Modules

### Module 1: Energy Engine
**Inputs:** distance, speed/traffic, gradient, temperature, vehicle efficiency  
**Formula (deterministic, from research physics):**
```python
def predict_energy(distance_km, traffic, temperature, gradient=0, efficiency=6.0):
    # Base energy
    base = distance_km / efficiency
    # Traffic penalty (stop-go increases consumption)
    traffic_factor = {"Low": 1.0, "Medium": 1.15, "High": 1.35}[traffic]
    # Temperature penalty (battery chemistry)
    temp_penalty = max(0, (temperature - 25) * 0.008)  # +0.8% per °C above 25
    # Gradient (uphill consumes more)
    gradient_factor = 1.0 + (gradient * 0.015)
    return base * traffic_factor * (1 + temp_penalty) * gradient_factor
```

### Module 2: Battery State Transition Engine
**Inputs:** initial SOC, energy consumed, SOH  
**Formula:**
```python
def battery_transition(soc_initial, energy_kwh, soh, capacity_kwh=40):
    # Usable capacity = nominal × SOH
    usable = capacity_kwh * (soh / 100)
    # Charge consumed as % of usable
    delta_soc = (energy_kwh / usable) * 100
    soc_after = max(0, soc_initial - delta_soc)
    return round(soc_after, 1)
```

### Module 3: Future State Projection Engine
**Inputs:** soc_after, soh, horizon_days, daily_distance  
**Purpose:** project battery state forward across planning horizon  
**Method:** deterministic baseline + uncertainty bands  
```python
def project_future_state(soc_after, soh, horizon_days, uncertainty="Low"):
    uncertainty_factor = {"Low": 0.02, "Medium": 0.05, "High": 0.10}[uncertainty]
    projections = []
    soc = soc_after
    for day in range(horizon_days):
        # Natural self-discharge + modeled recovery (if charged)
        projections.append({
            "day": day,
            "soc_expected": soc,
            "soc_low": soc * (1 - uncertainty_factor),
            "soc_high": min(100, soc * (1 + uncertainty_factor * 0.5))
        })
    return projections
```

### Module 4: Future Mobility Feasibility (FMF) Engine
**Core research contribution — from research document Section 13**  
**Formula:**
```
FMF(a) = P[I_future(a, ω) = 1]
       = P[all future trips can be completed given battery state after action a]
```
**Implementation:**
```python
def calculate_fmf(soc_after, soh, future_trips, capacity_kwh=40):
    feasible_count = 0
    total = len(future_trips)
    for trip in future_trips:
        energy_required = trip.distance_km / 6.0  # base efficiency
        soc_required = (energy_required / (capacity_kwh * soh/100)) * 100
        min_soc_needed = soc_required + 10  # 10% safety buffer
        if soc_after >= min_soc_needed:
            feasible_count += 1
    fmf = feasible_count / total if total > 0 else 1.0
    return round(fmf * 100, 1)  # return as percentage

def calculate_fmr(fmf_percent):
    return round(100 - fmf_percent, 1)
```

### Module 5: Decision Optimizer
**From research document Section 18:**  
```
min J(a) = CurrentCost(a) + λ·BatteryConsequence(a) + µ·FMR(a)
subject to: FMR(a) ≤ ε
```
**Deterministic implementation (Phase 1 — no ML):**
```python
def optimize(routes, lambda_battery=0.3, mu_fmr=0.5, epsilon=0.10):
    scored = []
    for route in routes:
        current_cost = normalize(route.time_min, route.cost_inr)
        battery_cost = normalize_battery(route.soc_after)
        fmr_cost = route.fmr / 100  # normalize 0-1
        J = current_cost + lambda_battery * battery_cost + mu_fmr * fmr_cost
        scored.append((J, route))
    best = min(scored, key=lambda x: x[0])
    return best[1]
```

### Module 6: Explanation Engine
**Generates the "Why this decision?" text shown in ConsumerPage**
```python
def explain(chosen, alternatives):
    fastest = min(alternatives, key=lambda r: r.time_min)
    time_diff = chosen.time_min - fastest.time_min
    risk_diff = fastest.fmr - chosen.fmr
    return {
        "reason": f"Route {chosen.name} takes {time_diff} additional minutes "
                  f"but reduces future mobility risk by {risk_diff:.1f} percentage points.",
        "battery_effect": f"{chosen.soc_after}% after today",
        "future_effect": f"{chosen.fmf}% feasible",
        "risk_change": f"−{risk_diff:.1f} points vs fastest",
        "trade_off": f"+{time_diff} min, −{risk_diff:.1f}% risk"
    }
```

---

## 8. Frontend-to-Backend Integration Plan

### Principle: Preserve All Existing UI — Only wire services

The existing service files already provide the correct abstraction layer. The integration replaces their internal implementations from JSON imports to API calls — **without changing any component code**.

### Phase 1: Consumer Flow Integration

**Step 1: Add EV State input form to ConsumerPage**  
Currently SOC=78%, SOH=94% are hardcoded display values.  
Add: a collapsible input section at the top of ConsumerPage using existing shadcn `Input`, `Slider` components.  
State: `useState<EVState>` for user's current vehicle state.

**Step 2: Add destination input**  
The `RouteMap` SVG currently hardcodes Coimbatore → Ooty.  
Add: two text inputs for origin/destination above the map.  
State: `useState<{origin: string, destination: string}>`.

**Step 3: Wire "Add Trip" form**  
Currently the add-trip form appears but submissions are ignored.  
Add: `useState<FutureTrip[]>` in FuturePage (or shared context).  
On submit → append to trip list → re-trigger feasibility calc.

**Step 4: Wire `routeService` to API**
```typescript
// BEFORE (current)
import routes from "@/data/routes.json";
export const routeService = { getOptions: () => routes };

// AFTER (Phase 1)
export const routeService = {
  getOptions: async (evState: EVState, origin: string, dest: string, trips: FutureTrip[]) => {
    const res = await fetch("/api/consumer/routes", {
      method: "POST",
      body: JSON.stringify({ evState, origin, destination: dest, futureTrips: trips })
    });
    return res.json() as Promise<RouteCandidate[]>;
  }
};
```

**Step 5: Wire `futureMobilityService` to API**
```typescript
// AFTER
export const futureMobilityService = {
  getFeasibility: async (batteryAfter: number, soh: number, trips: FutureTrip[]) => {
    const res = await fetch("/api/consumer/future-feasibility", { ... });
    return res.json() as Promise<FeasibilityResult>;
  }
};
```

**Step 6: Wire `simulationService` to API**
```typescript
// AFTER — keep local formula as fallback, prefer API
export const simulationService = {
  run: async (input: SimulationInput): Promise<SimulationOutput> => {
    try {
      const res = await fetch("/api/simulation/run", { method: "POST", body: JSON.stringify(input) });
      return res.json();
    } catch {
      return localFallback(input); // keep existing formula as offline fallback
    }
  }
};
```

### State Management Strategy
Use **TanStack Query** (already installed) for server state:
```typescript
// In ConsumerPage
const { data: routes, isLoading } = useQuery({
  queryKey: ["routes", evState, origin, destination, futureTrips],
  queryFn: () => routeService.getOptions(evState, origin, destination, futureTrips),
  enabled: !!(origin && destination)
});
```

### Loading States
The frontend already has a `running` state and progress animation in SimulationPage.  
Reuse same pattern for Consumer flow:
- Show existing `DemoLabel` → replace with live badge "COMPUTING" during API call
- On result → show "LIVE RESULT" badge instead of "SIMULATION EXAMPLE"

---

## 9. Recommended Development Order

### Phase 1 — Consumer Flow (implement first, end-to-end)

#### Sprint 1A: Backend Foundation (Python/FastAPI)
- [ ] Create `Backend/` folder alongside `Frontend/`
- [ ] `main.py` — FastAPI app
- [ ] `models/schemas.py` — all Pydantic models
- [ ] `engines/energy_engine.py` — deterministic energy prediction
- [ ] `engines/battery_engine.py` — SOC/SOH state transition
- [ ] `POST /api/consumer/routes` — generate 3 candidate routes with real energy/battery values

#### Sprint 1B: Feasibility Engine
- [ ] `engines/feasibility_engine.py` — FMF/FMR per route
- [ ] `engines/optimizer.py` — J(a) minimization, set `recommended` flag
- [ ] `engines/explanation_engine.py` — generate reason text
- [ ] `POST /api/consumer/decide` — returns recommended route + explanation
- [ ] `POST /api/consumer/future-feasibility` — FMF timeline

#### Sprint 1C: Frontend Wiring (Consumer)
- [ ] Add `EVState` input form to ConsumerPage (hidden by default, expand on click)
- [ ] Add origin/destination text inputs above RouteMap
- [ ] Wire `routeService` to API — routes now computed, not hardcoded
- [ ] Wire feasibility scores into route table (replace JSON values with API values)
- [ ] Wire `BatteryMemory` to show computed `soc_after` / `soc_tomorrow`
- [ ] Wire `DecisionTrace` to show API explanation text
- [ ] Wire FuturePage "Add Trip" form → store trips → re-run feasibility
- [ ] Wire FuturePage FMF/FMR display to API result
- [ ] Wire RiskPage risk timeline to API computed values
- [ ] Mark computed results with "LIVE RESULT" badge (vs "SIMULATION EXAMPLE")

#### Sprint 1D: Verification
- [ ] Run frontend + backend together
- [ ] Test: change SOH slider → routes recompute → FMF changes → explanation updates
- [ ] Verify: deterministic — same inputs = same outputs always
- [ ] Verify: "Add Trip" adds a CRITICAL trip → risk increases → different route recommended

---

### Phase 2 — Fleet Flow

#### Sprint 2A: Fleet Backend
- [ ] `engines/fleet_state_engine.py` — vehicle health scoring
- [ ] `engines/demand_engine.py` — future demand modeling
- [ ] `engines/fleet_feasibility_engine.py` — fleet-level FMF/FMR
- [ ] `engines/fleet_optimizer.py` — vehicle-to-task assignment
- [ ] `GET /api/fleet/state`
- [ ] `POST /api/fleet/assign`
- [ ] `POST /api/fleet/feasibility`

#### Sprint 2B: Frontend Wiring (Fleet)
- [ ] Wire fleet stats (24/18/4/2) to real vehicle counts from API
- [ ] Wire vehicle detail panel to computed future_capacity
- [ ] Wire future demand section to API demand forecast
- [ ] Add "PROTECT" recommendation for vulnerable vehicles (wire to optimizer)
- [ ] Wire fleet FMF/FMR display

---

### Phase 3 — Simulation Engine

#### Sprint 3A: Real Baseline Computations
- [ ] Implement all 4 baselines (Fastest, Energy-Aware, Battery-Aware, Proposed)
- [ ] Run deterministic scenario sweep across all 8 parameters
- [ ] `POST /api/simulation/run` returns real baseline comparison table
- [ ] Replace static `simulationResults.json` with API-computed results

#### Sprint 3B: Advanced Scenarios
- [ ] Multi-scenario sweep (change one variable, hold others fixed)
- [ ] Ablation study: remove FMR term → show degraded results
- [ ] Results export for research paper

---

## Research Document ↔ Frontend Mapping

| Research Module (PDF §12) | Frontend Location | Backend Engine |
|--------------------------|-------------------|----------------|
| Current-state engine | ConsumerPage SOC/SOH display | `state_engine.py` |
| Consequence engine | `batteryService.ts` (stub) | `battery_engine.py` |
| Future-state engine | FuturePage (hardcoded) | `future_state_engine.py` |
| Future-demand engine | FuturePage trips list | `future_demand_engine.py` |
| Decision engine | SimulationPage controls | `optimizer.py` |
| FMF/FMR engine | FuturePage 97.4% (hardcoded) | `feasibility_engine.py` |
| Explanation engine | ConsumerPage "Why?" section | `explanation_engine.py` |
| Feedback loop | Not present | `feedback_engine.py` (Phase 3) |

---

## Consumer End-to-End Flow (Target)

```
User enters:
  EVState { SOC: 78%, SOH: 94%, temp: 29°C }
  Origin: Coimbatore | Destination: Ooty (88 km)
  Future Trips: [Chennai 500km tomorrow (CRITICAL), Bangalore 330km Day5]

→ Backend generates 3 candidate routes:
    FASTEST:      42 min, ₹185, 14.8 kWh → SOC_after=58% → FMF=81.2% → FMR=18.8%
    FUTURE READY: 48 min, ₹172, 13.9 kWh → SOC_after=61% → FMF=97.4% → FMR=2.6%
    BATTERY CARE: 53 min, ₹160, 13.1 kWh → SOC_after=64% → FMF=99.0% → FMR=1.0%

→ Optimizer runs J(a) = time_cost + 0.3·battery_cost + 0.5·FMR
    FASTEST:      J = 0.0 + 0.3·0.42 + 0.5·0.188 = 0.220
    FUTURE READY: J = 0.1 + 0.3·0.39 + 0.5·0.026 = 0.230 ← lowest weighted
    BATTERY CARE: J = 0.2 + 0.3·0.36 + 0.5·0.010 = 0.313

→ FUTURE READY selected as RECOMMENDED

→ Explanation:
    "Route FUTURE READY takes 6 additional minutes but reduces future mobility
    risk by 16.2 points. Your CRITICAL Chennai trip tomorrow requires ~58% SOC.
    FASTEST leaves you at 58% — at the margin. FUTURE READY leaves 61%, giving
    you a 3% buffer for the Chennai journey."

→ Frontend displays:
    - Route table with LIVE calculated values (not JSON)
    - BatteryMemory: 78% → 61% → (projected) 57%
    - DecisionTrace: populated with real explanation
    - FuturePage FMF: 97.4% (computed, not hardcoded)
    - RiskPage risk_timeline: [2.6, 3.1, 4.2, 8.4, 12.6] for FASTEST
                              [1.0, 1.4, 2.1, 3.0, 2.6] for FUTURE READY
```

---

## Important Guardrails (From Research Document)

> [!IMPORTANT]
> All computed results that are NOT from real experiments must display the existing `DemoLabel` ("SIMULATION EXAMPLE"). Only replace it with "LIVE RESULT" when the value is actually computed from user inputs.

> [!WARNING]
> Do NOT fabricate percentages. The FMF/FMR numbers must come from the deterministic formula chain: energy_engine → battery_engine → feasibility_engine. If a value cannot be computed, show the original hardcoded demo value clearly labelled.

> [!NOTE]
> The research document (§14) says λ, µ, ε must NOT be chosen arbitrarily and claimed as universally correct. For Phase 1, expose them as configurable parameters in the Simulation page, with documented defaults.

> [!CAUTION]
> The `simulationService.ts` formula that currently exists is a good **approximation** but is not the research-paper formula. Keep it as the **offline fallback**. The backend must implement the proper 5-engine chain from §12 of the research document.

---

## File Creation Order (Execution)

```
Phase 1A — Create these files first:
  Backend/
    main.py
    models/schemas.py
    models/constants.py
    engines/energy_engine.py
    engines/battery_engine.py
    engines/feasibility_engine.py
    engines/optimizer.py
    engines/explanation_engine.py
    api/consumer.py
    requirements.txt

Phase 1B — Modify these frontend files (minimally):
  src/services/routeService.ts      → add async API call
  src/services/batteryService.ts    → wire to backend
  src/services/futureMobilityService.ts → wire to backend
  src/services/simulationService.ts → add API call with local fallback

Phase 1C — Modify one section of Pages.tsx:
  ConsumerPage → add EVState inputs + destination inputs + wire API
  FuturePage   → wire Add Trip form + show computed FMF
  RiskPage     → show computed risk timeline
  SimulationPage → wire to backend, replace static table
```
