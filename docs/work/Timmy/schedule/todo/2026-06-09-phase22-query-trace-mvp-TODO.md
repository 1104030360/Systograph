# 2026-06-09 Phase 22 Query Trace MVP TODO

## 實作邏輯

- Query Trace 必須是明確 opt-in 的 runtime 路徑，只能由 `kai-mind trace` 或 `POST /api/trace` 觸發。
- `kai-mind map`、`POST /api/map/build`、`GET /api/map` 與 viewer 讀取路徑維持靜態、read-only，不注入或呼叫 endpoint client。
- Trace 只能使用已驗證 `RagSystemMap.endpoints[]` 中的 endpoint id，不接受任意 URL 或任意本機檔案路徑。
- Trace 結果以 transient `TraceRunResult` 回傳，觀察到的 unknown/unmapped evidence 只標示 `step_type="unknown"` 與 `needs_mapping_confirmation`，不修改 canonical `flows`、`extensions`、manual mappings 或 baseline edges。
- 所有 query、output、retrieved chunks 進入 trace event 前必須走 shared masking/summarization path，不保存 raw sensitive query 或 raw response。
- Timeout / transport error 要保留 partial replay：至少包含 request event 與 error event，不讓整個 API/CLI 只剩 500 或 crash。

## 步驟

1. [x] 先寫 core RED tests：endpoint_not_found 不送 request、成功呼叫會遮蔽 query/output、timeout 保留 partial replay、trace 不污染 canonical map。
2. [x] 實作 `EndpointCallProvider` 與 `QueryTraceService` 的最小可用邏輯。
3. [x] 擴充 `QueryTraceEvent` 與新增 trace wrapper model，更新 schema contract。
4. [x] 補 web RED/GREEN：`POST /api/trace` 只接受 project session + endpoint id + query，project/map missing 回傳明確錯誤。
5. [x] 補 CLI RED/GREEN：`kai-mind trace` 是 thin adapter，讀入已驗證 map JSON 並輸出 trace result JSON。
6. [x] 補 API 文件與 scripts endpoint trace 範例。
7. [x] 跑 focused tests，再跑 full test suite；若有非本次變更造成的 failure，記錄在 report。
