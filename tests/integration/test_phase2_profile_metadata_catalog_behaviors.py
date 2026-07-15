from __future__ import annotations

import json
from pathlib import Path

from kai_mind.core.services.canonical_map_loader import CanonicalMapLoader
from kai_mind.core.services.profile_inference_service import (
    ProfileInferenceService,
)
from kai_mind.core.services.profile_registry_loader import (
    ProfileRegistryLoader,
)

FIXTURE = Path("tests/fixtures/ai_system_map/v2/grounded_rag.v2.json")


def test_packaged_profile_metadata_enriches_deterministic_findings() -> None:
    # Given: a real v2 map fixture and the package-bundled Metadata registry.
    system_map = (
        CanonicalMapLoader()
        .load(json.loads(FIXTURE.read_text(encoding="utf-8")))
        .normalized
    )
    metadata = (
        ProfileRegistryLoader().load_default().metadata_for("rag-grounding")
    )

    # When: the default inference path derives its 15 findings.
    result = ProfileInferenceService().infer(
        system_map,
        build_id="build:profile-metadata-integration",
        scan_id="scan:profile-metadata-integration",
        environment_id=system_map.environment_id,
    )

    # Then: presentation comes from TOML without changing deterministic status.
    finding = next(
        item for item in result.profiles if item.profile_id == "rag-grounding"
    )
    assert finding.label == metadata.display_name
    assert finding.description == metadata.description
    assert finding.primary_axis == metadata.primary_axis
    assert finding.status == "detected"
    assert finding.evidence_strength == "static_multiple_signals"
