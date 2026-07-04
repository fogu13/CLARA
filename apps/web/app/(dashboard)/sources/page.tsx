"use client";

import { SignalIntakePanel } from "../../components/signal-intake-panel";
import { useI18n } from "@/lib/i18n";

export default function SourcesPage() {
  const { t } = useI18n();
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">{t.intake.sourcesTitle}</h1>
        <p className="text-sm text-muted-foreground mt-1">{t.intake.sourcesSubtitle}</p>
      </div>

      <SignalIntakePanel />
    </div>
  );
}
