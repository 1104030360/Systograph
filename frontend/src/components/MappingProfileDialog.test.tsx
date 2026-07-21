import { fireEvent, render, screen } from "@testing-library/react";
import type { ComponentProps } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import profileInferenceSample from "../../../docs/work/Timmy/design/EPIC1/frontend-json-handoff/step-06-derived-assessment/frontend-profile-signals-sample.json";
import { MappingProfileDialog } from "./MappingProfileDialog";

const baseProps: ComponentProps<typeof MappingProfileDialog> = {
  dataSourceMode: "sample",
  buildId: "build:sample-b1",
  profileInference: profileInferenceSample,
  warnings: [],
  isProfileLoading: false,
  onRetryProfile: vi.fn(),
  onClose: vi.fn(),
};

function renderDialog(overrides: Partial<typeof baseProps> = {}) {
  const props = { ...baseProps, ...overrides };
  return {
    props,
    ...render(<MappingProfileDialog {...props} />),
  };
}

describe("MappingProfileDialog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders backend profile facts without repository-name or node-label inference", () => {
    renderDialog();

    expect(screen.getByRole("dialog", { name: "Mapping profile" })).toBeInTheDocument();
    expect(screen.getByText("15 capability profiles")).toBeInTheDocument();
    expect(screen.getByRole("article", { name: "Agentic Control" })).toBeInTheDocument();
    expect(screen.getByRole("article", { name: "Reranking" })).toHaveTextContent("0 / 1");
    expect(screen.getByText("Backend-owned · selected build only")).toBeInTheDocument();
    expect(screen.getByText(/does not infer a profile from repository names or graph labels/)).toBeInTheDocument();
  });

  it("shows missing profile sidecar facts as a degraded state", () => {
    renderDialog({
      profileInference: null,
      warnings: ["profile_signals_missing_or_invalid"],
    });

    expect(screen.getByText("Profile facts unavailable")).toBeInTheDocument();
    expect(screen.getByText(/base graph remains available/)).toBeInTheDocument();
  });

  it("shows profile loading, error, and retry states", () => {
    const onRetryProfile = vi.fn();
    const loading = renderDialog({ profileInference: null, isProfileLoading: true });
    expect(screen.getByText("Loading profile facts")).toBeInTheDocument();
    loading.unmount();

    renderDialog({
      profileInference: null,
      profileError: "Selected build request failed.",
      onRetryProfile,
    });
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(onRetryProfile).toHaveBeenCalledOnce();
  });

  it("does not trigger a new inventory scan when opened", () => {
    renderDialog({ dataSourceMode: "api" });

    expect(screen.queryByText(/inventory baseline/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/preflight/i)).not.toBeInTheDocument();
  });

  it("closes with Escape and from the backdrop", () => {
    const onClose = vi.fn();
    const { container } = renderDialog({ onClose });
    const dialog = screen.getByRole("dialog", { name: "Mapping profile" });
    const scrim = container.querySelector(".mapping-profile-scrim");

    fireEvent.mouseDown(dialog);
    expect(onClose).not.toHaveBeenCalled();
    fireEvent.keyDown(window, { key: "Escape" });
    fireEvent.mouseDown(scrim!);
    expect(onClose).toHaveBeenCalledTimes(2);
  });
});
