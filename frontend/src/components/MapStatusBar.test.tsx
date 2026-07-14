import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MapStatusBar } from "./MapStatusBar";

describe("MapStatusBar", () => {
  it("renders backend map metrics and an accessible completeness bar", () => {
    render(
      <MapStatusBar
        mappingCompleteness={0.067}
        normalizedNodes={70}
        declaredEdges={9}
        referenceMapVersion="1"
        projectionActive
        sourceLabel="API"
      />,
    );

    expect(screen.getByText("6.7%")).toBeInTheDocument();
    expect(screen.getByText("70")).toBeInTheDocument();
    expect(screen.getByText("9")).toBeInTheDocument();
    expect(screen.getByText("Reference projection active")).toBeInTheDocument();
    expect(screen.getByRole("progressbar", { name: "Mapping completeness" })).toHaveAttribute(
      "aria-valuenow",
      "6.7",
    );
  });

  it("keeps unavailable completeness explicit", () => {
    render(
      <MapStatusBar
        mappingCompleteness={null}
        normalizedNodes={0}
        declaredEdges={0}
        referenceMapVersion={null}
        projectionActive={false}
        sourceLabel="Sample"
      />,
    );

    expect(screen.getByRole("progressbar", { name: "Mapping completeness" })).not.toHaveAttribute("aria-valuenow");
    expect(screen.getByText("Projection unavailable")).toBeInTheDocument();
  });
});
