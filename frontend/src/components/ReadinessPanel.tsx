import { useEffect, useRef, useState } from "react";
import {
  CircleSlash2,
  ClipboardCheck,
  Download,
  Eye,
  FileText,
  FlaskConical,
  LoaderCircle,
  X,
} from "lucide-react";
import {
  readinessReportSchema,
  type ReadinessFinding,
  type ReadinessReport,
} from "../contracts/viewer";
import type { GraphViewModel } from "../types";
import { titleCase } from "../utils/format";
import {
  downloadMapBuildReport,
  MapReportError,
  type MapReportErrorReason,
} from "../services/mapReportApi";
import { useViewerStore } from "../store/viewerStore";

type Props = {
  /** Raw backend readiness report; unsupported payloads never become findings. */
  report: Record<string, unknown> | null;
  graph: GraphViewModel;
  /** Build displayed by the current viewer envelope; null before one exists. */
  buildId: string | null;
  onClose: () => void;
};

const SAMPLE_READINESS_REPORT: ReadinessReport = {
  schema_version: "readiness-report/v1",
  source_schema_version: "ai-system-map/v2",
  scan_id: "scan:sample-preview",
  build_id: "build:sample-preview",
  environment_id: "environment:default-static",
  generated_from_build_id: "build:sample-preview",
  mapping_completeness: {
    numerator: 34,
    denominator: 52,
    value: 34 / 52,
    weights: { detected: 1, partial: 0.5, undetermined: 0, not_detected: 1, conflicted: 0 },
  },
  grounding: {
    applicability: "undetermined",
    status: "undetermined",
    dimensions: [],
    evidence_ids: [],
    reason: "Static evidence is available, but runtime grounding has not been verified.",
  },
  capability_summaries: [],
  findings: [
    {
      finding_id: "readiness:sample:retrieval",
      category: "capability_readiness",
      status: "partial",
      title: "Retrieval path needs runtime verification",
      reason: "The repository declares a retriever and vector store, but no bounded query trace is attached to this sample.",
      evidence_ids: [],
      recommended_next_checks: ["Run an opt-in query trace against the selected build."],
    },
  ],
  recommended_next_checks: [
    "Review unmapped components before applying mappings.",
    "Run a detail scan on components with partial evidence.",
  ],
  limitations: ["This is a UI example only. It is not a readiness result for the current repository."],
  primary_map_type: "agentic_ai_system",
};

function StatusChip({ status }: { status: string }) {
  return <span className={`readiness-chip s-${status}`}>{titleCase(status)}</span>;
}

function evidenceLabel(graph: GraphViewModel, evidenceId: string): string {
  return graph.details.evidence_by_id[evidenceId]?.title ?? evidenceId;
}

function buildReadinessMarkdown(report: ReadinessReport, graph: GraphViewModel): string {
  const lines = [
    "# Readiness report",
    "",
    `- Build: \`${report.build_id}\``,
    `- Source: \`${report.source_schema_version}\``,
    `- Mapping completeness: **${(report.mapping_completeness.value * 100).toFixed(1)}%**`,
    `- Grounding: **${titleCase(report.grounding.status)}**`,
    "",
    "## Grounding",
    "",
    report.grounding.reason ?? "No grounding explanation was provided.",
  ];

  lines.push("", "## Findings", "");
  if (report.findings.length === 0) lines.push("No findings for this build.");
  report.findings.forEach((finding) => {
    lines.push(`### ${finding.title}`, "", `**${titleCase(finding.status)} · ${titleCase(finding.category)}**`, "", finding.reason);
    if (finding.evidence_ids.length > 0) {
      lines.push("", "Evidence:", ...finding.evidence_ids.map((id) => `- ${evidenceLabel(graph, id)}`));
    }
    if (finding.recommended_next_checks.length > 0) {
      lines.push("", "Recommended next checks:", ...finding.recommended_next_checks.map((check) => `- ${check}`));
    }
    lines.push("");
  });

  if (report.recommended_next_checks.length > 0) {
    lines.push("## Report next checks", "", ...report.recommended_next_checks.map((check) => `- ${check}`), "");
  }
  if (report.limitations.length > 0) {
    lines.push("## Limitations", "", ...report.limitations.map((limitation) => `- ${limitation}`), "");
  }
  return lines.join("\n").trim();
}

