from __future__ import annotations

import ast
import json
from importlib import import_module
from pathlib import Path

import pytest

from systograph.core.models.ai_system_map_v2 import AiSystemMapV2
from systograph.core.models.system_map import RagSystemMap
from systograph.core.services.system_map_index import SystemMapIndex
from systograph.core.services.system_map_v1_to_v2_adapter import (
    SystemMapV1ToV2Adapter,
)
from systograph.core.services.system_map_v2_validation_service import (
    SystemMapV2ValidationError,
    SystemMapV2ValidationService,
)

# ---------------------------------------------------------------------------
# 測試資料路徑
# Path(__file__) = 這個測試檔自己；parents[2] 往上兩層到 tests/
# 再進 fixtures/ai_system_map/ 拿樣本 JSON
# ---------------------------------------------------------------------------
V1_RICH_MAP = (
    Path(__file__).parents[2]
    / "fixtures"
    / "ai_system_map"
    / "valid_rich_frontend_sample.v1.json"
)
WORKFLOW_MAP = (
    Path(__file__).parents[2]
    / "fixtures"
    / "ai_system_map"
    / "v2"
    / "workflow_graph.v2.json"
)


# ---------------------------------------------------------------------------
# Fixture = 測試前自動準備好的資料
# 測試函式參數寫 canonical_map 時，pytest 會先跑這個函式再注入結果
# ---------------------------------------------------------------------------
@pytest.fixture
def canonical_map() -> AiSystemMapV2:
    """讀 v1 樣本 → 轉成 canonical v2（模擬產品真實路徑）。"""
    legacy = RagSystemMap.model_validate_json(
        V1_RICH_MAP.read_text(encoding="utf-8")
    )
    return SystemMapV1ToV2Adapter().adapt_to_canonical(legacy)


@pytest.fixture
def workflow_map() -> AiSystemMapV2:
    """
    讀原生 v2 workflow 樣本 → 驗證後回傳（用來測 location / json_pointer）。
    """
    payload = json.loads(WORKFLOW_MAP.read_text(encoding="utf-8"))
    return SystemMapV2ValidationService().validate(payload)


# ---------------------------------------------------------------------------
# 煙霧測試：先確認模組與 API「有落地」，還沒測行為對不對
# ---------------------------------------------------------------------------
def test_system_map_index_contract_is_available() -> None:
    # Given：要檢查的模組路徑
    module_name = "systograph.core.services.system_map_index"

    # When：嘗試 import；找不到就直接判定失敗
    try:
        module = import_module(module_name)
    except ModuleNotFoundError:
        pytest.fail("SystemMapIndex module is not implemented", pytrace=False)

    # Then：模組裡必須有 SystemMapIndex 這個 class
    assert hasattr(module, "SystemMapIndex")


def test_system_map_index_exposes_v2_factory() -> None:
    # Given
    index_type = SystemMapIndex

    # When：檢查是否有工廠方法 from_map（用 map 建 index）
    factory_exists = hasattr(index_type, "from_map")

    # Then
    assert factory_exists


def test_system_map_index_exposes_only_canonical_singular_lookups() -> None:
    # Given：七種「用 ID 查單一物件」的 API 名稱
    expected_lookups = {
        "component_by_id",
        "edge_by_id",
        "evidence_by_id",
        "endpoint_by_id",
        "risk_by_id",
        "unmapped_by_id",
        "candidate_fact_by_id",
    }

    # When：列出 class 上公開的名稱
    public_names = set(dir(SystemMapIndex))

    # Then：expected 必須是 public_names 的子集合（七個都在）
    assert expected_lookups <= public_names


# ---------------------------------------------------------------------------
# Found / Missing：lookup 的基本契約
# 有 ID → 回正確物件；沒 ID → 回 None（不丟例外）
# ---------------------------------------------------------------------------
def test_returns_each_canonical_fact_when_id_exists(
    canonical_map: AiSystemMapV2,
) -> None:
    # Given：先從 map 拿出第 0 筆，後面用它們的 ID 反查
    component = canonical_map.components[0]
    edge = canonical_map.edges[0]
    evidence = canonical_map.evidence[0]
    endpoint = canonical_map.endpoints[0]
    risk = canonical_map.risk_hints[0]
    unmapped = canonical_map.unmapped_components[0]
    candidate = canonical_map.candidate_facts[0]

    # When：用整份 map 建出電話簿（index）
    index = SystemMapIndex.from_map(canonical_map)

    # Then：用 ID 查回來的內容，要等於 map 裡原本那筆（== 比內容，
    # 不是比同一個物件）
    assert index.component_by_id(component.component_id) == component
    assert index.edge_by_id(edge.edge_id) == edge
    assert index.evidence_by_id(evidence.evidence_id) == evidence
    assert index.endpoint_by_id(endpoint.endpoint_id) == endpoint
    assert index.risk_by_id(risk.risk_id) == risk
    assert index.unmapped_by_id(unmapped.unmapped_id) == unmapped
    assert index.candidate_fact_by_id(candidate.candidate_fact_id) == candidate


