import { createFileRoute } from "@tanstack/react-router";
import { ConsumerPage } from "@/components/future-mobility/Pages";

export const Route = createFileRoute("/consumer")({
  head: () => ({
    meta: [
      { title: "Consumer EV Decisions — Future Mobility" },
      {
        name: "description",
        content: "Compare EV routes by energy, battery consequence, and future trip feasibility.",
      },
      { property: "og:title", content: "Consumer EV Decisions — Future Mobility" },
      {
        property: "og:description",
        content: "Compare EV routes by energy, battery consequence, and future trip feasibility.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: ConsumerPage,
});
