"use client";

import { LearningMemoryPanel } from "../../components/learning-memory-panel";
import { MeasurementCheckpointsPanel } from "../../components/measurement-checkpoints-panel";
import { OutcomeBoardPanel } from "../../components/outcome-board-panel";
import { useI18n } from "@/lib/i18n";

export default function LearningsPage() {
  const { t } = useI18n();
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">{t.learnings.title}</h1>
        <p className="text-sm text-muted-foreground mt-1">{t.learnings.subtitle}</p>
      </div>

      <MeasurementCheckpointsPanel />
      <OutcomeBoardPanel />
      <LearningMemoryPanel />
    </div>
  );
}
