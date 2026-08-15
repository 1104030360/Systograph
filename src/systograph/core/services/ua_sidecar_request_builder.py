from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from systograph.core.models.filesystem import FileInventory
from systograph.core.models.ua_analysis import (
    UaAnalysisRequest,
    UaAnalysisRequestFile,
    UaWorkDirectory,
)
from systograph.core.services.ua_sidecar_runtime import UaAnalysisError


class UaRequestBuilder:
    def build(
        self,
        root: Path,
        inventory: FileInventory,
    ) -> UaAnalysisRequest:
        try:
            if Path(inventory.project_root).resolve() != root:
                raise ValueError("Inventory project root does not match")
            if inventory.final_inventory_digest is None:
                raise ValueError("Final inventory digest is required")
            files = tuple(
                UaAnalysisRequestFile(
                    path=item.path,
                    language=item.language,
                    size_lines=item.size_lines,
                    file_category=item.file_category,
                    digest=self._required_digest(item.content_fingerprint),
                )
                for item in inventory.files
            )
            return UaAnalysisRequest(
                schema_version="systograph-ua-request/v1",
                project_root=str(root),
                inventory_digest=inventory.final_inventory_digest,
                work_dir=UaWorkDirectory(
                    location="system_temporary_directory",
                    cleanup="after_analysis",
                ),
                files=files,
            )
        except (OSError, ValueError, ValidationError) as exc:
            raise UaAnalysisError(
                "ua_request_invalid",
                "Approved inventory cannot form a valid UA request",
            ) from exc

    def import_input(self, request: UaAnalysisRequest) -> dict[str, object]:
        return {
            "projectRoot": request.project_root,
            "files": self.script_files(request),
        }

    def script_files(
        self,
        request: UaAnalysisRequest,
    ) -> list[dict[str, object]]:
        return [
            {
                "path": item.path,
                "language": item.language,
                "fileCategory": item.file_category.value,
                "sizeLines": item.size_lines,
            }
            for item in request.files
        ]

    def _required_digest(self, value: str | None) -> str:
        if value is None:
            raise ValueError("Content fingerprint is required")
        return value


def write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
