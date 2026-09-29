import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { Menu, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const links = [
  { label: "CONSUMER", to: "/consumer" },
  { label: "FUTURE", to: "/future" },
  { label: "FLEET", to: "/fleet" },
  { label: "RISK", to: "/risk" },
  { label: "SIMULATION", to: "/simulation" },
  { label: "RESEARCH", to: "/research" },
] as const;

export function SiteShell({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-50 grid h-16 grid-cols-[minmax(0,1fr)_auto] items-center border-b border-border bg-background/95 px-5 backdrop-blur-sm sm:px-10 lg:h-20 lg:grid-cols-[1.2fr_2fr_auto] lg:px-16">
        <Link
          to="/"
          className="min-w-0 text-sm font-semibold uppercase tracking-[0.14em] sm:text-base"
        >
          Future Mobility
        </Link>
        <nav className="hidden items-center justify-center gap-7 lg:flex">
          {links.map((link) => (
            <Link
              key={link.to}
              to={link.to}
              className="text-[10px] font-semibold tracking-[0.18em] text-muted-foreground transition-colors hover:text-foreground"
              activeProps={{ className: "text-foreground" }}
            >
              {link.label}
            </Link>
          ))}
        </nav>
        <Button
          variant="ghost"
          size="sm"
          className="rounded-none px-0 text-[10px] tracking-[0.18em]"
          onClick={() => setOpen(true)}
        >
          <Menu /> MENU
        </Button>
      </header>
      {open && (
        <div className="fixed inset-0 z-[60] bg-foreground text-background reveal-up">
          <div className="flex h-16 items-center justify-between border-b border-background/20 px-5 sm:px-10 lg:h-20 lg:px-16">
            <span className="text-sm font-semibold uppercase tracking-[0.14em]">
              Future Mobility
            </span>
            <Button
              variant="ghost"
              size="icon"
              className="text-background hover:bg-background/10 hover:text-background"
              onClick={() => setOpen(false)}
              aria-label="Close menu"
            >
              <X />
            </Button>
          </div>
          <nav className="grid min-h-[calc(100vh-4rem)] content-center px-5 py-12 sm:px-10 lg:px-16">
            {[...links, { label: "SYSTEM / ABOUT", to: "/system" as const }].map((link, index) => (
              <Link
                key={link.to}
                to={link.to}
                onClick={() => setOpen(false)}
                className="grid grid-cols-[2rem_1fr_auto] items-center border-t border-background/20 py-3 text-3xl font-light uppercase transition-all hover:pl-3 sm:text-5xl lg:text-7xl"
              >
                <span className="text-[10px] text-background/50">0{index + 1}</span>
                <span>{link.label}</span>
                <span className="text-base">↗</span>
              </Link>
            ))}
          </nav>
        </div>
      )}
      <main>{children}</main>
      <footer className="grid gap-8 border-t border-border px-5 py-10 sm:grid-cols-2 sm:px-10 lg:grid-cols-3 lg:px-16">
        <p className="text-sm font-semibold uppercase tracking-[0.14em]">Future Mobility</p>
        <p className="max-w-sm text-xs leading-5 text-muted-foreground">
          Future Mobility Feasibility under Battery Health and Demand Uncertainty.
        </p>
        <Link to="/system" className="text-xs uppercase tracking-[0.16em] sm:text-right">
          Inside the system →
        </Link>
      </footer>
    </div>
  );
}
