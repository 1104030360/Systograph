import { describe, expect, it } from "vitest";
import { graphViewModelSchema, type TraceEvent } from "../types";
import { resolveTraceHighlight, sortTraceEvents } from "./trace";

const graph = graphViewModelSchema.parse({
  nodes: [
    { id: "node:component:chat", component_id: "component:chat", label: "Chat", badges: [] },
  ],
  edges: [
    { id: "edge:chat:answer", source_id: "flow:chat:answer", from: "node:component:chat", to: "node:component:chat" },
  ],
  endpoints: [
    { endpoint_id: "endpoint:chat", value: "https://example.test/chat", endpoint_type: "external", component_id: "component:chat" },
  ],
  details: {},
  filters: {},
});

function event(overrides: Partial<TraceEvent> = {}): TraceEvent {
  return {
    id: "event:1",
    sequence_index: 1,
    timestamp: "2026-07-21T00:00:01Z",
    warnings: [],
    ...overrides,
  };
}

describe("trace utilities", () => {
  it("sorts exclusively by backend sequence_index with a stable id tie-break", () => {
    expect(sortTraceEvents([event({ id: "b", sequence_index: 2 }), event({ id: "a", sequence_index: 0 })]))
      .toEqual([event({ id: "a", sequence_index: 0 }), event({ id: "b", sequence_index: 2 })]);
  });

  it("highlights only exact projection identities and explicit endpoint linkage", () => {
    expect(resolveTraceHighlight(event({ endpoint_id: "endpoint:chat" }), graph)).toEqual({
      nodeIds: ["node:component:chat"],
      edgeIds: [],
      fallbackMessage: null,
    });
    expect(resolveTraceHighlight(event({ edge_id: "flow:chat:answer" }), graph)).toEqual({
      nodeIds: [],
      edgeIds: ["edge:chat:answer"],
      fallbackMessage: null,
    });
  });

  it("returns a bounded fallback instead of guessing from slot or topology", () => {
    const result = resolveTraceHighlight(
      event({ component_id: "component:missing", slot: "generation" }),
      graph,
    );

    expect(result.nodeIds).toEqual([]);
    expect(result.edgeIds).toEqual([]);
    expect(result.fallbackMessage).toContain("No exact architecture match for component:missing");
  });
});
