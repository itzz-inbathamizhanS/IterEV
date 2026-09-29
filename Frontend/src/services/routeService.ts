/**
 * routeService — Consumer route generation service.
 *
 * Primary: calls POST /api/consumer/routes on the FastAPI backend.
 * Fallback: runs local deterministic computation if API is unavailable.
 *
 * The fallback uses the same formulas as the backend engines so results
 * are physically consistent. Both paths clearly set `is_computed`.
 */
import type { EVState } from "@/hooks/useEvState";
import type { FutureTrip } from "@/hooks/useFutureTrips";

export type RouteCandidate = {
  id: string;
  name: string;
  time: number; // minutes
  cost: number; // INR
  energy: number; // kWh (computed)
  feasibility: number; // FMF % (computed)
  fmr: number; // Future Mobility Risk %
  after: number; // SOC after trip (computed)
  tomorrow: number; // Projected SOC next day (computed)
  recommended: boolean;
  explanation?: string;
  risk_change?: string;
  fmr_ci_lower?: number;
  fmr_ci_upper?: number;
  total_scenarios?: number;
  constraint_relaxed?: boolean;
  is_computed: boolean; // true = from engine; false = demo fallback
};

export type ConsumerRoutesRequest = {
  evState: EVState;
  origin: string;
  destination: string;
  distance_km: number;
  traffic: "Low" | "Medium" | "High";
  futureTrips: FutureTrip[];
};

const API_BASE =
  (import.meta as unknown as { env: Record<string, string> }).env?.VITE_API_URL ??
  "http://localhost:8000";

export const routeService = {
  async getOptions(request: ConsumerRoutesRequest): Promise<RouteCandidate[]> {
    try {
      const res = await fetch(`${API_BASE}/api/consumer/routes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
        signal: AbortSignal.timeout(8000),
      });
      if (!res.ok) throw new Error(`API ${res.status}`);
      return (await res.json()) as RouteCandidate[];
    } catch {
      // API unavailable — use local computation with same physics
      return localFallback(request);
    }
  },
};

// ─── Local fallback computation (mirrors backend engines) ─────────────────────

const TRAFFIC_MULT: Record<string, number> = { Low: 0.88, Medium: 1.0, High: 1.2 };
const TIME_TRAFFIC: Record<string, Record<string, number>> = {
  "01": { Low: 0.88, Medium: 1.0, High: 1.22 },
  "02": { Low: 0.9, Medium: 1.0, High: 1.18 },
  "03": { Low: 0.92, Medium: 1.0, High: 1.14 },
};
const PROFILES = [
  { id: "01", name: "FASTEST", baseEnergy: 14.8, baseTime: 42, baseCost: 185 },
  { id: "02", name: "FUTURE READY", baseEnergy: 13.9, baseTime: 48, baseCost: 172 },
  { id: "03", name: "BATTERY CARE", baseEnergy: 13.1, baseTime: 53, baseCost: 160 },
] as const;

const PRIORITY_W: Record<string, number> = { CRITICAL: 3, HIGH: 2, NORMAL: 1 };

function computeLocalFmf(
  socAfter: number,
  soh: number,
  trips: FutureTrip[],
  capacityKwh: number,
): number {
  if (!trips.length) return 99.0;
  const usable = capacityKwh * (soh / 100);
  let wFeasible = 0;
  let wTotal = 0;
  for (const trip of trips) {
    const energyNeeded = trip.distance_km / 6.0;
    const socRequired = (energyNeeded / usable) * 100 + 10;
    const w = PRIORITY_W[trip.priority] ?? 1;
    wTotal += w;
    if (socAfter >= socRequired) wFeasible += w;
  }
  return +((wFeasible / wTotal) * 100).toFixed(1);
}

function localFallback(req: ConsumerRoutesRequest): RouteCandidate[] {
  const { soc, soh, temperature, capacity_kwh } = req.evState;
  const traffic = req.traffic;
  const tMult = TRAFFIC_MULT[traffic] ?? 1.0;
  const tempMult = 1 + (temperature - 25) * 0.008;
  const sohMult = 1 + Math.max(0, (94 - soh) * 0.002);
  const usable = capacity_kwh * (soh / 100);

  const candidates = PROFILES.map((p) => {
    const energy = +(p.baseEnergy * tMult * tempMult * sohMult).toFixed(1);
    const deltaSoc = (energy / usable) * 100;
    const after = +Math.max(0, soc - deltaSoc).toFixed(1);
    const tomorrow = +(after * 0.91).toFixed(1);
    const fmf = computeLocalFmf(after, soh, req.futureTrips, capacity_kwh);
    const fmr = +(100 - fmf).toFixed(1);
    const timeAdj = Math.round(p.baseTime * (TIME_TRAFFIC[p.id]?.[traffic] ?? 1.0));
    return {
      id: p.id,
      name: p.name,
      time: timeAdj,
      cost: p.baseCost,
      energy,
      feasibility: fmf,
      fmr,
      after,
      tomorrow,
      recommended: false,
      is_computed: false,
    } as RouteCandidate;
  });

  // Simple optimizer: highest FMF with acceptable time trade-off
  const best = candidates.reduce((a, b) => (b.feasibility > a.feasibility ? b : a));
  best.recommended = true;

  const fastest = candidates.reduce((a, b) => (b.time < a.time ? b : a));
  if (best.id !== fastest.id) {
    const riskDiff = +(fastest.fmr - best.fmr).toFixed(1);
    const timeDiff = best.time - fastest.time;
    best.explanation = `Route ${best.name} takes ${timeDiff} additional minutes but reduces future mobility risk by ${riskDiff} points.`;
    best.risk_change = `−${riskDiff} pts vs fastest`;
  }

  return candidates;
}
