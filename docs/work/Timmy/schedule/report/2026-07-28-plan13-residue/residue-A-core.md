# Plan 13 v2 cutover 殘留稽核 — 分區 A：backend core（v1 map surface）

READ-ONLY 稽核。無任何檔案被修改。
基準文件：`13-retire-legacy-extension-contract.md`、`2026-07-17-phase2-plan13-v2-cutover-REP.md`、`CLAUDE.md`。
驗證環境：`.venv/bin/python`（3.11），`tests/contracts/test_v2_cutover_consumer_allowlist.py` + `test_canonical_output_configuration.py` + `test_v2_active_cutover.py` = `13 passed`。

---

### RA-1. 正常 build path 不只 import v1 producer，還在每次建構時**急切實例化**整個 v1 物件圖並讀 v1-only 規則檔【A類】

- **位置**：`src/systograph/core/services/map_build_service.py:56-58`、`:79-81`、`:151-162`

- **現況**（真實 code）

```python
# map_build_service.py:56-58 / 79-81（module-level import）
from systograph.core.services.legacy_v1_rollback_service import (
    LegacyV1RollbackService,
)
...
from systograph.core.services.system_map_materialization_service import (
    SystemMapMaterializationService,
)

# map_build_service.py:151-162（__init__ 內，無任何版本條件）
rollback_service = (
    legacy_v1_rollback_service
    or LegacyV1RollbackService(
        materialization_service=SystemMapMaterializationService(
            component_detection_service=component_detection_service,
            ...
        )
    )
)
```

- **證據**

runtime import 探測（正常 v2 模式，未設任何 env）：

```
$ .venv/bin/python -c "import systograph.core.services.map_build_service"
modules pulled in by importing map_build_service:
   systograph.core.models.system_map              <- v1 model 本體
   systograph.core.services.legacy_v1_rollback_service
   systograph.core.services.system_map_materialization_service
   systograph.core.services.system_map_normalize_service
   systograph.core.services.system_map_validation_service
   systograph.core.services.system_map_v1_to_v2_adapter
   systograph.core.services.viewer_legacy_compatibility
RagSystemMap reachable from map_build_service namespace? True
```

實例化探測（`MapBuildService()`，v2 模式）：

```
canonical_output_version      = ai-system-map/v2
pipeline._legacy_rollback     = LegacyV1RollbackService
  .._materialization          = SystemMapMaterializationService
  .._normalize_service        = SystemMapNormalizeService
  .._validation_service       = SystemMapValidationService
v1 recommended-next-check TOML loads during normal MapBuildService(): 1
```

亦即：即使 `canonical_output_version == "ai-system-map/v2"`，正常 build 仍然
(a) import 全套 v1 module、(b) 建構 `SystemMapMaterializationService` →
`SystemMapNormalizeService` → `RecommendedNextCheckService`、(c) 從磁碟讀
`recommended_next_check_rules.toml`（v1-only 規則目錄）。

- **判定理由**

Plan 13 **Task 5** 已打 `[x]` 的 checkbox：

> - [x] v1 schema/fixture、Legacy DTO、adapter 與 operator rollback serializer 明確標示
>   legacy/read-only；**normal build path 不得 import**。

`map_build_service.py` 就是 normal build path 的入口（CLI map / Web scan / Apply /
DetailScan 都經它），它 module-level import 了 operator rollback serializer
（`SystemMapMaterializationService`，allowlist 分類 `operator_rollback`）與
`LegacyV1RollbackService`。此外 census（`_python_legacy_hits`）只掃 4 個 symbol 名
（`RagSystemMap` / `ExtensionComponent` / `SystemMapValidationService` /
`new_extension_component`）與 2 個字串 literal，**完全看不到 `SystemMapMaterializationService`
與 `LegacyV1RollbackService` 這兩個 import**，所以 allowlist test 綠燈不代表隔離成立。

同檔 `:100` 的責任註解也還寫著 `# 自己呼叫：SystemMapMaterializationService、…`，指的是 v1 版本。

- **建議處置**：不要在 Plan 15 前刪。**改成 lazy 建構**——只有
  `self._canonical_output_version == "ai-system-map/v1"` 時才 import + 實例化
  `LegacyV1RollbackService`（function-local import），並把 `:100` 註解改成
  `SystemMapV2MaterializationService`。同時把 Task 5 那個 `[x]` 降回 `[ ]` 或改寫成
  「rollback boundary 允許在 composition root 被引用」。若不改實作，至少要把
  `map_build_service.py` 兩筆 import 補進 allowlist（需擴充 census 的 symbol 集合）。
- **風險**：中（目前不會產生 v1 artifact，但 Plan 15 想刪 v1 writer 時會直接撞到 normal path；
  另外每次 `MapBuildService()` 都做一次無用的 TOML 磁碟 I/O）

---

### RA-2. `MapBuildManifest` 的 `active_schema_version` / `requested_schema_version` 預設值切換後仍是 `ai-system-map/v1`【A類】

- **位置**：`src/systograph/core/models/analysis_history.py:148-153`

- **現況**

```python
class MapBuildManifest(AnalysisHistoryModel):
    ...
    active_schema_version: Literal["ai-system-map/v1", "ai-system-map/v2"] = (
        "ai-system-map/v1"
    )
    requested_schema_version: Literal[
        "ai-system-map/v1", "ai-system-map/v2"
    ] = "ai-system-map/v1"
```

對比同一次 cutover 已改對的 `MapBuildResult`（`map_build.py:91-93`）：

```python
active_schema_version: SystemMapSchemaSelection = "ai-system-map/v2"
requested_schema_version: SystemMapSchemaSelection = "ai-system-map/v2"
source_schema_version: SystemMapSchemaSelection = "ai-system-map/v2"
```

- **證據**

production 端 `build_manifest_service.py:107-108` 每次都顯式傳值，所以現行流程不會踩到。
但已經有 code 在踩預設值：

```python
# tests/unit/core/test_local_json_state_provider.py:73
def build_manifest(build_id: str = "build:b1") -> MapBuildManifest:
    return MapBuildManifest(
        lineage=MapBuildLineage(...),
        output_dir=f"/tmp/output/{build_id.replace(':', '_')}",
        artifact_digests={"ai_system_map.json": "sha256:map"},
    )   # <- 沒傳 active/requested_schema_version，落到 "ai-system-map/v1"
```

