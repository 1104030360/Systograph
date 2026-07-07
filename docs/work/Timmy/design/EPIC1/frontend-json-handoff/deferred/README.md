# frontend-runtime-trace-event-sample.json 欄位說明(先不用做)

`QueryTraceEvent` preview — **future** runtime trace，不屬 Phase2 static P0。

| 欄位 | 白話 |
|------|------|
| `trace_id` / `event_id` | 一次 trace 與單一事件 |
| `event_type` | 如 `response_received` |
| `component_ref` | 對回 map 上的 component |
| `related_static_refs` | 可選：連到 static 掃到的 candidate |
| `input_summary` / `output_summary` | **已遮罩**的摘要，不含 raw prompt/answer |
| `raw_*_included` | 是否包含原始內容（sample 為 `false`） |
| `warnings` | 提醒：不可由 static execution 偽造 runtime trace |
