/**
 * simulationService — Simulation engine service.
 *
 * Primary: calls POST /api/simulation/run on the FastAPI backend.
 *   Returns real baseline comparisons (FASTEST, ENERGY AWARE, BATTERY AWARE, PROPOSED)
 *   all computed with the same physical engines — fair comparison.
 *
 * Fallback: the original deterministic formula (kept as offline fallback).
 *   Clearly labelled as approximation, not the research-paper formula.
 */

export type SimulationInput = {
  mode: "Consumer" | "Fleet";
  horizon: number;
  soh: number;
  temperature: number;
  traffic: "Low" | "Medium" | "High";
  demand: "Low" | "Medium" | "High";
  charging: "Normal" | "Restricted";
  uncertainty: "Low" | "Medium" | "High";
  scenario_count?: number;
  random_seed?: number;
  charging_availability?: number;
  soc_initial?: number;
};

export type SimulationOutput = {
  feasibility: number;
  risk: number;
  energy: number;
  travelTime: number;
  riskRange: number;
  fmr_ci_lower?: number;
  fmr_ci_upper?: number;
  total_scenarios?: number;
  soh_loss?: number;
};

export type MethodComparisonRow = {
  method: string;
  travelTime: number;
  energy: number;
  feasibility: number;
  risk: number;
  soh_loss?: number;
  future_success_rate?: number;
  constraint_violations?: number;
};

export type SimulationResult = {
  primary: SimulationOutput;
  comparison: MethodComparisonRow[];
  is_computed: boolean;
  random_seed?: number;
  scenario_count?: number;
};

const API_BASE =
  (import.meta as unknown as { env: Record<string, string> }).env?.VITE_API_URL ??
  "http://localhost:8000";

const LEVEL: Record<string, number> = { Low: 0, Medium: 1, High: 2 };

/** Original local formula — kept as offline fallback only */
function localFallback(input: SimulationInput): SimulationResult {
  const heat = Math.max(0, input.temperature - 25);
  const demandPenalty = LEVEL[input.demand]! * (input.mode === "Fleet" ? 4.2 : 2.4);
  const trafficPenalty = LEVEL[input.traffic]! * 1.8;
  const chargePenalty = input.charging === "Restricted" ? 5.6 : 0;
  const horizonPenalty = Math.max(0, input.horizon - 1) * 0.55;
  const healthGain = (input.soh - 60) * 0.3;
  const uncertaintyPenalty = LEVEL[input.uncertainty]! * 2.1;
  const feasibility = Math.max(
    42,
    Math.min(
      99.4,
      79 +
        healthGain -
        heat * 0.22 -
        demandPenalty -
        trafficPenalty -
        chargePenalty -
        horizonPenalty -
        uncertaintyPenalty,
    ),
  );
  const primary: SimulationOutput = {
    feasibility: +feasibility.toFixed(1),
    risk: +(100 - feasibility).toFixed(1),
    energy: +(27.8 + heat * 0.18 + LEVEL[input.traffic]! * 2.1 + input.horizon * 0.35).toFixed(1),
    travelTime: Math.round(44 + LEVEL[input.traffic]! * 7 + (input.mode === "Fleet" ? 3 : 0)),
    riskRange: 1.2 + LEVEL[input.uncertainty]! * 2.3,
  };
  // Approximate baseline comparison (local only, clearly demo)
  const comparison: MethodComparisonRow[] = [
    { method: "FASTEST", travelTime: 42, energy: 14.8, feasibility: 81.8, risk: 18.2 },
    { method: "ENERGY AWARE", travelTime: 51, energy: 12.9, feasibility: 91.2, risk: 8.8 },
    { method: "BATTERY AWARE", travelTime: 55, energy: 13.2, feasibility: 95.1, risk: 4.9 },
    {
      method: "PROPOSED",
      travelTime: primary.travelTime,
      energy: primary.energy,
      feasibility: primary.feasibility,
      risk: primary.risk,
    },
  ];
  return { primary, comparison, is_computed: false };
}

export const simulationService = {
  async run(input: SimulationInput): Promise<SimulationResult> {
    try {
      const res = await fetch(`${API_BASE}/api/simulation/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(input),
        signal: AbortSignal.timeout(10_000),
      });
      if (!res.ok) throw new Error(`API ${res.status}`);
      return (await res.json()) as SimulationResult;
    } catch {
      return localFallback(input);
    }
  },
};