`grep -rn "MapBuildManifest("` 全部命中：`build_manifest_service.py:98`（顯式）、
`test_local_json_state_provider.py:73`（**落預設值**）、`test_local_json_concurrency.py:39`、
`test_build_manifest_service.py:123/183`。沒有任何測試釘住「新 manifest 預設應為 v2」。

- **判定理由**

Plan 13 Task 2 已打 `[x]`：「manifest 記錄 `active_schema_version`、`source_schema_version`、
`operator_rollback_active` 與 migration warnings，consumer 不得從檔案 shape 猜版本。」
Rollback contract 也明訂「預設值是 v2」。這裡的 model default 是唯一沒跟著 flip 的
schema-selection 預設值。實際危害路徑：`build_manifest_service.py:134`
`if loaded.active_schema_version != manifest.active_schema_version: raise
BuildArtifactLoadError`——任何漏傳欄位的 manifest writer 會產生「badge=v1、artifact=v2」的
永久不可 reload build。

- **建議處置**：立刻可改——把兩個 default 改成 `"ai-system-map/v2"`（read 舊 manifest JSON 時
  仍會顯式帶 `active_schema_version` 欄位，不影響既有資料回讀），並補一個
  `MapBuildManifest()` 最小構造的 default assertion 測試。
- **風險**：中（現行 happy path 不受影響，但這是一個沉默的錯誤預設，reload gate 會 fail closed）

---

### RA-3. `SystemMapNormalizeService` module docstring 仍自稱 "the active v1 writer"，並要求「Plan 13 前不要切」【D類】

- **位置**：`src/systograph/core/services/system_map_normalize_service.py:1-6`

- **現況**

```python
"""Assemble ai-system-map/v1 draft documents from scanner outputs.

00A compatibility note: this service remains the active v1 writer. Normalized
ai-system-map/v2 views are produced by CanonicalMapLoader + adapter after the
v1 map is validated. Do not silent-cutover this writer to v2 before Plan 13.
"""
```

- **證據**

allowlist 已把同一檔案的兩筆 hit 分類為 `operator_rollback`：

```python
# tests/contracts/test_v2_cutover_consumer_allowlist.py:201-212
path="src/systograph/core/services/system_map_normalize_service.py",
symbol="RagSystemMap",  classification="operator_rollback",
removal_plan="Plan 15 removes the isolated rollback normalizer.",
```

且唯一 import 它的是 `system_map_materialization_service.py:23-24`，而後者只被
`legacy_v1_rollback_service.py:15-16` 與 `map_build_service.py:154` 使用。它已不是
"the active v1 writer"。

- **判定理由**：Plan 13 已完成 default flip（報告：「Normal CLI/API build 已直接產生唯一
  normalized `AiSystemMapV2`」），docstring 描述的是 cutover 前狀態，且「Do not silent-cutover
  before Plan 13」這句指令已失效。同樣問題見 `system_map_validation_service.py:1-5`
  （`"""...00A keeps this service as the v1 validator."""`，仍以 00A 為時態基準，但至少沒有錯誤宣稱）。
- **建議處置**：改註解——改寫成
  `"Operator-rollback-only v1 writer. Not reachable from the normal v2 build path;
   Plan 15 removes it."`，並在同檔標註 `RecommendedNextCheckService` 的狀態（見 RA-4）。
- **風險**：低（不影響行為，但會誤導下一個維護者把它當 active writer）

---

### RA-4. `RecommendedNextCheckService` 與 `recommended_next_check_rules.toml` 事實上已降級為 rollback-only，正常 v2 build 的 `recommended_next_checks` 恆為空，但無人標示、無人追蹤【B類】

- **位置**：`src/systograph/core/services/system_map_normalize_service.py:91-264`（`RecommendedNextCheckService`）、
  `src/systograph/core/services/viewer_session_service.py:111-124`、
  `src/systograph/core/services/viewer_legacy_compatibility.py:31-43`

- **現況**

```python
# viewer_session_service.py:109-124
normalized = loaded.normalized
legacy_source = loaded.legacy_source_map
recommended_next_checks = []
if legacy_source is not None:                      # <- 只有 v1 來源才填
    normalized = _preserve_legacy_edge_order(legacy_source, normalized)
    recommended_next_checks = _graph_recommended_next_checks(legacy_source)
graph = self._graph_projection.project(
    normalized, ..., recommended_next_checks=recommended_next_checks,
)
```

`_graph_recommended_next_checks(system_map: RagSystemMap)` 讀的是
`RagSystemMap.recommended_next_checks`——只有 `SystemMapNormalizeService.assemble`
（v1 path，`:294-299`, `:343`）會填。`AiSystemMapV2` **根本沒有 `recommended_next_checks` 欄位**
（`ai_system_map_v2.py:425-449`）。

- **證據**

實跑一次正常 v2 build（`tests/fixtures/rag_projects/basic_qdrant_ollama_rag`）：

```
status                        = ok
active_schema_version         = ai-system-map/v2
graph.source_schema_version   = ai-system-map/v2
graph.nodes                   = 61
graph.recommended_next_checks = []      <-- 空
graph.details.evidence_by_id  = 16
```

`grep -rn "RecommendedNextCheckService"` 在 `src/` 只有 `system_map_normalize_service.py`
自己（`:91`, `:274`, `:278`）。`RuleCatalogLoader.load_default_recommended_next_check_rules`
（`rule_catalog_loader.py:101`）現在只被 `tests/unit/core/test_rule_catalog_loader.py:423`
呼叫，production 已無 caller。

Markdown 有 fallback（`graph_markdown_renderer.py:234-246` 改用 profile registry 的
per-node `recommended_next_checks`），所以報表不會空白——但資料來源已**默默換成另一套規則**。

- **判定理由**

Plan 13 census baseline 對 `Extension detection/materialization` 那列只講 extension，
對 `system_map_normalize_service.py` 只分類了 `RagSystemMap` 與 `ai-system-map/v1` 兩個 symbol。
`RecommendedNextCheckService`、`RUNTIME_CRITICAL_SLOTS` / `RAG_TRUST_CRITICAL_SLOTS` /
`PRIVACY_RISK_RULE_IDS` 三張表、以及 `core/rules/recommended_next_check_rules.toml`
**既不在 allowlist（census 看不到這些名字），也不在 Plan 15 的移除清單**
（Plan 15 只列 operator v1 writer/env、migration DTO/command/quarantine、fixtures）。
它們現在的實際狀態是「只在 operator rollback 或讀 legacy v1 artifact 時才會執行」，
但沒有任何文件或註解說明這件事。這正是「會永遠爛在那」的過渡寫法。

