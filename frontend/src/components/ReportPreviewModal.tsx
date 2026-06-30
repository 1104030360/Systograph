import { Download, X } from "lucide-react";

type Props = {
  markdown: string;
  downloadUrl: string;
  onClose: () => void;
};

export function ReportPreviewModal({
  markdown,
  downloadUrl,
  onClose,
}: Props) {
  return (
    <div className="modal-scrim" role="presentation" onClick={onClose}>
      <section
        className="report-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="report-preview-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="report-modal-header">
          <div>
            <span className="eyebrow">Controlled artifact</span>
            <h2 id="report-preview-title">Latest system map report</h2>
          </div>
          <button
            className="icon-btn"
            type="button"
            onClick={onClose}
            aria-label="Close report preview"
          >
            <X size={16} />
          </button>
        </header>

        <p className="report-modal-copy">
          This Markdown is served by the local backend from its latest validated
          build result.
        </p>
        <pre className="report-preview">{markdown}</pre>

        <footer className="report-modal-actions">
          <button className="btn" type="button" onClick={onClose}>
            Close
          </button>
          <a className="btn is-active" href={downloadUrl}>
            <Download size={14} />
            Download Markdown
          </a>
        </footer>
      </section>
    </div>
  );
}
