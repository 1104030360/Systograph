import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MappingCompletenessPanel } from "./MappingCompletenessPanel";

const completeness = {
  numerator: 4,
  denominator: 52,
  value: 0.076923,
  weights: {
    detected: 1,
    partial: 0.5,
    undetermined: 0,
    not_detected: 1,
    conflicted: 0,
  },
};

describe("MappingCompletenessPanel", () => {
  it("renders backend-provided value, scope, and activation boundary", () => {
    render(<MappingCompletenessPanel completeness={completeness} buildId="build:sample-b2" warningCount={1} />);

    expect(screen.getByText("7.7%")).toBeInTheDocument();
    expect(screen.getByText("4 weighted / 52 reference nodes")).toBeInTheDocument();
    expect(screen.getByText(/activation excluded/)).toBeInTheDocument();
    expect(screen.getByText(/1 load warning$/)).toBeInTheDocument();
  });

  it("does not fabricate a percentage when scope is absent", () => {
    render(<MappingCompletenessPanel />);

    expect(screen.getByText("Mapping completeness unavailable")).toBeInTheDocument();
    expect(screen.queryByText(/%/)).not.toBeInTheDocument();
  });
});
