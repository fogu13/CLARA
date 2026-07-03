import { MeasurementCheckpointsPanel } from "../../components/measurement-checkpoints-panel";
import { OutcomeBoardPanel } from "../../components/outcome-board-panel";

export default function LearningsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Learnings</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Track whether approved actions improved outcomes and capture reviewed learning conclusions.
        </p>
      </div>

      <MeasurementCheckpointsPanel />
      <OutcomeBoardPanel />
    </div>
  );
}
