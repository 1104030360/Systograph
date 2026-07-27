import { RefreshCw, Server } from "lucide-react";
import { useDismissibleDetails } from "../hooks/useDismissibleDetails";
import type { DataSourceMode } from "../types";

type Props = {
  mode: DataSourceMode;
  apiBaseUrl: string;
  projectPath: string;
  isLoading: boolean;
  isScanning: boolean;
  error?: string;
  scanError?: string;
  onModeChange: (mode: DataSourceMode) => void;
  onApiBaseUrlChange: (baseUrl: string) => void;
  onProjectPathChange: (path: string) => void;
  onRefresh: () => void;
  onStartScan: () => void;
};

export function DataSourceControl({
  mode,
  apiBaseUrl,
  projectPath,
  isLoading,
  isScanning,
  error,
  scanError,
  onModeChange,
  onApiBaseUrlChange,
  onProjectPathChange,
  onRefresh,
  onStartScan,
}: Props) {
  const detailsRef = useDismissibleDetails();

  return (
    <details ref={detailsRef} className="toolbar-menu source-control">
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
          <>
            <label className="api-field is-on">
              <Server size={13} />
              <input aria-label="API base URL" value={apiBaseUrl} onChange={(event) => onApiBaseUrlChange(event.target.value)} />
            </label>
            <label className="api-field is-on">
              <span className="mono">path</span>
              <input
                aria-label="Local project path"
                placeholder="C:\\path\\to\\project"
                value={projectPath}
                onChange={(event) => onProjectPathChange(event.target.value)}
              />
            </label>
            <button className="menu-action is-primary" type="button" disabled={isScanning || !projectPath.trim()} onClick={onStartScan}>
              <RefreshCw size={15} />
              {isScanning ? "Scanning project..." : "Start scan"}
            </button>
          </>
        ) : null}

        <button className="menu-action" type="button" disabled={isLoading} onClick={onRefresh}>
          <RefreshCw size={15} />
          Reload payload
        </button>

        {scanError ? <span className="source-error">{scanError}</span> : null}
        {error ? <span className="source-error">{error}</span> : null}
      </div>
    </details>
  );
}
