import { AlertTriangle, Send } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useQueryTrace } from "../hooks/useQueryTrace";
import type { DataSourceMode, GraphViewModel, TraceEvent } from "../types";
import { compactId } from "../utils/format";
import { sortTraceEvents } from "../utils/trace";
import { ReplayTimeline } from "./ReplayTimeline";

const MIN_TIMEOUT_SECONDS = 1;
const MAX_TIMEOUT_SECONDS = 120;
const DEFAULT_TIMEOUT_SECONDS = 30;

type ReplayProps = {
  events: TraceEvent[];
  activeIndex: number;
  isPlaying: boolean;
  fallbackMessage?: string | null;
  onIndexChange: (index: number) => void;
  onPlay: () => void;
  onPause: () => void;
  onPrevious: () => void;
  onNext: () => void;
  onReset: () => void;
};

type Props = ReplayProps & {
  mode: DataSourceMode;
  apiBaseUrl: string;
  projectId: string | null;
  buildId: string | null;
  endpoints: GraphViewModel["endpoints"];
  onTraceEvents: (events: TraceEvent[]) => void;
};

function endpointLabel(endpoint: GraphViewModel["endpoints"][number]): string {
  const method = endpoint.method ? `${endpoint.method.toLocaleUpperCase()} · ` : "";
  return `${method}${endpoint.endpoint_id}`;
}

function normalizedTimeout(raw: string): number {
  const parsed = Number(raw);
  if (!Number.isFinite(parsed)) return DEFAULT_TIMEOUT_SECONDS;
  return Math.min(MAX_TIMEOUT_SECONDS, Math.max(MIN_TIMEOUT_SECONDS, Math.round(parsed)));
}

export function QueryTracePanel({
  mode,
  apiBaseUrl,
  projectId,
  buildId,
  endpoints,
  events,
  activeIndex,
  isPlaying,
  fallbackMessage,
  onIndexChange,
  onPlay,
  onPause,
  onPrevious,
  onNext,
  onReset,
  onTraceEvents,
}: Props) {
  const [endpointId, setEndpointId] = useState("");
  const [query, setQuery] = useState("");
  const [timeoutSeconds, setTimeoutSeconds] = useState(DEFAULT_TIMEOUT_SECONDS);
  const trace = useQueryTrace(apiBaseUrl, projectId, buildId);

  useEffect(() => {
    if (!endpoints.some((endpoint) => endpoint.endpoint_id === endpointId)) {
      setEndpointId(endpoints[0]?.endpoint_id ?? "");
    }
  }, [endpointId, endpoints]);

  const scopeReady = mode === "api" && Boolean(projectId) && Boolean(buildId);
  const canRun = scopeReady && Boolean(endpointId) && Boolean(query.trim()) && !trace.isLoading;
  const canRetry = trace.state === "error" || trace.state === "timeout" || ["partial", "error"].includes(trace.result?.status ?? "");
  const statusClass = trace.result?.status === "completed" ? "is-ok" : trace.state === "error" || trace.state === "timeout" ? "is-error" : "is-warning";
  const selectedEndpoint = useMemo(
    () => endpoints.find((endpoint) => endpoint.endpoint_id === endpointId),
    [endpointId, endpoints],
  );

  const runTrace = async () => {
    if (!canRun) return;
    onPause();
    const response = await trace.runTrace({
      endpointId,
      query: query.trim(),
      timeoutSeconds,
    });
    if (response?.source_build_id === buildId) onTraceEvents(sortTraceEvents(response.events));
  };

  return (
    <section className="query-trace-panel" aria-labelledby="query-trace-title">
      <div className="query-trace-form">
        <div className="query-trace-copy">
          <strong id="query-trace-title">Query Trace</strong>
          <span>Opt-in runtime probe. No request is sent until Run.</span>
        </div>

        <label className="query-trace-field query-trace-endpoint">
          <span>Endpoint</span>
          <select value={endpointId} disabled={endpoints.length === 0 || trace.isLoading} onChange={(event) => setEndpointId(event.target.value)}>
            {endpoints.length === 0 ? <option value="">No endpoint in this build</option> : null}
            {endpoints.map((endpoint) => <option value={endpoint.endpoint_id} key={endpoint.endpoint_id}>{endpointLabel(endpoint)}</option>)}
          </select>
        </label>

        <label className="query-trace-field query-trace-query">
          <span>Query</span>
          <input
            value={query}
            disabled={trace.isLoading}
            placeholder="Send one masked, bounded runtime query"
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>

        <label className="query-trace-field query-trace-timeout">
          <span>Timeout (seconds)</span>
          <input
            type="number"
            min={MIN_TIMEOUT_SECONDS}
            max={MAX_TIMEOUT_SECONDS}
            value={timeoutSeconds}
            disabled={trace.isLoading}
            onChange={(event) => setTimeoutSeconds(normalizedTimeout(event.target.value))}
          />
        </label>

        <button className="btn primary" type="button" disabled={!canRun} onClick={() => void runTrace()}>
          <Send size={14} aria-hidden="true" />
          {trace.isLoading ? "Running…" : canRetry ? "Retry" : "Run"}
        </button>
      </div>

      <div className="query-trace-scope" aria-label="Trace build scope">
        <span>project <code>{projectId ? compactId(projectId) : "not selected"}</code></span>
        <span>build <code>{buildId ? compactId(buildId) : "not selected"}</code></span>
        {selectedEndpoint?.endpoint_type ? <span>{selectedEndpoint.endpoint_type} endpoint</span> : null}
      </div>

      <div className="query-trace-status" aria-live="polite">
        {mode !== "api" ? <span className="is-warning">Switch to API mode to run a trace.</span> : null}
        {mode === "api" && !projectId ? <span className="is-warning">Select a project before running a trace.</span> : null}
        {mode === "api" && projectId && !buildId ? <span className="is-warning">Load a build before running a trace.</span> : null}
        {trace.isLoading ? <span>Runtime request in progress. Existing replay events remain available.</span> : null}
        {trace.state === "timeout" ? <span className="is-error"><AlertTriangle size={12} />Client request timed out. Retry explicitly if appropriate.</span> : null}
        {trace.state === "error" ? <span className="is-error"><AlertTriangle size={12} />{trace.error}</span> : null}
        {trace.result ? (
          <span className={statusClass}>
            {trace.result.status}; query_sent: {String(trace.result.query_sent)}
            {trace.result.error_reason ? `; ${trace.result.error_reason}` : ""}
          </span>
        ) : null}
        {trace.result && trace.result.source_build_id !== buildId ? (
          <span className="is-error">Backend did not bind this result to the selected build. Existing replay is preserved.</span>
        ) : null}
        {trace.result?.warnings.map((warning) => <span className="is-warning" key={warning}>{warning}</span>)}
      </div>

      <ReplayTimeline
        events={events}
        activeIndex={activeIndex}
        isPlaying={isPlaying}
        fallbackMessage={fallbackMessage}
        onIndexChange={onIndexChange}
        onPlay={onPlay}
        onPause={onPause}
        onPrevious={onPrevious}
        onNext={onNext}
        onReset={onReset}
      />
    </section>
  );
}