def test_returns_none_when_canonical_fact_id_is_missing(
    canonical_map: AiSystemMapV2,
) -> None:
    # Given
    index = SystemMapIndex.from_map(canonical_map)

    # When：故意查不存在的 ID（七種 lookup 各查一次）
    lookups = (
        index.component_by_id("component:missing"),
        index.edge_by_id("edge:missing"),
        index.evidence_by_id("evidence:missing"),
        index.endpoint_by_id("endpoint:missing"),
        index.risk_by_id("risk:missing"),
        index.unmapped_by_id("unmapped:missing"),
        index.candidate_fact_by_id("candidate:missing"),
    )

    # Then：全部都應回 None（缺資料是正常狀態，不是崩潰）
    assert lookups == (None, None, None, None, None, None, None)


# ---------------------------------------------------------------------------
# Isolation：改來源 map 或改查詢結果，都不能污染 index 內部快照
# （index 建好當下就 deep copy；每次查詢也回 copy）
# ---------------------------------------------------------------------------
def test_index_and_source_map_remain_isolated_from_caller_mutation(
    canonical_map: AiSystemMapV2,
) -> None:
    # Given：留一份「建 index 當下」的基準複本
    original = canonical_map.model_copy(deep=True)
    index = SystemMapIndex.from_map(canonical_map)
    component_id = canonical_map.components[0].component_id

    # When：
    # 1) 改來源 map
    canonical_map.components[0].evidence_ids.append("evidence:source-only")
    first_result = index.component_by_id(component_id)
    assert first_result is not None
    # 2) 再改查詢結果（呼叫端拿到的 copy）
    first_result.evidence_ids.append("evidence:result-only")
    second_result = index.component_by_id(component_id)

    # Then：
    # 再查一次仍等於 original（index 沒被兩邊污染）
    assert second_result == original.components[0]
    # 來源 map 確實被改了（證明隔離靠 snapshot，不是靠禁止改 map）
    assert canonical_map.components[0] != original.components[0]


# ---------------------------------------------------------------------------
# Duplicate ID：應在進 index 之前就被 validator 擋住
# （parametrize = 同一支測試跑 7 種 collection）
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("collection_name", "id_label"),
    [
        ("components", "component_id"),
        ("edges", "edge_id"),
        ("evidence", "evidence_id"),
        ("endpoints", "endpoint_id"),
        ("risk_hints", "risk_id"),
        ("unmapped_components", "unmapped_id"),
        ("candidate_facts", "candidate_fact_id"),
    ],
)
def test_duplicate_ids_are_rejected_by_validator_before_indexing(
    canonical_map: AiSystemMapV2,
    collection_name: str,
    id_label: str,
) -> None:
    # Given：把某一類 list 的第一筆再 append 一次 → 故意製造重複 ID
    payload = canonical_map.model_dump(mode="json")
    collection = payload[collection_name]
    assert isinstance(collection, list)
    collection.append(collection[0])

    # When / Then：validate 應丟出含 "duplicate xxx_id" 的錯誤
    # 注意：這裡刻意不呼叫 SystemMapIndex —— 責任在 validator
    with pytest.raises(
        SystemMapV2ValidationError,
        match=f"duplicate {id_label}",
    ):
        SystemMapV2ValidationService().validate(payload)


# ---------------------------------------------------------------------------
# 架構邊界：index 只能查詢，不能長出 save/validate/project 等動作
# 也不能 import viewer / routes / filesystem 等上層依賴
# ---------------------------------------------------------------------------
def test_index_has_no_domain_actions_or_forbidden_dependencies() -> None:
    # Given：禁止出現在 SystemMapIndex 上的動作名稱
    forbidden_actions = {
        "save",
        "apply",
        "validate",
        "infer",
        "project",
        "render",
    }
    # 禁止出現在 import 路徑裡的關鍵字
    forbidden_dependencies = {
        "viewer",
        "profile",
        "readiness",
        "renderer",
        "routes",
        "repositories",
        "filesystem",
        "validation",
    }
    module = import_module("systograph.core.services.system_map_index")
    module_path = Path(module.__file__ or "")

    # When：用 AST 解析原始碼，收集 from xxx import ... 的模組路徑
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }

    # Then：class 上沒有禁止動作；import 路徑也不含禁止關鍵字
    assert forbidden_actions.isdisjoint(dir(SystemMapIndex))
    assert all(
        forbidden not in imported
        for forbidden in forbidden_dependencies
        for imported in imported_modules
    )


