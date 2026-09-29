/**
 * futureMobilityService — FMF/FMR computation service.
 *
 * Primary: calls POST /api/consumer/feasibility on the FastAPI backend.
 * Fallback: local computation using same priority-weighted formula.
 */
import type { EVState } from "@/hooks/useEvState";
import type { FutureTrip } from "@/hooks/useFutureTrips";

export type FeasibilityResult = {
  fmf: number;
  fmr: number;
  risk_timeline: number[];
  trip_details: {
    trip_id: string;
    destination: string;
    distance_km: number;
    priority: string;
    soc_required: number;
    soc_available: number;
    margin: number;
    feasible: boolean;
  }[];
  is_computed: boolean;
  // Probabilistic extensions
  total_scenarios?: number;
  successful_scenarios?: number;
  failed_scenarios?: number;
  confidence_interval?: { lower: number; upper: number; level: number };
  random_seed?: number;
};

export type FeasibilityRequest = {
  evState: EVState;
  futureTrips: FutureTrip[];
  soc_after_override?: number;
};

const API_BASE =
  (import.meta as unknown as { env: Record<string, string> }).env?.["VITE_API_URL"] ??
  "http://localhost:8000";

const PRIORITY_W: Record<string, number> = { CRITICAL: 3, HIGH: 2, NORMAL: 1 };

function localFeasibility(req: FeasibilityRequest): FeasibilityResult {
  const soc = req.soc_after_override ?? req.evState.soc;
  const { soh, capacity_kwh } = req.evState;
  const usable = capacity_kwh * (soh / 100);

  let wFeasible = 0;
  let wTotal = 0;
  const details = req.futureTrips.map((trip, i) => {
    // Project SOC forward for future trips
    const projSoc = i === 0 ? soc : Math.max(0, soc * Math.pow(0.91, i));
    const energyNeeded = trip.distance_km / 6.0;
    const socRequired = +Math.min(95, (energyNeeded / usable) * 100 + 10).toFixed(1);
    const margin = +(projSoc - socRequired).toFixed(1);
    const feasible = margin >= 0;
    const w = PRIORITY_W[trip.priority] ?? 1;
    wTotal += w;
    if (feasible) wFeasible += w;
    return {
      trip_id: trip.id,
      destination: trip.destination,
      distance_km: trip.distance_km,
      priority: trip.priority,
      soc_required: socRequired,
      soc_available: +projSoc.toFixed(1),
      margin,
      feasible,
    };
  });

  const fmf = wTotal > 0 ? +((wFeasible / wTotal) * 100).toFixed(1) : 99.0;
  const fmr = +(100 - fmf).toFixed(1);

  return { fmf, fmr, risk_timeline: [] as number[], trip_details: details, is_computed: false };
}

export const futureMobilityService = {
  // Legacy getter kept for backward compatibility
  getTrips: () => [],

  label: (score: number): string => (score >= 90 ? "FEASIBLE" : score >= 70 ? "WATCH" : "AT RISK"),

  async getFeasibility(req: FeasibilityRequest): Promise<FeasibilityResult> {
    try {
      const res = await fetch(`${API_BASE}/api/consumer/feasibility`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(req),
        signal: AbortSignal.timeout(8000),
      });
      if (!res.ok) throw new Error(`API ${res.status}`);
      return (await res.json()) as FeasibilityResult;
    } catch {
      return localFeasibility(req);
    }
  },
};
