from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from kai_mind.core.models.profile_signal import ProfileInferenceResult
from kai_mind.core.models.readiness_report import ReadinessReport
from kai_mind.core.models.scan import OutputRun
from kai_mind.core.models.system_map import RagSystemMap
from kai_mind.core.models.viewer import ViewerLoadResult
from kai_mind.core.providers.output_artifact_provider import (
    OutputArtifactProvider,
)
from kai_mind.core.services.markdown_summary_service import (
    MarkdownSummaryService,
)
from kai_mind.core.services.static_execution_artifact_service import (
    StaticExecutionArtifacts,
)
from kai_mind.core.services.viewer_session_service import ViewerSessionService


@dataclass(frozen=True, slots=True)
class PublishedBuildArtifacts:
    map_json_path: Path
    map_markdown_path: Path
    profile_signals_path: Path
    readiness_report_path: Path
    call_graph_path: Path
    dataflow_hints_path: Path
    execution_paths_path: Path
    evidence_table_path: Path
    system_map_mermaid_path: Path
    execution_map_mermaid_path: Path
    viewer_load_result: ViewerLoadResult


class BuildArtifactPublisher:
    def __init__(
        self,
        *,
        output_artifact_provider: OutputArtifactProvider | None = None,
        markdown_summary_service: MarkdownSummaryService | None = None,
        projection_service: ViewerSessionService | None = None,
    ) -> None:
        self.output_provider = (
            output_artifact_provider or OutputArtifactProvider()
        )
        self._markdown = markdown_summary_service or MarkdownSummaryService()
        self._projection = projection_service or ViewerSessionService()

    def publish(
        self,
        *,
        system_map: RagSystemMap,
        profile_result: ProfileInferenceResult,
        readiness_report: ReadinessReport,
        execution: StaticExecutionArtifacts,
        output_run: OutputRun,
    ) -> PublishedBuildArtifacts:
        try:
            return self._publish(
                system_map=system_map,
                profile_result=profile_result,
                readiness_report=readiness_report,
                execution=execution,
                output_run=output_run,
            )
        except Exception:
            self._discard_partial(output_run)
            raise

    def _publish(
        self,
        *,
        system_map: RagSystemMap,
        profile_result: ProfileInferenceResult,
        readiness_report: ReadinessReport,
        execution: StaticExecutionArtifacts,
        output_run: OutputRun,
    ) -> PublishedBuildArtifacts:
        map_json_path = self.output_provider.write_json(
            system_map,
            output_run=output_run,
        )
        map_markdown_path = self.output_provider.write_markdown(
            self._markdown.render(system_map),
            output_run=output_run,
        )
        profile_signals_path = self.output_provider.write_profile_signals(
            profile_result,
            output_run=output_run,
        )
        readiness_report_path = self.output_provider.write_readiness_report(
            readiness_report,
            output_run=output_run,
        )
        call_graph_path = self.output_provider.write_call_graph(
            execution.call_graph,
            output_run=output_run,
        )
        dataflow_hints_path = self.output_provider.write_dataflow_hints(
            execution.dataflow_hints,
            output_run=output_run,
        )
        execution_paths_path = self.output_provider.write_execution_paths(
            execution.execution_paths,
            output_run=output_run,
        )
        evidence_table_path = self.output_provider.write_evidence_table(
            execution.evidence_table,
            output_run=output_run,
        )
        system_map_mermaid_path = (
            self.output_provider.write_system_map_mermaid(
                execution.system_map_mermaid,
                output_run=output_run,
            )
        )
        execution_map_mermaid_path = (
            self.output_provider.write_execution_map_mermaid(
                execution.execution_map_mermaid,
                output_run=output_run,
            )
        )
        viewer = self._projection.build(
            system_map,
            map_json_path=map_json_path,
        )
        return PublishedBuildArtifacts(
            map_json_path=map_json_path,
            map_markdown_path=map_markdown_path,
            profile_signals_path=profile_signals_path,
            readiness_report_path=readiness_report_path,
            call_graph_path=call_graph_path,
            dataflow_hints_path=dataflow_hints_path,
            execution_paths_path=execution_paths_path,
            evidence_table_path=evidence_table_path,
            system_map_mermaid_path=system_map_mermaid_path,
            execution_map_mermaid_path=execution_map_mermaid_path,
            viewer_load_result=viewer,
        )

    @staticmethod
    def _discard_partial(output_run: OutputRun) -> None:
        paths = (
            output_run.map_json_path,
            output_run.map_markdown_path,
            output_run.profile_signals_path,
            output_run.readiness_report_path,
            output_run.call_graph_path,
            output_run.dataflow_hints_path,
            output_run.execution_paths_path,
            output_run.evidence_table_path,
            output_run.system_map_mermaid_path,
            output_run.execution_map_mermaid_path,
        )
        for path in paths:
            for candidate in (path, path.with_name(f".{path.name}.tmp")):
                try:
                    candidate.unlink(missing_ok=True)
                except OSError:
                    continue
        try:
            output_run.root_dir.rmdir()
        except OSError:
            pass
