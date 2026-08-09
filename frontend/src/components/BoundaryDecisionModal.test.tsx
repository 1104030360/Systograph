import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import preflightResponseSample from "../../../docs/work/Timmy/design/EPIC1/frontend-json-handoff/step-02-boundary-gate/frontend-inventory-preflight-response-sample.json";
import { proposalIdentity } from "../hooks/useProjectScanFlow";
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
    requestedPaths: [],
    missingRequiredCount: 2,
    error: null,
    notice: null,
    isBusy: false,
    onDecisionChange: vi.fn(),
    onCheckPath: vi.fn(),
    onRemoveRequestedPath: vi.fn(),
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

  it("keeps Shift+Tab inside the dialog when focus sits on the tabindex=-1 title", () => {
    const trigger = document.createElement("button");
    document.body.appendChild(trigger);
    trigger.focus();
    renderModal({ preflight: emptyPreflight(), missingRequiredCount: 0 });

    // The title holds initial focus but is not itself tabbable, so the trap has
    // to take over instead of letting the browser step out of the dialog.
    expect(screen.getByRole("heading", { name: "Review scan scope" })).toHaveFocus();
    fireEvent.keyDown(window, { key: "Tab", shiftKey: true });
    expect(screen.getByRole("button", { name: "Confirm and start scan" })).toHaveFocus();
    trigger.remove();
  });

  it("does not steal focus back to the title when only the flow status changes", () => {
    const { rerender, props } = renderModal({ preflight: emptyPreflight(), missingRequiredCount: 0 });

    const pathInput = screen.getByPlaceholderText("src/experimental.py or packages/local-tool");
    pathInput.focus();
    rerender(<BoundaryDecisionModal {...props} preflight={emptyPreflight()} status="submitting" />);

    expect(pathInput).toHaveFocus();
  });

  it("blocks the scan and explains why when decisions conflict", () => {
    // Two proposals for the same path+scope with different fingerprints: only
    // reachable through a superseded page, and it must never be submitted.
    const conflicting = structuredClone(samplePreflight);
    const [first] = conflicting.required_boundary_proposals;
    const second = structuredClone(first);
    second.proposal_id = "proposal:required-env-sample-stale";
    second.target.fingerprint = "sha256:metadata-env-sample-stale";
    conflicting.reviewable_excluded_page.items = [second];

    renderModal({
      preflight: conflicting,
      missingRequiredCount: 0,
      decisions: {
        [proposalIdentity(first)]: "scan_this_run",
        [proposalIdentity(second)]: "skip_this_run",
      },
    });

    expect(screen.getByText(/has conflicting one-run decisions/)).toBeInTheDocument();
    expect(screen.getByText("Conflicting decisions block this scan")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Confirm and start scan" })).toBeDisabled();
  });

  it("lists requested paths with a remove control so a rejected path is recoverable", () => {
    const onRemoveRequestedPath = vi.fn();
    renderModal({ requestedPaths: ["src/experimental.py"], onRemoveRequestedPath });

    fireEvent.click(
      screen.getByRole("button", { name: "Remove src/experimental.py from this preflight" }),
    );
    expect(onRemoveRequestedPath).toHaveBeenCalledWith("src/experimental.py");
  });

  it("uses fail-closed copy for an over-limit directory and never offers a partial scan", () => {
    const overLimit = structuredClone(samplePreflight);
    overLimit.requested_target_results = [
      {
        target_path: "node_modules",
        target_kind: "directory",
        status: "directory_limit_exceeded",
        proposal: null,
        reason_code: "inventory_selection_directory_limit_exceeded",
        limit_context: { limit_kind: "files", limit: 5000, observed_at_least: 5001 },
      },
    ];
    renderModal({ preflight: overLimit, missingRequiredCount: 1 });

    expect(
      screen.getByText("Too large to select as one folder; choose a smaller folder."),
    ).toBeInTheDocument();
    expect(screen.getByText(/observed at least 5,001 for the files limit of 5,000/)).toBeInTheDocument();
    expect(screen.queryByText(/first 5,?000|partial|Continue anyway/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("group", { name: /node_modules/ })).not.toBeInTheDocument();
  });

  it("explains non-reviewable results without leaking backend codes as the headline", () => {
    renderModal();

    expect(screen.getByText("Not found in the project.")).toBeInTheDocument();
    expect(screen.getByText("Backend reason: inventory_selection_target_missing")).toBeInTheDocument();
  });
});
