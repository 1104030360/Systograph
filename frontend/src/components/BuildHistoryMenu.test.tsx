import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { MapBuildHistorySummary } from "../contracts/viewer";
import { BuildHistoryMenu } from "./BuildHistoryMenu";

/* Backend order is generated_at ASC: the last entry is the latest build. */
const builds: MapBuildHistorySummary[] = [
  {
    project_id: "project:demo",
    scan_id: "scan:s1",
    build_id: "build:b1",
    based_on_build_id: null,
    build_reason: "initial_scan",
    applied_mapping_ids: [],
    generated_at: "2026-07-12T01:00:00Z",
  },
  {
    project_id: "project:demo",
    scan_id: "scan:s1",
    build_id: "build:b2",
    based_on_build_id: "build:b1",
    build_reason: "detail_scan",
    applied_mapping_ids: [],
    generated_at: "2026-07-12T02:00:00Z",
  },
];

describe("BuildHistoryMenu", () => {
  it("renders newest first and marks only the newest as latest", () => {
    render(<BuildHistoryMenu builds={builds} activeBuildId={null} onSelect={() => {}} />);

    const items = screen.getAllByRole("button", { name: /Scan/ });
    expect(items[0]).toHaveTextContent("Detail Scan");
    expect(items[0]).toHaveTextContent("latest");
    expect(items[1]).toHaveTextContent("Initial Scan");
    expect(items[1]).not.toHaveTextContent("latest");
  });

  it("marks the latest as viewed when no historical build is pinned", () => {
    render(<BuildHistoryMenu builds={builds} activeBuildId={null} onSelect={() => {}} />);

    const items = screen.getAllByRole("button", { name: /Scan/ });
    expect(items[0]).toHaveAttribute("aria-pressed", "true");
    expect(items[1]).toHaveAttribute("aria-pressed", "false");
  });

  it("selects a historical build by id and the latest as null", () => {
    const onSelect = vi.fn();
    render(<BuildHistoryMenu builds={builds} activeBuildId="build:b1" onSelect={onSelect} />);

    const items = screen.getAllByRole("button", { name: /Scan/ });
    expect(items[1]).toHaveAttribute("aria-pressed", "true");

    fireEvent.click(items[1]);
    expect(onSelect).toHaveBeenLastCalledWith("build:b1");

    fireEvent.click(items[0]);
    expect(onSelect).toHaveBeenLastCalledWith(null);
  });

  it("renders nothing without builds", () => {
    const { container } = render(<BuildHistoryMenu builds={[]} activeBuildId={null} onSelect={() => {}} />);
    expect(container).toBeEmptyDOMElement();
  });
});
