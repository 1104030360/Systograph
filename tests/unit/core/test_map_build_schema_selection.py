from __future__ import annotations

from pathlib import Path

from systograph.core.models.errors import (
    PreconditionError,
    PreconditionFailureReason,
)
from systograph.core.models.map_build import MapBuildRequest, MapBuildResult
from systograph.core.models.scan import PreconditionResult
from systograph.core.providers.output_artifact_provider import (
    OutputArtifactProvider,
)
from systograph.core.services.map_build_service import MapBuildService


def test_map_build_request_defaults_to_v2_active_schema() -> None:
    request = MapBuildRequest(project_path=Path("sample"))

    assert request.system_map_schema_version == "ai-system-map/v2"


def test_map_build_request_accepts_explicit_v2_opt_in() -> None:
    request = MapBuildRequest(
        project_path=Path("sample"),
        system_map_schema_version="ai-system-map/v2",
    )

    assert request.system_map_schema_version == "ai-system-map/v2"


def test_map_build_result_exposes_schema_provenance_metadata() -> None:
    """A v1-sourced map keeps its provenance without a rollback build.

    Given a build that migrated a historical v1 artifact,
    When the result reports its schema metadata,
    Then the active output stays v2 while source_schema_version still
    records v1, and operator_rollback_active is False because the v1
    write path no longer exists.
    """
    # Given / When
    result = MapBuildResult(
        status="ok",
        project_name="sample",
        active_schema_version="ai-system-map/v2",
        requested_schema_version="ai-system-map/v2",
        source_schema_version="ai-system-map/v1",
    )

    # Then
    assert result.active_schema_version == "ai-system-map/v2"
    assert result.requested_schema_version == "ai-system-map/v2"
    assert result.source_schema_version == "ai-system-map/v1"
    assert result.operator_rollback_active is False


class _FailingPreconditionProvider(OutputArtifactProvider):
    def check_preconditions(
        self,
        *,
        project_path: Path,
        output_dir: Path,
    ) -> PreconditionResult:
        return PreconditionResult(
            ok=False,
            project_root=None,
            output_run=None,
            error=PreconditionError(
                project_path=str(project_path),
                failure_reason=PreconditionFailureReason.PROJECT_PATH_NOT_FOUND,
            ),
        )


def test_precondition_error_preserves_requested_schema_version(
    tmp_path: Path,
) -> None:
    result = MapBuildService(
        output_artifact_provider=_FailingPreconditionProvider(),
    ).build(
        MapBuildRequest(
            project_path=tmp_path / "missing",
            output=tmp_path / "outputs",
            system_map_schema_version="ai-system-map/v2",
        )
    )

    assert result.status == "error"
    assert result.requested_schema_version == "ai-system-map/v2"
    assert result.active_schema_version == "ai-system-map/v2"
