from __future__ import annotations

import inspect
from importlib.util import find_spec
from typing import Final

import pytest

from systograph.core.services.map_build_pipeline import MapBuildPipeline
from systograph.core.services.map_build_service import MapBuildService
from systograph.core.services.system_map_v2_materialization_service import (
    SystemMapV2MaterializationService,
)

# Modules that existed only to write the operator rollback v1 artifact.
# Refactor 06 deleted them; the build path must never grow them back.
REMOVED_ROLLBACK_MODULES: Final[tuple[str, ...]] = (
    "systograph.core.services.legacy_v1_rollback_service",
    "systograph.core.services.system_map_materialization_service",
    "systograph.core.services.system_map_normalize_service",
)


@pytest.mark.parametrize("module_name", REMOVED_ROLLBACK_MODULES)
def test_rollback_writer_modules_no_longer_exist(module_name: str) -> None:
    """The v1 writer graph is gone, not merely unreferenced.

    Given a module that only the operator rollback writer needed,
    When the import system is asked to locate it,
    Then nothing is found, so no caller can reach a v1 writer.
    """
    assert find_spec(module_name) is None


def test_build_wiring_exposes_no_rollback_writer_seam() -> None:
    """No injection point survives the removed write path.

    Given the build service and the build pipeline constructors,
    When their parameters are inspected,
    Then none of them accepts a rollback writer, so the v1 output mode
    cannot be reintroduced through dependency injection.
    """
    # Given / When
    parameters = set(
        inspect.signature(MapBuildService.__init__).parameters
    ) | set(inspect.signature(MapBuildPipeline.__init__).parameters)

    # Then
    assert not [name for name in parameters if "rollback" in name]


def test_default_service_materializes_through_the_v2_writer_only() -> None:
    """One build path, one materializer.

    Given a default MapBuildService,
    When its pipeline is inspected,
    Then the only materializer wired in is the active v2 writer.
    """
    # Given / When
    service = MapBuildService()

    # Then
    assert isinstance(
        service._pipeline._materialization,
        SystemMapV2MaterializationService,
    )
