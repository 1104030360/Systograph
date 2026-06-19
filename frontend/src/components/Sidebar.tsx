import { Info, RotateCcw, Sparkles } from "lucide-react";
import type { GraphFilterModel, ScanSummary } from "../types";

type Props = {
  scanSummary?: ScanSummary;
  systemType?: string;
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

const LEGEND: Array<[string, string]> = [
  ["var(--line-strong)", "Detected"],
  ["var(--accent)", "Confirmed extension"],
  ["var(--risk)", "Risk hint attached"],
  ["var(--unmapped)", "Needs confirmation"],
  ["var(--text-faint)", "Missing / not configured"],
];

function fdotKind(kind: string): string {
  if (kind === "flow" || kind === "risk" || kind === "mapping") return kind;
  return "";
}

export function Sidebar({
  scanSummary,
  systemType,
  scanDepth,
  dataAvailable,
  filters,
  activeFilterIds,
  isOpen,
  onToggleFilter,
  onClearFilters,
}: Props) {
  const cell = (value: number | undefined) => (dataAvailable && value != null ? String(value) : "—");
  const missingAndNotConfigured =
    dataAvailable && (scanSummary?.missing_slots != null || scanSummary?.not_configured_slots != null)
      ? String((scanSummary?.missing_slots ?? 0) + (scanSummary?.not_configured_slots ?? 0))
      : "—";
  const reached = dataAvailable && scanDepth ? DEPTH_ORDER.indexOf(scanDepth) : -1;

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
          <span className="count mono">{dataAvailable ? (systemType ?? "rag") : "—"}</span>
        </div>
        <div className="summary-grid">
          <div className="summary-cell">
            <div className="v">{cell(scanSummary?.detected_slots)}</div>
            <div className="k">detected</div>
          </div>
          <div className="summary-cell is-warn">
            <div className="v">{missingAndNotConfigured}</div>
            <div className="k">missing / n.c.</div>
          </div>
          <div className="summary-cell is-risk">
            <div className="v">{cell(scanSummary?.risk_hints)}</div>
            <div className="k">risk hints</div>
          </div>
          <div className="summary-cell">
            <div className="v">{cell(scanSummary?.unmapped_components)}</div>
            <div className="k">unmapped</div>
          </div>
        </div>
        {!dataAvailable ? (
          <div className="scan-banner is-neutral">
            <Info className="ico" size={14} />
            <span>No map loaded. Summary unavailable until the backend returns a system map.</span>
          </div>
        ) : null}
      </section>

      <section className="side-section">
        <div className="side-head">
          <span className="eyebrow">Highlight</span>
          <button className="icon-btn" type="button" onClick={onClearFilters} title="Clear highlights" aria-label="Clear highlights">
            <RotateCcw size={14} />
          </button>
        </div>
        <div className="filter-list">
          {filters.map((filter) => {
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
                {filter.label}
                <span className="fcount">{filter.matches_node_ids.length + filter.matches_edge_ids.length}</span>
              </button>
            );
          })}
        </div>
      </section>

      <section className="side-section">
        <div className="side-head">
          <span className="eyebrow">Scan depth</span>
        </div>
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
      </section>

      <section className="side-section grow">
        <div className="side-head">
          <span className="eyebrow">Legend</span>
        </div>
        <div className="legend">
          {LEGEND.map(([color, label]) => (
            <div className="legend-row" key={label}>
              <span className="swatch" style={{ background: color }} />
              {label}
            </div>
          ))}
        </div>
      </section>
    </aside>
  );
}
