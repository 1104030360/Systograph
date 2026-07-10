"""Integration tests for ai-system-map/v2 compatibility gate (00A)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from kai_mind.core.models.ai_system_map_v2 import AiSystemMapV2
from kai_mind.core.services.canonical_map_loader import CanonicalMapLoader
from kai_mind.core.services.system_map_v1_to_v2_adapter import (
    SystemMapV1ToV2Adapter,
)
from kai_mind.core.services.system_map_v2_validation_service import (
    SystemMapV2ValidationService,
)
from kai_mind.core.services.system_map_validation_service import (
    SystemMapValidationService,
)

V1_RICH = Path(
    "tests/fixtures/ai_system_map/valid_rich_frontend_sample.v1.json"
)
V2_DIR = Path("tests/fixtures/ai_system_map/v2")
REPORT_PATH = Path(
    "docs/work/Timmy/schedule/report/"
    "2026-07-10-ai-system-map-v2-compatibility-gate.md"
)


def test_v1_fixture_adapter_preserves_resolvable_evidence_locations() -> None:
    payload = json.loads(V1_RICH.read_text(encoding="utf-8"))
    system_map = SystemMapValidationService().validate(payload)
    canonical = SystemMapV1ToV2Adapter().adapt_to_canonical(system_map)

    SystemMapV2ValidationService().validate(canonical.model_dump(mode="json"))
    source_ids = {item.id for item in system_map.evidence}
    adapted_ids = {item.evidence_id for item in canonical.evidence}
    assert adapted_ids == source_ids
    for item in canonical.evidence:
        if item.location.path is not None:
            assert "\\" not in item.location.path
            assert not item.location.path.startswith("/")
            assert ":" not in item.location.path.split("/")[0]


def test_dual_read_loader_keeps_v1_and_v2_clients_compatible() -> None:
    v1_payload = json.loads(V1_RICH.read_text(encoding="utf-8"))
    v2_payload = json.loads(
        (V2_DIR / "grounded_rag.v2.json").read_text(encoding="utf-8")
    )
    loader = CanonicalMapLoader()

    v1_result = loader.load(v1_payload)
    v2_result = loader.load(v2_payload)

    assert v1_result.active_schema_version == "ai-system-map/v1"
    assert v2_result.active_schema_version == "ai-system-map/v2"
    assert isinstance(v1_result.normalized, AiSystemMapV2)
    assert isinstance(v2_result.normalized, AiSystemMapV2)
    # Active artifact contract for v1 clients remains the original payload.
    assert v1_payload["schema_version"] == "ai-system-map/v1"
    assert "components_by_slot" in v1_payload


@pytest.mark.parametrize(
    "fixture_name",
    [
        "non_grounded_llm_app.v2.json",
        "tool_using_agent.v2.json",
        "workflow_graph.v2.json",
    ],
)
def test_non_rag_v2_fixtures_are_not_forced_into_rag_slots(
    fixture_name: str,
) -> None:
    payload = json.loads((V2_DIR / fixture_name).read_text(encoding="utf-8"))
    system_map = SystemMapV2ValidationService().validate(payload)

    dumped = system_map.model_dump(mode="json")
    assert "components_by_slot" not in dumped
    assert system_map.system_type == "ai_system"


def test_windows_and_posix_project_relative_paths_round_trip_as_posix() -> (
    None
):
    payload = json.loads(
        (V2_DIR / "grounded_rag.v2.json").read_text(encoding="utf-8")
    )
    payload["evidence"][0]["location"]["path"] = "src/api/chat.py"
    system_map = SystemMapV2ValidationService().validate(payload)
    assert system_map.evidence[0].location.path == "src/api/chat.py"

    with pytest.raises(Exception, match="project-relative|POSIX|path"):
        bad = json.loads(json.dumps(payload))
        bad["evidence"][0]["location"]["path"] = r"C:\repo\src\api\chat.py"
        SystemMapV2ValidationService().validate(bad)


def test_compatibility_gate_report_exists_with_consumer_matrix() -> None:
    assert REPORT_PATH.is_file()
    text = REPORT_PATH.read_text(encoding="utf-8")
    assert "等价" in text or "等價" in text or "equivalent" in text.lower()
    assert "Plan 13" in text
    assert "active output" in text.lower() or "active output" in text
