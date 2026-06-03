import { RotateCcw } from "lucide-react";
import type { GraphViewModel } from "../types";

type Props = {
  graph: GraphViewModel;
  scanDepth?: string;
  activeFilterIds: string[];
  onToggleFilter: (id: string) => void;
  onClearFilters: () => void;
};

const DEPTH_ORDER = ["system", "component", "code_path"];

export function Sidebar({ graph, scanDepth, activeFilterIds, onToggleFilter, onClearFilters }: Props) {
  const summary = graph.summary ?? {};
  const reachedDepth = scanDepth ? DEPTH_ORDER.indexOf(scanDepth) : -1;

  return (
    <aside className="sidebar">
      <div className="traffic-lights" aria-hidden="true">
        <span className="light red" />
        <span className="light yellow" />
        <span className="light green" />
      </div>

      <section className="sidebar-section">
        <div className="section-label">System Map</div>
        <h1>KAI-Mind Viewer</h1>
        <p className="sidebar-copy">{String(summary.title ?? "RAG architecture viewer")}</p>
      </section>

      <section className="sidebar-section">
        <div className="section-row">
          <div className="section-label">Highlight</div>
          <button className="icon-button" type="button" onClick={onClearFilters} title="Reset filters">
            <RotateCcw size={15} />
          </button>
        </div>
        <div className="filter-list">
          {graph.filters.available.map((filter) => (
            <button
              className={activeFilterIds.includes(filter.id) ? "filter-pill is-active" : "filter-pill"}
              key={filter.id}
              type="button"
              aria-pressed={activeFilterIds.includes(filter.id)}
              onClick={() => onToggleFilter(filter.id)}
            >
              <span className={`filter-dot ${filter.kind}`} />
              {filter.label}
            </button>
          ))}
        </div>
      </section>

      <section className="sidebar-section">
        <div className="section-label">Depth</div>
        <div className="depth-stack">
          <span className={reachedDepth >= 0 ? "depth-item is-ready" : "depth-item"}>L1 System</span>
          <span className={reachedDepth >= 1 ? "depth-item is-ready" : "depth-item"}>L2 Component</span>
          <span className={reachedDepth >= 2 ? "depth-item is-ready" : "depth-item"}>L3 Code Path</span>
        </div>
      </section>
    </aside>
  );
}
