import copy
import json
from pathlib import Path
from typing import Any, cast

import pytest

from kai_mind.core.services.system_map_validation_service import (
    SystemMapValidationError,
    SystemMapValidationService,
)

FIXTURE_DIR = Path(__file__).parents[2] / "fixtures" / "ai_system_map"


class BlindSecretMaskingService:
    def is_secret_key_name(self, key: str | None) -> bool:
        return False

    def contains_unmasked_secret(
        self,
        value: str,
        key: str | None = None,
        *,
        scan_key_value_pairs: bool = True,
    ) -> bool:
        return False


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


@pytest.mark.parametrize(
    "secret_value",
    [
        "sk-live-secret-value",
        "ghp_abcdefghijklmnopqrstuvwxyz1234567890",
        "glpat-abcdefghijklmnopqrstuvwxyz123456",
        "AKIAABCDEFGHIJKLMNOP",
        "xoxb-123456789012-123456789012-secretvalue",
        (
            "https://hooks.slack.com/services/"
            "T00000000/B00000000/abcdefghijklmnopqrstuvwx"
        ),
        "Authorization: Bearer live-token-value-1234567890",
    ],
)
def test_rejects_unmasked_token_patterns_supported_by_masking_service(
    minimal_map: dict[str, Any],
    secret_value: str,
) -> None:
    data = copy.deepcopy(minimal_map)
    data["evidence"][0]["value"] = secret_value

    with pytest.raises(SystemMapValidationError, match="Unmasked secret"):
        SystemMapValidationService().validate(data)


def test_rejects_unmasked_secret_key_value(
    minimal_map: dict[str, Any],
) -> None:
    data = copy.deepcopy(minimal_map)
    data["evidence"][0]["value"] = "OPENAI_API_KEY=sk-live-secret-value"

    with pytest.raises(SystemMapValidationError, match="Unmasked secret"):
        SystemMapValidationService().validate(data)


def test_rejects_unmasked_structured_secret_value(
    minimal_map: dict[str, Any],
) -> None:
    data = copy.deepcopy(minimal_map)
    data["evidence"][0]["key"] = "OPENAI_API_KEY"
    data["evidence"][0]["value"] = "ordinary-looking-secret"

    with pytest.raises(SystemMapValidationError, match="Unmasked secret"):
        SystemMapValidationService().validate(data)


@pytest.mark.parametrize("field", ["value", "snippet"])
def test_rejects_url_credentials_without_echoing_them(
    minimal_map: dict[str, Any],
    field: str,
) -> None:
    data = copy.deepcopy(minimal_map)
    raw_url = "postgresql://demo:synthetic-pass-138@db.example:5432/app"
    data["evidence"][0][field] = raw_url

    with pytest.raises(SystemMapValidationError) as exc_info:
        SystemMapValidationService().validate(data)

    message = str(exc_info.value)
    assert "Unmasked secret" in message
    assert f"$.evidence[0].{field}" in message
    assert raw_url not in message
    assert "synthetic-pass-138" not in message


def test_independent_validator_rejects_url_credentials_when_masker_is_blind(
    minimal_map: dict[str, Any],
) -> None:
    data = copy.deepcopy(minimal_map)
    data["evidence"][0]["value"] = (
        "redis://:synthetic-pass-138@cache.example:6379/0"
    )

    with pytest.raises(SystemMapValidationError, match="Unmasked secret"):
        SystemMapValidationService(
            secret_masking_service=BlindSecretMaskingService(),  # type: ignore[arg-type]
        ).validate(data)


def test_accepts_masked_url_credentials(
    minimal_map: dict[str, Any],
) -> None:
    data = copy.deepcopy(minimal_map)
    data["evidence"][0]["value"] = (
        "postgresql://demo:[MASKED]@db.example:5432/app"
    )

    SystemMapValidationService().validate(data)


def test_rejects_unmasked_secret_keyed_list_value(
    minimal_map: dict[str, Any],
) -> None:
    data = copy.deepcopy(minimal_map)
    data["query_trace_events"].append(
        {
            "id": "trace_event:secret-keyed-list",
            "sequence_index": 0,
            "timestamp": "2026-06-04T00:00:00Z",
            "input": {
                "api_key": ["ordinary-looking-secret"],
            },
        }
    )

    with pytest.raises(SystemMapValidationError, match="Unmasked secret"):
        SystemMapValidationService().validate(data)


