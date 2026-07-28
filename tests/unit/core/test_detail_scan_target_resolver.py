from __future__ import annotations

from pathlib import Path

import pytest

from systograph.core.models.ai_system_map_v2 import AiSystemMapV2
from systograph.core.models.system_map import RagSystemMap
from systograph.core.services.detail_scan_target_resolver import (
    DetailScanTargetError,
    DetailScanTargetResolver,
)
from systograph.core.services.system_map_index import SystemMapIndex
from systograph.core.services.system_map_v1_to_v2_adapter import (
    SystemMapV1ToV2Adapter,
)

RICH_MAP = (
    Path(__file__).parents[2]
    / "fixtures"
    / "ai_system_map"
    / "valid_rich_frontend_sample.v1.json"
)


@pytest.fixture(params=["v1-adapted", "v2-native"])
def canonical_map(request: pytest.FixtureRequest) -> AiSystemMapV2:
    legacy = RagSystemMap.model_validate_json(
        RICH_MAP.read_text(encoding="utf-8")
    )
    adapted = SystemMapV1ToV2Adapter().adapt_to_canonical(legacy)
    if request.param == "v1-adapted":
        return adapted
    return AiSystemMapV2.model_validate(adapted.model_dump(mode="json"))


def test_resolves_canonical_targets_and_related_files_in_evidence_order(
    canonical_map: AiSystemMapV2,
) -> None:
    index = SystemMapIndex.from_map(canonical_map)
    resolver = DetailScanTargetResolver(index)
    component = next(
        item for item in canonical_map.components if item.evidence_ids
    )
    edge = next(item for item in canonical_map.edges if item.evidence_ids)
    unmapped = canonical_map.unmapped_components[0]
    evidence = canonical_map.evidence[0]

    component_target = resolver.resolve(
        "component_instance", component.component_id
    )
    edge_target = resolver.resolve("edge", edge.edge_id)
    unmapped_target = resolver.resolve(
        "unmapped_component", unmapped.unmapped_id
    )
    evidence_target = resolver.resolve("evidence", evidence.evidence_id)

    assert component_target.target == component.component_id
    assert edge_target.target == edge.edge_id
    assert unmapped_target.target == unmapped.unmapped_id
    assert evidence_target.target == evidence.evidence_id
    assert component_target.related_files == list(
        dict.fromkeys(
            location.path
            for location in index.related_locations_for_evidence_ids(
                component.evidence_ids
            )
            if location.path is not None
        )
    )


def test_rejects_unknown_target_without_mutating_map(
    canonical_map: AiSystemMapV2,
) -> None:
    original = canonical_map.model_copy(deep=True)
    resolver = DetailScanTargetResolver(SystemMapIndex.from_map(canonical_map))

    with pytest.raises(DetailScanTargetError, match="target_not_found"):
        resolver.resolve("component_instance", "component:missing")

    assert canonical_map == original


def test_rejects_legacy_aliases_at_generic_resolver_boundary(
    canonical_map: AiSystemMapV2,
) -> None:
    resolver = DetailScanTargetResolver(SystemMapIndex.from_map(canonical_map))

    with pytest.raises(
        DetailScanTargetError, match="target_type_not_supported"
    ):
        resolver.resolve("component_slot", "retriever")
    with pytest.raises(
        DetailScanTargetError, match="target_type_not_supported"
    ):
        resolver.resolve("extension", "extension:reranker")
