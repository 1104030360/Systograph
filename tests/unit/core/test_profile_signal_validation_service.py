from __future__ import annotations

import json
from pathlib import Path

import pytest

from kai_mind.core.models.ai_system_map_v2 import AiSystemMapV2
from kai_mind.core.models.profile_signal import ProfileInferenceResult
from kai_mind.core.services.canonical_map_loader import CanonicalMapLoader
from kai_mind.core.services.profile_inference_service import (
    ProfileInferenceService,
)
from kai_mind.core.services.profile_signal_validation_service import (
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


def test_validation_rejects_unknown_related_risk_hint() -> None:
    system_map, result = valid_result()
    first = result.profiles[0].model_copy(
        update={"related_risk_hint_ids": ("risk:missing",)}
    )
    invalid = result.model_copy(
        update={"profiles": (first, *result.profiles[1:])}
    )

    with pytest.raises(ProfileSignalValidationError, match="risk hint"):
        ProfileSignalValidationService().validate(
            invalid, system_map=system_map
        )


def test_validation_accepts_same_build_complete_result() -> None:
    system_map, result = valid_result()

    validated = ProfileSignalValidationService().validate(
        result, system_map=system_map
    )

    assert validated is result
