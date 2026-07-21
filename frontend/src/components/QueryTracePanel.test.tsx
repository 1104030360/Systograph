import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { GraphViewModel, TraceEvent } from "../types";
import { QueryTracePanel } from "./QueryTracePanel";

const endpoints: GraphViewModel["endpoints"] = [
  {
    endpoint_id: "endpoint:chat",
    value: "https://example.test/chat",
    endpoint_type: "external",
    method: "POST",
    component_id: "component:chat",
  },
];

function traceEvent(sequenceIndex: number, eventType: string, error?: unknown): TraceEvent {
  return {
    id: `trace:1:event:${sequenceIndex}`,
    trace_id: "trace:1",
    sequence_index: sequenceIndex,
    timestamp: `2026-07-21T00:00:0${sequenceIndex}Z`,
    event_type: eventType,
    replay_depth: null,
    status: error ? "partial" : "sent",
    endpoint_id: "endpoint:chat",
    component_id: "component:chat",
    warnings: [],
    input: null,
    output: null,
    latency_ms: null,
    latency: null,
    retrieved_chunks: null,
    error,
  };
}

function partialResponse() {
  return {
    trace_id: "trace:1",
    status: "partial",
    query_sent: true,
    endpoint_id: "endpoint:chat",
    source_scan_id: "scan:1",
    source_build_id: "build:1",
    events: [
      traceEvent(1, "error", { type: "timeout", message: "Timeout after 30s" }),
      traceEvent(0, "request_sent"),
    ],
    warnings: [],
    error_reason: "timeout",
  };
}

function response(payload: unknown): Response {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

const replayProps = {
  activeIndex: 0,
  isPlaying: false,
  onIndexChange: vi.fn(),
  onPlay: vi.fn(),
  onPause: vi.fn(),
  onPrevious: vi.fn(),
  onNext: vi.fn(),
  onReset: vi.fn(),
};

function Harness() {
  const [events, setEvents] = useState<TraceEvent[]>([]);
  return (
    <QueryTracePanel
      mode="api"
      apiBaseUrl="http://127.0.0.1:8000"
      projectId="project:1"
      buildId="build:1"
      endpoints={endpoints}
      events={events}
      onTraceEvents={setEvents}
      {...replayProps}
    />
  );
}

describe("QueryTracePanel", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("is opt-in and binds the runtime request to the selected project and build", async () => {
    const fetchMock = vi.fn().mockResolvedValue(response(partialResponse()));
    vi.stubGlobal("fetch", fetchMock);
    const onTraceEvents = vi.fn();

    render(
      <QueryTracePanel
        mode="api"
        apiBaseUrl="http://127.0.0.1:8000"
        projectId="project:1"
        buildId="build:1"
        endpoints={endpoints}
        events={[]}
        onTraceEvents={onTraceEvents}
        {...replayProps}
      />,
    );

    expect(fetchMock).not.toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText("Query"), { target: { value: "masked health question" } });
    fireEvent.click(screen.getByRole("button", { name: "Run" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledOnce());
    const [, init] = fetchMock.mock.calls[0];
    expect(JSON.parse(String(init.body))).toEqual({
      project_id: "project:1",
      build_id: "build:1",
      endpoint_id: "endpoint:chat",
      query: "masked health question",
      timeout_seconds: 30,
    });
    await waitFor(() => expect(onTraceEvents).toHaveBeenCalled());
    expect(onTraceEvents.mock.calls[0][0].map((event: TraceEvent) => event.sequence_index)).toEqual([0, 1]);
  });

  it("preserves request and error events from a partial timeout result", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(partialResponse())));
    const { container } = render(<Harness />);

    fireEvent.change(screen.getByLabelText("Query"), { target: { value: "trace once" } });
    fireEvent.click(screen.getByRole("button", { name: "Run" }));

    await waitFor(() => expect(container.querySelectorAll(".tl-step")).toHaveLength(2));
    expect(screen.getByText(/partial; query_sent: true; timeout/)).toBeInTheDocument();
    expect(screen.getByText("Request Sent")).toBeInTheDocument();
    expect(screen.getByText("Error")).toBeInTheDocument();
  });

  it("keeps the previous replay when an explicit retry fails", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response(partialResponse()))
      .mockRejectedValueOnce(new Error("network offline"));
    vi.stubGlobal("fetch", fetchMock);
    const { container } = render(<Harness />);

    fireEvent.change(screen.getByLabelText("Query"), { target: { value: "trace once" } });
    fireEvent.click(screen.getByRole("button", { name: "Run" }));
    await waitFor(() => expect(container.querySelectorAll(".tl-step")).toHaveLength(2));

    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    await waitFor(() => expect(screen.getByText("network offline")).toBeInTheDocument());
    expect(container.querySelectorAll(".tl-step")).toHaveLength(2);
  });

  it("does not replace replay events when backend source_build_id is not the selected build", async () => {
    const mismatched = { ...partialResponse(), source_build_id: "build:other" };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(mismatched)));
    const onTraceEvents = vi.fn();

    render(
      <QueryTracePanel
        mode="api"
        apiBaseUrl="http://127.0.0.1:8000"
        projectId="project:1"
        buildId="build:1"
        endpoints={endpoints}
        events={[]}
        onTraceEvents={onTraceEvents}
        {...replayProps}
      />,
    );
    fireEvent.change(screen.getByLabelText("Query"), { target: { value: "trace once" } });
    fireEvent.click(screen.getByRole("button", { name: "Run" }));

    expect(await screen.findByText(/did not bind this result to the selected build/)).toBeInTheDocument();
    expect(onTraceEvents).not.toHaveBeenCalled();
    expect(screen.queryByText(/partial; query_sent/)).not.toBeInTheDocument();
  });

  it("shows loading and bounded client-timeout states without inventing replay events", async () => {
    vi.useFakeTimers();
    vi.stubGlobal("fetch", vi.fn((_input: RequestInfo | URL, init?: RequestInit) =>
      new Promise<Response>((_resolve, reject) => {
        init?.signal?.addEventListener(
          "abort",
          () => reject(new DOMException("The operation was aborted.", "AbortError")),
          { once: true },
        );
      }),
    ));

    render(<Harness />);
    fireEvent.change(screen.getByLabelText("Query"), { target: { value: "trace once" } });
    fireEvent.change(screen.getByLabelText("Timeout (seconds)"), { target: { value: "1" } });
    fireEvent.click(screen.getByRole("button", { name: "Run" }));
    expect(screen.getByRole("button", { name: "Running…" })).toBeDisabled();

    await act(async () => vi.advanceTimersByTimeAsync(11_000));
    expect(screen.getByText(/Client request timed out/)).toBeInTheDocument();
    expect(screen.getByText("No replay events in this payload.")).toBeInTheDocument();
  });

  it("never renders masked payload fields or raw query results in the replay UI", () => {
    const privateEvent = {
      ...traceEvent(0, "response_received"),
      output: { answer: "raw private answer" },
      retrieved_chunks: ["raw private chunk"],
    };
    render(
      <QueryTracePanel
        mode="api"
        apiBaseUrl="http://127.0.0.1:8000"
        projectId="project:1"
        buildId="build:1"
        endpoints={endpoints}
        events={[privateEvent]}
        onTraceEvents={vi.fn()}
        {...replayProps}
      />,
    );

    expect(screen.queryByText("raw private answer")).not.toBeInTheDocument();
    expect(screen.queryByText("raw private chunk")).not.toBeInTheDocument();
  });
});
