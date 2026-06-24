import { SignalIntakePanel } from "../../components/signal-intake-panel";

export default function SourcesPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Sources</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Import customer signals, validate CSV files and review generated problem candidates.
        </p>
      </div>

      <SignalIntakePanel />
    </div>
  );
}
