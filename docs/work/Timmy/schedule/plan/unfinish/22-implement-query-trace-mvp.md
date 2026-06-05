# Task 22: Implement Query Trace MVP

## 目標
實作 opt-in `QueryTraceService` 與 local web trace API，在使用者明確指定 endpoint/query 後呼叫一次 detected RAG endpoint，收集 basic trace result，映射成 `QueryTraceEvent[]`。找不到 endpoint 或 timeout 時必須保留 partial replay。

## 為什麼要先做這個
Query trace 會呼叫 runtime endpoint，可能有副作用，因此必須在 static map、viewer boundary、detail scan 都穩定後才做。它支援 replay UX；因為 Epic 1 優先 GUI/local web UI，本任務先提供 local API，CLI `kai-mind trace` 仍保留為同服務的 thin adapter。

## 承接 Task 16 延後功能
- 承接 Task 16 「不做 query trace / runtime endpoint 呼叫」的延後範圍。
- Task 16 的 map build 與 `GET /api/map` 永遠不得預設呼叫 runtime endpoint。
- 本任務才可建立會送出 query 的 local API，但必須由使用者明確提供 endpoint/query 並 opt-in。
- 若 Task 16 已建立 basic `GET /api/scan/events`，本任務可延伸 replay/progress event，但不得改壞既有 event target priority。

## 前置需求
- Task 14 已有 endpoint detection。
- Task 15 已有 QueryTraceEvent model/validation。
- Task 18 已有 graph projection。
- Task 21 已有 replay depth/detail scan 基礎。

## 實作範圍
- 建立 `EndpointCallProvider`。
- 建立 `QueryTraceService`。
- 使用 FastAPI 建立 local web trace route / handler。
- 更新 Epic 1 local API guide，加入 query trace endpoint、opt-in 規則、side-effect 警告與 masking 規則。
- CLI 採已決策選項 A：獨立命令 `kai-mind trace <map_json> --endpoint-id ... --query ...`，但不得繞過 `QueryTraceService`。
- 找不到 endpoint 回傳 `endpoint_not_found` 且 `query_sent=false`。
- timeout/error 產生 trace event，不丟棄 partial replay。
- input/output/retrieved_chunks 必須 masking。
- confirmed extension/unmapped trace step mapping。
- 明確承接 Task 14 未解決的 unmapped flow 問題：未確認的 unmapped component 不進 baseline `Flow.edges`，但 replay 若觀察到相關 evidence，應以 `Unknown / Needs confirmation` step 保留 partial replay。

## 不包含範圍
- 不做 proxy wrapper。
- 不做 full runtime observability。
- 不預設在 `kai-mind map` 呼叫 endpoint。
- 不保存 raw sensitive query。
- 不把 trace 觀察到的 unmapped component 自動升級成 detected slot 或 confirmed extension。
- 不在 replay 中替使用者做 manual mapping；確認與持久化仍交給 Task 19/20。

## 建議實作步驟
1. 建立 `src/kai_mind/core/providers/endpoint_call_provider.py`。
2. 建立 `src/kai_mind/core/services/query_trace_service.py`。
3. 實作 endpoint selection by endpoint_id。
4. 實作 bounded timeout。
5. 實作 basic response/error to QueryTraceEvent mapping。
6. 實作 confirmed extension / unmapped trace step mapping：
   - standard slot match -> `slot`。
   - confirmed extension match -> `component_id` / extension step metadata。
   - unmapped evidence match -> unknown step / needs_mapping_confirmation warning，不寫入 baseline `Flow.edges`。
7. 實作 trace events append 或 trace result output。
8. 建立 FastAPI trace route，要求明確 endpoint/query input。
9. 更新 `docs/work/Timmy/design/epic1-local-api-guide.md`，補上 trace API request/response、`endpoint_not_found`、timeout/error response、masking rule。
10. 建立 `kai-mind trace` thin CLI adapter，呼叫同一個 service。
11. 測試 endpoint_not_found、timeout partial replay、masked input/output、web API 和 CLI 都不預設送 query；trace 遇到 unmapped evidence 時保留 unknown step，不讓 replay 失敗。

## 預期輸出
- `src/kai_mind/core/providers/endpoint_call_provider.py`
- `src/kai_mind/core/services/query_trace_service.py`
- `src/kai_mind/web/routes/trace_routes.py`
- `src/kai_mind/cli/trace_command.py`
- 更新 `docs/work/Timmy/design/epic1-local-api-guide.md`
- `tests/unit/core/test_query_trace_service.py`
- `tests/web/test_trace_routes.py`
- `tests/cli/test_trace_command.py`

## 驗收標準
- trace 預設不會在 map command 執行。
- `kai-mind map` 不接受會呼叫 runtime endpoint 的 trace option；trace 必須走 `kai-mind trace`。
- local web trace API 必須由使用者明確送出 endpoint/query 才會呼叫 runtime endpoint。
- missing endpoint 不送 query。
- timeout/error 保留 partial replay event。
- trace step 可映射 standard slot、confirmed extension 或 unknown/unmapped。
- full query/output secret 不出現在 event。
- API guide 已同步記錄 trace API 必須 opt-in、不得由 map build 預設觸發、以及敏感資料 masking 規則。
- 未確認的 unmapped component 在 replay 中只能顯示為 unknown / needs_confirmation，不得變成 confirmed extension step。
- confirmed manual mapping 後，重新 normalize / regenerate 的 map 才能讓 replay 顯示正式 extension step。
- replay unknown step 不修改 canonical baseline `flows`，避免把 runtime observation 誤寫成靜態架構事實。

## 可能風險與注意事項
- 呼叫 endpoint 是 side effect，必須 opt-in。
- 測試應使用 mock HTTP server，不依賴真實服務。
- trace API contract 改動會直接影響 replay UI 和 desktop app，因此改 endpoint / response / error code 時必須同步更新 API guide。
- 參考依據：OpenTelemetry GenAI docs 提醒 inputs/outputs 敏感；OpenInference span kinds 可作 Retriever/LLM/Embedding/Tool vocabulary 參考。
- 如果 `QueryTraceEvent` 現有 schema 無法表達 `unmapped_component_id`、`step_type=unknown` 或 warning，必須在 Task 15/本任務中同步擴充模型與 validation；不可用任意 extra fields 繞過 contract。

## 新手提示
Query trace 是「真的問系統一次」。因為會碰 runtime，所以不能偷偷做，必須使用者明確要求。

## 視覺化說明
```text
┌──────────────┐
│ map_json     │
└──────┬───────┘
       ↓
┌──────────────────────┐
│ QueryTraceService     │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ endpoint found?       │
└──────┬─────────┬─────┘
       │ no      │ yes
       ↓         ↓
┌──────────────────────┐ ┌──────────────────────┐
│ endpoint_not_found    │ │ EndpointCallProvider  │
│ query_sent = false    │ └──────────┬───────────┘
└──────────────────────┘            ↓
                         ┌──────────────────────┐
                         │ QueryTraceEvent       │
                         └──────────┬───────────┘
                                    ↓
                         ┌──────────────────────┐
                         │ timeout/error keeps   │
                         │ partial replay        │
                         └──────────────────────┘
```
