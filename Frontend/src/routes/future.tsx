import { createFileRoute } from "@tanstack/react-router";
import { FuturePage } from "@/components/future-mobility/Pages";

export const Route = createFileRoute("/future")({
  head: () => ({ meta: [
    { title: "Future Trip Feasibility — Future Mobility" },
    { name: "description", content: "Plan future trips and understand how today changes tomorrow’s mobility." },
    { property: "og:title", content: "Future Trip Feasibility — Future Mobility" },
    { property: "og:description", content: "Plan future trips and understand how today changes tomorrow’s mobility." },
    { property: "og:type", content: "website" },
    { name: "twitter:card", content: "summary_large_image" },
  ] }),
  component: FuturePage,
});
