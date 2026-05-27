import { Activity, Pause, Play } from "lucide-react";
import type { ScanTarget } from "../types";

type Props = {
  targets: ScanTarget[];
  activeIndex: number;
  isRunning: boolean;
  onRunningChange: (running: boolean) => void;
};

export function ProgressStrip({ targets, activeIndex, isRunning, onRunningChange }: Props) {
  const active = targets[activeIndex];
  const percent = targets.length > 0 ? Math.round(((activeIndex + 1) / targets.length) * 100) : 0;

  return (
    <div className="progress-strip">
      <div className="progress-title">
        <Activity size={16} />
        <div>
          <span className="section-label">Scan Progress</span>
          <strong>{active?.label ?? "Waiting"}</strong>
        </div>
      </div>
      <div className="progress-meter" aria-label="scan progress">
        <span style={{ width: `${percent}%` }} />
      </div>
      <button className="icon-button primary" type="button" onClick={() => onRunningChange(!isRunning)} title={isRunning ? "Pause mock progress" : "Play mock progress"}>
        {isRunning ? <Pause size={15} /> : <Play size={15} />}
      </button>
    </div>
  );
}
