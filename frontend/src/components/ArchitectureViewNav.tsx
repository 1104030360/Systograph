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
import { PHASE2_STATUS_LEGEND } from "../utils/assessment";
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
        <h2 id="filter-views-title">Filter</h2>
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

      <div className="dr-filter-scroll">
        <div className="dr-filter-stack" role="group" aria-label="Architecture filter views">
          {views.map((view) => {
            const Icon = ICONS[view.id];
            const active = activeViewId === view.id;
            const description = view.supported ? view.description : view.unavailableReason ?? view.description;
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
                aria-describedby={`filter-description-${view.id}`}
                disabled={!view.supported}
                title={description}
                onClick={() => onSelect(view.id)}
              >
                <span className="dr-filter-icon" aria-hidden="true">
                  <Icon size={15} />
                </span>
                <span className="dr-filter-copy">
                  <strong>{view.label}</strong>
                  <span id={`filter-description-${view.id}`} className="sr-only">{description}</span>
                </span>
                <span className="dr-filter-count">{view.supported ? view.matchesNodeIds.length : "—"}</span>
              </button>
            );
          })}
        </div>
      </div>

      <div className="dr-filter-legend" role="group" aria-label="Assessment and node kind legend">
        <div className="dr-filter-legend-statuses">
          {PHASE2_STATUS_LEGEND.map(({ key, label }) => (
            <span key={key} title={label}>
              <i className={`dr-status-dot s-${key}`} aria-hidden="true" />
              {label}
            </span>
          ))}
        </div>
        <div className="dr-filter-legend-kinds">
          <span title="Reference capability"><i className="dr-kind-mark reference" aria-hidden="true" />Reference</span>
          <span title="Repository component"><i className="dr-kind-mark component" aria-hidden="true" />Repo</span>
          <span title="Declared flow"><i className="dr-edge-mark declared" aria-hidden="true" />Flow</span>
          <span title="Backend mapping"><i className="dr-edge-mark mapping" aria-hidden="true" />Mapping</span>
        </div>
      </div>
    </aside>
  );
}
