/**
 * useFutureTrips — React hook for managing the user's future trip list.
 *
 * Persists to localStorage so trips survive page navigation between
 * /consumer and /future routes.
 *
 * Default trips match the demo scenario from futureTrips.json:
 *   TOMORROW: Coimbatore → Chennai (500 km, CRITICAL)
 *   DAY 3:   Local → Mobility (60 km, NORMAL)
 *   DAY 5:   Coimbatore → Bangalore (330 km, HIGH)
 *
 * Used by: FuturePage (display + add trip), ConsumerPage (FMF calculation)
 */
import { useState, useEffect } from "react";

export type TripPriority = "NORMAL" | "HIGH" | "CRITICAL";

export type FutureTrip = {
  id: string;
  day: string;
  origin: string;
  destination: string;
  distance_km: number;
  priority: TripPriority;
};

export const DEFAULT_FUTURE_TRIPS: FutureTrip[] = [
  {
    id: "default-1",
    day: "TOMORROW",
    origin: "Coimbatore",
    destination: "Chennai",
    distance_km: 500,
    priority: "CRITICAL",
  },
  {
    id: "default-2",
    day: "DAY 3",
    origin: "Local",
    destination: "Mobility",
    distance_km: 60,
    priority: "NORMAL",
  },
  {
    id: "default-3",
    day: "DAY 5",
    origin: "Coimbatore",
    destination: "Bangalore",
    distance_km: 330,
    priority: "HIGH",
  },
];

const STORAGE_KEY = "fm_future_trips";

export function useFutureTrips() {
  const [trips, setTrips] = useState<FutureTrip[]>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) return JSON.parse(saved) as FutureTrip[];
    } catch {
      // ignore parse errors
    }
    return DEFAULT_FUTURE_TRIPS;
  });

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(trips));
    } catch {
      // ignore storage errors
    }
  }, [trips]);

  const addTrip = (trip: Omit<FutureTrip, "id">) => {
    const newTrip: FutureTrip = { ...trip, id: `trip-${Date.now()}` };
    setTrips((prev) => [...prev, newTrip]);
  };

  const removeTrip = (id: string) => {
    setTrips((prev) => prev.filter((t) => t.id !== id));
  };

  const resetTrips = () => setTrips(DEFAULT_FUTURE_TRIPS);

  return { trips, addTrip, removeTrip, resetTrips };
}
