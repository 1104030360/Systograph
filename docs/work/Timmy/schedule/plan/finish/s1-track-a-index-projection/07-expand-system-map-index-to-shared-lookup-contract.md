# 擴充 SystemMapIndex 為 Generic Shared Lookup Contract 實作計畫

> **狀態：已完成（2026-07-12）。** Backend implementation與驗證全部通過。

> **2026-07-05 sequence sync：** 使用者確認 `05 -> 06 -> 07`。本計畫在 Plan 06 第一條
> projection vertical slice 通過後才擴充 lookup；不得反向阻塞 Plan 06，也不得將
> reference catalog、五態 evaluator 或 frontend filter logic 塞進 index。

> **2026-07-11 live-state sync：** 00A loader/adapter/v2 validation與四組 v2 fixtures已完成。
> 執行本計畫前，Plan 05 minimal index與 Plan 06A base graph必須已通過。本計畫只依
> 06A/06B與 Plan 08 的真實 caller需求擴充 grouping/direction/location lookup；不索引
> profile/readiness/grounding sidecars，也不重複 `SystemMapV2ValidationService`。

## 2026-07-07 UA 整合對齊

UA 整合不改變本計畫範圍。Shared lookup contract 仍只服務 normalized `AiSystemMapV2` 與
derived artifacts 的 canonical refs；`ua-analysis-result` 保持 scan snapshot internal
sidecar，不納入 `SystemMapIndex` public API。

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:subagent-driven-development` or `superpowers:executing-plans`.

**Goal:** 將 Plan 05 的 minimal index 擴成 normalized `AiSystemMapV2` 的 shared、
read-only lookup contract，供 Plan 06B projection/renderers與 Plan 08 selected consumers
重用。

**Architecture:** `SystemMapIndex` 只索引 generic canonical facts，不 validate、
mutate、persist、rescan、infer profile、決定 readiness 或產生 graph ids。v1 input
必須先經 00A `CanonicalMapLoader`；index 不知道 schema migration 細節。

**Tech Stack:** Python 3.11、Pydantic v2 `AiSystemMapV2`、frozen dataclass、pytest。

---

## 執行摘要

### 目標

建立 component/edge/evidence/layer/type/endpoint/risk/unmapped/candidate 的單一
deterministic lookup surface，避免各 service 重複建立 dict與 missing-id semantics。

### 背景

Graph projection/renderers、detail scan read-only resolution 與 proposal packet都需要
相同 canonical facts。若各自 lookup，evidence order、project-relative location、unknown
reference與 v1 compatibility會漂移。Profile inference/readiness目前已有自己的 semantic
owner，不是本計畫 migration target。

### 目前 code 狀態

截至 2026-07-11 live baseline，repo 尚無 `SystemMapIndex`；00A normalized v2 boundary、
v2 validator與 fixtures已存在。Plan 05 execution會先建立 singular lookups，Plan 06A會成為
第一個 consumer；本計畫不可在兩者通過前先做 speculative expansion。

### 相關檔案

- Create: `src/kai_mind/core/services/system_map_index.py`
- Create: `tests/unit/core/test_system_map_index.py`
- Read: `src/kai_mind/core/models/ai_system_map_v2.py`
- Read: `src/kai_mind/core/services/canonical_map_loader.py`
- Read: `src/kai_mind/core/services/system_map_v2_validation_service.py`

### 實作步驟

先寫 found/missing/order/no-mutation tests，再實作 frozen index；加入 dependency
guardrails，最後只讓 Plan 06 projection/renderers使用擴充 methods。既有 consumer
migration留給 Plan 08。

### 驗收標準

相同 normalized v2 input 永遠回傳相同 ordering；unknown ids 回 `None`/empty；index
不改 map、不讀 filesystem、不決定任何 domain status。

### 風險與注意事項

不要把 index 做成 god object。Workflow node projection、profile attachment anchors、
validation invariants、mapping replay、LLM assist 與 runtime trace 留在 owning service。

## Public Contract

```python
@dataclass(frozen=True, slots=True)
class SystemMapIndex:
    @classmethod
    def from_map(cls, system_map: AiSystemMapV2) -> "SystemMapIndex": ...

    def component_by_id(self, component_id: str) -> CanonicalComponent | None: ...
    def edge_by_id(self, edge_id: str) -> CanonicalEdge | None: ...
    def evidence_by_id(self, evidence_id: str) -> CanonicalEvidence | None: ...
    def endpoint_by_id(self, endpoint_id: str) -> CanonicalEndpoint | None: ...
    def risk_by_id(self, risk_id: str) -> CanonicalRiskHint | None: ...
    def unmapped_by_id(
        self, unmapped_id: str
    ) -> CanonicalUnmappedComponent | None: ...
    def candidate_fact_by_id(
        self, candidate_fact_id: str
    ) -> CanonicalCandidateFact | None: ...
    def components_by_type(self, canonical_type: str) -> tuple[CanonicalComponent, ...]: ...
    def components_by_layer(self, layer: str) -> tuple[CanonicalComponent, ...]: ...
    def outgoing_edges(self, component_id: str) -> tuple[CanonicalEdge, ...]: ...
    def incoming_edges(self, component_id: str) -> tuple[CanonicalEdge, ...]: ...
    def evidence_for_ids(self, ids: Iterable[str]) -> tuple[CanonicalEvidence, ...]: ...
    def related_locations_for_evidence_ids(
        self, ids: Iterable[str]
    ) -> tuple[CanonicalEvidenceLocation, ...]: ...