- **建議處置**：兩選一並補文件——
  (a) 若確定 `recommended_next_checks` 是產品要保留的能力：這是 cutover **功能缺口**，
      要在 v2 producer 或 profile 層補回來，並在 Plan 14 的 final validation 列為 blocker；
  (b) 若確定已由 profile registry 的 per-node checks 取代：把 `RecommendedNextCheckService`、
      `recommended_next_check_rules.toml`、`GraphViewModel.recommended_next_checks`、
      `viewer_legacy_compatibility._graph_recommended_next_checks` 一併補進 Plan 15
      移除清單，並在 cutover report 的 “Remaining warnings” 明列此行為變更。
  無論哪一種，都要先在 `system_map_normalize_service.py` 頂端補一行 rollback-only 標示。
- **風險**：中（產品可見行為在 cutover 中靜默改變，報告未列為 remaining warning）

---

### RA-5. `ViewerSessionService.build()` / `project_to_graph()` 是 v1-typed public API、production 零 caller、責任註解全部過時【B類 + D類】

- **位置**：`src/systograph/core/services/viewer_session_service.py:149-196`

- **現況**

```python
# :149-154 責任註解
    # 做什麼：對已驗證的 v1 RagSystemMap 做投影，回完整 ViewerLoadResult。
    # 被誰呼叫：load_map（v1）、BuildArtifactPublisher.publish、
    # BuildManifestService.load。
    def build(
        self,
        system_map: RagSystemMap,          # <- v1 型別
        *, map_json_path=None, normalized_system_map=None, profile_result=None,
    ) -> ViewerLoadResult: ...

    def project_to_graph(
        self,
        system_map: RagSystemMap,          # <- v1 型別
        *, map_json_path: Path | None = None,
    ) -> GraphViewModel: ...
```

- **證據**

```
$ grep -rn "\.build_loaded(\|\.build_canonical(\|\.project_to_graph(" src tests
src/systograph/core/services/build_manifest_service.py:166:  self._viewer.build_loaded(...)
src/systograph/core/services/build_artifact_publisher.py:129: self._projection.build_canonical(...)
src/systograph/web/routes/detail_scan_routes.py:187:          viewer_service.build_canonical(...)
tests/unit/core/test_viewer_session_service.py:268/299:    ViewerSessionService().project_to_graph(...)
tests/unit/core/test_viewer_session_service.py:334/411:    ViewerSessionService().build(...)
```

`build()` 與 `project_to_graph()` 在 `src/` 內**沒有任何 caller**；
註解列出的三個呼叫者實際上呼叫的是 `build_loaded` / `build_canonical`，
且 `load_map` 自己走 `build_loaded`（`:97`）。註解已 100% 失真。

- **判定理由**

Plan 13 census baseline 的 `Viewer/projection` 那列 target 是「全部接 v2/GraphViewModel；
schema branching 只在 loader」。allowlist 兩筆 `viewer_session_service.py` 記錄
（`RagSystemMap` / `SystemMapValidationService`，皆 `migration_only`，
removal_plan「Plan 15 removes the legacy Viewer reload input」）把它當成「legacy reload 入口」，
但實際上這兩個 method 已經沒有 reload 用途——reload 走的是 `build_loaded`。
分類與現實對不上，而且它是 active service 上兩個吃 v1 DTO 的公開 method，
未來任何新 caller 都會不小心把 v1 帶回 active path。

- **建議處置**：`build()` 與 `project_to_graph()` 可**立刻降級為 test-only helper**
  （移到 `tests/helpers/` 或改名加 `_legacy_` 前綴並標 deprecated），
  同時修正 `:149-154` 的「被誰呼叫」註解。allowlist 的 removal_plan 要改成
  「Plan 15 removes the unused legacy Viewer projection entry points（no production caller）」。
- **風險**：中（v1 型別的公開 API 掛在 active service 上，是最容易被誤用回退的入口）

---

### RA-6. `materialize_existing_map` 的 rollback 分支：`require_representable` 的結果被丟棄，之後無條件 raise 同一個 error code【B類】

- **位置**：`src/systograph/core/services/map_build_pipeline.py:174-180`

- **現況**

```python
    def materialize_existing_map(self, *, system_map: AiSystemMapV2, ...):
        if self._canonical_output_version == "ai-system-map/v1":
            if self._legacy_rollback is None:
                raise LegacyV1RollbackError("legacy_rollback_writer_unavailable")
            self._legacy_rollback.require_representable(system_map)   # <- 回傳值被丟棄
            raise LegacyV1RollbackError("legacy_rollback_not_representable")  # <- 無條件
```

`require_representable` 本身（`legacy_v1_rollback_service.py:82-91`）在
「map 不可用 v1 表示」時 raise 同一個 code。所以：
- 不可表示 → `require_representable` raise `legacy_rollback_not_representable`
- **可**表示 → 下一行還是 raise `legacy_rollback_not_representable`

`require_representable(...)` 這一行對可觀察行為毫無影響，是 dead call；
而「detail scan 在 rollback 模式不支援」這個真正的意圖被冒用了一個語意錯誤的 stable error code。

- **證據**

唯一覆蓋這條路徑的測試是
`tests/integration/test_v2_active_cutover.py:168` `test_operator_rollback_rejects_native_v2_enrichment_without_output`，
它傳入的是 **native v2** map（`normal.ai_system_map`，`source_schema_version == "ai-system-map/v2"`），
會在 `require_representable` 的**第一個** if 就 raise：

```python
# legacy_v1_rollback_service.py:83-85
if system_map.source_schema_version != "ai-system-map/v1":
    raise LegacyV1RollbackError("legacy_rollback_not_representable")
```

也就是說 `:180` 那行無條件 raise 從來沒被任何測試走到；
Plan 13 相關檔案清單列為 `Create` 的 `tests/unit/core/test_legacy_v1_rollback_service.py`
**不存在**（見 RA-14）。

- **判定理由**

Plan 13 Rollback contract：「Rollback preflight 只允許可由 legacy contract 完整表示的 build。
**若存在 v2-only component、endpoint/edge 或其他無法無損表示的 fact**，回傳
`legacy_rollback_not_representable`」。這裡是「不管能不能表示都回這個 code」，
違反 stable error code 的語意；同時 dead call 讓人以為有 preflight 分支，實際沒有。

