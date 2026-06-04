import { Info, RefreshCw, WifiOff } from "lucide-react";

export type ViewerState = "loaded" | "loading" | "error" | "pending";

type Props = {
  kind: ViewerState;
  apiBaseUrl: string;
  message?: string;
  onRetry: () => void;
  onUseSample: () => void;
};

/**
 * Neutral, honest overlay for non-loaded graph states. Never falls back to
 * sample data silently — "Use sample data" is an explicit user action.
 */
export function StateOverlay({ kind, apiBaseUrl, message, onRetry, onUseSample }: Props) {
  if (kind === "loaded") return null;

  if (kind === "loading") {
    return (
      <div className="state-overlay">
        <div className="state-card">
          <div className="state-ico is-loading">
            <div className="spinner" />
          </div>
          <h3>Loading from API</h3>
          <p>Waiting for the local Python API to respond.</p>
          <div className="mono">GET {apiBaseUrl}/api/map</div>
        </div>
      </div>
    );
  }

  if (kind === "error") {
    return (
      <div className="state-overlay">
        <div className="state-card">
          <div className="state-ico is-error">
            <WifiOff size={20} />
          </div>
          <h3>API unavailable</h3>
          <p>Could not load the viewer payload. Sample data is not shown while in API mode.</p>
          <div className="mono">{message ?? `GET ${apiBaseUrl}/api/map failed`}</div>
          <div className="state-actions">
            <button className="btn primary" type="button" onClick={onRetry}>
              <RefreshCw size={14} />
              Retry
            </button>
            <button className="btn" type="button" onClick={onUseSample}>
              Use sample data
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="state-overlay">
      <div className="state-card">
        <div className="state-ico">
          <Info size={20} />
        </div>
        <h3>No map loaded yet</h3>
        <p>
          The backend has not produced an ai_system_map for this project. Run a scan, or switch to sample data to explore
          the viewer.
        </p>
        <div className="state-actions">
          <button className="btn primary" type="button" onClick={onRetry}>
            Check again
          </button>
          <button className="btn" type="button" onClick={onUseSample}>
            Use sample data
          </button>
        </div>
      </div>
    </div>
  );
}