```

`AiSystemMapV2.candidate_facts` 是 canonical compatibility facts，可由
`candidate_fact_by_id()` lookup；`ProfileInferenceResult.capability_candidate_components`、
profile findings、Mapping Completeness與 grounding/readiness均屬 sidecar，不放入
canonical index。需要時由 projection在 sidecar boundary建立局部 read-only maps，不能用
legacy extension或 canonical candidate fact冒充 profile identity。

## Task 1：Plan 05 Contract Characterization

- [x] 重用既有 grounded RAG、non-grounded LLM、tool agent、workflow graph v2 fixtures，
  不建立重複 fixture taxonomy。
- [x] 先確認 Plan 05 singular found/missing/order/no-mutation與 06A caller tests全數 PASS。
- [x] 再寫本計畫 failing tests：type/layer grouping、edge directions、multi-evidence input
  order、duplicate location removal與 JSON pointer/config key preservation。
- [x] 執行：

```bash
.venv/bin/pytest tests/unit/core/test_system_map_index.py -q
```

Expected：Plan 05 tests先 PASS；新增 grouping/direction/location tests因 methods尚不存在而
FAIL，且 failure reason不是 fixture/import錯誤。

## Task 2：Expand Frozen Index

- [x] 實作 frozen dataclass 與 private immutable lookup dictionaries。
- [x] 保留 input list order；只在 API 明確要求 sorted ids 時排序。
- [x] Related locations 以 `(path, start_line, end_line, json_pointer, config_key)` stable
  去重，不讀檔案、不檢查 path existence。
- [x] Unknown refs 回 `None`/empty tuple；schema invariant errors 由 validator 負責。
- [x] 執行 focused tests，預期 PASS。

## Task 3：Boundary Guardrails

- [x] Source dependency test 禁止 import viewer/routes/repositories/filesystem providers、
  mapping/manual services、query trace、LLM providers。
- [x] Public API test 禁止 `save/apply/validate/infer/project/render` methods。
- [x] Test 證明 index 不輸出 `primary_map_type`、profile status 或 readiness verdict。

## Task 4：Integration with Real Callers

- [x] Plan 06B projection/renderers可使用 grouping/direction/location helpers；不得把
  graph ids、filter membership、anchor selection或 semantic status搬入 index。
- [x] 不在本計畫修改 detail scan/proposal routes；由 Plan 08 characterization/equivalence
  matrix通過後遷移。
- [x] 不讓 Plan 07 反向阻擋已完成的 profile/readiness、Plan 05或 Plan 06A vertical
  slice；只在第二個 refactor batch執行。

## 驗收標準

- [x] `SystemMapIndex.from_map()` 只接受 normalized `AiSystemMapV2`。
- [x] Lookup 涵蓋 canonical components、edges、evidence、endpoints、risks、unmapped
  components與 candidate facts；derived grounding/profile/readiness明確不在 contract。
- [x] Workflow JSON evidence locations 保留 JSON pointer。
- [x] Index read-only、dependency-light、deterministic。
- [x] Index與新 normalized-v2 consumers不含 schema branching；既有 v1 compatibility
  surface在 Plan 13 前可保留，但只能透過 `CanonicalMapLoader` 進入新 index/projection。
- [x] Focused tests、Plan 06 projection/renderer tests、Ruff、scoped Mypy通過。

## 驗證

```bash
.venv/bin/pytest tests/unit/core/test_system_map_index.py \
  tests/unit/core/test_graph_projection_service.py \
  tests/unit/core/test_reference_map_overlay_projector.py -q
.venv/bin/ruff check src/kai_mind/core/services/system_map_index.py \
  tests/unit/core/test_system_map_index.py
.venv/bin/mypy src/kai_mind/core/services/system_map_index.py \
  tests/unit/core/test_system_map_index.py
git diff --check -- \
  docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/s1-track-a-index-projection/07-expand-system-map-index-to-shared-lookup-contract.md
```

## 不在範圍內

- 不建立 persistence/cache/query language。
- 不索引 raw scanner facts或讀 target filesystem。
- 不擁有 profile/readiness/LLM/rendering logic。
- 不遷移既有 consumers。

## P0 Execution Mapping 補充（2026-07-03）

Shared lookup contract可服務 execution artifact display refs，但不接管 validation：

- `call_graph.json` 的 caller/callee、`dataflow_hints.json` 的 source/target與
  `execution_paths.json` 的 component refs若需在 UI/detail resolve，可透過 shared lookup；
  ref integrity仍由 normalized v2 validator與 artifact load boundary驗證。
- Lookup contract 只解析 ids 與 evidence locations；不做 AST parsing、不跑 dataflow、不排序 path。
- Workflow JSON edge 的 JSON pointer evidence 必須保留，供 execution path detail panel 導覽。
- 現有 `StaticExecutionArtifactService` 從已驗證 normalized v2直接產生 artifacts；index
  不重跑 validator，也不為 generated artifact建立第二套 truth。
- v1/v2 branching仍只在 `CanonicalMapLoader`；execution artifacts一律以 normalized v2 refs
  作 source of truth。