- **建議處置**：改成明確的兩段——先 `require_representable(...)`（保留 preflight 語意），
  再 raise 一個新的、誠實的 code（例如 `legacy_rollback_detail_scan_unsupported`），
  或直接刪掉 dead call 並在註解說明「rollback 模式不支援 enriched-map 重建」。
  另外補一個 unit test 覆蓋「v1-sourced 且可表示的 map 進 `materialize_existing_map`」。
- **風險**：低（rollback 是 default-off；但 error code 誤導稽核與 operator）

---

### RA-7. rollback-only 的 v1 materializer / validator 檔案**完全沒有** legacy 標示，且非限定命名是誤用陷阱【D類 + B類】

- **位置**：`src/systograph/core/services/system_map_materialization_service.py:1-38`

- **現況**

整個檔案沒有 module docstring、沒有 class docstring、沒有任何 legacy/rollback 註記：

```python
from __future__ import annotations
from dataclasses import dataclass
...
class SystemMapMaterializationService:
    def __init__(self, *, ...):
```

命名對照（左＝legacy，右＝active）：

| legacy（無版本後綴） | active（有 V2 後綴） |
| --- | --- |
| `SystemMapMaterializationService` | `SystemMapV2MaterializationService` |
| `SystemMapNormalizeService` | `SystemMapV2NormalizeService` |
| `SystemMapValidationService` | `SystemMapV2ValidationService` |

- **證據**

allowlist 明確把 `system_map_materialization_service.py` 的 `RagSystemMap` 與
`SystemMapValidationService` 兩筆分類為 `operator_rollback`
（`test_v2_cutover_consumer_allowlist.py:189-200`），
但檔案本體零標示。相較之下 `system_map_normalize_service.py` 與
`system_map_validation_service.py` 至少各有一段（過時的）docstring。

- **判定理由**

Plan 13 Task 5 已打 `[x]`：「v1 schema/fixture、Legacy DTO、adapter 與 **operator rollback
serializer 明確標示 legacy/read-only**」。`system_map_materialization_service.py` 就是
operator rollback serializer 的組裝點，沒有任何標示，checkbox 與 code 不符。
命名層面：未加版本後綴的名字反而是 legacy 版本，新 code auto-import 時極易誤選
（RA-1 顯示 `map_build_service.py` 同時 import 兩個名字，只差三個字元）。

- **建議處置**：補註解（module docstring：`Operator-rollback-only v1 materializer.
  Not part of the normal ai-system-map/v2 build path; Plan 15 removes it.`）。
  若可接受一次性 rename，建議改名為 `LegacyV1SystemMapMaterializationService` /
  `LegacyV1SystemMapNormalizeService` / `LegacyV1SystemMapValidationService`
  （rename 需同步更新 allowlist 的 `symbol` 欄位）。
- **風險**：中（命名陷阱是實際會導致回退的機制，不只是可讀性問題）

---

### RA-8. v1 module `system_map.py` 同時是 active v2 path 的共用 DTO 來源；census 只看得到 3 個 symbol，Plan 15 依字面無法刪除【B類】

- **位置**：`src/systograph/core/models/system_map.py`（整檔）、`src/systograph/core/models/ai_system_map_v2.py:30`

- **現況**

```python
# ai_system_map_v2.py:30 —— v2 canonical model 直接 import v1 module 的型別
from systograph.core.models.system_map import Evidence
```

正常 v2 path 對 `system_map.py` 的實際依賴（`grep "from systograph.core.models.system_map import"`）：

| 匯入者 | 匯入的 v1 型別 |
| --- | --- |
| `models/ai_system_map_v2.py:30` | `Evidence` |
| `models/scan.py:15` | `Evidence` |
| `models/map_build.py:25` | `DetailScanResult` |
| `models/analysis_history.py:14` | `DetailScanResult` |
| `models/trace.py:9` | `QueryTraceEvent` |
| `providers/{code_pattern,workflow_json,dependency_manifest,config_parse,docker_compose}_provider.py` | `Evidence` |
| `services/component_detection_service.py:11` | v1 slot/instance 型別 |
| `services/endpoint_detection_service.py:13` | `Endpoint` 等 |
| `services/risk_hint_service.py:11` | `RiskHint` 等 |
| `services/flow_derivation_service.py:8` | `Flow` / `Edge` |
| `services/system_map_v2_normalize_service.py:23` | `Endpoint, Flow, RiskHint` |
| `services/query_trace_service.py:14` | `QueryTraceEvent` |
| `services/project_scan_service.py:20` | `Evidence` |
| `services/scan_boundary_review_service.py:33` | `Evidence` |
| `services/canonical_evidence_service.py:8` | `Evidence` |
| `services/code_path_scan_service.py:10` | v1 型別 |
| `services/detail_scan_service.py:10`、`detail_scan_build_service.py:15` | `DetailScanResult, ScanDepth` |
| `web/schemas.py:39`、`web/routes/detail_scan_routes.py:11` | `DetailScanResult` |

allowlist 只為此檔登記三筆：`ExtensionComponent` / `RagSystemMap` / `ai-system-map/v1`，
removal_plan 一致寫「Remove the read-only v1 DTO after migration support」。

- **證據**

`_python_legacy_hits()`（`test_v2_cutover_consumer_allowlist.py:323-350`）只比對
`LEGACY_NAMES = {RagSystemMap, ExtensionComponent, SystemMapValidationService,
new_extension_component}` 與 `LEGACY_LITERALS = {ai-system-map/v1, new_extension_component}`。
`Evidence` / `Endpoint` / `Flow` / `RiskHint` / `DetailScanResult` / `QueryTraceEvent` /
`UnmappedComponent` / `ComponentSlot` / `ComponentInstance` 一個都不在集合裡，
所以上表 20+ 個 active import **在 census 中完全不可見**。

同檔 header 註解（`:1-15`）也已過時：

```
# 掃描管線各 service 產出的「系統地圖」JSON，形狀都依這裡的 model。   <- 已不成立（normal path 產 v2）
#   MarkdownSummary / QueryTrace / DetailScan / Viewer               <- MarkdownSummaryService 已於 0a68ccd 刪除
```

`:305-308` 的 `RagSystemMap` 註解同樣仍寫「被誰用：MapBuildService / Normalize /
Validation / Markdown / Trace / Viewer 等」。

- **判定理由**

