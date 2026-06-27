import { useCallback, useEffect, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Crosshair, Folder, Layers3, Maximize, Menu, MessageCircle, Moon, MoreHorizontal, Share2, Sun } from "lucide-react";
import { ChatPanel } from "./components/ChatPanel";
import { BoundaryDecisionModal, decisionsForBoundary } from "./components/BoundaryDecisionModal";
import { DataSourceControl } from "./components/DataSourceControl";
import { DetailPanel } from "./components/DetailPanel";
import { DraggableInspector } from "./components/DraggableInspector";
import { ProgressStrip } from "./components/ProgressStrip";
import { ReplayTimeline } from "./components/ReplayTimeline";
import { Sidebar } from "./components/Sidebar";
import { StateOverlay, type ViewerState } from "./components/StateOverlay";
import { SystemGraph } from "./components/SystemGraph";
import { ScanTemplatePage } from "./pages/ScanTemplatePage";
import { ProposalModal, type ProposalTarget } from "./components/proposal/ProposalModal";
import { WordingProvider } from "./wording";
import { getTraceEvents, viewerPayload as sampleViewerPayload } from "./data/sampleMap";
import { useScanProgress } from "./hooks/useScanProgress";
import { useDetailScan } from "./hooks/useDetailScan";
import { useTheme } from "./hooks/useTheme";
import { useViewerPayload } from "./hooks/useViewerPayload";
import { importProject, startProjectScan } from "./services/projectScanApi";
import { loadApiViewerPayload } from "./services/viewerApi";
import type { DetailScanTarget } from "./services/detailScanApi";
import { useViewerStore } from "./store/viewerStore";
import type {
  DetailScanDepth,
  GraphViewModel,
  ProjectImportResponse,
  ScanBoundaryAction,
  ScanBoundaryProposal,
} from "./types";
import { createProgressTargets, resolveProgressTargetId } from "./utils/graph";

const EMPTY_GRAPH: GraphViewModel = {
  nodes: [],
  edges: [],
  details: { evidence_by_id: {}, risk_hints_by_id: {} },
  filters: { available: [] },
};

const MAP_KEY: Array<[string, string]> = [
  ["var(--accent)", "Detected"],
  ["var(--accent-strong)", "Confirmed"],
  ["var(--risk)", "Risk"],
  ["var(--unmapped)", "Review"],
  ["var(--text-faint)", "Missing"],
];

