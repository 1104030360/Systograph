# Task 16: Implement MapBuildService and Local Web API

## 目標
串起 `MapBuildService` 與 local web API，讓 GUI/local web UI 可以從畫面觸發 scan 並產生 `ai_system_map.json`。這是 Epic 1 backend 第一個完整 end-to-end milestone，也是 frontend 能開始接畫面的關鍵 API。

## 為什麼要先做這個
設計文件的核心交付是 project folder -> canonical JSON。因為 Epic 1 優先 GUI/local web UI，本任務先做 local API adapter，讓前端不用等 CLI 完整後才開始對接；CLI 之後只需包同一個 `MapBuildService`。

## 前置需求
- Task 6 已完成 precondition/output policy。
- Task 12 已完成 ProjectScanService。
- Task 15 已完成 normalize/validate。
- Task 3 已完成 template service。
- Task 1 已建立 `web/` adapter skeleton。
- 已完成 local web backend framework 選擇：FastAPI。

## 實作範圍
- 建立 `MapBuildService`。
- 使用 FastAPI 實作 local web API map build route / handler。
- 支援 `project_path`、`output`、`redact_root_path`、`no_snippets` 等基本 request 欄位。
- 建立 Epic 1 local API guide，作為前端、desktop app、CLI adapter 共用的 API contract 文件。
- 寫出 `ai_system_map.json`。
- fatal error 寫出 `map-error.md`。
- 回傳 structured `MapBuildResult`。
- 在 local web API 完成後，補上 `kai-mind map` thin adapter，CLI 只能呼叫同一個 `MapBuildService`。

## 不包含範圍
- 不產生 Markdown，留給 Task 17。
- 不做 viewer command。
- 不做 CLI 專屬 scanner logic；CLI 是次要入口，只能 thin-wrap core service。
- 不做 query trace。
- 不做 detail scan。
- 不做 frontend GUI 畫面。

## 建議實作步驟
1. 建立 `src/kai_mind/core/services/map_build_service.py`。
2. 將 precondition、template、scan、detection、endpoint/risk/flow、normalize、validate 串起來。
3. 補強 `OutputArtifactProvider.write_json()`。
4. 建立 FastAPI app scaffold：`src/kai_mind/web/app.py`。
5. 建立 `src/kai_mind/web/routes/map_routes.py`，並用 FastAPI router 掛載 map build endpoint。
6. 建立 request/response schema，讓 route handler 只做輸入轉換與結果回傳。
7. 建立 `docs/work/Timmy/design/epic1-local-api-guide.md`，先記錄 API guide 結構、local-only 原則、共用 error format、map build endpoint、版本相容規則。
8. 在 API guide 註明：任何 task 若新增、移除或改動 endpoint / request / response / error code，都必須同步更新本文件。
9. 用 FastAPI TestClient 或 HTTPX 寫 web API integration test：basic fixture 產生 JSON。
10. 寫 missing project test：API 回傳 error result，且只產生 error report。
11. 建立 `src/kai_mind/cli/map_command.py`，讓 CLI 呼叫同一個 `MapBuildService` method。
12. 寫 CLI thin adapter test：確認 CLI 產生的 artifact contract 與 local API 相同，且 CLI 不直接呼叫 providers。

## 預期輸出
- `src/kai_mind/core/services/map_build_service.py`
- `src/kai_mind/web/app.py`
- `src/kai_mind/web/routes/map_routes.py`
- `src/kai_mind/web/schemas.py`
- `src/kai_mind/cli/map_command.py`
- `src/kai_mind/cli/main.py`
- `docs/work/Timmy/design/epic1-local-api-guide.md`
- `tests/web/test_map_routes.py`
- `tests/cli/test_map_command.py`
- `tests/integration/test_map_build_service.py`

## 驗收標準
- Local web API 呼叫 map build 後產生 valid JSON。
- missing project 產生 `map-error.md` 且不產生 normal map。
- outputs 已存在時產生 timestamped directory。
- Web adapter 不直接掃描檔案，只呼叫 core service。
- Route handler 不包含 provider/detection/normalization logic。
- `kai-mind map ./fixture --output outputs` 作為 thin adapter 產生同 contract 的 valid JSON。
- `epic1-local-api-guide.md` 已記錄 map build API、request/response schema、error format、local-only policy。
- PR / task 完成前若 API contract 有變更，必須同步更新 API guide。

## 可能風險與注意事項
- Web adapter 不應承擔 scanner logic，避免與 CLI adapter 重複。
- request/response schema 要貼近 core model，但不要讓 web framework 型別滲進 core services。
- API guide 是 frontend / desktop app / CLI adapter 的協作契約，不是自動產生文件的替代品；FastAPI OpenAPI 可以輔助，但 Markdown guide 必須保留設計意圖與使用規則。
- 參考依據：FastAPI 官方文件提供 OpenAPI、Pydantic model 與 automatic docs；這符合 GUI/local web UI 優先、typed API contract、frontend 快速對接的需求。

## 新手提示
MapBuildService 是總指揮。local web API 只是把 GUI 送來的資料轉給它，然後把結果路徑和狀態回傳給畫面。

## 視覺化說明
```text
┌──────────────┐
│ GUI / Web UI │
└──────┬───────┘
       ↓
┌──────────────┐
│ Local API    │
└──────┬───────┘
       ↓
┌──────────────────────┐
│ MapBuildService       │
└──────┬──────┬────────┘
       │      │
       ↓      ↓
┌──────────────┐ ┌──────────────────────┐
│ Precondition │ │ ProjectScanService    │
└──────┬───────┘ └──────────┬───────────┘
       │                    ↓
       │          ┌──────────────────────┐
       │          │ Detection/Risk/Flow   │
       │          └──────────┬───────────┘
       └────────────┬───────┘
                    ↓
┌──────────────────────┐
│ Normalize / Validate  │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ ai_system_map.json    │
└──────────────────────┘
```