Plan 13 把 `core/models/system_map.py` 整檔放進「Migration-only allowlist」那列，
Plan 15 的 ownership 是「移除…不再需要的 fixtures；將 dual-read 收斂成 migration-only 或刪除」。
但這個檔案裡真正 migration-only 的只有 `RagSystemMap` / `ExtensionComponent` /
`Classification` / `ReferenceArchitecture` / `ComponentSlot` / `ComponentInstance` /
`ScanSummary` / `RecommendedNextCheck`；其餘 8 個型別是 active v2 path 的骨幹。
沒有任何文件記錄「刪 v1 model 之前要先把共用型別抽出去」，Plan 15 執行者會撞牆。

- **建議處置**：留到 Plan 15，但**現在就要補進 Plan 15 的 task 清單**：
  新增一條「將 `Evidence` / `Endpoint` / `Flow` / `Edge` / `RiskHint` / `DetailScanResult` /
  `QueryTraceEvent` / `CodePathStep` / `DetailScanFinding` / `UnmappedComponent` / `ScanDepth`
  從 `models/system_map.py` 抽到中立 module（例如 `models/scan_facts.py`），
  `system_map.py` 只保留純 v1 contract」。同時修 `:1-15` 與 `:305-308` 的過時註解
  （尤其刪掉已不存在的 `MarkdownSummary`）。
- **風險**：中（不影響現行行為；但這是 Plan 15 的隱藏 blocker，且註解會誤導）

---

### RA-9. `ai_system_map_v2.py` 的 Compatibility/Generic 過渡型別群只被 adapter 使用，但 allowlist 的 removal_plan 只提「provenance literal」【B類】

- **位置**：`src/systograph/core/models/ai_system_map_v2.py:121-286`（含題目點名的 `:156`、`:269`）

- **現況**（題目指定的兩段註解）

```python
# :156-159
# 做什麼：adapter 過渡用的通用元件（還沒完全 canonical 化前的形狀）。
# 被誰用：AiSystemMapV2CompatibilityView.components。
class GenericComponent(CompatibilityContractModel):

# :269-275
# 做什麼：Plan 00 adapter 的過渡根物件（v1 → v2 中間 compatibility view）。
# 被誰用：SystemMapV1ToV2Adapter 產出；再轉成正式 AiSystemMapV2。
# 注意：這裡的 evidence 仍用 v1 的 Evidence model（來自 system_map.py）。
class AiSystemMapV2CompatibilityView(CompatibilityContractModel):
```

- **證據**

`grep -rn "AiSystemMapV2CompatibilityView\|GenericComponent\|GenericEdge\|GenericEndpoint\|
GenericRiskHint\|GenericUnmappedFact\|GenericCandidateFact\|CompatibilityProject"` 在 `src/`
的**唯一非定義端**是 `system_map_v1_to_v2_adapter.py`（`:12`, `:27-39`, `:83-568`）。
`src/` 其他檔案、`tests/` 皆零命中。

→ **判定：這兩個註解描述的用途是準確的（純 migration-only，active path 摸不到），
但用詞「過渡用 / 還沒完全 canonical 化前」暗示還有進行中的收斂工作，這在 Plan 13 之後已不成立。**
它們現在的狀態是「凍結的 v1→v2 adapter 中繼型別，等 Plan 15 隨 dual-read 一起處理」。

同檔另有兩個**命名殘留**（不是 dead code，是活的但名字誤導）：
- `CompatibilityLayer`（`:79-91`）被 **canonical** 的 `CanonicalComponent.layer`（`:336`）與
  active 的 `SystemMapV2NormalizeService.SLOT_LAYER_BY_ID`（`:31`）使用。
- `CompatibilityCandidateKind = Literal["legacy_extension"]`（`:100`）被 **canonical** 的
  `CanonicalCandidateFact.candidate_kind`（`:409`）使用——意味 canonical v2 的 candidate fact
  只能是 `"legacy_extension"` 一種 kind。

- **判定理由**

allowlist 對 `ai_system_map_v2.py` 只有一筆記錄（symbol `ai-system-map/v1`，`migration_only`，
removal_plan「Remove provenance literal after v1 read support ends.」）。
這個 removal_plan 只涵蓋 `:278` / `:436` 的 literal，**沒有涵蓋** 9 個 `Generic*` class +
`AiSystemMapV2CompatibilityView` + `CompatibilityProject` + `CompatibilityContractModel`
這一整組 migration-only 型別。Plan 15 的清單也沒提。屬「既不在 allowlist 分類、也不在 Plan 15
移除清單」的無人追蹤過渡 scaffolding。

- **建議處置**：留到 Plan 15，但**改註解 + 補進 Plan 15 清單**：
  (1) 把 `:156` / `:269` 的「過渡用」改成「migration-only：僅由 `SystemMapV1ToV2Adapter` 使用，
      normal v2 path 不產生也不消費；Plan 15 隨 v1 read support 一併移除」；
  (2) Plan 15 新增一條「移除 `ai_system_map_v2.py` 的 Compatibility/Generic 型別群」；
  (3) `CompatibilityLayer` / `CompatibilityCandidateKind` 既然是 canonical 在用，
      建議改名為 `CanonicalLayer` / `CanonicalCandidateKind`（純命名，零行為變更），
      否則 Plan 15 有人依名字誤刪。
- **風險**：低（純可維護性；但 `CompatibilityLayer` 被誤刪會直接打爛 canonical model）

---

### RA-10. `SLOT_LAYER_BY_ID` 在 active v2 normalizer 與 migration-only adapter 各有一份逐字相同的複本【B類】

- **位置**：`src/systograph/core/services/system_map_v2_normalize_service.py:31-45`
  ／ `src/systograph/core/services/system_map_v1_to_v2_adapter.py:55-69`

- **現況**：兩份 13 個 legacy slot → `CompatibilityLayer` 的對照表完全相同
  （`app_api_or_orchestrator: control` … `observability: governance_observability`），
  一份在 active v2 producer，一份在 migration-only adapter。

- **證據**：兩檔的 dict 內容逐行比對一致；型別皆為 `dict[str, CompatibilityLayer]`；
  無共用 module。allowlist 對兩檔各自有記錄，但分類不同
  （`system_map_v2_normalize_service.py` 根本不在 allowlist；
  `system_map_v1_to_v2_adapter.py` 是 `migration_only`）。

