import type { TaxonomyNode } from "@/lib/types";
import { Badge } from "@/components/ui/badge";

function NodeRow({ node, depth, onUndo }: { node: TaxonomyNode; depth: number; onUndo?: (id: string) => void }) {
  return (
    <div>
      <div className="flex items-center gap-2 py-1.5 border-b border-border/50" style={{ paddingLeft: depth * 20 }}>
        <span className="text-sm font-medium">{node.name}</span>
        <Badge variant="outline" className="text-[10px]">L{node.level}</Badge>
        {typeof node.match_count === "number" && node.match_count > 0 && (
          <span className="text-xs text-muted-foreground">{node.match_count} signal(s)</span>
        )}
        {node.description && <span className="text-xs text-muted-foreground truncate">— {node.description}</span>}
        {node.auto_promoted && (
          <>
            <Badge variant="outline" className="text-[10px]">auto</Badge>
            {onUndo && (
              <button className="text-[10px] text-muted-foreground underline" onClick={() => onUndo(node.id)}>undo</button>
            )}
          </>
        )}
      </div>
      {node.children?.map((c) => <NodeRow key={c.id} node={c} depth={depth + 1} onUndo={onUndo} />)}
    </div>
  );
}

export function TaxonomyTree({ nodes, onUndo }: { nodes: TaxonomyNode[]; onUndo?: (id: string) => void }) {
  if (!nodes.length) {
    return <p className="text-sm text-muted-foreground py-8 text-center">No taxonomy yet. Upload a CSV or JSON to get started.</p>;
  }
  return <div>{nodes.map((n) => <NodeRow key={n.id} node={n} depth={0} onUndo={onUndo} />)}</div>;
}
