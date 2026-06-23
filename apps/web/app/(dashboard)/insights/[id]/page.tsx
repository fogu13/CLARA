// Insight detail — port of reference/elvis/src/pages/InsightDetail.tsx (695 lines)
// TODO(Phase 4): status stepper, severity/team/status badges, summary, impact/confidence/
// contacts scores, correlated signals, timeline, Run Rules, suggested actions, Close the
// Loop panel (Measure now / Record manually) with closure chips.

export default async function InsightDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <div className="p-8">
      <h1 className="text-2xl font-semibold">Insight {id}</h1>
      <p className="text-muted-foreground">TODO: port from reference/elvis/src/pages/InsightDetail.tsx</p>
    </div>
  );
}
