import { RefreshCw, Server } from "lucide-react";
import type { DataSourceMode } from "../types";

type Props = {
  mode: DataSourceMode;
  apiBaseUrl: string;
  isLoading: boolean;
  error?: string;
  onModeChange: (mode: DataSourceMode) => void;
  onApiBaseUrlChange: (baseUrl: string) => void;
  onRefresh: () => void;
};

export function DataSourceControl({ mode, apiBaseUrl, isLoading, error, onModeChange, onApiBaseUrlChange, onRefresh }: Props) {
  return (
    <details className="toolbar-menu source-control">
      <summary className="source-summary" aria-label={`Source ${mode}`}>
        <Server size={13} />
        <span>Source</span>
        <b>{mode === "sample" ? "Sample" : "API"}</b>
      </summary>

      <div className="toolbar-popover align-right source-popover">
        <div className="segment">
          <button
            className={mode === "sample" ? "is-active" : ""}
            type="button"
            aria-pressed={mode === "sample"}
            onClick={() => onModeChange("sample")}
          >
            Sample
          </button>
          <button
            className={mode === "api" ? "is-active" : ""}
            type="button"
            aria-pressed={mode === "api"}
            onClick={() => onModeChange("api")}
          >
            API
          </button>
        </div>

        {mode === "api" ? (
          <label className="api-field is-on">
            <Server size={13} />
            <input aria-label="API base URL" value={apiBaseUrl} onChange={(event) => onApiBaseUrlChange(event.target.value)} />
          </label>
        ) : null}

        <button className="menu-action" type="button" disabled={isLoading} onClick={onRefresh}>
          <RefreshCw size={15} />
          Reload payload
        </button>

        {error ? <span className="source-error">{error}</span> : null}
      </div>
    </details>
  );
}
