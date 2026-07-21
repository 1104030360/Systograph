import { render } from "@testing-library/react";
import { Telescope } from "lucide-react";
import { describe, expect, it } from "vitest";
import { GRAPH_STUDIO_LENS_KEYS } from "../utils/lenses";
import { PLANE_PRESENTATION_ORDER, UNASSIGNED_PLANE_ID } from "../utils/planes";
import { BrandMark } from "./BrandMark";
import { getLensIcon, getPlaneIcon, LENS_ICONS, PLANE_ICONS } from "./registry";

describe("icon registry", () => {
  it("maps each fixed lens to a distinct icon", () => {
    const icons = GRAPH_STUDIO_LENS_KEYS.map((key) => LENS_ICONS[key]);
    expect(new Set(icons).size).toBe(GRAPH_STUDIO_LENS_KEYS.length);
  });

  it("resolves backend lens ids and labels to the same icon as the fixed key", () => {
    expect(getLensIcon("lens:data")).toBe(LENS_ICONS.data);
    expect(getLensIcon("Risk")).toBe(LENS_ICONS.risk);
  });

  it("falls back to the generic lens glyph for extra backend lenses", () => {
    expect(getLensIcon("lens:latency")).toBe(Telescope);
  });

  it("covers exactly the canonical backend planes", () => {
    PLANE_PRESENTATION_ORDER.forEach((planeId) => {
      expect(getPlaneIcon(planeId), `missing icon for plane ${planeId}`).toBeDefined();
    });
    expect(Object.keys(PLANE_ICONS).sort()).toEqual([...PLANE_PRESENTATION_ORDER].sort());
  });

  it("renders no icon for unassigned, unknown, or missing plane ids", () => {
    expect(getPlaneIcon(UNASSIGNED_PLANE_ID)).toBeUndefined();
    expect(getPlaneIcon("plane:mystery")).toBeUndefined();
    expect(getPlaneIcon(null)).toBeUndefined();
    expect(getPlaneIcon(undefined)).toBeUndefined();
  });
});

describe("BrandMark", () => {
  it("is decorative and preserves the original prototype palette", () => {
    const { container } = render(<BrandMark />);
    const svg = container.querySelector("svg");
    expect(svg).not.toBeNull();
    expect(svg).toHaveAttribute("aria-hidden", "true");
    expect(svg).toHaveAttribute("focusable", "false");
    expect(container.innerHTML).toContain("#256ee8");
    expect(container.innerHTML).toContain("#22b35d");
    expect(container.innerHTML).toContain("#ff9f1c");
    expect(container.innerHTML).toContain("#8a45d7");
  });
});
