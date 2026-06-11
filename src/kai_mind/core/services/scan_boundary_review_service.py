"""Create and apply scan boundary review proposals."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from typing import Protocol
from uuid import uuid4

from kai_mind.core.models.filesystem import (
    FileInventory,
    FileRecord,
    SkippedFile,
    SkipReason,
)
from kai_mind.core.models.scan_boundary import (
    MAX_BOUNDARY_EVIDENCE_SNIPPET_CHARS,
    MAX_BOUNDARY_EVIDENCE_VALUE_CHARS,
    ScanBoundaryDecision,
    ScanBoundaryDecisionAction,
    ScanBoundaryDecisionRequest,
    ScanBoundaryDecisionResult,
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
VECTOR_OR_MODEL_MARKERS = (
    "chroma",
    "faiss",
    "milvus",
    "qdrant",
    "weaviate",
    "vector",
)


@dataclass(frozen=True)
class _BoundaryCandidate:
    path: str
    risk_type: str
    reason: str
    size_bytes: int | None
    target_type: str


class ScanBoundaryRepository(Protocol):
    """Storage boundary for scan boundary proposal lifecycle state."""

    def save_proposal(
        self,
        proposal: ScanBoundaryProposal,
    ) -> ScanBoundaryProposal:
        """Create or replace one boundary proposal."""
        ...

    def get_proposal(self, proposal_id: str) -> ScanBoundaryProposal | None:
        """Return one boundary proposal by id."""
        ...

    def list_proposals_for_project(
        self,
        project_id: str,
    ) -> list[ScanBoundaryProposal]:
        """Return proposals for one project."""
        ...

    def save_decision(
        self,
        decision: ScanBoundaryDecision,
    ) -> ScanBoundaryDecision:
        """Create or replace one boundary decision."""
        ...

    def get_decision_for_proposal(
        self,
        proposal_id: str,
    ) -> ScanBoundaryDecision | None:
        """Return the decision tied to a proposal."""
        ...

    def list_decisions_for_project(
        self,
        project_id: str,
    ) -> list[ScanBoundaryDecision]:
        """Return decisions for one project."""
        ...


class InMemoryScanBoundaryRepository:
    """Process-local scan boundary repository for local API and tests."""

    def __init__(self) -> None:
        self._proposals: dict[str, ScanBoundaryProposal] = {}
        self._decisions: dict[str, ScanBoundaryDecision] = {}

    def save_proposal(
        self,
        proposal: ScanBoundaryProposal,
    ) -> ScanBoundaryProposal:
        self._proposals[proposal.proposal_id] = proposal
        return proposal

    def get_proposal(self, proposal_id: str) -> ScanBoundaryProposal | None:
        return self._proposals.get(proposal_id)

    def list_proposals_for_project(
        self,
        project_id: str,
    ) -> list[ScanBoundaryProposal]:
        return sorted(
            [
                proposal
                for proposal in self._proposals.values()
                if proposal.project_id == project_id
            ],
            key=lambda item: (item.created_at, item.target.path),
        )

    def save_decision(
        self,
        decision: ScanBoundaryDecision,
    ) -> ScanBoundaryDecision:
        self._decisions[decision.proposal_id] = decision
        return decision

    def get_decision_for_proposal(
        self,
        proposal_id: str,
    ) -> ScanBoundaryDecision | None:
        return self._decisions.get(proposal_id)

    def list_decisions_for_project(
        self,
        project_id: str,
    ) -> list[ScanBoundaryDecision]:
        return sorted(
            [
                decision
                for decision in self._decisions.values()
                if decision.project_id == project_id
            ],
            key=lambda item: item.created_at,
        )


class _ProjectBoundaryPolicy:
    def __init__(
        self,
        *,
        service: ScanBoundaryReviewService,
        project_id: str,
    ) -> None:
        self._service = service
        self._project_id = project_id

    def apply(
        self,
        *,
        project_root: Path,
        inventory: FileInventory,
    ) -> FileInventory:
        return self._service.apply_policy_overlay(
            project_id=self._project_id,
            project_root=project_root,
            inventory=inventory,
        )


class ScanBoundaryReviewService:
    """Manage scan boundary proposals and next-run policy overlay."""

    def __init__(
        self,
        *,
        repository: ScanBoundaryRepository | None = None,
        secret_masking_service: SecretMaskingService | None = None,
    ) -> None:
        self._repository = repository or InMemoryScanBoundaryRepository()
        self._secret_masking_service = (
            secret_masking_service or SecretMaskingService()
        )
        self._decision_lock = RLock()

    def create_proposals(
        self,
        *,
        project_id: str,
        project_root: Path,
        inventory: FileInventory,
        evidence: Iterable[Evidence] = (),
    ) -> list[ScanBoundaryProposal]:
        """Create pending proposals from inventory and masked evidence."""

        _require_text("project_id", project_id)
        root = project_root.resolve()
        evidence_items = list(evidence)
        proposals: list[ScanBoundaryProposal] = []

        for candidate in self._candidate_targets(inventory):
            target = ScanBoundaryTarget(
                path=candidate.path,
                target_type=candidate.target_type,
                risk_type=candidate.risk_type,
                reason=candidate.reason,
                size_bytes=candidate.size_bytes,
                fingerprint=self._fingerprint(root, candidate.path),
            )
            existing = self._matching_proposal(project_id, target)
            if existing is not None:
                proposals.append(existing)
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
                self._repository.save_proposal(
                    ScanBoundaryProposal(
                        proposal_id=f"scan-boundary-proposal:{uuid4()}",
                        project_id=project_id,
                        status=ScanBoundaryProposalStatus.PENDING,
                        target=target,
                        evidence_packet=packet,
                        created_at=now,
                        updated_at=now,
                    )
                )
            )

        return sorted(proposals, key=lambda item: item.target.path)

    def list_for_project(self, project_id: str) -> list[ScanBoundaryProposal]:
        """Return boundary proposals for a project."""

        _require_text("project_id", project_id)
        return self._repository.list_proposals_for_project(project_id)

    def decide(
        self,
        proposal_id: str,
        request: ScanBoundaryDecisionRequest,
    ) -> ScanBoundaryDecisionResult:
        """Persist one user decision without mutating canonical artifacts."""

        with self._decision_lock:
            proposal = self._repository.get_proposal(proposal_id)
            if proposal is None:
                raise KeyError(proposal_id)
            if proposal.status != ScanBoundaryProposalStatus.PENDING:
                raise ValueError(
                    f"Proposal is not pending: {proposal.status.value}"
                )

            reason = self._safe_text(request.reason)
            now = _now()
            decision = ScanBoundaryDecision(
                decision_id=f"scan-boundary-decision:{uuid4()}",
                proposal_id=proposal.proposal_id,
                project_id=proposal.project_id,
                target=proposal.target,
                decision=request.decision,
                reason=reason,
                decision_digest=self._decision_digest(
                    proposal=proposal,
                    decision=request.decision,
                    reason=reason,
                ),
                created_at=now,
            )
            updated = proposal.model_copy(
                update={
                    "status": ScanBoundaryProposalStatus.DECIDED,
                    "updated_at": now,
                }
            )
            self._repository.save_proposal(updated)
            self._repository.save_decision(decision)
            return ScanBoundaryDecisionResult(
                proposal=updated,
                decision=decision,
            )

    def for_project(self, project_id: str) -> _ProjectBoundaryPolicy:
        """Return an inventory policy adapter for ProjectScanService."""

        _require_text("project_id", project_id)
        return _ProjectBoundaryPolicy(service=self, project_id=project_id)

    def apply_policy_overlay(
        self,
        *,
        project_id: str,
        project_root: Path,
        inventory: FileInventory,
    ) -> FileInventory:
        """Apply matching decisions to an inventory copy for a future scan."""

        decisions_by_path = self._active_decisions_by_path(project_id)
        root = project_root.resolve()
        kept_files: list[FileRecord] = []
        overlay_skipped: list[SkippedFile] = []
        kept_skipped: list[SkippedFile] = []

        for file_record in inventory.files:
            decision = decisions_by_path.get(file_record.path)
            if decision is None:
                pending_reason = self._pending_review_reason(file_record)
                if pending_reason is None:
                    kept_files.append(file_record)
                    continue
                overlay_skipped.append(
                    SkippedFile(
                        path=file_record.path,
                        reason=pending_reason,
                        size_bytes=file_record.size_bytes,
                    )
                )
                continue

            if not self._decision_matches_current_file(
                decision=decision,
                project_root=root,
                file_record=file_record,
            ):
                overlay_skipped.append(
                    SkippedFile(
                        path=file_record.path,
                        reason=SkipReason.PENDING_BOUNDARY_REVIEW,
                        size_bytes=file_record.size_bytes,
                    )
                )
                continue

            skip_reason = self._skip_reason_for_decision(decision.decision)
            if skip_reason is None:
                kept_files.append(file_record)
                continue

            overlay_skipped.append(
                SkippedFile(
                    path=file_record.path,
                    reason=skip_reason,
                    size_bytes=file_record.size_bytes,
                )
            )
            if decision.decision == ScanBoundaryDecisionAction.SKIP_THIS_RUN:
                self._repository.save_decision(
                    decision.model_copy(update={"applied_at": _now()})
                )

        for skipped in inventory.skipped:
            kept_skipped.append(
                self._apply_skipped_decision(
                    skipped=skipped,
                    decision=decisions_by_path.get(skipped.path),
                    project_root=root,
                )
            )

        skipped_files = sorted(
            [*kept_skipped, *overlay_skipped],
            key=lambda item: (item.path, item.reason.value),
        )
        return inventory.model_copy(
            update={
                "files": kept_files,
                "skipped": skipped_files,
            }
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

        for skipped in inventory.skipped:
            risk_type = self._risk_type_for_skipped(skipped)
            if risk_type is None:
                continue
            candidates.setdefault(
                skipped.path,
                _BoundaryCandidate(
                    path=skipped.path,
                    risk_type=risk_type,
                    reason=self._reason_for_risk(risk_type),
                    size_bytes=skipped.size_bytes,
                    target_type="directory"
                    if skipped.path.endswith("/")
                    else "file",
                ),
            )

        return sorted(candidates.values(), key=lambda item: item.path)

    def _risk_type_for_file(self, path: str) -> str | None:
        if _is_secret_like_path(path):
            return "secret_like_config"
        if _is_vector_or_model_path(path):
            return "model_or_vector_persistence"
        return None

    def _risk_type_for_skipped(self, skipped: SkippedFile) -> str | None:
        if _is_secret_like_path(skipped.path):
            return "secret_like_config"
        if skipped.reason == SkipReason.MODEL_WEIGHT:
            return "model_or_vector_persistence"
        if skipped.reason in {
            SkipReason.LARGE_FILE,
            SkipReason.LARGE_LOG,
            SkipReason.BINARY,
            SkipReason.GENERATED,
        }:
            return "large_binary_generated_or_log"
        if skipped.reason in {
            SkipReason.DEPENDENCY_DIRECTORY,
            SkipReason.VIRTUAL_ENV,
            SkipReason.BUILD_OUTPUT,
            SkipReason.CACHE_DIRECTORY,
            SkipReason.COVERAGE_OUTPUT,
        }:
            return "dependency_cache_or_generated"
        if skipped.reason == SkipReason.SYMLINK_OUTSIDE_ROOT:
            return "boundary_escape"
        if skipped.reason == SkipReason.GITIGNORED:
            return "gitignored_boundary"
        return None

    def _reason_for_risk(self, risk_type: str) -> str:
        reasons = {
            "secret_like_config": (
                "Secret-like config path requires user confirmation before "
                "future deep scanning."
            ),
            "model_or_vector_persistence": (
                "Model or vector persistence files are usually large and may "
                "only need metadata-level scanning."
            ),
            "large_binary_generated_or_log": (
                "Large, binary, generated, or log files should not be read "
                "deeply without an explicit policy decision."
            ),
            "dependency_cache_or_generated": (
                "Dependency, cache, or generated output is usually outside "
                "the project architecture source boundary."
            ),
            "boundary_escape": (
                "Symlink boundary escape requires explicit confirmation."
            ),
            "gitignored_boundary": (
                "Gitignored paths may contain local-only or sensitive data."
            ),
        }
        return reasons.get(risk_type, "Path requires scan boundary review.")

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

    def _matching_proposal(
        self,
        project_id: str,
        target: ScanBoundaryTarget,
    ) -> ScanBoundaryProposal | None:
        for proposal in self._repository.list_proposals_for_project(
            project_id
        ):
            if (
                proposal.target.path == target.path
                and proposal.target.fingerprint == target.fingerprint
            ):
                decision = self._repository.get_decision_for_proposal(
                    proposal.proposal_id
                )
                if (
                    decision is not None
                    and decision.decision
                    == ScanBoundaryDecisionAction.SKIP_THIS_RUN
                    and decision.applied_at is not None
                ):
                    continue
                return proposal
        return None

    def _active_decisions_by_path(
        self,
        project_id: str,
    ) -> dict[str, ScanBoundaryDecision]:
        active: dict[str, ScanBoundaryDecision] = {}
        for decision in self._repository.list_decisions_for_project(
            project_id
        ):
            if (
                decision.decision == ScanBoundaryDecisionAction.SKIP_THIS_RUN
                and decision.applied_at is not None
            ):
                continue
            active[decision.target.path] = decision
        return active

    def _pending_review_reason(
        self,
        file_record: FileRecord,
    ) -> SkipReason | None:
        if self._risk_type_for_file(file_record.path) is None:
            return None
        return SkipReason.PENDING_BOUNDARY_REVIEW

    def _decision_matches_current_file(
        self,
        *,
        decision: ScanBoundaryDecision,
        project_root: Path,
        file_record: FileRecord,
    ) -> bool:
        return self._decision_matches_current_path(
            decision=decision,
            project_root=project_root,
            path=file_record.path,
        )

    def _decision_matches_current_path(
        self,
        *,
        decision: ScanBoundaryDecision,
        project_root: Path,
        path: str,
    ) -> bool:
        if decision.target.path != path:
            return False
        try:
            current = self._fingerprint(project_root, path)
        except ValueError:
            return False
        return current == decision.target.fingerprint

    def _apply_skipped_decision(
        self,
        *,
        skipped: SkippedFile,
        decision: ScanBoundaryDecision | None,
        project_root: Path,
    ) -> SkippedFile:
        if decision is None:
            return skipped
        if not self._decision_matches_current_path(
            decision=decision,
            project_root=project_root,
            path=skipped.path,
        ):
            return skipped.model_copy(
                update={"reason": SkipReason.PENDING_BOUNDARY_REVIEW}
            )

        skip_reason = self._skip_reason_for_decision(decision.decision)
        if skip_reason is None:
            return skipped
        if decision.decision == ScanBoundaryDecisionAction.SKIP_THIS_RUN:
            self._repository.save_decision(
                decision.model_copy(update={"applied_at": _now()})
            )
        return skipped.model_copy(update={"reason": skip_reason})

    def _skip_reason_for_decision(
        self,
        decision: ScanBoundaryDecisionAction,
    ) -> SkipReason | None:
        if decision in {
            ScanBoundaryDecisionAction.SKIP_THIS_RUN,
            ScanBoundaryDecisionAction.ALWAYS_SKIP,
        }:
            return SkipReason.SKIPPED_BY_POLICY_OVERLAY
        if decision == ScanBoundaryDecisionAction.METADATA_ONLY:
            return SkipReason.METADATA_ONLY_BY_POLICY_OVERLAY
        if decision == ScanBoundaryDecisionAction.MASKED_SUMMARY_ONLY:
            return SkipReason.MASKED_SUMMARY_ONLY_BY_POLICY_OVERLAY
        return None

    def _safe_text(self, value: str | None) -> str | None:
        if value is None:
            return None
        masked = self._secret_masking_service.mask_text(value)
        return redact_local_paths(masked)

    def _decision_digest(
        self,
        *,
        proposal: ScanBoundaryProposal,
        decision: ScanBoundaryDecisionAction,
        reason: str | None,
    ) -> str:
        payload = {
            "proposal_id": proposal.proposal_id,
            "project_id": proposal.project_id,
            "target_path": proposal.target.path,
            "target_fingerprint": proposal.target.fingerprint,
            "decision": decision.value,
            "reason": reason,
        }
        encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
        return f"sha256:{hashlib.sha256(encoded).hexdigest()}"

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


def _is_vector_or_model_path(path: str) -> bool:
    safe = _safe_relative_path(path)
    normalized = safe.lower()
    return any(marker in normalized for marker in VECTOR_OR_MODEL_MARKERS)


def _require_text(name: str, value: str) -> None:
    if not value:
        raise ValueError(f"{name} is required")


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
