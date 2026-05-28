"use client";

import type { ReefGraph, ReefNode } from "@/lib/types";
import { useCallback, useEffect, useRef, useState } from "react";

// react-force-graph-2d is dynamically imported to avoid SSR issues
// (it directly accesses `window` during module evaluation).
import dynamic from "next/dynamic";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full text-[var(--color-text-muted)] text-sm">
      Loading graph…
    </div>
  ),
});

/** Colour per source kind */
const SOURCE_COLORS: Record<ReefNode["source_kind"], string> = {
  github: "#6e8efb",
  sentry: "#f76b8a",
  stripe: "#6f72e2",
  linear: "#4e8ce4",
  datadog: "#b57bee",
  osv: "#ff6b6b",
  gmail: "#e06c75",
  slack: "#56b6c2",
};

interface ReefMapProps {
  graph: ReefGraph;
}

interface SelectedNode extends ReefNode {
  x?: number;
  y?: number;
}

/**
 * ReefMap
 *
 * Client Component. Renders a force-directed graph of Coral source nodes and
 * JOIN-relationship edges from the last executed voyage. Clicking a node
 * displays its table count and schema info.
 */
export function ReefMap({ graph }: ReefMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 520 });
  const [selectedNode, setSelectedNode] = useState<SelectedNode | null>(null);

  // Measure the container and update on resize
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) {
        setDimensions({
          width: entry.contentRect.width,
          height: entry.contentRect.height,
        });
      }
    });

    observer.observe(el);
    setDimensions({ width: el.clientWidth, height: el.clientHeight });

    return () => observer.disconnect();
  }, []);

  const handleNodeClick = useCallback((node: object) => {
    const reefNode = node as SelectedNode;
    setSelectedNode((prev) => (prev?.id === reefNode.id ? null : reefNode));
  }, []);

  // Type-annotated graph data for ForceGraph2D
  type GraphNode = ReefNode & { x?: number; y?: number; vx?: number; vy?: number };
  type GraphLink = { source: string; target: string; join_key: string; voyage_id: string };

  const graphData: { nodes: GraphNode[]; links: GraphLink[] } = {
    nodes: graph.nodes as GraphNode[],
    links: graph.links as GraphLink[],
  };

  return (
    <div className="relative w-full h-full" ref={containerRef}>
      <ForceGraph2D
        graphData={graphData}
        width={dimensions.width}
        height={dimensions.height}
        backgroundColor="transparent"
        nodeLabel={(node) => {
          const n = node as ReefNode;
          return `${n.label} (${n.table_count} tables)`;
        }}
        nodeColor={(node) => {
          const n = node as ReefNode;
          return SOURCE_COLORS[n.source_kind] ?? "#7a93b4";
        }}
        nodeRelSize={6}
        linkColor={() => "#1e2d45"}
        linkWidth={1.5}
        linkDirectionalArrowLength={4}
        linkDirectionalArrowRelPos={1}
        linkLabel={(link) => {
          const l = link as GraphLink;
          return `JOIN on ${l.join_key}`;
        }}
        onNodeClick={handleNodeClick}
        nodeCanvasObject={(node, ctx, globalScale) => {
          const n = node as GraphNode;
          const label = n.label;
          const fontSize = 12 / globalScale;
          const x = n.x ?? 0;
          const y = n.y ?? 0;
          const color = SOURCE_COLORS[n.source_kind] ?? "#7a93b4";

          // Draw node circle
          ctx.beginPath();
          ctx.arc(x, y, 6, 0, 2 * Math.PI);
          ctx.fillStyle = color;
          ctx.fill();

          // Highlight ring if selected
          if (selectedNode?.id === n.id) {
            ctx.beginPath();
            ctx.arc(x, y, 8, 0, 2 * Math.PI);
            ctx.strokeStyle = "#ffffff";
            ctx.lineWidth = 1.5 / globalScale;
            ctx.stroke();
          }

          // Draw label
          ctx.font = `${fontSize}px monospace`;
          ctx.fillStyle = "#e8f0fe";
          ctx.textAlign = "center";
          ctx.fillText(label, x, y + 14 / globalScale);
        }}
      />

      {/* Selected node detail panel */}
      {selectedNode && (
        <aside className="absolute top-4 right-4 w-56 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-raise)]/95 backdrop-blur-sm p-4 text-sm">
          <div className="flex items-center justify-between mb-3">
            <h4 className="font-semibold text-[var(--color-text-primary)]">{selectedNode.label}</h4>
            <button
              type="button"
              onClick={() => setSelectedNode(null)}
              className="text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] text-xs"
              aria-label="Close node details"
            >
              ✕
            </button>
          </div>
          <dl className="space-y-1.5 text-xs">
            <div className="flex justify-between">
              <dt className="text-[var(--color-text-muted)]">Kind</dt>
              <dd className="font-mono text-[var(--color-text-primary)]">
                {selectedNode.source_kind}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-[var(--color-text-muted)]">Tables</dt>
              <dd className="font-mono text-[var(--color-text-primary)]">
                {selectedNode.table_count}
              </dd>
            </div>
          </dl>
        </aside>
      )}

      {/* Empty state */}
      {graph.nodes.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center text-[var(--color-text-muted)] text-sm">
          No graph data — run a voyage to populate the Reef Map.
        </div>
      )}
    </div>
  );
}
