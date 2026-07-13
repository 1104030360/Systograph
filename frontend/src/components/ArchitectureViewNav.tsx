import {
  Activity,
  ArrowRightLeft,
  BrainCircuit,
  CircleAlert,
  CircleDot,
  Database,
  FileCode2,
  GitBranch,
  LayoutGrid,
  Network,
  PackageOpen,
  Puzzle,
  Search,
  SearchCheck,
  ShieldCheck,
  TriangleAlert,
  Workflow,
  type LucideIcon,
} from "lucide-react";
import type { ArchitectureViewId, ArchitectureViewModel } from "../utils/architectureViews";

type Props = {
  views: ArchitectureViewModel[];
  activeViewId: ArchitectureViewId;
  search: string;
  onSelect: (id: ArchitectureViewId) => void;
  onSearchChange: (value: string) => void;
};

const ICONS: Record<ArchitectureViewId, LucideIcon> = {
  overview: LayoutGrid,
  dataflow: ArrowRightLeft,
  control: Workflow,
  ingestion: PackageOpen,
  retrieval: SearchCheck,
  memory: Database,
  governance: ShieldCheck,
  runtime: Activity,
  variants: GitBranch,
  known: CircleDot,
  extensions: Puzzle,
  unmapped: CircleAlert,
  reasoning: BrainCircuit,
  topology: Network,
  source: FileCode2,
  risk: TriangleAlert,
};

export function ArchitectureViewNav({ views, activeViewId, search, onSelect, onSearchChange }: Props) {
  return (
    <aside className="dr-filter-panel" aria-labelledby="filter-views-title">
      <div className="dr-panel-heading">
        <span className="eyebrow">Explore the projection</span>
        <h2 id="filter-views-title">Filter Views</h2>
        <p>Each enabled view uses backend-declared plane, lens, status or semantic-kind metadata.</p>
      </div>

      <label className="dr-search-box">
        <Search size={15} aria-hidden="true" />
        <span className="sr-only">Search nodes</span>
        <input
          type="search"
          value={search}
          placeholder="Search nodes..."
          onChange={(event) => onSearchChange(event.currentTarget.value)}
        />
      </label>

      <div className="dr-filter-stack" role="group" aria-label="Architecture filter views">
        {views.map((view) => {
          const Icon = ICONS[view.id];
          const active = activeViewId === view.id;
          return (
            <button
              key={view.id}
              className={[
                "dr-filter-button",
                `dr-view-${view.id}`,
                active ? "is-active" : "",
                view.id === "risk" || view.id === "unmapped" ? "is-warning" : "",
              ]
                .filter(Boolean)
                .join(" ")}
              type="button"
              aria-pressed={active}
              disabled={!view.supported}
              title={view.supported ? view.description : view.unavailableReason ?? view.description}
              onClick={() => onSelect(view.id)}
            >
              <span className="dr-filter-icon" aria-hidden="true">
                <Icon size={15} />
              </span>
              <span className="dr-filter-copy">
                <strong>{view.label}</strong>
                <small>{view.supported ? view.description : view.unavailableReason}</small>
              </span>
              <span className="dr-filter-count">{view.supported ? view.matchesNodeIds.length : "—"}</span>
            </button>
          );
        })}
      </div>

      <div className="dr-schema-card">
        <strong>Backend projection contract</strong>
        <code>10 canonical planes</code>
        <code>reference + repo nodes</code>
        <code>assessment + activation</code>
        <code>evidence + risk details</code>
      </div>
    </aside>
  );
}
