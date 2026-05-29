import copy
import json
from pathlib import Path
from typing import Any, cast

import pytest

from kai_mind.core.services.system_map_validation_service import (
    SystemMapValidationError,
    SystemMapValidationService,
)

FIXTURE_DIR = Path(__file__).parents[1] / "fixtures" / "ai_system_map"


@pytest.fixture
def minimal_map() -> dict[str, Any]:
    fixture = FIXTURE_DIR / "valid_minimal.v1.json"
    return cast(
        "dict[str, Any]", json.loads(fixture.read_text(encoding="utf-8"))
    )


def test_rejects_nested_confidence_field(
    minimal_map: dict[str, Any],
) -> None:
    data = copy.deepcopy(minimal_map)
    data["components_by_slot"]["retriever"]["instances"][0]["confidence"] = 0.9

    with pytest.raises(SystemMapValidationError, match="confidence"):
        SystemMapValidationService().validate(data)


def test_rejects_windows_absolute_evidence_path(
    minimal_map: dict[str, Any],
) -> None:
    data = copy.deepcopy(minimal_map)
    data["evidence"][0]["file"] = "C:/repo/src/rag/retriever.py"

    with pytest.raises(
        SystemMapValidationError, match="project-relative POSIX"
    ):
        SystemMapValidationService().validate(data)


def test_rejects_windows_separator_evidence_path(
    minimal_map: dict[str, Any],
) -> None:
    data = copy.deepcopy(minimal_map)
    data["evidence"][0]["file"] = "src\\rag\\retriever.py"

    with pytest.raises(
        SystemMapValidationError, match="project-relative POSIX"
    ):
        SystemMapValidationService().validate(data)


def test_rejects_detected_slot_with_dangling_evidence_id(
    minimal_map: dict[str, Any],
) -> None:
    data = copy.deepcopy(minimal_map)
    data["components_by_slot"]["retriever"]["instances"][0]["evidence_ids"] = [
        "evidence:missing"
    ]

    with pytest.raises(SystemMapValidationError, match="evidence"):
        SystemMapValidationService().validate(data)


def test_rejects_endpoint_with_dangling_evidence_id(
    minimal_map: dict[str, Any],
) -> None:
    data = copy.deepcopy(minimal_map)
    data["endpoints"][0]["evidence_id"] = "evidence:missing"

    with pytest.raises(SystemMapValidationError, match="Endpoint"):
        SystemMapValidationService().validate(data)


def test_rejects_flow_edge_with_unknown_slot(
    minimal_map: dict[str, Any],
) -> None:
    data = copy.deepcopy(minimal_map)
    data["flows"][0]["edges"][0]["to_slot"] = "unknown_slot"

    with pytest.raises(SystemMapValidationError, match="unknown slot"):
        SystemMapValidationService().validate(data)


@pytest.mark.parametrize(
    ("target_type", "target"),
    [
        ("component_instance", "component:missing"),
        ("endpoint", "endpoint:missing"),
        ("component_slot", "missing_slot"),
        ("evidence", "evidence:missing"),
        ("file", "src/missing.py"),
    ],
)
def test_rejects_risk_hint_with_missing_target(
    minimal_map: dict[str, Any], target_type: str, target: str
) -> None:
    data = copy.deepcopy(minimal_map)
    data["risk_hints"].append(
        {
            "id": f"risk:missing:{target_type}",
            "type": "readiness",
            "target": target,
            "target_type": target_type,
            "evidence_id": data["evidence"][0]["id"],
            "rule_id": "test_missing_risk_target",
            "rationale": "Regression test for dangling risk target.",
        }
    )

    with pytest.raises(SystemMapValidationError, match="RiskHint"):
        SystemMapValidationService().validate(data)


def test_rejects_unmapped_component_with_dangling_evidence_id(
    minimal_map: dict[str, Any],
) -> None:
    data = copy.deepcopy(minimal_map)
    data["unmapped_components"].append(
        {
            "id": "unmapped:test",
            "observed_kind": "reranker",
            "status": "needs_confirmation",
            "reason": "Ambiguous custom component.",
            "evidence_ids": ["evidence:missing"],
        }
    )

    with pytest.raises(SystemMapValidationError, match="UnmappedComponent"):
        SystemMapValidationService().validate(data)


def test_rejects_extension_component_with_dangling_evidence_id(
    minimal_map: dict[str, Any],
) -> None:
    data = copy.deepcopy(minimal_map)
    data["extensions"].append(
        {
            "id": "extension:test",
            "name": "Redis cache",
            "kind": "cache",
            "status": "detected",
            "evidence_ids": ["evidence:missing"],
        }
    )

    with pytest.raises(SystemMapValidationError, match="ExtensionComponent"):
        SystemMapValidationService().validate(data)
