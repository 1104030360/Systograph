# Step 4 Component Bridge Registry 實作計畫

> **2026-07-11 backend execution status：** typed Python bridge registry、rule extraction、
> weak/ambiguous evidence boundary、multi-instance merge 與 injection tests 已完成；未新增
> TOML executable DSL。完成證據見
> `docs/work/Timmy/schedule/report/2026-07-11/2026-07-11-phase2-s1-pipeline-core-REP.md`。

> **執行者注意：** 逐 task 實作本計畫。步驟使用 checkbox（`- [ ]`）
> 語法以便追蹤。

**Goal:** 將 Step 4「掃描事實 → canonical component / unmapped review item /
capability candidate input」的比對規則集中到專門 Python module，避免規則散在
`ComponentDetectionService` 的大型 `if`/`elif`，也避免把 executable semantic
matching 搬進 TOML。

**Architecture:** Phase A 執行本計畫時，Step 3 仍由現有 Systograph TOML providers 產生 primary
typed `ScanFact` / `Evidence`；Gate-1 通過並完成 Plan 16 後，Phase B 才改由 UA structural
adapter 產生 primary facts，Systograph TOML providers 轉為 parity-only。Step 4 在兩個階段都由
`component_bridge_registry.py` 內的 typed Python
registry 負責比對：以 `rule_id`、`kind`、`path`、`value`、evidence strength 與
legacy/manual context 產生 bridge decision。registry 內部可用 list/table + for loop
實作，但 ownership 必須是 Python code，不新增第三份 TOML rule DSL。

**Tech Stack:** Python 3.11、dataclass / Pydantic v2、pytest、Ruff、mypy、現有
`ProjectScanResult`、`ComponentDetectionService`、`ManualMappingService`、
`SystemMapNormalizeService`。

---

## 2026-07-06 決策

Step 4 component bridge 的比對規則採 **Python 專門 module + table-driven list**
維護：

```text
ProjectScanResult.facts[] + evidence[]
  -> ComponentBridgeRegistry.match(...)
  -> ComponentBridgeDecision
       | component_candidate
       | unmapped_review_item
       | non_baseline_capability_signal
       | no_match
  -> ComponentDetectionService assemble ComponentDetectionResult
```

不是二選一：

- **維護位置：** 專門 Python 檔案，例如
  `src/systograph/core/services/component_bridge_registry.py`。
- **實作方式：** typed Python list / table + deterministic for loop。
- **禁止：** 將 Step 4 component 對位、evidence threshold、manual replay 或
  capability candidate 分流寫進 TOML。

## 2026-07-07 UA 整合對齊

Bridge registry 在 Phase A 即必須保留現有 Systograph TOML rule ids，並預先接受 Plan 16 將產生的
UA adapter `rule_id`，例如 `ua_import_*`、
`ua_symbol_*`、`ua_endpoint_*` 或 `ua_call_hint_*`。這些 rule id 仍只能在 Step 4
分流為 repo component / unmapped review item / non-baseline signal；registry 不得輸出
`plane_id`、`reference_node_id`、profile status 或 GraphViewModel layout。只有進入 Phase B
後，Systograph TOML rule ids 才轉為 parity 對比輸入；Phase A 它們仍是 Step 3 主掃描來源。

### 與 Phase2 Pipeline Step 對齊

本計畫只擁有 **橋接 1（Step 4）**，也就是把 Step 3 掃到的 raw facts 解讀成
「這份 repo map 裡可以安全 materialize 的東西」。它刻意不碰固定能力底圖：

```text
Step 3 ProjectScanResult.facts[] / evidence[]
  -> Step 4 component_bridge_registry.py
       component_candidate              -> ai_system_map.json.components
       unmapped_review_item             -> ai_system_map.json.unmapped_components[]
       non_baseline_capability_signal   -> Step 6 sidecar input / review context
       no_match                         -> 保留 evidence / warnings，不升格

Step 6 ProfileInferenceService
  -> 才把 validated repo facts 對到 10 planes / 52 reference nodes
```

