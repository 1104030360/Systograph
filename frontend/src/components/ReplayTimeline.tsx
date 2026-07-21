import { AlertTriangle, Pause, Play, RotateCcw, SkipBack, SkipForward } from "lucide-react";
import type { TraceEvent } from "../types";
import { compactId, titleCase } from "../utils/format";
import { traceErrorLabel, traceEventHasFailure } from "../utils/trace";

type Props = {
  events: TraceEvent[];
  activeIndex: number;
  isPlaying: boolean;
  fallbackMessage?: string | null;
  onIndexChange: (index: number) => void;
  onPlay: () => void;
  onPause: () => void;
  onPrevious: () => void;
  onNext: () => void;
  onReset: () => void;
};

export function ReplayTimeline({
  events,
  activeIndex,
  isPlaying,
  fallbackMessage,
  onIndexChange,
  onPlay,
  onPause,
  onPrevious,
  onNext,
  onReset,
}: Props) {
  const active = events[activeIndex];
  const maxIndex = Math.max(events.length - 1, 0);
  const activeFailed = traceEventHasFailure(active);

  return (
    <footer className="replay">
      <div className="replay-head">
        <div className="r-title">
          <strong>Query replay</strong>
        </div>
        <div className="r-ctrls">
          <button
            className="icon-btn"
            type="button"
            aria-label="Reset replay"
            title="Reset replay"
            disabled={events.length === 0 || activeIndex === 0}
            onClick={onReset}
          >
            <RotateCcw size={14} />
          </button>
          <button
            className="icon-btn"
            type="button"
            aria-label="Previous step"
            title="Previous step"
            disabled={events.length === 0 || activeIndex === 0}
            onClick={onPrevious}
          >
            <SkipBack size={14} />
          </button>
          <button
            className="icon-btn primary"
            type="button"
            aria-pressed={isPlaying}
            aria-label={isPlaying ? "Pause replay" : "Play replay"}
            title={isPlaying ? "Pause" : "Play"}
            disabled={events.length === 0}
            onClick={isPlaying ? onPause : onPlay}
          >
            {isPlaying ? <Pause size={14} /> : <Play size={14} />}
          </button>
          <button
            className="icon-btn"
            type="button"
            aria-label="Next step"
            title="Next step"
            disabled={events.length === 0 || activeIndex === maxIndex}
            onClick={onNext}
          >
            <SkipForward size={14} />
          </button>
        </div>
        <div className="r-meta">
          {active ? (
            <span className="chip">
              step {activeIndex + 1}/{events.length}
            </span>
          ) : null}
          {active?.latency_ms != null ? <span className="chip">{active.latency_ms} ms</span> : null}
          <span className={activeFailed ? "has-error" : "ok"}>
            {activeFailed ? traceErrorLabel(active?.error) : (active?.status ?? "ready")}
          </span>
        </div>
      </div>

      {fallbackMessage ? <div className="replay-fallback" role="status">{fallbackMessage}</div> : null}

      {events.length === 0 ? (
        <div className="replay-empty">No replay events in this payload.</div>
      ) : (
        <div className="timeline">
          {events.map((event, index) => {
            const failed = traceEventHasFailure(event);
            return (
            <button
              key={event.id}
              className={[
                "tl-step",
                index === activeIndex ? "is-active" : "",
                failed ? "has-error" : "",
              ]
                .filter(Boolean)
                .join(" ")}
              type="button"
              onClick={() => onIndexChange(index)}
            >
              <span className="tl-idx">{index + 1}</span>
              <span className="tl-body">
                <span className="tl-slot">
                  {failed ? <AlertTriangle size={12} aria-hidden="true" /> : null}
                  {titleCase(event.slot ?? event.step_type ?? event.event_type ?? "step")}
                </span>
                <span className="tl-sub">
                  {compactId(event.component_id ?? event.edge_id ?? event.endpoint_id ?? event.event_type ?? "")}
                </span>
              </span>
            </button>
            );
          })}
        </div>
      )}
    </footer>
  );
}
