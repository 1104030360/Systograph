import { useCallback, useEffect, useMemo, useState } from "react";
import type { TraceEvent } from "../types";
import { sortTraceEvents } from "../utils/trace";

const REPLAY_STEP_MS = 1_100;

export function useTraceReplay(scopeKey: string) {
  const [sourceEvents, setSourceEvents] = useState<TraceEvent[]>([]);
  const events = sourceEvents;
  const sortedEvents = useMemo(() => sortTraceEvents(events), [events]);
  const eventsKey = sortedEvents.map((event) => `${event.sequence_index}:${event.id}`).join("|");
  const [activeIndex, setActiveIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  const reset = useCallback(() => {
    setIsPlaying(false);
    setActiveIndex(0);
  }, []);

  useEffect(() => reset(), [eventsKey, reset]);
  useEffect(() => {
    setSourceEvents([]);
    reset();
  }, [reset, scopeKey]);

  useEffect(() => {
    if (!isPlaying || sortedEvents.length === 0) return;
    const timer = window.setInterval(() => {
      setActiveIndex((current) => {
        const next = Math.min(current + 1, sortedEvents.length - 1);
        if (next === sortedEvents.length - 1) setIsPlaying(false);
        return next;
      });
    }, REPLAY_STEP_MS);
    return () => window.clearInterval(timer);
  }, [isPlaying, sortedEvents.length]);

  const play = useCallback(() => {
    if (sortedEvents.length === 0) return;
    setActiveIndex((current) => (current >= sortedEvents.length - 1 ? 0 : current));
    setIsPlaying(true);
  }, [sortedEvents.length]);

  const pause = useCallback(() => setIsPlaying(false), []);
  const previous = useCallback(() => {
    setIsPlaying(false);
    setActiveIndex((current) => Math.max(0, current - 1));
  }, []);
  const next = useCallback(() => {
    setIsPlaying(false);
    setActiveIndex((current) => Math.max(0, Math.min(sortedEvents.length - 1, current + 1)));
  }, [sortedEvents.length]);
  const select = useCallback((index: number) => {
    setIsPlaying(false);
    setActiveIndex(Math.max(0, Math.min(Math.max(0, sortedEvents.length - 1), index)));
  }, [sortedEvents.length]);
  const replaceEvents = useCallback((nextEvents: TraceEvent[]) => setSourceEvents(nextEvents), []);

  return {
    events: sortedEvents,
    activeIndex,
    activeEvent: sortedEvents[activeIndex],
    isPlaying,
    play,
    pause,
    previous,
    next,
    select,
    reset,
    replaceEvents,
  };
}
