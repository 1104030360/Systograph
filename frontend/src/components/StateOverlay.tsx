import { Info, RefreshCw, WifiOff } from "lucide-react";

export type ViewerState = "loaded" | "loading" | "error" | "empty" | "pending";

type Props = {
  kind: ViewerState;
  apiBaseUrl: string;
  message?: string;
  onRetry: () => void;
  onUseSample: () => void;
};

/**
 * Neutral, honest overlay for non-loaded graph states. Never falls back to
 * sample data silently — inspecting the legacy sample is an explicit action.
 */
export function StateOverlay({ kind, apiBaseUrl, message, onRetry, onUseSample }: Props) {
  if (kind === "loaded") return null;

  if (kind === "empty") {
    return (
      <div className="state-overlay">
        <div className="state-card">
          <div className="state-ico">
            <Info size={20} />
          </div>
          <h3>No project selected</h3>
          <p>Import a project to load a map. No API request is sent until a project is selected.</p>
          <div className="state-actions">
            <button className="btn" type="button" onClick={onUseSample}>
              Inspect legacy sample
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (kind === "loading") {
    return (
      <div className="state-overlay">
        <div className="state-card">
          <div className="state-ico is-loading">
            <div className="spinner" />
          </div>
          <h3>Loading from API</h3>
          <p>Loading the selected project or build from the local Python API.</p>
          <div className="mono">API {apiBaseUrl}</div>
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
          <p>Could not load the backend projection. The legacy sample is never substituted silently.</p>
          <div className="mono">{message ?? `Request to ${apiBaseUrl} failed`}</div>
          <div className="state-actions">
            <button className="btn primary" type="button" onClick={onRetry}>
              <RefreshCw size={14} />
              Retry
            </button>
            <button className="btn" type="button" onClick={onUseSample}>
              Inspect legacy sample
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
          The backend has not produced an ai_system_map for this project. Import and scan a local project to create the
          normalized ten-plane projection.
        </p>
        <div className="state-actions">
          <button className="btn primary" type="button" onClick={onRetry}>
            Check again
          </button>
          <button className="btn" type="button" onClick={onUseSample}>
            Inspect legacy sample
          </button>
        </div>
      </div>
    </div>
  );
}
