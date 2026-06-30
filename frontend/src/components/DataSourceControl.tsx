import { Download, FileJson, FileText, RefreshCw, Server } from "lucide-react";
import type { DataSourceMode } from "../types";

type Props = {
  mode: DataSourceMode;
  apiBaseUrl: string;
  projectPath: string;
  mapJsonPath: string;
  isLoading: boolean;
  isScanning: boolean;
  artifactBusy?: "load-map" | "report";
  error?: string;
  scanError?: string;
  artifactError?: string;
  reportDownloadUrl: string;
  onModeChange: (mode: DataSourceMode) => void;
  onApiBaseUrlChange: (baseUrl: string) => void;
  onProjectPathChange: (path: string) => void;
  onMapJsonPathChange: (path: string) => void;
  onRefresh: () => void;
  onStartScan: () => void;
  onLoadMap: () => void;
  onPreviewReport: () => void;
};

export function DataSourceControl({
  mode,
  apiBaseUrl,
  projectPath,
  mapJsonPath,
  isLoading,
  isScanning,
  artifactBusy,
  error,
  scanError,
  artifactError,
  reportDownloadUrl,
  onModeChange,
  onApiBaseUrlChange,
  onProjectPathChange,
  onMapJsonPathChange,
  onRefresh,
  onStartScan,
  onLoadMap,
  onPreviewReport,
}: Props) {
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
            <div className="source-divider" />
            <label className="api-field is-on">
              <FileJson size={13} />
              <input
                aria-label="Existing map JSON path"
                placeholder="C:\\path\\to\\ai_system_map.json"
                value={mapJsonPath}
                onChange={(event) => onMapJsonPathChange(event.target.value)}
              />
            </label>
            <button
              className="menu-action"
              type="button"
              disabled={Boolean(artifactBusy) || !mapJsonPath.trim()}
              onClick={onLoadMap}
            >
              <FileJson size={15} />
              {artifactBusy === "load-map" ? "Loading map..." : "Load existing map"}
            </button>
            <button
              className="menu-action"
              type="button"
              disabled={Boolean(artifactBusy)}
              onClick={onPreviewReport}
            >
              <FileText size={15} />
              {artifactBusy === "report" ? "Loading report..." : "Preview latest report"}
            </button>
            <a className="menu-action" href={reportDownloadUrl}>
              <Download size={15} />
              Download latest report
            </a>
          </>
        ) : null}

        <button className="menu-action" type="button" disabled={isLoading} onClick={onRefresh}>
          <RefreshCw size={15} />
          Reload payload
        </button>

        {scanError ? <span className="source-error">{scanError}</span> : null}
        {artifactError ? <span className="source-error">{artifactError}</span> : null}
        {error ? <span className="source-error">{error}</span> : null}
      </div>
    </details>
  );
}
