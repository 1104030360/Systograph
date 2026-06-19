"""Create and apply same-run scan boundary review decisions."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from kai_mind.core.models.filesystem import (
    FileInventory,
    FileRecord,
    SkippedFile,
    SkipReason,
)
from kai_mind.core.models.scan_boundary import (
    MAX_BOUNDARY_EVIDENCE_SNIPPET_CHARS,
    MAX_BOUNDARY_EVIDENCE_VALUE_CHARS,
    ScanBoundaryDecisionAction,
    ScanBoundaryDecisionRequest,
    ScanBoundaryEvidencePacket,
    ScanBoundaryProposal,
    ScanBoundaryProposalStatus,
    ScanBoundaryTarget,
)
from kai_mind.core.models.system_map import Evidence
from kai_mind.core.services.path_safety_service import (
    PathSafetyError,
    is_project_relative_posix_path,
    normalize_project_relative_path,
    redact_local_paths,
)
from kai_mind.core.services.secret_masking_service import SecretMaskingService

FINGERPRINT_SAMPLE_BYTES = 4096
MAX_BOUNDARY_EVIDENCE_ITEMS = 12
SECRET_LIKE_FILENAMES = {
    ".env",
    ".env.local",
    ".env.development",
    ".env.production",
    ".env.test",
}
SECRET_LIKE_SUFFIXES = {
    ".key",
    ".pem",
    ".p12",
    ".pfx",
    ".keystore",
    ".jks",
}
SECRET_LIKE_MARKERS = (
    "secret",
    "token",
    "credential",
    "apikey",
    "api_key",
    "password",
)
VECTOR_PERSISTENCE_MARKERS = {
    "chroma",
    "faiss",
    "milvus",
    "qdrant",
    "weaviate",
    "vector",
    "vectors",
    "vector_store",
    "vectorstore",
}
VECTOR_PERSISTENCE_SUFFIXES = {
    ".ann",
    ".db",
    ".duckdb",
    ".faiss",
    ".hnsw",
    ".index",
    ".npy",
    ".npz",
    ".sqlite",
    ".sqlite3",
}
SOURCE_OR_DOC_SUFFIXES = {
    ".c",
    ".cc",
    ".cpp",
    ".cs",
    ".go",
    ".h",
    ".hpp",
    ".java",
    ".js",
    ".jsx",
    ".json",
    ".kt",
    ".md",
    ".php",
    ".py",
    ".rb",
    ".rs",
    ".scala",
    ".swift",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}


@dataclass(frozen=True)
class _BoundaryCandidate:
    path: str
    risk_type: str
    reason: str
    size_bytes: int | None
    target_type: str


class _RunBoundaryPolicy:
    def __init__(
        self,
        *,
        service: ScanBoundaryReviewService,
        project_id: str,
        decisions: tuple[ScanBoundaryDecisionRequest, ...],
    ) -> None:
        self._service = service
        self._project_id = project_id
        self._decisions = decisions

    def apply(
        self,
        *,
        project_root: Path,
        inventory: FileInventory,
    ) -> FileInventory:
        return self._service.apply_decisions(
            project_id=self._project_id,
            project_root=project_root,
            inventory=inventory,
            decisions=self._decisions,
        )


class ScanBoundaryReviewService:
    """Build pending boundary proposals and same-run inventory overlays."""

    def __init__(
        self,
        *,
        secret_masking_service: SecretMaskingService | None = None,
    ) -> None:
        self._secret_masking_service = (
            secret_masking_service or SecretMaskingService()
        )

    def create_proposals(
        self,
        *,
        project_id: str,
        project_root: Path,
        inventory: FileInventory,
        evidence: Iterable[Evidence] = (),
        decisions: Iterable[ScanBoundaryDecisionRequest] = (),
    ) -> list[ScanBoundaryProposal]:
        """Return boundary proposals still unresolved for the current scan."""

        _require_text("project_id", project_id)
        root = project_root.resolve()
        evidence_items = list(evidence)
        decisions_by_path = self._decisions_by_path(decisions)
        proposals: list[ScanBoundaryProposal] = []

        for candidate in self._candidate_targets(inventory):
            target = self._target_for_candidate(
                project_id=project_id,
                project_root=root,
                candidate=candidate,
            )
            decision = decisions_by_path.get(target.path)
            if decision is not None and self._decision_matches_target(
                decision=decision,
                target=target,
            ):
                continue

            packet = self._evidence_packet(
                project_id=project_id,
                project_root=root,
                target=target,
                evidence=evidence_items,
            )
            self._reject_unsafe_payload(packet.model_dump(mode="json"), root)
            now = _now()
            proposals.append(
                ScanBoundaryProposal(
                    proposal_id=self._proposal_id(
                        project_id=project_id,
                        target=target,
                    ),
                    project_id=project_id,
                    status=ScanBoundaryProposalStatus.PENDING,
                    target=target,
                    evidence_packet=packet,
                    created_at=now,
                    updated_at=now,
                )
            )

        return sorted(proposals, key=lambda item: item.target.path)

    def apply_decisions(
        self,
        *,
        project_id: str,
        project_root: Path,
        inventory: FileInventory,
        decisions: Iterable[ScanBoundaryDecisionRequest] = (),
    ) -> FileInventory:
        """Apply same-run decisions before providers collect file evidence."""

        _require_text("project_id", project_id)
        root = project_root.resolve()
        decisions_by_path = self._decisions_by_path(decisions)
        kept_files: list[FileRecord] = []
        overlay_skipped: list[SkippedFile] = []

        for file_record in inventory.files:
            risk_type = self._risk_type_for_file(file_record.path)
            if risk_type is None:
                kept_files.append(file_record)
                continue

            target = self._target_for_candidate(
                project_id=project_id,
                project_root=root,
                candidate=_BoundaryCandidate(
                    path=file_record.path,
                    risk_type=risk_type,
                    reason=self._reason_for_risk(risk_type),
                    size_bytes=file_record.size_bytes,
                    target_type="file",
                ),
            )
            decision = decisions_by_path.get(target.path)
            if decision is None or not self._decision_matches_target(
                decision=decision,
                target=target,
            ):
                overlay_skipped.append(
                    SkippedFile(
                        path=file_record.path,
                        reason=SkipReason.PENDING_BOUNDARY_REVIEW,
                        size_bytes=file_record.size_bytes,
                    )
                )
                continue

            if decision.decision == ScanBoundaryDecisionAction.SCAN_THIS_RUN:
                kept_files.append(file_record)
                continue

            overlay_skipped.append(
                SkippedFile(
                    path=file_record.path,
                    reason=SkipReason.SKIPPED_BY_POLICY_OVERLAY,
                    size_bytes=file_record.size_bytes,
                )
            )

        skipped_files = sorted(
            [*inventory.skipped, *overlay_skipped],
            key=lambda item: (item.path, item.reason.value),
        )
        return inventory.model_copy(
            update={
                "files": kept_files,
                "skipped": skipped_files,
            }
        )

    def for_decisions(
        self,
        *,
        project_id: str,
        decisions: Iterable[ScanBoundaryDecisionRequest] = (),
    ) -> _RunBoundaryPolicy:
        """Return a one-run inventory policy for ProjectScanService."""

        _require_text("project_id", project_id)
        return _RunBoundaryPolicy(
            service=self,
            project_id=project_id,
            decisions=tuple(decisions),
        )

    def _candidate_targets(
        self,
        inventory: FileInventory,
    ) -> list[_BoundaryCandidate]:
        candidates: dict[str, _BoundaryCandidate] = {}

        for file_record in inventory.files:
            risk_type = self._risk_type_for_file(file_record.path)
            if risk_type is None:
                continue
            candidates[file_record.path] = _BoundaryCandidate(
                path=file_record.path,
                risk_type=risk_type,
                reason=self._reason_for_risk(risk_type),
                size_bytes=file_record.size_bytes,
                target_type="file",
            )

        return sorted(candidates.values(), key=lambda item: item.path)

    def _risk_type_for_file(self, path: str) -> str | None:
        if _is_secret_like_path(path):
            return "secret_like_config"
        if _is_vector_persistence_path(path):
            return "model_or_vector_persistence"
        return None

    def _reason_for_risk(self, risk_type: str) -> str:
        reasons = {
            "secret_like_config": (
                "Secret-like config path requires user confirmation before "
                "this scan can inspect it."
            ),
            "model_or_vector_persistence": (
                "Model or vector persistence files may be large or local-only "
                "and require confirmation before this scan inspects them."
            ),
        }
        return reasons.get(risk_type, "Path requires scan boundary review.")

    def _target_for_candidate(
        self,
        *,
        project_id: str,
        project_root: Path,
        candidate: _BoundaryCandidate,
    ) -> ScanBoundaryTarget:
        del project_id
        return ScanBoundaryTarget(
            path=candidate.path,
            target_type=candidate.target_type,
            risk_type=candidate.risk_type,
            reason=candidate.reason,
            size_bytes=candidate.size_bytes,
            fingerprint=self._fingerprint(project_root, candidate.path),
        )

    def _evidence_packet(
        self,
        *,
        project_id: str,
        project_root: Path,
        target: ScanBoundaryTarget,
        evidence: Iterable[Evidence],
    ) -> ScanBoundaryEvidencePacket:
        matching = [item for item in evidence if item.file == target.path][
            :MAX_BOUNDARY_EVIDENCE_ITEMS
        ]
        return ScanBoundaryEvidencePacket(
            project_id=project_id,
            target_path=target.path,
            risk_type=target.risk_type,
            reason=target.reason,
            evidence_ids=[item.id for item in matching],
            rule_ids=sorted(
                {item.rule_id for item in matching if item.rule_id is not None}
            ),
            masked_evidence_values=[
                self._bounded_masked_text(
                    item.value,
                    project_root=project_root,
                    limit=MAX_BOUNDARY_EVIDENCE_VALUE_CHARS,
                )
                for item in matching
                if item.value is not None
            ],
            masked_snippets=[
                self._bounded_masked_text(
                    item.snippet,
                    project_root=project_root,
                    limit=MAX_BOUNDARY_EVIDENCE_SNIPPET_CHARS,
                )
                for item in matching
                if item.snippet is not None
            ],
            context_limits={
                "max_evidence_items": MAX_BOUNDARY_EVIDENCE_ITEMS,
                "max_value_chars": MAX_BOUNDARY_EVIDENCE_VALUE_CHARS,
                "max_snippet_chars": MAX_BOUNDARY_EVIDENCE_SNIPPET_CHARS,
                "raw_file_contents_included": False,
                "project_root_included": False,
            },
        )

    def _bounded_masked_text(
        self,
        value: str | None,
        *,
        project_root: Path,
        limit: int,
    ) -> str:
        if value is None:
            return ""
        masked = self._secret_masking_service.mask_text(value)
        redacted = redact_local_paths(masked, workspace_root=project_root)
        if len(redacted) <= limit:
            return redacted
        return f"{redacted[:limit]}...[truncated]"

    def _decisions_by_path(
        self,
        decisions: Iterable[ScanBoundaryDecisionRequest],
    ) -> dict[str, ScanBoundaryDecisionRequest]:
        by_path: dict[str, ScanBoundaryDecisionRequest] = {}
        for decision in decisions:
            safe_path = _safe_relative_path(decision.target_path)
            by_path[safe_path] = decision.model_copy(
                update={
                    "target_path": safe_path,
                    "reason": self._safe_text(decision.reason),
                }
            )
        return by_path

    def _decision_matches_target(
        self,
        *,
        decision: ScanBoundaryDecisionRequest,
        target: ScanBoundaryTarget,
    ) -> bool:
        return (
            decision.target_path == target.path
            and decision.fingerprint == target.fingerprint
        )

    def _safe_text(self, value: str | None) -> str | None:
        if value is None:
            return None
        masked = self._secret_masking_service.mask_text(value)
        return redact_local_paths(masked)

    def _proposal_id(
        self,
        *,
        project_id: str,
        target: ScanBoundaryTarget,
    ) -> str:
        payload = f"{project_id}:{target.path}:{target.fingerprint}"
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return f"scan-boundary-proposal:{digest[:32]}"

    def _fingerprint(self, project_root: Path, path: str) -> str:
        safe_path = _safe_relative_path(path)
        local_path = (project_root / safe_path).resolve()
        try:
            local_path.relative_to(project_root)
        except ValueError as exc:
            message = "Scan boundary path escapes project root"
            raise ValueError(message) from exc

        digest = hashlib.sha256()
        digest.update(safe_path.encode("utf-8"))
        try:
            stat_result = local_path.stat()
        except OSError:
            digest.update(b"missing")
            return f"sha256:{digest.hexdigest()}"

        digest.update(str(stat_result.st_size).encode("utf-8"))
        digest.update(str(stat_result.st_mtime_ns).encode("utf-8"))
        if local_path.is_file():
            digest.update(self._bounded_file_hash(local_path).encode("utf-8"))
        else:
            digest.update(b"not-file")
        return f"sha256:{digest.hexdigest()}"

    def _bounded_file_hash(self, local_path: Path) -> str:
        digest = hashlib.sha256()
        with local_path.open("rb") as handle:
            head = handle.read(FINGERPRINT_SAMPLE_BYTES)
            digest.update(head)
            try:
                handle.seek(
                    max(
                        0,
                        local_path.stat().st_size - FINGERPRINT_SAMPLE_BYTES,
                    )
                )
            except OSError:
                return digest.hexdigest()
            digest.update(handle.read(FINGERPRINT_SAMPLE_BYTES))
        return digest.hexdigest()

    def _reject_unsafe_payload(
        self,
        payload: object,
        project_root: Path,
    ) -> None:
        encoded = json.dumps(payload, sort_keys=True)
        if redact_local_paths(encoded, workspace_root=project_root) != encoded:
            raise ValueError("Scan boundary payload contains local path")
        if self._secret_masking_service.contains_unmasked_secret(encoded):
            raise ValueError("Scan boundary payload contains unmasked secret")


def _safe_relative_path(path: str) -> str:
    try:
        safe = normalize_project_relative_path(path)
    except PathSafetyError as exc:
        message = "Scan boundary path must be project-relative"
        raise ValueError(message) from exc
    if not is_project_relative_posix_path(safe):
        raise ValueError("Scan boundary path must be project-relative")
    return safe


def _is_secret_like_path(path: str) -> bool:
    safe = _safe_relative_path(path)
    name = Path(safe).name.lower()
    normalized = safe.lower().replace("-", "_")
    return (
        name in SECRET_LIKE_FILENAMES
        or any(name.endswith(suffix) for suffix in SECRET_LIKE_SUFFIXES)
        or any(marker in normalized for marker in SECRET_LIKE_MARKERS)
    )


def _is_vector_persistence_path(path: str) -> bool:
    safe = _safe_relative_path(path)
    path_obj = Path(safe)
    suffix = path_obj.suffix.lower()
    if suffix in SOURCE_OR_DOC_SUFFIXES:
        return False

    path_parts = {
        part.lower().replace("-", "_").lstrip(".") for part in path_obj.parts
    }
    stem = path_obj.stem.lower().replace("-", "_")
    has_marker = bool(
        VECTOR_PERSISTENCE_MARKERS.intersection(path_parts)
    ) or any(marker in stem for marker in VECTOR_PERSISTENCE_MARKERS)
    return has_marker and (
        suffix in VECTOR_PERSISTENCE_SUFFIXES or suffix == ""
    )


def _require_text(name: str, value: str) -> None:
    if not value:
        raise ValueError(f"{name} is required")


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
