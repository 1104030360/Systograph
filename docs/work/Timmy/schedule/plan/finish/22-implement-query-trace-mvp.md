# Task 22: Implement Query Trace MVP

## 目標
實作 opt-in `QueryTraceService` 與 local web trace API，在使用者明確指定 endpoint/query 後呼叫一次 detected RAG endpoint，收集 basic trace result，映射成 `QueryTraceEvent[]` 或 trace run wrapper。找不到 endpoint 或 timeout/error 時必須保留 partial replay。

## 為什麼要先做這個
Query trace 會呼叫 runtime endpoint，可能有副作用，因此必須在 static map、viewer boundary、manual mapping、proposal flow、detail scan 都穩定後才做。它支援 replay UX；因為 Epic 1 優先 GUI/local web UI，本任務先提供 local API，CLI `systograph trace` 仍保留為同服務的 thin adapter。

## 最新 repo 進度校正（2026-06-09）
目前 repo 已完成的前置能力：

- Task 14 endpoint detection 已存在：`EndpointDetectionService` 從 static facts 推導 Docker published port / internal service URL / OpenAI default endpoint / Chroma HTTP client endpoint。它不做 runtime probing。
- Task 15 `QueryTraceEvent` model 已存在於 `src/systograph/core/models/system_map.py`，但目前欄位仍偏 minimal：`slot`、`component_id`、`edge_id`、`input`、`output`、`error`、`retrieved_chunks` 等。若 Task 22 要表達 `query_sent`、`status=partial`、`step_type=unknown`、`unmapped_component_id`、warning，必須明確擴充 model 或新增 trace result wrapper，不能用 `extra` 欄位繞過 Pydantic `extra="forbid"`。
- `SecretMaskingService` 是 shared masking path，支援 string / JSON-like 遞迴遮蔽；`SystemMapValidationService` 會拒絕 `confidence` 與未遮蔽 secret-like value。
- Task 16 / 18 local web API 與 viewer projection 已存在：`POST /api/map/build`、`GET /api/map`、`GET /map`、`GET /api/map/report`。目前沒有 `/api/trace` 或 `trace_routes.py`。
- Task 19 manual mapping store 已完成，confirmed mapping 只在後續 scan / normalize 時生效。
- Task 20 mapping proposal flow 已完成：proposal 只吃 masked / bounded `MappingEvidencePacket`，provider output 需 validation，未 accept 不改 canonical map。
- Task 21 progressive detail scan 已完成：`DetailScanService` / `ComponentDetailScanService` / `CodePathScanService` 只做 target-scoped static extraction，不執行 target project，不呼叫 runtime endpoint，並把新 evidence 追加到 `evidence[]` 與 target `evidence_ids`。
- `src/systograph/cli/main.py` 目前只 register `map` / `viewer`；尚無 `trace_command.py`。

因此 Task 22 不是補 L2/L3 或 proposal 基礎，而是在上述基礎上新增唯一會送 runtime query 的 opt-in path。

## 外部研究查證結論（2026-06-09）
使用官方文件 / GitHub repo 查證後，研究方向大致正確，但有一點需要修正語氣：

| 來源 | 查證結論 | 對 Task 22 的落地 |
|---|---|---|
| GitDiagram | GitDiagram 會抓 GitHub default branch、recursive file tree、README，過濾 noise，LLM 產生 graph 後再用 file tree 驗證 path / connection，最後 compile Mermaid。這支持 staged validation，但不能把 LLM graph 當 Systograph canonical truth。 | Trace 只能補 runtime observation；static map 仍由 deterministic scanner + validation 決定。 |
| Understand-Anything | 官方 repo 說明它以 multi-agent pipeline 建 knowledge graph；本 repo 既有 review 也確認它會保留 deterministic scan inventory / import map，再做 LLM semantic layer 與 merge/validation。 | Trace 觀察到未知元件時，只能保留 `unknown / needs_mapping_confirmation`，不得自行更新 baseline flow 或 mapping。 |
| OpenTelemetry GenAI | 官方 GenAI semantic conventions 明確指出 model instructions、user messages、model outputs 通常敏感且很大，instrumentation 預設不應 capture，應提供 opt-in；也建議可 truncate/filter。 | Query trace 預設不保存 raw query/output/retrieved chunks；必須先 masking / truncation，再進 event、log、report 或 API response。 |
| OpenInference / Phoenix | OpenInference span kind 包含 `LLM`、`EMBEDDING`、`CHAIN`、`RETRIEVER`、`TOOL` 等；Phoenix/OpenInference SDK 提供 tracing helpers 與 attributes。 | `QueryTraceEvent` vocabulary 可對齊 retriever / embedding / llm / tool / chain，但 Systograph 不需要在 MVP 引入 Phoenix 或 OTEL backend。 |
| Langfuse | Langfuse SDK 支援 mask function，會在 trace data（input/output/metadata）送出前套用；self-hosted docs 也強調 client-side masking 可防止敏感資料離開 application boundary。 | `EndpointCallProvider` / `QueryTraceService` 必須在資料寫入任何 trace event 前呼叫 shared masking middleware。 |
| DeepEval | DeepEval 官方定位是 open-source、local-first、Pytest-style LLM evaluation framework，也支援 error config / async config，避免 custom judge JSON error 或 concurrency 造成整批 eval 中斷。GitHub README 也展示把 LLM app 當 black-box end-to-end 測。 | 可借鏡「黑箱測試、錯誤不中斷、bounded concurrency/timeout」；但官方文件沒有直接證明 DeepEval 會輸出 Systograph 需要的 partial replay event，所以 partial replay 是本任務自己的 API contract，不應寫成 DeepEval 已提供的行為。 |

