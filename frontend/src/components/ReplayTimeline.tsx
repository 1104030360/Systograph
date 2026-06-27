import { Pause, Play, SkipBack, SkipForward } from "lucide-react";
import type { TraceEvent } from "../types";
import { compactId, titleCase } from "../utils/format";

type Props = {
  events: TraceEvent[];
  activeIndex: number;
  isRunning: boolean;
  onIndexChange: (index: number) => void;
  onSelectEvent?: (event: TraceEvent) => void;
  onRunningChange: (running: boolean) => void;
};

export function ReplayTimeline({
  events,
  activeIndex,
  isRunning,
  onIndexChange,
  onSelectEvent,
  onRunningChange,
}: Props) {
  const active = events[activeIndex];
  const maxIndex = Math.max(events.length - 1, 0);

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
            aria-label="Previous step"
            title="Previous step"
            onClick={() => onIndexChange(Math.max(activeIndex - 1, 0))}
          >
            <SkipBack size={14} />
          </button>
          <button
            className="icon-btn primary"
            type="button"
            aria-pressed={isRunning}
            aria-label={isRunning ? "Pause replay" : "Play replay"}
            title={isRunning ? "Pause" : "Play"}
            onClick={() => onRunningChange(!isRunning)}
          >
            {isRunning ? <Pause size={14} /> : <Play size={14} />}
          </button>
          <button
            className="icon-btn"
            type="button"
            aria-label="Next step"
            title="Next step"
            onClick={() => onIndexChange(Math.min(activeIndex + 1, maxIndex))}
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
          <span className={active?.error ? "" : "ok"}>{active?.error ? (active.error.code ?? "error") : "ok"}</span>
        </div>
      </div>

      {events.length === 0 ? (
        <div className="replay-empty">No replay events in this payload.</div>
      ) : (
        <div className="timeline">
          {events.map((event, index) => (
            <button
              key={event.id ?? index}
              className={[
                "tl-step",
                index === activeIndex ? "is-active" : "",
                event.error ? "has-error" : "",
              ]
                .filter(Boolean)
                .join(" ")}
              type="button"
              onClick={() => {
                onIndexChange(index);
                onSelectEvent?.(event);
              }}
            >
              <span className="tl-idx">{index + 1}</span>
              <span className="tl-body">
                <span className="tl-slot">{titleCase(event.slot ?? event.step_type ?? "step")}</span>
                <span className="tl-sub">{compactId(event.component_id ?? event.step_type ?? "")}</span>
              </span>
            </button>
          ))}
        </div>
      )}
    </footer>
  );
}
