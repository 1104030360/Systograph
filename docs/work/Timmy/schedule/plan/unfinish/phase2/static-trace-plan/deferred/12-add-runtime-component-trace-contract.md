# Runtime Component Trace Deferred Boundary 計畫

> **For agentic workers:** 本文件是 deferred boundary，不是 implementation
> checklist。active static path 00–11、13、14、15 未完成前不得依本文新增 runtime execution 功能。

**Goal:** 凍結 static system map 與 observed runtime trace 的語意邊界，避免把
static capability inference 假裝成單次 query 的實際路徑。

**Architecture:** Phase2 canonical map、capability overlays、
readiness findings、Mermaid 與 viewer projection全部來自 deterministic static facts。
未來 runtime trace 必須由 target runtime explicit envelope 或可驗證 telemetry 提供，
只作 transient highlight，不寫回 canonical/profile artifacts。

**Tech Stack:** 僅 contract/ADR 文件；未來實作可能使用現有 Pydantic trace models、
FastAPI route、React replay UI，但不在本計畫執行。

---

## 2026-07-07 UA 整合對齊

UA 整合不改變本計畫範圍。`ua-analysis-result` 與 static execution artifacts 都是
static evidence / candidate input，不是 observed runtime trace。Runtime trace 仍必須由
未來 target runtime explicit envelope 或可驗證 telemetry 提供，且不得寫回
canonical/profile artifacts。

## 執行摘要

### 目標

記錄未來 runtime trace 必須回答「這次 query 實際走過哪些 components」，不能由
static map 推測。

### 背景

Static scan 可證明 component、edge、agent controller 或 reranker 看起來存在，但
cache、feature flag、conditional routing、fallback 或 error 可能讓單次 query 跳過它。

### 目前 code 狀態

`QueryTraceService` 只做 opt-in black-box endpoint request/response；SSE route 回單一
完成事件，尚無可信的 internal typed steps。這不阻擋 static readiness MVP。

### 相關檔案

- `src/systograph/core/services/query_trace_service.py`
- `src/systograph/core/models/trace.py`
- `src/systograph/core/providers/endpoint_call_provider.py`
- `src/systograph/web/routes/trace_routes.py`
- `frontend/src/components/ReplayTimeline.tsx`
- `docs/security/query-trace-egress-policy.md`

### 實作步驟

本輪只保留 typed reference、no-mutation、unknown-ref、masking/bounds 與 opt-in
原則。若未來另行批准，必須先建立獨立 implementation plan（見
[`../dynamic-trace-plan/01-implement-runtime-component-trace-mvp.md`](../dynamic-trace-plan/01-implement-runtime-component-trace-mvp.md)），再以 TDD 實作。

### 驗收標準

00–11/13/14/15、CLI、reports、Mermaid 與 Viewer 不宣稱 static profile 是 runtime proof；
沒有 runtime trace 也能完成 Phase2 release-readiness acceptance。

### 風險與注意事項

不得把本文件的 future envelope 當成已支援 API。不得讓 Plan 13 cutover 或 Plan 14
驗收依賴 target app 配合回傳 trace。

## Frozen Future Contract

未來可考慮：

```text
TraceComponentRef.ref_type =
  endpoint
  component
  edge
  grounding_dimension
  capability_candidate
  capability_profile
```

Future requirements：

- runtime trace opt-in、transient、bounded、masked；
- target runtime 必須 explicit 回報，backend 不從 static topology合成 steps；
- unknown refs 顯示 warning，不建立 graph node/edge；
- trace 可 focus 已存在 projection elements，但不修改 map/profile/readiness；
- v1 refs 先經 00A adapter 對應 normalized v2 ids；
- runtime security/egress review 必須在未來 implementation plan 重新執行。
- capability `activation` 仍是 static config/code assessment，不等於 observed runtime
  execution；即使顯示 `enabled`，也不可宣稱單次 request 實際 traversed 該節點。

## 驗收標準

- [ ] Plan 12 未列入 00–11、13 或 14 的 dependency gate。
- [ ] Static reports 使用 `appears`, `detected by static evidence`, `undetermined`
  等語意，不使用 `executed` 或 `traversed`。
- [ ] Viewer capability attachments 明確標示 static projection。
- [ ] `system_map.mmd` 不畫單次 query runtime animation/path。
- [ ] 本文件沒有可直接執行的 source modification tasks。

## 不在範圍內

- 不修改 Python/TypeScript source。
- 不新增 OpenTelemetry、trace persistence、replay 或 retention。
- 不要求 target app 實作 trace envelope。
- 不以 runtime observability 作為 Phase2 差異化。

## P0 Execution Mapping 補充（2026-07-03）

P0 新增 static inferred execution map 後，本邊界更重要：

- dynamic `00` 的 `call_graph.json`、`dataflow_hints.json`、`execution_paths.json` 仍是 static
  artifacts，不是 runtime trace。
- Static reports 可說 "static evidence suggests this path"，不可說 "this query executed this
  path"。
- dynamic `01` runtime trace 若日後觀測到 target envelope，只能 transient focus existing ids；
  不自動把 `runtime_verified` 寫回 canonical map/profile/readiness。
- 本文件仍沒有 source modification tasks；dynamic `00` 與 dynamic `01` 才是實作計劃。
