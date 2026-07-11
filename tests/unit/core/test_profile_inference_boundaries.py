from __future__ import annotations

import ast
import json
from pathlib import Path

from kai_mind.core.models.ai_system_map_v2 import (
    AiSystemMapV2,
    CanonicalRiskHint,
    CanonicalUnmappedComponent,
)
from kai_mind.core.services.canonical_map_loader import CanonicalMapLoader
from kai_mind.core.services.profile_inference_service import (
    ProfileInferenceService,
)
from kai_mind.web.app import create_app

PROFILE_MODULES = (
    Path("src/kai_mind/core/services/profile_inference_service.py"),
    Path("src/kai_mind/core/services/profile_finding_service.py"),
    Path("src/kai_mind/core/services/profile_signal_validation_service.py"),
    Path(
        "src/kai_mind/core/services/reference_capability_assessment_service.py"
    ),
)
FORBIDDEN_IMPORT_PREFIXES = (
    "kai_mind.core.services.manual_mapping",
    "kai_mind.core.services.mapping_proposal",
    "kai_mind.web",
)
FIXTURE = Path("tests/fixtures/ai_system_map/v2/non_grounded_llm_app.v2.json")


def load_map() -> AiSystemMapV2:
    return (
        CanonicalMapLoader()
        .load(json.loads(FIXTURE.read_text(encoding="utf-8")))
        .normalized
    )


def test_profile_modules_do_not_depend_on_mutation_lifecycles() -> None:
    imported_modules: set[str] = set()
    for path in PROFILE_MODULES:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.add(node.module)
            elif isinstance(node, ast.Import):
                imported_modules.update(alias.name for alias in node.names)

    assert not any(
        module.startswith(prefix)
        for module in imported_modules
        for prefix in FORBIDDEN_IMPORT_PREFIXES
    )


def test_unmapped_and_risk_hints_cannot_promote_profiles() -> None:
    system_map = load_map()
    evidence_id = system_map.evidence[0].evidence_id
    weak_only = system_map.model_copy(
        update={
            "unmapped_components": [
                CanonicalUnmappedComponent(
                    unmapped_id="unmapped:reranker-name",
                    observed_kind="reranker",
                    status="needs_confirmation",
                    reason="Name-only reranker signal.",
                    source_file="src/config.py",
                    evidence_ids=[evidence_id],
                )
            ],
            "risk_hints": [
                CanonicalRiskHint(
                    risk_id="risk:agent-name",
                    type="agentic_name_only",
                    target="unmapped:reranker-name",
                    target_type="evidence",
                    evidence_id=evidence_id,
                    rule_id="name_only",
                    rationale="A name is not control-flow proof.",
                )
            ],
        }
    )

    result = ProfileInferenceService().infer(
        weak_only,
        build_id="build:weak-only",
        scan_id="scan:weak-only",
        environment_id=weak_only.environment_id,
    )
    profiles = {item.profile_id: item for item in result.profiles}

    assert profiles["reranking"].status == "undetermined"
    assert profiles["reranking"].related_unmapped_component_ids == (
        "unmapped:reranker-name",
    )
    assert profiles["reranking"].related_risk_hint_ids == ("risk:agent-name",)
    assert profiles["agentic-control"].status == "undetermined"


def test_web_contract_has_no_profile_mutation_route(tmp_path: Path) -> None:
    app = create_app(state_dir=tmp_path / "state")
    mutation_routes = [
        route.path
        for route in app.routes
        if "profile" in route.path.lower()
        and set(route.methods or ()) & {"POST", "PUT", "PATCH", "DELETE"}
    ]

    assert mutation_routes == []
