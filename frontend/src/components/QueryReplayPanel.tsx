import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Pause, Play, RotateCcw, Send, SkipBack, SkipForward } from "lucide-react";
import { useQueryTrace } from "../hooks/useQueryTrace";
import type { DataSourceMode, SystemEndpoint, TraceEvent } from "../types";
import { compactId, titleCase } from "../utils/format";
import { sortTraceEvents, traceErrorLabel, traceEventHasFailure } from "../utils/trace";

type Props = {
  mode: DataSourceMode;
  apiBaseUrl: string;
  projectId: string;
  endpoints: SystemEndpoint[];
  events: TraceEvent[];
  activeIndex: number;
  isRunning: boolean;
  onIndexChange: (index: number) => void;
  onRunningChange: (running: boolean) => void;
  onTraceEvents: (events: TraceEvent[]) => void;
};

const TIMEOUT_MIN_SECONDS = 1;
const TIMEOUT_MAX_SECONDS = 120;
const TIMEOUT_DEFAULT_SECONDS = 30;

function clampTimeoutSeconds(raw: string) {
  const value = Number(raw);
  if (!Number.isFinite(value) || value === 0) return TIMEOUT_DEFAULT_SECONDS;
  return Math.min(Math.max(Math.round(value), TIMEOUT_MIN_SECONDS), TIMEOUT_MAX_SECONDS);
}

function endpointLabel(endpoint: SystemEndpoint) {
  const method = endpoint.method ? `${endpoint.method.toUpperCase()} ` : "";
  return `${method}${endpoint.value}`;
}

function statusLabel(status: string | undefined) {
  if (!status) return "Ready";
  return status.replace(/_/g, " ");
}

