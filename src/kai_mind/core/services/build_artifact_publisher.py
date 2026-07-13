# 這個檔案負責：把一次 build 的 map / profile / readiness / execution / viewer
# 寫到 output_run 目錄，並組出 PublishedBuildArtifacts（含路徑與
# ViewerLoadResult）。
# 失敗時會清掉部分寫入的檔案，避免留下半套 artifacts。
#
# 呼叫鏈：
#   MapBuildPipeline._complete()
#     → BuildArtifactPublisher.publish(...)
#         → OutputArtifactProvider.write_*
#         → ViewerSessionService.build（→ GraphProjection）
#         → GraphMarkdownRenderer / GraphMermaidRenderer
#     → 路徑回填 MapBuildResult
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from kai_mind.core.models.ai_system_map_v2 import AiSystemMapV2
from kai_mind.core.models.profile_signal import ProfileInferenceResult
from kai_mind.core.models.readiness_report import ReadinessReport
from kai_mind.core.models.scan import OutputRun
from kai_mind.core.models.system_map import RagSystemMap
from kai_mind.core.models.viewer import ViewerLoadResult
from kai_mind.core.providers.output_artifact_provider import (
    OutputArtifactProvider,
)
from kai_mind.core.services.graph_markdown_renderer import (
    GraphMarkdownRenderer,
)
from kai_mind.core.services.graph_mermaid_renderer import (
    GraphMermaidRenderer,
)
from kai_mind.core.services.static_execution_artifact_service import (
    StaticExecutionArtifacts,
)
from kai_mind.core.services.viewer_session_service import ViewerSessionService


# 做什麼：publish 成功後的路徑集合 + viewer_load_result。
# 被誰用：MapBuildPipeline._complete 填 MapBuildResult 各 *_path。
# 自己呼叫：無；純資料。
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


# 做什麼：發佈 build artifacts 到磁碟，並產生 viewer payload。
# 被誰用：MapBuildPipeline。
# 自己呼叫：OutputArtifactProvider、ViewerSessionService、markdown/mermaid
# renderers。
class BuildArtifactPublisher:
    # 做什麼：注入寫檔 provider、renderer、viewer projection。
    # 被誰呼叫：MapBuildService.__init__。
    # 自己呼叫：預設 OutputArtifactProvider / GraphMarkdownRenderer /
    #           GraphMermaidRenderer / ViewerSessionService。
    def __init__(
        self,
        *,
        output_artifact_provider: OutputArtifactProvider | None = None,
        markdown_renderer: GraphMarkdownRenderer | None = None,
        mermaid_renderer: GraphMermaidRenderer | None = None,
        projection_service: ViewerSessionService | None = None,
    ) -> None:
        self.output_provider = (
            output_artifact_provider or OutputArtifactProvider()
        )
        self._markdown = markdown_renderer or GraphMarkdownRenderer()
        self._mermaid = mermaid_renderer or GraphMermaidRenderer()
        self._projection = projection_service or ViewerSessionService()

    # 做什麼：公開入口；失敗時 _discard_partial 再重新拋出。
    # 被誰呼叫：MapBuildPipeline._complete。
    # 自己呼叫：_publish；例外時 _discard_partial。
    def publish(
        self,
        *,
        system_map: RagSystemMap,
        normalized_system_map: AiSystemMapV2,
        profile_result: ProfileInferenceResult,
        readiness_report: ReadinessReport,
        execution: StaticExecutionArtifacts,
        output_run: OutputRun,
    ) -> PublishedBuildArtifacts:
        try:
            return self._publish(
                system_map=system_map,
                normalized_system_map=normalized_system_map,
                profile_result=profile_result,
                readiness_report=readiness_report,
                execution=execution,
                output_run=output_run,
            )
        except Exception:
            self._discard_partial(output_run)
            raise

    # 做什麼：實際寫出所有 artifacts，並用 ViewerSessionService.build 投影
    # viewer。
    # 被誰呼叫：publish()。
    # 自己呼叫：
    #   write_json(map) → ViewerSessionService.build（含 GraphProjection）
    #   write_markdown / profile / readiness / call_graph / dataflow /
    #   execution_paths / evidence_table / mermaid
    def _publish(
        self,
        *,
        system_map: RagSystemMap,
        normalized_system_map: AiSystemMapV2,
        profile_result: ProfileInferenceResult,
        readiness_report: ReadinessReport,
        execution: StaticExecutionArtifacts,
        output_run: OutputRun,
    ) -> PublishedBuildArtifacts:
        map_json_path = self.output_provider.write_json(
            system_map,
            output_run=output_run,
        )
        viewer = self._projection.build(
            system_map,
            map_json_path=map_json_path,
            normalized_system_map=normalized_system_map,
            profile_result=profile_result,
        )
        graph = viewer.graph_view_model
        map_markdown_path = self.output_provider.write_markdown(
            self._markdown.render(graph),
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
                self._mermaid.render(graph),
                output_run=output_run,
            )
        )
        execution_map_mermaid_path = (
            self.output_provider.write_execution_map_mermaid(
                execution.execution_map_mermaid,
                output_run=output_run,
            )
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

    # 做什麼：publish 中途失敗時刪除已寫檔與空目錄，避免半套產物。
    # 被誰呼叫：publish() 的 except。
    # 自己呼叫：Path.unlink / rmdir（忽略 OSError）。
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
