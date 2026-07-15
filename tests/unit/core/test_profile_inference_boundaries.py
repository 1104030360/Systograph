from __future__ import annotations

import ast
import json
from collections import deque
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Final, TypeAlias

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

SOURCE_ROOT: Final = Path("src")
PROFILE_SERVICE_ROOT: Final = SOURCE_ROOT / "kai_mind/core/services"
PROFILE_MODEL_ROOT: Final = SOURCE_ROOT / "kai_mind/core/models"
REFERENCE_ASSESSMENT_MODULE: Final = (
    "kai_mind.core.services.reference_capability_assessment_service"
)
FORBIDDEN_IMPORT_PREFIXES: Final = (
    "kai_mind.core.services.manual_mapping",
    "kai_mind.core.services.mapping_proposal",
    "kai_mind.core.services.llm_proposal_config_loader",
    "kai_mind.core.providers.llm_proposal_provider",
    "kai_mind.web",
)
FIXTURE: Final = Path(
    "tests/fixtures/ai_system_map/v2/non_grounded_llm_app.v2.json"
)
ImportGraph: TypeAlias = Mapping[str, Sequence[str]]


def _module_name(path: Path) -> str:
    relative = path.with_suffix("").relative_to(SOURCE_ROOT)
    parts = (
        relative.parts[:-1] if relative.name == "__init__" else relative.parts
    )
    return ".".join(parts)


def _profile_module_names() -> tuple[str, ...]:
    modules = {
        _module_name(path) for path in PROFILE_SERVICE_ROOT.glob("profile*.py")
    }
    modules.update(
        _module_name(path) for path in PROFILE_MODEL_ROOT.glob("profile*.py")
    )
    modules.add(REFERENCE_ASSESSMENT_MODULE)
    return tuple(sorted(modules))


def _imported_modules(path: Path, module_name: str) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    package_parts = module_name.split(".")
    if path.name != "__init__.py":
        package_parts = package_parts[:-1]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
            continue
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.level == 0:
            if node.module:
                imports.add(node.module)
            continue
        parent_count = node.level - 1
        base_parts = (
            package_parts[:-parent_count] if parent_count else package_parts
        )
        if node.module:
            imports.add(".".join((*base_parts, *node.module.split("."))))
        else:
            imports.update(
                ".".join((*base_parts, alias.name.split(".")[0]))
                for alias in node.names
            )
    return tuple(sorted(imports))


def _repo_import_graph() -> dict[str, tuple[str, ...]]:
    return {
        _module_name(path): _imported_modules(path, _module_name(path))
        for path in SOURCE_ROOT.joinpath("kai_mind").rglob("*.py")
    }


def _find_forbidden_import_chain(
    start: str,
    graph: ImportGraph,
) -> tuple[str, ...] | None:
    queue: deque[tuple[str, tuple[str, ...]]] = deque(((start, (start,)),))
    visited = {start}
    while queue:
        current, chain = queue.popleft()
        for imported in sorted(graph.get(current, ())):
            next_chain = (*chain, imported)
            if any(
                imported.startswith(prefix)
                for prefix in FORBIDDEN_IMPORT_PREFIXES
            ):
                return next_chain
            if imported in graph and imported not in visited:
                visited.add(imported)
                queue.append((imported, next_chain))
    return None


def load_map() -> AiSystemMapV2:
    return (
        CanonicalMapLoader()
        .load(json.loads(FIXTURE.read_text(encoding="utf-8")))
        .normalized
    )


def test_profile_modules_do_not_depend_on_mutation_lifecycles() -> None:
    # Given: the repository import graph and every profile-owned module.
    graph = _repo_import_graph()

    # When: each module is traced through direct and indirect imports.
    chains = tuple(
        chain
        for module in _profile_module_names()
        if (chain := _find_forbidden_import_chain(module, graph)) is not None
    )

    # Then: no profile path reaches a mutation, proposal, LLM, or web owner.
    assert not chains, "forbidden profile import chains:\n" + "\n".join(
        " -> ".join(chain) for chain in chains
    )


def test_profile_dependency_guard_discovers_profile_modules() -> None:
    # Given: every current profile-prefixed service source file.
    expected = {
        _module_name(path) for path in PROFILE_SERVICE_ROOT.glob("profile*.py")
    }
    expected.update(
        _module_name(path) for path in PROFILE_MODEL_ROOT.glob("profile*.py")
    )
    expected.add(REFERENCE_ASSESSMENT_MODULE)

    # When / Then: discovery returns the exact profile ownership surface.
    assert set(_profile_module_names()) == expected


def test_profile_dependency_guard_includes_projection_models() -> None:
    # Given: the read-only profile registry projection model.
    projection_module = "kai_mind.core.models.profile_registry_projection"

    # When / Then: profile boundary discovery includes the model layer.
    assert projection_module in _profile_module_names()


def test_profile_dependency_guard_reports_transitive_import_chain() -> None:
    # Given: a profile module that reaches a forbidden owner indirectly.
    graph = {
        "kai_mind.core.services.profile_demo": (
            "kai_mind.core.services.safe_bridge",
        ),
        "kai_mind.core.services.safe_bridge": (
            "kai_mind.core.services.mapping_proposal_service",
        ),
    }

    # When: the dependency guard traces the profile module.
    chain = _find_forbidden_import_chain(
        "kai_mind.core.services.profile_demo",
        graph,
    )

    # Then: the full shortest import chain identifies the boundary violation.
    assert chain == (
        "kai_mind.core.services.profile_demo",
        "kai_mind.core.services.safe_bridge",
        "kai_mind.core.services.mapping_proposal_service",
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
