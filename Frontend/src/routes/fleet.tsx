import { createFileRoute } from "@tanstack/react-router";
import { FleetPage } from "@/components/future-mobility/Pages";

export const Route = createFileRoute("/fleet")({
  head: () => ({ meta: [
    { title: "Fleet Capacity Intelligence — Future Mobility" },
    { name: "description", content: "Balance today’s EV fleet assignments with tomorrow’s capacity and demand." },
    { property: "og:title", content: "Fleet Capacity Intelligence — Future Mobility" },
    { property: "og:description", content: "Balance today’s EV fleet assignments with tomorrow’s capacity and demand." },
    { property: "og:type", content: "website" },
    { name: "twitter:card", content: "summary_large_image" },
  ] }),
  component: FleetPage,
});
