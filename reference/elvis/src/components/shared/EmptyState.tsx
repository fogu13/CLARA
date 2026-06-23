import type { ReactNode } from "react";

export function EmptyState({ title, description, children }: { title: string; description?: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-border py-16 text-center">
      <h3 className="text-sm font-semibold">{title}</h3>
      {description && <p className="mt-1 text-sm text-muted-foreground max-w-md">{description}</p>}
      {children && <div className="mt-4 flex flex-wrap items-center justify-center gap-2">{children}</div>}
    </div>
  );
}
