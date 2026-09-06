/**
 * useEvState — React hook for managing the user's EV state.
 *
 * Persists to localStorage so the state survives page navigation.
 * Default values match the demo scenario (SOC 78%, SOH 94%, 29°C).
 *
 * Used by: ConsumerPage, FuturePage (via feasibility endpoint)
 */
import { useState, useEffect } from "react";

export type EVState = {
  vehicle_id: string;
  soc: number;         // State of Charge (%)
  soh: number;         // State of Health (%)
  temperature: number; // Battery temperature (°C)
  capacity_kwh: number;// Nominal battery capacity (kWh)
  efficiency: number;  // Baseline efficiency (km/kWh)
};

export const DEFAULT_EV_STATE: EVState = {
  vehicle_id: "EV-001",
  soc: 78,
  soh: 94,
  temperature: 29,
  capacity_kwh: 80,
  efficiency: 6.0,
};

const STORAGE_KEY = "fm_ev_state";

export function useEvState() {
  const [evState, setEvState] = useState<EVState>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        return { ...DEFAULT_EV_STATE, ...JSON.parse(saved) };
      }
    } catch {
      // ignore parse errors
    }
    return DEFAULT_EV_STATE;
  });

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(evState));
    } catch {
      // ignore storage errors
    }
  }, [evState]);

  const updateEvState = (updates: Partial<EVState>) => {
    setEvState((prev) => ({ ...prev, ...updates }));
  };

  const resetEvState = () => setEvState(DEFAULT_EV_STATE);

  /** Estimated current range based on SOC, SOH, capacity, efficiency */
  const rangeKm = Math.round(
    (evState.soc / 100) *
      evState.capacity_kwh *
      (evState.soh / 100) *
      evState.efficiency,
  );

  return { evState, updateEvState, resetEvState, rangeKm };
}