# ---------------------------------------------------------------------------
# 分組查詢：依 type / layer 篩選，保留輸入順序；找不到回空 tuple
# ---------------------------------------------------------------------------
def test_groups_components_by_type_and_layer_in_input_order(
    canonical_map: AiSystemMapV2,
) -> None:
    # Given：自己先用 list comprehension 算出「正確答案」當基準
    expected_by_type = tuple(
        item
        for item in canonical_map.components
        if item.canonical_type == "slot_placeholder"
    )
    expected_by_layer = tuple(
        item for item in canonical_map.components if item.layer == "retrieval"
    )
    index = SystemMapIndex.from_map(canonical_map)

    # When
    by_type = index.components_by_type("slot_placeholder")
    by_layer = index.components_by_layer("retrieval")

    # Then：結果與基準相同；miss 回 ()；改回傳物件也不污染下次查詢
    assert by_type == expected_by_type
    assert by_layer == expected_by_layer
    assert index.components_by_type("missing") == ()
    assert index.components_by_layer("missing") == ()
    by_type[0].evidence_ids.append("evidence:caller-only")
    assert index.components_by_type("slot_placeholder") == expected_by_type


# ---------------------------------------------------------------------------
# Edge 方向：outgoing = 我指出去；incoming = 別人指進來；順序跟 map 一致
# ---------------------------------------------------------------------------
def test_resolves_edge_directions_in_canonical_input_order(
    canonical_map: AiSystemMapV2,
) -> None:
    # Given：選定一個已知 component，自己先算出進出邊基準
    component_id = "component:retriever:qdrant-retriever"
    expected_outgoing = tuple(
        edge for edge in canonical_map.edges if edge.source == component_id
    )
    expected_incoming = tuple(
        edge for edge in canonical_map.edges if edge.target == component_id
    )
    index = SystemMapIndex.from_map(canonical_map)

    # When
    outgoing = index.outgoing_edges(component_id)
    incoming = index.incoming_edges(component_id)

    # Then
    assert outgoing == expected_outgoing
    assert incoming == expected_incoming
    assert index.outgoing_edges("component:missing") == ()
    assert index.incoming_edges("component:missing") == ()


# ---------------------------------------------------------------------------
# Evidence 批次：依「請求順序」回傳；未知 ID 跳過（不插 None）
# ---------------------------------------------------------------------------
def test_resolves_evidence_in_requested_order_and_skips_unknown_ids(
    canonical_map: AiSystemMapV2,
) -> None:
    # Given：請求順序故意是 [第 2 筆, 假 ID, 第 0 筆]
    requested_ids = [
        canonical_map.evidence[2].evidence_id,
        "evidence:missing",
        canonical_map.evidence[0].evidence_id,
    ]
    index = SystemMapIndex.from_map(canonical_map)

    # When
    evidence = index.evidence_for_ids(requested_ids)

    # Then：只回找到的兩筆，且順序是 2 → 0（假 ID 被跳過）
    assert evidence == (
        canonical_map.evidence[2],
        canonical_map.evidence[0],
    )
    locations = index.related_locations_for_evidence_ids(requested_ids)
    assert [item.config_key for item in locations] == [
        canonical_map.evidence[2].location.config_key,
        canonical_map.evidence[0].location.config_key,
    ]


# ---------------------------------------------------------------------------
# Location 穩定化：重複 evidence ID 要去重，並保留 json_pointer / path
# ---------------------------------------------------------------------------
def test_related_locations_stably_deduplicate_and_preserve_json_pointer(
    workflow_map: AiSystemMapV2,
) -> None:
    # Given：同一 evidence ID 出現兩次（應只算一次 location）
    requested_ids = [
        "evidence:workflow-edges",
        "evidence:workflow-nodes",
        "evidence:workflow-edges",
    ]
    index = SystemMapIndex.from_map(workflow_map)

    # When
    locations = index.related_locations_for_evidence_ids(requested_ids)

    # Then：兩個不同 location；json_pointer 與 path 都保留
    assert [location.json_pointer for location in locations] == [
        "/edges",
        "/nodes",
    ]
    assert [location.path for location in locations] == [
        "flows/main.json",
        "flows/main.json",
    ]


# ---------------------------------------------------------------------------
# 消費者遷移檢查：選定檔案不應再依賴 legacy v1 model / schema 分支
# （這是靜態讀原始碼字串，不是執行那些模組）
# ---------------------------------------------------------------------------
def test_normalized_consumers_have_no_legacy_models_or_schema_branch() -> None:
    # parents[3]：從此測試檔往上到專案根目錄
    root = Path(__file__).parents[3]
    selected = [
        root / "src/systograph/core/services/detail_scan_target_resolver.py",
        root
        / "src/systograph/core/services/mapping_evidence_packet_builder.py",
        root / "src/systograph/web/routes/mapping_proposal_routes.py",
    ]

    for path in selected:
        source = path.read_text(encoding="utf-8")
        # 不該再直接用舊 model、手動判 schema、或摸 .extensions
        assert "models.system_map" not in source
        assert "schema_version ==" not in source
        assert ".extensions" not in source
