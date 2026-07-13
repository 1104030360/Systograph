import { render } from "@testing-library/react";
import type { NodeProps } from "reactflow";
import { describe, expect, it } from "vitest";
import { UNASSIGNED_PLANE_ID } from "../utils/planes";
import { PlaneBandNode, type PlaneBandData } from "./PlaneBandNode";

function bandProps(data: PlaneBandData): NodeProps<PlaneBandData> {
  return {
    id: `plane-band:${data.planeId}`,
    type: "planeBand",
    data,
    selected: false,
    isConnectable: false,
    zIndex: -1,
    xPos: 0,
    yPos: 0,
    dragging: false,
  };
}

describe("PlaneBandNode", () => {
  it("shows the registry icon for a canonical backend plane", () => {
    const { container } = render(
      <PlaneBandNode {...bandProps({ planeId: "control", label: "Control", sublabel: null, count: 3 })} />,
    );

    const icon = container.querySelector(".plane-band-head .plane-band-ico");
    expect(icon).not.toBeNull();
    expect(icon).toHaveAttribute("aria-hidden", "true");
    expect(container.querySelector(".plane-band-head strong")).toHaveTextContent("Control");
    expect(container.querySelector(".plane-band-head span")).toHaveTextContent("3");
  });

  it("renders no icon for the unassigned band", () => {
    const { container } = render(
      <PlaneBandNode
        {...bandProps({
          planeId: UNASSIGNED_PLANE_ID,
          label: "Unassigned components",
          sublabel: "plane not published by this build",
          count: 2,
        })}
      />,
    );

    expect(container.querySelector(".plane-band-ico")).toBeNull();
    expect(container.querySelector(".plane-band-head strong")).toHaveTextContent("Unassigned components");
  });

  it("renders no icon for a plane id outside the registry instead of inferring one", () => {
    const { container } = render(
      <PlaneBandNode {...bandProps({ planeId: "future_plane", label: "Future Plane", sublabel: null, count: 1 })} />,
    );

    expect(container.querySelector(".plane-band-ico")).toBeNull();
    expect(container.querySelector(".plane-band-head strong")).toHaveTextContent("Future Plane");
  });

  it("stays visual chrome only: the band is hidden from the accessibility tree", () => {
    const { container } = render(
      <PlaneBandNode {...bandProps({ planeId: "retrieval", label: "Retrieval", sublabel: null, count: 4 })} />,
    );

    expect(container.querySelector(".plane-band")).toHaveAttribute("aria-hidden", "true");
  });
});
