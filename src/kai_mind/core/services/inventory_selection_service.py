from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from kai_mind.core.models.scan_boundary import ScanBoundaryDecisionRequest
from kai_mind.core.services.inventory_preflight_service import (
    InventoryPreflightService,
)
from kai_mind.core.services.inventory_selection_decision_service import (
    InventorySelectionDecisionService,
)
from kai_mind.core.services.inventory_selection_materializer import (
    InventorySelectionMaterialization,
    InventorySelectionMaterializer,
)


class InventorySelectionService:
    def __init__(
        self,
        *,
        preflight_service: InventoryPreflightService | None = None,
        decision_service: InventorySelectionDecisionService | None = None,
        materializer: InventorySelectionMaterializer | None = None,
    ) -> None:
        self._preflight = preflight_service or InventoryPreflightService()
        self._decisions = (
            decision_service or InventorySelectionDecisionService()
        )
        self._materializer = materializer or InventorySelectionMaterializer()

    def select(
        self,
        *,
        project_id: str,
        project_root: Path,
        preflight_request_id: str,
        decisions: Iterable[ScanBoundaryDecisionRequest],
    ) -> InventorySelectionMaterialization:
        normalized = self._decisions.normalize(tuple(decisions))
        state = self._preflight.revalidate(
            project_id,
            project_root,
            preflight_request_id,
            normalized,
        )
        resolved = self._decisions.resolve(state, normalized)
        return self._materializer.materialize(
            project_root=project_root,
            state=state,
            decisions=resolved,
        )