因此 Step 4 registry 不能輸出 `plane_id`、`reference_node_id`、profile status、
Mapping Completeness 或 GraphViewModel layout。這些分別屬於 Plan `01A`/`02`/`06`。
`non_baseline_capability_signal` 也只是候選能力輸入：未確認前最多支持
`undetermined` / review context；confirmed non-baseline decision 由 Apply replay 後才穩定
materialize 到 `profile_signals.json.capability_candidate_components`。

### 為什麼不是 TOML

Step 4 不是單純字串對應。它需要同時處理：

- `rule_id` + `kind` + `path/value` 的 slot-aware whitelist，例如
  `vector_store.provider` 只能映射到 vector store，不能誤吃到 LLM。
- direct / indirect / weak evidence 的保守分流。
- legacy `rag-core-v1` compatibility slot 與 generic v2 component 的過渡。
- `unmapped_components[]` 與 Step 9 review lifecycle。
- confirmed manual mappings replay。
- non-baseline capability candidate 只進 Step 6/profile sidecar，不寫入
  `ai_system_map.json` canonical topology。
- schema invariant、排序、去重與 evidence id validation。

這些都需要 Python 型別、unit tests、integration tests 與清楚 call boundary。
TOML 仍可存在，但只屬於：

- Step 3 raw detector rules：`code_pattern_rules.toml`、
  `dependency_manifest_rules.toml`、`docker_image_rules.toml`。
- metadata/wording：`risk_hint_rules.toml`、
  `recommended_next_check_rules.toml`、future profile metadata TOML。

## 與既有 plans 的關係

| Plan | 關係 |
|---|---|
| `00A` | 提供 `ai-system-map/v2` normalized target；本 plan 的 registry 必須能支援 v1 compatibility 與 v2 output |
| `01` | 本 plan 把 non-baseline / unmapped 分流集中；`01` 持續擁有 manual decision model 與 capability candidate materialization |
| `01A` | Reference map 是 10-plane / 52-node metadata；Step 4 registry 不直接寫 reference node assessment |
| `02` | Profile inference 消費 Step 4/Step 9 後的 validated map facts 與 confirmed capability candidates |
| `03A` | Apply 從 scan snapshot replay Step 4 registry，不重跑 Step 3 UA sidecar / parity scan |
| `10` / `11` | 只定義 profile rule / metadata 邊界；不擁有 Step 4 component bridge |

## 目標資料流

```text
Step 3 ProjectScanService
  Phase A：Systograph TOML providers（primary）
  Phase B：UnderstandAnythingAnalysisService + UaStructuralAdapter（primary）
           + Systograph TOML providers parity diff
  -> ProjectScanResult(facts, evidence, issues, warnings, skipped_files)

Step 4 ComponentDetectionService
  -> ComponentBridgeRegistry.match(fact, evidence_ids)
  -> component candidates / unmapped review items / non-baseline signals
  -> ManualMappingService replay confirmed decisions
  -> ComponentDetectionResult

Normalize / validate
  -> ai_system_map.json
     components / edges / evidence / endpoints / risk_hints / unmapped_components

Step 6
  -> profile_signals.json
     capability_candidate_components only after confirmed non-baseline decision
```

## Target module shape

```python
@dataclass(frozen=True)
class ComponentBridgeRule:
    rule_ids: frozenset[str]
    fact_kinds: frozenset[str]
    output: Literal[
        "component_candidate",
        "unmapped_review_item",
        "non_baseline_capability_signal",
    ]
    canonical_type: str | None = None
    layer: str | None = None
    legacy_slot: str | None = None
    provider: str | None = None
    required_path_tokens: frozenset[str] = frozenset()
    required_value_tokens: frozenset[str] = frozenset()

    def matches(self, fact: ScanFact) -> bool:
        ...


COMPONENT_BRIDGE_RULES: tuple[ComponentBridgeRule, ...] = (
    ComponentBridgeRule(
        rule_ids=frozenset({
            "code_pattern_vector_store_qdrant",
            "docker_qdrant_image_detected",
        }),
        fact_kinds=frozenset({"vector_store", "docker_service"}),
        output="component_candidate",
        canonical_type="vector_store",
        layer="retrieval",
        legacy_slot="vector_store",
        provider="qdrant",
    ),
)
```

