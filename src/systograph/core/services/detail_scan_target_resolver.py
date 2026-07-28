from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from systograph.core.services.path_safety_service import (
    is_project_relative_posix_path,
)
from systograph.core.services.system_map_index import SystemMapIndex

CanonicalDetailTargetType = Literal[
    "component_instance",
    "unmapped_component",
    "edge",
    "evidence",
]


class DetailScanTargetError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class DetailScanTarget:
    target_type: str
    target: str
    related_files: list[str]


class DetailScanTargetResolver:
    def __init__(self, index: SystemMapIndex) -> None:
        self._index = index

    def resolve(self, target_type: str, target: str) -> DetailScanTarget:
        if target_type == "component_instance":
            component = self._index.component_by_id(target)
            evidence_ids = component.evidence_ids if component else None
        elif target_type == "unmapped_component":
            unmapped = self._index.unmapped_by_id(target)
            if unmapped is None:
                evidence_ids = None
            else:
                locations = self._index.related_locations_for_evidence_ids(
                    unmapped.evidence_ids
                )
                return DetailScanTarget(
                    target_type=target_type,
                    target=target,
                    related_files=_unique_project_files(
                        [
                            *(location.path for location in locations),
                            unmapped.source_file,
                        ]
                    ),
                )
        elif target_type == "edge":
            edge = self._index.edge_by_id(target)
            evidence_ids = edge.evidence_ids if edge else None
        elif target_type == "evidence":
            evidence = self._index.evidence_by_id(target)
            if evidence is None:
                evidence_ids = None
            else:
                return DetailScanTarget(
                    target_type=target_type,
                    target=target,
                    related_files=_unique_project_files(
                        [evidence.location.path]
                    ),
                )
        else:
            raise DetailScanTargetError("target_type_not_supported")

        if evidence_ids is None:
            raise DetailScanTargetError("target_not_found")
        return DetailScanTarget(
            target_type=target_type,
            target=target,
            related_files=_unique_project_files(
                location.path
                for location in self._index.related_locations_for_evidence_ids(
                    evidence_ids
                )
            ),
        )


def _unique_project_files(paths: Iterable[str | None]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for path in paths:
        if (
            path is None
            or not is_project_relative_posix_path(path)
            or path in seen
        ):
            continue
        seen.add(path)
        result.append(path)
    return result
