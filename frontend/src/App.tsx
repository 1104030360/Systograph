import { useCallback, useEffect, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ClipboardCheck, Folder, Info, Layers3, MessageCircle, Moon, MoreHorizontal, RotateCcw, Share2, Sun } from "lucide-react";
import { ArchitectureMap } from "./components/ArchitectureMap";
import { ArchitectureInfoDialog } from "./components/ArchitectureInfoDialog";
import { ArchitectureViewNav } from "./components/ArchitectureViewNav";
import { ChatPanel } from "./components/ChatPanel";
import { BoundaryDecisionModal } from "./components/BoundaryDecisionModal";
import { BuildHistoryMenu } from "./components/BuildHistoryMenu";
import { DataSourceControl } from "./components/DataSourceControl";
import { DetailPanel } from "./components/DetailPanel";
import { MapStatusBar } from "./components/MapStatusBar";
import { MappingProfileDialog } from "./components/MappingProfileDialog";
import { ProgressStrip } from "./components/ProgressStrip";
import { QueryTracePanel } from "./components/QueryTracePanel";
import { ReadinessPanel } from "./components/ReadinessPanel";
import { StateOverlay, type ViewerState } from "./components/StateOverlay";
import { ProposalModal, type ProposalTarget } from "./components/proposal/ProposalModal";
import { WordingProvider } from "./wording";
import { viewerPayload as sampleViewerPayload } from "./data/sampleMap";
import { BrandMark } from "./icons/BrandMark";
import { useMapBuilds } from "./hooks/useMapBuilds";
import { useDismissibleDetails } from "./hooks/useDismissibleDetails";
import { useProjectScanFlow } from "./hooks/useProjectScanFlow";
import { useScanProgress } from "./hooks/useScanProgress";
import { useTheme } from "./hooks/useTheme";
import { useTraceReplay } from "./hooks/useTraceReplay";
import { useViewerPayload } from "./hooks/useViewerPayload";
import { extractMappingCompleteness } from "./contracts/viewer";
import { loadLatestMapBuild } from "./services/mapBuildApi";
import { useViewerStore } from "./store/viewerStore";
import type { GraphViewModel, Selection } from "./types";
import { buildArchitectureViews, type ArchitectureViewId } from "./utils/architectureViews";
import { hasBackendPlaneProjection } from "./utils/planes";
import { resolveTraceHighlight } from "./utils/trace";

const EMPTY_GRAPH: GraphViewModel = {
  nodes: [],
  edges: [],
  relationships: [],
  endpoints: [],
  recommended_next_checks: [],
  details: {
    evidence_by_id: {},
    risk_hints_by_id: {},
    reference_assessments_by_id: {},
    profile_findings_by_id: {},
    capability_candidates_by_id: {},
  },
  filters: { available: [], lenses: [] },
};

