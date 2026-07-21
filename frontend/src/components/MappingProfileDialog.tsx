import { useEffect, useRef } from "react";
import type { PendingProposalRow } from "../types";
import { ScanTemplatePage } from "../pages/ScanTemplatePage";

type Props = {
  onClose: () => void;
  onOpenProposal: (row: PendingProposalRow) => void;
};

export function MappingProfileDialog({ onClose, onOpenProposal }: Props) {
  const dialogRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const trigger = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    dialogRef.current?.focus();

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
      className="modal-scrim mapping-profile-scrim"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section
        ref={dialogRef}
        className="mapping-profile-dialog"
        role="dialog"
        aria-modal="true"
        aria-label="Mapping profile"
        tabIndex={-1}
      >
        <ScanTemplatePage onClose={onClose} onOpenProposal={onOpenProposal} />
      </section>
    </div>
  );
}
