import { useCallback, useEffect, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ClipboardCheck, Folder, Layers3, MessageCircle, Moon, MoreHorizontal, RotateCcw, Share2, Sun } from "lucide-react";
import { ArchitectureMap } from "./components/ArchitectureMap";
import { ArchitectureViewNav } from "./components/ArchitectureViewNav";
import { ChatPanel } from "./components/ChatPanel";
import { BoundaryDecisionModal, decisionsForBoundary } from "./components/BoundaryDecisionModal";
import { BuildHistoryMenu } from "./components/BuildHistoryMenu";
import { DataSourceControl } from "./components/DataSourceControl";
import { DetailPanel } from "./components/DetailPanel";
import { MapStatusBar } from "./components/MapStatusBar";
import { ProgressStrip } from "./components/ProgressStrip";
import { ReadinessPanel } from "./components/ReadinessPanel";
import { StateOverlay, type ViewerState } from "./components/StateOverlay";
import { ScanTemplatePage } from "./pages/ScanTemplatePage";
import { ProposalModal, type ProposalTarget } from "./components/proposal/ProposalModal";
import { WordingProvider } from "./wording";
import { viewerPayload as sampleViewerPayload } from "./data/sampleMap";
import { BrandMark } from "./icons/BrandMark";
import { useMapBuilds } from "./hooks/useMapBuilds";
import { useScanProgress } from "./hooks/useScanProgress";
import { useTheme } from "./hooks/useTheme";
import { useViewerPayload } from "./hooks/useViewerPayload";
import { extractMappingCompleteness } from "./contracts/viewer";
import { importProject, startProjectScan } from "./services/projectScanApi";
import { loadApiViewerPayload } from "./services/viewerApi";
import { useViewerStore } from "./store/viewerStore";
import type { GraphViewModel, ProjectImportResponse, ScanBoundaryAction, ScanBoundaryProposal } from "./types";
import { buildArchitectureViews, type ArchitectureViewId } from "./utils/architectureViews";
import { hasBackendPlaneProjection } from "./utils/planes";

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
  const [readinessOpen, setReadinessOpen] = useState(false);

  // The node/edge inspector and the readiness drawer share the right rail, so
  // making a selection (including readiness component drilldown) closes the drawer.
  useEffect(() => {
    if (selected) setReadinessOpen(false);
  }, [selected]);

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
    async (projectId: string) => {
      const freshPayload = await loadApiViewerPayload(apiBaseUrl, undefined, projectId);
      queryClient.setQueryData(["viewer-load-result", "api", apiBaseUrl, projectId, null], freshPayload);
      void queryClient.invalidateQueries({ queryKey: ["map-builds"] });
      setActiveProjectId(projectId);
      setActiveBuildId(null);
      setDataSourceMode("api");
      setProgressRunning(false);
      setLiveProgressEvent({
        event: "scan_progress",
        status: "completed",
        stage: "map",
        message: "Scan completed. Loading map.",
        percent: 100,
      });
    },
    [apiBaseUrl, queryClient, setActiveBuildId, setActiveProjectId, setDataSourceMode, setLiveProgressEvent, setProgressRunning],
  );

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
          setProgressRunning(false);
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
        await completeScanFlow(session.project_id);
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        setScanFlowError(message);
        setProgressRunning(false);
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
    [apiBaseUrl, completeScanFlow, setLiveProgressEvent, setProgressRunning],
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
      setProgressRunning(false);
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

  const projectName = graph.summary?.project_name ? String(graph.summary.project_name) : "Local AI Health Doctor";

  return (
    <div className="dr-app">
      <a className="skip-link" href="#architecture-workspace">Skip to AI Agent System</a>

      <header className="dr-header">
        <a className="dr-brand" href="#top" aria-label="Agent System Map home">
          <span className="dr-brand-mark" aria-hidden="true"><BrandMark size={22} /></span>
          <span>
            <strong>Agent System Map</strong>
            <small>Release-readiness architecture projection</small>
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

          <button className="btn" type="button" onClick={() => setView("scan-template")} title="Scan template & mapping profile">
            <Layers3 size={14} />
            Mapping profile
          </button>
          <button
            className={readinessOpen ? "btn is-active" : "btn"}
            type="button"
            aria-pressed={readinessOpen}
            disabled={!dataAvailable}
            onClick={() => setReadinessOpen(!readinessOpen)}
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
            isScanning={scanBusy}
            error={sourceError}
            scanError={scanFlowError}
            onModeChange={setDataSourceMode}
            onApiBaseUrlChange={setApiBaseUrl}
            onProjectPathChange={setProjectPath}
            onRefresh={() => void payloadQuery.refetch()}
            onStartScan={() => void handleStartScan()}
          />
          <details className="toolbar-menu more-menu">
            <summary className="icon-btn" aria-label="More tools" title="More tools"><MoreHorizontal size={16} /></summary>
            <div className="toolbar-popover align-right">
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
        </nav>
      </header>

      <main className="dr-main" id="top">
        <section className="dr-context-strip" aria-labelledby="page-title">
          <div className="dr-context-copy">
            <span className="eyebrow">{dataSourceMode === "api" ? "Backend build projection" : "Legacy sample payload"}</span>
            <h1 id="page-title">AI Agent System · 10-plane normalized architecture</h1>
            <p>
              A backend-driven view of reference capabilities, repository components, assessment state, evidence and risk.
              The UI does not infer missing plane or lens membership.
            </p>
          </div>
        </section>

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
          <section className="dr-map-panel" aria-labelledby="architecture-map-title">
            <header className="dr-map-toolbar">
              <div>
                <span className="eyebrow">Normalized reference map</span>
                <h2 id="architecture-map-title">AI Agent System</h2>
                <p>
                  {architectureViews.find((candidate) => candidate.id === activeArchitectureView)?.description}
                </p>
              </div>
              <button
                className="btn"
                type="button"
                onClick={() => {
                  setActiveArchitectureView("overview");
                  setNodeSearch("");
                  setSelected(null);
                }}
              >
                <RotateCcw size={14} />
                Reset view
              </button>
            </header>

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
                  onSelect={setSelected}
                />
              )}

              {readinessOpen && !selected && !showOverlay && payload ? (
                <ReadinessPanel
                  report={payload.viewer_load_result.readiness_report}
                  graph={graph}
                  onClose={() => setReadinessOpen(false)}
                />
              ) : null}
            </div>
          </section>

          <aside className="dr-inspector-panel" aria-labelledby="node-inspector-title">
            <div className="dr-inspector-label">
              <span className="eyebrow">Selection details</span>
              <h2 id="node-inspector-title">Node Inspector</h2>
              <p>{selected ? "Backend-provided facts for the selected map element." : "Select a node or declared flow."}</p>
            </div>
            {selected && !showOverlay && payload ? (
              <DetailPanel
                graph={graph}
                payload={payload}
                selected={selected}
                detailMode={detailMode}
                onDetailModeChange={setDetailMode}
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
          </aside>
        </section>

        <section className="dr-explain-grid" aria-label="How to read the architecture map">
          <article>
            <span className="eyebrow">Architecture model</span>
            <h2>Why ten planes?</h2>
            <p>
              The fixed reference map separates intent, control, ingestion, retrieval, extensions, evidence, generation,
              memory, governance and deployment. Repository components are projected into these backend-owned planes.
            </p>
          </article>
          <article>
            <span className="eyebrow">Assessment model</span>
            <h2>Status is not activation</h2>
            <p>
              Assessment describes the available evidence; activation describes runtime configuration. Both values remain
              visible so an enabled component is never mistaken for a well-supported readiness finding.
            </p>
          </article>
          <article>
            <span className="eyebrow">Filter behavior</span>
            <h2>Backend membership only</h2>
            <p>
              Enabled views use published lenses, plane IDs and semantic kinds. Runtime, Variants and Reasoning Mode remain
              disabled until their metadata becomes part of the graph contract.
            </p>
          </article>
        </section>

        <section className="dr-backend-scope" aria-labelledby="backend-scope-title">
          <div>
            <span className="eyebrow">Current contract boundary</span>
            <h2 id="backend-scope-title">The frontend projects facts; it does not invent architecture.</h2>
            <p>
              Plane membership, lens membership, evidence, conflicts, endpoints and risk hints come from the selected immutable
              build. Missing metadata is presented as unavailable rather than reconstructed in the browser.
            </p>
          </div>
          <dl>
            <div><dt>Source schema</dt><dd>{graph.source_schema_version ?? "unavailable"}</dd></div>
            <div><dt>Graph schema</dt><dd>{graph.schema_version ?? "unavailable"}</dd></div>
            <div><dt>Build</dt><dd>{graph.build_id ?? "sample / unavailable"}</dd></div>
            <div><dt>Environment</dt><dd>{graph.environment_id ?? "unavailable"}</dd></div>
          </dl>
        </section>

        <MapStatusBar
          mappingCompleteness={mappingCompleteness?.value ?? null}
          normalizedNodes={graph.nodes.length}
          declaredEdges={graph.edges.length}
          referenceMapVersion={graph.reference_map_version ?? null}
          projectionActive={graphHasPlanes}
          sourceLabel={dataSourceMode === "api" ? "API" : "Sample"}
        />
      </main>

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
            // Cancelling the boundary review abandons this scan run: stop the
            // progress stream and return the strip to its idle state.
            setProgressRunning(false);
            setLiveProgressEvent(null);
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
          <ProposalModal node={proposalTarget} scenario="ok" onClose={() => setProposalTarget(null)} />
        ) : null}
      </WordingProvider>
    </div>
  );
}
