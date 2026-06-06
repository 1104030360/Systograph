import { Pause, Play } from "lucide-react";

type Props = {
  isRunning: boolean;
  percent: number;
  message: string;
  stage: string;
  isError: boolean;
  onToggle: () => void;
};

export function ProgressStrip({ isRunning, percent, message, stage, isError, onToggle }: Props) {
  const dotClass = isError ? "dot error" : isRunning ? "dot" : "dot idle";

  return (
    <div className="progress-strip">
      <div className="ps-label">
        <div className="ps-stage">
          <span className={dotClass} />
          scan · {stage}
        </div>
        <div className="ps-msg">{message}</div>
      </div>
      <div className={isError ? "progress-meter is-error" : "progress-meter"} aria-label="scan progress">
        <span style={{ width: `${percent}%` }} />
      </div>
      <div className="progress-pct mono">{percent}%</div>
      <button
        className={isRunning ? "icon-btn primary" : "icon-btn"}
        type="button"
        aria-pressed={isRunning}
        aria-label={isRunning ? "Pause scan" : "Resume scan"}
        title={isRunning ? "Pause scan" : "Resume scan"}
        onClick={onToggle}
      >
        {isRunning ? <Pause size={14} /> : <Play size={14} />}
      </button>
    </div>
  );
}
