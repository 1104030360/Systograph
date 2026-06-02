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
      <div className="segmented-control compact">
        <button className={mode === "sample" ? "is-active" : ""} type="button" onClick={() => onModeChange("sample")}>
          Sample
        </button>
        <button className={mode === "api" ? "is-active" : ""} type="button" onClick={() => onModeChange("api")}>
          API
        </button>
      </div>

      <label className={mode === "api" ? "api-url is-enabled" : "api-url"}>
        <Server size={14} />
        <input
          aria-label="Python API base URL"
          disabled={mode !== "api"}
          value={apiBaseUrl}
          onChange={(event) => onApiBaseUrlChange(event.target.value)}
        />
      </label>

      <button className="icon-button" disabled={isLoading} type="button" onClick={onRefresh} title="Reload viewer payload">
        <RefreshCw size={15} />
      </button>

      {error ? <span className="source-error">{error}</span> : null}
    </div>
  );
}