這是示意，不是最終 API。實作時可依 Pydantic/dataclass 與 existing
`ComponentCandidate` shape 調整，但必須保留以下性質：

- registry 是 typed Python data，不是 TOML/JSON DSL。
- matching order deterministic，且若多條 rule 命中，priority 明確。
- 每個 emitted item 都必須有 evidence ids；沒有 evidence 不可 materialize。
- legacy slot 欄位只作 compatibility metadata；active v2 不可把
  `rag-core-v1` slot completeness 當產品 verdict。
- capability candidate signal 不等於 profile `detected`，也不直接寫入 canonical map。

## 不在範圍內

- 不新增 `component_bridge_rules.toml`。
- 不把 reference map `plane_id` / node id 寫進 Step 3 scan TOML。
- 不在本 plan 實作 profile inference rules；由 `02` 擁有。
- 不在本 plan 實作 `ProfileInferenceService` 或 `GraphProjectionService`。
- 不移除 legacy `rag-core-v1` reader；退役由 `13` / `15` 擁有。
- 不讓 MappingProposal LLM provider 參與 Step 4 deterministic bridge。

## 實作 Tasks

### Task 1：Characterization tests 鎖定現行 Step 4 行為

**檔案：**

- Modify: `tests/unit/core/test_component_detection_service.py`
- Modify: `tests/integration/test_phase13_component_detection_behaviors.py`

- [ ] 補齊目前已支援的 mapping cases：Qdrant、Chroma、pgvector、OpenAI LLM、
  OpenAI embeddings、Ollama、FastAPI/Flask/Express route、retriever、prompt template。
- [ ] 補 dependency-only weak signal 保持 unmapped / needs review，不自動升 component。
- [ ] 補 reranker/router-like evidence 不自動寫 legacy extension；target flow 先保留
  unmapped / non-baseline capability signal。
- [ ] 補沒有 evidence ids 時不得產生 component / unmapped / candidate。
- [ ] 固定 deterministic ordering 與 duplicate merge 行為。

### Task 2：建立 Step 4 bridge registry module

**檔案：**

- Create: `src/systograph/core/services/component_bridge_registry.py`
- Test: `tests/unit/core/test_component_bridge_registry.py`

- [ ] 定義 `ComponentBridgeRule`、`ComponentBridgeDecision` 與
  `ComponentBridgeRegistry`。
- [ ] 將現有 `rule_id -> slot/provider/kind` 的 deterministic rules 搬成 typed
  Python list/table。
- [ ] 支援 path/value token predicates，但保持 small explicit helpers；不得引入可在
  TOML 中配置的 expression language。
- [ ] 為每個 rule 加 unit tests，確認輸入 `ScanFact` 後輸出正確 decision。
- [ ] 加 unknown rule / weak dependency / unsupported provider tests，確認回
  `no_match` 或 `unmapped_review_item`，不 silent upgrade。

### Task 3：讓 ComponentDetectionService 只負責 orchestration

**檔案：**

- Modify: `src/systograph/core/services/component_detection_service.py`
- Test: `tests/unit/core/test_component_detection_service.py`

- [ ] `ComponentDetectionService.detect()` 改為呼叫
  `ComponentBridgeRegistry.match(...)`。
- [ ] Service 保留 assemble / merge / sorting / manual mapping hook orchestration。
- [ ] 移除散落的大型 `_vector_store_candidates()`、`_llm_candidates()` 等 rule
  branching，或縮成 registry 使用的 private helper。
- [ ] 保持 constructor 可注入 registry，讓 tests 可用 fake registry 驗證 orchestration。
- [ ] 確認 injected `ComponentDetectionService` / registry 不被 `MapBuildService`
  靜默替換。

### Task 4：明確處理 non-baseline capability signal

**檔案：**