function FindingCard({ finding, graph }: { finding: ReadinessFinding; graph: GraphViewModel }) {
  return (
    <article className="readiness-finding" aria-label={finding.title}>
      <h3>{finding.title}</h3>
      <div className="readiness-finding-meta">
        <StatusChip status={finding.status} />
        <span className="readiness-category">{titleCase(finding.category)}</span>
      </div>
      <p>{finding.reason}</p>
      {finding.evidence_ids.length > 0 ? (
        <div className="readiness-refs">
          <strong>Evidence</strong>
          <ul className="readiness-checks">
            {finding.evidence_ids.map((id) => <li key={id}>{evidenceLabel(graph, id)}</li>)}
          </ul>
        </div>
      ) : null}
      {finding.recommended_next_checks.length > 0 ? (
        <div className="readiness-refs">
          <strong>Recommended next checks</strong>
          <ul className="readiness-checks">
            {finding.recommended_next_checks.map((check) => <li key={check}>{check}</li>)}
          </ul>
        </div>
      ) : null}
    </article>
  );
}

function RenderedReport({ report, graph }: { report: ReadinessReport; graph: GraphViewModel }) {
  return (
    <article className="readiness-markdown-document">
      <h1>Readiness report</h1>
      <dl className="readiness-markdown-meta">
        <div><dt>Build</dt><dd><code>{report.build_id}</code></dd></div>
        <div><dt>Source</dt><dd><code>{report.source_schema_version}</code></dd></div>
        <div><dt>Mapping completeness</dt><dd><strong>{(report.mapping_completeness.value * 100).toFixed(1)}%</strong></dd></div>
        <div><dt>Grounding</dt><dd><StatusChip status={report.grounding.status} /></dd></div>
      </dl>

      <h2>Grounding</h2>
      <p>{report.grounding.reason ?? "No grounding explanation was provided."}</p>

      <h2>Findings</h2>
      {report.findings.length === 0 ? <p>No findings for this build.</p> : null}
      {report.findings.map((finding) => <FindingCard key={finding.finding_id} finding={finding} graph={graph} />)}

      {report.recommended_next_checks.length > 0 ? (
        <section>
          <h2>Report next checks</h2>
          <ul className="readiness-checks">
            {report.recommended_next_checks.map((check) => <li key={check}>{check}</li>)}
          </ul>
        </section>
      ) : null}

      {report.limitations.length > 0 ? (
        <section>
          <h2>Limitations</h2>
          <ul className="readiness-checks readiness-limitations">
            {report.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}
          </ul>
        </section>
      ) : null}
    </article>
  );
}

type DownloadState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success" }
  | { status: "error"; reason: MapReportErrorReason };

function downloadNote(state: DownloadState): string {
  switch (state.status) {
    case "idle":
      return "Download the map report published for this build.";
    case "loading":
      return "Preparing the build report…";
    case "success":
      return "Saved ai_system_map.md.";
    case "error":
      switch (state.reason) {
        case "artifact_not_available":
          return "This build did not publish a Markdown report.";
        case "build_not_found":
          return "This build no longer exists. Choose another build from build history.";
        case "artifact_not_found":
          return "The report artifact is not available at the expected path.";
        case "unknown":
          return "Could not download the report. Check the local API server and try again.";
      }
  }
}

