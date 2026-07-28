# 這個檔案負責：定義 ai-system-map/v1 的 Pydantic 資料契約（舊版 / v1 map）。
# 掃描管線各 service 產出的「系統地圖」JSON，形狀都依這裡的 model。
# 注意：新管線正規化後的 canonical 形狀在 ai_system_map_v2.py；本檔是 v1
# contract。
#
# 呼叫鏈（誰會用到這些 model）：
#   providers（掃檔找證據）→ Evidence / Endpoint / ComponentInstance
#   ComponentDetection / EndpointDetection / FlowDerivation / RiskHint
#     → 組裝進 RagSystemMap
#   SystemMapNormalizeService / SystemMapValidationService
#     → 驗證、正規化 RagSystemMap
#   MarkdownSummary / QueryTrace / DetailScan / Viewer
#     → 讀取 RagSystemMap 各子區塊
#   build_system_map_schema()
#     → 產出 JSON Schema 給 contract / 文件用
"""Pydantic models for the ai-system-map/v1 contract."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# RecommendedNextCheck 的 canonical home 在 models/recommended_next_check.py
# （版本中立 DTO，v1 / v2 共用）。這裡 import 進來綁定名字，讓
# RagSystemMap.recommended_next_checks 維持 v1 contract 不變。
from kai_mind.core.models.recommended_next_check import RecommendedNextCheck

SCHEMA_VERSION = "ai-system-map/v1"
SCHEMA_ID = "https://kai-mind.local/schemas/ai-system-map.v1.schema.json"
JSON_SCHEMA_DRAFT = "https://json-schema.org/draft/2020-12/schema"

SystemMapSchemaVersion = Literal["ai-system-map/v1"]
SystemType = Literal["rag"]
ClassificationMode = Literal["user_selected_or_default"]
ScanDepth = Literal["system", "component", "code_path"]
SlotStatus = Literal["detected", "missing", "not_configured", "not_applicable"]
EndpointType = Literal["local", "external"]
RiskTargetType = Literal[
    "component_instance", "endpoint", "component_slot", "evidence", "file"
]


# 做什麼：所有 v1 contract model 的基底；禁止多出未知欄位（extra="forbid"）。
# 被誰用：本檔所有 class 都繼承它。
# 自己呼叫：Pydantic BaseModel（序列化 / 驗證）。
class ContractModel(BaseModel):
    """Base model that forbids silent contract drift."""

    model_config = ConfigDict(extra="forbid")


# 做什麼：記錄這份 map 用哪個模板分類（目前固定 rag-core-v1）。
# 被誰用：組裝 RagSystemMap 時填入；normalize / validation 會讀。
# 內含：無巢狀 model，只有 mode / selected_template。
class Classification(ContractModel):
    mode: ClassificationMode
    selected_template: Literal["rag-core-v1"]
    future_layer: str | None = None


# 做什麼：被掃描專案的基本資訊（名稱、路徑、schema version）。
# 被誰用：map build assemble、path safety / redaction 相關流程。
# 內含：無巢狀 model。
class Project(ContractModel):
    name: str
    root_path: str | None = None
    root_path_redacted: str | None = None
    path_mode: str | None = None
    system_map_schema_version: SystemMapSchemaVersion | None = None


# 做什麼：參考架構模板（有哪些 slots / flows）。
# 被誰用：組裝 RagSystemMap；對照「應有哪些 RAG 槽位」。
# 內含：slots / flows 字串列表（非巢狀 model）。
class ReferenceArchitecture(ContractModel):
    id: Literal["rag-core-v1"]
    version: str | None = None
    slots: list[str]
    flows: list[str]


# 做什麼：某個 slot 裡偵測到的實際元件實例（如 Qdrant retriever）。
# 被誰用：ComponentDetectionService 建立；Endpoint / Flow / Risk / DetailScan
# 會引用 id。
# 內含：evidence_ids 指向 Evidence.id。
class ComponentInstance(ContractModel):
    id: str
    slot: str
    kind: str
    name: str
    description: str | None = None
    provider: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)


# 做什麼：一個架構槽位（如 vector_store）及其狀態、底下 instances。
# 被誰用：ComponentDetection 填入；RagSystemMap.components_by_slot 的 value。
# 內含：instances → list[ComponentInstance]。
class ComponentSlot(ContractModel):
    slot: str
    required_for_rag: bool
    status: SlotStatus
    instances: list[ComponentInstance] = Field(default_factory=list)


# 做什麼：一筆可追溯證據（哪個檔、哪幾行、什麼值、哪個 rule）。
# 被誰用：providers（code_pattern / config_parse / dependency / docker…）建立；
#         幾乎所有 detection / risk / mapping / detail scan 都會引用。
# 內含：無巢狀 model；file 必須是專案相對 POSIX path。
class Evidence(ContractModel):
    id: str
    kind: str
    file: str | None = Field(
        default=None,
        description=(
            "Project-relative POSIX path. Must not contain a drive, UNC root, "
            "absolute path, backslash separator, or parent traversal."
        ),
    )
    path: str | None = None
    value: str | None = None
    rule_id: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    snippet: str | None = None


# 做什麼：偵測到的 API / service endpoint（local 或 external）。
# 被誰用：EndpointDetectionService 建立；QueryTrace / RiskHint 可能引用。
# 內含：evidence_id → Evidence；可選 component_instance_id →
# ComponentInstance。
class Endpoint(ContractModel):
    id: str
    value: str
    endpoint_type: EndpointType
    method: str | None = None
    slot: str | None = None
    component_instance_id: str | None = None
    evidence_id: str


# 做什麼：flow 裡的一條邊（從哪個 slot/component 到哪個）。
# 被誰用：FlowDerivationService 建立；包在 Flow.edges 裡。
# 內含：evidence_ids → Evidence；可選 from/to_component_id →
# ComponentInstance。
class Edge(ContractModel):
    id: str
    flow_id: str
    from_slot: str
    to_slot: str
    from_component_id: str | None = None
    to_component_id: str | None = None
    relationship: str
    evidence_ids: list[str] = Field(default_factory=list)


# 做什麼：一條資料流（例如 query → retrieve → generate），含多條 Edge。
# 被誰用：FlowDerivationService；RagSystemMap.flows；Viewer 畫圖會讀。
# 內含：edges → list[Edge]。
class Flow(ContractModel):
    id: str
    name: str | None = None
    flow_type: str | None = None
    edges: list[Edge] = Field(default_factory=list)


# 做什麼：風險提示（指向某個 target，並附 evidence / rationale）。
# 被誰用：RiskHintService 建立；readiness / markdown summary / viewer 會讀。
# 內含：evidence_id → Evidence；target 依 target_type 指向 component/endpoint/
# …。
class RiskHint(ContractModel):
    id: str
    type: str
    target: str
    target_type: RiskTargetType
    evidence_id: str
    rule_id: str
    rationale: str
    uncertainty: str | None = None
    severity_hint: str | None = None


# 做什麼：detail scan 的單筆 finding（摘要 + 相關 evidence）。
# 被誰用：DetailScanService 寫入；包在 DetailScanResult.findings。
# 內含：evidence_ids → Evidence。
class DetailScanFinding(ContractModel):
    kind: str
    summary: str
    evidence_ids: list[str] = Field(default_factory=list)
    best_effort: bool | None = None


# 做什麼：detail scan 追到的程式路徑一步（檔案 / symbol / 行號）。
# 被誰用：DetailScanService；包在 DetailScanResult.code_path。
# 內含：可選 evidence_id → Evidence。
class CodePathStep(ContractModel):
    file: str = Field(
        description=(
            "Project-relative POSIX path. Must not contain a drive, UNC root, "
            "absolute path, backslash separator, or parent traversal."
        )
    )
    symbol: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    evidence_id: str | None = None
    best_effort: bool | None = None


# 做什麼：一次 detail scan 的完整結果（findings + code_path + warnings）。
# 被誰用：DetailScanService / routes；掛在 RagSystemMap.detail_scans。
# 內含：findings → DetailScanFinding；code_path → CodePathStep。
class DetailScanResult(ContractModel):
    id: str
    target_type: str
    target: str
    scan_depth: ScanDepth
    status: str
    replay_depth: str | None = None
    findings: list[DetailScanFinding] = Field(default_factory=list)
    code_path: list[CodePathStep] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    best_effort: bool | None = None
    context_limits: dict[str, Any] = Field(default_factory=dict)


# 做什麼：query replay / trace 的單一事件（時間序、延遲、input/output）。
# 被誰用：QueryTraceService；Viewer ReplayTimeline；掛在
# RagSystemMap.query_trace_events。
# 內含：可選 endpoint_id / component_id / edge_id 等導航欄位。
class QueryTraceEvent(ContractModel):
    id: str
    trace_id: str | None = None
    sequence_index: int
    timestamp: str
    event_type: str | None = None
    step_type: str | None = None
    status: str | None = None
    query_sent: bool | None = None
    endpoint_id: str | None = None
    replay_depth: str | None = None
    slot: str | None = None
    component_id: str | None = None
    unmapped_component_id: str | None = None
    edge_id: str | None = None
    warnings: list[str] = Field(default_factory=list)
    input: Any | None = None
    output: Any | None = None
    latency_ms: int | float | None = None
    latency: str | None = None
    error: Any | None = None
    retrieved_chunks: Any | None = None


# 做什麼：模板外的擴充元件（使用者確認或偵測到但不在核心 slots）。
# 被誰用：manual mapping / confirmation；normalize 時可能轉成 v2
# candidate_facts。
# 內含：evidence_ids → Evidence。
class ExtensionComponent(ContractModel):
    id: str
    name: str
    kind: str
    status: str
    confirmed_by_user: bool | None = None
    description: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)


# 做什麼：掃到但尚未對應到正式 slot 的元件（待 mapping）。
# 被誰用：ComponentDetection；MappingProposal / MappingEvidencePacketBuilder。
# 內含：evidence_ids → Evidence。
class UnmappedComponent(ContractModel):
    id: str
    source_file: str | None = None
    observed_kind: str
    status: str
    reason: str
    evidence_ids: list[str] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)


# 做什麼：整次掃描的計數摘要（掃了幾檔、缺幾個 slot、幾個 risk…）。
# 被誰用：map build 結尾填入 RagSystemMap.scan_summary。
# 內含：無巢狀 model。
class ScanSummary(ContractModel):
    status: str
    files_scanned: int = 0
    files_skipped: int = 0
    detected_slots: int = 0
    missing_slots: int = 0
    not_configured_slots: int = 0
    unmapped_components: int = 0
    risk_hints: int = 0
    secret_masking_applied: bool = False


# 做什麼：v1 AI System Map 的根物件（整份地圖）。
# 被誰用：MapBuildService / Normalize / Validation / Markdown / Trace / Viewer
# 等。
# 內含：把上面所有區塊組在一起（slots、evidence、flows、risks…）。
# 之後若進 v2：通常經 adapter → AiSystemMapV2 → SystemMapIndex。
class RagSystemMap(ContractModel):
    schema_version: SystemMapSchemaVersion
    system_type: SystemType
    classification: Classification
    project: Project
    reference_architecture: ReferenceArchitecture
    scan_depth: ScanDepth
    scan_summary: ScanSummary | None = None
    components_by_slot: dict[str, ComponentSlot]
    evidence: list[Evidence]
    endpoints: list[Endpoint]
    flows: list[Flow]
    extensions: list[ExtensionComponent]
    unmapped_components: list[UnmappedComponent]
    detail_scans: list[DetailScanResult]
    risk_hints: list[RiskHint]
    recommended_next_checks: list[RecommendedNextCheck]
    query_trace_events: list[QueryTraceEvent]


# 做什麼：從 RagSystemMap 產出確定性的 JSON Schema（給 contract / schema 檔用）
# 。
# 被誰呼叫：schema 產生腳本、contracts 測試（驗證 schema artifact）。
# 自己呼叫：RagSystemMap.model_json_schema()，再補上 $schema / $id。
def build_system_map_schema() -> dict[str, Any]:
    """Return the deterministic JSON Schema artifact for ai-system-map/v1."""

    schema = RagSystemMap.model_json_schema()
    schema["$schema"] = JSON_SCHEMA_DRAFT
    schema["$id"] = SCHEMA_ID
    return schema
