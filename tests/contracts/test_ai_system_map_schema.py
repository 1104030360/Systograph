import json
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator

from kai_mind.core.models.system_map import (
    RagSystemMap,
    build_system_map_schema,
)
from kai_mind.core.services.system_map_validation_service import (
    SystemMapValidationError,
    SystemMapValidationService,
)

FIXTURE_DIR = Path(__file__).parents[1] / "fixtures" / "ai_system_map"
SCHEMA_PATH = (
    Path(__file__).parents[2] / "schemas" / "ai-system-map.v1.schema.json"
)


def load_fixture(name: str) -> dict[str, Any]:
    return cast(
        "dict[str, Any]",
        json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8")),
    )


def assert_valid_contract(data: dict[str, Any]) -> None:
    RagSystemMap.model_validate(data)
    Draft202012Validator(load_schema()).validate(data)
    SystemMapValidationService().validate(data)


def load_schema() -> dict[str, Any]:
    return cast(
        "dict[str, Any]",
        json.loads(SCHEMA_PATH.read_text(encoding="utf-8")),
    )


def test_valid_minimal_fixture_satisfies_ai_system_map_contract() -> None:
    data = load_fixture("valid_minimal.v1.json")

    assert_valid_contract(data)


def test_valid_rich_frontend_fixture_satisfies_ai_system_map_contract() -> (
    None
):
    data = load_fixture("valid_rich_frontend_sample.v1.json")

    assert_valid_contract(data)
    assert "viewer_load_result" not in data
    assert "graph_view_model" not in data


def test_checked_in_schema_matches_pydantic_generated_schema() -> None:
    assert load_schema() == build_system_map_schema()


def test_schema_requires_canonical_top_level_arrays() -> None:
    schema = load_schema()

    assert {
        "endpoints",
        "flows",
        "extensions",
        "unmapped_components",
        "detail_scans",
        "risk_hints",
        "recommended_next_checks",
        "query_trace_events",
    }.issubset(set(schema["required"]))


def test_schema_documents_project_relative_posix_path_fields() -> None:
    schema = load_schema()

    evidence_file = schema["$defs"]["Evidence"]["properties"]["file"]
    code_path_file = schema["$defs"]["CodePathStep"]["properties"]["file"]

    assert "project-relative posix" in evidence_file["description"].lower()
    assert "project-relative posix" in code_path_file["description"].lower()


def test_invalid_confidence_fixture_is_rejected() -> None:
    data = load_fixture("invalid_confidence.v1.json")

    try:
        SystemMapValidationService().validate(data)
    except SystemMapValidationError as exc:
        assert "confidence" in str(exc)
    else:
        raise AssertionError("confidence fixture should fail validation")


def test_invalid_detected_without_evidence_fixture_is_rejected() -> None:
    data = load_fixture("invalid_detected_without_evidence.v1.json")

    try:
        SystemMapValidationService().validate(data)
    except SystemMapValidationError as exc:
        assert "evidence" in str(exc)
    else:
        raise AssertionError(
            "detected slot without evidence should fail validation"
        )


def test_invalid_status_fixture_is_rejected() -> None:
    data = load_fixture("invalid_invalid_status.v1.json")

    try:
        RagSystemMap.model_validate(data)
    except ValueError as exc:
        assert "archived" in str(exc)
    else:
        raise AssertionError(
            "invalid status fixture should fail model validation"
        )


def test_invalid_absolute_evidence_path_fixture_is_rejected() -> None:
    data = load_fixture("invalid_absolute_evidence_path.v1.json")

    try:
        SystemMapValidationService().validate(data)
    except SystemMapValidationError as exc:
        assert "project-relative POSIX" in str(exc)
    else:
        raise AssertionError(
            "absolute evidence path fixture should fail validation"
        )
