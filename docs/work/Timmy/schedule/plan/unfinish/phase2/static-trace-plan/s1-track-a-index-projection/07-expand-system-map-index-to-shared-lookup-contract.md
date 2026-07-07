# 擴充 SystemMapIndex 為 Generic Shared Lookup Contract 實作計畫

> **2026-07-05 sequence sync：** 使用者確認 `05 -> 06 -> 07`。本計畫在 Plan 06 第一條
> projection vertical slice 通過後才擴充 lookup；不得反向阻塞 Plan 06，也不得將
> reference catalog、五態 evaluator 或 frontend filter logic 塞進 index。

## 2026-07-07 UA 整合對齊

UA 整合不改變本計畫範圍。Shared lookup contract 仍只服務 normalized `AiSystemMapV2` 與
derived artifacts 的 canonical refs；`ua-analysis-result` 保持 scan snapshot internal
sidecar，不納入 `SystemMapIndex` public API。

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:subagent-driven-development` or `superpowers:executing-plans`.

**Goal:** 將 Plan 05 的 minimal index 擴成 normalized `AiSystemMapV2` 的 shared、
read-only lookup contract，供 readiness、profiles、renderers 與 selected consumers
重用。

**Architecture:** `SystemMapIndex` 只索引 generic canonical facts，不 validate、
mutate、persist、rescan、infer profile、決定 readiness 或產生 graph ids。v1 input
必須先經 00A `CanonicalMapLoader`；index 不知道 schema migration 細節。

**Tech Stack:** Python 3.11、Pydantic v2 `AiSystemMapV2`、frozen dataclass、pytest。

---

## 執行摘要

### 目標

建立 component/edge/evidence/layer/type/endpoint/risk/grounding dimension 的單一
deterministic lookup surface，避免各 service 重複建立 dict 與 missing-id semantics。

### 背景

Profile inference、readiness report、Mermaid、viewer、detail scan 與 proposal packet
都需要相同 facts。若各自 lookup，evidence order、project-relative location、unknown
reference 與 v1 compatibility 會漂移。

### 目前 code 狀態

Repo 尚無 `SystemMapIndex`。現有 viewer、detail scan、validation 與 routes 都直接對
`RagSystemMap` 建立 local maps；00A 將新增 normalized v2 boundary。

### 相關檔案

- Create: `src/kai_mind/core/services/system_map_index.py`
- Create: `tests/unit/core/test_system_map_index.py`
- Read: `src/kai_mind/core/models/ai_system_map_v2.py`
- Read: `src/kai_mind/core/services/canonical_map_loader.py`
- Read: `src/kai_mind/core/services/system_map_validation_service.py`

### 實作步驟

先寫 found/missing/order/no-mutation tests，再實作 frozen index；加入 dependency
guardrails，最後只讓新 readiness/profile/renderer modules 使用。既有 consumer
migration 留給 08。

### 驗收標準

相同 normalized v2 input 永遠回傳相同 ordering；unknown ids 回 `None`/empty；index
不改 map、不讀 filesystem、不決定任何 domain status。

### 風險與注意事項

不要把 index 做成 god object。Workflow node projection、profile attachment anchors、
validation invariants、mapping replay、LLM assist 與 runtime trace 留在 owning service。

## Public Contract

```python
@dataclass(frozen=True)
class SystemMapIndex:
    system_map: AiSystemMapV2

    @classmethod
    def from_map(cls, system_map: AiSystemMapV2) -> "SystemMapIndex": ...

    def component_by_id(self, component_id: str) -> CanonicalComponent | None: ...
    def edge_by_id(self, edge_id: str) -> CanonicalEdge | None: ...
    def evidence_by_id(self, evidence_id: str) -> CanonicalEvidence | None: ...
    def endpoint_by_id(self, endpoint_id: str) -> CanonicalEndpoint | None: ...
    def risk_by_id(self, risk_id: str) -> RiskHint | None: ...
    def grounding_dimension_by_id(
        self, dimension_id: str
    ) -> GroundingDimensionResult | None: ...
    def components_by_type(self, canonical_type: str) -> tuple[CanonicalComponent, ...]: ...
    def components_by_layer(self, layer: str) -> tuple[CanonicalComponent, ...]: ...
    def outgoing_edges(self, component_id: str) -> tuple[CanonicalEdge, ...]: ...
    def incoming_edges(self, component_id: str) -> tuple[CanonicalEdge, ...]: ...
    def evidence_for_ids(self, ids: Iterable[str]) -> tuple[CanonicalEvidence, ...]: ...
    def related_locations_for_evidence_ids(
        self, ids: Iterable[str]
    ) -> tuple[CanonicalEvidenceLocation, ...]: ...