export default function App() {
  const queryClient = useQueryClient();
  const { theme, toggleTheme } = useTheme();

  const dataSourceMode = useViewerStore((state) => state.dataSourceMode);
  const apiBaseUrl = useViewerStore((state) => state.apiBaseUrl);
  const activeProjectId = useViewerStore((state) => state.activeProjectId);
  const activeBuildId = useViewerStore((state) => state.activeBuildId);
  const setDataSourceMode = useViewerStore((state) => state.setDataSourceMode);
  const setApiBaseUrl = useViewerStore((state) => state.setApiBaseUrl);
  const setActiveProjectId = useViewerStore((state) => state.setActiveProjectId);
  const setActiveBuildId = useViewerStore((state) => state.setActiveBuildId);
  const payloadQuery = useViewerPayload(dataSourceMode, apiBaseUrl, activeProjectId, activeBuildId);
  const buildsQuery = useMapBuilds(dataSourceMode, apiBaseUrl, activeProjectId);
  const data = payloadQuery.data;

  // ---- state matrix (explicit and honest) --------------------------------
  const appState: ViewerState =
    dataSourceMode === "sample"
      ? "loaded"
      : activeProjectId == null && activeBuildId == null
        ? "empty"
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
  // PR #250 may publish a backend-owned reference/plane projection while its
  // canonical source artifact is still v1. Use explicit projection metadata
  // instead of treating source_schema_version as a presentation capability.
  const graphHasPlanes = payload
    ? hasBackendPlaneProjection(payload.viewer_load_result.graph_view_model)
    : false;
  const hasBuildLineage = payload?.viewer_load_result.build_id != null;
  const graph = dataAvailable && payload ? payload.viewer_load_result.graph_view_model : EMPTY_GRAPH;
  const aiSystemMap = dataAvailable ? payload?.viewer_load_result.ai_system_map : undefined;
  const scanSummary = aiSystemMap?.scan_summary;
  const architectureViews = useMemo(() => buildArchitectureViews(graph), [graph]);
  const mappingCompleteness = payload ? extractMappingCompleteness(payload) : undefined;
  const traceProjectId = dataSourceMode === "api" ? (payload?.viewer_load_result.project_id ?? null) : null;
  const traceBuildId = dataSourceMode === "api" ? (payload?.viewer_load_result.build_id ?? null) : null;
  const traceScopeKey = `${dataSourceMode}|${apiBaseUrl}|${traceProjectId ?? ""}|${traceBuildId ?? ""}`;
  const canReviewCurrentMapping =
    dataSourceMode === "api" &&
    activeBuildId == null &&
    traceProjectId != null &&
    traceBuildId != null;

  const selected = useViewerStore((state) => state.selected);
  const isProgressRunning = useViewerStore((state) => state.isProgressRunning);
  const liveProgressEvent = useViewerStore((state) => state.liveProgressEvent);
  const detailMode = useViewerStore((state) => state.detailMode);
  const setSelected = useViewerStore((state) => state.setSelected);
  const setProgressRunning = useViewerStore((state) => state.setProgressRunning);
  const setLiveProgressEvent = useViewerStore((state) => state.setLiveProgressEvent);
  const setDetailMode = useViewerStore((state) => state.setDetailMode);

  const [chatOpen, setChatOpen] = useState(false);
  const [activeArchitectureView, setActiveArchitectureView] = useState<ArchitectureViewId>("overview");
  const [nodeSearch, setNodeSearch] = useState("");
  const [projectPath, setProjectPath] = useState("");
  // Mapping Profile is a build-scoped read-only dialog. Mapping Proposal stays
  // a separate workflow and is not inferred from profile findings.
  const [view, setView] = useState<"viewer" | "scan-template">("viewer");
  const [proposalTarget, setProposalTarget] = useState<ProposalTarget | null>(null);
  const [readinessOpen, setReadinessOpen] = useState(false);
  const [architectureInfoOpen, setArchitectureInfoOpen] = useState(false);
  const [inspectorMode, setInspectorMode] = useState<"details" | "trace">("details");
  const moreToolsRef = useDismissibleDetails();
  const replay = useTraceReplay(traceScopeKey);
  const traceHighlight = useMemo(
    () => resolveTraceHighlight(replay.activeEvent, graph),
    [graph, replay.activeEvent],
  );

  useEffect(() => {
    setProposalTarget(null);
  }, [activeBuildId, activeProjectId, apiBaseUrl, dataSourceMode]);

  const sourceError = payloadQuery.error instanceof Error ? payloadQuery.error.message : undefined;
  const scanError = liveProgressEvent?.event === "sse_error";

  // ---- progress strip values (honest: never implies completion) ----------
  const progressPercent = liveProgressEvent?.percent ?? (isProgressRunning ? 5 : 0);
  const progressMessage =
    liveProgressEvent?.message ??
    (isProgressRunning ? "Scanning the imported project." : "Showing the committed map.");
  const progressStage =
    liveProgressEvent?.stage ?? (isProgressRunning ? "scan" : "idle");

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

  const completeScanFlow = useCallback(
    async (projectId: string, isCurrent: () => boolean) => {
      // Inventory Scan success is project/build scoped, so refresh the exact
      // project's latest published build.
      const latest = await loadLatestMapBuild(apiBaseUrl, projectId);
      // A cancel or a newly started scan during the fetch above owns the
      // session now; publishing this build would point the viewer at the
      // previous project.
      if (!isCurrent()) return;
      queryClient.setQueryData(["viewer-load-result", "api", apiBaseUrl, projectId, null], latest.payload);
      void queryClient.invalidateQueries({ queryKey: ["map-builds", apiBaseUrl, projectId] });
      setActiveProjectId(projectId);
      setActiveBuildId(null);
      setDataSourceMode("api");
    },
    [apiBaseUrl, queryClient, setActiveBuildId, setActiveProjectId, setDataSourceMode],
  );

  const handleProjectScanProgress = useCallback(
    (progress: {
      running: boolean;
      stage: string;
      message: string;
      percent: number;
      status: "running" | "waiting" | "completed" | "error";
    }) => {
      // The progress strip can describe import/preflight while SSE is enabled
      // only for the actual scan stage.
      setProgressRunning(progress.running && progress.stage === "scan");
      setLiveProgressEvent({
        event: "scan_progress",
        status: progress.status,
        stage: progress.stage,
        message: progress.message,
        percent: progress.percent,
      });
    },
    [setLiveProgressEvent, setProgressRunning],
  );

  const scanFlow = useProjectScanFlow({
    apiBaseUrl,
    onCompleted: async (projectId, _response, isCurrent) => {
      await completeScanFlow(projectId, isCurrent);
    },
    onProgress: handleProjectScanProgress,
  });

  const handleStartScan = useCallback(async () => {
    const path = projectPath.trim();
    if (!path) return;

    setDataSourceMode("api");
    await scanFlow.start(path);
  }, [projectPath, scanFlow, setDataSourceMode]);

  const handleResetView = useCallback(() => {
    setActiveArchitectureView("overview");
    setNodeSearch("");
    setSelected(null);
  }, [setSelected]);

  const handleMapSelect = useCallback(
    (selection: Selection) => {
      setSelected(selection);
      if (selection) setInspectorMode("details");
    },
    [setSelected],
  );

  const projectName = graph.summary?.project_name ? String(graph.summary.project_name) : "Systograph";

  return (
    <div className="dr-app">
      <a className="skip-link" href="#architecture-workspace">Skip to AI Agent System</a>

      <header className="dr-header">
        <a className="dr-brand" href="#top" aria-label="Systograph home">
          <span className="dr-brand-mark" aria-hidden="true"><BrandMark size={22} /></span>
          <span>
            <strong>Systograph</strong>
            <small>AI system release-readiness map</small>
          </span>
        </a>
        <nav className="dr-header-actions" aria-label="Viewer actions">
          <div className="toolbar-menu project-menu">
            <button className="tb-title-project" type="button" aria-label={`Project ${projectName}`}>
              <Folder size={13} />
              <span>{projectName}</span>
            </button>
            <div className="toolbar-popover">
              <div className="popover-title">Current project</div>
              <div className="popover-main">{projectName}</div>
              <div className="meta-list">
                <span><Layers3 size={13} /><b>{graph.nodes.length}</b> Nodes</span>
                <span><Share2 size={13} /><b>{graph.edges.length}</b> Edges</span>
                <span><span className="pulse" />status <b>{dataAvailable ? (scanSummary?.status ?? "unknown") : "unknown"}</b></span>
              </div>
              {hasBuildLineage && payload ? (
                <dl className="build-lineage" aria-label="Build lineage">
                  <div><dt>scan</dt><dd><code>{payload.viewer_load_result.scan_id}</code></dd></div>
                  <div><dt>build</dt><dd><code>{payload.viewer_load_result.build_id}</code></dd></div>
                  <div><dt>environment</dt><dd><code>{payload.viewer_load_result.environment_id}</code></dd></div>
                </dl>
              ) : null}
            </div>
          </div>

          <button className="btn" type="button" aria-haspopup="dialog" onClick={() => setView("scan-template")} title="Project mapping profile">
            <Layers3 size={14} />
            Mapping profile
          </button>
          <button
            className={readinessOpen ? "btn is-active" : "btn"}
            type="button"
            aria-haspopup="dialog"
            aria-pressed={readinessOpen}
            disabled={!dataAvailable}
            onClick={() => {
              setArchitectureInfoOpen(false);
              setReadinessOpen((open) => !open);
            }}
          >
            <ClipboardCheck size={14} />
            Readiness
          </button>
          {dataSourceMode === "api" ? (
            <BuildHistoryMenu builds={buildsQuery.data ?? []} activeBuildId={activeBuildId} onSelect={setActiveBuildId} />
          ) : null}
          <DataSourceControl
            mode={dataSourceMode}
            apiBaseUrl={apiBaseUrl}
            projectPath={projectPath}
            isLoading={payloadQuery.isFetching}
            isScanning={scanFlow.isBusy}
            error={sourceError}
            scanError={scanFlow.externalError}
            onModeChange={setDataSourceMode}
            onApiBaseUrlChange={setApiBaseUrl}
            onProjectPathChange={setProjectPath}
            onRefresh={() => void payloadQuery.refetch()}
            onStartScan={() => void handleStartScan()}
          />
          <button
            className="icon-btn"
            type="button"
            aria-label="Reset view"
            title="Reset view"
            onClick={handleResetView}
          >
            <RotateCcw size={16} />
          </button>
          <button
            className={architectureInfoOpen ? "icon-btn is-active" : "icon-btn"}
            type="button"
            aria-label="Architecture information"
            title="Architecture information"
            aria-haspopup="dialog"
            aria-pressed={architectureInfoOpen}
            onClick={() => {
              setReadinessOpen(false);
              setArchitectureInfoOpen((open) => !open);
            }}
          >
            <Info size={16} />
          </button>
          <details ref={moreToolsRef} className="toolbar-menu more-menu">
            <summary className="icon-btn" aria-label="More tools" title="More tools"><MoreHorizontal size={16} /></summary>
            <div className="toolbar-popover align-right">
              <button
                className="menu-action"
                type="button"
                onClick={() => {
                  toggleTheme();
                  if (moreToolsRef.current) moreToolsRef.current.open = false;
                }}
              >
                {theme === "dark" ? <Sun size={15} /> : <Moon size={15} />}
                {theme === "dark" ? "Light theme" : "Dark theme"}
              </button>
              <button
                className="menu-action"
                type="button"
                onClick={() => {
                  setChatOpen(true);
                  if (moreToolsRef.current) moreToolsRef.current.open = false;
                }}
              >
                <MessageCircle size={15} />
                Local chat
              </button>
            </div>
          </details>
        </nav>
      </header>

      <main className="dr-main" id="top">
        <div className="dr-viewer-stage">
          {isProgressRunning || liveProgressEvent ? (
            <div className="dr-progress-host">
              <ProgressStrip
                isRunning={isProgressRunning}
                percent={progressPercent}
                message={progressMessage}
                stage={progressStage}
                isError={scanError}
                onToggle={() => setProgressRunning(!isProgressRunning)}
              />
            </div>
          ) : null}

          <section className="dr-workspace" id="architecture-workspace">
            <ArchitectureViewNav
              views={architectureViews}
              activeViewId={activeArchitectureView}
              search={nodeSearch}
              onSelect={setActiveArchitectureView}
              onSearchChange={setNodeSearch}
            />
            <section className="dr-map-panel" aria-label="AI Agent System architecture map">
              <div className="dr-map-body">
                {showOverlay ? (
                  <StateOverlay
                    kind={appState}
                    apiBaseUrl={apiBaseUrl}
                    message={sourceError}
                    onRetry={() => void payloadQuery.refetch()}
                    onUseSample={() => setDataSourceMode("sample")}
                  />
                ) : (
                  <ArchitectureMap
                    graph={graph}
                    views={architectureViews}
                    activeViewId={activeArchitectureView}
                    search={nodeSearch}
                    selected={selected}
                    traceHighlight={traceHighlight}
                    onSelect={handleMapSelect}
                  />
                )}
              </div>
            </section>

            <aside className="dr-inspector-panel" aria-label="Details and query trace">
              <div className="dr-inspector-mode-tabs" role="tablist" aria-label="Right panel view">
                <button
                  id="details-mode-tab"
                  type="button"
                  role="tab"
                  aria-controls="details-mode-panel"
                  aria-selected={inspectorMode === "details"}
                  className={inspectorMode === "details" ? "is-active" : ""}
                  onClick={() => setInspectorMode("details")}
                >
                  Details
                </button>
                <button
                  id="trace-mode-tab"
                  type="button"
                  role="tab"
                  aria-controls="trace-mode-panel"
                  aria-selected={inspectorMode === "trace"}
                  className={inspectorMode === "trace" ? "is-active" : ""}
                  onClick={() => setInspectorMode("trace")}
                >
                  Query Trace
                </button>
              </div>

              {inspectorMode === "trace" ? (
                <div
                  id="trace-mode-panel"
                  className="dr-inspector-mode-body"
                  role="tabpanel"
                  aria-labelledby="trace-mode-tab"
                >
                  <QueryTracePanel
                    mode={dataSourceMode}
                    apiBaseUrl={apiBaseUrl}
                    projectId={traceProjectId}
                    buildId={traceBuildId}
                    endpoints={dataAvailable ? graph.endpoints : []}
                    events={replay.events}
                    activeIndex={replay.activeIndex}
                    isPlaying={replay.isPlaying}
                    fallbackMessage={traceHighlight.fallbackMessage}
                    onIndexChange={replay.select}
                    onPlay={replay.play}
                    onPause={replay.pause}
                    onPrevious={replay.previous}
                    onNext={replay.next}
                    onReset={replay.reset}
                    onTraceEvents={replay.replaceEvents}
                  />
                </div>
              ) : (
                <div
                  id="details-mode-panel"
                  className="dr-inspector-mode-body"
                  role="tabpanel"
                  aria-labelledby="details-mode-tab"
                >
                  {selected && !showOverlay && payload ? (
                    <DetailPanel
                      graph={graph}
                      payload={payload}
                      selected={selected}
                      detailMode={detailMode}
                      onDetailModeChange={setDetailMode}
                      onReviewMapping={canReviewCurrentMapping ? setProposalTarget : undefined}
                      onClose={() => setSelected(null)}
                    />
                  ) : (
                    <div className="dr-inspector-empty">
                      <BrandMark size={28} />
                      <strong>Inspect the normalized architecture</strong>
                      <p>Choose any reference capability, repository component or backend-declared flow.</p>
                      <dl>
                        <div><dt>Focused view</dt><dd>{architectureViews.find((candidate) => candidate.id === activeArchitectureView)?.label}</dd></div>
                        <div><dt>Nodes</dt><dd>{graph.nodes.length}</dd></div>
                        <div><dt>Risk hints</dt><dd>{scanSummary?.risk_hints ?? "—"}</dd></div>
                        <div><dt>Build warnings</dt><dd>{payload?.viewer_load_result.warnings.length ?? "—"}</dd></div>
                      </dl>
                    </div>
                  )}
                </div>
              )}
            </aside>
          </section>
        </div>

        <div className="dr-status-slot">
          <MapStatusBar
            mappingCompleteness={mappingCompleteness?.value ?? null}
            normalizedNodes={graph.nodes.length}
            declaredEdges={graph.edges.length}
            referenceMapVersion={graph.reference_map_version ?? null}
            projectionActive={graphHasPlanes}
            sourceLabel={dataSourceMode === "api" ? "API" : "Sample"}
          />
        </div>

      </main>

      <ChatPanel open={chatOpen} onClose={() => setChatOpen(false)} />

      {readinessOpen && !showOverlay && payload ? (
        <ReadinessPanel
          report={payload.viewer_load_result.readiness_report}
          graph={graph}
          apiBaseUrl={apiBaseUrl}
          mapReportEnabled={dataSourceMode === "api"}
          isHistoricalBuild={dataSourceMode === "api" && activeBuildId != null}
          onClose={() => setReadinessOpen(false)}
        />
      ) : null}

      {architectureInfoOpen ? (
        <ArchitectureInfoDialog graph={graph} onClose={() => setArchitectureInfoOpen(false)} />
      ) : null}

      {scanFlow.dialogOpen ? (
        <BoundaryDecisionModal
          status={scanFlow.status}
          preflight={scanFlow.preflight}
          decisions={scanFlow.decisionsByIdentity}
          requestedPaths={scanFlow.requestedPaths}
          missingRequiredCount={scanFlow.missingRequiredCount}
          error={scanFlow.error}
          notice={scanFlow.notice}
          isBusy={scanFlow.isBusy}
          onDecisionChange={scanFlow.setDecision}
          onCheckPath={(path) => void scanFlow.checkPath(path)}
          onRemoveRequestedPath={(path) => void scanFlow.removeRequestedPath(path)}
          onLoadMore={() => void scanFlow.loadMore()}
          onRetryPreflight={() => void scanFlow.retryPreflight()}
          onSubmit={() => void scanFlow.submit()}
          onCancel={scanFlow.cancel}
        />
      ) : null}

      <WordingProvider>
        {view === "scan-template" ? (
          <MappingProfileDialog
            dataSourceMode={dataSourceMode}
            buildId={payload?.viewer_load_result.build_id ?? null}
            profileInference={payload?.viewer_load_result.profile_inference_result ?? null}
            warnings={payload?.viewer_load_result.warnings ?? []}
            isProfileLoading={dataSourceMode === "api" && payloadQuery.isFetching && !payload}
            profileError={dataSourceMode === "api" ? sourceError : undefined}
            onRetryProfile={() => void payloadQuery.refetch()}
            onClose={() => setView("viewer")}
          />
        ) : null}

        {proposalTarget && canReviewCurrentMapping && traceProjectId && traceBuildId ? (
          <ProposalModal
            node={proposalTarget}
            apiBaseUrl={apiBaseUrl}
            projectId={traceProjectId}
            buildId={traceBuildId}
            onApplied={() => {
              setActiveBuildId(null);
              setProposalTarget(null);
            }}
            onClose={() => setProposalTarget(null)}
          />
        ) : null}
      </WordingProvider>
    </div>
  );
}
