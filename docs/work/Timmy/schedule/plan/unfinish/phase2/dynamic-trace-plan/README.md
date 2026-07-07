# Dynamic Trace Plan

動態 **runtime / query trace** 與 trace-adjacent execution mapping 計劃。與
[`../static-trace-plan/`](../static-trace-plan/) 的靜態 readiness 主線分開編號，但
dynamic `00` 是 P0 static inferred execution map 的橋接計劃，不是 runtime trace。

## 與 Static 的關係

| 層次 | 位置 | 內容 |
|---|---|---|
| 邊界 / ADR | static Plan `12` | 凍結 static vs runtime 語意；不實作 source changes |
| Static inferred execution map | dynamic `00` | `call_graph.json`、`dataflow_hints.json`、`execution_paths.json`、`execution_map.mmd` |
| Black-box MVP | finished Plan `22` | opt-in endpoint 呼叫；無 typed internal steps |
| Runtime trace MVP | dynamic `01` | typed `trace_steps` / `component_ref`、viewer transient focus |

```text
static 00A/03/05
        |
        v
dynamic 00 (static inferred call graph + execution paths)
        |
        v
static 13 -> static 14 validation -> static 15 complete retirement
        |
        v
dynamic 01 (runtime typed steps, opt-in)
```

## 前置條件

- dynamic `00`：需要 `00A` normalized v2 contract，並對齊 `03` artifact lifecycle 與
  `05` lookup primitives。
- dynamic `01`：Static path 至少完成 active `00`～`15`，且 Plan `12` runtime boundary 已凍結。
- 所有實作不得寫回 `ai_system_map.json` / `profile_signals.json` 作為新的 canonical truth。
- 安全：runtime trace 類計劃須重新驗收 `docs/security/query-trace-egress-policy.md`。

## 計畫一覽

| # | 檔案 | 狀態 | 主題 |
|---:|---|---|---|
| 00 | [00-implement-static-call-graph-and-execution-path-mvp.md](./00-implement-static-call-graph-and-execution-path-mvp.md) | draft | Static call graph、shallow dataflow、execution path artifacts |
| 01 | [01-implement-runtime-component-trace-mvp.md](./01-implement-runtime-component-trace-mvp.md) | draft | Typed runtime trace contract + backend MVP + viewer transient focus |

## 依序完成什麼

1. `README.md`：定義 dynamic trace plan 的邊界與順序，先把 static inferred
   execution map、finished black-box trace、future runtime trace 三者分清楚。
2. `00-implement-static-call-graph-and-execution-path-mvp.md`：先完成不發送 runtime
   request 的 static execution artifacts，包括 `call_graph.json`、`dataflow_hints.json`、
   `execution_paths.json`、`evidence_table.json` 與 `execution_map.mmd`；所有結果都必須標成
   static inferred / `runtime_verified=false`。
3. `01-implement-runtime-component-trace-mvp.md`：等 static path 完成後，再擴充現有
   Query Trace，讓 opt-in `/api/trace` 回傳 typed `trace_steps[]`、`component_ref` 與 viewer
   transient focus；trace 結果仍不得寫回 canonical map、profile 或 readiness artifacts。

## 相關文件（repo 內）

- Static boundary：[`../static-trace-plan/deferred/12-add-runtime-component-trace-contract.md`](../static-trace-plan/deferred/12-add-runtime-component-trace-contract.md)
- Static plan index：[`../static-trace-plan/README.md`](../static-trace-plan/README.md)
- 已完成 black-box trace：[finished Plan 22](../../../finish/22-implement-query-trace-mvp.md)
- Frontend 方向（等 backend sample 與產品決策）：[frontend-runtime-trace.md](../../../../../../Meeting-Sync/meeting_sync_2026_07_07/frontend-runtime-trace.md)
- API：`docs/API-GUIDE.md`、`frontend/API_CONTRACT.md`

## 不在本 folder

- Langflow/Dify/Flowise 完整 importer 或 round-trip
- OpenTelemetry 整合、trace persistence / retention、跨 request 聚合
- 用 static graph 假裝 runtime path
- 將 trace 結果自動升級 mapping / profile / readiness verdict