```

Capability candidates 與 profile findings 屬 sidecar，不放入 canonical index。需要時
由 profile service 建立小型 sidecar index，不能用 extension lookup 冒充。

## Task 1：Characterization Tests

- [ ] 建立 grounded RAG、non-grounded LLM、tool agent、workflow graph v2 fixtures。
- [ ] 先寫 failing tests：found/missing、type/layer grouping、edge directions、evidence
  order、duplicate location removal、JSON pointer preservation、no mutation。
- [ ] 執行：

```bash
.venv/bin/pytest tests/unit/core/test_system_map_index.py -q
```

Expected：因 module 尚不存在而 FAIL。

## Task 2：Minimal Frozen Index

- [ ] 實作 frozen dataclass 與 private immutable lookup dictionaries。
- [ ] 保留 input list order；只在 API 明確要求 sorted ids 時排序。
- [ ] Related locations 以 `(path, line/json_pointer/config_key)` 去重，不讀檔案。
- [ ] Unknown refs 回 `None`/empty tuple；schema invariant errors 由 validator 負責。
- [ ] 執行 focused tests，預期 PASS。

## Task 3：Boundary Guardrails

- [ ] Source dependency test 禁止 import viewer/routes/repositories/filesystem providers、
  mapping/manual services、query trace、LLM providers。
- [ ] Public API test 禁止 `save/apply/validate/infer/project/render` methods。
- [ ] Test 證明 index 不輸出 `primary_map_type`、profile status 或 readiness verdict。

## Task 4：Integration with New Modules

- [ ] Plan 02 profile inference、Plan 03 readiness writer、Plan 06 renderers 可使用 index。
- [ ] 不在本計畫修改 detail scan/proposal routes；由 08 characterization 後遷移。
- [ ] 不讓 07 阻擋 02/03/05/06 的 first vertical slice；只在第二個 refactor batch 執行。

## 驗收標準

- [ ] `SystemMapIndex.from_map()` 只接受 normalized `AiSystemMapV2`。
- [ ] Lookup 涵蓋 generic components、edges、evidence、endpoints、risks 與 grounding dimensions。
- [ ] Workflow JSON evidence locations 保留 JSON pointer。
- [ ] Index read-only、dependency-light、deterministic。
- [ ] v1/v2 branching 只存在 `CanonicalMapLoader`，不出現在 index。
- [ ] Focused tests、相關 profile/renderer tests、Ruff、Mypy 通過。

## 不在範圍內

- 不建立 persistence/cache/query language。
- 不索引 raw scanner facts或讀 target filesystem。
- 不擁有 profile/readiness/LLM/rendering logic。
- 不遷移既有 consumers。

## P0 Execution Mapping 補充（2026-07-03）

Shared lookup contract 需納入 execution artifact refs：

- `call_graph.json` 的 caller/callee、`dataflow_hints.json` 的 source/target 與
  `execution_paths.json` 的 step component refs 都必須可透過 shared lookup 驗證。
- Lookup contract 只解析 ids 與 evidence locations；不做 AST parsing、不跑 dataflow、不排序 path。
- Workflow JSON edge 的 JSON pointer evidence 必須保留，供 execution path detail panel 導覽。
- v1/v2 branching 仍只在 `CanonicalMapLoader`；execution artifacts 一律以 normalized v2 refs
  作 source of truth。
