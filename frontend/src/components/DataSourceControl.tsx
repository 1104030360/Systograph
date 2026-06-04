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
    <div className="source-control">
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

      <label className={mode === "api" ? "api-field is-on" : "api-field"}>
        <Server size={13} />
        <input
          aria-label="API base URL"
          disabled={mode !== "api"}
          value={apiBaseUrl}
          onChange={(event) => onApiBaseUrlChange(event.target.value)}
        />
      </label>

      <button
        className="icon-btn"
        type="button"
        disabled={isLoading}
        onClick={onRefresh}
        title="Reload payload"
        aria-label="Reload payload"
      >
        <RefreshCw size={15} />
      </button>

      {error ? <span className="source-error">{error}</span> : null}
    </div>
  );
}
