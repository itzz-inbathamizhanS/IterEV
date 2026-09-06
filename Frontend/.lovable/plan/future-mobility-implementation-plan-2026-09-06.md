# Future Mobility — implementation plan

## Experience
- Build one cohesive premium editorial interface across exactly eight routes: Home, Consumer, Future, Fleet, Risk, Simulation, Research, and System.
- Use an ivory/white/near-black design system with restrained green, amber, and red states; large editorial type; thin rules; asymmetric layouts; and no photo-led sections.
- Add a shared sticky desktop navigation and a focused full-screen mobile menu.

## Core visuals and interactions
- Create reusable technical visuals for the mobility thread, battery memory, future-capacity arc, decision trace, vehicle state, route map, risk timelines, and architecture diagrams.
- Add purposeful motion for route flow, vehicle movement, state transitions, number changes, progressive disclosure, and simulation progress, with reduced-motion support.
- Make route selection, vehicle selection, future-trip editing, architecture nodes, timelines, and simulation controls interactive.

## Data and logic
- Keep all demo content in the requested JSON files.
- Add service modules for vehicles, routes, batteries, future mobility, fleets, and simulations.
- Implement deterministic formulas so battery health, temperature, traffic, demand, charging availability, horizon, and uncertainty visibly affect simulation results.
- Label all illustrative results as “Simulation example” or “Demo data.”

## Technical implementation
- Use the existing React/TanStack Start structure, Tailwind CSS token system, Lucide icons, and Recharts where appropriate.
- Create route-specific metadata for all eight pages.
- Keep route and research logic outside visual components and organize shared page furniture and visual primitives into focused modules.

## Validation
- Verify all navigation links and interactive flows in the running preview.
- Check representative desktop and mobile viewports for layout integrity, readable typography, non-overlapping controls, and working animations.