參考資料：

- Langfuse masking: https://langfuse.com/docs/observability/sdk/advanced-features , https://langfuse.com/self-hosting/security/data-masking
- OpenTelemetry GenAI semantic conventions: https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/
- OpenInference semantic conventions: https://arize-ai.github.io/openinference/spec/semantic_conventions.html
- Phoenix OpenInference core docs: https://arize.com/docs/phoenix/sdk-api-reference/typescript/arizeai-openinference-core
- DeepEval docs / repo: https://deepeval.com/docs/introduction , https://deepeval.com/docs/evaluation-flags-and-configs , https://github.com/confident-ai/deepeval
- GitDiagram: https://github.com/ahmedkhaleel2004/gitdiagram
- Understand-Anything: https://github.com/Lum1104/Understand-Anything

## 產品與架構校正
本任務提供 runtime observation，但不能變成 Task 20 mapping proposal 的預設資料來源。`systograph map` / `POST /api/map/build` / `GET /api/map` / `GET /map` 必須維持 static、read-only、無 runtime side effect。

如果使用者明確 opt-in query trace，trace result 可以在後續 UI 中作為補充 evidence 顯示，例如「這條路徑在一次測試 query 中被觀察到」。但它仍然不能自動把 unmapped component 升級成 detected slot、confirmed extension 或 baseline flow edge。

明確禁止：

- 不在 default map build 中呼叫 endpoint。
- 不在 `GET /api/map`、`GET /map` 或 viewer load route 中呼叫 endpoint。
- 不使用 `sys.settrace`、debug hook、monkey patch 或 in-process instrumentation 追蹤使用者 app。
- 不把 runtime observation 當成 canonical architecture fact。
- 不把 raw query/output/retrieved chunks 存進 event、log、report、proposal 或 API response。
- 不讓 trace route 接受 arbitrary file path 或 raw source；trace 只能讀已 validate 的 map / project session。

## 承接 Task 16/20/21 延後功能
- 承接 Task 16 「不做 query trace / runtime endpoint 呼叫」的延後範圍。
- Task 16 的 map build 與 `GET /api/map` 永遠不得預設呼叫 runtime endpoint。
- Task 20 的 proposal flow 必須能在沒有 query trace 的情況下運作；trace 只能是 opt-in supplemental evidence。
- Task 21 的 detail scan 是 static evidence extraction；若使用者需要 runtime 證據，才進 Task 22。
- 若 Task 16 已建立 basic `GET /api/scan/events`，本任務可延伸 replay/progress event，但不得改壞既有 event target priority。

## 前置需求
- Task 14 已有 endpoint detection。
- Task 15 已有 `QueryTraceEvent` model/validation，但本任務需評估是否擴充欄位或新增 `TraceRunResult`。
- Task 18 已有 graph projection。
- Task 19 已有 confirmed manual mapping store。
- Task 20 已有 pending-only mapping proposal flow。
- Task 21 已有 bounded detail scan / code path scan 基礎。

## 實作範圍
- 建立 `EndpointCallProvider`，使用 bounded timeout，且只在 trace service 明確呼叫時送出 request。
- 建立 `QueryTraceService`，作為 endpoint selection、request event、response/error event、masking、trace mapping 的唯一 orchestration boundary。
- 使用 FastAPI 建立 local web trace route / handler，建議路徑 `POST /api/trace`。
- 更新 `docs/API-GUIDE.md` 與 `docs/work/Timmy/design/epic1-local-api-guide.md`，加入 query trace endpoint、opt-in 規則、side-effect 警告、masking 規則與 partial replay response。
- CLI 採已決策選項 A：獨立命令 `systograph trace <map_json> --endpoint-id ... --query ...`，但不得繞過 `QueryTraceService`。
- 找不到 endpoint 回傳 `endpoint_not_found` 且 `query_sent=false`，不可產生任何 HTTP request。
- timeout/error 產生 trace event，不丟棄 partial replay，不讓 viewer 收到空白 500。
- input/output/retrieved_chunks 必須 masking / truncate；若無法安全表示，至少保留 type / length / masked marker。
- confirmed extension / unmapped trace step mapping。
- 明確承接 Task 14 / Task 19 的 unmapped flow 邊界：未確認的 unmapped component 不進 baseline `Flow.edges`，但 replay 若觀察到相關 evidence，應以 `Unknown / Needs confirmation` step 保留 partial replay。

