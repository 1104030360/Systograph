import { render } from "@testing-library/react";
import { ReactFlowProvider, type NodeProps } from "reactflow";
import { describe, expect, it, vi } from "vitest";
import { graphNodeSchema } from "../types";
import type { FlowNodeData } from "../utils/graph";
import { SystemNode } from "./SystemNode";

function nodeProps(data: FlowNodeData): NodeProps<FlowNodeData> {
  return {
    id: data.id,
    type: "systemNode",
    data,
    selected: false,
    isConnectable: false,
    zIndex: 0,
    xPos: 0,
    yPos: 0,
    dragging: false,
  };
}

describe("SystemNode", () => {
  it("deduplicates repeated backend badges without emitting a React key warning", () => {
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    const data: FlowNodeData = {
      ...graphNodeSchema.parse({
        id: "node:reference:client_app",
        label: "Client App",
        status: "undetermined",
        activation: "not_applicable",
        semantic_kind: "reference_capability",
        badges: ["not_applicable", "not_applicable"],
      }),
      isFocused: false,
      isDimmed: false,
      isSelected: false,
      isProgressTarget: false,
    };

    try {
      const { container } = render(
        <ReactFlowProvider>
          <SystemNode {...nodeProps(data)} />
        </ReactFlowProvider>,
      );

      expect([...container.querySelectorAll(".node-badge")].map((badge) => badge.textContent)).toEqual([
        "not_applicable",
      ]);
      expect(
        errorSpy.mock.calls.some((call) => call.some((value) => String(value).includes("same key"))),
      ).toBe(false);
    } finally {
      errorSpy.mockRestore();
    }
  });
});
