import { createFileRoute } from "@tanstack/react-router";
import { RiskPage } from "@/components/future-mobility/Pages";

export const Route = createFileRoute("/risk")({
  head: () => ({ meta: [
    { title: "Future Mobility Risk — Future Mobility" },
    { name: "description", content: "Explore future mobility risk across routes, battery states, and demand scenarios." },
    { property: "og:title", content: "Future Mobility Risk — Future Mobility" },
    { property: "og:description", content: "Explore future mobility risk across routes, battery states, and demand scenarios." },
    { property: "og:type", content: "website" },
    { name: "twitter:card", content: "summary_large_image" },
  ] }),
  component: RiskPage,
});
