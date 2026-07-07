# 前端同步：Runtime Trace Deferred Boundary

Last updated: 2026-07-07（UA 整合決策對齊）

2026-07-07 UA 整合決策：本文件範圍不受影響；UA sidecar 屬 static scan / snapshot internal，
不改變 runtime trace deferred boundary。

## 目的（Purpose）

Plan `12` 是 deferred boundary 文件。它不會在 Phase2 static path 啟動 runtime trace 實作。

Static plans 現已包含 `dynamic-trace-plan/00`，但該檔是 **static inferred execution
mapping**，不是 runtime tracing。Runtime 實作稍後由 dynamic `01` 開始。

## 目前決策（Current Decision）

Frontend 應理解邊界，但不應依 static plan `12` 建立新的 runtime trace UI。

```text
Static execution map
  = scanner-inferred architecture path
  = call_graph.json / dataflow_hints.json / execution_paths.json
  = runtime_verified=false

Runtime trace
  = opt-in endpoint call / target-provided trace envelope
  = transient focus
  = does not write back to artifacts
```

## Frontend 規則

- 不要用 static graph / profile / static execution artifacts 宣稱某次 query 實際走了該 path。
- 不要從 `execution_paths.json` 合成 runtime `trace_steps`。
- 不要從 runtime trace 新增 graph nodes/edges。
- 不要將 trace 結果寫入 `ai_system_map.json`、`profile_signals.json` 或 execution artifacts。
- 若舊 trace payload 沒有 typed `trace_steps`，維持 black-box replay 行為。

## 未來 Runtime Trace Contract

Dynamic `01` 啟動時，frontend 應等待 backend sample/API payload 含 typed refs，例如：

```text
trace_steps[].component_ref.ref_type
trace_steps[].component_ref.ref_id
trace_steps[].status
trace_steps[].warnings
```

Possible ref types 由 backend 定義。Frontend 不得自行發明 ref types。

## 與 Static Execution Map 的互動

Static execution UI 可顯示：

- "static evidence suggests"；
- "appears to flow"；
- `runtime_verified=false`；
- limitations。

不得顯示：

- "executed"；
- "traversed at runtime"；
- "this query went through"；
- runtime latency 或 status（除非 `/api/trace` 提供）。

## 驗收標準（Acceptance Criteria）

- [ ] Runtime trace 工作仍自 static plan `12` deferred。
- [ ] Frontend 不從 static artifacts 合成 runtime path。
- [ ] Static execution 標籤明確標示 static inferred。
- [ ] 既有 black-box trace UI 與 static execution map 分離。
- [ ] 未來 dynamic `01` 需 backend sample 後才開始 frontend 實作。

## 禁止事項（Do Not Do）

- 不要依本 sync 開始 runtime trace 實作。
- 不要把 `execution_paths.json` 當 runtime proof。
- 不要從 trace UI mutate artifacts。
- 不要在 backend contract 存在前新增 frontend-only `component_ref` 解析規則。