## 不包含範圍
- 不做 proxy wrapper。
- 不做 full runtime observability。
- 不整合 Phoenix / Langfuse / OpenTelemetry backend；只概念對齊 vocabulary 與 masking 原則。
- 不預設在 `systograph map` 呼叫 endpoint。
- 不使用 `sys.settrace`、debug hook、monkey patch 或 in-process instrumentation 追蹤目標 app。
- 不保存 raw sensitive query。
- 不把 trace 觀察到的 unmapped component 自動升級成 detected slot 或 confirmed extension。
- 不在 replay 中替使用者做 manual mapping；確認與持久化仍交給 Task 19/20。
- 不把 query trace 當成 Task 20 proposal 的必要條件。
- 不讓前端提交 raw trace event 直接寫回 canonical map。

## 建議實作步驟
1. 先補 trace model：確認現有 `QueryTraceEvent` 是否足夠；若不足，新增受控欄位或建立 `TraceRunResult` / `TraceRunStatus` model。需要表達：`trace_id`、`status`、`query_sent`、`endpoint_id`、`events[]`、`warnings[]`、`error_reason`。
2. 建立 `src/systograph/core/providers/endpoint_call_provider.py`。
3. `EndpointCallProvider` 使用 `httpx` 或等價 HTTP client，設定短 bounded timeout；捕捉 timeout / connection / non-JSON response，轉成 typed result，不讓例外直接炸出 route。
4. 建立 shared masking middleware，例如 `mask_trace_payload(payload)` 或在 `QueryTraceService` 中集中呼叫 `SecretMaskingService.mask_json_like()`；不得在 provider、route、CLI 各寫一套 masking。
5. 建立 `src/systograph/core/services/query_trace_service.py`。
6. 實作 endpoint selection by endpoint_id；只允許從 validated `RagSystemMap.endpoints[]` 選，不接受 arbitrary URL 作為第一版預設。
7. 實作 `endpoint_not_found`：回傳 `query_sent=false`、`status="endpoint_not_found"`、events 可為空或只含 local validation event，但不可送 HTTP request。
8. 實作 request lifecycle events：
   - `request_prepared` / `request_sent`：只保留 masked query metadata、endpoint id、method、trace id。
   - `response_received`：保留 masked / truncated output metadata。
   - `error`：保留 sanitized error type、timeout seconds、`status="partial"`。
9. 實作 basic response/error to `QueryTraceEvent[]` mapping。
10. 實作 confirmed extension / unmapped trace step mapping：
    - standard slot match -> `slot`。
    - confirmed extension match -> `component_id` / extension step metadata。
    - unmapped evidence match -> `step_type="unknown"` / `needs_mapping_confirmation` warning，不寫入 baseline `Flow.edges`。
11. 實作 trace result append 或 trace result output。若要寫入 `ai_system_map.query_trace_events[]`，必須重新跑 `SystemMapValidationService.validate()`；若只回傳 transient `TraceRunResult`，也必須維持 schema typed。
12. 建立 FastAPI trace route，要求明確 `project_id` 或 `map_json_path`、`endpoint_id`、`query`、optional timeout。Project session flow 優先；若允許 `map_json_path`，只能透過 viewer/load 後的受控 map，不開 arbitrary path read。
13. 更新 `docs/API-GUIDE.md`，補上 trace API request/response、`endpoint_not_found`、timeout/error response、masking rule、side-effect warning。
14. 建立 `src/systograph/cli/trace_command.py` thin adapter，並在 `src/systograph/cli/main.py` register；CLI 只做參數解析與輸出，不重寫 trace 邏輯。
15. 測試 endpoint_not_found、timeout partial replay、masked input/output/retrieved_chunks、web API 和 CLI 都不預設送 query；trace 遇到 unmapped evidence 時保留 unknown step，不讓 replay 失敗。
16. 測試 `systograph map` / `POST /api/map/build` / `GET /api/map` 不會建構 `EndpointCallProvider` 或送出任何 runtime request。
17. 測試 trace result 若被提供給 proposal/detail UI，只能以 masked supplemental evidence 顯示，不會自動建立 manual mapping 或 canonical edge。

