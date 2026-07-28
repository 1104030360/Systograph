import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import preflightResponseSample from "../../../docs/work/Timmy/design/EPIC1/frontend-json-handoff/step-02-boundary-gate/frontend-inventory-preflight-response-sample.json";
import { scanInventoryPreflightResponseSchema, type ScanInventoryPreflightResponse } from "../types";
import { BoundaryDecisionModal } from "./BoundaryDecisionModal";

const samplePreflight = scanInventoryPreflightResponseSchema.parse(preflightResponseSample);

function emptyPreflight(): ScanInventoryPreflightResponse {
  return {
    ...samplePreflight,
    summary: {
      default_included_file_count: 0,
      required_review_count: 0,
      reviewable_excluded_count: 0,
      hard_blocked_count: 0,
      missing_count: 0,
      collapsed_directory_count: 0,
    },
    required_boundary_proposals: [],
    reviewable_excluded_page: { items: [], next_cursor: null, total: 0 },
    requested_target_results: [],
    blocked_summaries: [],
    warnings: [],
  };
}

function renderModal(overrides: Partial<React.ComponentProps<typeof BoundaryDecisionModal>> = {}) {
  const props: React.ComponentProps<typeof BoundaryDecisionModal> = {
    status: "reviewing",
    preflight: samplePreflight,
    decisions: {},
    missingRequiredCount: 2,
    error: null,
    notice: null,
    isBusy: false,
    onDecisionChange: vi.fn(),
    onCheckPath: vi.fn(),
    onLoadMore: vi.fn(),
    onRetryPreflight: vi.fn(),
    onSubmit: vi.fn(),
    onCancel: vi.fn(),
    ...overrides,
  };
  return { ...render(<BoundaryDecisionModal {...props} />), props };
}

describe("BoundaryDecisionModal Inventory Preflight UI", () => {
  it("renders backend summary, risk/policy explanation, defaults, and one-run safety copy", () => {
    renderModal();

    expect(screen.getByRole("dialog", { name: "Review scan scope" })).toHaveAttribute("aria-modal", "true");
    expect(screen.getByText(/Adjustments apply only to this scan/)).toBeInTheDocument();
    expect(screen.getByText(".gitignore", { selector: "code" })).toBeInTheDocument();
    expect(screen.getByText("143")).toBeInTheDocument();
    expect(screen.getByText("Potential secret-bearing configuration file requires a one-run decision.")).toBeInTheDocument();
    expect(screen.getAllByText("source: project_ignore")).toHaveLength(2);
    expect(screen.getByText("policy: dependency-directory-default-skip")).toBeInTheDocument();
    expect(screen.getByText("23", { selector: "dd" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Scan all selectable files" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Skip all selectable files" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Confirm and start scan" })).toBeDisabled();
  });

  it("shows optional backend default state without serializing a fake user decision", () => {
    renderModal();
    const ignoredGroup = screen.getByRole("group", {
      name: "One-run decision for ignored/custom-loader.py",
    });
    expect(within(ignoredGroup).getByRole("button", { name: "Skip this run" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("supports exact path checks, opaque pagination, and non-actionable missing results", () => {
    const onCheckPath = vi.fn();
    const onLoadMore = vi.fn();
    renderModal({ onCheckPath, onLoadMore });

    const pathInput = screen.getByPlaceholderText("src/experimental.py or packages/local-tool");
    fireEvent.change(pathInput, { target: { value: "packages/local-tool" } });
    fireEvent.submit(pathInput.closest("form")!);
    expect(onCheckPath).toHaveBeenCalledWith("packages/local-tool");

    fireEvent.click(screen.getByRole("button", { name: "Load more excluded candidates" }));
    expect(onLoadMore).toHaveBeenCalledOnce();
    expect(screen.getByText("missing.env")).toBeInTheDocument();
    expect(screen.queryByRole("group", { name: /missing\.env/ })).not.toBeInTheDocument();
  });

  it("renders an honest no-decision-needed state and allows an empty confirmation", () => {
    renderModal({
      preflight: emptyPreflight(),
      missingRequiredCount: 0,
    });

    expect(screen.getByText("No backend candidate requires a mandatory one-run decision.")).toBeInTheDocument();
    expect(screen.getByText("0 one-run decisions will be sent.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Confirm and start scan" })).toBeEnabled();
  });

  it("hides all review controls for unavailable/invalid baseline errors", () => {
    renderModal({
      status: "baseline_error",
      preflight: null,
      error: {
        kind: "baseline",
        code: "inventory_rules_invalid",
        message: "The default scan inventory policy is invalid.",
        retryable: false,
      },
      missingRequiredCount: 0,
    });

    expect(screen.getByText("The backend inventory policy did not pass its safety gate")).toBeInTheDocument();
    expect(screen.getByText(/cannot bypass this backend gate/)).toBeInTheDocument();
    expect(screen.queryByPlaceholderText("src/experimental.py or packages/local-tool")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Scan this run/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Retry preflight/ })).not.toBeInTheDocument();
  });

  it("makes stale recovery explicit and never presents old decisions", () => {
    const onRetryPreflight = vi.fn();
    renderModal({
      status: "stale",
      error: {
        kind: "stale",
        code: "inventory_preflight_stale",
        message: "Scan selection changed. Refresh the file review.",
        retryable: true,
      },
      onRetryPreflight,
    });

    expect(screen.getByText(/Previous decisions were cleared/)).toBeInTheDocument();
    expect(screen.queryByRole("group", { name: /One-run decision/ })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Reload preflight" }));
    expect(onRetryPreflight).toHaveBeenCalledOnce();
  });

  it("does not render masked values or raw content even if a malformed fixture includes them", () => {
    const unsafe = structuredClone(samplePreflight);
    unsafe.required_boundary_proposals[0].evidence_packet.masked_evidence_values = ["SECRET=raw-value"];
    unsafe.required_boundary_proposals[0].evidence_packet.masked_snippets = ["private file contents"];
    renderModal({ preflight: unsafe });

    expect(screen.queryByText(/SECRET=raw-value/)).not.toBeInTheDocument();
    expect(screen.queryByText(/private file contents/)).not.toBeInTheDocument();
  });

  it("moves focus into the dialog, traps Tab, restores focus, and closes on Escape", () => {
    const trigger = document.createElement("button");
    trigger.textContent = "Start scan";
    document.body.appendChild(trigger);
    trigger.focus();
    const onCancel = vi.fn();
    const { unmount } = renderModal({
      preflight: emptyPreflight(),
      missingRequiredCount: 0,
      onCancel,
    });

    expect(screen.getByRole("heading", { name: "Review scan scope" })).toHaveFocus();
    const continueButton = screen.getByRole("button", { name: "Confirm and start scan" });
    continueButton.focus();
    fireEvent.keyDown(window, { key: "Tab" });
    expect(screen.getByRole("button", { name: "Close inventory preflight" })).toHaveFocus();

    fireEvent.keyDown(window, { key: "Escape" });
    expect(onCancel).toHaveBeenCalledOnce();
    unmount();
    expect(trigger).toHaveFocus();
    trigger.remove();
  });
});
