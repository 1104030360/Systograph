import { useState } from "react";
import { AlertTriangle, ArrowLeft, Check, CornerDownRight, GitBranch, Layers3, Lock, RefreshCw } from "lucide-react";
import { ConfirmedTable, PendingTable, SkeletonTable, SkippedTable } from "./MappingStatusTables";
import { useWording } from "../../wording";
import type { PendingProposalRow, ScanProfile } from "../../types";
import type { MappingStatusLists } from "../../services/scanTemplateApi";

type Tab = "confirmed" | "pending" | "skipped";
type PageState = "loading" | "error" | "loaded";

export function TemplateDetail({
  profile,
  buildMode = false,
  isSelected,
  onUse,
  onBack,
  lists,
  pageState,
  onRetry,
  onOpenProposal,
}: {
  // null + buildMode === true → "derive a project custom version" flow
  profile: ScanProfile | null;
  buildMode?: boolean;
  isSelected: boolean;
  onUse: () => void;
  onBack: () => void;
  lists?: MappingStatusLists;
  pageState: PageState;
  onRetry: () => void;
  onOpenProposal: (row: PendingProposalRow) => void;
}) {
  const w = useWording();
  const isSystem = profile?.kind === "system_default";
  const isCustom = buildMode || profile?.kind === "project_custom";
  const [tab, setTab] = useState<Tab>(buildMode ? "pending" : "confirmed");

  const counts = {
    confirmed: lists?.confirmed.length ?? 0,
    pending: lists?.pending.length ?? 0,
    skipped: lists?.skipped.length ?? 0,
  };

  const visibleTabs: [Tab, string, number][] = buildMode
    ? [
        ["pending", w.tabPending, counts.pending],
        ["skipped", w.tabSkipped, counts.skipped],
      ]
    : [
        ["confirmed", w.tabConfirmed, counts.confirmed],
        ["pending", w.tabPending, counts.pending],
        ["skipped", w.tabSkipped, counts.skipped],
      ];

  const name = buildMode ? w.customName : isSystem ? w.systemName : w.customName;
  const desc = buildMode ? w.buildDesc : isSystem ? w.systemDesc : w.customDesc;

  return (
    <div className="st-detail">
      <button className="btn ghost st-crumb" type="button" onClick={onBack}>
        <ArrowLeft size={14} /> All templates
      </button>

      {/* Template summary header */}
      <div className="st-detail-head">
        <div className="st-card-mark">{isSystem ? <Layers3 size={20} /> : <GitBranch size={20} />}</div>
        <div className="st-detail-titles">
          <h2>{name}</h2>
          <div className="st-card-badges">
            {buildMode ? (
              <span className="pill is-derived">
                <CornerDownRight size={11} /> {w.derivedBadge}
              </span>
            ) : (
              <>
                <span className={"pill mono " + (isSystem ? "is-derived" : "is-accent")}>{profile?.version_label}</span>
                {isSystem ? (
                  <span className="pill is-readonly">
                    <Lock size={11} /> {w.readOnlyBadge}
                  </span>
                ) : (
                  <span className="pill is-derived">
                    <CornerDownRight size={11} /> {w.derivedBadge}
                  </span>
                )}
              </>
            )}
          </div>
          <p className="st-detail-desc">{desc}</p>
        </div>
        {!buildMode ? (
          <div className="st-detail-actions">
            <button className={isSelected ? "btn primary" : "btn"} type="button" disabled={isSelected} onClick={onUse}>
              {isSelected ? (
                <>
                  <Check size={14} /> {w.inUse}
                </>
              ) : (
                w.useForNextScan
              )}
            </button>
          </div>
        ) : null}
      </div>

      {/* System default → read-only baseline components */}
      {isSystem && profile ? (
        <section>
          <div className="st-sec-head">
            <h3>{w.baselineHead}</h3>
            <span className="st-sec-note">{w.baselineNote}</span>
          </div>
          <div className="st-comp-list">
            {profile.core_components.map((c) => (
              <div className="st-comp-row" key={c.slot}>
                <span className="st-comp-dot" />
                {c.label}
                <span className="st-comp-slot">{c.slot}</span>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {/* Project custom → mapping status (no duplicate stat grid; counts live on the tabs) */}
      {isCustom ? (
        <section>
          <div className="st-sec-head">
            <h3>{w.statusHead}</h3>
            <span className="st-sec-note">{w.statusNote}</span>
          </div>
          <div className="st-status">
            <div className="st-status-tabs">
              {visibleTabs.map(([key, label, n]) => (
                <button
                  key={key}
                  className={tab === key ? "detail-tab is-active" : "detail-tab"}
                  type="button"
                  onClick={() => setTab(key)}
                >
                  {label}
                  <span className="tabcount">{pageState === "loaded" ? n : "—"}</span>
                </button>
              ))}
              <button
                className="icon-btn st-refresh"
                type="button"
                title="Refresh list"
                aria-label="Refresh list"
                onClick={onRetry}
              >
                <RefreshCw size={14} />
              </button>
            </div>

            {pageState === "loading" ? <SkeletonTable /> : null}

            {pageState === "error" ? (
              <div className="st-state">
                <div className="ico is-error">
                  <AlertTriangle size={20} />
                </div>
                <h4>Couldn't load the matches</h4>
                <p>Something went wrong. Check that the local scan is still running, then try again.</p>
                <button className="btn" type="button" onClick={onRetry}>
                  <RefreshCw size={14} /> Retry
                </button>
              </div>
            ) : null}

            {pageState === "loaded" && lists ? (
              <>
                {tab === "confirmed" ? <ConfirmedTable rows={lists.confirmed} /> : null}
                {tab === "pending" ? <PendingTable rows={lists.pending} onReview={onOpenProposal} /> : null}
                {tab === "skipped" ? <SkippedTable rows={lists.skipped} /> : null}
              </>
            ) : null}
          </div>
        </section>
      ) : null}
    </div>
  );
}
