import { ChevronDown, Info, RotateCcw, Sparkles } from "lucide-react";
import type { GraphFilterModel, GraphLensModel, ScanSummary } from "../types";
import { LensPanel } from "./LensPanel";

type Props = {
  scanSummary?: ScanSummary;
  scanDepth?: string;
  dataAvailable: boolean;
  filters: GraphFilterModel[];
  lenses: GraphLensModel[];
  activeFilterIds: string[];
  activeLensId: string | null;
  isOpen: boolean;
  onToggleFilter: (id: string) => void;
  onToggleLens: (id: string) => void;
  onClearFilters: () => void;
};

const DEPTH_ROWS = [
  { level: "L1", name: "System", index: 0 },
  { level: "L2", name: "Component", index: 1 },
  { level: "L3", name: "Code Path", index: 2 },
];
const DEPTH_ORDER = ["system", "component", "code_path"];

function fdotKind(kind: string): string {
  if (kind === "flow" || kind === "risk" || kind === "mapping") return kind;
  return "";
}

export function Sidebar({
  scanSummary,
  scanDepth,
  dataAvailable,
  filters,
  lenses,
  activeFilterIds,
  activeLensId,
  isOpen,
  onToggleFilter,
  onToggleLens,
  onClearFilters,
}: Props) {
  const cell = (value: number | undefined) => (dataAvailable && value != null ? String(value) : "unknown");
  const missingAndNotConfigured =
    dataAvailable && (scanSummary?.missing_slots != null || scanSummary?.not_configured_slots != null)
      ? String((scanSummary?.missing_slots ?? 0) + (scanSummary?.not_configured_slots ?? 0))
      : "unknown";
  const reached = dataAvailable && scanDepth ? DEPTH_ORDER.indexOf(scanDepth) : -1;
  const scanStatus = dataAvailable ? (scanSummary?.status ?? "unknown") : "unknown";

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
        <div className="summary-compact">
          <div className="summary-status">
            <span className="pulse" />
            <strong>{scanStatus}</strong>
          </div>
          <div className="summary-line">
            <span>{cell(scanSummary?.detected_slots)} detected</span>
            <span>{missingAndNotConfigured} missing</span>
          </div>
          <div className="summary-line">
            <span>{cell(scanSummary?.risk_hints)} risk hints</span>
            <span>{cell(scanSummary?.unmapped_components)} unmapped</span>
          </div>
        </div>
        {!dataAvailable ? (
          <div className="scan-banner is-neutral">
            <Info className="ico" size={14} />
            <span>No map loaded. Summary unavailable until the backend returns a system map.</span>
          </div>
        ) : null}
      </section>

      <LensPanel lenses={lenses} activeLensId={activeLensId} onToggleLens={onToggleLens} />

      <section className="side-section">
        <div className="side-head">
          <span className="eyebrow">View filters</span>
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
