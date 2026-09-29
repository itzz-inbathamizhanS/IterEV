import { createFileRoute } from "@tanstack/react-router";
import { SystemPage } from "@/components/future-mobility/Pages";

export const Route = createFileRoute("/system")({
  head: () => ({
    meta: [
      { title: "Inside the Future Mobility System" },
      {
        name: "description",
        content:
          "Understand the data, intelligence, decisions, and future outcomes in the platform.",
      },
      { property: "og:title", content: "Inside the Future Mobility System" },
      {
        property: "og:description",
        content:
          "Understand the data, intelligence, decisions, and future outcomes in the platform.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: SystemPage,
});
