from __future__ import annotations

import os
from pathlib import Path

import pytest

from systograph.core.models.inventory_policy import InventoryPolicyAction
from systograph.core.models.inventory_provenance import (
    InventoryPolicyEffectiveOutcome,
)
from systograph.core.models.inventory_selection import (
    InventoryCandidate,
    InventoryCandidateOutcome,
    InventoryRequestedTargetResult,
    InventoryRequestedTargetStatus,
    InventoryTargetKind,
)
from systograph.core.models.scan_boundary import (
    ScanBoundaryDecisionAction,
    ScanBoundaryDecisionRequest,
)
from systograph.core.services.inventory_candidate_classifier import (
    InventoryCandidateClassifier,
)
from systograph.core.services.inventory_policy_matcher import (
    InventoryPolicyMatcher,
)
from systograph.core.services.inventory_selection_decision_service import (
    InventoryResolvedDecision,
)
from systograph.core.services.inventory_selection_precedence_service import (
    InventorySelectionPrecedenceService,
)
from systograph.core.services.scan_inventory_rule_loader import (
    ScanInventoryRuleLoader,
)


def classify(path: str, tmp_path: Path) -> InventoryCandidate:
    target = tmp_path / "file.py"
    target.write_text("x = 1\n", encoding="utf-8")
    catalog = ScanInventoryRuleLoader().load_default()
    classifier = InventoryCandidateClassifier(
        matcher=InventoryPolicyMatcher(catalog)
    )
    return classifier.classify(path, os.stat(target))


@pytest.mark.parametrize(
    "path",
    [
        "tests/unit/config/fixtures/minimal_config/settings.yaml",
        "packages/graphrag/tests/unit/test_tokenizer_config.py",
        "test/integration/docker-compose.yml",
        "src/__tests__/app.test.ts",
    ],
)
def test_test_suite_paths_are_hard_blocked(path: str, tmp_path: Path) -> None:
    # Given/When: a path inside a test-suite directory convention.
    candidate = classify(path, tmp_path)

    # Then: it never enters inventory and cannot be overridden, so test
    # fixtures can never light a capability node as detected.
    assert candidate.base_outcome == InventoryCandidateOutcome.HARD_BLOCKED
    assert candidate.override_allowed is False
    assert candidate.decision_required is False
    assert candidate.reason_code == "test_suite"


@pytest.mark.parametrize(
    "path",
    [
        "src/latest/app.py",
        "goldenverba/components/chunking/TokenChunker.py",
        "packages/graphrag/graphrag/config/defaults.py",
        "src/protest/handler.py",
        "app/testimonials.py",
    ],
)
def test_product_paths_are_not_blocked_by_name_similarity(
    path: str,
    tmp_path: Path,
) -> None:
    # Given/When/Then: only directory conventions are blocked -- a
    # substring match on "test" must never cut product code.
    candidate = classify(path, tmp_path)
    assert candidate.base_outcome != InventoryCandidateOutcome.HARD_BLOCKED


def test_scan_this_run_cannot_reinstate_a_blocked_test_file(
    tmp_path: Path,
) -> None:
    # Given: a hard-blocked test file and an explicit approve-everything
    # decision, which is exactly what the Web review flow can produce.
    candidate = classify("tests/unit/test_settings.py", tmp_path)
    decision = InventoryResolvedDecision(
        request=ScanBoundaryDecisionRequest(
            target_path=candidate.path,
            fingerprint=candidate.metadata_fingerprint,
            decision=ScanBoundaryDecisionAction.SCAN_THIS_RUN,
        ),
        target=InventoryRequestedTargetResult(
            target_path=candidate.path,
            target_kind=InventoryTargetKind.FILE,
            status=InventoryRequestedTargetStatus.REVIEWABLE,
            file_candidate=candidate,
        ),
    )

    # When
    effective, _reason = InventorySelectionPrecedenceService().planned_outcome(
        candidate,
        decision,
    )

    # Then: the block wins over the decision.
    assert effective == InventoryPolicyEffectiveOutcome.HARD_BLOCKED


def test_default_catalog_declares_test_suite_blocks() -> None:
    # Given/When
    catalog = ScanInventoryRuleLoader().load_default()

    # Then: the block action is a first-class catalog action.
    blocked = [
        rule
        for rule in catalog.path_rules
        if rule.action == InventoryPolicyAction.BLOCK
    ]
    assert {rule.pattern for rule in blocked} >= {"tests/", "test/"}
