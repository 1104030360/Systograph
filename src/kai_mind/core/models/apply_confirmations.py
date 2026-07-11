from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from kai_mind.core.models.map_build import MapBuildResult
from kai_mind.core.models.viewer import ViewerLoadResult


class ApplyConfirmationsResult(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        extra="forbid",
        frozen=True,
    )

    project_id: str
    scan_id: str
    build_id: str
    based_on_build_id: str
    build_reason: Literal["apply_confirmations"] = "apply_confirmations"
    applied_mapping_ids: tuple[str, ...]
    build_result: MapBuildResult
    viewer_load_result: ViewerLoadResult
