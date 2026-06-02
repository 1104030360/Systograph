import { Pause, Play, SkipBack, SkipForward } from "lucide-react";
import type { TraceEvent } from "../types";
import { compactId } from "../utils/format";

type Props = {
  events: TraceEvent[];
  activeIndex: number;
  isRunning: boolean;
  onIndexChange: (index: number) => void;
  onRunningChange: (running: boolean) => void;
};

export function ReplayTimeline({ events, activeIndex, isRunning, onIndexChange, onRunningChange }: Props) {
  const active = events[activeIndex];
  const maxIndex = Math.max(events.length - 1, 0);

  return (
    <footer className="replay-panel">
      <div className="replay-toolbar">
        <div>
          <span className="section-label">Query Replay</span>
          <strong>{active?.replay_depth ?? "coarse_replay"}</strong>
        </div>
        <div className="replay-actions">
          <button className="icon-button" type="button" onClick={() => onIndexChange(Math.max(activeIndex - 1, 0))} title="Previous step">
            <SkipBack size={15} />
          </button>
          <button className="icon-button primary" type="button" onClick={() => onRunningChange(!isRunning)} title={isRunning ? "Pause" : "Play"}>
            {isRunning ? <Pause size={15} /> : <Play size={15} />}
          </button>
          <button className="icon-button" type="button" onClick={() => onIndexChange(Math.min(activeIndex + 1, maxIndex))} title="Next step">
            <SkipForward size={15} />
          </button>
        </div>
      </div>

      <div className="timeline-track">
        {events.map((event, index) => (
          <button
            className={[
              "timeline-step",
              index === activeIndex ? "is-active" : "",
              event.error ? "has-error" : "",
            ].join(" ")}
            key={event.id ?? index}
            type="button"
            onClick={() => onIndexChange(index)}
          >
            <span className="step-dot" />
            <span className="step-label">{event.slot ?? event.step_type ?? compactId(event.component_id ?? event.edge_id ?? event.id ?? "step")}</span>
          </button>
        ))}
      </div>

      <div className="replay-status">
        <span>{active ? `Step ${activeIndex + 1} / ${events.length}` : "No replay events"}</span>
        <span>{active?.latency_ms ? `${active.latency_ms} ms` : "sample trace"}</span>
        <span>{active?.error?.code ?? "ok"}</span>
      </div>
    </footer>
  );
}
