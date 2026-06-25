import { redirect } from "next/navigation";

// "/" is served by the static marketing landing (public/home.html) via a
// beforeFiles rewrite in next.config.mjs. This component is only reached if that
// rewrite is ever removed; it then falls back to the marketing page.
export default function RootPage() {
  redirect("/home.html");
}
