/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { researchService } from "@/services/researchService";
import { cn } from "@/lib/utils";

type ColumnDef = {
  header: string;
  key: string;
  align?: "left" | "right" | "center" | string;
  className?: (value: any) => string | undefined;
  render?: (value: any, row: any) => React.ReactNode;
};

type ResearchDataTableProps = {
  columns: ColumnDef[];
  rows?: any[];
  loading?: boolean;
  error?: any;
  metadata?: any;
};

function ResearchDataTable({ columns, rows, loading, error, metadata }: ResearchDataTableProps) {
  if (error) {
    return (
      <div className="p-8 border border-destructive/20 bg-destructive/5 text-destructive">
        <p className="font-semibold mb-2">RESEARCH RESULT UNAVAILABLE</p>
        <p className="text-sm">Backend result could not be retrieved.</p>
        {error instanceof Error ? <p className="text-xs mt-2 opacity-70">{error.message}</p> : null}
      </div>
    );
  }

  return (
    <div className="animate-in fade-in duration-300">
      <div className="overflow-x-auto relative">
        <table className="w-full min-w-[700px] border-collapse text-left text-sm">
          <thead>
            <tr>
              {columns.map((col: ColumnDef) => (
                <th
                  key={col.key || col.header}
                  className={cn(
                    "border-y border-border py-4 text-[10px] tracking-[.14em] text-muted-foreground uppercase whitespace-nowrap",
                    col.align === "right" && "text-right",
                  )}
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className={cn(loading && "opacity-40 transition-opacity pointer-events-none")}>
            {rows?.map((row: Record<string, any>, i: number) => (
              <tr key={i} className="hover:bg-card transition-colors border-b border-border">
                {columns.map((col: ColumnDef) => (
                  <td
                    key={col.key || col.header}
                    className={cn(
                      "py-4 whitespace-nowrap",
                      col.align === "right" && "text-right tabular-nums",
                      col.className?.(row[col.key]),
                    )}
                  >
                    {col.render ? col.render(row[col.key], row) : (row[col.key] as React.ReactNode)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="bg-background/80 px-4 py-2 border border-border text-xs tracking-widest uppercase">
              Loading Research Result...
            </span>
          </div>
        )}
      </div>
      {metadata && (
        <div className="mt-4 pt-4 border-t border-border flex flex-wrap gap-x-6 gap-y-2 text-xs text-muted-foreground">
          {metadata.source && <span className="font-mono">Source: {metadata.source}</span>}
          <span>N: {metadata.n ?? 5000}</span>
          <span>Seed: {metadata.seed ?? 42}</span>
        </div>
      )}
    </div>
  );
}

// --- Tabs ---

export function BaselineTab() {
  const [scenario, setScenario] = useState("constraint_feasible");
  const {
    data: result,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["research", "baseline", scenario],
    queryFn: () => researchService.getBaseline(scenario),
  });

  const columns = [
    { header: "METHOD", key: "method", className: () => "font-semibold tracking-wider text-xs" },
    {
      header: "TIME",
      key: "travel_time",
      align: "right",
      render: (v: any) => `${Math.round(Number(v))} min`,
    },
    {
      header: "ENERGY",
      key: "energy_consumption",
      align: "right",
      render: (v: any) => `${Number(v).toFixed(1)} kWh`,
    },
    {
      header: "SOC AFTER",
      key: "soc_after",
      align: "right",
      render: (v: any) => `${Number(v).toFixed(1)}%`,
    },
    {
      header: "SOH LOSS",
      key: "soh_loss",
      align: "right",
      render: (v: any) => `${Number(v).toFixed(4)}%`,
    },
    {
      header: "FMR",
      key: "fmr",
      align: "right",
      className: (v: any) =>
        Number(v) > 10 ? "text-amber-500 font-medium" : "text-success font-medium",
      render: (v: any) => `${Number(v).toFixed(1)}%`,
    },
    {
      header: "95% CI",
      key: "fmr",
      align: "right",
      render: (_: any, row: Record<string, any>) =>
        `${Number(row.fmr_ci_lower).toFixed(1)}–${Number(row.fmr_ci_upper).toFixed(1)}%`,
    },
    {
      header: "STATUS",
      key: "constraint_relaxed",
      className: (v: string) =>
        v === "True"
          ? "text-amber-500 text-xs tracking-widest"
          : "text-muted-foreground text-xs tracking-widest",
      render: (v: string, row: Record<string, any>) =>
        v === "True" ? "CONSTRAINT RELAXED" : row.optimizer_status?.toUpperCase() || "FEASIBLE",
    },
  ];

  return (
    <div>
      <div className="mb-6 flex gap-4 items-center">
        <label className="text-[9px] uppercase tracking-widest text-muted-foreground">
          Scenario
        </label>
        <select
          className="bg-transparent border border-border p-2 text-sm uppercase tracking-wider"
          value={scenario}
          onChange={(e) => setScenario(e.target.value)}
        >
          <option value="constraint_feasible">Constraint Feasible</option>
          <option value="stress_baseline">Stress Baseline</option>
        </select>
      </div>
      <ResearchDataTable
        columns={columns}
        rows={result?.data}
        loading={isLoading}
        error={error}
        metadata={result?.metadata}
      />
    </div>
  );
}

export function AblationTab() {
  const [scenario, setScenario] = useState("High Stress");
  const {
    data: result,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["research", "ablation", scenario],
    queryFn: () => researchService.getAblation(scenario),
  });

  // Calculate delta FMR against IterEV
  const rows = result?.data || [];
  const iterEvRow = rows.find((r) => r.method === "ITEREV" && r.variant === "Full IterEV");
  const iterEvFmr = iterEvRow ? Number(iterEvRow.fmr) : null;

  const rowsWithDelta = rows.map((r) => ({
    ...r,
    delta_fmr: iterEvFmr !== null ? Number(r.fmr) - iterEvFmr : null,
  }));

  const columns = [
    { header: "VARIANT", key: "variant", className: () => "font-semibold" },
    { header: "ROUTE", key: "route_name" },
    {
      header: "FMR",
      key: "fmr",
      align: "right",
      render: (v: any) => `${Number(v).toFixed(1)}%`,
    },
    {
      header: "ΔFMR",
      key: "delta_fmr",
      align: "right",
      render: (v: any) => (v === null ? "—" : v > 0 ? `+${v.toFixed(1)}%` : `${v.toFixed(1)}%`),
      className: (v: any) => (v && v > 0 ? "text-amber-500" : ""),
    },
    {
      header: "95% CI",
      key: "fmr",
      align: "right",
      render: (_: any, row: Record<string, any>) =>
        `${Number(row.fmr_ci_lower).toFixed(1)}–${Number(row.fmr_ci_upper).toFixed(1)}%`,
    },
    {
      header: "FMF",
      key: "fmf",
      align: "right",
      render: (v: any) => `${Number(v).toFixed(1)}%`,
    },
    {
      header: "SOC AFTER",
      key: "soc_after",
      align: "right",
      render: (v: any) => `${Number(v).toFixed(1)}%`,
    },
    {
      header: "STATUS",
      key: "constraint_relaxed",
      className: (v: string) =>
        v === "True"
          ? "text-amber-500 text-xs tracking-widest"
          : "text-muted-foreground text-xs tracking-widest",
      render: (v: string) => (v === "True" ? "CONSTRAINT RELAXED" : "FEASIBLE"),
    },
  ];

  return (
    <div>
      <div className="mb-6 flex gap-4 items-center">
        <label className="text-[9px] uppercase tracking-widest text-muted-foreground">
          Scenario
        </label>
        <select
          className="bg-transparent border border-border p-2 text-sm uppercase tracking-wider"
          value={scenario}
          onChange={(e) => setScenario(e.target.value)}
        >
          <option value="High Stress">High Stress</option>
          <option value="Moderate">Moderate</option>
        </select>
      </div>
      <ResearchDataTable
        columns={columns}
        rows={rowsWithDelta}
        loading={isLoading}
        error={error}
        metadata={{ ...result?.metadata, n: 1000, seed: "42 (Ablation)" }}
      />
    </div>
  );
}

export function ReplicationTab() {
  const {
    data: result,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["research", "replication"],
    queryFn: () => researchService.getReplication(),
  });

  const columns = [
    { header: "CASE", key: "case", className: () => "font-semibold" },
    { header: "SOC", key: "soc", align: "right" },
    { header: "SOH", key: "soh", align: "right" },
    { header: "DEMAND", key: "demand" },
    { header: "CHARGING", key: "charging" },
    {
      header: "PREDICTED FMR",
      key: "predicted_fmr",
      align: "right",
      render: (v: any) => `${Number(v).toFixed(1)}%`,
    },
    {
      header: "OBSERVED RATE",
      key: "observed_failure_rate",
      align: "right",
      render: (v: any) => `${Number(v).toFixed(1)}%`,
    },
    {
      header: "ERROR",
      key: "replication_error",
      align: "right",
      render: (v: any) => `${Number(v).toFixed(2)}%`,
    },
    {
      header: "95% CI",
      key: "val_ci_lower",
      align: "right",
      render: (_: any, row: Record<string, any>) =>
        `${Number(row.val_ci_lower).toFixed(1)}–${Number(row.val_ci_upper).toFixed(1)}%`,
    },
  ];

  return (
    <div>
      <div className="mb-6 p-4 border border-foreground/10 bg-muted/50 text-xs text-muted-foreground">
        Independent simulation replication using a separate random seed; no real-world dataset is
        used.
      </div>
      <ResearchDataTable
        columns={columns}
        rows={result?.data}
        loading={isLoading}
        error={error}
        metadata={{
          source: result?.metadata?.source,
          n: result?.data?.[0]?.validation_scenarios || 2000,
          seed: result?.data?.[0]?.validation_seed || 4242,
        }}
      />
    </div>
  );
}

export function MonotonicityTab() {
  const [param, setParam] = useState("SOC");
  const {
    data: result,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["research", "monotonicity"],
    queryFn: () => researchService.getMonotonicity(),
  });

  const rows =
    result?.data?.filter((r: any) => r.parameter.toLowerCase() === param.toLowerCase()) || [];

  const columns = [
    {
      header: "PARAMETER",
      key: "parameter",
      className: () => "uppercase font-semibold tracking-wider text-xs",
    },
    { header: "VALUE", key: "value", align: "right" },
    {
      header: "FMR",
      key: "fmr",
      align: "right",
      render: (v: any) => `${Number(v).toFixed(1)}%`,
    },
    {
      header: "95% CI",
      key: "ci_lower",
      align: "right",
      render: (_: any, row: Record<string, any>) =>
        `${Number(row.ci_lower).toFixed(1)}–${Number(row.ci_upper).toFixed(1)}%`,
    },
    { header: "SELECTED ROUTE", key: "selected_route" },
    {
      header: "STATUS",
      key: "constraint_status",
      className: () => "text-xs tracking-widest text-muted-foreground",
    },
    {
      header: "MONOTONICITY",
      key: "monotonicity_flag",
      className: (v: string) => (v === "True" ? "text-success" : "text-amber-500"),
      render: (v: string) => (v === "True" ? "PRESERVED" : "VIOLATED"),
    },
  ];

  return (
    <div>
      <div className="mb-6 flex gap-4 items-center">
        <label className="text-[9px] uppercase tracking-widest text-muted-foreground">
          Parameter
        </label>
        <select
          className="bg-transparent border border-border p-2 text-sm uppercase tracking-wider"
          value={param}
          onChange={(e) => setParam(e.target.value)}
        >
          {["SOC", "SOH", "Temperature", "Demand", "Charging", "Horizon"].map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
      </div>
      <ResearchDataTable
        columns={columns}
        rows={rows}
        loading={isLoading}
        error={error}
        metadata={result?.metadata}
      />
    </div>
  );
}

export function SensitivityTab() {
  const [param, setParam] = useState("SOC");
  const {
    data: result,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["research", "sensitivity", param],
    queryFn: () => researchService.getSensitivity(param),
  });

  const parameterKeyMap: Record<string, string> = {
    SOC: "soc",
    SOH: "soh",
    Temperature: "temperature",
    Demand: "demand",
    Charging: "charging_availability",
    Horizon: "planning_horizon",
    Uncertainty: "uncertainty",
  };
  const valueKey = parameterKeyMap[param];

  const columns = [
    { header: param.toUpperCase(), key: valueKey, align: "right" },
    { header: "METHOD", key: "method", className: () => "font-semibold tracking-wider text-xs" },
    {
      header: "TIME",
      key: "travel_time",
      align: "right",
      render: (v: any) => `${Math.round(Number(v))} min`,
    },
    {
      header: "ENERGY",
      key: "energy_consumption",
      align: "right",
      render: (v: any) => `${Number(v).toFixed(1)} kWh`,
    },
    {
      header: "FMR",
      key: "fmr",
      align: "right",
      className: (v: any) =>
        Number(v) > 10 ? "text-amber-500 font-medium" : "text-foreground font-medium",
      render: (v: any) => `${Number(v).toFixed(1)}%`,
    },
    {
      header: "95% CI",
      key: "fmr",
      align: "right",
      render: (_: any, row: Record<string, any>) =>
        `${Number(row.fmr_ci_lower).toFixed(1)}–${Number(row.fmr_ci_upper).toFixed(1)}%`,
    },
  ];

  return (
    <div>
      <div className="mb-6 flex gap-4 items-center">
        <label className="text-[9px] uppercase tracking-widest text-muted-foreground">
          Parameter
        </label>
        <select
          className="bg-transparent border border-border p-2 text-sm uppercase tracking-wider"
          value={param}
          onChange={(e) => setParam(e.target.value)}
        >
          {Object.keys(parameterKeyMap).map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
      </div>
      <ResearchDataTable
        columns={columns}
        rows={result?.data}
        loading={isLoading}
        error={error}
        metadata={result?.metadata}
      />
    </div>
  );
}

export function ConvergenceTab() {
  const {
    data: result,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["research", "convergence"],
    queryFn: () => researchService.getConvergence(),
  });

  const columns = [
    { header: "N", key: "N", align: "right" },
    {
      header: "FMR",
      key: "fmr",
      align: "right",
      render: (v: any) => `${Number(v).toFixed(2)}%`,
    },
    {
      header: "CI LOWER",
      key: "fmr_ci_lower",
      align: "right",
      render: (v: any) => `${Number(v).toFixed(2)}%`,
    },
    {
      header: "CI UPPER",
      key: "fmr_ci_upper",
      align: "right",
      render: (v: any) => `${Number(v).toFixed(2)}%`,
    },
    {
      header: "CI WIDTH",
      key: "absolute_ci_width",
      align: "right",
      render: (v: any) => `${Number(v).toFixed(2)}%`,
    },
    { header: "FAILURES", key: "failures", align: "right" },
    {
      header: "COMP TIME",
      key: "computation_time_s",
      align: "right",
      render: (v: any) => `${Number(v).toFixed(3)} s`,
    },
  ];

  return (
    <ResearchDataTable
      columns={columns}
      rows={result?.data}
      loading={isLoading}
      error={error}
      metadata={{ source: result?.metadata?.source, n: "Variable" }}
    />
  );
}

export function RiskDecompositionTab() {
  const {
    data: result,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["research", "risk-decomposition"],
    queryFn: () => researchService.getRiskDecomposition(),
    retry: false,
  });

  const columns = [
    { header: "COMPONENT", key: "component", className: () => "font-semibold" },
    {
      header: "BASELINE FMR",
      key: "baseline_fmr",
      align: "right",
      render: (v: any) => `${Number(v).toFixed(1)}%`,
    },
    {
      header: "VARIANT FMR",
      key: "variant_fmr",
      align: "right",
      render: (v: any) => `${Number(v).toFixed(1)}%`,
    },
    {
      header: "ΔFMR",
      key: "delta_fmr",
      align: "right",
      render: (v: any) => (v > 0 ? `+${Number(v).toFixed(1)}%` : `${Number(v).toFixed(1)}%`),
    },
    {
      header: "95% CI",
      key: "ci_lower",
      align: "right",
      render: (_: any, row: Record<string, any>) =>
        `${Number(row.ci_lower).toFixed(1)}–${Number(row.ci_upper).toFixed(1)}%`,
    },
  ];

  return (
    <ResearchDataTable
      columns={columns}
      rows={result?.data}
      loading={isLoading}
      error={error}
      metadata={result?.metadata}
    />
  );
}

export function TrajectoriesTab() {
  const {
    data: result,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["research", "trajectories"],
    queryFn: () => researchService.getTrajectories(),
  });

  const columns = [
    { header: "SCENARIO ID", key: "scenario_id", className: () => "font-mono text-xs" },
    {
      header: "DAY 0",
      key: "day_0",
      align: "right",
      render: (v: any) => `${Number(v).toFixed(1)}%`,
    },
    {
      header: "DAY 1",
      key: "day_1",
      align: "right",
      render: (v: any) => `${Number(v).toFixed(1)}%`,
    },
    {
      header: "DAY 2",
      key: "day_2",
      align: "right",
      render: (v: any) => `${Number(v).toFixed(1)}%`,
    },
    {
      header: "DAY 3",
      key: "day_3",
      align: "right",
      render: (v: any) => `${Number(v).toFixed(1)}%`,
    },
    {
      header: "DAY 4",
      key: "day_4",
      align: "right",
      render: (v: any) => `${Number(v).toFixed(1)}%`,
    },
    {
      header: "DAY 5",
      key: "day_5",
      align: "right",
      render: (v: any) => `${Number(v).toFixed(1)}%`,
    },
  ];

  return (
    <ResearchDataTable
      columns={columns}
      rows={result?.data?.slice(0, 100)} // Show first 100 trajectories
      loading={isLoading}
      error={error}
      metadata={result?.metadata}
    />
  );
}

export function FailureTaxonomyTab() {
  const {
    data: result,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["research", "failure-taxonomy"],
    queryFn: () => researchService.getFailureTaxonomy(),
  });

  // Convert JSON to rows
  const rawData = result?.data || {};
  const total = Object.values(rawData).reduce((acc: number, val: any) => acc + Number(val), 0) || 1;
  const rows = Object.entries(rawData).map(([mode, count]) => ({
    mode,
    count: Number(count),
    percentage: (Number(count) / total) * 100,
  }));

  const columns = [
    { header: "FAILURE MODE", key: "mode", className: () => "font-semibold" },
    { header: "COUNT", key: "count", align: "right" },
    {
      header: "PERCENTAGE",
      key: "percentage",
      align: "right",
      render: (v: any) => `${Number(v).toFixed(1)}%`,
    },
  ];

  return (
    <ResearchDataTable
      columns={columns}
      rows={rows}
      loading={isLoading}
      error={error}
      metadata={{ source: result?.metadata?.source, n: total }}
    />
  );
}

export function ResearchTabs({ activeTab }: { activeTab: string }) {
  switch (activeTab) {
    case "Baseline Comparison":
      return <BaselineTab />;
    case "Ablation":
      return <AblationTab />;
    case "Independent Replication":
      return <ReplicationTab />;
    case "Risk Decomposition":
      return <RiskDecompositionTab />;
    case "Sensitivity":
      return <SensitivityTab />;
    case "Monotonicity":
      return <MonotonicityTab />;
    case "Convergence":
      return <ConvergenceTab />;
    case "Failure Taxonomy":
      return <FailureTaxonomyTab />;
    case "Trajectories":
      return <TrajectoriesTab />;
    default:
      return <BaselineTab />;
  }
}
