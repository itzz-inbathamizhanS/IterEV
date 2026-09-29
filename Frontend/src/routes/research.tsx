import { createFileRoute } from "@tanstack/react-router";
import { ResearchPage } from "@/components/future-mobility/Pages";

export const Route = createFileRoute("/research")({
  head: () => ({
    meta: [
      { title: "Future Mobility Research Framework" },
      {
        name: "description",
        content: "Explore the research model for future mobility feasibility and risk.",
      },
      { property: "og:title", content: "Future Mobility Research Framework" },
      {
        property: "og:description",
        content: "Explore the research model for future mobility feasibility and risk.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: ResearchPage,
});
