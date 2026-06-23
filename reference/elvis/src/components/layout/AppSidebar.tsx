import { NavLink, useLocation } from "react-router-dom";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard, Radio, Lightbulb, Workflow, ClipboardList,
  GraduationCap, Plug, Settings, Cable, Scale, Network,
} from "lucide-react";

const navItems = [
  { to: "/app", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/signals", icon: Radio, label: "Signals" },
  { to: "/taxonomy", icon: Network, label: "Taxonomy" },
  { to: "/insights", icon: Lightbulb, label: "Insights" },
  { to: "/rules", icon: Workflow, label: "Rules" },
  { to: "/actions", icon: ClipboardList, label: "Actions" },
  { to: "/learnings", icon: GraduationCap, label: "Learnings" },
  { to: "/sources", icon: Plug, label: "Sources" },
  { to: "/integrations", icon: Cable, label: "Integrations" },
  { to: "/compliance", icon: Scale, label: "Compliance" },
];

export function AppSidebar() {
  const location = useLocation();

  return (
    <aside className="fixed inset-y-0 left-0 z-30 flex w-60 flex-col bg-sidebar border-r border-sidebar-border">
      {/* Logo */}
      <div className="flex h-16 items-center gap-2.5 px-5 border-b border-sidebar-border">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-sidebar-primary">
          <span className="text-sm font-bold text-sidebar-primary-foreground">O</span>
        </div>
        <div>
          <span className="text-sm font-bold text-sidebar-foreground">Odradek</span>
          <span className="block text-[10px] text-sidebar-muted leading-tight">Feedback Loop</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
        {navItems.map((item) => {
          const isActive = item.to === "/app" ? location.pathname === "/app" : location.pathname.startsWith(item.to);
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                isActive
                  ? "bg-sidebar-accent text-sidebar-foreground"
                  : "text-sidebar-muted hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
              )}
            >
              <item.icon className="h-4 w-4 shrink-0" />
              {item.label}
            </NavLink>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="border-t border-sidebar-border p-3">
        <NavLink
          to="/settings"
          className={cn(
            "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
            location.pathname === "/settings"
              ? "bg-sidebar-accent text-sidebar-foreground"
              : "text-sidebar-muted hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
          )}
        >
          <Settings className="h-4 w-4 shrink-0" />
          Settings
        </NavLink>
      </div>
    </aside>
  );
}
