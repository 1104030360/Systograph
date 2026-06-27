import { ChevronDown, Info, RotateCcw, Sparkles } from "lucide-react";
import type { GraphFilterModel, ScanSummary } from "../types";

type Props = {
  scanSummary?: ScanSummary;
  scanDepth?: string;
  dataAvailable: boolean;
  filters: GraphFilterModel[];
  activeFilterIds: string[];
  isOpen: boolean;
  onToggleFilter: (id: string) => void;
  onClearFilters: () => void;
};

const DEPTH_ROWS = [
  { level: "L1", name: "System", index: 0 },
  { level: "L2", name: "Component", index: 1 },
  { level: "L3", name: "Code Path", index: 2 },
];
const DEPTH_ORDER = ["system", "component", "code_path"];

const FILTER_GROUPS = [
  { id: "status", label: "Status", kinds: ["status"] },
  { id: "type", label: "Component type", kinds: ["type"] },
  { id: "flow", label: "Flow", kinds: ["flow"] },
  { id: "review", label: "Review signals", kinds: ["risk", "mapping"] },
] as const;

function fdotKind(kind: string): string {
  if (kind === "flow" || kind === "risk" || kind === "mapping") return kind;
  return "";
}

function filterDisplayLabel(filter: GraphFilterModel): string {
  if (filter.kind === "status") return filter.label.replace(/^Status:\s*/i, "");
  if (filter.kind === "type") return filter.label.replace(/^Type:\s*/i, "");
  return filter.label;
}

export function Sidebar({
  scanSummary,
  scanDepth,
  dataAvailable,
  filters,
  activeFilterIds,
  isOpen,
  onToggleFilter,
  onClearFilters,
}: Props) {
  const cell = (value: number | undefined) => (value != null ? String(value) : "—");
  const missingAndNotConfigured = String(
    (scanSummary?.missing_slots ?? 0) + (scanSummary?.not_configured_slots ?? 0),
  );
  const reached = dataAvailable && scanDepth ? DEPTH_ORDER.indexOf(scanDepth) : -1;
  const scanStatus = scanSummary?.status ?? "unknown";
  const knownFilterKinds = new Set<string>(FILTER_GROUPS.flatMap((group) => group.kinds));
  const groupedFilters = [
    ...FILTER_GROUPS.map((group) => ({
      id: group.id,
      label: group.label,
      filters: filters.filter((filter) => (group.kinds as readonly string[]).includes(filter.kind)),
    })),
    {
      id: "other",
      label: "Other",
      filters: filters.filter((filter) => !knownFilterKinds.has(filter.kind)),
    },
  ].filter((group) => group.filters.length > 0);

  return (
    <aside className={isOpen ? "sidebar is-open" : "sidebar"}>
      <div className="brand">
        <div className="brand-mark">
          <Sparkles size={17} />
        </div>
        <div className="brand-text">
          <strong>Health Doctor</strong>
          <span className="mono">system map viewer</span>
        </div>
      </div>

      <section className="side-section">
        <div className="side-head">
          <span className="eyebrow">Scan summary</span>
        </div>
        {dataAvailable && scanSummary ? (
          <div className="summary-compact">
            <div className="summary-status">
              <span className="pulse" />
              <strong>{scanStatus}</strong>
            </div>
            <div className="summary-line">
              <span><b>{cell(scanSummary.detected_slots)}</b> detected</span>
              <span><b>{missingAndNotConfigured}</b> missing</span>
            </div>
            <div className="summary-line">
              <span><b>{cell(scanSummary.risk_hints)}</b> risk hints</span>
              <span><b>{cell(scanSummary.unmapped_components)}</b> unmapped</span>
            </div>
          </div>
        ) : (
          <div className="summary-empty">
            <span className="summary-empty-icon">
              <Info size={15} />
            </span>
            <div>
              <strong>{dataAvailable ? "Map loaded" : "Waiting for map"}</strong>
              <span>
                {dataAvailable
                  ? "This map does not include scan summary metrics."
                  : "Choose API, enter a project path, then start a scan."}
              </span>
            </div>
          </div>
        )}
      </section>

      <section className="side-section">
        <div className="side-head">
          <span className="eyebrow">View filters</span>
          <button className="icon-btn" type="button" onClick={onClearFilters} title="Clear highlights" aria-label="Clear highlights">
            <RotateCcw size={14} />
          </button>
        </div>
        {groupedFilters.length > 0 ? (
          <div className="filter-groups">
            {groupedFilters.map((group) => (
              <section className="filter-group" key={group.id} aria-labelledby={`filter-group-${group.id}`}>
                <h3 id={`filter-group-${group.id}`}>{group.label}</h3>
                <div className="filter-list">
                  {group.filters.map((filter) => {
                    const active = activeFilterIds.includes(filter.id);
                    return (
                      <button
                        key={filter.id}
                        className={active ? "filter-pill is-active" : "filter-pill"}
                        type="button"
                        aria-pressed={active}
                        onClick={() => onToggleFilter(filter.id)}
                      >
                        <span className={`fdot ${fdotKind(filter.kind)}`} />
                        <span className="filter-label">{filterDisplayLabel(filter)}</span>
                        <span className="fcount">
                          {filter.matches_node_ids.length + filter.matches_edge_ids.length}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </section>
            ))}
          </div>
        ) : (
          <div className="filter-empty">Filters appear after a map is loaded.</div>
        )}
      </section>

      <details className="side-section collapse-section">
        <summary className="collapse-head">
          <span className="eyebrow">Scan depth</span>
          <ChevronDown size={14} />
        </summary>
        <div className="depth-list">
          {DEPTH_ROWS.map((row) => {
            const ready = reached >= row.index;
            const isCurrent = reached === row.index;
            return (
              <div key={row.level} className={ready ? "depth-item is-ready" : "depth-item is-pending"}>
                <span className="dlevel">{row.level}</span>
                <span>{row.name}</span>
                <span className="dstate">{isCurrent ? "current" : ready ? "done" : "pending"}</span>
              </div>
            );
          })}
        </div>
      </details>
    </aside>
  );
}
