import { createFileRoute } from "@tanstack/react-router";
import { SimulationPage } from "@/components/future-mobility/Pages";

export const Route = createFileRoute("/simulation")({
  head: () => ({
    meta: [
      { title: "EV Research Simulation — Future Mobility" },
      {
        name: "description",
        content: "Test deterministic EV battery, demand, charging, and traffic scenarios.",
      },
      { property: "og:title", content: "EV Research Simulation — Future Mobility" },
      {
        property: "og:description",
        content: "Test deterministic EV battery, demand, charging, and traffic scenarios.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: SimulationPage,
});
