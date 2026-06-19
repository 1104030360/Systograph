import { useCallback, useEffect, useMemo, useState } from "react";
import { Crosshair, Folder, Layers3, Maximize, Menu, MessageCircle, Moon, Share2, Sun } from "lucide-react";
import { ChatPanel } from "./components/ChatPanel";
import { DataSourceControl } from "./components/DataSourceControl";
import { DetailPanel } from "./components/DetailPanel";
import { ProgressStrip } from "./components/ProgressStrip";
import { ReplayTimeline } from "./components/ReplayTimeline";
import { Sidebar } from "./components/Sidebar";
import { StateOverlay, type ViewerState } from "./components/StateOverlay";
import { SystemGraph } from "./components/SystemGraph";
import { ScanTemplatePage } from "./pages/ScanTemplatePage";
import { ProposalModal, type ProposalTarget } from "./components/proposal/ProposalModal";
import { WordingProvider, type WordingMode } from "./wording";
import { getTraceEvents, viewerPayload as sampleViewerPayload } from "./data/sampleMap";
import { useScanProgress } from "./hooks/useScanProgress";
import { useTheme } from "./hooks/useTheme";
import { useViewerPayload } from "./hooks/useViewerPayload";
import { useViewerStore } from "./store/viewerStore";
import type { GraphViewModel } from "./types";
import { createProgressTargets, resolveProgressTargetId } from "./utils/graph";

const EMPTY_GRAPH: GraphViewModel = {
  nodes: [],
  edges: [],
  details: { evidence_by_id: {}, risk_hints_by_id: {} },
  filters: { available: [] },
};

