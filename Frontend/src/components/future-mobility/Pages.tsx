import { useEffect, useState } from "react";
import { Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { ArrowDown, ArrowRight, Check, Plus, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { cn } from "@/lib/utils";
import vehicles from "@/data/vehicles.json";
import demand from "@/data/futureDemand.json";
import scenarios from "@/data/riskScenarios.json";
import baseResultsDemo from "@/data/simulationResults.json";
import research from "@/data/researchResults.json";
import { routeService, type RouteCandidate } from "@/services/routeService";
import { futureMobilityService } from "@/services/futureMobilityService";
import {
  simulationService,
  type SimulationInput,
  type MethodComparisonRow,
} from "@/services/simulationService";
import { useEvState } from "@/hooks/useEvState";
import { useFutureTrips, type TripPriority } from "@/hooks/useFutureTrips";
import {
  BatteryMemory,
  CapacityArc,
  DecisionTrace,
  DemoLabel,
  Eyebrow,
  MobilityThread,
  NodeDiagram,
  PageTitle,
  VehicleSilhouette,
} from "./Visuals";

const section = "px-5 py-20 sm:px-10 sm:py-28 lg:px-16";
const ruleTitle = "text-[clamp(2.5rem,6vw,6.6rem)] font-light uppercase leading-[.92]";
const choices = <T extends string>({
  value,
  onChange,
  items,
}: {
  value: T;
  onChange: (v: T) => void;
  items: readonly T[];
}) => (
  <div className="flex flex-wrap gap-px bg-border">
    {items.map((item) => (
      <Button
        key={item}
        variant="ghost"
        onClick={() => onChange(item)}
        className={cn(
          "h-10 flex-1 rounded-none bg-background px-4 text-[10px] tracking-[.14em] hover:bg-secondary",
          value === item &&
            "bg-foreground text-background hover:bg-foreground hover:text-background",
        )}
      >
        {item}
      </Button>
    ))}
  </div>
);

function RoadGrid() {
  return (
    <svg
      className="absolute inset-0 h-full w-full text-border"
      viewBox="0 0 1200 700"
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      <g stroke="currentColor" strokeWidth="1" opacity=".7">
        {Array.from({ length: 10 }).map((_, i) => (
          <path key={`v${i}`} d={`M${i * 134} 0 L${600 + (i - 4.5) * 245} 700`} />
        ))}
        {Array.from({ length: 8 }).map((_, i) => (
          <line key={`h${i}`} x1="0" y1={90 + i * 82} x2="1200" y2={90 + i * 82} />
        ))}
      </g>
      <path
        d="M 70 570 C 300 520, 380 590, 550 455 S 870 300, 1130 125"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeDasharray="12 14"
        className="route-dash"
      />
    </svg>
  );
}

export function HomePage() {
  const [expanded, setExpanded] = useState(0);
  const chain = [
    "CURRENT STATE",
    "ROUTE OPTIONS",
    "FUTURE SCENARIOS",
    "FMR",
    "OPTIMIZATION",
    "RECOMMENDATION",
  ];
  return (
    <>
      <section className="relative min-h-[calc(100svh-4rem)] overflow-hidden px-5 pb-14 pt-12 sm:px-10 lg:px-16 lg:pt-16">
        <RoadGrid />
        <div className="relative z-10 flex min-h-[70svh] flex-col justify-between">
          <div className="flex justify-between">
            <Eyebrow>ITEREV</Eyebrow>
            <DemoLabel />
          </div>
          <h1 className="font-display text-[clamp(4rem,12vw,10rem)] font-medium uppercase leading-[.85] tracking-normal">
            <span className="block">Predictive EV</span>
            <span className="block text-right">Decision Intelligence</span>
          </h1>
          <div className="grid gap-5 border-t border-foreground pt-5 sm:grid-cols-2">
            <div>
              <p className="max-w-md text-sm font-semibold uppercase leading-6 tracking-[.15em]">
                Make today's EV decision with tomorrow in mind.
              </p>
              <div className="mt-4 flex flex-wrap gap-x-4 gap-y-2 text-xs font-semibold tracking-[.1em] text-muted-foreground">
                <span>Future Mobility Risk</span>
                <span className="opacity-30">|</span>
                <span>Battery State</span>
                <span className="opacity-30">|</span>
                <span>Uncertainty</span>
                <span className="opacity-30">|</span>
                <span>Chance-Constrained Routing</span>
              </div>
            </div>
            <div className="car-travel w-32 justify-self-end">
              <VehicleSilhouette />
            </div>
          </div>
        </div>
      </section>

      <section className={section}>
        <Eyebrow>System Chain</Eyebrow>
        <div className="mt-12 overflow-x-auto pb-4">
          <div className="flex min-w-[1000px] items-stretch">
            {chain.map((item, index) => (
              <button
                key={item}
                onClick={() => setExpanded(index)}
                className={cn(
                  "group min-h-52 border-l border-border p-5 text-left transition-[flex] duration-500",
                  expanded === index ? "flex-[2] bg-card" : "flex-1 hover:bg-card",
                  index === chain.length - 1 && "border-r",
                )}
              >
                <span className="text-[10px] text-muted-foreground">0{index + 1}</span>
                <div className="flex items-center gap-3">
                  <p className="mt-20 text-xs font-semibold tracking-[.14em]">{item}</p>
                  {index < chain.length - 1 && (
                    <ArrowRight className="mt-20 size-3 text-muted-foreground opacity-50" />
                  )}
                </div>
                {expanded === index && (
                  <p className="mt-5 max-w-xs text-sm leading-6 text-muted-foreground reveal-up">
                    {index === 0 &&
                      "Captures SOC, SOH, and constraints to initialize the predictive engine."}
                    {index === 1 &&
                      "Evaluates available paths including fastest and battery-aware options."}
                    {index === 2 &&
                      "Monte Carlo sampling over demand, degradation, and environmental uncertainty."}
                    {index === 3 &&
                      "Future Mobility Risk (FMR) measures the probability of failing tomorrow's critical trips."}
                    {index === 4 &&
                      "Chance-constrained objective penalizing energy, battery degradation, and FMR."}
                    {index === 5 &&
                      "Provides an actionable recommendation satisfying the configured risk threshold."}
                  </p>
                )}
              </button>
            ))}
          </div>
        </div>
      </section>

      <section className="grid border-t border-border lg:grid-cols-[1.15fr_.85fr]">
        <Link
          to="/consumer"
          className="group min-h-[520px] px-5 py-16 transition-colors hover:bg-card sm:px-10 lg:px-16"
        >
          <Eyebrow>Consumer / 01</Eyebrow>
          <h2 className="mt-20 text-6xl font-light uppercase sm:text-8xl">Your EV</h2>
          <p className="mt-8 text-lg leading-8 text-muted-foreground">
            Current state.
            <br />
            Route options.
            <br />
            Future constraint.
          </p>
          <span className="mt-20 inline-flex items-center gap-2 text-xs font-semibold tracking-[.18em]">
            EXPLORE <ArrowRight className="size-4 transition-transform group-hover:translate-x-2" />
          </span>
        </Link>
        <Link
          to="/research"
          className="group min-h-[520px] border-t border-border bg-foreground px-5 py-16 text-background lg:border-l lg:border-t-0 sm:px-10 lg:px-16"
        >
          <Eyebrow className="text-background/60">Research / 02</Eyebrow>
          <h2 className="mt-20 text-6xl font-light uppercase sm:text-8xl">Validation</h2>
          <p className="mt-8 text-lg leading-8 text-background/60">
            Ablation analysis.
            <br />
            Independent Replication.
            <br />
            Monte Carlo convergence.
          </p>
          <span className="mt-28 inline-flex items-center gap-2 text-xs font-semibold tracking-[.18em]">
            EXPLORE <ArrowRight className="size-4 transition-transform group-hover:translate-x-2" />
          </span>
        </Link>
      </section>
    </>
  );
}

function RouteMap({ selected }: { selected: number }) {
  return (
    <div className="relative h-[440px] overflow-hidden bg-card">
      <svg viewBox="0 0 900 440" className="h-full w-full text-border">
        <g fill="none" stroke="currentColor">
          {Array.from({ length: 8 }).map((_, i) => (
            <path key={i} d={`M${i * 120} 0 Q ${440 - i * 30} 220 ${i * 105 + 80} 440`} />
          ))}
          <path
            d={
              selected === 0
                ? "M90 350 C240 200 390 330 790 90"
                : selected === 1
                  ? "M90 350 C280 320 420 110 790 90"
                  : "M90 350 C210 80 570 390 790 90"
            }
            className="route-dash text-foreground"
            strokeWidth="3"
            strokeDasharray="10 11"
          />
        </g>
      </svg>
      <span className="absolute left-[10%] top-[77%] size-3 rounded-full bg-foreground" />
      <span className="absolute right-[11%] top-[18%] size-3 rounded-full bg-success" />
      <span className="absolute bottom-12 left-5 text-xs font-semibold tracking-[.15em]">
        COIMBATORE
      </span>
      <span className="absolute right-5 top-12 text-xs font-semibold tracking-[.15em]">OOTY</span>
      <span className="absolute right-5 bottom-5 text-xs text-muted-foreground">
        88 KM / ROUTE 0{selected + 1}
      </span>
    </div>
  );
}

// Demo routes used as skeleton while API loads
const DEMO_ROUTES: RouteCandidate[] = [
  {
    id: "01",
    name: "FASTEST",
    time: 42,
    cost: 185,
    energy: 14.8,
    feasibility: 94,
    fmr: 6,
    after: 58,
    tomorrow: 52,
    recommended: false,
    is_computed: false,
  },
  {
    id: "02",
    name: "FUTURE READY",
    time: 48,
    cost: 172,
    energy: 13.9,
    feasibility: 98,
    fmr: 2,
    after: 61,
    tomorrow: 55,
    recommended: true,
    is_computed: false,
  },
  {
    id: "03",
    name: "BATTERY CARE",
    time: 53,
    cost: 160,
    energy: 13.1,
    feasibility: 99,
    fmr: 1,
    after: 64,
    tomorrow: 58,
    recommended: false,
    is_computed: false,
  },
];

export function ConsumerPage() {
  const { evState, updateEvState, rangeKm } = useEvState();
  const { trips } = useFutureTrips();
  const [selected, setSelected] = useState(1);
  const [traffic, setTraffic] = useState<"Low" | "Medium" | "High">("Medium");
  const [showInputs, setShowInputs] = useState(false);

  // Fetch computed routes from backend (or local fallback)
  const {
    data: computedRoutes,
    isLoading,
    isSuccess,
  } = useQuery({
    queryKey: [
      "consumer-routes",
      evState.soc,
      evState.soh,
      evState.temperature,
      evState.capacity_kwh,
      traffic,
      trips.map((t) => `${t.id}:${t.distance_km}`).join(","),
    ],
    queryFn: () =>
      routeService.getOptions({
        evState,
        origin: "Coimbatore",
        destination: "Ooty",
        distance_km: 88,
        traffic,
        futureTrips: trips,
      }),
    staleTime: 60_000,
    placeholderData: DEMO_ROUTES,
  });

  const routeData: RouteCandidate[] = computedRoutes ?? DEMO_ROUTES;
  const route = routeData[selected] ?? routeData[0];
  const recommendedRoute = routeData.find((r) => r.recommended) ?? routeData[1] ?? routeData[0];
  if (!route || !recommendedRoute) return null;

  // Build DecisionTrace items from computed or demo data
  const fmrCiLower = recommendedRoute.fmr_ci_lower;
  const fmrCiUpper = recommendedRoute.fmr_ci_upper;
  const totalScenarios = recommendedRoute.total_scenarios;
  const constraintRelaxed = recommendedRoute.constraint_relaxed;
  const traceItems = [
    { label: "Decision", value: recommendedRoute.name },
    { label: "Reason", value: "Preserve energy for future mobility" },
    { label: "Battery effect", value: `${recommendedRoute.after}% after today` },
    {
      label: "Future risk (FMR)",
      value: totalScenarios
        ? `${recommendedRoute.fmr}% (95% CI: ${fmrCiLower?.toFixed(1)}–${fmrCiUpper?.toFixed(1)}%)`
        : `${recommendedRoute.fmr}%`,
    },
    {
      label: "Scenarios",
      value: totalScenarios ? `${totalScenarios.toLocaleString()} Monte Carlo` : "N/A",
    },
    { label: "Risk change", value: recommendedRoute.risk_change ?? "—" },
  ];

  return (
    <>
      <PageTitle lines={["My EV"]} kicker={`Consumer / ${evState.vehicle_id}`} />

      {/* ── EV State Configuration ───────────────────────────── */}
      <section className="border-b border-border px-5 py-4 sm:px-10 lg:px-16">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Eyebrow>EV configuration</Eyebrow>
            {isSuccess && computedRoutes?.[0]?.is_computed && (
              <span className="text-[9px] font-semibold tracking-[.16em] text-success">
                ● LIVE RESULT
              </span>
            )}
            {isLoading && (
              <span className="animate-pulse text-[9px] font-semibold tracking-[.16em] text-muted-foreground">
                ● COMPUTING
              </span>
            )}
            {!isLoading && (!isSuccess || !computedRoutes?.[0]?.is_computed) && <DemoLabel />}
          </div>
          <Button
            variant="ghost"
            className="h-7 rounded-none text-[9px] tracking-[.16em]"
            onClick={() => setShowInputs(!showInputs)}
          >
            {showInputs ? "COLLAPSE ↑" : "CONFIGURE ↓"}
          </Button>
        </div>
        {showInputs && (
          <div className="mt-4 grid gap-px bg-border p-px sm:grid-cols-2 lg:grid-cols-4 reveal-up">
            <label className="bg-background p-4">
              <Eyebrow>State of charge / {evState.soc}%</Eyebrow>
              <Slider
                value={[evState.soc]}
                min={10}
                max={100}
                step={1}
                className="mt-4"
                onValueChange={(v) => updateEvState({ soc: v[0]! })}
              />
            </label>
            <label className="bg-background p-4">
              <Eyebrow>Battery health / {evState.soh}%</Eyebrow>
              <Slider
                value={[evState.soh]}
                min={60}
                max={100}
                step={1}
                className="mt-4"
                onValueChange={(v) => updateEvState({ soh: v[0]! })}
              />
            </label>
            <label className="bg-background p-4">
              <Eyebrow>Temperature / {evState.temperature}°C</Eyebrow>
              <Slider
                value={[evState.temperature]}
                min={15}
                max={48}
                step={1}
                className="mt-4"
                onValueChange={(v) => updateEvState({ temperature: v[0]! })}
              />
            </label>
            <label className="bg-background p-4">
              <Eyebrow>Traffic conditions</Eyebrow>
              <div className="mt-4">
                {choices({
                  value: traffic,
                  onChange: setTraffic,
                  items: ["Low", "Medium", "High"] as const,
                })}
              </div>
            </label>
          </div>
        )}
      </section>

      {/* ── Predictive FMR Centerpiece ────────────────────────── */}
      <section className={`${section} border-y border-border pb-16 pt-12`}>
        <div className="grid gap-12 lg:grid-cols-[1.2fr_.8fr]">
          {/* FMR Main Display */}
          <div>
            <Eyebrow>Future Mobility Risk</Eyebrow>
            <div className="mt-8 flex items-baseline gap-6">
              <span className="text-[clamp(6rem,12vw,10rem)] font-light leading-none tabular-nums tracking-tight">
                {recommendedRoute.fmr.toFixed(1)}
                <span className="text-4xl">%</span>
              </span>
              <div className="flex flex-col gap-1 text-xs font-semibold tracking-[.1em] text-muted-foreground uppercase">
                <span>95% CI</span>
                <span className="text-foreground">
                  {fmrCiLower?.toFixed(1) ?? "—"} — {fmrCiUpper?.toFixed(1) ?? "—"}%
                </span>
              </div>
            </div>

            {/* Constraint visualization */}
            <div className="mt-14 max-w-xl">
              <div className="mb-3 flex justify-between text-[10px] font-semibold tracking-[.15em]">
                <span className="text-muted-foreground">PREDICTED RISK</span>
                <span className="text-foreground">RISK LIMIT 10%</span>
              </div>
              <div className="relative h-2 bg-muted">
                <div
                  className={cn(
                    "absolute inset-y-0 left-0 transition-all duration-700",
                    constraintRelaxed ? "bg-amber-500" : "bg-foreground",
                  )}
                  style={{ width: `${Math.min(recommendedRoute.fmr, 100)}%` }}
                />
                <div className="absolute inset-y-[-4px] left-[10%] w-px bg-foreground" />
              </div>

              <div className="mt-6 flex items-center gap-3">
                {constraintRelaxed ? (
                  <>
                    <span className="flex size-2 bg-amber-500" />
                    <span className="text-xs font-semibold tracking-[.15em] text-amber-500 uppercase">
                      NO FEASIBLE ACTION — CHANCE CONSTRAINT NOT SATISFIED
                    </span>
                  </>
                ) : (
                  <>
                    <span className="flex size-2 bg-success" />
                    <span className="text-xs font-semibold tracking-[.15em] text-success uppercase">
                      FEASIBLE — WITHIN CONSTRAINT
                    </span>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Monte Carlo Summary */}
          <div className="flex flex-col justify-between border-t border-border pt-8 lg:border-l lg:border-t-0 lg:pl-12 lg:pt-0">
            <div>
              <Eyebrow>Monte Carlo Simulation</Eyebrow>
              <div className="mt-6">
                <span className="text-5xl font-light tabular-nums tracking-tight">
                  {totalScenarios ? totalScenarios.toLocaleString() : "—"}
                </span>
                <span className="ml-3 text-xs font-semibold tracking-[.15em] text-muted-foreground uppercase">
                  Scenarios
                </span>
              </div>
            </div>

            <div className="mt-8 space-y-4">
              <div className="grid grid-cols-2 gap-4 text-xs font-semibold tracking-[.15em] uppercase border-b border-border pb-4">
                <div className="flex flex-col gap-1">
                  <span className="text-muted-foreground">Successful</span>
                  <span className="text-success">
                    {totalScenarios
                      ? Math.round(
                          totalScenarios * (1 - recommendedRoute.fmr / 100),
                        ).toLocaleString()
                      : "—"}
                  </span>
                </div>
                <div className="flex flex-col gap-1">
                  <span className="text-muted-foreground">Future failures</span>
                  <span className={constraintRelaxed ? "text-amber-500" : "text-foreground"}>
                    {totalScenarios
                      ? Math.round(totalScenarios * (recommendedRoute.fmr / 100)).toLocaleString()
                      : "—"}
                  </span>
                </div>
              </div>
              <div className="flex justify-between text-[10px] text-muted-foreground tracking-[.15em] uppercase">
                <span>Uncertainty Model: IterEV</span>
                <span>Seed: 42</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Route Options Table ──────────────────────────────── */}
      <section className="border-y border-border">
        <div className="grid px-5 py-4 text-[10px] font-semibold tracking-[.15em] text-muted-foreground sm:grid-cols-[1.5fr_repeat(4,1fr)] sm:px-10 lg:px-16">
          <span>ROUTE OPTION</span>
          <span>TIME</span>
          <span>COST</span>
          <span>ENERGY</span>
          <span>FUTURE</span>
        </div>
        {isLoading && (
          <div className="border-t border-border px-5 py-7 text-xs tracking-[.14em] text-muted-foreground animate-pulse sm:px-10 lg:px-16">
            GENERATING ROUTES...
          </div>
        )}
        {routeData.map((item, index) => (
          <button
            key={item.id}
            onClick={() => setSelected(index)}
            className={cn(
              "grid w-full grid-cols-2 gap-y-5 border-t border-border px-5 py-7 text-left transition-colors hover:bg-card sm:grid-cols-[1.5fr_repeat(4,1fr)] sm:px-10 lg:px-16",
              selected === index && "bg-card",
            )}
          >
            <span>
              <b className="text-sm tracking-[.14em]">{item.name}</b>
              {item.recommended && (
                <span className="ml-3 text-[9px] text-success">RECOMMENDED</span>
              )}
              {item.constraint_relaxed && (
                <span className="ml-2 text-[9px] text-amber-500">CONSTRAINT RELAXED</span>
              )}
            </span>
            <span>{item.time} min</span>
            <span>₹{item.cost}</span>
            <span>{item.energy} kWh</span>
            <span className="flex flex-col justify-center">
              <span className="text-2xl font-light">
                {item.fmr.toFixed(1)}%
                <span className="ml-1 text-[9px] text-muted-foreground">FMR PT. ESTIMATE</span>
              </span>
              <span className="text-[9px] text-muted-foreground mt-1 tracking-widest">
                CI: {item.fmr_ci_lower?.toFixed(1) ?? '0.0'}% – {item.fmr_ci_upper?.toFixed(1) ?? '0.0'}%
              </span>
            </span>
          </button>
        ))}
      </section>

      {/* ── Battery Memory ───────────────────────────────────── */}
      <section className={section}>
        <Eyebrow>Battery memory / route 0{selected + 1}</Eyebrow>
        <div className="mt-8">
          <BatteryMemory current={evState.soc} after={route.after} tomorrow={route.tomorrow} />
        </div>
      </section>

      {/* ── Decision Explanation ─────────────────────────────── */}
      <section className={`${section} grid gap-12 bg-card lg:grid-cols-[.6fr_1.4fr]`}>
        <h2 className="text-4xl font-light uppercase">Why this decision?</h2>
        <div>
          <p className="max-w-2xl text-2xl font-light leading-10">
            {recommendedRoute.explanation ??
              "Route 02 takes six additional minutes but leaves a stronger predicted battery state for upcoming mobility requirements."}
          </p>
          <div className="mt-14">
            <DecisionTrace items={traceItems} />
          </div>
          {(!isSuccess || !computedRoutes?.[0]?.is_computed) && (
            <div className="mt-6">
              <DemoLabel />
            </div>
          )}
        </div>
      </section>
    </>
  );
}

export function FuturePage() {
  const { evState } = useEvState();
  const { trips, addTrip, removeTrip } = useFutureTrips();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    origin: "",
    destination: "",
    day: "",
    distance_km: "",
    priority: "NORMAL" as TripPriority,
  });

  // Fetch computed FMF/FMR from API
  const { data: feasibility, isSuccess: feasLoaded } = useQuery({
    queryKey: [
      "future-feasibility",
      evState.soc,
      evState.soh,
      evState.capacity_kwh,
      trips.map((t) => `${t.id}:${t.distance_km}`).join(","),
    ],
    queryFn: () => futureMobilityService.getFeasibility({ evState, futureTrips: trips }),
    staleTime: 60_000,
  });

  const fmf = feasibility?.fmf ?? 97.4;
  const fmr = feasibility?.fmr ?? 2.6;
  const riskTimeline = feasibility?.risk_timeline ?? [2.1, 3.4, 4.1, 3.0, 2.6];

  const handleAddTrip = () => {
    const dist = parseFloat(form.distance_km);
    if (!form.origin || !form.destination || isNaN(dist) || dist <= 0) return;
    addTrip({
      origin: form.origin,
      destination: form.destination,
      day: form.day || "UPCOMING",
      distance_km: dist,
      priority: form.priority,
    });
    setForm({ origin: "", destination: "", day: "", distance_km: "", priority: "NORMAL" });
    setOpen(false);
  };

  return (
    <>
      <PageTitle lines={["What comes after", "today?"]} kicker="Future requirements" />
      <section className={section}>
        <div className="overflow-x-auto">
          <div className="flex min-w-[900px]">
            {trips.map((trip, index) => (
              <div key={trip.id} className="min-w-0 flex-1 border-t border-foreground px-4 pt-5">
                <span className="mb-8 block size-2 -translate-y-[25px] rounded-full bg-foreground" />
                <div className="flex items-start justify-between">
                  <Eyebrow>{trip.day}</Eyebrow>
                  <button
                    onClick={() => removeTrip(trip.id)}
                    className="text-muted-foreground/50 hover:text-foreground transition-colors"
                    aria-label="Remove trip"
                  >
                    <X className="size-3" />
                  </button>
                </div>
                <p className="mt-8 text-2xl font-light">
                  {trip.origin}
                  <br />→ {trip.destination}
                </p>
                <p className="mt-8 text-sm text-muted-foreground">
                  {trip.distance_km} KM / {trip.priority}
                </p>
                {index < trips.length - 1 && <ArrowRight className="mt-10 size-4" />}
              </div>
            ))}
          </div>
        </div>
        <Button variant="outline" className="mt-12 gap-3" onClick={() => setOpen(!open)}>
          <Plus /> ADD TRIP
        </Button>
        {open && (
          <div className="mt-6 grid gap-px bg-border p-px sm:grid-cols-3 reveal-up">
            {(
              [
                ["Origin", "origin", "text"],
                ["Destination", "destination", "text"],
                ["Day", "day", "text"],
                ["Distance (km)", "distance_km", "number"],
              ] as const
            ).map(([label, key, type]) => (
              <label key={label} className="bg-background p-4">
                <Eyebrow>{label}</Eyebrow>
                <input
                  className="mt-3 w-full bg-transparent text-sm outline-none"
                  placeholder={label}
                  type={type}
                  value={form[key]}
                  onChange={(e) => setForm((p) => ({ ...p, [key]: e.target.value }))}
                />
              </label>
            ))}
            <label className="bg-background p-4">
              <Eyebrow>Priority</Eyebrow>
              <div className="mt-3">
                {choices({
                  value: form.priority,
                  onChange: (v: TripPriority) => setForm((p) => ({ ...p, priority: v })),
                  items: ["NORMAL", "HIGH", "CRITICAL"] as const,
                })}
              </div>
            </label>
            <div className="flex items-end bg-background p-4">
              <Button className="h-10 w-full text-[10px] tracking-[.14em]" onClick={handleAddTrip}>
                ADD TRIP
              </Button>
            </div>
          </div>
        )}
      </section>

      <section
        className={`${section} grid items-center gap-12 border-y border-border lg:grid-cols-2`}
      >
        <div>
          <Eyebrow>Future mobility risk (FMR)</Eyebrow>
          <p className="mt-7 text-[clamp(6rem,15vw,13rem)] font-light leading-none tabular-nums">
            {fmr.toFixed(1)}
            <span className="text-3xl">%</span>
          </p>
          {feasibility?.confidence_interval && (
            <p className="mt-2 text-sm text-muted-foreground">
              95% CI: {feasibility.confidence_interval.lower.toFixed(1)}% –{" "}
              {feasibility.confidence_interval.upper.toFixed(1)}%
            </p>
          )}
          {feasibility?.total_scenarios ? (
            <p className="mt-1 text-xs text-muted-foreground">
              Scenarios: {feasibility.total_scenarios.toLocaleString()} · Failed:{" "}
              {feasibility.failed_scenarios?.toLocaleString()} · Successful:{" "}
              {feasibility.successful_scenarios?.toLocaleString()}
            </p>
          ) : null}
          <p className="mt-6 max-w-xl text-sm leading-6 text-muted-foreground">
            Estimated probability that future mobility requirements cannot be satisfied after the
            current decision. Computed via Monte Carlo scenario simulation.
          </p>
          {feasLoaded && feasibility?.is_computed ? (
            <span className="text-[9px] font-semibold tracking-[.16em] text-success">
              ● COMPUTED
            </span>
          ) : (
            <DemoLabel />
          )}
        </div>
        <CapacityArc current={evState.soc} future={fmf} risk={fmr} />
      </section>

      <section className={section}>
        <Eyebrow>Future risk / hover points</Eyebrow>
        <div className="mt-16 grid grid-cols-5">
          {riskTimeline.map((v, i) => (
            <div key={i} className="group border-t border-border pt-6 text-center">
              <span className="mx-auto -mt-[29px] block size-2 rounded-full bg-foreground transition-transform group-hover:scale-[2]" />
              <p className="mt-5 text-3xl font-light">{v}%</p>
              <p className="mt-2 text-[9px] tracking-[.15em] text-muted-foreground">
                {i === 0 ? "TODAY" : `DAY ${i + 1}`}
              </p>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}

export function FleetPage() {
  const [selected, setSelected] = useState(1);
  const vehicle = vehicles[selected] ?? vehicles[0];
  if (!vehicle) return null;
  return (
    <>
      <PageTitle lines={["Your fleet"]} kicker="Operations intelligence" />
      <section className="grid grid-cols-2 border-b border-border lg:grid-cols-4">
        {[
          [24, "VEHICLES"],
          [18, "ACTIVE"],
          [4, "CHARGING"],
          [2, "AVAILABLE"],
        ].map(([v, l], i) => (
          <div
            key={String(l)}
            className={cn("px-5 py-12 sm:px-10", i > 0 && "border-l border-border")}
          >
            <p className="text-6xl font-light tabular-nums sm:text-8xl">{v}</p>
            <Eyebrow className="mt-5">{l}</Eyebrow>
          </div>
        ))}
      </section>
      <section className={`${section} grid gap-12 lg:grid-cols-[1.4fr_.6fr]`}>
        <div className="relative min-h-[560px] border-y border-border bg-card">
          <Eyebrow className="absolute left-5 top-5">Spatial fleet / select vehicle</Eyebrow>
          {vehicles.map((v, i) => (
            <button
              key={v.id}
              onClick={() => setSelected(i)}
              className={cn(
                "absolute w-24 p-2 text-left transition-all hover:scale-110",
                selected === i && "bg-background",
              )}
              style={{ left: `${v.x}%`, top: `${v.y}%`, transform: "translate(-50%,-50%)" }}
            >
              <VehicleSilhouette />
              <span className="text-[9px] tracking-[.12em]">
                {v.id} · {v.soc}%
              </span>
            </button>
          ))}
        </div>
        <aside className="border-l border-border pl-7">
          <Eyebrow>Vehicle detail</Eyebrow>
          <h2 className="mt-6 text-5xl font-light">{vehicle.id}</h2>
          <div className="mt-10 grid grid-cols-2 gap-px bg-border">
            {[
              ["SOC", vehicle.soc],
              ["SOH", vehicle.soh],
              ["FUTURE CAPACITY", vehicle.capacity],
              ["TEMP", vehicle.temp],
            ].map(([l, v]) => (
              <div className="bg-background p-5" key={String(l)}>
                <Eyebrow>{l}</Eyebrow>
                <p className="mt-4 text-3xl font-light">
                  {v}
                  {l === "TEMP" ? "°C" : "%"}
                </p>
              </div>
            ))}
          </div>
          <p
            className={cn(
              "mt-8 border-l-2 pl-4 text-sm font-semibold tracking-[.16em]",
              vehicle.status === "PROTECT" ? "border-critical" : "border-success",
            )}
          >
            {vehicle.status}
          </p>
        </aside>
      </section>
      <section className={`${section} grid gap-8 bg-foreground text-background sm:grid-cols-3`}>
        <div>
          <Eyebrow className="text-background/50">Future demand</Eyebrow>
          <p className="mt-4 text-7xl font-light">{demand.day}</p>
        </div>
        <div>
          <p className="text-8xl font-light">{demand.tasks}</p>
          <Eyebrow className="text-background/50">Tasks</Eyebrow>
        </div>
        <div>
          <p className="text-5xl font-light">+{demand.change}%</p>
          <Eyebrow className="mt-2 text-background/50">Expected demand</Eyebrow>
          <DemoLabel>{demand.label}</DemoLabel>
        </div>
      </section>
      <section className={section}>
        <h2 className={ruleTitle}>
          Today's assignment
          <br />
          <span className="text-muted-foreground">changes tomorrow's capacity.</span>
        </h2>
      </section>
    </>
  );
}

export function RiskPage() {
  const { evState } = useEvState();
  const { trips } = useFutureTrips();

  // Fetch computed feasibility + risk timeline from API
  const { data: feasibility, isSuccess: feasLoaded } = useQuery({
    queryKey: [
      "risk-feasibility",
      evState.soc,
      evState.soh,
      evState.capacity_kwh,
      trips.map((t) => `${t.id}:${t.distance_km}`).join(","),
    ],
    queryFn: () => futureMobilityService.getFeasibility({ evState, futureTrips: trips }),
    staleTime: 60_000,
  });

  // Fetch computed routes for the decision comparison section
  const { data: computedRoutes } = useQuery({
    queryKey: [
      "risk-routes",
      evState.soc,
      evState.soh,
      evState.temperature,
      evState.capacity_kwh,
      trips.map((t) => `${t.id}:${t.distance_km}`).join(","),
    ],
    queryFn: () =>
      routeService.getOptions({
        evState,
        origin: "Coimbatore",
        destination: "Ooty",
        distance_km: 88,
        traffic: "Medium",
        futureTrips: trips,
      }),
    staleTime: 60_000,
  });

  const fmr = feasibility?.fmr ?? 2.6;
  const fmf = feasibility?.fmf ?? 97.4;
  const riskTimeline = feasibility?.risk_timeline ?? [2.1, 3.4, 4.1, 3.0, 2.6];
  const isComputed = feasLoaded && (feasibility?.is_computed ?? false);
  const riskLevel = fmr <= 5 ? "low" : fmr <= 15 ? "moderate" : fmr <= 30 ? "high" : "critical";

  // Get fastest and recommended routes for comparison
  const fastest = computedRoutes
    ? computedRoutes.reduce((a, b) => (b.time < a.time ? b : a))
    : null;
  const recommended = computedRoutes?.find((r) => r.recommended) ?? null;
  const fastestTime = fastest?.time ?? 42;
  const fastestRisk = fastest?.fmr ?? 18.2;
  const recTime = recommended?.time ?? 48;
  const recRisk = recommended?.fmr ?? 2.6;

  return (
    <>
      <PageTitle lines={["Future", "mobility risk"]} kicker="Risk intelligence" />
      <section className={`${section} grid items-center gap-14 lg:grid-cols-2`}>
        <div>
          <p className="text-[clamp(8rem,18vw,16rem)] font-light leading-none">
            {fmr.toFixed(1)}
            <span className="text-3xl">%</span>
          </p>
          <Eyebrow>Future risk / {riskLevel}</Eyebrow>
          {feasibility?.confidence_interval && (
            <p className="mt-2 text-sm text-muted-foreground">
              95% CI: {feasibility.confidence_interval.lower.toFixed(1)}% –{" "}
              {feasibility.confidence_interval.upper.toFixed(1)}%
            </p>
          )}
          {feasibility?.total_scenarios ? (
            <p className="mt-1 text-xs text-muted-foreground">
              {feasibility.total_scenarios.toLocaleString()} scenarios · Seed:{" "}
              {feasibility.random_seed ?? "—"}
            </p>
          ) : null}
          {isComputed ? (
            <span className="text-[9px] font-semibold tracking-[.16em] text-success">
              ● COMPUTED
            </span>
          ) : (
            <DemoLabel />
          )}
        </div>
        <MobilityThread score={Math.round(fmf)} />
      </section>

      <section className="border-y border-border">
        <div className="relative pt-12 pb-4">
          <div className="absolute left-0 right-0 top-16 h-px bg-foreground opacity-20 border-t border-dashed" />
          <span className="absolute left-5 top-12 text-[9px] font-semibold tracking-[.15em] text-foreground opacity-50">
            RISK THRESHOLD 10%
          </span>

          <div className="grid grid-cols-5 relative z-10">
            {riskTimeline.map((v, i) => (
              <div
                key={i}
                className={cn("px-3 py-10 text-center relative", i > 0 && "border-l border-border")}
              >
                <div
                  className={cn(
                    "absolute bottom-full left-1/2 w-1 -translate-x-1/2 transition-all",
                    v > 10 ? "bg-amber-500" : "bg-foreground",
                  )}
                  style={{ height: `${v * 4}px` }}
                />
                <p
                  className={cn(
                    "text-3xl font-light sm:text-5xl",
                    v > 10 ? "text-amber-500" : "text-foreground",
                  )}
                >
                  {v}%
                </p>
                <Eyebrow className="mt-5">{i === 0 ? "TODAY" : `DAY ${i + 1}`}</Eyebrow>
                <p className="mt-2 text-[9px] text-muted-foreground uppercase tracking-widest text-center">
                  Cumulative Risk
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className={section}>
        <Eyebrow>Scenario matrix</Eyebrow>
        <div className="mt-8">
          {scenarios.map((s, i) => (
            <div
              key={s.name}
              className="grid grid-cols-[1fr_auto_auto] items-center border-t border-border py-5"
            >
              <span className="text-xs font-semibold tracking-[.14em]">{s.name}</span>
              <span className="mr-8 text-3xl font-light">{s.risk}%</span>
              <span
                className={cn(
                  "h-6 w-1",
                  i === 0 ? "bg-success" : i < 3 ? "bg-warning" : "bg-critical",
                )}
              />
            </div>
          ))}
        </div>
      </section>

      <section className={`${section} bg-card`}>
        <div className="grid items-center gap-10 lg:grid-cols-[1fr_auto_1fr]">
          <div>
            <Eyebrow>Original decision</Eyebrow>
            <p className="mt-8 text-7xl font-light">
              {fastestTime} <span className="text-lg">MIN</span>
            </p>
            <p className="mt-4">
              Future risk <b className="text-critical">{fastestRisk}%</b>
            </p>
          </div>
          <ArrowDown className="size-8 lg:-rotate-90" />
          <div>
            <Eyebrow>Recommended decision</Eyebrow>
            <p className="mt-8 text-7xl font-light">
              {recTime} <span className="text-lg">MIN</span>
            </p>
            <p className="mt-4">
              Future risk <b className="text-success">{recRisk}%</b>
            </p>
          </div>
        </div>
        <div className="mt-20 grid gap-5 border-t border-border pt-8 lg:grid-cols-[.3fr_1fr]">
          <h3 className="text-4xl font-light">WHY?</h3>
          <p className="max-w-3xl text-2xl font-light leading-10">
            {recommended?.explanation ??
              "The recommended decision slightly increases current travel time but substantially reduces predicted future mobility risk."}
          </p>
        </div>
        {isComputed ? (
          <span className="mt-6 text-[9px] font-semibold tracking-[.16em] text-success">
            ● LIVE RESULT
          </span>
        ) : (
          <div className="mt-6">
            <DemoLabel />
          </div>
        )}
      </section>

      <section className={`${section} grid grid-cols-2 gap-px bg-border sm:grid-cols-4`}>
        {["LOW", "WARNING", "HIGH", "CRITICAL"].map((s, i) => (
          <div className="bg-background p-6" key={s}>
            <span
              className={cn(
                "block h-1 w-10",
                i === 0 ? "bg-success" : i === 1 ? "bg-warning" : "bg-critical",
              )}
            />
            <p className="mt-10 text-sm tracking-[.14em]">{s}</p>
          </div>
        ))}
      </section>
    </>
  );
}

export function SimulationPage() {
  const [input, setInput] = useState<SimulationInput>({
    mode: "Consumer",
    horizon: 5,
    soh: 94,
    temperature: 29,
    traffic: "Medium",
    demand: "Medium",
    charging: "Normal",
    uncertainty: "Low",
    scenario_count: 1000,
    random_seed: 42,
    charging_availability: 0.95,
    soc_initial: 78,
  } as SimulationInput);
  const [running, setRunning] = useState(false);
  const [step, setStep] = useState(7);
  const [liveResult, setLiveResult] = useState<{
    primary: {
      feasibility: number;
      risk: number;
      energy: number;
      travelTime: number;
      riskRange: number;
    };
    comparison: MethodComparisonRow[];
    is_computed: boolean;
  } | null>(null);

  const stages = [
    "GENERATING ROUTES",
    "PREDICTING ENERGY",
    "PROPAGATING BATTERY STATE",
    "GENERATING FUTURE SCENARIOS",
    "CALCULATING FEASIBILITY",
    "CALCULATING RISK",
    "OPTIMIZING",
    "COMPLETE",
  ];

  const run = async () => {
    setRunning(true);
    setStep(0);
    const result = await simulationService.run(input);
    setLiveResult(result);
  };

  useEffect(() => {
    if (!running) return;
    if (step >= 7) {
      setRunning(false);
      return;
    }
    const timer = setTimeout(() => setStep((v) => v + 1), 300);
    return () => clearTimeout(timer);
  }, [running, step]);

  const primary = liveResult?.primary;
  const comparison = liveResult?.comparison ?? baseResultsDemo;
  const isComputed = liveResult?.is_computed ?? false;

  return (
    <>
      <PageTitle lines={["Research", "simulation"]} kicker="Test today's decision" />
      <section className={`${section} grid gap-14 lg:grid-cols-[.9fr_1.1fr]`}>
        <div>
          <p className="max-w-lg text-2xl font-light leading-9">
            Test how today's decision changes tomorrow's mobility.
          </p>
          {isComputed ? (
            <span className="text-[9px] font-semibold tracking-[.16em] text-success">
              ● LIVE RESULT
            </span>
          ) : (
            <DemoLabel>DEMO DATA — REPLACE WITH EXPERIMENTAL RESULTS</DemoLabel>
          )}
        </div>
        <div className="space-y-8">
          <Control label="Mode">
            {choices({
              value: input.mode,
              onChange: (v) => setInput({ ...input, mode: v }),
              items: ["Consumer", "Fleet"] as const,
            })}
          </Control>
          <Control label="Planning horizon">
            {choices({
              value: String(input.horizon),
              onChange: (v) => setInput({ ...input, horizon: Number(v) }),
              items: ["1", "3", "5", "7"] as const,
            })}
          </Control>
          <Control label={`Battery SOH / ${input.soh}%`}>
            <Slider
              value={[input.soh]}
              min={60}
              max={100}
              step={1}
              onValueChange={(v) => setInput({ ...input, soh: v[0] ?? input.soh })}
            />
          </Control>
          <Control label={`Temperature / ${input.temperature}°C`}>
            <Slider
              value={[input.temperature]}
              min={15}
              max={48}
              step={1}
              onValueChange={(v) => setInput({ ...input, temperature: v[0] ?? input.temperature })}
            />
          </Control>
          <Control label="Traffic">
            {choices({
              value: input.traffic,
              onChange: (v) => setInput({ ...input, traffic: v }),
              items: ["Low", "Medium", "High"] as const,
            })}
          </Control>
          <Control label="Future demand">
            {choices({
              value: input.demand,
              onChange: (v) => setInput({ ...input, demand: v }),
              items: ["Low", "Medium", "High"] as const,
            })}
          </Control>
          <Control label="Charging availability">
            {choices({
              value: input.charging,
              onChange: (v) => setInput({ ...input, charging: v }),
              items: ["Normal", "Restricted"] as const,
            })}
          </Control>
          <Control label="Battery uncertainty">
            {choices({
              value: input.uncertainty,
              onChange: (v) => setInput({ ...input, uncertainty: v }),
              items: ["Low", "Medium", "High"] as const,
            })}
          </Control>
          <Button className="h-14 w-full text-xs tracking-[.2em]" onClick={run} disabled={running}>
            {running ? "RUNNING" : "RUN"} <ArrowRight />
          </Button>
        </div>
      </section>
      {running && (
        <section className={`${section} bg-foreground text-background`}>
          {stages.map((s, i) => (
            <div
              key={s}
              className={cn(
                "grid grid-cols-[2rem_1fr_auto] border-t border-background/20 py-4 text-background/30",
                i <= step && "text-background",
              )}
            >
              <span className="text-[10px]">0{i + 1}</span>
              <span className="text-xs tracking-[.16em]">{s}</span>
              {i < step && <Check className="size-4" />}
            </div>
          ))}
        </section>
      )}
      <section className="grid grid-cols-2 border-y border-border lg:grid-cols-4">
        {[
          [primary?.feasibility ?? 97.8, "%", "FUTURE FEASIBILITY"],
          [primary?.risk ?? 2.2, "%", "FUTURE RISK"],
          [primary?.energy ?? 13.9, " kWh", "ENERGY"],
          [primary?.travelTime ?? 48, " min", "TRAVEL TIME"],
        ].map(([v, u, l], i) => (
          <div
            key={String(l)}
            className={cn(
              "px-5 py-12",
              i % 2 && "border-l border-border",
              i > 1 && "border-t border-border lg:border-t-0",
              i > 0 && "lg:border-l",
            )}
          >
            <p className="text-5xl font-light sm:text-7xl">
              {v}
              <span className="text-sm">{u}</span>
            </p>
            <Eyebrow className="mt-5">{l}</Eyebrow>
          </div>
        ))}
      </section>
      <section className={section}>
        <Eyebrow>Method comparison</Eyebrow>
        <div className="mt-8 overflow-x-auto">
          <table className="w-full min-w-[700px] border-collapse text-left">
            <thead>
              <tr>
                {["METHOD", "TRAVEL TIME", "ENERGY", "FUTURE FEASIBILITY", "FUTURE RISK"].map(
                  (h) => (
                    <th
                      key={h}
                      className="border-y border-border py-4 text-[9px] tracking-[.14em] text-muted-foreground"
                    >
                      {h}
                    </th>
                  ),
                )}
              </tr>
            </thead>
            <tbody>
              {comparison.map((row: MethodComparisonRow) => (
                <tr key={row.method} className={row.method === "PROPOSED" ? "bg-card" : ""}>
                  <td className="border-b border-border py-5 text-xs font-semibold tracking-[.12em]">
                    {row.method}
                  </td>
                  <td className="border-b border-border py-5">{row.travelTime} min</td>
                  <td className="border-b border-border py-5">{row.energy} kWh</td>
                  <td className="border-b border-border py-5">{row.feasibility}%</td>
                  <td className="border-b border-border py-5">{row.risk}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {isComputed ? (
          <span className="text-[9px] font-semibold tracking-[.16em] text-success">
            ● LIVE RESULT
          </span>
        ) : (
          <DemoLabel>DEMO DATA — REPLACE WITH EXPERIMENTAL RESULTS</DemoLabel>
        )}
      </section>
    </>
  );
}
function Control({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <Eyebrow className="mb-4">{label}</Eyebrow>
      {children}
    </div>
  );
}

const architectureNodes = [
  {
    label: "Data",
    detail:
      "Vehicle telemetry, trips, traffic, charging, weather and demand establish the evidence base.",
  },
  {
    label: "Current state",
    detail:
      "The system forms a synchronized view of battery health, location, energy and present intent.",
  },
  {
    label: "Energy prediction",
    detail:
      "Route-specific energy use is estimated under traffic, terrain and temperature conditions.",
  },
  {
    label: "Battery consequence",
    detail: "Each candidate action is translated into an immediate battery-state consequence.",
  },
  {
    label: "Future state",
    detail: "The resulting state is propagated across the planning horizon with uncertainty.",
  },
  {
    label: "Future mobility",
    detail: "Known and plausible future trips or tasks are tested against available capability.",
  },
  {
    label: "Feasibility",
    detail:
      "The probability of retaining the ability to meet future mobility requirements is quantified.",
  },
  {
    label: "Risk",
    detail: "The system estimates the chance that future requirements become infeasible.",
  },
  {
    label: "Optimizer",
    detail:
      "Candidates are balanced across present cost, travel time, battery consequence and future risk.",
  },
  {
    label: "Decision",
    detail: "A transparent recommendation is selected and its reasoning is retained.",
  },
  {
    label: "Execution",
    detail: "The chosen route, charge or assignment is delivered to the consumer or fleet.",
  },
  {
    label: "Feedback",
    detail: "Observed outcomes return to the system to refine subsequent decisions.",
  },
];

export function ResearchPage() {
  const [activeTab, setActiveTab] = useState("Baseline Comparison");

  return (
    <>
      <PageTitle
        lines={["From today's", "optimization", "to tomorrow's", "feasibility."]}
        kicker="Research framework"
      />
      <section className={`${section} grid gap-10 lg:grid-cols-[.45fr_1fr]`}>
        <Eyebrow>Real problem</Eyebrow>
        <p className="max-w-4xl text-[clamp(2rem,4vw,4.7rem)] font-light leading-[1.08]">
          An EV may successfully complete today's trip while today's route, charging or assignment
          changes the capability available for future mobility.
        </p>
      </section>
      <section className={`${section} border-y border-border`}>
        <Eyebrow>Existing research</Eyebrow>
        <div className="mt-16 border-l border-foreground">
          {research.years.map((y, i) => (
            <div
              key={y.year}
              className="grid gap-6 border-t border-border py-10 pl-7 sm:grid-cols-[.3fr_1fr]"
            >
              <p className="text-6xl font-light">{y.year}</p>
              <div className="grid gap-2 sm:grid-cols-2">
                {y.topics.map((t) => (
                  <p key={t} className="text-sm text-muted-foreground">
                    {t}
                  </p>
                ))}
              </div>
              {i < research.years.length - 1 && (
                <ArrowDown className="ml-[-39px] size-6 bg-background p-1" />
              )}
            </div>
          ))}
          <div className="bg-foreground p-8 text-background">
            <Eyebrow className="text-background/50">Research opportunity</Eyebrow>
            <p className="mt-6 text-4xl font-light uppercase">Future Mobility Feasibility</p>
          </div>
        </div>
      </section>
      <section className={section}>
        <Eyebrow>Research gap</Eyebrow>
        <div className="mt-12 grid gap-px bg-border lg:grid-cols-3">
          <div className="bg-background p-8">
            <Eyebrow>Existing</Eyebrow>
            {[
              "Energy-aware",
              "Battery-aware",
              "Charging-aware",
              "Degradation-aware",
              "Fleet-aware",
              "Uncertainty-aware",
            ].map((x) => (
              <p className="border-t border-border py-3 text-sm" key={x}>
                {x}
              </p>
            ))}
          </div>
          <div className="bg-card p-8">
            <Eyebrow>Limitation</Eyebrow>
            <p className="mt-10 text-2xl font-light leading-9">
              Many individual components are already heavily researched.
            </p>
          </div>
          <div className="bg-foreground p-8 text-background">
            <Eyebrow className="text-background/50">Proposed</Eyebrow>
            <p className="mt-10 text-2xl font-light uppercase leading-9">
              Explicitly quantify future mobility feasibility and future mobility risk as part of
              today's decision.
            </p>
          </div>
        </div>
      </section>
      <section className={`${section} border-y border-border`}>
        <Eyebrow>Interactive architecture</Eyebrow>
        <div className="mt-12">
          <NodeDiagram nodes={architectureNodes} />
        </div>
      </section>

      {/* Validation Results Console */}
      <section className={section}>
        <div className="flex justify-between items-center mb-8">
          <Eyebrow>Validation Results</Eyebrow>
          <DemoLabel>DEMO DATA — AWAITING PIPELINE EXPORT</DemoLabel>
        </div>

        <div className="mt-8 overflow-x-auto pb-4">
          <div className="flex gap-4 min-w-[600px] text-xs font-semibold tracking-[.15em] text-muted-foreground uppercase">
            {["Baseline Comparison", "Independent Replication", "Ablation", "Risk Decomposition", "Sensitivity", "Monotonicity", "Convergence"].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={cn(
                  "pb-2 transition-colors",
                  activeTab === tab ? "text-foreground border-b-2 border-foreground" : "hover:text-foreground cursor-pointer"
                )}
              >
                {tab}
              </button>
            ))}
          </div>
        </div>

        {activeTab === "Baseline Comparison" && (
          <div className="mt-12 animate-in fade-in duration-500">
            <h3 className="text-2xl font-light mb-6">Constraint Feasible Scenario</h3>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[700px] border-collapse text-left">
                <thead>
                  <tr>
                    {["METHOD", "TIME", "ENERGY", "FMR", "STATUS"].map((h) => (
                      <th
                        key={h}
                        className="border-y border-border py-4 text-[9px] tracking-[.14em] text-muted-foreground uppercase"
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  <tr className="hover:bg-card transition-colors">
                    <td className="border-b border-border py-5 text-xs font-semibold tracking-[.12em]">
                      FASTEST
                    </td>
                    <td className="border-b border-border py-5 text-sm">31 min</td>
                    <td className="border-b border-border py-5 text-sm">14.2 kWh</td>
                    <td className="border-b border-border py-5 text-sm text-success">0.02%</td>
                    <td className="border-b border-border py-5 text-xs tracking-widest text-muted-foreground">
                      FEASIBLE
                    </td>
                  </tr>
                  <tr className="hover:bg-card transition-colors">
                    <td className="border-b border-border py-5 text-xs font-semibold tracking-[.12em]">
                      ENERGY_MIN
                    </td>
                    <td className="border-b border-border py-5 text-sm">36 min</td>
                    <td className="border-b border-border py-5 text-sm">12.9 kWh</td>
                    <td className="border-b border-border py-5 text-sm text-success">0.02%</td>
                    <td className="border-b border-border py-5 text-xs tracking-widest text-muted-foreground">
                      FEASIBLE
                    </td>
                  </tr>
                  <tr className="bg-card">
                    <td className="border-b border-border py-5 text-xs font-semibold tracking-[.12em]">
                      ITEREV
                    </td>
                    <td className="border-b border-border py-5 text-sm">33 min</td>
                    <td className="border-b border-border py-5 text-sm">13.5 kWh</td>
                    <td className="border-b border-border py-5 text-sm text-success">0.02%</td>
                    <td className="border-b border-border py-5 text-xs tracking-widest text-muted-foreground">
                      FEASIBLE
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <h3 className="text-2xl font-light mt-16 mb-6">Stress Scenario</h3>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[700px] border-collapse text-left">
                <thead>
                  <tr>
                    {["METHOD", "TIME", "ENERGY", "FMR", "STATUS"].map((h) => (
                      <th
                        key={h}
                        className="border-y border-border py-4 text-[9px] tracking-[.14em] text-muted-foreground uppercase"
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  <tr className="hover:bg-card transition-colors">
                    <td className="border-b border-border py-5 text-xs font-semibold tracking-[.12em]">
                      FASTEST
                    </td>
                    <td className="border-b border-border py-5 text-sm">31 min</td>
                    <td className="border-b border-border py-5 text-sm">14.2 kWh</td>
                    <td className="border-b border-border py-5 text-sm text-amber-500">43.1%</td>
                    <td className="border-b border-border py-5 text-xs tracking-widest text-amber-500">
                      NO FEASIBLE ACTION
                    </td>
                  </tr>
                  <tr className="bg-card">
                    <td className="border-b border-border py-5 text-xs font-semibold tracking-[.12em]">
                      ITEREV
                    </td>
                    <td className="border-b border-border py-5 text-sm">36 min</td>
                    <td className="border-b border-border py-5 text-sm">12.9 kWh</td>
                    <td className="border-b border-border py-5 text-sm text-amber-500">42.2%</td>
                    <td className="border-b border-border py-5 text-xs tracking-widest text-amber-500">
                      NO FEASIBLE ACTION
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab !== "Baseline Comparison" && (
          <div className="mt-12 p-12 border border-border bg-card flex flex-col items-center justify-center min-h-[400px] text-center animate-in fade-in duration-500">
            <Eyebrow className="mb-4">Data pipeline sync required</Eyebrow>
            <h3 className="text-3xl font-light mb-6 uppercase tracking-wider">{activeTab}</h3>
            <p className="text-muted-foreground max-w-lg leading-relaxed text-sm">
              The frontend requires the latest JSON manifest from the Python backend to render the 
              {activeTab.toLowerCase()} visualization.
              <br /><br />
              Run the full experiment suite via CLI: <br />
              <code className="text-xs bg-background px-2 py-1 mt-4 inline-block tracking-widest border border-border">python -m experiments.runner</code>
            </p>
          </div>
        )}
      </section>

      <section className={`${section} grid gap-12 lg:grid-cols-[.4fr_1fr] border-t border-border`}>
        <Eyebrow>Mathematics</Eyebrow>
        <div>
          {research.equations.map((eq, i) => (
            <p
              key={eq}
              className={cn(
                "border-t border-border py-8 font-mono text-xl sm:text-3xl",
                i === 3 && "text-amber-500",
              )}
            >
              {eq}
            </p>
          ))}
        </div>
      </section>
    </>
  );
}

export function SystemPage() {
  const layers = [
    {
      name: "DATA",
      items: ["Vehicle telemetry", "Trips", "Traffic", "Charging", "Weather", "Demand"],
    },
    {
      name: "INTELLIGENCE",
      items: ["Energy prediction", "Battery state", "Future demand", "Scenario generation"],
    },
    { name: "DECISION", items: ["Routing", "Charging", "Fleet assignment"] },
    { name: "FUTURE", items: ["Mobility feasibility", "Mobility risk", "Fleet capacity"] },
  ];
  return (
    <>
      <PageTitle lines={["Inside", "future mobility"]} kicker="System / about" />
      <section className={section}>
        <Eyebrow>System landscape</Eyebrow>
        <div className="mt-12 grid gap-px bg-border lg:grid-cols-4">
          {layers.map((layer, i) => (
            <div
              key={layer.name}
              className={cn(
                "relative min-h-96 p-7",
                i === 3 ? "bg-foreground text-background" : "bg-background",
              )}
            >
              <span className="text-[10px] opacity-50">0{i + 1}</span>
              <h2 className="mt-10 text-3xl font-light">{layer.name}</h2>
              <div className="mt-20">
                {layer.items.map((item) => (
                  <p className="border-t border-current/20 py-3 text-sm opacity-70" key={item}>
                    {item}
                  </p>
                ))}
              </div>
              {i < 3 && (
                <ArrowRight className="absolute -right-3 top-12 z-10 size-6 bg-background p-1" />
              )}
            </div>
          ))}
        </div>
      </section>
      <section className="grid border-y border-border lg:grid-cols-2">
        <Compare
          title="Consumer"
          items={[
            "Current trip",
            "Future trips",
            "Personal preferences",
            "Battery state",
            "Future trip feasibility",
          ]}
        />
        <Compare
          title="Fleet"
          items={[
            "Current tasks",
            "Future demand",
            "Vehicle health",
            "Charging capacity",
            "Future fleet feasibility",
          ]}
          dark
        />
      </section>
      <section className={`${section} min-h-[80svh]`}>
        <h2 className={ruleTitle}>
          Don't just
          <br />
          optimize
          <br />
          the trip.
        </h2>
        <h3 className="mt-24 text-right text-[clamp(3rem,7vw,8rem)] font-medium uppercase leading-[.9]">
          Protect the mobility
          <br />
          that comes after it.
        </h3>
        <div className="mt-20">
          <MobilityThread score={98} />
        </div>
      </section>
    </>
  );
}
function Compare({
  title,
  items,
  dark = false,
}: {
  title: string;
  items: string[];
  dark?: boolean;
}) {
  return (
    <div className={cn("p-8 sm:p-14", dark && "bg-foreground text-background")}>
      <Eyebrow className={dark ? "text-background/50" : ""}>{title}</Eyebrow>
      <h2 className="mt-12 text-6xl font-light uppercase">{title}</h2>
      <div className="mt-20">
        {items.map((i) => (
          <p key={i} className="border-t border-current/20 py-4 text-sm">
            {i}
          </p>
        ))}
      </div>
    </div>
  );
}