- **判定理由**：Plan 13 census baseline 的 `Derived consumers` 那列要求「只接 v2 或 GraphViewModel；
  保留 `source_schema_version` 作 provenance，不自行 dispatch」，但沒有處理這種
  「active 與 migration-only 共用同一份 legacy 對照表」的情況。
  現在 v1 adapted map 與 native v2 map 的 layer 語意等價性靠「兩份複本剛好一樣」維持——
  Plan 13 Stage A gate 的 paired-fixture semantic equivalence 測試正是靠這個。
  一旦有人只改其中一份，equivalence 就靜默破裂；而 Plan 15 刪 adapter 時，
  留下的那份會失去對照組。
- **建議處置**：留到 Plan 15 前處理較安全——把表抽到中立 module
  （例如 `core/services/legacy_slot_layer_map.py`）並兩邊共用，
  或至少在兩處互相加 `# NOTE: must stay identical to <other file>:<line>` 交叉註解。
- **風險**：中（drift 會讓 v1/v2 semantic equivalence 測試以外的路徑靜默不一致）

---

### RA-11. 正常 v2 producer 仍以 `rag-core-v1` 的 13 個 slot 為 assembly blueprint，並把 `required_for_rag` 寫進 canonical component metadata【D類】

- **位置**：`src/systograph/core/services/system_map_v2_materialization_service.py:78`、
  `src/systograph/core/services/system_map_v2_normalize_service.py:31-45`、`:127-131`

- **現況**

```python
# system_map_v2_materialization_service.py:78（normal v2 path 的第一行工作）
template = RagTemplateService.load("rag-core-v1")

# system_map_v2_normalize_service.py:127-131（每個 canonical component 的 metadata）
metadata={
    "legacy_slot": slot.slot,
    "required_for_rag": slot.required_for_rag,
    "semantic_kind": "repo_component",
},
```

`SLOT_LAYER_BY_ID`（`:31-45`）只認得這 13 個 RAG slot，其餘一律 `"undetermined"`。

- **證據**

`rag_template_service.py` 本身有明確 boundary 標示（`:37-43`）：

```python
RAG_CORE_V1_BOUNDARY_METADATA: Final = RagTemplateBoundaryMetadata(
    template_id=BUILTIN_TEMPLATE_ID,
    template_input_kind="legacy_template_input",
    active_readiness_surface=False,
    active_profile_status_surface=False,
    active_frontend_summary_surface=False,
)
```

但這個 metadata 只被 `tests/unit/core/test_rag_template_service.py` 消費
（`grep -rn "boundary_metadata"` 在 `src/` 只有定義端），
`SystemMapV2MaterializationService` 呼叫 `load()` 時完全沒有走 boundary check。
另外 `rag_template_service.py:115-118` 的驗證訊息仍寫
`"Allowed statuses must match ai-system-map/v1 SlotStatus"`。

- **判定理由**

Plan 13 驗收標準已打 `[x]`：「v2 是 generic AI system map，**不預設 RAG/Agent 類別**」。
就 **schema** 而言這是真的（`AiSystemMapV2` 沒有 RAG-only required field，
`tests/integration/test_v2_active_cutover.py:69` 有測）。
但就 **producer** 而言不成立：normal v2 build 的 component 集合、layer 分派與 metadata
仍完全由 `rag-core-v1` 的 13 slot 決定，並在每個 canonical component 上留 `required_for_rag`。
Task 3 的措辭「`rag-core-v1` 只保留為 legacy input grounding 或 operator rollback boundary」
可以勉強涵蓋（"legacy input grounding"），但報告與驗收條目的說法過強，
容易讓下一階段以為 producer 已 generic 化。

- **建議處置**：修文件——在 Plan 13 的驗收條目與 cutover report 加一句限定：
  「generic 指 schema 層；Step-4 assembly blueprint 仍是 `rag-core-v1` 的 13 slot，
   generic producer 不在 Plan 13/14/15 範圍」。
  另把 `rag_template_service.py:117` 的錯誤訊息去掉 `ai-system-map/v1` 字樣，
  並考慮讓 `SystemMapV2MaterializationService` 實際呼叫 `boundary_metadata()` 做斷言，
  否則那組 metadata 只是裝飾。
- **風險**：低（行為正確且有測試；問題在於文件宣稱超出實作）

---

### RA-12. `models/viewer.py` docstring 仍寫「derived from ai-system-map/v1」【D類】

- **位置**：`src/systograph/core/models/viewer.py:1-4`、`:14`

- **現況**

```python
# 這個檔案負責：前端 Viewer 用的圖投影契約（nodes / edges / filters / load result）。
# 注意：這是「投影結果」，不是 canonical map 真相；真相在 AiSystemMapV2 /
# RagSystemMap.                                        <- 仍把 v1 列為真相之一
...
"""Viewer projection models derived from ai-system-map/v1."""   # <- :14
```

- **證據**：`GraphProjectionService.project()` 的輸入型別是 `AiSystemMapV2`
  （`graph_projection_service.py:120` 讀 `system_map.source_schema_version`），
  `ViewerSessionService` 的 active 入口 `build_loaded` / `build_canonical` 也都吃 v2。
  Plan 13 Task 3 已打 `[x]`：「Viewer、`SystemMapIndex`、graph projection … 只接
  `AiSystemMapV2` 或 `GraphViewModel`」。
  同類問題：`models/scan.py:1` `"""Scanner workflow models that are not part of
  ai-system-map/v1."""`（仍以 v1 為敘述基準，較輕微）。
- **判定理由**：CLAUDE.md 明訂 `ai-system-map.v1` 是 legacy read/migration only，
  docstring 卻把 Viewer 投影說成從 v1 衍生。
- **建議處置**：改註解——`"""Viewer projection models derived from ai-system-map/v2."""`，
  並把 `:3-4` 的「真相在 AiSystemMapV2 / RagSystemMap」改成只留 `AiSystemMapV2`。
- **風險**：低

---

### RA-13. `POST /api/scans` 的 public v1 拒絕發生在**完整 scan + 已持久化 snapshot 之後**，且僅靠 broad `except ValueError` 轉 422【B類】

- **位置**：`src/systograph/web/routes/scan_routes.py:276-313`、`:336-337`

- **現況**

```python
# :276-282 —— 先掃描並存 snapshot
snapshot = snapshot_service.scan_and_save(
    project_id=payload.project_id, project_root=project.project_path, ...
)
...
def build(output_run: OutputRun) -> MapBuildResult:
    return service.build_from_snapshot(          # <- require_public_v2_selection 在這裡才跑
        snapshot, request=MapBuildRequest(..., system_map_schema_version=(
            payload.system_map_schema_version)), ...
    )
result = commit_service.commit(..., build=build)
...
except ValueError as exc:                        # :336-337 —— 泛型攔截
    raise HTTPException(status_code=422, detail=str(exc)) from exc
```

