import { createFileRoute } from "@tanstack/react-router";
import { HomePage } from "@/components/future-mobility/Pages";

// No head() here: the home route inherits title/description/og/twitter from
// __root.tsx, and ships no og:image so serve-time hosting can inject the
// project's social preview (explicit og:image or latest screenshot).
export const Route = createFileRoute("/")({
  head: () => ({ meta: [
    { title: "Future Mobility — EV Decision Intelligence" },
    { name: "description", content: "Make today's EV decision with tomorrow in mind." },
    { property: "og:title", content: "Future Mobility — EV Decision Intelligence" },
    { property: "og:description", content: "Make today's EV decision with tomorrow in mind." },
    { property: "og:type", content: "website" },
    { name: "twitter:card", content: "summary_large_image" },
  ] }),
  component: HomePage,
});