export function QueryReplayPanel({
  mode,
  apiBaseUrl,
  projectId,
  endpoints,
  events,
  activeIndex,
  isRunning,
  onIndexChange,
  onRunningChange,
  onTraceEvents,
}: Props) {
  const sortedEvents = useMemo(() => sortTraceEvents(events), [events]);
  const active = sortedEvents[activeIndex];
  const maxIndex = Math.max(sortedEvents.length - 1, 0);
  const [selectedEndpointId, setSelectedEndpointId] = useState("");
  const [query, setQuery] = useState("");
  const [timeoutSeconds, setTimeoutSeconds] = useState(TIMEOUT_DEFAULT_SECONDS);
  const [projectIdInput, setProjectIdInput] = useState(projectId);
  const trace = useQueryTrace(apiBaseUrl);

  useEffect(() => {
    if (endpoints.length === 0) {
      setSelectedEndpointId("");
      return;
    }

    if (!endpoints.some((endpoint) => endpoint.id === selectedEndpointId)) {
      setSelectedEndpointId(endpoints[0].id);
    }
  }, [endpoints, selectedEndpointId]);

  useEffect(() => {
    if (projectId && !projectIdInput) {
      setProjectIdInput(projectId);
    }
  }, [projectId, projectIdInput]);

  const selectedEndpoint = endpoints.find((endpoint) => endpoint.id === selectedEndpointId);
  const canRun =
    mode === "api" &&
    Boolean(selectedEndpoint) &&
    Boolean(projectIdInput.trim()) &&
    Boolean(query.trim()) &&
    !trace.isLoading;
  const missingEndpoint = endpoints.length === 0;
  const hasFailure = traceEventHasFailure(active);
  const metaStatus = trace.result?.status ?? (hasFailure ? "error" : "ready");

  const runTrace = async () => {
    if (!selectedEndpoint || !canRun) return;

    onRunningChange(false);
    const response = await trace.runTrace({
      project_id: projectIdInput.trim(),
      endpoint_id: selectedEndpoint.id,
      query: query.trim(),
      timeout_seconds: timeoutSeconds,
    });

    if (response) {
      onTraceEvents(sortTraceEvents(response.events));
      onIndexChange(0);
    }
  };

  return (
    <footer className="replay query-replay">
      <div className="query-panel" aria-label="Query trace controls">
        <div className="query-copy">
          <strong>Query trace</strong>
          <span>Explicit runtime probe. Sends one query only after Run.</span>
        </div>

        <label className="query-field endpoint-select">
          <span>Endpoint</span>
          <select value={selectedEndpointId} onChange={(event) => setSelectedEndpointId(event.target.value)} disabled={missingEndpoint}>
            {missingEndpoint ? <option value="">endpoint_not_found</option> : null}
            {endpoints.map((endpoint) => (
              <option key={endpoint.id} value={endpoint.id}>
                {endpointLabel(endpoint)}
              </option>
            ))}
          </select>
        </label>

        {mode === "api" ? (
          <label className="query-field project-id-field">
            <span>Project ID</span>
            <input value={projectIdInput} onChange={(event) => setProjectIdInput(event.target.value)} placeholder="project:<uuid>" />
          </label>
        ) : null}

        <label className="query-field query-input">
          <span>Question</span>
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Ask once against the selected endpoint" />
        </label>

        <label className="query-field timeout-field">
          <span>Timeout</span>
          <input
            min={TIMEOUT_MIN_SECONDS}
            max={TIMEOUT_MAX_SECONDS}
            type="number"
            value={timeoutSeconds}
            onChange={(event) => setTimeoutSeconds(clampTimeoutSeconds(event.target.value))}
          />
        </label>

        <button className="btn primary" type="button" disabled={!canRun} onClick={() => void runTrace()}>
          <Send size={14} />
          {trace.isLoading ? "Running" : "Run"}
        </button>
      </div>

      <div className="query-status">
        {mode !== "api" ? <span>Switch to API mode to run a live query trace.</span> : null}
        {missingEndpoint ? <span className="is-warning">endpoint_not_found: no endpoint is available in this map.</span> : null}
        {mode === "api" && !projectIdInput.trim() ? <span className="is-warning">Project ID is required for `/api/trace`.</span> : null}
        {trace.error ? <span className="is-error">{trace.error}</span> : null}
        {trace.result ? (
          <span className={trace.result.status === "completed" ? "is-ok" : "is-warning"}>
            trace {trace.result.status}; query_sent: {String(trace.result.query_sent)}
            {trace.result.error_reason ? `; ${trace.result.error_reason}` : ""}
          </span>
        ) : null}
        {trace.result?.warnings.map((warning) => (
          <span className="is-warning" key={warning}>
            {warning}
          </span>
        ))}
      </div>

      <div className="replay-head">
        <div className="r-title">
          <strong>Replay</strong>
          <span className="mono">{selectedEndpoint ? compactId(selectedEndpoint.id) : "no endpoint"}</span>
        </div>
        <div className="r-ctrls">
          <button className="icon-btn" type="button" aria-label="Reset replay" title="Reset replay" onClick={() => onIndexChange(0)}>
            <RotateCcw size={14} />
          </button>
          <button
            className="icon-btn"
            type="button"
            aria-label="Previous step"
            title="Previous step"
            onClick={() => onIndexChange(Math.max(activeIndex - 1, 0))}
          >
            <SkipBack size={14} />
          </button>
          <button
            className="icon-btn primary"
            type="button"
            aria-pressed={isRunning}
            aria-label={isRunning ? "Pause replay" : "Play replay"}
            title={isRunning ? "Pause" : "Play"}
            disabled={sortedEvents.length === 0}
            onClick={() => onRunningChange(!isRunning)}
          >
            {isRunning ? <Pause size={14} /> : <Play size={14} />}
          </button>
          <button
            className="icon-btn"
            type="button"
            aria-label="Next step"
            title="Next step"
            onClick={() => onIndexChange(Math.min(activeIndex + 1, maxIndex))}
          >
            <SkipForward size={14} />
          </button>
        </div>
        <div className="r-meta">
          {active ? (
            <span className="chip">
              step {activeIndex + 1}/{sortedEvents.length}
            </span>
          ) : null}
          {active?.latency_ms != null ? <span className="chip">{active.latency_ms} ms</span> : null}
          <span className={hasFailure ? "has-error" : "ok"}>{hasFailure ? traceErrorLabel(active?.error) : statusLabel(metaStatus)}</span>
        </div>
      </div>

      {sortedEvents.length === 0 ? (
        <div className="replay-empty">No replay events in this payload.</div>
      ) : (
        <div className="timeline">
          {sortedEvents.map((event, index) => {
            const failed = traceEventHasFailure(event);
            return (
              <button
                key={event.id ?? `${event.sequence_index ?? index}-${index}`}
                className={["tl-step", index === activeIndex ? "is-active" : "", failed ? "has-error" : ""].filter(Boolean).join(" ")}
                type="button"
                onClick={() => onIndexChange(index)}
              >
                <span className="tl-idx">{index + 1}</span>
                <span className="tl-body">
                  <span className="tl-slot">
                    {failed ? <AlertTriangle size={12} /> : null}
                    {titleCase(event.slot ?? event.step_type ?? event.event_type ?? "step")}
                  </span>
                  <span className="tl-sub">{compactId(event.component_id ?? event.edge_id ?? event.endpoint_id ?? event.step_type ?? "")}</span>
                </span>
              </button>
            );
          })}
        </div>
      )}
    </footer>
  );
}
