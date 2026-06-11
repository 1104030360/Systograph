from __future__ import annotations

from pathlib import Path

from kai_mind.core.models.filesystem import (
    FileInventory,
    FileInventorySource,
    FileRecord,
    SkippedFile,
    SkipReason,
)
from kai_mind.core.models.scan_boundary import (
    ScanBoundaryDecisionAction,
    ScanBoundaryDecisionRequest,
    ScanBoundaryProposalStatus,
)
from kai_mind.core.models.system_map import Evidence
from kai_mind.core.services.scan_boundary_review_service import (
    InMemoryScanBoundaryRepository,
    ScanBoundaryReviewService,
)


def build_inventory(project_root: Path) -> FileInventory:
    return FileInventory(
        source=FileInventorySource.RECURSIVE,
        project_root=str(project_root),
        files=[
            FileRecord(path=".env", size_bytes=32),
            FileRecord(path="src/app.py", size_bytes=12),
        ],
        skipped=[
            SkippedFile(
                path="models/llm.gguf",
                reason=SkipReason.MODEL_WEIGHT,
                size_bytes=2_000_000,
            ),
            SkippedFile(
                path="logs/scan.log",
                reason=SkipReason.LARGE_LOG,
                size_bytes=2_000_000,
            ),
        ],
    )


def test_create_proposals_uses_masked_bounded_packets_and_fingerprints(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / ".env").write_text(
        "OPENAI_API_KEY=sk-live-secret-value",
        encoding="utf-8",
    )
    (project_root / "src").mkdir()
    (project_root / "src" / "app.py").write_text("print('ok')\n")
    (project_root / "models").mkdir()
    (project_root / "models" / "llm.gguf").write_bytes(b"model")
    (project_root / "logs").mkdir()
    (project_root / "logs" / "scan.log").write_text("x" * 100)
    inventory = build_inventory(project_root)

    proposals = ScanBoundaryReviewService().create_proposals(
        project_id="project:demo",
        project_root=project_root,
        inventory=inventory,
        evidence=[
            Evidence(
                id="evidence:env",
                kind="config_value",
                file=".env",
                path="OPENAI_API_KEY",
                value="[MASKED]",
                rule_id="config_env_value_detected",
            )
        ],
    )

    assert [proposal.status for proposal in proposals] == [
        ScanBoundaryProposalStatus.PENDING,
        ScanBoundaryProposalStatus.PENDING,
        ScanBoundaryProposalStatus.PENDING,
    ]
    by_path = {proposal.target.path: proposal for proposal in proposals}
    env_proposal = by_path[".env"]
    assert env_proposal.target.risk_type == "secret_like_config"
    assert env_proposal.target.fingerprint.startswith("sha256:")
    assert env_proposal.evidence_packet.masked_evidence_values == ["[MASKED]"]
    assert "sk-live-secret-value" not in env_proposal.model_dump_json()
    assert str(tmp_path) not in env_proposal.model_dump_json()

    assert by_path["models/llm.gguf"].target.risk_type == (
        "model_or_vector_persistence"
    )
    assert by_path["logs/scan.log"].target.risk_type == (
        "large_binary_generated_or_log"
    )


def test_unresolved_secret_like_file_is_held_before_provider_collection(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / ".env").write_text(
        "OPENAI_API_KEY=sk-live-secret-value",
        encoding="utf-8",
    )
    (project_root / "src.py").write_text("print('ok')\n", encoding="utf-8")
    inventory = FileInventory(
        source=FileInventorySource.RECURSIVE,
        project_root=str(project_root),
        files=[
            FileRecord(path=".env", size_bytes=32),
            FileRecord(path="src.py", size_bytes=12),
        ],
    )

    overlaid = ScanBoundaryReviewService().apply_policy_overlay(
        project_id="project:demo",
        project_root=project_root,
        inventory=inventory,
    )

    assert [item.path for item in overlaid.files] == ["src.py"]
    assert [(item.path, item.reason) for item in overlaid.skipped] == [
        (".env", SkipReason.PENDING_BOUNDARY_REVIEW)
    ]