- Modify: `src/systograph/core/services/component_bridge_registry.py`
- Modify: `src/systograph/core/services/component_detection_service.py`
- Modify: `src/systograph/core/services/manual_mapping_service.py`
- Test: `tests/unit/core/test_manual_mapping_service.py`

- [ ] Registry 可把 reranker/router/tool-like evidence 標成
  `non_baseline_capability_signal` 或 `unmapped_review_item`，但不直接寫入
  `ai_system_map.json`。
- [ ] 未確認前，high-impact ambiguous item 進 `unmapped_components[]` / review
  queue；low-impact ambiguous evidence 可只留 evidence table / detail。
- [ ] `ManualMappingService` 套用 confirmed
  `non_baseline_capability_candidate` 後，materialize 到
  `ComponentDetectionResult.capability_candidate_components`。
- [ ] `profile_signals.json.capability_candidate_components` 只由 Step 6 sidecar
  writer 輸出；Step 4 canonical map 不包含它。

### Task 5：Boundary tests，防止 Step 4 規則移進 TOML

**檔案：**

- Create or modify: `tests/unit/core/test_component_bridge_boundaries.py`
- Modify: `src/systograph/core/services/rule_catalog_loader.py`（只有必要時）

- [ ] 測試 `RuleCatalogLoader` 不提供 `load_component_bridge_rules()`。
- [ ] 測試 `component_bridge_registry.py` 不讀取 `core/rules/*.toml`。
- [ ] 測試 `code_pattern_rules.toml` / `dependency_manifest_rules.toml` /
  `docker_image_rules.toml` 中不得出現 `plane_id`、`reference_node_id`、
  `profile_id`、`canonical_type`、`legacy_slot` 等 Step 4/6 output 欄位。
- [ ] 測試 future metadata TOML 若存在，也不得含 `condition`、`threshold`、
  `status_weight`、`mapping_type`、`accept_action` 這類 executable fields。

### Task 6：文件與 handoff 對齊

**檔案：**

- Modify: `docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/README.md`
- Modify: `docs/work/Timmy/schedule/plan/unfinish/phase2/README.md`
- Modify: `docs/work/Timmy/schedule/plan/unfinish/phase4-scanner-expansion/00-phase2-pipeline-ascii-map.md`
- Optional: `docs/MODEL-CONTRACT.md`

- [ ] 文件明確寫：Phase A 由 Systograph TOML providers 負責 primary raw facts；Gate-1 通過並完成
  Plan 16 後，Phase B 才由 UA sidecar / adapter 接手 primary，TOML providers 轉為 parity；
  Step 4 Python registry 在兩階段都負責 component bridge。
- [ ] 文件明確寫：list + for loop 是允許的 implementation pattern，但必須包在專門
  Python module，不可散在 service method。
- [ ] 文件明確寫：capability candidate input 不等於 canonical component，也不等於
  profile detected。
- [ ] 對齊 `needs_review` vs current v1 `needs_confirmation` 的 migration wording。

## 驗收標準

- [ ] Step 4 component bridge 有專門 Python module，且 `ComponentDetectionService`
  不再承載主要 rule table。
- [ ] 新增 scanner rule 時，開發者知道要同步：
  1. Step 3 raw detector TOML/provider；
  2. Step 4 Python bridge registry；
  3. Step 6 profile/readiness tests（若 relevant）。
- [ ] 沒有新 TOML catalog 擁有 component bridge、profile trigger 或 reference-node
  assessment logic。
- [ ] Existing v1 fixtures 與 manual mapping compatibility tests 通過。
- [ ] Generic v2 fixtures 可表達 non-RAG LLM app、tool-using agent、workflow graph，
  不被 forced into `rag-core-v1` slot completeness。

## 參考

- `01-rework-manual-mapping-capability-candidates.md`
- `01A-define-ai-system-capability-map-reference-catalog.md`
- `02-implement-stackable-profile-inference.md`
- `03A-implement-apply-build-lineage-and-local-json-persistence.md`
- `10-define-profile-rule-catalog-boundary.md`
- `docs/work/Timmy/schedule/plan/unfinish/phase4-scanner-expansion/00-phase2-pipeline-ascii-map.md`
