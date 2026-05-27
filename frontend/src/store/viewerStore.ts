import { create } from "zustand";
import type { ScanTarget, Selection, TraceEvent } from "../types";

type ViewerState = {
  selected: Selection;
  activeFilterIds: string[];
  activeTraceIndex: number;
  isReplayRunning: boolean;
  progressIndex: number;
  isProgressRunning: boolean;
  detailMode: "overview" | "component" | "code_path";
  setSelected: (selected: Selection) => void;
  toggleFilter: (id: string) => void;
  clearFilters: () => void;
  setActiveTraceIndex: (index: number) => void;
  setReplayRunning: (running: boolean) => void;
  setProgressRunning: (running: boolean) => void;
  setProgressIndex: (index: number) => void;
  setDetailMode: (mode: ViewerState["detailMode"]) => void;
  resetFocus: () => void;
};

export const useViewerStore = create<ViewerState>((set) => ({
  selected: null,
  activeFilterIds: ["filter:flow:query_answer"],
  activeTraceIndex: 0,
  isReplayRunning: false,
  progressIndex: 0,
  isProgressRunning: false,
  detailMode: "overview",
  setSelected: (selected) => set({ selected, detailMode: "overview" }),
  toggleFilter: (id) =>
    set((state) => ({
      activeFilterIds: state.activeFilterIds.includes(id)
        ? state.activeFilterIds.filter((filterId) => filterId !== id)
        : [...state.activeFilterIds, id],
    })),
  clearFilters: () => set({ activeFilterIds: [] }),
  setActiveTraceIndex: (activeTraceIndex) => set({ activeTraceIndex }),
  setReplayRunning: (isReplayRunning) => set({ isReplayRunning }),
  setProgressRunning: (isProgressRunning) => set({ isProgressRunning }),
  setProgressIndex: (progressIndex) => set({ progressIndex }),
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
