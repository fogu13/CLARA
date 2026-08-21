import type { ReactNode } from "react";
import { SiteFooter, SiteHeader } from "./site-shell";
import "./public.css";

// One shell for the whole public surface: the landing, /research, /pricing,
// /security, /legal/* and /ai-literacy-basics all share this header, footer
// and stylesheet, so leaving the landing never changes the floor underfoot.
export default function PublicLayout({ children }: { children: ReactNode }) {
  return (
    <div className="site">
      <SiteHeader />
      {children}
      <SiteFooter />
    </div>
  );
}