`CanonicalOutputConfigurationError` 是 `ValueError` 子類、`__str__` 回傳 code，
所以 detail 確實是 `legacy_output_not_selectable`（Plan 13 Task 7 的 API 422 宣稱成立）。

- **證據**
  - `map_routes.py:29-32` 有**顯式**的 `except CanonicalOutputConfigurationError` → 422，
    且 `MapBuildService.build()` 在 `:187` 第一行就檢查，掃描前失敗。
  - `scan_routes.py` 沒有對應的顯式 handler；`require_public_v2_selection` 在
    `build_from_snapshot`（`map_build_service.py:252`）才跑，此時 scan 已完成、
    `ScanSnapshot` 已寫進 state directory。
  - staging 目錄不會殘留（`build_commit_service.py:88-101` 有
    `finally: if not published: self._remove_staging(...)`）。

- **判定理由**：Plan 13 Task 2 只要求「要求 v1 時回傳 `legacy_output_not_selectable`」，
  沒規定時機，所以嚴格說不算違規；但 (a) 泛型 `except ValueError` 讓這個 stable code 是
  「碰巧」正確的，任何內部 `ValueError` 都會被同樣包成 422；(b) 一次無效請求會付出完整
  filesystem scan 成本並留下持久化 snapshot。這屬於沒人分類的過渡行為。
- **建議處置**：改實作（低成本）——在 `create_scan` 進入 preflight 之前呼叫
  `require_public_v2_selection(payload.system_map_schema_version)`，
  並補一個顯式的 `except CanonicalOutputConfigurationError` handler。
  或在 Plan 15 移除 request field 時一併處理。
- **風險**：低

---

### RA-14. Plan 13「相關檔案」列為 `Create` 的 `tests/unit/core/test_legacy_v1_rollback_service.py` 不存在；rollback writer 只有 3 個 integration 測試【D類】

- **位置**：`docs/.../13-retire-legacy-extension-contract.md:185`

- **現況**：計畫的相關檔案清單有
  `- Create: tests/unit/core/test_legacy_v1_rollback_service.py`。

- **證據**

```
$ for f in tests/unit/core/test_legacy_v1_rollback_service.py \
           tests/unit/core/test_build_commit_service.py \
           tests/unit/core/test_legacy_manual_mapping_migration_service.py; do ...
  MISSING tests/unit/core/test_legacy_v1_rollback_service.py
  OK      tests/unit/core/test_build_commit_service.py
  OK      tests/unit/core/test_legacy_manual_mapping_migration_service.py

$ grep -rln "LegacyV1RollbackService\|LegacyV1RollbackError" tests/
tests/integration/test_v2_active_cutover.py       <- 唯一
```

該檔內對 rollback 的覆蓋只有 3 個 test（`:106` rollback 寫 v1、`:132` public v1 拒絕、
`:168` enriched-map 拒絕）。`LegacyV1RollbackService.require_representable` 的
第二個條件（`semantic_kind` 不在 `{repo_component, slot_placeholder, legacy_extension}`）
與 RA-6 的無條件 raise 分支皆無測試。

- **判定理由**：Plan 13 其他 `Create` 檔都存在，只有這一個沒建，計畫文件未更新。
  依 `AGENTS.md`「Missing tests for scanner behavior … 是 P1」的標準，
  rollback writer（Plan 15 才會刪、Plan 14 要做 final validation 的東西）
  只有 integration 級覆蓋是偏薄的。
- **建議處置**：修文件（把該行從 `Create` 移除或標註實際落在
  `tests/integration/test_v2_active_cutover.py`），並在 Plan 14 補
  `require_representable` 的 unit 測試。
- **風險**：低（文件一致性 + 測試覆蓋缺口）

---

## C類：合法保留，逐條一句話

- `src/systograph/core/services/canonical_map_loader.py` — **「唯一 schema dispatch owner」宣稱驗證通過**：
  `grep 'schema_version ==|in |!=|\.get("schema_version")|\["schema_version"\]'` 在 `src/` 只命中
  loader 本身（`:118-125`）、`legacy_v1_rollback_service.py:84`（rollback preflight，operator boundary 內）、
  以及 `build_manifest_service.py:134` / `build_manifest_artifacts.py:66,151,180`
  （比對 manifest badge vs artifact，是 fail-closed 一致性檢查而非 shape 猜測）——**沒有** route/renderer/viewer 自行 dispatch。
- `src/systograph/core/services/canonical_output_configuration.py` — **rollback 預設關閉驗證通過**：
  `:21` 缺省 `"ai-system-map/v2"`，`:22-25` 非法值 raise `invalid_canonical_output_version`；
  composition root `web/app.py:138` 是 `create_app()` 的**第一行**（測試
  `test_v2_active_cutover.py:153 test_invalid_operator_version_prevents_app_startup` 覆蓋），
  CLI 由 `map_command.py:72-79` catch 並 exit 1；`tests/unit/core/test_canonical_output_configuration.py`
  釘住 default=v2 / v1 可設 / bogus fail / public v1 拒絕四種情形。
- `src/systograph/core/services/system_map_v1_to_v2_adapter.py` — allowlist `migration_only` 三筆分類正確；
  只被 `CanonicalMapLoader._load_v1` 呼叫，normal path 不可達。
- `src/systograph/core/services/system_map_validation_service.py` — 維持純 v1 validator，未擴張成第二個 dispatcher
  （`validate()` 只接受 v1 shape），符合 Plan 13 Task 2 最後一條。
- `src/systograph/core/services/viewer_legacy_compatibility.py` — 確實是 no-I/O module
  （只有 `RagSystemMap` → `GraphViewModel` 的純函式，無檔案/網路存取），Stage A 宣稱屬實。
- `models/profile_signal.py:201`、`models/readiness_report.py:56` 的
  `source_schema_version: Literal["ai-system-map/v1","ai-system-map/v2"]` — 純 provenance；
  `grep source_schema_version` 顯示唯一的決策用途在 `legacy_v1_rollback_service.py:84`（operator boundary），
  其餘皆只是傳遞/顯示（`graph_markdown_renderer.py:25` 只印字串）。
- `models/readiness_report.py:68` `primary_map_type` — 由 `readiness_report_service.py:144-155`
  從 `ProfileInferenceResult` 推導（`agentic-control` / `rag-grounding` detected → 對應 type），
  符合 Task 3「`primary_map_type` 只能由 report/projection 推導」。
