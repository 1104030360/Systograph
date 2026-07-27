import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, CheckCircle2, ChevronRight, FlaskConical, Folder, Info, Layers3, RefreshCw, Search } from "lucide-react";
import { scanTemplateApi } from "../services/scanTemplateApi";
import { TemplateGallery } from "../components/scan-template/TemplateGallery";
import { TemplateDetail } from "../components/scan-template/TemplateDetail";
import { useWording } from "../wording";
import type { PendingProposalRow, ScanProfile } from "../types";

type GalleryTab = "system_default" | "project_custom";
type Nav = { view: "gallery" } | { view: "detail"; profileId: string } | { view: "build" };

const SYSTEM_ID = "profile:rag-core-v1";
const CUSTOM_ID = "profile:project-custom-v1";

export function ScanTemplatePage({
  onClose,
  onOpenProposal,
}: {
  onClose: () => void;
  onOpenProposal: (row: PendingProposalRow) => void;
}) {
  const w = useWording();
  const stateQuery = useQuery({ queryKey: ["scan-template-state"], queryFn: () => scanTemplateApi.getState() });
  const listsQuery = useQuery({ queryKey: ["mapping-status"], queryFn: () => scanTemplateApi.listMappingStatus() });

  const [nav, setNav] = useState<Nav>({ view: "gallery" });
  const [galleryTab, setGalleryTab] = useState<GalleryTab>("system_default");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const state = stateQuery.data;
  const profiles = useMemo<ScanProfile[]>(() => state?.profiles ?? [], [state]);
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
  const projectName = state?.project_name ?? "unknown";
  const workflowStep = nav.view === "build" ? "review" : "setup";

  const refreshAll = () => {
    void stateQuery.refetch();
    void listsQuery.refetch();
  };

  const headerBack = () => (nav.view === "gallery" ? onClose() : setNav({ view: "gallery" }));
  const detailProfile = nav.view === "detail" ? profiles.find((p) => p.profile_id === nav.profileId) ?? null : null;
  const pageHint =
    nav.view === "build"
      ? w.buildDesc
      : detailProfile?.kind === "system_default"
        ? w.systemDesc
        : detailProfile?.kind === "project_custom"
          ? w.customDesc
          : w.localAiBody;

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
    <div className="st-route">
      <header className="st-head st-head-steps">
        <div className="st-head-main">
          <button
            className="icon-btn st-back"
            type="button"
            onClick={headerBack}
            title={nav.view === "gallery" ? "Back to viewer" : "Back to templates"}
            aria-label={nav.view === "gallery" ? "Back to viewer" : "Back to templates"}
          >
            <ArrowLeft size={16} />
          </button>
          <div className="st-title-mark" aria-hidden="true">
            <Layers3 size={18} />
          </div>
          <div className="st-titles">
            <span className="st-eyebrow">Scan setup</span>
            <h1>
              Scan Template
              <span className="st-sample-badge" title={w.sampleBadgeHint}>
                <FlaskConical size={11} /> {w.sampleBadge}
              </span>
            </h1>
            <span className="st-sub">{subtitle}</span>
            <span className="st-project">
              <Folder size={12} /> project <b>{projectName}</b>
            </span>
          </div>
        </div>

        <div className="st-workflow" aria-label="Scan template workflow">
          <button type="button" onClick={onClose}>
            <Folder size={13} /> Project
          </button>
          <ChevronRight size={12} />
          <button
            className={workflowStep === "setup" ? "is-active" : ""}
            type="button"
            disabled={workflowStep === "setup"}
            onClick={() => setNav({ view: "gallery" })}
          >
            <Layers3 size={13} /> Setup
          </button>
          <ChevronRight size={12} />
          <button className={workflowStep === "review" ? "is-active" : ""} type="button" disabled>
            <CheckCircle2 size={13} /> Review
          </button>
        </div>

        <div className="st-actions">
          <button className="btn" type="button" onClick={refreshAll}>
            <RefreshCw size={14} /> Refresh
          </button>
          {/* The scan-template-scoped scan API does not exist yet; an enabled
              button that does nothing reads as broken, so keep it disabled. */}
          <button className="btn primary lg" type="button" disabled title={w.newScanUnavailable}>
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
                    {isCustomSelected ? <> - {w.derivedBadge.toLowerCase()}</> : null}
                  </span>
                </div>
                <div className="st-sm-actions">
                  <button
                    className="btn"
                    type="button"
                    onClick={() => setSelectedId(isCustomSelected ? SYSTEM_ID : customExists ? CUSTOM_ID : SYSTEM_ID)}
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

      <p className="st-page-hint">
        <Info size={13} />
        <span>
          <b>{w.localAiTitle}</b> {pageHint}
        </span>
      </p>
    </div>
  );
}
