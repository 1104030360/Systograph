import { Activity, Pause, Play } from "lucide-react";
import type { DataSourceMode, ScanProgressEvent, ScanTarget } from "../types";

type Props = {
  targets: ScanTarget[];
  activeIndex: number;
  isRunning: boolean;
  mode: DataSourceMode;
  liveEvent: ScanProgressEvent | null;
  onRunningChange: (running: boolean) => void;
};

export function ProgressStrip({ targets, activeIndex, isRunning, mode, liveEvent, onRunningChange }: Props) {
  const active = targets[activeIndex];
  const percent = liveEvent?.percent ?? (targets.length > 0 ? Math.round(((activeIndex + 1) / targets.length) * 100) : 0);
  const label = liveEvent?.message ?? active?.label ?? "Waiting";
  const status = liveEvent?.stage ?? liveEvent?.event ?? liveEvent?.type ?? (mode === "api" ? "SSE ready" : "mock progress");

  return (
    <div className="progress-strip">
      <div className="progress-title">
        <Activity size={16} />
        <div>
          <span className="section-label">Scan Progress · {status}</span>
          <strong>{label}</strong>
        </div>
      </div>
      <div className="progress-meter" aria-label="scan progress">
        <span style={{ width: `${percent}%` }} />
      </div>
      <button
        className="icon-button primary"
        type="button"
        aria-pressed={isRunning}
        aria-label={isRunning ? "Pause progress" : "Play progress"}
        onClick={() => onRunningChange(!isRunning)}
        title={isRunning ? "Pause progress" : "Play progress"}
      >
        {isRunning ? <Pause size={15} /> : <Play size={15} />}
      </button>
    </div>
  );
}
