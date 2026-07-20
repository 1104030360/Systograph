"""Prepare output directories and write scanner artifact files."""

from __future__ import annotations

import json
import os
from pathlib import Path

from pydantic import BaseModel

from kai_mind.core.models.errors import PreconditionError
from kai_mind.core.models.scan import OutputRun, PreconditionResult
from kai_mind.core.providers.output_artifact_policy import (
    Clock,
    OutputArtifactPolicy,
)


class OutputArtifactProvider:
    """Own output artifact policy for map builds."""

    def __init__(self, clock: Clock | None = None) -> None:
        self._policy = OutputArtifactPolicy(clock)

    def check_preconditions(
        self,
        *,
        project_path: Path,
        output_dir: Path,
    ) -> PreconditionResult:
        return self._policy.check_preconditions(
            project_path=project_path,
            output_dir=output_dir,
        )

    def prepare_output_run(self, output_dir: Path) -> OutputRun:
        return self._policy.prepare_output_run(output_dir)

    def prepare_output_run_dir(self, output_dir: Path) -> Path:
        return self._policy.prepare_output_run_dir(output_dir)

    def write_map_error(
        self,
        error: PreconditionError,
        *,
        output_run: OutputRun,
    ) -> Path:
        output_run.root_dir.mkdir(parents=True, exist_ok=True)
        error_path = output_run.map_error_path
        return self._write_text_atomic(
            error_path,
            self._render_map_error(error),
        )

    def write_json(
        self,
        system_map: BaseModel,
        *,
        output_run: OutputRun,
    ) -> Path:
        output_run.root_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = output_run.map_json_path
        serialized = (
            json.dumps(
                system_map.model_dump(mode="json"),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
        return self._write_text_atomic(artifact_path, serialized)

    def write_markdown(
        self,
        markdown: str,
        *,
        output_run: OutputRun,
    ) -> Path:
        output_run.root_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = output_run.map_markdown_path
        return self._write_text_atomic(artifact_path, markdown)

    def write_profile_signals(
        self,
        result: BaseModel,
        *,
        output_run: OutputRun,
    ) -> Path:
        return self._write_model_json(
            result,
            output_run.profile_signals_path,
        )

    def write_readiness_report(
        self,
        report: BaseModel,
        *,
        output_run: OutputRun,
    ) -> Path:
        return self._write_model_json(
            report,
            output_run.readiness_report_path,
        )

    def write_call_graph(
        self,
        artifact: BaseModel,
        *,
        output_run: OutputRun,
    ) -> Path:
        return self._write_model_json(artifact, output_run.call_graph_path)

    def write_dataflow_hints(
        self,
        artifact: BaseModel,
        *,
        output_run: OutputRun,
    ) -> Path:
        return self._write_model_json(
            artifact,
            output_run.dataflow_hints_path,
        )

    def write_execution_paths(
        self,
        artifact: BaseModel,
        *,
        output_run: OutputRun,
    ) -> Path:
        return self._write_model_json(
            artifact,
            output_run.execution_paths_path,
        )

    def write_evidence_table(
        self,
        artifact: BaseModel,
        *,
        output_run: OutputRun,
    ) -> Path:
        return self._write_model_json(
            artifact,
            output_run.evidence_table_path,
        )

    def write_system_map_mermaid(
        self,
        mermaid: str,
        *,
        output_run: OutputRun,
    ) -> Path:
        return self._write_text_atomic(
            output_run.system_map_mermaid_path,
            mermaid,
        )

    def write_execution_map_mermaid(
        self,
        mermaid: str,
        *,
        output_run: OutputRun,
    ) -> Path:
        return self._write_text_atomic(
            output_run.execution_map_mermaid_path,
            mermaid,
        )

    def _write_model_json(self, model: BaseModel, path: Path) -> Path:
        serialized = (
            json.dumps(
                model.model_dump(mode="json"),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
        return self._write_text_atomic(path, serialized)

    def _write_text_atomic(self, path: Path, content: str) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.tmp")
        with temporary.open("w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        return path

    def _render_map_error(self, error: PreconditionError) -> str:
        return "\n".join(
            [
                "# KAI-Mind Map Build Failed",
                "",
                f"scan_stage: {error.scan_stage}",
                f"project_path: {error.project_path}",
                f"failure_reason: {error.failure_reason.value}",
                "",
            ]
        )
