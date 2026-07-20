# 這個檔案負責：map build 管線的「輸入請求」與「輸出結果」契約。
# 不負責實際掃描；真正組 map 的是 MapBuildService / MapBuildPipeline。
#
# 呼叫鏈：
#   CLI map_command / Web scan_routes / ApplyConfirmations / DetailScanBuild
#     → 組 MapBuildRequest
#     → MapBuildService.build() / build_from_snapshot() /
# build_from_enriched_map()
#     → MapBuildPipeline.materialize*()
#     → 回傳 MapBuildResult（路徑、canonical v2、profile、readiness、viewer）
"""Models for core map build orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from kai_mind.core.models.ai_system_map_v2 import AiSystemMapV2
from kai_mind.core.models.analysis_history import MapBuildLineage
from kai_mind.core.models.errors import PreconditionError
from kai_mind.core.models.profile_signal import ProfileInferenceResult
from kai_mind.core.models.readiness_report import ReadinessReport
from kai_mind.core.models.system_map import DetailScanResult
from kai_mind.core.models.viewer import ViewerLoadResult

SystemMapSchemaSelection = Literal["ai-system-map/v1", "ai-system-map/v2"]


# 做什麼：map build 相關 model 的基底（允許 Path 等 arbitrary types，
# 禁止未知欄位）。
# 被誰用：MapBuildRequest / MapBuildResult 繼承。
# 自己呼叫：Pydantic BaseModel。
class MapBuildModel(BaseModel):
    """Base model for map build inputs and results."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


# 做什麼：啟動一次 map build 的輸入參數（掃哪個專案、輸出哪裡、要不要 redact）
# 。
# 被誰用：
#   - CLI：map_command 轉成這個 request
#   - Web：scan_routes / apply_confirmations / materialization 組 request
#   - MapBuildService.build*() 當入口參數
# 內含：無巢狀 map；public v1 value 只保留到 Plan 15 作穩定拒絕，實際
# output version 由 process-level operator setting 決定。
class MapBuildRequest(MapBuildModel):
    project_path: Path
    output: Path = Path("outputs")
    redact_root_path: bool = True
    no_snippets: bool = False
    system_map_schema_version: SystemMapSchemaSelection = "ai-system-map/v2"


# 做什麼：一次 map build 的完整結果（成功/失敗、產物路徑、記憶體內 map 與報告）
# 。
# 被誰用：
#   - MapBuildService / MapBuildPipeline / BuildArtifactPublisher 組出並回傳
#   - ApplyConfirmations / BuildManifest / DetailScanBuild 讀取結果與路徑
#   - CLI / Web 把結果呈現或寫入 history
# 內含：
#   - ai_system_map → 唯一 normalized AiSystemMapV2 canonical truth
#   - profile_inference_result / readiness_report / viewer_load_result /
# lineage
#   - 各種 *_path → 磁碟上的 10 個 sibling artifacts
#   - error → PreconditionError（失敗時）
# 自己呼叫：無方法；純資料承載。
class MapBuildResult(MapBuildModel):
    status: Literal["ok", "error"]
    project_name: str
    output_run_dir: Path | None = None
    map_json_path: Path | None = None
    map_markdown_path: Path | None = None
    map_error_path: Path | None = None
    profile_signals_path: Path | None = None
    readiness_report_path: Path | None = None
    call_graph_path: Path | None = None
    dataflow_hints_path: Path | None = None
    execution_paths_path: Path | None = None
    evidence_table_path: Path | None = None
    system_map_mermaid_path: Path | None = None
    execution_map_mermaid_path: Path | None = None
    viewer_load_result: ViewerLoadResult | None = None
    ai_system_map: AiSystemMapV2 | None = None
    profile_inference_result: ProfileInferenceResult | None = None
    readiness_report: ReadinessReport | None = None
    detail_scan_results: list[DetailScanResult] = Field(default_factory=list)
    lineage: MapBuildLineage | None = None
    active_schema_version: SystemMapSchemaSelection = "ai-system-map/v2"
    requested_schema_version: SystemMapSchemaSelection = "ai-system-map/v2"
    source_schema_version: SystemMapSchemaSelection = "ai-system-map/v2"
    operator_rollback_active: bool = False
    migration_warnings: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    error: PreconditionError | None = None
