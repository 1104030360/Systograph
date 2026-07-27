import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PrototypeIcon, type PrototypeIconKind } from "./PrototypeIcon";

const KINDS: PrototypeIconKind[] = [
  "overview",
  "data",
  "control",
  "ingestion",
  "retrieval",
  "memory",
  "governance",
  "runtime",
  "variant",
  "risk",
  "known",
  "extension",
  "unmapped",
  "mode",
  "topology",
  "source",
];

describe("PrototypeIcon", () => {
  it.each(KINDS)("renders %s as a bounded scalable SVG glyph", (kind) => {
    const { container } = render(<PrototypeIcon kind={kind} size={23} />);
    const tile = container.firstElementChild;
    const glyph = tile?.querySelector("svg");

    expect(tile).toHaveClass("prototype-icon", `prototype-icon-${kind}`);
    expect(tile).toHaveStyle({ "--prototype-icon-size": "23px" });
    expect(tile).toHaveAttribute("aria-hidden", "true");
    expect(glyph).not.toBeNull();
    expect(glyph).toHaveAttribute("width", "14");
    expect(glyph).toHaveAttribute("height", "14");
  });

  it("uses distinct semantic glyphs for the previously distorted filter icons", () => {
    const problemKinds: PrototypeIconKind[] = ["retrieval", "variant", "topology", "ingestion", "memory"];
    const glyphClasses = problemKinds.map((kind) => {
      const { container, unmount } = render(<PrototypeIcon kind={kind} />);
      const className = container.querySelector("svg")?.getAttribute("class");
      unmount();
      return className;
    });

    expect(new Set(glyphClasses).size).toBe(problemKinds.length);
  });
});
