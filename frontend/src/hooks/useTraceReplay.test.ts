import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { TraceEvent } from "../types";
import { useTraceReplay } from "./useTraceReplay";

function event(sequenceIndex: number): TraceEvent {
  return {
    id: `event:${sequenceIndex}`,
    sequence_index: sequenceIndex,
    timestamp: `2026-07-21T00:00:0${sequenceIndex}Z`,
    event_type: sequenceIndex === 0 ? "request_sent" : "response_received",
    warnings: [],
  };
}

describe("useTraceReplay", () => {
  afterEach(() => vi.useRealTimers());

  it("uses backend sequence_index and stops at the last event", () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useTraceReplay("scope:a"));
    act(() => result.current.replaceEvents([event(1), event(0)]));

    expect(result.current.events.map((item) => item.sequence_index)).toEqual([0, 1]);
    act(() => result.current.play());
    expect(result.current.isPlaying).toBe(true);

    act(() => vi.advanceTimersByTime(1_100));
    expect(result.current.activeIndex).toBe(1);
    expect(result.current.isPlaying).toBe(false);
  });

  it("supports previous, next, reset, and clears playback position on scope change", () => {
    const { result, rerender } = renderHook(
      ({ scopeKey }) => useTraceReplay(scopeKey),
      { initialProps: { scopeKey: "project:a|build:a" } },
    );
    act(() => result.current.replaceEvents([event(0), event(1)]));

    act(() => result.current.next());
    expect(result.current.activeIndex).toBe(1);
    act(() => result.current.previous());
    expect(result.current.activeIndex).toBe(0);
    act(() => result.current.next());
    act(() => result.current.reset());
    expect(result.current.activeIndex).toBe(0);
    expect(result.current.isPlaying).toBe(false);

    act(() => result.current.next());
    rerender({ scopeKey: "project:a|build:b" });
    expect(result.current.activeIndex).toBe(0);
    expect(result.current.isPlaying).toBe(false);
    expect(result.current.events).toEqual([]);
  });
});
