from __future__ import annotations

from collections.abc import Mapping
from typing import Final, TypeAlias

import pytest
from tests.helpers.profile_inference import (
    infer_profile_fixture,
    load_profile_map,
)

from kai_mind.core.models.profile_signal import (
    EvidenceStrength,
    ImplementationDepthLevel,
    ProfileStatus,
)
from kai_mind.core.services.profile_finding_service import (
    ProfileFindingService,
)
from kai_mind.core.services.profile_inference_service import (
    MVP_CAPABILITY_PROFILE_IDS,
    ProfileInferenceService,
)
from kai_mind.core.services.profile_registry_loader import (
    ProfileMetadataCoverageError,
    ProfileRegistryLoader,
)

ProfileSummary: TypeAlias = tuple[
    ProfileStatus,
    ImplementationDepthLevel,
    EvidenceStrength,
]
DEFAULT_PROFILE_SUMMARY: Final[ProfileSummary] = (
    "undetermined",
    0,
    "weak_or_ambiguous_signal",
)


@pytest.mark.parametrize(
    ("fixture_name", "overrides"),
    [
        (
            "grounded_rag.v2.json",
            {
                "rag-grounding": (
                    "detected",
                    3,
                    "static_multiple_signals",
                ),
                "agentic-control": (
                    "undetermined",
                    0,
                    "static_single_signal",
                ),
            },
        ),
        (
            "non_grounded_llm_app.v2.json",
            {
                "rag-grounding": (
                    "undetermined",
                    0,
                    "static_single_signal",
                ),
                "agentic-control": (
                    "undetermined",
                    0,
                    "static_single_signal",
                ),
            },
        ),
        (
            "tool_using_agent.v2.json",
            {
                "rag-grounding": (
                    "undetermined",
                    0,
                    "static_single_signal",
                ),
                "agentic-control": (
                    "detected",
                    3,
                    "static_multiple_signals",
                ),
                "tool-calling": (
                    "detected",
                    3,
                    "static_multiple_signals",
                ),
                "self-reflection": (
                    "undetermined",
                    0,
                    "static_single_signal",
                ),
            },
        ),
        (
            "workflow_graph.v2.json",
            {
                "workflow-orchestration": (
                    "detected",
                    3,
                    "static_multiple_signals",
                ),
                "modular-composition": (
                    "partial",
                    2,
                    "static_single_signal",
                ),
            },
        ),
    ],
)
def test_profile_fixture_semantics_are_stable(
    fixture_name: str,
    overrides: Mapping[str, ProfileSummary],
) -> None:
    # Given: the established semantic summary for one v2 fixture.
    expected = tuple(
        overrides.get(profile_id, DEFAULT_PROFILE_SUMMARY)
        for profile_id in MVP_CAPABILITY_PROFILE_IDS
    )

    # When: profile inference runs through the current deterministic path.
    result = infer_profile_fixture(fixture_name)

    # Then: order, status, depth, and evidence strength remain unchanged.
    assert tuple(item.profile_id for item in result.profiles) == (
        MVP_CAPABILITY_PROFILE_IDS
    )
    assert (
        tuple(
            (
                item.status,
                item.implementation_depth_level,
                item.evidence_strength,
            )
            for item in result.profiles
        )
        == expected
    )


def test_custom_profile_metadata_changes_presentation_only() -> None:
    # Given: the packaged registry with custom wording for one profile.
    registry = ProfileRegistryLoader().load_default()
    original = registry.profiles[0]
    customized = original.model_copy(
        update={
            "display_name": "Grounding Readiness",
            "description": "Custom presentation description.",
            "default_uncertainty": "Custom runtime uncertainty.",
            "recommended_next_checks": ("Inspect runtime retrieval.",),
        }
    )
    custom_registry = registry.model_copy(
        update={"profiles": (customized, *registry.profiles[1:])}
    )
    system_map = load_profile_map("grounded_rag.v2.json")
    baseline = ProfileInferenceService().infer(
        system_map,
        build_id="build:metadata-baseline",
        scan_id="scan:metadata-baseline",
        environment_id=system_map.environment_id,
    )

    # When: inference uses an injected typed Metadata registry.
    result = ProfileInferenceService(
        finding_service=ProfileFindingService(
            metadata_registry=custom_registry,
        )
    ).infer(
        system_map,
        build_id="build:metadata-custom",
        scan_id="scan:metadata-custom",
        environment_id=system_map.environment_id,
    )

    # Then: presentation changes while deterministic semantics stay equal.
    baseline_finding = baseline.profiles[0]
    finding = result.profiles[0]
    assert finding.label == "Grounding Readiness"
    assert finding.description == "Custom presentation description."
    assert finding.uncertainty == "Custom runtime uncertainty."
    assert (
        finding.status,
        finding.implementation_depth_level,
        finding.evidence_ids,
        finding.evidence_strength,
        finding.coverage_detected,
        finding.coverage_total,
    ) == (
        baseline_finding.status,
        baseline_finding.implementation_depth_level,
        baseline_finding.evidence_ids,
        baseline_finding.evidence_strength,
        baseline_finding.coverage_detected,
        baseline_finding.coverage_total,
    )


def test_profile_finding_service_rejects_missing_metadata() -> None:
    # Given: a typed registry missing one active profile entry.
    registry = ProfileRegistryLoader().load_default()
    incomplete = registry.model_copy(
        update={"profiles": registry.profiles[:-1]}
    )

    # When / Then: service construction fails before inference can emit rows.
    with pytest.raises(
        ProfileMetadataCoverageError,
        match="coverage mismatch",
    ):
        ProfileFindingService(metadata_registry=incomplete)