def test_decision_applies_policy_overlay_only_when_fingerprint_matches(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    env_path = project_root / ".env"
    env_path.write_text(
        "OPENAI_API_KEY=sk-live-secret-value",
        encoding="utf-8",
    )
    inventory = FileInventory(
        source=FileInventorySource.RECURSIVE,
        project_root=str(project_root),
        files=[FileRecord(path=".env", size_bytes=32)],
    )
    service = ScanBoundaryReviewService(
        repository=InMemoryScanBoundaryRepository()
    )
    proposal = service.create_proposals(
        project_id="project:demo",
        project_root=project_root,
        inventory=inventory,
    )[0]

    result = service.decide(
        proposal.proposal_id,
        ScanBoundaryDecisionRequest(
            decision=ScanBoundaryDecisionAction.ALWAYS_SKIP,
            reason="Known local developer secret file.",
        ),
    )
    assert result.proposal.status == ScanBoundaryProposalStatus.DECIDED
    assert result.decision is not None
    assert result.decision.target.fingerprint == proposal.target.fingerprint

    overlaid = service.apply_policy_overlay(
        project_id="project:demo",
        project_root=project_root,
        inventory=inventory,
    )

    assert overlaid.files == []
    assert [(item.path, item.reason) for item in overlaid.skipped] == [
        (".env", SkipReason.SKIPPED_BY_POLICY_OVERLAY)
    ]

    env_path.write_text("OPENAI_API_KEY=sk-different-value", encoding="utf-8")
    changed = service.apply_policy_overlay(
        project_id="project:demo",
        project_root=project_root,
        inventory=inventory,
    )

    assert changed.files == []
    assert [(item.path, item.reason) for item in changed.skipped] == [
        (".env", SkipReason.PENDING_BOUNDARY_REVIEW)
    ]


def test_scan_normally_decision_allows_matching_secret_like_file(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / ".env").write_text(
        "OPENAI_API_KEY=sk-live-secret-value",
        encoding="utf-8",
    )
    inventory = FileInventory(
        source=FileInventorySource.RECURSIVE,
        project_root=str(project_root),
        files=[FileRecord(path=".env", size_bytes=32)],
    )
    service = ScanBoundaryReviewService()
    proposal = service.create_proposals(
        project_id="project:demo",
        project_root=project_root,
        inventory=inventory,
    )[0]
    service.decide(
        proposal.proposal_id,
        ScanBoundaryDecisionRequest(
            decision=ScanBoundaryDecisionAction.SCAN_NORMALLY,
            reason="Approved for normal config parsing.",
        ),
    )

    overlaid = service.apply_policy_overlay(
        project_id="project:demo",
        project_root=project_root,
        inventory=inventory,
    )

    assert [item.path for item in overlaid.files] == [".env"]
    assert overlaid.skipped == []


def test_skip_this_run_decision_is_consumed_after_first_overlay(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / ".env").write_text("TOKEN=sk-live-secret-value")
    inventory = FileInventory(
        source=FileInventorySource.RECURSIVE,
        project_root=str(project_root),
        files=[FileRecord(path=".env", size_bytes=26)],
    )
    service = ScanBoundaryReviewService()
    proposal = service.create_proposals(
        project_id="project:demo",
        project_root=project_root,
        inventory=inventory,
    )[0]
    service.decide(
        proposal.proposal_id,
        ScanBoundaryDecisionRequest(
            decision=ScanBoundaryDecisionAction.SKIP_THIS_RUN,
            reason="Skip once for local demo.",
        ),
    )

    first = service.apply_policy_overlay(
        project_id="project:demo",
        project_root=project_root,
        inventory=inventory,
    )
    second = service.apply_policy_overlay(
        project_id="project:demo",
        project_root=project_root,
        inventory=inventory,
    )

    assert first.files == []
    assert [(item.path, item.reason) for item in first.skipped] == [
        (".env", SkipReason.SKIPPED_BY_POLICY_OVERLAY)
    ]
    assert second.files == []
    assert [(item.path, item.reason) for item in second.skipped] == [
        (".env", SkipReason.PENDING_BOUNDARY_REVIEW)
    ]


def test_consumed_skip_this_run_allows_new_pending_proposal(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / ".env").write_text("TOKEN=sk-live-secret-value")
    inventory = FileInventory(
        source=FileInventorySource.RECURSIVE,
        project_root=str(project_root),
        files=[FileRecord(path=".env", size_bytes=26)],
    )
    service = ScanBoundaryReviewService()
    proposal = service.create_proposals(
        project_id="project:demo",
        project_root=project_root,
        inventory=inventory,
    )[0]
    service.decide(
        proposal.proposal_id,
        ScanBoundaryDecisionRequest(
            decision=ScanBoundaryDecisionAction.SKIP_THIS_RUN,
            reason="Skip once for local demo.",
        ),
    )
    service.apply_policy_overlay(
        project_id="project:demo",
        project_root=project_root,
        inventory=inventory,
    )

    proposals = service.create_proposals(
        project_id="project:demo",
        project_root=project_root,
        inventory=inventory,
    )

    assert len(proposals) == 1
    assert proposals[0].proposal_id != proposal.proposal_id
    assert proposals[0].status == ScanBoundaryProposalStatus.PENDING


def test_skipped_target_decision_replaces_audit_reason(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "models").mkdir()
    (project_root / "models" / "llm.gguf").write_bytes(b"model")
    inventory = FileInventory(
        source=FileInventorySource.RECURSIVE,
        project_root=str(project_root),
        skipped=[
            SkippedFile(
                path="models/llm.gguf",
                reason=SkipReason.MODEL_WEIGHT,
                size_bytes=4,
            )
        ],
    )
    service = ScanBoundaryReviewService()
    proposal = service.create_proposals(
        project_id="project:demo",
        project_root=project_root,
        inventory=inventory,
    )[0]
    service.decide(
        proposal.proposal_id,
        ScanBoundaryDecisionRequest(
            decision=ScanBoundaryDecisionAction.METADATA_ONLY,
            reason="Use metadata-only audit for model weights.",
        ),
    )

    overlaid = service.apply_policy_overlay(
        project_id="project:demo",
        project_root=project_root,
        inventory=inventory,
    )

    assert overlaid.files == []
    assert [(item.path, item.reason) for item in overlaid.skipped] == [
        ("models/llm.gguf", SkipReason.METADATA_ONLY_BY_POLICY_OVERLAY)
    ]


def test_skip_this_run_is_consumed_for_skipped_targets(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "logs").mkdir()
    (project_root / "logs" / "scan.log").write_text("x" * 100)
    inventory = FileInventory(
        source=FileInventorySource.RECURSIVE,
        project_root=str(project_root),
        skipped=[
            SkippedFile(
                path="logs/scan.log",
                reason=SkipReason.LARGE_LOG,
                size_bytes=100,
            )
        ],
    )
    service = ScanBoundaryReviewService()
    proposal = service.create_proposals(
        project_id="project:demo",
        project_root=project_root,
        inventory=inventory,
    )[0]
    service.decide(
        proposal.proposal_id,
        ScanBoundaryDecisionRequest(
            decision=ScanBoundaryDecisionAction.SKIP_THIS_RUN,
            reason="Skip once for local demo.",
        ),
    )

    first = service.apply_policy_overlay(
        project_id="project:demo",
        project_root=project_root,
        inventory=inventory,
    )
    second = service.apply_policy_overlay(
        project_id="project:demo",
        project_root=project_root,
        inventory=inventory,
    )

    assert [(item.path, item.reason) for item in first.skipped] == [
        ("logs/scan.log", SkipReason.SKIPPED_BY_POLICY_OVERLAY)
    ]
    assert [(item.path, item.reason) for item in second.skipped] == [
        ("logs/scan.log", SkipReason.LARGE_LOG)
    ]


def test_decision_reason_redacts_local_absolute_paths(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / ".env").write_text("TOKEN=sk-live-secret-value")
    inventory = FileInventory(
        source=FileInventorySource.RECURSIVE,
        project_root=str(project_root),
        files=[FileRecord(path=".env", size_bytes=26)],
    )
    service = ScanBoundaryReviewService()
    proposal = service.create_proposals(
        project_id="project:demo",
        project_root=project_root,
        inventory=inventory,
    )[0]

    result = service.decide(
        proposal.proposal_id,
        ScanBoundaryDecisionRequest(
            decision=ScanBoundaryDecisionAction.ALWAYS_SKIP,
            reason=f"See {project_root / '.env'} before skipping.",
        ),
    )

    assert result.decision is not None
    reason = result.decision.reason
    assert reason is not None
    assert str(project_root) not in reason
    assert "<LOCAL_PATH>" in reason
