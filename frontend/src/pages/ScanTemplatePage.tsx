import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, CheckCircle2, ChevronRight, FileCode2, RefreshCw, Search } from "lucide-react";
import { scanTemplateApi } from "../services/scanTemplateApi";
import { TemplateGallery } from "../components/scan-template/TemplateGallery";
import { TemplateDetail } from "../components/scan-template/TemplateDetail";
import { useWording, type WordingMode } from "../wording";
import type { PendingProposalRow, ScanProfile } from "../types";

type GalleryTab = "system_default" | "project_custom";
type Nav = { view: "gallery" } | { view: "detail"; profileId: string } | { view: "build" };

const SYSTEM_ID = "profile:rag-core-v1";
const CUSTOM_ID = "profile:project-custom-v1";

export function ScanTemplatePage({
  onClose,
  onOpenProposal,
  wordingMode,
  onWordingModeChange,
}: {
  onClose: () => void;
  onOpenProposal: (row: PendingProposalRow) => void;
  wordingMode: WordingMode;
  onWordingModeChange: (mode: WordingMode) => void;
}) {
  const w = useWording();
  const stateQuery = useQuery({ queryKey: ["scan-template-state"], queryFn: () => scanTemplateApi.getState() });
  const listsQuery = useQuery({ queryKey: ["mapping-status"], queryFn: () => scanTemplateApi.listMappingStatus() });

  const [nav, setNav] = useState<Nav>({ view: "gallery" });
  const [galleryTab, setGalleryTab] = useState<GalleryTab>("system_default");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const state = stateQuery.data;
  const profiles = useMemo<ScanProfile[]>(() => state?.profiles ?? [], [state]);
  const systemDefault = profiles.find((p) => p.kind === "system_default");
  const custom = profiles.find((p) => p.kind === "project_custom");
  const customExists = Boolean(custom);

  const backendSelected = state?.selected_profile_id ?? SYSTEM_ID;
  const rawSelected = selectedId ?? backendSelected;
  const effectiveSelected = !customExists && rawSelected === CUSTOM_ID ? SYSTEM_ID : rawSelected;
  const isCustomSelected = effectiveSelected === CUSTOM_ID;

  const lists = listsQuery.data;
  const pageState: "loading" | "error" | "loaded" = listsQuery.isError
    ? "error"
    : listsQuery.isPending
      ? "loading"
      : "loaded";

  const selectedName = isCustomSelected ? w.customName : w.systemName;

  const refreshAll = () => {
    void stateQuery.refetch();
    void listsQuery.refetch();
  };

  const headerBack = () => (nav.view === "gallery" ? onClose() : setNav({ view: "gallery" }));
  const detailProfile = nav.view === "detail" ? profiles.find((p) => p.profile_id === nav.profileId) ?? null : null;

  // Context-aware subtitle so the user can tell they've drilled into a template.
  const crumbName =
    nav.view === "build"
      ? w.customName
      : detailProfile?.kind === "system_default"
        ? w.systemName
        : detailProfile?.kind === "project_custom"
          ? w.customName
          : null;
  const subtitle =
    nav.view === "gallery" || !crumbName ? (
      w.pageSubtitle
    ) : (
      <span className="st-sub-crumb">
        Scan templates <ChevronRight size={12} /> <b>{crumbName}</b>
      </span>
    );

  return (
    <div className="st-route" role="dialog" aria-label="Scan Template">
      <header className="st-head">
        <button
          className="icon-btn st-back"
          type="button"
          onClick={headerBack}
          title={nav.view === "gallery" ? "Back to viewer" : "Back to templates"}
          aria-label={nav.view === "gallery" ? "Back to viewer" : "Back to templates"}
        >
          <ArrowLeft size={16} />
        </button>
        <div className="st-titles">
          <h1>Scan Template</h1>
          <span className="st-sub">{subtitle}</span>
          <span className="st-project">
            <FileCode2 size={12} /> project <b>{state?.project_name ?? "—"}</b>
          </span>
        </div>
        <div className="st-actions">
          {/* TEMP: wording A/B compare — remove once a direction is chosen. */}
          <div className="st-wording-toggle" title="Wording style (for comparison)">
            <span className="seg-label">Wording</span>
            <div className="segment">
              <button
                className={wordingMode === "explained" ? "is-active" : ""}
                type="button"
                onClick={() => onWordingModeChange("explained")}
              >
                A · explained
              </button>
              <button
                className={wordingMode === "casual" ? "is-active" : ""}
                type="button"
                onClick={() => onWordingModeChange("casual")}
              >
                B · plain
              </button>
              <button
                className={wordingMode === "hybrid" ? "is-active" : ""}
                type="button"
                onClick={() => onWordingModeChange("hybrid")}
              >
                C · mix
              </button>
            </div>
          </div>
          <button className="btn" type="button" onClick={refreshAll}>
            <RefreshCw size={14} /> Refresh
          </button>
          <button className="btn primary lg" type="button">
            <Search size={14} /> New scan
          </button>
        </div>
      </header>

      <div className="st-scroll">
        <div className="st-body">
          {nav.view === "gallery" ? (
            <>
              <div className="st-summary">
                <div className="st-sm-ico">
                  <CheckCircle2 size={17} />
                </div>
                <div className="st-sm-text">
                  <span className="st-sm-k">{w.nextScanWillUse}</span>
                  <span className="st-sm-v">
                    <b>{selectedName}</b>
                    {isCustomSelected ? (
                      <>
                        {" · "}
                        {w.derivedBadge.toLowerCase()}
                      </>
                    ) : null}
                  </span>
                </div>
                <div className="st-sm-actions">
                  <button
                    className="btn"
                    type="button"
                    onClick={() =>
                      setSelectedId(isCustomSelected ? SYSTEM_ID : customExists ? CUSTOM_ID : SYSTEM_ID)
                    }
                  >
                    Change
                  </button>
                </div>
              </div>

              <TemplateGallery
                profiles={profiles}
                activeTab={galleryTab}
                onTabChange={setGalleryTab}
                selectedProfileId={effectiveSelected}
                customExists={customExists}
                onOpen={(profileId) => setNav({ view: "detail", profileId })}
                onReviewUnmapped={() => {
                  setGalleryTab("project_custom");
                  setNav({ view: "build" });
                }}
              />
            </>
          ) : null}

          {nav.view === "detail" ? (
            <TemplateDetail
              profile={detailProfile}
              isSelected={effectiveSelected === detailProfile?.profile_id}
              onUse={() => detailProfile && setSelectedId(detailProfile.profile_id)}
              onBack={() => setNav({ view: "gallery" })}
              lists={lists}
              pageState={pageState}
              onRetry={() => void listsQuery.refetch()}
              onOpenProposal={onOpenProposal}
            />
          ) : null}

          {nav.view === "build" ? (
            <TemplateDetail
              profile={null}
              buildMode
              isSelected={false}
              onUse={() => {}}
              onBack={() => setNav({ view: "gallery" })}
              lists={lists}
              pageState={pageState}
              onRetry={() => void listsQuery.refetch()}
              onOpenProposal={onOpenProposal}
            />
          ) : null}
        </div>
      </div>
    </div>
  );
}
