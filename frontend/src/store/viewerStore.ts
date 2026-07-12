import { create } from "zustand";
import type { DataSourceMode, ScanProgressEvent, ScanTarget, Selection, TraceEvent } from "../types";

type ViewerState = {
  dataSourceMode: DataSourceMode;
  apiBaseUrl: string;
  /** Imported project driving build-scoped API reads; null before any import. */
  activeProjectId: string | null;
  /** Selected historical build; null means "follow the project's latest build". */
  activeBuildId: string | null;
  selected: Selection;
  activeFilterIds: string[];
  activeLensId: string | null;
  activeTraceIndex: number;
  isReplayRunning: boolean;
  progressIndex: number;
  isProgressRunning: boolean;
  followFocus: boolean;
  liveProgressEvent: ScanProgressEvent | null;
  detailMode: "overview" | "component" | "code_path";
  setDataSourceMode: (mode: DataSourceMode) => void;
  setApiBaseUrl: (baseUrl: string) => void;
  setActiveProjectId: (projectId: string | null) => void;
  setActiveBuildId: (buildId: string | null) => void;
  setSelected: (selected: Selection) => void;
  toggleFilter: (id: string) => void;
  toggleLens: (id: string) => void;
  clearFilters: () => void;
  setActiveTraceIndex: (index: number) => void;
  setReplayRunning: (running: boolean) => void;
  setProgressRunning: (running: boolean) => void;
  setProgressIndex: (index: number) => void;
  setFollowFocus: (enabled: boolean) => void;
  setLiveProgressEvent: (event: ScanProgressEvent | null) => void;
  setDetailMode: (mode: ViewerState["detailMode"]) => void;
  resetFocus: () => void;
};

// || (not ??): an empty VITE_API_BASE_URL must still fall back to the default.
const defaultApiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export const useViewerStore = create<ViewerState>((set) => ({
  dataSourceMode: "sample",
  apiBaseUrl: defaultApiBaseUrl,
  activeProjectId: null,
  activeBuildId: null,
  selected: null,
  activeFilterIds: ["filter:flow:query_answer"],
  activeLensId: null,
  activeTraceIndex: 0,
  isReplayRunning: false,
  progressIndex: 0,
  isProgressRunning: false,
  followFocus: true,
  liveProgressEvent: null,
  detailMode: "overview",
  setDataSourceMode: (dataSourceMode) => set({ dataSourceMode, liveProgressEvent: null }),
  setApiBaseUrl: (apiBaseUrl) => set({ apiBaseUrl }),
  // Switching projects always leaves historical-build viewing.
  setActiveProjectId: (activeProjectId) => set({ activeProjectId, activeBuildId: null }),
  setActiveBuildId: (activeBuildId) => set({ activeBuildId }),
  setSelected: (selected) => set({ selected, detailMode: "overview" }),
  toggleFilter: (id) =>
    set((state) => ({
      activeFilterIds: state.activeFilterIds.includes(id)
        ? state.activeFilterIds.filter((filterId) => filterId !== id)
        : [...state.activeFilterIds, id],
    })),
  toggleLens: (id) =>
    set((state) => ({
      activeLensId: state.activeLensId === id ? null : id,
    })),
  clearFilters: () => set({ activeFilterIds: [], activeLensId: null }),
  setActiveTraceIndex: (activeTraceIndex) => set({ activeTraceIndex }),
  setReplayRunning: (isReplayRunning) => set({ isReplayRunning }),
  setProgressRunning: (isProgressRunning) => set({ isProgressRunning }),
  setProgressIndex: (progressIndex) => set({ progressIndex }),
  setFollowFocus: (followFocus) => set({ followFocus }),
  setLiveProgressEvent: (liveProgressEvent) => set({ liveProgressEvent }),
  setDetailMode: (detailMode) => set({ detailMode }),
  resetFocus: () =>
    set({
      selected: null,
      activeTraceIndex: 0,
      progressIndex: 0,
      isReplayRunning: false,
      isProgressRunning: false,
      detailMode: "overview",
    }),
}));

export function traceTarget(event: TraceEvent): ScanTarget | null {
  if (event.component_id) {
    return {
      kind: "node",
      id: event.component_id,
      label: event.slot ?? event.component_id,
    };
  }

  if (event.unmapped_component_id) {
    return {
      kind: "node",
      id: event.unmapped_component_id,
      label: "Needs confirmation",
    };
  }

  if (event.edge_id) {
    return {
      kind: "edge",
      id: event.edge_id,
      label: event.edge_id,
    };
  }

  return null;
}
