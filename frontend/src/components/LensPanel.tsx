import type { GraphLensModel } from "../types";
import { getLensIcon } from "../icons/registry";
import { resolveLensSlots } from "../utils/lenses";

type Props = {
  lenses: GraphLensModel[];
  activeLensId: string | null;
  onToggleLens: (id: string) => void;
};

/* The six Graph Studio lenses are view modes over one backend projection:
   activating one highlights its membership and dims the rest — nothing is
   removed. A lens without backend membership stays disabled and says why. */
export function LensPanel({ lenses, activeLensId, onToggleLens }: Props) {
  const slots = resolveLensSlots(lenses);
  const activeSlot = slots.find((slot) => slot.id != null && slot.id === activeLensId);

  return (
    <section className="side-section">
      <div className="side-head">
        <span className="eyebrow">Lenses</span>
      </div>
      <div className="lens-list" role="group" aria-label="Graph lenses">
        {slots.map((slot) => {
          const disabled = slot.availability !== "available";
          const active = !disabled && slot.id != null && slot.id === activeLensId;
          const LensIcon = getLensIcon(slot.key);
          return (
            <button
              key={slot.key}
              className={[
                "filter-pill",
                "lens-pill",
                active ? "is-active" : "",
                disabled ? "is-unavailable" : "",
              ]
                .filter(Boolean)
                .join(" ")}
              type="button"
              disabled={disabled}
              aria-pressed={active}
              title={slot.unavailableReason ?? undefined}
              onClick={() => {
                if (slot.id != null) onToggleLens(slot.id);
              }}
            >
              <LensIcon className="lens-ico" size={13} aria-hidden="true" />
              {slot.label}
              <span className="fcount">{disabled ? "n/a" : slot.matchCount}</span>
            </button>
          );
        })}
      </div>
      {slots.every((slot) => slot.availability !== "available") ? (
        <p className="lens-note" role="note">
          Lenses are unavailable: the loaded build does not include lens membership.
        </p>
      ) : null}
      {activeSlot && activeSlot.matchCount === 0 ? (
        <p className="lens-note" role="status">
          No items match the {activeSlot.label} lens in this build.
        </p>
      ) : null}
    </section>
  );
}
