from __future__ import annotations

import json
from pathlib import Path

import pytest

from systograph.core.models.ai_system_map_v2 import AiSystemMapV2
from systograph.core.models.profile_signal import ProfileInferenceResult
from systograph.core.services.canonical_map_loader import CanonicalMapLoader
from systograph.core.services.profile_inference_service import (
    ProfileInferenceService,
)
from systograph.core.services.profile_signal_validation_service import (
    ProfileSignalValidationError,
    ProfileSignalValidationService,
)

FIXTURE = Path("tests/fixtures/ai_system_map/v2/grounded_rag.v2.json")


def load_map() -> AiSystemMapV2:
    return (
        CanonicalMapLoader()
        .load(json.loads(FIXTURE.read_text(encoding="utf-8")))
        .normalized
    )


def valid_result() -> tuple[AiSystemMapV2, ProfileInferenceResult]:
    system_map = load_map()
    result = ProfileInferenceService().infer(
        system_map,
        build_id="build:grounded-rag",
        scan_id="scan:grounded-rag",
        environment_id="environment:default-static",
    )
    return system_map, result


def test_validation_rejects_unknown_assessment_evidence() -> None:
    system_map, result = valid_result()
    first = result.reference_capability_assessments[0]
    invalid_first = first.model_copy(
        update={
            "status": "detected",
            "evidence_ids": ("evidence:missing",),
            "direct_evidence_ids": ("evidence:missing",),
        }
    )
    invalid = result.model_copy(
        update={
            "reference_capability_assessments": (
                invalid_first,
                *result.reference_capability_assessments[1:],
            )
        }
    )

    with pytest.raises(ProfileSignalValidationError, match="unknown evidence"):
        ProfileSignalValidationService().validate(
            invalid, system_map=system_map
        )


def test_validation_rejects_absolute_path_in_profile_text() -> None:
    system_map, result = valid_result()
    first = result.profiles[0].model_copy(
        update={"uncertainty": "review /Users/example/private/app.py"}
    )
    invalid = result.model_copy(
        update={"profiles": (first, *result.profiles[1:])}
    )

    with pytest.raises(ProfileSignalValidationError, match="absolute path"):
        ProfileSignalValidationService().validate(
            invalid, system_map=system_map
        )


@pytest.mark.parametrize(
    ("field", "unknown_id", "match"),
    [
        ("related_component_ids", "component:missing", "component reference"),
        (
            "related_unmapped_component_ids",
            "unmapped:missing",
            "unmapped component reference",
        ),
        (
            "related_capability_candidate_component_ids",
            "capability-candidate:missing",
            "capability candidate reference",
        ),
        ("related_risk_hint_ids", "risk:missing", "risk hint reference"),
    ],
)
def test_validation_rejects_unknown_profile_navigation_reference(
    field: str,
    unknown_id: str,
    match: str,
) -> None:
    # Given: a valid result with one unknown navigation reference.
    system_map, result = valid_result()
    first = result.profiles[0].model_copy(update={field: (unknown_id,)})
    invalid = result.model_copy(
        update={"profiles": (first, *result.profiles[1:])}
    )

    # When / Then: validation fails closed instead of emitting partial output.
    with pytest.raises(ProfileSignalValidationError, match=match):
        ProfileSignalValidationService().validate(
            invalid, system_map=system_map
        )


def test_validation_accepts_same_build_complete_result() -> None:
    system_map, result = valid_result()

    validated = ProfileSignalValidationService().validate(
        result, system_map=system_map
    )

    assert validated is result
