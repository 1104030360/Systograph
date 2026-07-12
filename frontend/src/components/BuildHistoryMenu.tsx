import { History } from "lucide-react";
import type { MapBuildHistorySummary } from "../contracts/viewer";
import { titleCase } from "../utils/format";
import { relTime } from "../utils/time";

type Props = {
  /** Backend order: generated_at ASC — the last entry is the latest build. */
  builds: MapBuildHistorySummary[];
  activeBuildId: string | null;
  onSelect: (buildId: string | null) => void;
};

export function BuildHistoryMenu({ builds, activeBuildId, onSelect }: Props) {
  if (builds.length === 0) return null;

  const latestBuildId = builds[builds.length - 1].build_id;
  const viewedBuildId = activeBuildId ?? latestBuildId;
  const newestFirst = [...builds].reverse();

  return (
    <details className="toolbar-menu build-history-menu">
      <summary className="btn" aria-label={`Build history, ${builds.length} builds`} title="Immutable build history">
        <History size={14} />
        Builds
        <span className="fcount">{builds.length}</span>
      </summary>
      <div className="toolbar-popover align-right">
        <div className="popover-title">Build history</div>
        <div className="build-history-list">
          {newestFirst.map((build) => {
            const isLatest = build.build_id === latestBuildId;
            const isViewed = build.build_id === viewedBuildId;
            return (
              <button
                key={build.build_id}
                className={isViewed ? "build-history-item is-active" : "build-history-item"}
                type="button"
                aria-pressed={isViewed}
                onClick={() => onSelect(isLatest ? null : build.build_id)}
              >
                <span className="bh-reason">
                  {titleCase(build.build_reason)}
                  {isLatest ? <em className="bh-latest">latest</em> : null}
                </span>
                <code className="bh-id" title={build.build_id}>
                  {build.build_id}
                </code>
                <span className="bh-time">{relTime(build.generated_at)}</span>
              </button>
            );
          })}
        </div>
      </div>
    </details>
  );
}
