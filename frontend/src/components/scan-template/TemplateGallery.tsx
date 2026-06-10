import { Check, ChevronRight, CornerDownRight, GitBranch, Layers3, Lock } from "lucide-react";
import { useWording } from "../../wording";
import type { ScanProfile } from "../../types";

type GalleryTab = "system_default" | "project_custom";

function TemplateTile({
  profile,
  isSelected,
  onOpen,
}: {
  profile: ScanProfile;
  isSelected: boolean;
  onOpen: () => void;
}) {
  const w = useWording();
  const isSystem = profile.kind === "system_default";
  const name = isSystem ? w.systemName : w.customName;
  const desc = isSystem ? w.systemDesc : w.customDesc;
  return (
    <button className={"st-tile" + (isSelected ? " is-selected" : "")} type="button" onClick={onOpen}>
      {isSelected ? (
        <span className="st-tile-flag">
          <Check size={11} /> {w.inUse}
        </span>
      ) : null}
      <div className="st-tile-mark">{isSystem ? <Layers3 size={20} /> : <GitBranch size={20} />}</div>
      <div className="st-tile-name">{name}</div>
      <div className="st-tile-badges">
        <span className={"pill mono " + (isSystem ? "is-derived" : "is-accent")}>{profile.version_label}</span>
        {isSystem ? (
          <span className="pill is-readonly">
            <Lock size={11} /> {w.readOnlyBadge}
          </span>
        ) : (
          <span className="pill is-derived">
            <CornerDownRight size={11} /> {w.derivedShort}
          </span>
        )}
      </div>
      <p className="st-tile-desc">{desc}</p>
      <span className="st-tile-open">
        {w.galleryOpen} <ChevronRight size={13} />
      </span>
    </button>
  );
}

export function TemplateGallery({
  profiles,
  activeTab,
  onTabChange,
  selectedProfileId,
  customExists,
  onOpen,
  onReviewUnmapped,
}: {
  profiles: ScanProfile[];
  activeTab: GalleryTab;
  onTabChange: (tab: GalleryTab) => void;
  selectedProfileId: string;
  customExists: boolean;
  onOpen: (profileId: string) => void;
  onReviewUnmapped: () => void;
}) {
  const w = useWording();
  const shown = profiles.filter((p) => p.kind === activeTab);

  return (
    <div className="st-gallery">
      <div className="st-gallery-tabs">
        <button
          className={activeTab === "system_default" ? "detail-tab is-active" : "detail-tab"}
          type="button"
          onClick={() => onTabChange("system_default")}
        >
          {w.tabSystem}
          <span className="tabcount">{profiles.filter((p) => p.kind === "system_default").length}</span>
        </button>
        <button
          className={activeTab === "project_custom" ? "detail-tab is-active" : "detail-tab"}
          type="button"
          onClick={() => onTabChange("project_custom")}
        >
          {w.tabCustom}
          <span className="tabcount">{profiles.filter((p) => p.kind === "project_custom").length}</span>
        </button>
      </div>

      {activeTab === "project_custom" && !customExists ? (
        <div className="st-state">
          <div className="ico">
            <GitBranch size={20} />
          </div>
          <h4>{w.noCustomTitle}</h4>
          <p>{w.noCustomBody}</p>
          <button className="btn primary" type="button" onClick={onReviewUnmapped}>
            {w.reviewUnmapped}
          </button>
        </div>
      ) : (
        <div className="st-grid">
          {shown.map((p) => (
            <TemplateTile
              key={p.profile_id}
              profile={p}
              isSelected={p.profile_id === selectedProfileId}
              onOpen={() => onOpen(p.profile_id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
