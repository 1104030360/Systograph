import { useCallback, useEffect, useMemo } from "react";
import { Crosshair, Database, GitBranch, Layers3, SearchCode } from "lucide-react";
import { ChatPanel } from "./components/ChatPanel";
import { DataSourceControl } from "./components/DataSourceControl";
import { DetailPanel } from "./components/DetailPanel";
import { ProgressStrip } from "./components/ProgressStrip";
import { ReplayTimeline } from "./components/ReplayTimeline";
import { Sidebar } from "./components/Sidebar";
import { SystemGraph } from "./components/SystemGraph";
import { getTraceEvents, graphViewModel, viewerPayload as sampleViewerPayload } from "./data/sampleMap";
import { useScanProgress } from "./hooks/useScanProgress";
import { useViewerPayload } from "./hooks/useViewerPayload";
import { useViewerStore } from "./store/viewerStore";
import { createProgressTargets, resolveProgressTargetId } from "./utils/graph";

export default function App() {
  const dataSourceMode = useViewerStore((state) => state.dataSourceMode);
  const apiBaseUrl = useViewerStore((state) => state.apiBaseUrl);
  const setDataSourceMode = useViewerStore((state) => state.setDataSourceMode);
  const setApiBaseUrl = useViewerStore((state) => state.setApiBaseUrl);
  const payloadQuery = useViewerPayload(dataSourceMode, apiBaseUrl);
  const payload = payloadQuery.data ?? sampleViewerPayload;
  const graph = payload.viewer_load_result.graph_view_model ?? graphViewModel;
  const traceEvents = useMemo(() => getTraceEvents(payload), [payload]);
  const progressTargets = useMemo(() => createProgressTargets(graph), [graph]);
  const selected = useViewerStore((state) => state.selected);
  const activeFilterIds = useViewerStore((state) => state.activeFilterIds);
  const activeTraceIndex = useViewerStore((state) => state.activeTraceIndex);
  const isReplayRunning = useViewerStore((state) => state.isReplayRunning);
  const isProgressRunning = useViewerStore((state) => state.isProgressRunning);
  const followFocus = useViewerStore((state) => state.followFocus);
  const progressIndex = useViewerStore((state) => state.progressIndex);
  const liveProgressEvent = useViewerStore((state) => state.liveProgressEvent);
  const detailMode = useViewerStore((state) => state.detailMode);
  const setSelected = useViewerStore((state) => state.setSelected);
  const toggleFilter = useViewerStore((state) => state.toggleFilter);
  const clearFilters = useViewerStore((state) => state.clearFilters);
  const setActiveTraceIndex = useViewerStore((state) => state.setActiveTraceIndex);
  const setReplayRunning = useViewerStore((state) => state.setReplayRunning);
  const setProgressRunning = useViewerStore((state) => state.setProgressRunning);
  const setProgressIndex = useViewerStore((state) => state.setProgressIndex);
  const setFollowFocus = useViewerStore((state) => state.setFollowFocus);
  const setLiveProgressEvent = useViewerStore((state) => state.setLiveProgressEvent);
  const setDetailMode = useViewerStore((state) => state.setDetailMode);
  const resetFocus = useViewerStore((state) => state.resetFocus);
  const activeTraceEvent = traceEvents[activeTraceIndex];
  const progressTarget = progressTargets[progressIndex];
  const liveProgressTargetId = resolveProgressTargetId(liveProgressEvent, graph);
  const progressTargetId = liveProgressTargetId ?? progressTarget?.id;
  const sourceError = payloadQuery.error instanceof Error ? payloadQuery.error.message : undefined;
  const scanError = liveProgressEvent?.event === "sse_error" ? liveProgressEvent.message : undefined;

  const handleScanEvent = useCallback(
    (event: typeof liveProgressEvent) => {
      if (event) setLiveProgressEvent(event);
    },
    [setLiveProgressEvent],
  );

  const handleScanError = useCallback(
    (message: string) => {
      setLiveProgressEvent({
        event: "sse_error",
        status: "warning",
        message,
      });
    },
    [setLiveProgressEvent],
  );

  useScanProgress({
    mode: dataSourceMode,
    apiBaseUrl,
    enabled: isProgressRunning,
    onEvent: handleScanEvent,
    onError: handleScanError,
  });

  useEffect(() => {
    if (!isReplayRunning || traceEvents.length === 0) return;

    const timer = window.setInterval(() => {
      setActiveTraceIndex((activeTraceIndex + 1) % traceEvents.length);
    }, 1100);

    return () => window.clearInterval(timer);
  }, [activeTraceIndex, isReplayRunning, setActiveTraceIndex, traceEvents.length]);

  useEffect(() => {
    if (!isProgressRunning || progressTargets.length === 0 || (dataSourceMode === "api" && liveProgressEvent?.event !== "sse_error")) return;

    const timer = window.setInterval(() => {
      setProgressIndex((progressIndex + 1) % progressTargets.length);
    }, 850);

    return () => window.clearInterval(timer);
  }, [dataSourceMode, isProgressRunning, liveProgressEvent?.event, progressIndex, progressTargets.length, setProgressIndex]);

  useEffect(() => {
    if (activeTraceIndex >= traceEvents.length) {
      setActiveTraceIndex(0);
    }
  }, [activeTraceIndex, setActiveTraceIndex, traceEvents.length]);

  return (
    <main className="app-shell">
      <Sidebar graph={graph} activeFilterIds={activeFilterIds} onToggleFilter={toggleFilter} onClearFilters={clearFilters} />

      <section className="workspace">
        <header className="toolbar">
          <div className="toolbar-title">
            <GitBranch size={18} />
            <div>
              <span className="section-label">Epic 1 Viewer</span>
              <strong>{graph.summary?.project_name ? String(graph.summary.project_name) : "Local AI Health Doctor"}</strong>
            </div>
          </div>
          <div className="toolbar-metrics">
            <span>
              <Layers3 size={15} />
              {graph.nodes.length} nodes
            </span>
            <span>
              <SearchCode size={15} />
              {graph.edges.length} edges
            </span>
            <span>
              <Database size={15} />
              {String(payload.viewer_load_result.ai_system_map.scan_depth ?? "system")}
            </span>
          </div>
          <DataSourceControl
            mode={dataSourceMode}
            apiBaseUrl={apiBaseUrl}
            isLoading={payloadQuery.isFetching}
            error={sourceError ?? scanError}
            onModeChange={setDataSourceMode}
            onApiBaseUrlChange={setApiBaseUrl}
            onRefresh={() => void payloadQuery.refetch()}
          />
          <button
            className={followFocus ? "toolbar-button follow-button is-active" : "toolbar-button follow-button"}
            type="button"
            onClick={() => setFollowFocus(!followFocus)}
            title={followFocus ? "Disable follow focus" : "Enable follow focus"}
          >
            <Crosshair size={15} />
            Follow
          </button>
          <button className="toolbar-button" type="button" onClick={resetFocus}>
            Reset
          </button>
        </header>

        <div className="graph-frame">
          <ProgressStrip
            targets={progressTargets}
            activeIndex={progressIndex}
            isRunning={isProgressRunning}
            mode={dataSourceMode}
            liveEvent={liveProgressEvent}
            onRunningChange={setProgressRunning}
          />
          <SystemGraph
            graph={graph}
            activeFilterIds={activeFilterIds}
            selected={selected}
            traceEvent={activeTraceEvent}
            progressTargetId={progressTargetId}
            followFocus={followFocus}
            onSelect={setSelected}
          />
        </div>

        <ReplayTimeline
          events={traceEvents}
          activeIndex={activeTraceIndex}
          isRunning={isReplayRunning}
          onIndexChange={setActiveTraceIndex}
          onRunningChange={setReplayRunning}
        />
      </section>

      <ChatPanel />
      <DetailPanel
        graph={graph}
        payload={payload}
        selected={selected}
        detailMode={detailMode}
        onDetailModeChange={setDetailMode}
        onClose={() => setSelected(null)}
      />
    </main>
  );
}
