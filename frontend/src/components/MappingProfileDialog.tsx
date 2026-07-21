import { useEffect, useRef } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Database,
  Info,
  Layers3,
  RefreshCw,
  X,
} from "lucide-react";
import {
  profileInferenceResultSchema,
  type ProfileFinding,
} from "../contracts/viewer";
import type { DataSourceMode } from "../types";
import { titleCase } from "../utils/format";

export type MappingProfileDialogProps = {
  dataSourceMode: DataSourceMode;
  buildId: string | null;
  profileInference: Record<string, unknown> | null;
  warnings: string[];
  isProfileLoading: boolean;
  profileError?: string;
  onRetryProfile: () => void;
  onClose: () => void;
};

function StatusChip({ status }: { status: string }) {
  return <span className={`readiness-chip s-${status}`}>{titleCase(status)}</span>;
}

function ProfileCard({ profile }: { profile: ProfileFinding }) {
  return (
    <article className="st-card" aria-label={profile.label}>
      <div className="st-card-top">
        <div className="st-card-mark" aria-hidden="true"><Layers3 size={17} /></div>
        <div className="st-card-headings">
          <h3>{profile.label}</h3>
          <div className="st-card-badges">
            <StatusChip status={profile.status} />
            <span className="pill mono">{titleCase(profile.activation)}</span>
          </div>
        </div>
      </div>

      <p className="st-card-desc">
        {profile.description ?? profile.implementation_depth_reason}
      </p>

      <dl className="readiness-markdown-meta">
        <div><dt>Profile ID</dt><dd><code>{profile.profile_id}</code></dd></div>
        <div><dt>Axis</dt><dd>{titleCase(profile.primary_axis)}</dd></div>
        <div><dt>Coverage</dt><dd>{profile.coverage_detected} / {profile.coverage_total}</dd></div>
        <div><dt>Evidence</dt><dd>{profile.evidence_ids.length}</dd></div>
      </dl>

      {profile.missing_signals.length > 0 ? (
        <div className="readiness-refs">
          <strong>Missing deterministic signals</strong>
          <ul className="readiness-checks">
            {profile.missing_signals.map((signal) => <li key={signal}><code>{signal}</code></li>)}
          </ul>
        </div>
      ) : null}

      {profile.recommended_next_checks.length > 0 ? (
        <div className="readiness-refs">
          <strong>Recommended next checks</strong>
          <ul className="readiness-checks">
            {profile.recommended_next_checks.map((check) => <li key={check}>{check}</li>)}
          </ul>
        </div>
      ) : null}
    </article>
  );
}

function StateCard({
  kind,
  title,
  message,
  onRetry,
}: {
  kind: "loading" | "warning" | "error";
  title: string;
  message: string;
  onRetry?: () => void;
}) {
  const Icon = kind === "loading" ? RefreshCw : AlertTriangle;
  return (
    <div className="st-state" role={kind === "error" ? "alert" : "status"}>
      <span className={`ico ${kind === "error" ? "is-error" : ""}`}><Icon size={18} /></span>
      <h4>{title}</h4>
      <p>{message}</p>
      {onRetry ? <button className="btn" type="button" onClick={onRetry}><RefreshCw size={14} /> Retry</button> : null}
    </div>
  );
}

export function MappingProfileDialog({
  dataSourceMode,
  buildId,
  profileInference,
  warnings,
  isProfileLoading,
  profileError,
  onRetryProfile,
  onClose,
}: MappingProfileDialogProps) {
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

  const parsedProfile = profileInference == null
    ? null
    : profileInferenceResultSchema.safeParse(profileInference);
  const profileIdentityMismatch = parsedProfile?.success && buildId != null
    ? parsedProfile.data.build_id !== buildId
    : false;
  const profileMissingWarning = warnings.includes("profile_signals_missing_or_invalid");

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
        aria-labelledby="mapping-profile-title"
        tabIndex={-1}
      >
        <div className="st-route">
          <header className="st-head">
            <div className="st-head-main">
              <div className="st-title-mark" aria-hidden="true"><Layers3 size={18} /></div>
              <div className="st-titles">
                <span className="st-eyebrow">Backend facts</span>
                <h1 id="mapping-profile-title">Mapping profile</h1>
                <span className="st-sub">Read-only profile inference for the selected build.</span>
                {buildId ? <span className="st-project"><Database size={12} /> build <b>{buildId}</b></span> : null}
              </div>
            </div>
            <div className="st-actions">
              <button className="icon-btn" type="button" aria-label="Close mapping profile" onClick={onClose}><X size={16} /></button>
            </div>
          </header>

          <div className="st-scroll">
            <div className="st-body">
              <section aria-labelledby="profile-inference-heading">
                <div className="st-sec-head">
                  <h2 id="profile-inference-heading">Profile inference</h2>
                  <span className="st-sec-note">Backend-owned · selected build only</span>
                </div>

                {isProfileLoading ? (
                  <StateCard kind="loading" title="Loading profile facts" message="Waiting for the selected build response." />
                ) : profileError ? (
                  <StateCard kind="error" title="Profile facts could not be loaded" message={profileError} onRetry={onRetryProfile} />
                ) : profileInference == null ? (
                  <StateCard
                    kind="warning"
                    title="Profile facts unavailable"
                    message={profileMissingWarning
                      ? "The backend marked profile_signals.json missing or invalid. The base graph remains available."
                      : "This selected build does not include profile inference facts."}
                    onRetry={dataSourceMode === "api" ? onRetryProfile : undefined}
                  />
                ) : !parsedProfile?.success || profileIdentityMismatch ? (
                  <StateCard
                    kind="error"
                    title="Profile contract mismatch"
                    message={profileIdentityMismatch
                      ? "The profile facts belong to a different build and were not displayed."
                      : "The selected build returned a profile contract this viewer does not support."}
                    onRetry={dataSourceMode === "api" ? onRetryProfile : undefined}
                  />
                ) : (
                  <>
                    <div className="st-summary">
                      <div className="st-sm-ico"><CheckCircle2 size={17} /></div>
                      <div className="st-sm-text">
                        <span className="st-sm-k">Validated sidecar</span>
                        <span className="st-sm-v">
                          <b>{parsedProfile.data.profiles.length} capability profiles</b> · {parsedProfile.data.reference_capability_assessments.length} reference assessments
                        </span>
                      </div>
                    </div>
                    <div className="st-cards">
                      {parsedProfile.data.profiles.map((profile) => <ProfileCard key={profile.profile_id} profile={profile} />)}
                    </div>
                  </>
                )}
              </section>

            </div>
          </div>

          <p className="st-page-hint">
            <Info size={13} />
            <span>Profile labels, statuses, coverage and missing signals come from backend inference. This dialog does not infer a profile from repository names or graph labels.</span>
          </p>
        </div>
      </section>
    </div>
  );
}
