import { useState } from "react";
import { ChevronLeft, ChevronRight, Pause, Play } from "lucide-react";

type Props = {
  isRunning: boolean;
  percent: number;
  message: string;
  stage: string;
  isError: boolean;
  onToggle: () => void;
};

export function ProgressStrip({ isRunning, percent, message, stage, isError, onToggle }: Props) {
  const [isExpanded, setIsExpanded] = useState(false);
  const dotClass = isError ? "dot error" : isRunning ? "dot" : "dot idle";
  const showDetails = isExpanded || isRunning || isError;

  return (
    <div className={showDetails ? "progress-strip is-expanded" : "progress-strip is-collapsed"}>
      {showDetails ? (
        <>
          <div className="ps-label">
            <div className="ps-stage">
              <span className={dotClass} />
              scan - {stage}
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
          {!isRunning && !isError ? (
            <button
              className="icon-btn"
              type="button"
              aria-label="Hide scan status"
              title="Hide scan status"
              onClick={() => setIsExpanded(false)}
            >
              <ChevronLeft size={14} />
            </button>
          ) : null}
        </>
      ) : (
        <button
          className="icon-btn"
          type="button"
          aria-label="Show scan status"
          title="Show scan status"
          onClick={() => setIsExpanded(true)}
        >
          <ChevronRight size={14} />
        </button>
      )}
    </div>
  );
}