## 預期輸出
- `src/systograph/core/providers/endpoint_call_provider.py`
- `src/systograph/core/services/query_trace_service.py`
- 可能更新 `src/systograph/core/models/system_map.py`
- 可能新增 `src/systograph/core/models/trace.py`
- `src/systograph/web/routes/trace_routes.py`
- 更新 `src/systograph/web/app.py`
- 更新 `src/systograph/web/schemas.py`
- `src/systograph/cli/trace_command.py`
- 更新 `src/systograph/cli/main.py`
- 更新 `/Users/linjunting/Systograph/docs/API-GUIDE.md`
- 更新 `docs/work/Timmy/design/epic1-local-api-guide.md`
- `tests/unit/core/test_endpoint_call_provider.py`
- `tests/unit/core/test_query_trace_service.py`
- `tests/web/test_trace_routes.py`
- `tests/cli/test_trace_command.py`

## 驗收標準
- trace 預設不會在 map command、map build route、map read route、viewer load route 執行。
- `systograph map` 不接受會呼叫 runtime endpoint 的 trace option；trace 必須走 `systograph trace`。
- local web trace API 必須由使用者明確送出 endpoint/query 才會呼叫 runtime endpoint。
- query trace 不使用 `sys.settrace`、debug hook、monkey patch 或 in-process instrumentation。
- missing endpoint 不送 query，且回傳 `endpoint_not_found` / `query_sent=false`。
- timeout/error 保留 partial replay event，HTTP route 不因 runtime timeout 回空白 500。
- trace step 可映射 standard slot、confirmed extension 或 unknown/unmapped。
- full query/output/retrieved chunks / secret 不出現在 event、log、report、API response 或 tests snapshots。
- `QueryTraceEvent` 或 trace wrapper contract 能明確表達 partial/error/unknown state，且通過 Pydantic validation。
- API guide 已同步記錄 trace API 必須 opt-in、不得由 map build 預設觸發、以及敏感資料 masking 規則。
- 未確認的 unmapped component 在 replay 中只能顯示為 unknown / needs_confirmation，不得變成 confirmed extension step。
- confirmed manual mapping 後，重新 normalize / regenerate 的 map 才能讓 replay 顯示正式 extension step。
- replay unknown step 不修改 canonical baseline `flows`，避免把 runtime observation 誤寫成靜態架構事實。
- Task 20 在沒有 query trace 的情況下仍可產生 pending proposal；trace 只是一種 opt-in supplemental evidence。

## 可能風險與注意事項
- 呼叫 endpoint 是 side effect，必須 opt-in。
- 測試應使用 FastAPI `TestClient`、`httpx.MockTransport`、`pytest_httpx` 或 mock provider，不依賴真實 RAG 服務；若使用 `responses`，要注意它主要攔截 `requests`，不一定適合 `httpx`。
- trace API contract 改動會直接影響 replay UI 和 desktop app，因此改 endpoint / response / error code 時必須同步更新 API guide。
- OpenTelemetry GenAI docs 提醒 inputs/outputs 敏感且不應預設擷取；OpenInference span kinds 可作 Retriever/LLM/Embedding/Tool vocabulary 參考，但不應成為 MVP public schema 的硬依賴。
- Langfuse 的 masking 設計支持「送出前遮蔽」原則；Systograph 應重用 `SecretMaskingService`，不要引入第二套 masking 規則。
- DeepEval 可作黑箱 eval / pytest-style failure containment 參考，但 partial replay event 是 Systograph 自己的 UX/API contract。
- 如果 `QueryTraceEvent` 現有 schema 無法表達 `unmapped_component_id`、`step_type=unknown`、`query_sent=false` 或 warning，必須在本任務同步擴充模型與 validation；不可用任意 extra fields 繞過 contract。
- runtime observation 的產品文案必須說明「observed in this opt-in trace」，不能寫成「system architecture confirmed」。

## 新手提示
Query trace 是「真的問系統一次」。因為會碰 runtime，所以不能偷偷做，必須使用者明確要求。它像測試一次路線有沒有跑通，不是重新定義系統架構。

## 視覺化說明
```text
┌──────────────────────┐
│ validated map/project │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ QueryTraceService     │
│ opt-in only           │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ endpoint_id exists?   │
└──────┬─────────┬─────┘
       │ no      │ yes
       ↓         ↓
┌──────────────────────┐ ┌──────────────────────┐
│ endpoint_not_found    │ │ EndpointCallProvider  │
│ query_sent = false    │ │ bounded timeout       │
└──────────────────────┘ └──────────┬───────────┘
                                     ↓
                          ┌──────────────────────┐
                          │ mask / truncate       │
                          │ query/output/chunks   │
                          └──────────┬───────────┘
                                     ↓
                          ┌──────────────────────┐
                          │ QueryTraceEvent[]     │
                          │ or TraceRunResult     │
                          └──────────┬───────────┘
                                     ↓
                          ┌──────────────────────┐
                          │ timeout/error keeps   │
                          │ partial replay        │
                          └──────────────────────┘
```
