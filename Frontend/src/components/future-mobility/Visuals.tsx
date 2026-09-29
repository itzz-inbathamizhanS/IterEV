import { useState } from "react";
import { ArrowDown, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";

export function Eyebrow({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <p
      className={cn(
        "text-[10px] font-semibold uppercase tracking-[0.22em] text-muted-foreground",
        className,
      )}
    >
      {children}
    </p>
  );
}

export function PageTitle({ lines, kicker }: { lines: string[]; kicker?: string }) {
  return (
    <header className="border-b border-border px-5 pb-12 pt-20 sm:px-10 sm:pb-16 sm:pt-28 lg:px-16">
      {kicker && <Eyebrow className="mb-7">{kicker}</Eyebrow>}
      <h1 className="font-display text-[clamp(3.6rem,10vw,9rem)] font-medium uppercase leading-[0.82] tracking-normal">
        {lines.map((line) => (
          <span className="block" key={line}>
            {line}
          </span>
        ))}
      </h1>
    </header>
  );
}

export function DemoLabel({ children = "SIMULATION EXAMPLE" }: { children?: React.ReactNode }) {
  return (
    <span className="inline-flex border border-border px-2 py-1 text-[9px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
      {children}
    </span>
  );
}

export function MobilityThread({ score = 97 }: { score?: number }) {
  return (
    <div className="py-8">
      <div className="mb-3 grid grid-cols-3 text-[10px] font-semibold uppercase tracking-[0.2em]">
        <span>Today</span>
        <span className="text-center">Tomorrow</span>
        <span className="text-right">Future</span>
      </div>
      <div className="relative h-px bg-border">
        <div
          className="thread-flow absolute inset-y-0 left-0 bg-gradient-to-r from-success via-foreground to-success"
          style={{ width: `${score}%` }}
        />
        <span
          className="absolute top-1/2 size-3 -translate-y-1/2 border border-foreground bg-background transition-all duration-700"
          style={{ left: `calc(${score}% - 6px)`, borderRadius: "50%" }}
        />
      </div>
    </div>
  );
}

export function BatteryMemory({
  current,
  after,
  tomorrow,
}: {
  current: number;
  after: number;
  tomorrow: number;
}) {
  const values = [
    { label: "CURRENT", value: current },
    { label: "AFTER TODAY", value: after },
    { label: "TOMORROW", value: tomorrow },
  ];
  return (
    <div className="grid gap-0 border-y border-border sm:grid-cols-3">
      {values.map((item, index) => (
        <div
          key={item.label}
          className={cn(
            "relative px-5 py-7 transition-all duration-500 sm:px-7",
            index > 0 && "border-t border-border sm:border-l sm:border-t-0",
          )}
        >
          <Eyebrow>{item.label}</Eyebrow>
          <p className="mt-5 text-5xl font-light tabular-nums">
            {item.value}
            <span className="text-base">%</span>
          </p>
          <div className="mt-6 h-1 bg-muted">
            <div
              className="h-full bg-foreground transition-all duration-700"
              style={{ width: `${item.value}%` }}
            />
          </div>
          {index < 2 && (
            <ArrowRight className="absolute -right-3 top-1/2 z-10 hidden size-6 bg-background p-1 sm:block" />
          )}
        </div>
      ))}
    </div>
  );
}

export function CapacityArc({
  current,
  future,
  risk,
}: {
  current: number;
  future: number;
  risk: number;
}) {
  const dash = Math.min(214, future * 2.14);
  return (
    <div className="relative mx-auto aspect-square w-full max-w-[330px]">
      <svg
        viewBox="0 0 240 240"
        className="h-full w-full -rotate-[130deg]"
        aria-label={`Future capacity ${future}%`}
      >
        <circle
          cx="120"
          cy="120"
          r="82"
          fill="none"
          stroke="currentColor"
          className="text-border"
          strokeWidth="1"
          strokeDasharray="214 302"
          strokeLinecap="butt"
        />
        <circle
          cx="120"
          cy="120"
          r="82"
          fill="none"
          stroke="currentColor"
          className="text-success transition-all duration-700"
          strokeWidth="5"
          strokeDasharray={`${dash} 302`}
          strokeLinecap="butt"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
        <Eyebrow>Future capacity</Eyebrow>
        <div className="mt-2 text-6xl font-light tabular-nums">{future}%</div>
        <p className="mt-3 text-xs text-muted-foreground">
          Current {current}% · Risk {risk}%
        </p>
      </div>
    </div>
  );
}

export function VehicleSilhouette({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 160 64"
      className={cn("w-full", className)}
      aria-label="Electric vehicle silhouette"
    >
      <path
        d="M9 42h8l11-20c3-5 8-8 14-8h66c8 0 14 3 19 9l14 19h10v10h-9a14 14 0 0 1-27 0H49a14 14 0 0 1-27 0H9V42Z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
      />
      <path d="M36 22h36v20H26m54-20h29l18 20H80V22Z" fill="none" stroke="currentColor" />
      <circle cx="36" cy="50" r="7" fill="var(--background)" stroke="currentColor" />
      <circle cx="128" cy="50" r="7" fill="var(--background)" stroke="currentColor" />
    </svg>
  );
}

export type TraceItem = { label: string; value: string };
export function DecisionTrace({ items }: { items: TraceItem[] }) {
  return (
    <div className="grid gap-0 border-y border-border md:grid-cols-5">
      {items.map((item, index) => (
        <div
          key={item.label}
          className={cn(
            "relative min-w-0 px-4 py-6",
            index > 0 && "border-t border-border md:border-l md:border-t-0",
          )}
        >
          <Eyebrow>{item.label}</Eyebrow>
          <p className="mt-4 text-sm leading-relaxed">{item.value}</p>
          {index < items.length - 1 && (
            <ArrowDown className="absolute -bottom-3 left-4 z-10 size-6 bg-background p-1 md:hidden" />
          )}
        </div>
      ))}
    </div>
  );
}

export function NodeDiagram({ nodes }: { nodes: { label: string; detail: string }[] }) {
  const [active, setActive] = useState(0);
  return (
    <div className="grid gap-8 lg:grid-cols-[1fr_.7fr]">
      <div>
        {nodes.map((node, index) => (
          <button
            key={node.label}
            onClick={() => setActive(index)}
            className={cn(
              "grid w-full grid-cols-[2rem_1fr_auto] items-center border-t border-border py-4 text-left transition-colors",
              active === index ? "text-foreground" : "text-muted-foreground hover:text-foreground",
            )}
          >
            <span className="text-[10px] tabular-nums">{String(index + 1).padStart(2, "0")}</span>
            <span className="text-sm font-medium uppercase tracking-[0.15em]">{node.label}</span>
            <ArrowRight
              className={cn("size-4 transition-transform", active === index && "translate-x-1")}
            />
          </button>
        ))}
      </div>
      <aside className="border-l border-border pl-8 lg:pt-24">
        <Eyebrow>Purpose / {String(active + 1).padStart(2, "0")}</Eyebrow>
        <h3 className="mt-6 text-4xl font-light uppercase">{nodes[active]?.label}</h3>
        <p className="mt-6 max-w-md text-base leading-7 text-muted-foreground">
          {nodes[active]?.detail}
        </p>
      </aside>
    </div>
  );
}
