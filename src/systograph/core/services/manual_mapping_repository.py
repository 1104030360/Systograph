from __future__ import annotations

from typing import Protocol

from systograph.core.models.mapping import ManualMapping


class ManualMappingRepository(Protocol):
    def save(self, mapping: ManualMapping) -> ManualMapping: ...

    def get(self, mapping_id: str) -> ManualMapping | None: ...

    def list_for_project(self, project_id: str) -> list[ManualMapping]: ...


class InMemoryManualMappingRepository:
    def __init__(self) -> None:
        self._items: dict[str, ManualMapping] = {}

    def save(self, mapping: ManualMapping) -> ManualMapping:
        self._items[mapping.mapping_id] = mapping
        return mapping

    def get(self, mapping_id: str) -> ManualMapping | None:
        return self._items.get(mapping_id)

    def list_for_project(self, project_id: str) -> list[ManualMapping]:
        return sorted(
            [
                mapping
                for mapping in self._items.values()
                if mapping.project_id == project_id
            ],
            key=lambda item: item.created_at,
        )
