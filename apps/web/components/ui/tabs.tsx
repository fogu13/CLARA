"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

const TabsContext = React.createContext<{
  value: string;
  setValue: (v: string) => void;
} | null>(null);

export function Tabs({ value, onValueChange, children, className }: {
  value: string;
  onValueChange?: (v: string) => void;
  children: React.ReactNode;
  className?: string;
}) {
  const [internalValue, setInternalValue] = React.useState(value);
  const current = onValueChange ? value : internalValue;
  const setValue = onValueChange || setInternalValue;
  return (
    <TabsContext.Provider value={{ value: current, setValue }}>
      <div className={className}>{children}</div>
    </TabsContext.Provider>
  );
}

export function TabsList({ children, className }: { children: React.ReactNode; className?: string }) {
  const listRef = React.useRef<HTMLDivElement>(null);

  // Roving focus: Left/Right (and Home/End) move between tabs and activate
  // the focused one, per the WAI-ARIA tabs pattern.
  function onKeyDown(event: React.KeyboardEvent) {
    const tabs = Array.from(
      listRef.current?.querySelectorAll<HTMLButtonElement>('[role="tab"]') ?? []
    );
    if (tabs.length === 0) return;
    const currentIndex = tabs.indexOf(document.activeElement as HTMLButtonElement);
    let next = -1;
    if (event.key === "ArrowRight") next = (currentIndex + 1) % tabs.length;
    else if (event.key === "ArrowLeft") next = (currentIndex - 1 + tabs.length) % tabs.length;
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = tabs.length - 1;
    if (next >= 0) {
      event.preventDefault();
      tabs[next].focus();
      tabs[next].click();
    }
  }

  return (
    <div
      ref={listRef}
      role="tablist"
      onKeyDown={onKeyDown}
      className={cn("inline-flex h-10 items-center justify-center rounded-md bg-muted p-1 text-muted-foreground", className)}
    >
      {children}
    </div>
  );
}

export function TabsTrigger({ value, children, className }: { value: string; children: React.ReactNode; className?: string }) {
  const ctx = React.useContext(TabsContext);
  if (!ctx) return null;
  const active = ctx.value === value;
  return (
    <button
      role="tab"
      id={`tab-${value}`}
      aria-selected={active}
      aria-controls={`tabpanel-${value}`}
      tabIndex={active ? 0 : -1}
      className={cn(
        "inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 disabled:pointer-events-none disabled:opacity-50",
        active && "bg-background text-foreground shadow-sm",
        className
      )}
      onClick={() => ctx.setValue(value)}
    >
      {children}
    </button>
  );
}

export function TabsContent({ value, children, className }: { value: string; children: React.ReactNode; className?: string }) {
  const ctx = React.useContext(TabsContext);
  if (!ctx || ctx.value !== value) return null;
  return (
    <div
      role="tabpanel"
      id={`tabpanel-${value}`}
      aria-labelledby={`tab-${value}`}
      tabIndex={0}
      className={cn("mt-2 focus-visible:outline-none", className)}
    >
      {children}
    </div>
  );
}
