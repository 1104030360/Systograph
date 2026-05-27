import { useEffect, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Database, GitBranch, Layers3, SearchCode } from "lucide-react";
import { DetailPanel } from "./components/DetailPanel";
import { ProgressStrip } from "./components/ProgressStrip";
import { ReplayTimeline } from "./components/ReplayTimeline";
import { Sidebar } from "./components/Sidebar";
import { SystemGraph } from "./components/SystemGraph";
import { defaultTraceEvents, graphViewModel, viewerPayload } from "./data/sampleMap";
import { useViewerStore } from "./store/viewerStore";
import { createProgressTargets } from "./utils/graph";

function useViewerPayload() {
  return useQuery({
    queryKey: ["viewer-load-result", "sample"],
    queryFn: async () => viewerPayload,
    staleTime: Number.POSITIVE_INFINITY,
  });
}

export default function App() {
  const payloadQuery = useViewerPayload();
  const graph = payloadQuery.data?.viewer_load_result.graph_view_model ?? graphViewModel;
  const progressTargets = useMemo(() => createProgressTargets(graph), [graph]);
  const selected = useViewerStore((state) => state.selected);
  const activeFilterIds = useViewerStore((state) => state.activeFilterIds);
  const activeTraceIndex = useViewerStore((state) => state.activeTraceIndex);
  const isReplayRunning = useViewerStore((state) => state.isReplayRunning);
  const isProgressRunning = useViewerStore((state) => state.isProgressRunning);
  const progressIndex = useViewerStore((state) => state.progressIndex);
  const detailMode = useViewerStore((state) => state.detailMode);
  const setSelected = useViewerStore((state) => state.setSelected);
  const toggleFilter = useViewerStore((state) => state.toggleFilter);
  const clearFilters = useViewerStore((state) => state.clearFilters);
  const setActiveTraceIndex = useViewerStore((state) => state.setActiveTraceIndex);
  const setReplayRunning = useViewerStore((state) => state.setReplayRunning);
  const setProgressRunning = useViewerStore((state) => state.setProgressRunning);
  const setProgressIndex = useViewerStore((state) => state.setProgressIndex);
  const setDetailMode = useViewerStore((state) => state.setDetailMode);
  const resetFocus = useViewerStore((state) => state.resetFocus);
  const activeTraceEvent = defaultTraceEvents[activeTraceIndex];
  const progressTarget = progressTargets[progressIndex];

  useEffect(() => {
    if (!isReplayRunning || defaultTraceEvents.length === 0) return;

    const timer = window.setInterval(() => {
      setActiveTraceIndex((activeTraceIndex + 1) % defaultTraceEvents.length);
    }, 1100);

    return () => window.clearInterval(timer);
  }, [activeTraceIndex, isReplayRunning, setActiveTraceIndex]);

  useEffect(() => {
    if (!isProgressRunning || progressTargets.length === 0) return;

    const timer = window.setInterval(() => {
      setProgressIndex((progressIndex + 1) % progressTargets.length);
    }, 850);

    return () => window.clearInterval(timer);
  }, [isProgressRunning, progressIndex, progressTargets.length, setProgressIndex]);

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
              {String(viewerPayload.viewer_load_result.ai_system_map.scan_depth ?? "system")}
            </span>
          </div>
          <button className="toolbar-button" type="button" onClick={resetFocus}>
            Reset
          </button>
        </header>

        <div className="graph-frame">
          <ProgressStrip targets={progressTargets} activeIndex={progressIndex} isRunning={isProgressRunning} onRunningChange={setProgressRunning} />
          <SystemGraph
            graph={graph}
            activeFilterIds={activeFilterIds}
            selected={selected}
            traceEvent={activeTraceEvent}
            progressTargetId={progressTarget?.id}
            onSelect={setSelected}
          />
        </div>

        <ReplayTimeline
          events={defaultTraceEvents}
          activeIndex={activeTraceIndex}
          isRunning={isReplayRunning}
          onIndexChange={setActiveTraceIndex}
          onRunningChange={setReplayRunning}
        />
      </section>

      <DetailPanel graph={graph} payload={viewerPayload} selected={selected} detailMode={detailMode} onDetailModeChange={setDetailMode} />
    </main>
  );
}
