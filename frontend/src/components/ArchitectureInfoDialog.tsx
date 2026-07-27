import { useEffect, useRef } from "react";
import { Info, X } from "lucide-react";
import type { GraphViewModel } from "../types";

type Props = {
  graph: GraphViewModel;
  onClose: () => void;
};

export function ArchitectureInfoDialog({ graph, onClose }: Props) {
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const trigger = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    closeButtonRef.current?.focus();

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      trigger?.focus();
    };
  }, [onClose]);

  return (
    <div
      className="modal-scrim"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section
        className="architecture-info-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="architecture-info-title"
      >
        <header className="architecture-info-head">
          <div>
            <span className="eyebrow">Architecture guide</span>
            <h2 id="architecture-info-title">
              <Info aria-hidden="true" size={18} />
              How to read this map
            </h2>
          </div>
          <button
            ref={closeButtonRef}
            className="icon-btn"
            type="button"
            aria-label="Close architecture information"
            onClick={onClose}
          >
            <X size={15} />
          </button>
        </header>

        <div className="architecture-info-body">
          <div className="architecture-info-grid">
            <article>
              <span className="eyebrow">Architecture model</span>
              <h3>Why ten planes?</h3>
              <p>
                The fixed reference map separates intent, control, ingestion, retrieval, extensions, evidence, generation,
                memory, governance and deployment. Repository components are projected into backend-owned planes.
              </p>
            </article>
            <article>
              <span className="eyebrow">Assessment model</span>
              <h3>Status is not activation</h3>
              <p>
                Assessment describes available evidence; activation describes runtime configuration. Both remain visible so
                an enabled component is never mistaken for a well-supported readiness finding.
              </p>
            </article>
            <article>
              <span className="eyebrow">Filter behavior</span>
              <h3>Backend membership only</h3>
              <p>
                Enabled views use published lenses, plane IDs and semantic kinds. Unsupported metadata remains unavailable
                instead of being reconstructed in the browser.
              </p>
            </article>
          </div>

          <section className="architecture-info-contract" aria-labelledby="architecture-contract-title">
            <div>
              <span className="eyebrow">Current contract boundary</span>
              <h3 id="architecture-contract-title">The frontend projects facts; it does not invent architecture.</h3>
              <p>
                Plane membership, lens membership, evidence, conflicts, endpoints and risk hints come from the selected
                immutable build. Missing metadata is presented as unavailable.
              </p>
            </div>
            <dl>
              <div><dt>Source schema</dt><dd>{graph.source_schema_version ?? "unavailable"}</dd></div>
              <div><dt>Graph schema</dt><dd>{graph.schema_version ?? "unavailable"}</dd></div>
              <div><dt>Build</dt><dd>{graph.build_id ?? "sample / unavailable"}</dd></div>
              <div><dt>Environment</dt><dd>{graph.environment_id ?? "unavailable"}</dd></div>
            </dl>
          </section>
        </div>
      </section>
    </div>
  );
}
