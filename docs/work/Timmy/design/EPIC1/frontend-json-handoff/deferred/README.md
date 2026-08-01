# Deferred — Rich Runtime Trace Linkage

Last updated: 2026-07-15（current trace 與 future sample 分界）

Systograph current 已有 opt-in `POST /api/trace`，回傳 `TraceRunResult`，其 `events[]` 使用 current
`QueryTraceEvent`（`id`、`sequence_index`、`component_id`、`input`／`output` 等欄位）。

[`frontend-runtime-trace-event-sample.json`](frontend-runtime-trace-event-sample.json) 不是 current
Pydantic response；它是 future richer safe-linkage design，示範 `component_ref`、
`related_static_refs`、masked summaries 與 raw-content flags。Dynamic trace plan 尚未凍結這個
shape 前，frontend parser 不得依賴它。

| Future 欄位 | 用意 |
| --- | --- |
| `trace_id` / `event_id` | Trace 與事件 identity |
| `component_ref` | 安全對回 canonical／projection identity |
| `related_static_refs` | Optional static candidate linkage，不等於 runtime topology |
| `input_summary` / `output_summary` | 遮罩後摘要，不包含 raw prompt／answer |
| `raw_input_included` / `raw_output_included` | 明示 raw content 是否存在 |

Current 與 future 都必須遵守：trace 是使用者 opt-in 的 runtime observation；Step 6 static
call graph／dataflow／execution paths 不得偽裝成 trace event，也不得在 sample、log 或 report
洩漏 raw secret、完整 prompt、answer 或 absolute path。
