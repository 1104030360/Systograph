import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useViewerStore } from "../store/viewerStore";
import { graphViewModelSchema } from "../types";
import { ReadinessPanel } from "./ReadinessPanel";

const graph = graphViewModelSchema.parse({
  nodes: [],
  edges: [],
  details: {
    evidence_by_id: { "evidence:prompt-context": { title: "Prompt context assembly" } },
    risk_hints_by_id: {},
    profile_findings_by_id: {},
    capability_candidates_by_id: {},
  },
  filters: { available: [], lenses: [] },
});

/* Shape mirrors systograph.core.models.readiness_report.ReadinessReport. */
const report = {
  schema_version: "readiness-report/v1",
  source_schema_version: "ai-system-map/v2",
  scan_id: "scan:sample",
  build_id: "build:sample",
  environment_id: "environment:default-static",
  generated_from_build_id: "build:sample",
  mapping_completeness: {
    numerator: 4,
    denominator: 52,
    value: 0.076923,
    weights: { detected: 1, partial: 0.5, undetermined: 0, not_detected: 1, conflicted: 0 },
  },
  grounding: {
    applicability: "undetermined",
    status: "undetermined",
    dimensions: [],
    evidence_ids: [],
    reason: "Scanner coverage is insufficient to prove absence.",
  },
  capability_summaries: [],
  findings: [
    {
      finding_id: "readiness:profile:rag-grounding",
      category: "capability_readiness",
      status: "undetermined",
      title: "Capability readiness: rag-grounding",
      reason: "Scanner coverage is insufficient to prove absence.",
      evidence_ids: ["evidence:prompt-context"],
      recommended_next_checks: ["Review the missing deterministic capability signals."],
    },
  ],
  recommended_next_checks: ["Run a detail scan on the retrieval components."],
  limitations: ["Static analysis does not prove runtime behavior."],
  primary_map_type: "agentic_ai_system",
};

beforeEach(() => {
  useViewerStore.setState({
    dataSourceMode: "api",
    apiBaseUrl: "http://127.0.0.1:8000",
    activeBuildId: null,
  });
});

afterEach(async () => {
  /* The download service releases its object URL on the next macrotask. */
  await new Promise((resolve) => setTimeout(resolve, 0));
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  Reflect.deleteProperty(URL, "createObjectURL");
  Reflect.deleteProperty(URL, "revokeObjectURL");
});

describe("ReadinessPanel", () => {
  it("renders backend grounding summary, five-state chips, and next checks", () => {
    render(<ReadinessPanel report={report} graph={graph} buildId={null} onClose={() => {}} />);

    expect(screen.getByRole("dialog", { name: "Readiness" })).toBeInTheDocument();
    expect(screen.getAllByText("Undetermined").length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: "Grounding" })).toBeInTheDocument();
    expect(screen.getByText("Capability readiness: rag-grounding")).toBeInTheDocument();
    expect(screen.getByText("Review the missing deterministic capability signals.")).toBeInTheDocument();
    expect(screen.getByText("Run a detail scan on the retrieval components.")).toBeInTheDocument();
    expect(screen.getByText("Prompt context assembly")).toBeInTheDocument();
    expect(screen.getByText(/Static analysis does not prove runtime behavior/)).toBeInTheDocument();
  });

  it("explains a missing report instead of fabricating findings", () => {
    render(<ReadinessPanel report={null} graph={graph} buildId={null} onClose={() => {}} />);

    expect(screen.getByText(/does not include a readiness report/)).toBeInTheDocument();
    expect(screen.getByText(/UI example only/)).toBeInTheDocument();
    expect(screen.getByText(/not a scan result/)).toBeInTheDocument();
  });

  it("switches to safe plain-text Markdown source", () => {
    render(<ReadinessPanel report={report} graph={graph} buildId={null} onClose={() => {}} />);

    fireEvent.click(screen.getByRole("tab", { name: "Generated Markdown" }));

    expect(screen.getByText(/^# Readiness report/)).toBeInTheDocument();
    expect(screen.getByText(/build:sample/)).toBeInTheDocument();
    expect(screen.getByText(/generated from the inline/)).toBeInTheDocument();
    expect(screen.getByText(/is a separate document/)).toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: /Latest map report/ })).not.toBeInTheDocument();
  });

  it("degrades on an unsupported report contract", () => {
    render(
      <ReadinessPanel
        report={{ schema_version: "readiness-report/v99" }}
        graph={graph}
        buildId={null}
        onClose={() => {}}
      />,
    );

    expect(screen.getByText(/contract this viewer version does not support/)).toBeInTheDocument();
  });

  it("closes with Escape", () => {
    const onClose = vi.fn();
    render(<ReadinessPanel report={report} graph={graph} buildId={null} onClose={onClose} />);

    fireEvent.keyDown(window, { key: "Escape" });

    expect(onClose).toHaveBeenCalledOnce();
  });
});

function stubBrowserSave() {
  URL.createObjectURL = vi.fn(() => "blob:systograph/ai-system-map");
  URL.revokeObjectURL = vi.fn();
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
}