function BuildReportDownload({
  apiBaseUrl,
  buildId,
}: {
  apiBaseUrl: string;
  buildId: string;
}) {
  const [state, setState] = useState<DownloadState>({ status: "idle" });
  const controllerRef = useRef<AbortController | null>(null);
  const settled = state.status === "error" && state.reason !== "unknown";

  useEffect(() => () => controllerRef.current?.abort(), []);

  async function save() {
    const controller = new AbortController();
    controllerRef.current?.abort();
    controllerRef.current = controller;
    setState({ status: "loading" });

    try {
      await downloadMapBuildReport(apiBaseUrl, buildId, controller.signal);
      if (!controller.signal.aborted) setState({ status: "success" });
    } catch (error) {
      if (controller.signal.aborted) return;
      setState({
        status: "error",
        reason: error instanceof MapReportError ? error.reason : "unknown",
      });
    } finally {
      if (controllerRef.current === controller) controllerRef.current = null;
    }
  }

  return (
    <div className="readiness-download">
      <button
        className="btn"
        type="button"
        onClick={() => void save()}
        disabled={state.status === "loading" || settled}
      >
        {state.status === "loading" ? (
          <LoaderCircle className="spin" aria-hidden="true" size={14} />
        ) : (
          <Download aria-hidden="true" size={14} />
        )}
        {state.status === "loading" ? "Downloading…" : "Download report (.md)"}
      </button>
      <p className="readiness-download-note" role="status" aria-live="polite">
        {downloadNote(state)}
      </p>
    </div>
  );
}

export function ReadinessPanel({
  report,
  graph,
  buildId,
  onClose,
}: Props) {
  const parsed = report == null ? null : readinessReportSchema.safeParse(report);
  const isSample = report == null;
  const displayReport = parsed?.success ? parsed.data : isSample ? SAMPLE_READINESS_REPORT : null;
  const [mode, setMode] = useState<"preview" | "source">("preview");
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const dataSourceMode = useViewerStore((state) => state.dataSourceMode);
  const apiBaseUrl = useViewerStore((state) => state.apiBaseUrl);
  const activeBuildId = useViewerStore((state) => state.activeBuildId);
  const downloadBuildId = dataSourceMode === "api" ? (activeBuildId ?? buildId) : null;

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
    <div className="modal-scrim" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className="readiness-dialog" role="dialog" aria-modal="true" aria-labelledby="readiness-dialog-title">
        <header className="readiness-head">
          <div>
            <span className="eyebrow">Inline build report</span>
            <h2 id="readiness-dialog-title"><ClipboardCheck aria-hidden="true" size={17} />Readiness</h2>
          </div>
          {displayReport ? <StatusChip status={displayReport.grounding.status} /> : null}
          <button ref={closeButtonRef} className="icon-btn" type="button" aria-label="Close readiness dialog" onClick={onClose}>
            <X size={15} />
          </button>
        </header>

        {downloadBuildId ? (
          <BuildReportDownload
            key={downloadBuildId}
            apiBaseUrl={apiBaseUrl}
            buildId={downloadBuildId}
          />
        ) : null}

        {isSample ? (
          <div className="readiness-sample-note" role="note">
            <FlaskConical aria-hidden="true" size={15} />
            <span><strong>Sample preview.</strong> This build does not include a readiness report; the content below is not a scan result.</span>
          </div>
        ) : null}

        <div className="readiness-view-tabs" role="tablist" aria-label="Readiness document view">
          <button type="button" role="tab" aria-selected={mode === "preview"} className={mode === "preview" ? "is-active" : ""} onClick={() => setMode("preview")}>
            <Eye aria-hidden="true" size={14} /> Preview
          </button>
          <button type="button" role="tab" aria-selected={mode === "source"} className={mode === "source" ? "is-active" : ""} disabled={!displayReport} onClick={() => setMode("source")}>
            <FileText aria-hidden="true" size={14} /> Generated Markdown
          </button>
        </div>
        <div className="readiness-body">
          {displayReport && mode === "preview" ? (
            <RenderedReport report={displayReport} graph={graph} />
          ) : displayReport ? (
            <div className="readiness-source-view">
              <div className="readiness-sample-note" role="note">
                <FileText aria-hidden="true" size={15} />
                <span>
                  This plain text is generated from the inline <code>readiness-report/v1</code>
                  payload. The build&apos;s own map artifact, <code>ai_system_map.md</code>, is a
                  separate document with its own download, not this text.
                </span>
              </div>
              <pre className="readiness-markdown-source">{buildReadinessMarkdown(displayReport, graph)}</pre>
            </div>
          ) : (
            <div className="readiness-empty">
              <CircleSlash2 aria-hidden="true" size={16} />
              <p>The readiness report uses a contract this viewer version does not support, so findings are not shown.</p>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