export default function App() {
  const { theme, toggleTheme } = useTheme();

  const dataSourceMode = useViewerStore((state) => state.dataSourceMode);
  const apiBaseUrl = useViewerStore((state) => state.apiBaseUrl);
  const setDataSourceMode = useViewerStore((state) => state.setDataSourceMode);
  const setApiBaseUrl = useViewerStore((state) => state.setApiBaseUrl);
  const payloadQuery = useViewerPayload(dataSourceMode, apiBaseUrl);
  const data = payloadQuery.data;

  // ---- state matrix (explicit and honest) --------------------------------
  const appState: ViewerState =
    dataSourceMode === "sample"
      ? "loaded"
      : payloadQuery.isError
        ? "error"
        : !data
          ? "loading"
          : data.viewer_load_result.loaded === false
            ? "pending"
            : "loaded";
  const dataAvailable = appState === "loaded";
  const showOverlay = appState !== "loaded";

  const payload = dataSourceMode === "sample" ? sampleViewerPayload : data;
  const graph = dataAvailable && payload ? payload.viewer_load_result.graph_view_model : EMPTY_GRAPH;
  const aiSystemMap = dataAvailable ? payload?.viewer_load_result.ai_system_map : undefined;
  const scanSummary = aiSystemMap?.scan_summary;

  const traceEvents = useMemo(() => (dataAvailable && payload ? getTraceEvents(payload) : []), [dataAvailable, payload]);
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

  const [chatOpen, setChatOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [fitSignal, setFitSignal] = useState(0);
  // Scan Template route (full-bleed overlay) + Mapping Proposal modal (z 60, can
  // sit over the route or the graph). The selection API does not exist yet, so
  // the page runs on the scanTemplateApi mock seam.
  const [view, setView] = useState<"viewer" | "scan-template">("viewer");
  const [proposalTarget, setProposalTarget] = useState<ProposalTarget | null>(null);
  // TEMP: lets the team compare wording drafts in-product (see wording.ts).
  const [wordingMode, setWordingMode] = useState<WordingMode>("direct");

  const activeTraceEvent = traceEvents[activeTraceIndex];
  const progressTarget = progressTargets[progressIndex];
  const liveProgressTargetId = resolveProgressTargetId(liveProgressEvent, graph);
  const progressTargetId = liveProgressTargetId ?? (isProgressRunning ? progressTarget?.id : undefined);
  const sourceError = payloadQuery.error instanceof Error ? payloadQuery.error.message : undefined;
  const scanError = liveProgressEvent?.event === "sse_error";

  // ---- progress strip values (honest: never implies completion) ----------
  const progressPercent = liveProgressEvent?.percent ?? (isProgressRunning && progressTargets.length > 0
    ? Math.round(((progressIndex + 1) / progressTargets.length) * 100)
    : 0);
  const progressMessage =
    liveProgressEvent?.message ??
    (isProgressRunning ? `Inspecting ${progressTarget?.label ?? "component"}` : "Scan idle — showing committed map");
  const progressStage =
    liveProgressEvent?.stage ?? (isProgressRunning ? (dataSourceMode === "api" ? "sse stream" : "mock walk") : "idle");

  const handleScanEvent = useCallback(
    (event: typeof liveProgressEvent) => {
      if (event) setLiveProgressEvent(event);
    },
    [setLiveProgressEvent],
  );

  const handleScanError = useCallback(
    (message: string) => {
      setLiveProgressEvent({ event: "sse_error", status: "warning", message });
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

  // replay loop — interval created once per run (latest index read from store)
  useEffect(() => {
    if (!isReplayRunning || traceEvents.length === 0) return;
    const timer = window.setInterval(() => {
      const current = useViewerStore.getState().activeTraceIndex;
      setActiveTraceIndex((current + 1) % traceEvents.length);
    }, 1100);
    return () => window.clearInterval(timer);
  }, [isReplayRunning, setActiveTraceIndex, traceEvents.length]);

  // scan progress loop
  useEffect(() => {
    if (!isProgressRunning || progressTargets.length === 0 || (dataSourceMode === "api" && liveProgressEvent?.event !== "sse_error")) return;
    const timer = window.setInterval(() => {
      const current = useViewerStore.getState().progressIndex;
      setProgressIndex((current + 1) % progressTargets.length);
    }, 850);
    return () => window.clearInterval(timer);
  }, [dataSourceMode, isProgressRunning, liveProgressEvent?.event, progressTargets.length, setProgressIndex]);

  useEffect(() => {
    if (activeTraceIndex >= traceEvents.length) setActiveTraceIndex(0);
  }, [activeTraceIndex, setActiveTraceIndex, traceEvents.length]);

  const handleReset = useCallback(() => {
    resetFocus();
    setFitSignal((value) => value + 1);
  }, [resetFocus]);

  const projectName = graph.summary?.project_name ? String(graph.summary.project_name) : "Local AI Health Doctor";

  return (
    <div className="app">
      {menuOpen ? <div className="sidebar-scrim" role="presentation" onClick={() => setMenuOpen(false)} /> : null}

      <Sidebar
        scanSummary={scanSummary}
        systemType={aiSystemMap?.system_type}
        scanDepth={aiSystemMap?.scan_depth}
        dataAvailable={dataAvailable}
        filters={graph.filters.available}
        activeFilterIds={activeFilterIds}
        isOpen={menuOpen}
        onToggleFilter={toggleFilter}
        onClearFilters={clearFilters}
      />

      <section className="workspace">
        <header className="toolbar">
          <button className="icon-btn menu-btn" type="button" onClick={() => setMenuOpen(true)} title="Menu" aria-label="Open menu">
            <Menu size={16} />
          </button>
          <div className="tb-title">
            <div className="tb-title-project" aria-label={`Project ${projectName}`} title={`${projectName} - projection`}>
              <Folder size={13} />
              <span>{projectName}</span>
            </div>
          </div>
          <div className="tb-metrics">
            <span className="metric">
              <Layers3 size={14} />
              <b>{graph.nodes.length}</b>
              nodes
            </span>
            <span className="metric">
              <Share2 size={14} />
              <b>{graph.edges.length}</b>
              edges
            </span>
            <span className="metric is-status" title="Backend scan status">
              <span className="pulse" />
              status <b>{dataAvailable ? (scanSummary?.status ?? "unknown") : "—"}</b>
            </span>
          </div>
          <div className="tb-spacer" />

          <button
            className="btn"
            type="button"
            onClick={() => setView("scan-template")}
            title="Scan template & mapping profile"
          >
            <Layers3 size={14} />
            Scan Template
          </button>

          <DataSourceControl
            mode={dataSourceMode}
            apiBaseUrl={apiBaseUrl}
            isLoading={payloadQuery.isFetching}
            error={sourceError}
            onModeChange={setDataSourceMode}
            onApiBaseUrlChange={setApiBaseUrl}
            onRefresh={() => void payloadQuery.refetch()}
          />

          <button
            className={followFocus ? "btn is-active" : "btn"}
            type="button"
            aria-pressed={followFocus}
            onClick={() => setFollowFocus(!followFocus)}
            title="Follow active focus"
          >
            <Crosshair size={14} />
            Follow
          </button>
          <button className="icon-btn" type="button" onClick={handleReset} title="Reset view" aria-label="Reset view">
            <Maximize size={15} />
          </button>
          <button
            className="icon-btn"
            type="button"
            onClick={toggleTheme}
            title={theme === "dark" ? "Switch to light" : "Switch to dark"}
            aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
          >
            {theme === "dark" ? <Sun size={15} /> : <Moon size={15} />}
          </button>
          <button className="icon-btn" type="button" onClick={() => setChatOpen(true)} title="Local model chat" aria-label="Open chat">
            <MessageCircle size={15} />
          </button>
        </header>

        <div className="graph-frame">
          {!showOverlay ? (
            <ProgressStrip
              isRunning={isProgressRunning}
              percent={progressPercent}
              message={progressMessage}
              stage={progressStage}
              isError={scanError}
              onToggle={() => setProgressRunning(!isProgressRunning)}
            />
          ) : null}

          {showOverlay ? (
            <StateOverlay
              kind={appState}
              apiBaseUrl={apiBaseUrl}
              message={sourceError}
              onRetry={() => void payloadQuery.refetch()}
              onUseSample={() => setDataSourceMode("sample")}
            />
          ) : null}

          <SystemGraph
            graph={graph}
            activeFilterIds={activeFilterIds}
            selected={selected}
            traceEvent={activeTraceEvent}
            progressTargetId={progressTargetId}
            followFocus={followFocus}
            fitSignal={fitSignal}
            onSelect={setSelected}
          />

          {selected && !showOverlay && payload ? (
            <div className="inspector">
              <DetailPanel
                graph={graph}
                payload={payload}
                selected={selected}
                detailMode={detailMode}
                onDetailModeChange={setDetailMode}
                onClose={() => setSelected(null)}
              />
            </div>
          ) : null}
        </div>

        <ReplayTimeline
          events={dataAvailable ? traceEvents : []}
          activeIndex={activeTraceIndex}
          isRunning={isReplayRunning}
          onIndexChange={setActiveTraceIndex}
          onRunningChange={setReplayRunning}
        />
      </section>

      <ChatPanel open={chatOpen} onClose={() => setChatOpen(false)} />

      <WordingProvider mode={wordingMode}>
        {view === "scan-template" ? (
          <ScanTemplatePage
            onClose={() => setView("viewer")}
            wordingMode={wordingMode}
            onWordingModeChange={setWordingMode}
            onOpenProposal={(row) =>
              setProposalTarget({
                unmapped_id: row.unmapped_id,
                node_path: row.node_path,
                node_kind: row.node_kind,
              })
            }
          />
        ) : null}

        {proposalTarget ? (
          <ProposalModal node={proposalTarget} scenario="ok" onClose={() => setProposalTarget(null)} />
        ) : null}
      </WordingProvider>
    </div>
  );
}
