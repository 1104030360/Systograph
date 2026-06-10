import { FileCode2 } from "lucide-react";
import type { EvidenceRef } from "../../types";

/** Lists the concrete code evidence a mapping / candidate is based on —
 *  file · symbol (· line). Used instead of a confidence score, since the
 *  backend cites what it actually saw rather than guessing. */
export function EvidenceList({ items, compact = false }: { items: EvidenceRef[]; compact?: boolean }) {
  if (!items.length) return <span className="ev-none">No evidence recorded</span>;
  return (
    <div className={compact ? "ev-list is-compact" : "ev-list"}>
      {items.map((e) => (
        <span className="ev-ref" key={e.evidence_id} title={e.label ?? `${e.file}${e.symbol ? ` · ${e.symbol}` : ""}`}>
          <FileCode2 size={12} className="ico" />
          <span className="ev-file">{e.file.split("/").pop()}</span>
          {e.symbol ? <span className="ev-sym">{e.symbol}</span> : null}
          {e.line ? <span className="ev-line">:{e.line}</span> : null}
          {!e.symbol && e.label ? <span className="ev-label">{e.label}</span> : null}
        </span>
      ))}
    </div>
  );
}
