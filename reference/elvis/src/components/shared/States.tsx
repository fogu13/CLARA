import { cn } from "@/lib/utils";

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}: {
  icon?: string;
  title: string;
  description: string;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col items-center justify-center py-16 text-center", className)}>
      {icon && <span className="text-5xl mb-4">{icon}</span>}
      <h3 className="text-lg font-semibold text-foreground mb-1">{title}</h3>
      <p className="text-sm text-muted-foreground max-w-sm mb-4">{description}</p>
      {action}
    </div>
  );
}

export function LoadingState({ className }: { className?: string }) {
  return (
    <div className={cn("space-y-4", className)}>
      {[1, 2, 3].map((i) => (
        <div key={i} className="animate-pulse">
          <div className="h-4 bg-muted rounded w-3/4 mb-2" />
          <div className="h-3 bg-muted rounded w-1/2" />
        </div>
      ))}
    </div>
  );
}

export function CardSkeleton({ className }: { className?: string }) {
  return (
    <div className={cn("rounded-lg border bg-card p-6 animate-pulse", className)}>
      <div className="flex items-center justify-between mb-4">
        <div className="h-3 bg-muted rounded w-20" />
        <div className="h-3 bg-muted rounded w-12" />
      </div>
      <div className="h-8 bg-muted rounded w-16 mb-2" />
      <div className="h-3 bg-muted rounded w-32" />
    </div>
  );
}
