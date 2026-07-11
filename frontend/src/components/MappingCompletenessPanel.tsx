import { CircleSlash2 } from "lucide-react";
import type { MappingCompleteness } from "../types";
import { compactId } from "../utils/format";

type Props = {
  completeness?: MappingCompleteness;
  buildId?: string | null;
  warningCount?: number;
};

const percent = new Intl.NumberFormat(undefined, {
  style: "percent",
  maximumFractionDigits: 1,
});

export function MappingCompletenessPanel({ completeness, buildId, warningCount = 0 }: Props) {
  if (!completeness) {
    return (
      <section className="mapping-completeness is-unavailable" aria-label="Mapping completeness unavailable">
        <CircleSlash2 aria-hidden="true" size={16} />
        <div>
          <strong>Mapping completeness unavailable</strong>
          <span>The backend did not provide denominator and scope.</span>
        </div>
      </section>
    );
  }

  return (
    <section className="mapping-completeness" aria-label="Mapping completeness">
      <div className="mapping-completeness-head">
        <span>Mapping completeness</span>
        {buildId ? <code title={buildId}>{compactId(buildId)}</code> : null}
      </div>
      <div className="mapping-completeness-value">
        <strong>{percent.format(completeness.value)}</strong>
        <span>
          {completeness.numerator} weighted / {completeness.denominator} reference nodes
        </span>
      </div>
      <div className="mapping-completeness-note">
        Backend assessed · activation excluded
        {warningCount > 0 ? ` · ${warningCount} load warning${warningCount === 1 ? "" : "s"}` : ""}
      </div>
    </section>
  );
}