export default function App() {
  const queryClient = useQueryClient();
  const { theme, toggleTheme } = useTheme();

  const dataSourceMode = useViewerStore((state) => state.dataSourceMode);
  const apiBaseUrl = useViewerStore((state) => state.apiBaseUrl);
  const setDataSourceMode = useViewerStore((state) => state.setDataSourceMode);
  const setApiBaseUrl = useViewerStore((state) => state.setApiBaseUrl);
  const payloadQuery = useViewerPayload(dataSourceMode, apiBaseUrl);
  const detailScan = useDetailScan(apiBaseUrl);
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
  const [graphInteracting, setGraphInteracting] = useState(false);
  const [projectPath, setProjectPath] = useState("");
  const [projectSession, setProjectSession] = useState<ProjectImportResponse | null>(null);
  const [pendingBoundary, setPendingBoundary] = useState<ScanBoundaryProposal[]>([]);
  const [boundaryDecisions, setBoundaryDecisions] = useState<Record<string, ScanBoundaryAction>>({});
  const [scanBusy, setScanBusy] = useState(false);
  const [scanFlowError, setScanFlowError] = useState<string | undefined>();
  // Scan Template route (full-bleed overlay) + Mapping Proposal modal (z 60, can
  // sit over the route or the graph). The selection API does not exist yet, so
  // the page runs on the scanTemplateApi mock seam.
  const [view, setView] = useState<"viewer" | "scan-template">("viewer");
  const [proposalTarget, setProposalTarget] = useState<ProposalTarget | null>(null);

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

  const completeScanFlow = useCallback(async () => {
    const freshPayload = await loadApiViewerPayload(apiBaseUrl);
    queryClient.setQueryData(["viewer-load-result", "api", apiBaseUrl], freshPayload);
    setDataSourceMode("api");
    setProgressRunning(false);
    setLiveProgressEvent({
      event: "scan_progress",
      status: "completed",
      stage: "map",
      message: "Scan completed. Loading map.",
      percent: 100,
    });
  }, [apiBaseUrl, queryClient, setDataSourceMode, setLiveProgressEvent, setProgressRunning]);

  const runScan = useCallback(
    async (session: ProjectImportResponse, decisions: ReturnType<typeof decisionsForBoundary> = []) => {
      setScanBusy(true);
      setScanFlowError(undefined);
      setLiveProgressEvent({
        event: "scan_progress",
        status: "running",
        stage: "scan",
        message: "Scanning project.",
        percent: 30,
      });

      try {
        const response = await startProjectScan(apiBaseUrl, {
          projectId: session.project_id,
          boundaryDecisions: decisions,
        });

        if (response.status === "requires_boundary_decision") {
          setPendingBoundary(response.boundary_proposals);
          setBoundaryDecisions({});
          setLiveProgressEvent({
            event: "scan_progress",
            status: "running",
            stage: "boundary",
            message: "Waiting for scan boundary review.",
            percent: 10,
          });
          return;
        }

        if (response.status === "error") {
          setScanFlowError("Scan finished with an error. Check the backend report or logs for details.");
          setLiveProgressEvent({
            event: "scan_progress",
            status: "error",
            stage: "scan",
            message: "Scan finished with an error.",
            percent: 100,
          });
          return;
        }

        setPendingBoundary([]);
        setBoundaryDecisions({});
        await completeScanFlow();
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        setScanFlowError(message);
        setLiveProgressEvent({
          event: "scan_progress",
          status: "error",
          stage: "scan",
          message,
          percent: 100,
        });
      } finally {
        setScanBusy(false);
      }
    },
    [apiBaseUrl, completeScanFlow, setLiveProgressEvent],
  );

  const handleStartScan = useCallback(async () => {
    const path = projectPath.trim();
    if (!path) return;

    setScanBusy(true);
    setScanFlowError(undefined);
    setDataSourceMode("api");
    setProgressRunning(true);
    setLiveProgressEvent({
      event: "scan_progress",
      status: "running",
      stage: "project",
      message: "Importing project.",
      percent: 5,
    });

    try {
      const session = await importProject(apiBaseUrl, path);
      setProjectSession(session);
      await runScan(session);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setScanFlowError(message);
      setLiveProgressEvent({
        event: "scan_progress",
        status: "error",
        stage: "project",
        message,
        percent: 100,
      });
      setScanBusy(false);
    }
  }, [apiBaseUrl, projectPath, runScan, setDataSourceMode, setLiveProgressEvent, setProgressRunning]);

  const handleBoundarySubmit = useCallback(async () => {
    if (!projectSession) return;
    await runScan(projectSession, decisionsForBoundary(pendingBoundary, boundaryDecisions));
  }, [boundaryDecisions, pendingBoundary, projectSession, runScan]);

  const handleRunDetailScan = (target: DetailScanTarget, scanDepth: DetailScanDepth) => {
    if (!projectSession) return;
    detailScan.run({
      projectId: projectSession.project_id,
      target,
      scanDepth,
    });
  };

  const projectName = graph.summary?.project_name ? String(graph.summary.project_name) : "Local AI Health Doctor";

  return (
    <div className="app">
      {menuOpen ? <div className="sidebar-scrim" role="presentation" onClick={() => setMenuOpen(false)} /> : null}

      <Sidebar
        scanSummary={scanSummary}
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
          <div className="toolbar-menu project-menu">
            <button className="tb-title-project" type="button" aria-label={`Project ${projectName}`}>
              <Folder size={13} />
              <span>{projectName}</span>
            </button>
            <div className="toolbar-popover">
              <div className="popover-title">Project</div>
              <div className="popover-main">{projectName}</div>
              <div className="meta-list">
                <span>
                  <Layers3 size={13} />
                  <b>{graph.nodes.length}</b> Nodes
                </span>
                <span>
                  <Share2 size={13} />
                  <b>{graph.edges.length}</b> Edges
                </span>
                <span>
                  <span className="pulse" />
                  status <b>{dataAvailable ? (scanSummary?.status ?? "unknown") : "unknown"}</b>
                </span>
                <span>projection</span>
              </div>
            </div>
          </div>
          <div className="tb-metrics is-hidden">
            <span className="metric">
              <Layers3 size={14} />
              <b>{graph.nodes.length}</b>
              Nodes
            </span>
            <span className="metric">
              <Share2 size={14} />
              <b>{graph.edges.length}</b>
              Edges
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
            projectPath={projectPath}
            isLoading={payloadQuery.isFetching}
            isScanning={scanBusy}
            error={sourceError}
            scanError={scanFlowError}
            onModeChange={setDataSourceMode}
            onApiBaseUrlChange={setApiBaseUrl}
            onProjectPathChange={setProjectPath}
            onRefresh={() => void payloadQuery.refetch()}
            onStartScan={() => void handleStartScan()}
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
          <details className="toolbar-menu more-menu">
            <summary className="icon-btn" aria-label="More tools" title="More tools">
              <MoreHorizontal size={16} />
            </summary>
            <div className="toolbar-popover align-right">
              <button className="menu-action" type="button" onClick={handleReset}>
                <Maximize size={15} />
                Reset view
              </button>
              <button className="menu-action" type="button" onClick={toggleTheme}>
                {theme === "dark" ? <Sun size={15} /> : <Moon size={15} />}
                {theme === "dark" ? "Light theme" : "Dark theme"}
              </button>
              <button className="menu-action" type="button" onClick={() => setChatOpen(true)}>
                <MessageCircle size={15} />
                Local chat
              </button>
            </div>
          </details>
        </header>

        <div className={graphInteracting ? "graph-frame is-interacting" : "graph-frame"}>
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
            onInteractingChange={setGraphInteracting}
          />

          <div className="map-key-float" aria-label="Map color key">
            {MAP_KEY.map(([color, label]) => (
              <span className="legend-chip" key={label}>
                <span className="swatch" style={{ background: color }} />
                {label}
              </span>
            ))}
          </div>

          {selected && !showOverlay && payload ? (
            <DraggableInspector>
              <DetailPanel
                graph={graph}
                payload={payload}
                selected={selected}
                traceEvents={traceEvents}
                dataSourceMode={dataSourceMode}
                projectId={dataSourceMode === "api" ? projectSession?.project_id : undefined}
                detailMode={detailMode}
                detailRequest={{
                  projectId: detailScan.variables?.projectId,
                  target: detailScan.variables?.target,
                  scanDepth: detailScan.variables?.scanDepth,
                  result: detailScan.data?.response.detail_scan,
                  isPending: detailScan.isPending,
                  error: detailScan.error,
                  refreshWarning: detailScan.data?.refreshError,
                }}
                onRunDetailScan={handleRunDetailScan}
                onOpenMappingProposal={(node) =>
                  setProposalTarget({
                    unmapped_id: node.source_id ?? node.id.replace(/^node:/, ""),
                    node_path: node.subtitle ?? node.label,
                    node_kind: node.type,
                    realApi: true,
                  })
                }
                onDetailModeChange={setDetailMode}
                onClose={() => setSelected(null)}
              />
            </DraggableInspector>
          ) : null}
        </div>

        <ReplayTimeline
          events={dataAvailable ? traceEvents : []}
          activeIndex={activeTraceIndex}
          isRunning={isReplayRunning}
          onIndexChange={setActiveTraceIndex}
          onSelectEvent={(event) => {
            if (event.id) setSelected({ kind: "trace", id: event.id });
          }}
          onRunningChange={setReplayRunning}
        />
      </section>

      <ChatPanel open={chatOpen} onClose={() => setChatOpen(false)} />

      {pendingBoundary.length > 0 ? (
        <BoundaryDecisionModal
          proposals={pendingBoundary}
          decisions={boundaryDecisions}
          isSubmitting={scanBusy}
          error={scanFlowError}
          onDecisionChange={(proposalId, decision) =>
            setBoundaryDecisions((current) => ({ ...current, [proposalId]: decision }))
          }
          onSubmit={() => void handleBoundarySubmit()}
          onCancel={() => {
            setPendingBoundary([]);
            setBoundaryDecisions({});
            setScanBusy(false);
          }}
        />
      ) : null}

      <WordingProvider>
        {view === "scan-template" ? (
          <ScanTemplatePage
            onClose={() => setView("viewer")}
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
          <ProposalModal
            node={proposalTarget}
            scenario="ok"
            apiBaseUrl={proposalTarget.realApi ? apiBaseUrl : undefined}
            projectId={proposalTarget.realApi ? projectSession?.project_id : undefined}
            onClose={() => setProposalTarget(null)}
          />
        ) : null}
      </WordingProvider>
    </div>
  );
}
