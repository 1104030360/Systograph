from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from systograph.core.services.ua_sidecar_projection import (
    project_structure_rows,
)
from systograph.core.services.ua_sidecar_runtime import UaAnalysisError
from systograph.core.services.ua_sidecar_script_models import UaStructureFile


def dockerfile_row(**service_overrides: Any) -> UaStructureFile:
    # The service payload mirrors what the UA Dockerfile parser actually
    # emits for a FROM stage: no "kind" field.
    return UaStructureFile.model_validate(
        {
            "path": "Dockerfile",
            "services": [
                {
                    "name": "python",
                    "image": "python:3.13",
                    "ports": [],
                    "startLine": 1,
                    "endLine": 2,
                    **service_overrides,
                }
            ],
        }
    )


def test_service_without_kind_validates_and_projects_service_kind() -> None:
    # Given: a Dockerfile stage exactly as the upstream parser emits it.
    row = dockerfile_row()

    # When
    _, _, resources, _, warnings = project_structure_rows(
        (row,), {"Dockerfile": 2}
    )

    # Then: the projection supplies Systograph's own kind value.
    assert [
        (item.kind, item.name, item.line_start, item.line_end)
        for item in resources
    ] == [("service", "python", 1, 2)]
    assert warnings == ()


def test_terraform_resource_without_kind_is_rejected() -> None:
    # Given/When/Then: resources[] keeps its required kind — a Terraform
    # row without one is not acceptable input.
    with pytest.raises(ValidationError):
        UaStructureFile.model_validate(
            {
                "path": "main.tf",
                "resources": [{"name": "bucket", "startLine": 1}],
            }
        )


def test_service_end_one_past_eof_is_clamped_with_warning() -> None:
    # Given: the known upstream artifact — the last stage of a
    # trailing-newline Dockerfile ends one line past the file.
    row = dockerfile_row(endLine=3)

    # When
    _, _, resources, _, warnings = project_structure_rows(
        (row,), {"Dockerfile": 2}
    )

    # Then: the end line is clamped to the file and the correction is
    # recorded, never silent.
    assert [item.line_end for item in resources] == [2]
    assert len(warnings) == 1
    assert warnings[0].stage == "structure_projection"
    assert "Dockerfile" in warnings[0].message


def test_service_end_two_past_eof_still_fails_closed() -> None:
    # Given: an end line that does not match the known +1 signature.
    row = dockerfile_row(endLine=4)

    # When/Then
    with pytest.raises(UaAnalysisError) as excinfo:
        project_structure_rows((row,), {"Dockerfile": 2})
    assert excinfo.value.code == "ua_line_invalid"


def test_resource_end_one_past_eof_is_not_clamped() -> None:
    # Given: the clamp is scoped to services — a Terraform resource with
    # an out-of-bounds end line is not the proven upstream artifact.
    row = UaStructureFile.model_validate(
        {
            "path": "main.tf",
            "resources": [
                {
                    "name": "bucket",
                    "kind": "aws_s3_bucket",
                    "startLine": 1,
                    "endLine": 3,
                }
            ],
        }
    )

    # When/Then
    with pytest.raises(UaAnalysisError) as excinfo:
        project_structure_rows((row,), {"main.tf": 2})
    assert excinfo.value.code == "ua_line_invalid"