function stubFetch(response: Response) {
  const fetchMock = vi.fn().mockResolvedValue(response);
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function markdownResponse() {
  return new Response("# AI System Map\n", {
    status: 200,
    headers: { "Content-Type": "text/markdown; charset=utf-8" },
  });
}

function notFoundResponse(detail: string) {
  return new Response(JSON.stringify({ detail }), {
    status: 404,
    headers: { "Content-Type": "application/json" },
  });
}

const downloadButton = { name: /Download report/ };

describe("ReadinessPanel build report download", () => {
  beforeEach(() => {
    stubBrowserSave();
  });

  it("keeps the download control outside the document-view tablist", () => {
    render(
      <ReadinessPanel report={report} graph={graph} buildId="build:latest" onClose={() => {}} />,
    );

    const tablist = screen.getByRole("tablist", { name: "Readiness document view" });
    expect(within(tablist).queryByRole("button", downloadButton)).not.toBeInTheDocument();
    expect(screen.getByRole("button", downloadButton)).toBeInTheDocument();
  });

  it("downloads the build the viewer is following", async () => {
    const fetchMock = stubFetch(markdownResponse());
    render(
      <ReadinessPanel report={report} graph={graph} buildId="build:latest" onClose={() => {}} />,
    );

    fireEvent.click(screen.getByRole("button", downloadButton));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledOnce());
    expect(String(fetchMock.mock.calls[0][0])).toBe(
      "http://127.0.0.1:8000/api/map-builds/build%3Alatest/artifacts/ai_system_map.md",
    );
    expect(await screen.findByText(/Saved ai_system_map\.md/)).toBeInTheDocument();
  });

  it("downloads the pinned historical build rather than the envelope build", async () => {
    useViewerStore.setState({ activeBuildId: "build:a" });
    const fetchMock = stubFetch(markdownResponse());
    render(
      <ReadinessPanel report={report} graph={graph} buildId="build:latest" onClose={() => {}} />,
    );

    fireEvent.click(screen.getByRole("button", downloadButton));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledOnce());
    expect(String(fetchMock.mock.calls[0][0])).toContain(
      "/api/map-builds/build%3Aa/artifacts/ai_system_map.md",
    );
  });

  it("settles when the selected build did not publish a report", async () => {
    stubFetch(notFoundResponse("artifact_not_available"));
    render(
      <ReadinessPanel report={report} graph={graph} buildId="build:latest" onClose={() => {}} />,
    );

    fireEvent.click(screen.getByRole("button", downloadButton));

    expect(await screen.findByText(/did not publish a Markdown report/)).toBeInTheDocument();
    expect(screen.queryByText(/artifact_not_available/)).not.toBeInTheDocument();
    expect(screen.getByRole("button", downloadButton)).toBeDisabled();
  });

  it("settles when the selected build has vanished", async () => {
    stubFetch(notFoundResponse("build_not_found"));
    render(
      <ReadinessPanel report={report} graph={graph} buildId="build:latest" onClose={() => {}} />,
    );

    fireEvent.click(screen.getByRole("button", downloadButton));

    expect(await screen.findByText(/no longer exists.*build history/i)).toBeInTheDocument();
    expect(screen.queryByText(/build_not_found/)).not.toBeInTheDocument();
    expect(screen.getByRole("button", downloadButton)).toBeDisabled();
  });

  it("settles when the artifact path no longer matches the backend contract", async () => {
    stubFetch(notFoundResponse("artifact_not_found"));
    render(
      <ReadinessPanel report={report} graph={graph} buildId="build:latest" onClose={() => {}} />,
    );

    fireEvent.click(screen.getByRole("button", downloadButton));

    expect(
      await screen.findByText(/report artifact is not available at the expected path/i),
    ).toBeInTheDocument();
    expect(screen.queryByText(/artifact_not_found/)).not.toBeInTheDocument();
    expect(screen.getByRole("button", downloadButton)).toBeDisabled();
  });

  it("offers retry after an unknown failure without showing raw error text", async () => {
    const fetchMock = vi
      .fn()
      .mockRejectedValueOnce(new TypeError("private network details"))
      .mockResolvedValueOnce(markdownResponse());
    vi.stubGlobal("fetch", fetchMock);
    render(
      <ReadinessPanel report={report} graph={graph} buildId="build:latest" onClose={() => {}} />,
    );

    fireEvent.click(screen.getByRole("button", downloadButton));

    expect(await screen.findByText(/Could not download the report/)).toBeInTheDocument();
    expect(screen.queryByText(/private network details/)).not.toBeInTheDocument();
    const retry = screen.getByRole("button", downloadButton);
    expect(retry).toBeEnabled();
    fireEvent.click(retry);

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(await screen.findByText(/Saved ai_system_map\.md/)).toBeInTheDocument();
  });

  it("resets a settled failure when the active build changes", async () => {
    stubFetch(notFoundResponse("artifact_not_available"));
    render(
      <ReadinessPanel report={report} graph={graph} buildId="build:latest" onClose={() => {}} />,
    );

    fireEvent.click(screen.getByRole("button", downloadButton));
    expect(await screen.findByText(/did not publish a Markdown report/)).toBeInTheDocument();
    expect(screen.getByRole("button", downloadButton)).toBeDisabled();

    act(() => useViewerStore.setState({ activeBuildId: "build:b2" }));

    expect(screen.getByRole("button", downloadButton)).toBeEnabled();
    expect(screen.queryByText(/did not publish a Markdown report/)).not.toBeInTheDocument();
  });

  it("hides the control in Sample mode and when no build id exists", () => {
    useViewerStore.setState({ dataSourceMode: "sample" });
    const { unmount } = render(
      <ReadinessPanel report={report} graph={graph} buildId="build:latest" onClose={() => {}} />,
    );
    expect(screen.queryByRole("button", downloadButton)).not.toBeInTheDocument();
    unmount();

    useViewerStore.setState({ dataSourceMode: "api", activeBuildId: null });
    render(<ReadinessPanel report={report} graph={graph} buildId={null} onClose={() => {}} />);
    expect(screen.queryByRole("button", downloadButton)).not.toBeInTheDocument();
  });
});
