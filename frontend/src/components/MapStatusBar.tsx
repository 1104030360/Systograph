type Props = {
  mappingCompleteness: number | null;
  normalizedNodes: number;
  declaredEdges: number;
  referenceMapVersion: string | null;
  projectionActive: boolean;
  sourceLabel: string;
};

export function MapStatusBar({
  mappingCompleteness,
  normalizedNodes,
  declaredEdges,
  referenceMapVersion,
  projectionActive,
  sourceLabel,
}: Props) {
  const percent =
    mappingCompleteness == null
      ? null
      : Math.round(Math.min(100, Math.max(0, mappingCompleteness * 100)) * 10) / 10;
  const percentLabel = percent == null ? "—" : `${percent.toFixed(1)}%`;

  return (
    <footer className="dr-status-bar" aria-label="Current map metrics">
      <div className="dr-status-quality">
        <i className="dr-status-live-dot" aria-hidden="true" />
        <span>Mapping completeness</span>
        <strong>{percentLabel}</strong>
        <span
          className="dr-status-progress"
          role="progressbar"
          aria-label="Mapping completeness"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={percent ?? undefined}
          aria-valuetext={percentLabel}
        >
          <i style={{ width: `${percent ?? 0}%` }} />
        </span>
      </div>

      <div className="dr-status-metrics">
        <span><small>Normalized nodes</small><strong>{normalizedNodes}</strong></span>
        <span><small>Declared edges</small><strong>{declaredEdges}</strong></span>
        <span><small>Reference map</small><strong>{referenceMapVersion ?? "—"}</strong></span>
      </div>

      <div className="dr-status-source">
        <span>{sourceLabel}</span>
        <span className={projectionActive ? "is-active" : ""}>
          <i aria-hidden="true" />
          {projectionActive ? "Reference projection active" : "Projection unavailable"}
        </span>
      </div>
    </footer>
  );
}