- **`MarkdownSummaryService` 已確實移除** — `git log --diff-filter=D` 顯示於 commit `0a68ccd`
  連同 `tests/unit/core/test_markdown_summary_service.py` 一起刪除；`src/`/`tests/` 零殘留
  （唯一殘影是 `models/system_map.py:12` 的過時註解，已列入 RA-8；`docs/` 內 5 處舊設計文件引用屬其他分區）。
- **`contradicted` 第六態：零風險** — `grep -rn "contradicted"` 在 `src` / `tests` / `schemas` /
  `frontend/src` **全部零命中**。v1 的 `SlotStatus`（`system_map.py:32`）本來就只有
  `detected|missing|not_configured|not_applicable`，不含 `contradicted`，
  v2 的 `AssessmentStatus`（`ai_system_map_v2.py:41-47`）為五態且不含 `contradicted`。
  Plan 13「legacy `contradicted` 必須經 adapter 對應為 `conflicted`」這條要求是**空集合約束**，
  沒有第六種 active status 的風險。
- **`normalized_ai_system_map` 雙真相已完全移除** — `grep -rn "normalized_ai_system_map" src tests`
  只剩一筆反向斷言：`tests/integration/test_v2_active_cutover.py:59`
  `assert "normalized_ai_system_map" not in MapBuildResult.model_fields`。Task 2 該項屬實。
- `requested_schema_version` 已不作決策欄位 — `map_build_pipeline.py:266-267` 只把它寫進 result 作
  provenance，output version 全由 `self._canonical_output_version` 決定（`:113`）；
  唯一的公開輸入把關是 `require_public_v2_selection`。符合 Task 2。

---

## 隔離性結論

**一句話：不會產生 v1 output，但「碰得到」。**
今天的 normal build path 在 **執行語意** 上碰不到 v1 producer（`MapBuildPipeline.materialize`
的 v1 分支被 `self._canonical_output_version == "ai-system-map/v1"` 守住，預設值為 v2 且
非法值 fail startup）；但在 **import 與物件建構** 上完整碰得到——`MapBuildService.__init__`
每次都 module-level import 並急切實例化 `LegacyV1RollbackService` →
`SystemMapMaterializationService` → `SystemMapNormalizeService` → `SystemMapValidationService`，
連 v1-only 的 `recommended_next_check_rules.toml` 都會被讀進來（RA-1，已用 runtime probe 證實）。
因此 Plan 13 Task 5 的 `[x] normal build path 不得 import` 這一條**與 code 不符**，
且這條路徑對現行 census 完全隱形。

### Import / 呼叫鏈圖

```
CLI map_command / Web map_routes / scan_routes / ApplyConfirmations / DetailScanBuild
  └─> MapBuildService.__init__            [src/systograph/core/services/map_build_service.py]
        ├─ (module import, 無條件)
        │    ├─ legacy_v1_rollback_service        :56   ← operator_rollback
        │    └─ system_map_materialization_service :79   ← operator_rollback
        │
        ├─ [ACTIVE] SystemMapV2MaterializationService              :129-140
        │      ├─ RagTemplateService.load("rag-core-v1")           (RA-11)
        │      ├─ SystemMapV2NormalizeService  → AiSystemMapV2
        │      └─ SystemMapV2ValidationService
        │
        └─ [EAGER, 但執行時 dormant]  LegacyV1RollbackService       :151-162   ★RA-1
               └─ SystemMapMaterializationService
                     ├─ SystemMapNormalizeService                  ★RA-3
                     │     └─ RecommendedNextCheckService
                     │           └─ RuleCatalogLoader
                     │                 └─ recommended_next_check_rules.toml   ★RA-4 (磁碟 I/O)
                     ├─ SystemMapValidationService  → RagSystemMap ★RA-7
                     └─ RagTemplateService.load("rag-core-v1")

  └─> MapBuildPipeline.materialize        [map_build_pipeline.py:92-156]
        ├─ if canonical_output_version == "ai-system-map/v1":   :113
        │     └─ LegacyV1RollbackService.materialize
        │           → RagSystemMap(v1 artifact)
        │           → CanonicalMapLoader.load  → AiSystemMapV2      (單向，無 v2→v1 downgrade ✔)
        └─ else (DEFAULT):
              └─ SystemMapV2MaterializationService.materialize → AiSystemMapV2
        → _complete → ProfileInference → Readiness → StaticExecution → Publisher
        → MapBuildResult.ai_system_map : AiSystemMapV2   (唯一 canonical field ✔)

  └─> MapBuildPipeline.materialize_existing_map   [:161-192]
        └─ if v1: require_representable(...)  ← 回傳值被丟棄
                  raise "legacy_rollback_not_representable"  ← 無條件   ★RA-6

READ path（唯一 schema dispatch）:
  BuildManifestService.load / ViewerSessionService.load_map / build_canonical
    └─> CanonicalMapLoader.load                    ✔ 唯一 dispatcher（已驗證）
          ├─ v1 → SystemMapValidationService → SystemMapV1ToV2Adapter
          │        └─ AiSystemMapV2CompatibilityView → AiSystemMapV2      ★RA-9
          └─ v2 → SystemMapV2ValidationService → AiSystemMapV2
    └─> ViewerSessionService.build_loaded
          └─ if legacy_source is not None:  ← 只有 v1 才有
                _graph_recommended_next_checks(...)      ★RA-4（v2 恆為 []）
                _with_legacy_details(...)

共用 DTO（census 看不見的耦合）:
  models/system_map.py [v1 module]
    ├─ Evidence          ──> ai_system_map_v2.py:30, scan.py, 5 個 provider, canonical_evidence_service …
    ├─ Endpoint/Flow/RiskHint ──> system_map_v2_normalize_service.py:23  (ACTIVE v2 producer)
    ├─ DetailScanResult  ──> map_build.py:25, analysis_history.py:14, web/schemas.py:39
    └─ QueryTraceEvent   ──> trace.py:9, query_trace_service.py:14        ★RA-8
```

**Plan 15 前必須先解的兩件事**：(1) RA-1 的 eager 建構要改成 lazy，否則刪 v1 writer 會直接
打斷 normal path 的 import；(2) RA-8 的共用 DTO 要先從 `models/system_map.py` 抽出，
否則「刪除 v1 model」在字面上不可執行。
