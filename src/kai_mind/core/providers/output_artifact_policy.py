from __future__ import annotations

import os
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

from kai_mind.core.models.errors import (
    PreconditionError,
    PreconditionFailureReason,
)
from kai_mind.core.models.scan import OutputRun, PreconditionResult

Clock = Callable[[], datetime]

ARTIFACT_FILENAMES: Final = (
    "ai_system_map.json",
    "profile_signals.json",
    "readiness_report.json",
    "call_graph.json",
    "dataflow_hints.json",
    "execution_paths.json",
    "evidence_table.json",
    "ai_system_map.md",
    "system_map.mmd",
    "execution_map.mmd",
    "map-error.md",
)


class OutputArtifactPolicy:
    def __init__(self, clock: Clock | None = None) -> None:
        self._clock = clock or self._default_clock

    def check_preconditions(
        self,
        *,
        project_path: Path,
        output_dir: Path,
    ) -> PreconditionResult:
        output_error = self._validate_output_dir(output_dir)
        if output_error is not None:
            return PreconditionResult(ok=False, error=output_error)
        output_run = self.prepare_output_run(output_dir)
        project_error = self._validate_project_path(project_path)
        if project_error is not None:
            return PreconditionResult(
                ok=False,
                output_run=output_run,
                error=project_error,
            )
        return PreconditionResult(
            ok=True,
            project_root=project_path.resolve(),
            output_run=output_run,
        )

    def prepare_output_run(self, output_dir: Path) -> OutputRun:
        return OutputRun(root_dir=self.prepare_output_run_dir(output_dir))

    def prepare_output_run_dir(self, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        if not self._has_existing_artifact(output_dir):
            return output_dir.resolve()
        run_dir = self._unique_timestamped_run_dir(output_dir)
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir.resolve()

    @staticmethod
    def _validate_project_path(
        project_path: Path,
    ) -> PreconditionError | None:
        if not project_path.exists():
            return OutputArtifactPolicy._project_error(
                project_path,
                PreconditionFailureReason.PROJECT_PATH_NOT_FOUND,
            )
        if not project_path.is_dir():
            return OutputArtifactPolicy._project_error(
                project_path,
                PreconditionFailureReason.PROJECT_PATH_NOT_DIRECTORY,
            )
        if not os.access(project_path, os.R_OK | os.X_OK):
            return OutputArtifactPolicy._project_error(
                project_path,
                PreconditionFailureReason.PROJECT_PATH_NOT_READABLE,
            )
        return None

    @staticmethod
    def _validate_output_dir(output_dir: Path) -> PreconditionError | None:
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            return OutputArtifactPolicy._project_error(
                output_dir,
                PreconditionFailureReason.OUTPUT_DIRECTORY_NOT_WRITABLE,
            )
        if not os.access(output_dir, os.W_OK | os.X_OK):
            return OutputArtifactPolicy._project_error(
                output_dir,
                PreconditionFailureReason.OUTPUT_DIRECTORY_NOT_WRITABLE,
            )
        return None

    @staticmethod
    def _project_error(
        path: Path,
        reason: PreconditionFailureReason,
    ) -> PreconditionError:
        return PreconditionError(
            project_path=str(path),
            failure_reason=reason,
        )

    @staticmethod
    def _has_existing_artifact(output_dir: Path) -> bool:
        return any((output_dir / name).exists() for name in ARTIFACT_FILENAMES)

    def _unique_timestamped_run_dir(self, output_dir: Path) -> Path:
        timestamp = self._clock().strftime("%Y%m%dT%H%M%S")
        run_dir = output_dir / timestamp
        if not run_dir.exists():
            return run_dir
        suffix = 1
        while True:
            suffixed_run_dir = output_dir / f"{timestamp}-{suffix}"
            if not suffixed_run_dir.exists():
                return suffixed_run_dir
            suffix += 1

    @staticmethod
    def _default_clock() -> datetime:
        return datetime.now(UTC)
