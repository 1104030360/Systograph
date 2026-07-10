"""Unit tests for opt-in v2 map build contract selection."""

from __future__ import annotations

from pathlib import Path

from kai_mind.core.models.errors import (
    PreconditionError,
    PreconditionFailureReason,
)
from kai_mind.core.models.map_build import MapBuildRequest, MapBuildResult
from kai_mind.core.models.scan import PreconditionResult
from kai_mind.core.providers.output_artifact_provider import (
    OutputArtifactProvider,
)
from kai_mind.core.services.map_build_service import MapBuildService


def test_map_build_request_defaults_to_v1_active_schema() -> None:
    request = MapBuildRequest(project_path=Path("sample"))

    assert request.system_map_schema_version == "ai-system-map/v1"


def test_map_build_request_accepts_explicit_v2_opt_in() -> None:
    request = MapBuildRequest(
        project_path=Path("sample"),
        system_map_schema_version="ai-system-map/v2",
    )

    assert request.system_map_schema_version == "ai-system-map/v2"


def test_map_build_result_exposes_active_schema_and_migration_warnings() -> (
    None
):
    result = MapBuildResult(
        status="ok",
        project_name="sample",
        active_schema_version="ai-system-map/v1",
        requested_schema_version="ai-system-map/v2",
        migration_warnings=[
            "active_output_remains_v1_until_plan_13",
        ],
    )

    assert result.active_schema_version == "ai-system-map/v1"
    assert result.requested_schema_version == "ai-system-map/v2"
    assert (
        "active_output_remains_v1_until_plan_13" in result.migration_warnings
    )


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
    assert result.active_schema_version == "ai-system-map/v1"
