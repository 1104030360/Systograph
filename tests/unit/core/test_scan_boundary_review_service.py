from __future__ import annotations

from pathlib import Path

from systograph.core.models.filesystem import (
    FileInventory,
    FileInventorySource,
    FileRecord,
    SkippedFile,
    SkipReason,
)
from systograph.core.models.scan_boundary import (
    ScanBoundaryDecisionAction,
    ScanBoundaryDecisionRequest,
    ScanBoundaryProposalStatus,
)
from systograph.core.models.system_map import Evidence
from systograph.core.providers.filesystem_provider import FilesystemProvider
from systograph.core.services.scan_boundary_review_service import (
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


def test_create_proposals_uses_metadata_only_packets_and_fingerprints(
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
    ]
    proposal = proposals[0]
    assert proposal.target.path == ".env"
    assert proposal.target.risk_type == "secret_like_config"
    assert proposal.target.fingerprint.startswith("sha256:")
    assert [action.value for action in proposal.available_actions] == [
        "scan_this_run",
        "skip_this_run",
    ]
    assert proposal.evidence_packet.masked_evidence_values == []
    assert proposal.evidence_packet.masked_snippets == []
    assert "sk-live-secret-value" not in proposal.model_dump_json()
    assert str(tmp_path) not in proposal.model_dump_json()


def test_missing_decision_holds_secret_like_file_before_provider_collection(
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

    overlaid = ScanBoundaryReviewService().apply_decisions(
        project_id="project:demo",
        project_root=project_root,
        inventory=inventory,
    )

    assert [item.path for item in overlaid.files] == ["src.py"]
    assert [(item.path, item.reason) for item in overlaid.skipped] == [
        (".env", SkipReason.PENDING_BOUNDARY_REVIEW)
    ]


def test_scan_this_run_decision_allows_matching_file_only_for_current_overlay(
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
    decisions = [
        ScanBoundaryDecisionRequest(
            target_path=".env",
            fingerprint=proposal.target.fingerprint,
            decision=ScanBoundaryDecisionAction.SCAN_THIS_RUN,
        )
    ]

    first = service.apply_decisions(
        project_id="project:demo",
        project_root=project_root,
        inventory=inventory,
        decisions=decisions,
    )
    second = service.apply_decisions(
        project_id="project:demo",
        project_root=project_root,
        inventory=inventory,
    )

    assert [item.path for item in first.files] == [".env"]
    assert first.skipped == []
    assert second.files == []
    assert [(item.path, item.reason) for item in second.skipped] == [
        (".env", SkipReason.PENDING_BOUNDARY_REVIEW)
    ]


def test_skip_this_run_decision_skips_matching_file_for_current_overlay(
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

    overlaid = service.apply_decisions(
        project_id="project:demo",
        project_root=project_root,
        inventory=inventory,
        decisions=[
            ScanBoundaryDecisionRequest(
                target_path=".env",
                fingerprint=proposal.target.fingerprint,
                decision=ScanBoundaryDecisionAction.SKIP_THIS_RUN,
                reason="Skip this local file.",
            )
        ],
    )

    assert overlaid.files == []
    assert [(item.path, item.reason) for item in overlaid.skipped] == [
        (".env", SkipReason.SKIPPED_BY_POLICY_OVERLAY)
    ]
    assert overlaid.inventory_policy_audit[0].outcome == "skipped"
    assert overlaid.inventory_policy_audit[0].source == "runtime_boundary"
    assert overlaid.inventory_policy_audit[0].boundary_decision == (
        "skip_this_run"
    )


def test_stale_decision_returns_pending_proposal_and_holds_file(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    env_path = project_root / ".env"
    env_path.write_text("TOKEN=sk-live-secret-value")
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
    env_path.write_text("TOKEN=sk-different-value")
    decisions = [
        ScanBoundaryDecisionRequest(
            target_path=".env",
            fingerprint=proposal.target.fingerprint,
            decision=ScanBoundaryDecisionAction.SCAN_THIS_RUN,
        )
    ]

    proposals = service.create_proposals(
        project_id="project:demo",
        project_root=project_root,
        inventory=inventory,
        decisions=decisions,
    )
    overlaid = service.apply_decisions(
        project_id="project:demo",
        project_root=project_root,
        inventory=inventory,
        decisions=decisions,
    )

    assert len(proposals) == 1
    assert proposals[0].target.fingerprint != proposal.target.fingerprint
    assert overlaid.files == []
    assert [(item.path, item.reason) for item in overlaid.skipped] == [
        (".env", SkipReason.PENDING_BOUNDARY_REVIEW)
    ]


def test_skipped_targets_do_not_create_user_decision_proposals(
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
    proposals = ScanBoundaryReviewService().create_proposals(
        project_id="project:demo",
        project_root=project_root,
        inventory=inventory,
    )
    overlaid = ScanBoundaryReviewService().apply_decisions(
        project_id="project:demo",
        project_root=project_root,
        inventory=inventory,
        decisions=[
            ScanBoundaryDecisionRequest(
                target_path="models/llm.gguf",
                fingerprint="sha256:untrusted",
                decision=ScanBoundaryDecisionAction.SCAN_THIS_RUN,
            )
        ],
    )

    assert proposals == []
    assert overlaid.files == []
    assert overlaid.skipped == inventory.skipped


def test_vector_source_code_is_not_treated_as_persistence_artifact(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    source_dir = project_root / "src"
    persistence_dir = project_root / "data" / "vector_store"
    source_dir.mkdir(parents=True)
    persistence_dir.mkdir(parents=True)
    (source_dir / "vector_store.py").write_text(
        "class VectorStore: pass\n",
        encoding="utf-8",
    )
    (persistence_dir / "index.faiss").write_bytes(b"faiss-index")
    inventory = FileInventory(
        source=FileInventorySource.RECURSIVE,
        project_root=str(project_root),
        files=[
            FileRecord(path="src/vector_store.py", size_bytes=24),
            FileRecord(path="data/vector_store/index.faiss", size_bytes=11),
        ],
    )

    proposals = ScanBoundaryReviewService().create_proposals(
        project_id="project:demo",
        project_root=project_root,
        inventory=inventory,
    )
    overlaid = ScanBoundaryReviewService().apply_decisions(
        project_id="project:demo",
        project_root=project_root,
        inventory=inventory,
    )

    assert [proposal.target.path for proposal in proposals] == [
        "data/vector_store/index.faiss"
    ]
    assert [item.path for item in overlaid.files] == ["src/vector_store.py"]
    assert [(item.path, item.reason) for item in overlaid.skipped] == [
        (
            "data/vector_store/index.faiss",
            SkipReason.PENDING_BOUNDARY_REVIEW,
        )
    ]


def test_removed_long_term_policy_actions_are_not_valid_decisions() -> None:
    valid_actions = {action.value for action in ScanBoundaryDecisionAction}

    assert valid_actions == {"scan_this_run", "skip_this_run"}


def test_runtime_overlay_updates_audit_and_reproducibility_digest(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / ".env").write_text(
        "PLACEHOLDER=redacted\n",
        encoding="utf-8",
    )
    (project_root / "app.py").write_text(
        "print('ok')\n",
        encoding="utf-8",
    )
    persistence_path = project_root / "data" / "vector_store"
    persistence_path.mkdir(parents=True)
    (persistence_path / "index.faiss").write_bytes(b"faiss-index")
    inventory = FilesystemProvider().build_inventory(project_root)
    service = ScanBoundaryReviewService()
    proposals = service.create_proposals(
        project_id="project:demo",
        project_root=project_root,
        inventory=inventory,
    )
    assert {item.path for item in inventory.files} == {
        ".env",
        "app.py",
        "data/vector_store/index.faiss",
    }
    assert [item.target.path for item in proposals] == [
        ".env",
        "data/vector_store/index.faiss",
    ]
    proposal = proposals[0]
    scan_decision = ScanBoundaryDecisionRequest(
        target_path=".env",
        fingerprint=proposal.target.fingerprint,
        decision=ScanBoundaryDecisionAction.SCAN_THIS_RUN,
    )

    pending = service.apply_decisions(
        project_id="project:demo",
        project_root=project_root,
        inventory=inventory,
    )
    included = service.apply_decisions(
        project_id="project:demo",
        project_root=project_root,
        inventory=inventory,
        decisions=[scan_decision],
    )
    replayed = service.apply_decisions(
        project_id="project:demo",
        project_root=project_root,
        inventory=included,
        decisions=[scan_decision],
    )

    pending_entry = next(
        entry
        for entry in pending.inventory_policy_audit
        if entry.path == ".env"
    )
    included_entry = next(
        entry
        for entry in included.inventory_policy_audit
        if entry.path == ".env"
    )
    assert pending_entry.outcome == "pending_review"
    assert pending_entry.source == "runtime_boundary"
    assert pending_entry.target_fingerprint == proposal.target.fingerprint
    assert included_entry.outcome == "included"
    assert included_entry.boundary_decision == "scan_this_run"
    assert included.inventory_run_digest != inventory.inventory_run_digest
    assert included.inventory_run_digest != pending.inventory_run_digest
    assert replayed.inventory_policy_audit == included.inventory_policy_audit
    assert replayed.inventory_run_digest == included.inventory_run_digest
