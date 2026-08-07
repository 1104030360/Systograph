# 2026-06-09 Completed Phase 22 Query Trace MVP Report

## 實作邏輯

- 新增明確 opt-in 的 Query Trace runtime 路徑：`POST /api/trace` 與 `systograph trace`。靜態 `map` / `scan` / `viewer` 路徑不會自動呼叫 endpoint。
- `EndpointCallProvider` 只負責 bounded HTTP call，並把 timeout / transport / HTTP error 包成 typed result，不讓例外直接炸穿 replay。
- `QueryTraceService` 只回傳 transient `TraceRunResult`，不寫回 canonical `ai_system_map.json`、不修改 `flows`、`extensions`、manual mappings 或 proposal state。
- Trace event payload 在進入 response 前會走 shared `SecretMaskingService.mask_json_like()`，並進一步摘要化 query、output、retrieved chunks，避免 raw sensitive query / raw response 出現在 API、CLI 或 report。
- 找不到 endpoint 時回 `status="endpoint_not_found"`、`query_sent=false`，不送 HTTP request。
- Timeout / transport / HTTP error 回 `status="partial"`，保留 `request_sent` 與 `error` events，前端 replay 可以停在失敗點。
- Response metadata 若帶有已知 `unmapped_component_id`，只在 event 標示 `step_type="unknown"` 與 `needs_mapping_confirmation`，不自動升級成 confirmed extension 或 baseline edge。

## 步驟

1. 先補 RED tests：core provider/service、web route、CLI command、static map boundary。
2. 實作 `src/systograph/core/providers/endpoint_call_provider.py`。
3. 實作 `src/systograph/core/models/trace.py` 與 `src/systograph/core/services/query_trace_service.py`。
4. 擴充 `QueryTraceEvent` 欄位，並重新產生 `schemas/ai-system-map.v1.schema.json`。
5. 新增 `src/systograph/web/routes/trace_routes.py`，更新 `web/app.py`、`web/dependencies.py`、`web/schemas.py`。
6. 新增 `src/systograph/cli/trace_command.py` 並註冊到 `systograph trace`。
7. 更新 `docs/API-GUIDE.md`、`docs/work/Timmy/design/epic1-local-api-guide.md`、新增 `scripts/trace_query_trace.sh`，並把它加入 `scripts/trace_all.sh`。
8. Phase 完成後，將 `22-implement-query-trace-mvp.md` 從 `plan/unfinish` 移到 `plan/finish`。

## 測試方式

- `tests/unit/core/test_endpoint_call_provider.py`
- `tests/unit/core/test_query_trace_service.py`
- `tests/unit/core/test_query_trace_boundaries.py`
- `tests/web/test_trace_routes.py`
- `tests/cli/test_trace_command.py`
- `tests/contracts/test_ai_system_map_schema.py`
- `bash -n scripts/trace_query_trace.sh scripts/trace_all.sh`
- `.venv/bin/pytest`
- `.venv/bin/mypy src tests`
- `.venv/bin/ruff check .`

## 遇到的問題與解法

- `QueryTraceEvent` 原本 `extra="forbid"` 且欄位不足，不能在 event 偷塞 `event_type`、`status`、`query_sent` 等 replay metadata；解法是正式擴充 Pydantic model 並更新 checked-in JSON schema。
- `SecretMaskingService.mask_json_like()` 會遮蔽 secret-like pattern，但不應讓一般 query/output 明文進入 trace；解法是在 shared masking 後再做 payload summary，只保留型別、長度、list 長度與 `[MASKED]`。
- Trace smoke script 若預設打真實 endpoint 會違反 opt-in；解法是 `scripts/trace_query_trace.sh` 預設使用 `endpoint:missing`，只驗證 no-request contract，使用者明確傳入 `--endpoint-id` 才會呼叫 runtime endpoint。

## 測試結果

- Focused Query Trace + schema tests：21 passed。
- 全套測試：392 passed。
- mypy：Success，127 source files 無 issue。
- ruff：All checks passed。
- shell script syntax check：通過。
