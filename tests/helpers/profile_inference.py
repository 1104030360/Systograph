from __future__ import annotations

import json
from pathlib import Path

from kai_mind.core.models.ai_system_map_v2 import (
    AiSystemMapV2,
    CanonicalComponent,
    CanonicalEdge,
    CanonicalEvidence,
    CanonicalEvidenceLocation,
)
from kai_mind.core.models.profile_signal import ProfileInferenceResult
from kai_mind.core.services.canonical_map_loader import CanonicalMapLoader
from kai_mind.core.services.profile_inference_service import (
    ProfileInferenceService,
)

FIXTURE_DIR = Path(__file__).parents[1] / "fixtures/ai_system_map/v2"


def load_profile_map(name: str) -> AiSystemMapV2:
    payload = json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))
    return CanonicalMapLoader().load(payload).normalized


def infer_profile_fixture(name: str) -> ProfileInferenceResult:
    system_map = load_profile_map(name)
    return ProfileInferenceService().infer(
        system_map,
        build_id=system_map.build_id or "build:test",
        scan_id=system_map.scan_id or "scan:test",
        environment_id=system_map.environment_id,
    )


def map_with_profile_signals(
    component_types: tuple[str, ...],
    *,
    relationship: str | None = None,
    explicit_negative_nodes: tuple[str, ...] = (),
) -> AiSystemMapV2:
    base = load_profile_map("non_grounded_llm_app.v2.json")
    evidence = [
        CanonicalEvidence(
            evidence_id=f"evidence:{component_type}:{index}",
            artifact_type="python",
            evidence_kind="direct",
            location=CanonicalEvidenceLocation(
                path=f"src/{component_type}.py",
                start_line=1,
            ),
            rule_id=f"test.{component_type}",
        )
        for index, component_type in enumerate(component_types)
    ]
    components = [
        CanonicalComponent(
            component_id=f"component:{component_type}:{index}",
            display_name=component_type.replace("_", " ").title(),
            canonical_type=component_type,
            layer="undetermined",
            status="detected",
            activation="enabled",
            evidence_ids=[evidence[index].evidence_id],
            metadata={},
        )
        for index, component_type in enumerate(component_types)
    ]
    negative_evidence = [
        CanonicalEvidence(
            evidence_id=f"evidence:coverage:{node_id}",
            artifact_type="coverage",
            evidence_kind="explicit_negative",
            location=CanonicalEvidenceLocation(),
            rule_id=f"coverage.reference.{node_id}",
        )
        for node_id in explicit_negative_nodes
    ]
    edges = []
    if relationship is not None and components:
        edges.append(
            CanonicalEdge(
                edge_id=f"edge:{relationship}",
                source=components[0].component_id,
                target=components[-1].component_id,
                relationship=relationship,
                status="observed",
                evidence_ids=[evidence[0].evidence_id],
            )
        )
    return base.model_copy(
        update={
            "components": components,
            "edges": edges,
            "evidence": [*evidence, *negative_evidence],
            "risk_hints": [],
            "unmapped_components": [],
        }
    )
