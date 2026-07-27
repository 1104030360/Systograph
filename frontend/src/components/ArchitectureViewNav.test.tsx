import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { ArchitectureViewModel } from "../utils/architectureViews";
import { ArchitectureViewNav } from "./ArchitectureViewNav";

const views: ArchitectureViewModel[] = [
  {
    id: "overview",
    label: "Overview",
    description: "The complete backend projection",
    supported: true,
    unavailableReason: null,
    matchesNodeIds: ["node:one", "node:two"],
    matchesEdgeIds: [],
  },
  {
    id: "runtime",
    label: "Runtime",
    description: "Runtime trace membership",
    supported: false,
    unavailableReason: "Runtime metadata is unavailable.",
    matchesNodeIds: [],
    matchesEdgeIds: [],
  },
];

describe("ArchitectureViewNav", () => {
  it("renders a compact Filter heading while keeping descriptions accessible", () => {
    const { container } = render(
      <ArchitectureViewNav
        views={views}
        activeViewId="overview"
        search=""
        onSelect={() => {}}
        onSearchChange={() => {}}
      />,
    );

    expect(screen.getByRole("heading", { name: "Filter" })).toBeInTheDocument();
    expect(screen.queryByText("Filter Views")).toBeNull();
    expect(screen.getByRole("button", { name: /Overview.*complete backend projection/ })).toHaveAttribute(
      "title",
      "The complete backend projection",
    );
    expect(screen.getByRole("button", { name: /Runtime.*metadata is unavailable/ })).toBeDisabled();
    expect(container.querySelector(".dr-schema-card")).toBeNull();
    expect(container.querySelector(".dr-filter-scroll")).not.toBeNull();
    expect(container.querySelector(".prototype-icon-overview")).not.toBeNull();
    expect(container.querySelectorAll(".dr-filter-icon svg")).toHaveLength(views.length);
    expect(container.querySelectorAll('.dr-filter-icon[aria-hidden="true"]')).toHaveLength(views.length);
    const legend = screen.getByRole("group", { name: "Assessment and node kind legend" });
    expect(legend).toHaveTextContent("Detected");
    expect(legend).toHaveTextContent("Partial");
    expect(legend).toHaveTextContent("Undetermined");
    expect(legend).toHaveTextContent("Reference");
    expect(legend).toHaveTextContent("Mapping");
  });
});
