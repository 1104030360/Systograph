import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { StateOverlay } from "./StateOverlay";

describe("StateOverlay", () => {
  it("shows a neutral project-selection state without a misleading retry", () => {
    const onRetry = vi.fn();
    const onUseSample = vi.fn();

    render(
      <StateOverlay
        kind="empty"
        apiBaseUrl="http://127.0.0.1:8000"
        onRetry={onRetry}
        onUseSample={onUseSample}
      />,
    );

    expect(screen.getByRole("heading", { name: "No project selected" })).toBeInTheDocument();
    expect(screen.getByText(/Import a project to load a map/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /retry|check again/i })).not.toBeInTheDocument();
    expect(screen.queryByText(/\/api\/map/)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Inspect legacy sample" }));
    expect(onUseSample).toHaveBeenCalledOnce();
    expect(onRetry).not.toHaveBeenCalled();
  });

  it("does not advertise a retired endpoint while loading or after an error", () => {
    const props = {
      apiBaseUrl: "http://127.0.0.1:8000",
      onRetry: vi.fn(),
      onUseSample: vi.fn(),
    };
    const { rerender } = render(<StateOverlay kind="loading" {...props} />);

    expect(screen.queryByText(/\/api\/map/)).not.toBeInTheDocument();

    rerender(<StateOverlay kind="error" {...props} />);
    expect(screen.getByText("Request to http://127.0.0.1:8000 failed")).toBeInTheDocument();
    expect(screen.queryByText(/\/api\/map/)).not.toBeInTheDocument();
  });
});
