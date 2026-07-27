import { History } from "lucide-react";

type Props = {
  buildId: string | null;
  onBackToLatest: () => void;
};

/* Constant reminder while a pinned historical build is on screen, so an old
   overlay is never mistaken for the project's current state. */
export function HistoricalBuildIndicator({ buildId, onBackToLatest }: Props) {
  if (!buildId) return null;

  return (
    <div className="historical-indicator" role="note" aria-label="Historical build indicator">
      <History size={13} />
      <span>
        Historical build <code title={buildId}>{buildId}</code> — not the latest state
      </span>
      <button type="button" onClick={onBackToLatest}>
        Back to latest
      </button>
    </div>
  );
}