@pytest.mark.parametrize(
    "api_key_payload",
    [
        {"value": "ordinary-looking-secret"},
        {"nested": {"value": "ordinary-looking-secret"}},
    ],
)
def test_rejects_unmasked_secret_keyed_nested_object_value(
    minimal_map: dict[str, Any],
    api_key_payload: dict[str, Any],
) -> None:
    data = copy.deepcopy(minimal_map)
    data["query_trace_events"].append(
        {
            "id": "trace_event:secret-keyed-object",
            "sequence_index": 0,
            "timestamp": "2026-06-04T00:00:00Z",
            "input": {
                "api_key": api_key_payload,
            },
        }
    )

    with pytest.raises(SystemMapValidationError, match="Unmasked secret"):
        SystemMapValidationService().validate(data)


def test_accepts_secret_keyed_metadata_fields(
    minimal_map: dict[str, Any],
) -> None:
    data = copy.deepcopy(minimal_map)
    data["query_trace_events"].append(
        {
            "id": "trace_event:secret-keyed-metadata",
            "sequence_index": 0,
            "timestamp": "2026-06-04T00:00:00Z",
            "input": {
                "api_key": {
                    "source": "env",
                    "provider": "openai",
                    "redacted": True,
                    "last4": "1234",
                    "value": "[MASKED]",
                },
            },
        }
    )

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


def test_rejects_parent_traversal_evidence_path(
    minimal_map: dict[str, Any],
) -> None:
    data = copy.deepcopy(minimal_map)
    data["evidence"][0]["file"] = "../secrets.txt"

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


def test_rejects_duplicate_endpoint_id(
    minimal_map: dict[str, Any],
) -> None:
    data = copy.deepcopy(minimal_map)
    duplicate_endpoint = copy.deepcopy(data["endpoints"][0])
    duplicate_endpoint["value"] = "http://localhost:8000/duplicate"
    data["endpoints"].append(duplicate_endpoint)

    with pytest.raises(SystemMapValidationError, match="duplicate id"):
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


def test_accepts_detail_scan_targets_for_extension_and_evidence(
    minimal_map: dict[str, Any],
) -> None:
    data = copy.deepcopy(minimal_map)
    extension_id = "extension:test"
    evidence_id = data["evidence"][0]["id"]
    data["extensions"].append(
        {
            "id": extension_id,
            "name": "Redis cache",
            "kind": "cache",
            "status": "detected",
            "confirmed_by_user": True,
        }
    )
    data["detail_scans"].extend(
        [
            {
                "id": "detail:extension",
                "target_type": "extension",
                "target": extension_id,
                "scan_depth": "component",
                "status": "success",
            },
            {
                "id": "detail:evidence",
                "target_type": "evidence",
                "target": evidence_id,
                "scan_depth": "code_path",
                "status": "success",
            },
        ]
    )

    SystemMapValidationService().validate(data)


def test_accepts_recommended_next_check_with_valid_endpoint_target(
    minimal_map: dict[str, Any],
) -> None:
    data = copy.deepcopy(minimal_map)
    endpoint_id = data["endpoints"][0]["id"]
    data["recommended_next_checks"].append(
        {
            "id": "check:runtime_readiness",
            "target_type": "endpoint",
            "target": endpoint_id,
            "reason": "Runtime endpoint should be verified.",
            "action": "Start the app and verify the endpoint is reachable.",
        }
    )

    SystemMapValidationService().validate(data)


def test_rejects_recommended_next_check_with_missing_target(
    minimal_map: dict[str, Any],
) -> None:
    data = copy.deepcopy(minimal_map)
    data["recommended_next_checks"].append(
        {
            "id": "check:runtime_readiness",
            "target_type": "endpoint",
            "target": "endpoint:missing",
            "reason": "Runtime endpoint should be verified.",
            "action": "Start the app and verify the endpoint is reachable.",
        }
    )

    with pytest.raises(SystemMapValidationError, match="RecommendedNextCheck"):
        SystemMapValidationService().validate(data)
