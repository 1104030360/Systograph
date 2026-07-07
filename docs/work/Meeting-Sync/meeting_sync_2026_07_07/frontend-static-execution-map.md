# 前端同步：Static Execution Map

Last updated: 2026-07-07（UA 整合決策對齊）

## 目的（Purpose）

Dynamic plan `00` 是 static execution mapping MVP。雖位於 `dynamic-trace-plan`，
但它不是 runtime trace。

Frontend 應準備顯示 backend 提供的 static inferred execution artifacts。

## Backend Artifacts

預期 artifacts：

```text
call_graph.json
dataflow_hints.json
execution_paths.json
evidence_table.json
execution_map.mmd
```

這些 artifacts 的來源依 staged rollout 切換：Phase A 使用現有 KAI scan TOML provider facts；
Phase B 使用 UA-primary structural facts（imports、symbols、endpoints、call-like hints）並保留
TOML parity；Phase C 為 UA only。它們也可使用 workflow JSON edges 與既有 map components，
且必須含 static-only limitations 與 `runtime_verified=false`。

2026-07-07 UA 整合決策不改變 static execution artifact schema；semantic sidecar 是
reserved nullable snapshot internal slot，Phase2 active path 不產生、不消費，不是 frontend
可依賴的資料來源。`ua_analysis_result=null` 不阻擋 build / Apply。

## UI 語意

建議文案：

```text
Static evidence suggests this path.
This path is inferred from code/config/workflow artifacts.
Runtime execution is not confirmed.
```

避免：

```text
This query executed this path.
The app traversed these steps.
Runtime path confirmed.
```

## 建議 Views

Frontend 可呈現為：

- static execution path panel；
- call graph view；
- dataflow hints list；
- 渲染的 `execution_map.mmd`；
- 以 evidence id 連結的 evidence drill-down。

每個 view 在資料 partial 或 undetermined 時必須顯示 limitations。

## 與 Runtime Trace 的互動

Static execution map 與 runtime trace 分離：

| Static execution map | Runtime trace |
|---|---|
| 來自 code/config/workflow scan | 來自 opt-in runtime endpoint response |
| 寫入 artifacts | Transient UI overlay |
| `runtime_verified=false` | 僅在 backend trace contract 指明時為 observed |
| Scan 後即可顯示 | 需 dynamic `01` contract |

Frontend 不得將 static execution path 轉成 runtime trace steps。

## 驗收標準（Acceptance Criteria）

- [ ] Static execution UI 明確標示 inferred status。
- [ ] `runtime_verified=false` 在 detail/limitations 可見或可理解。
- [ ] Unknown / partial paths 顯示 limitations，不製造 false certainty。
- [ ] Evidence ids 可連回 evidence detail（若可用）。
- [ ] Static execution artifacts 不 mutate canonical graph。

## 禁止事項（Do Not Do）

- 不要在 frontend infer call graph。
- 不要合成 missing execution paths。
- 除非 backend projection 明確要求，不要從 static execution artifacts 建立 graph nodes/edges。
- 不要在 static execution views 混入 runtime trace latency/status。
