import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SampleDataIndicator } from "./SampleDataIndicator";

describe("SampleDataIndicator", () => {
  it("renders a persistent disclosure in sample mode", () => {
    render(<SampleDataIndicator visible />);

    expect(screen.getByRole("note", { name: "Sample data indicator" })).toHaveTextContent(
      "Sample data — example map, not a real scan",
    );
  });

  it("does not render in API mode", () => {
    render(<SampleDataIndicator visible={false} />);

    expect(screen.queryByRole("note", { name: "Sample data indicator" })).not.toBeInTheDocument();
  });
});
