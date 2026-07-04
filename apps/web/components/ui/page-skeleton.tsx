"use client";

import { Skeleton } from "@/components/ui/skeleton";
import { useI18n } from "@/lib/i18n";

export function PageSkeleton({ cards = 5 }: { cards?: number }) {
  const { t } = useI18n();
  return (
    <div className="space-y-6" role="status" aria-live="polite" aria-label={t.common.loading}>
      <div className="space-y-2">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-4 w-96 max-w-full" />
      </div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        {Array.from({ length: cards }, (_, i) => (
          <Skeleton key={i} className="h-28" />
        ))}
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <Skeleton className="h-64" />
        <Skeleton className="h-64" />
      </div>
    </div>
  );
}
