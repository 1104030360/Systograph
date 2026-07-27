import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { GraphLensModel } from "../types";
import { LensPanel } from "./LensPanel";

function lens(overrides: Partial<GraphLensModel> & { id: string; label: string }): GraphLensModel {
  return {
    supported: true,
    unavailable_reason: null,
    matches_node_ids: [],
    matches_edge_ids: [],
    ...overrides,
  };
}

describe("LensPanel", () => {
  it("disables all six lenses with an explanation when membership is missing", () => {
    render(<LensPanel lenses={[]} activeLensId={null} onToggleLens={() => {}} />);

    const buttons = screen.getAllByRole("button");
    expect(buttons).toHaveLength(6);
    buttons.forEach((button) => {
      expect(button).toBeDisabled();
    });
    expect(screen.getByRole("note")).toHaveTextContent("does not include lens membership");
  });

  it("renders a distinct decorative icon per fixed lens", () => {
    const { container } = render(<LensPanel lenses={[]} activeLensId={null} onToggleLens={() => {}} />);

    const icons = [...container.querySelectorAll("button .lens-ico")];
    expect(icons).toHaveLength(6);
    icons.forEach((icon) => {
      expect(icon).toHaveAttribute("aria-hidden", "true");
    });
    const glyphClasses = new Set(icons.map((icon) => icon.getAttribute("class")));
    expect(glyphClasses.size).toBe(6);
  });

  it("toggles a supported lens and marks it pressed", () => {
    const onToggleLens = vi.fn();
    render(
      <LensPanel
        lenses={[lens({ id: "lens:data", label: "Data", matches_node_ids: ["node:a"] })]}
        activeLensId="lens:data"
        onToggleLens={onToggleLens}
      />,
    );

    const dataButton = screen.getByRole("button", { name: /Data/ });
    expect(dataButton).toHaveAttribute("aria-pressed", "true");
    expect(dataButton).toHaveTextContent("1");

    fireEvent.click(dataButton);
    expect(onToggleLens).toHaveBeenCalledWith("lens:data");
  });

  it("keeps an unsupported lens disabled with the backend reason", () => {
    render(
      <LensPanel
        lenses={[lens({ id: "lens:risk", label: "Risk", supported: false, unavailable_reason: "risk sidecar not generated" })]}
        activeLensId={null}
        onToggleLens={() => {}}
      />,
    );

    const riskButton = screen.getByRole("button", { name: /Risk/ });
    expect(riskButton).toBeDisabled();
    expect(riskButton).toHaveAttribute("title", "risk sidecar not generated");
  });

  it("announces when the active lens matches nothing in this build", () => {
    render(
      <LensPanel
        lenses={[lens({ id: "lens:evidence", label: "Evidence" })]}
        activeLensId="lens:evidence"
        onToggleLens={() => {}}
      />,
    );

    expect(screen.getByRole("status")).toHaveTextContent("No items match the Evidence lens");
  });
});
