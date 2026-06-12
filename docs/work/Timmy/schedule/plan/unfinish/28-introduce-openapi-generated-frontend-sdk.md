# Task 28: Introduce OpenAPI Generated Frontend SDK

## 最新狀態校正（2026-06-12）

- 程式碼現況：後端 FastAPI routes / Pydantic schemas 已能支撐 runtime OpenAPI，但 repo 尚未看到 OpenAPI export script、versioned OpenAPI artifact、frontend codegen config、generated TypeScript client、schema drift check。前端目前仍由 `frontend/src/services/viewerApi.ts` 手寫 `/api/map` 與 SSE 相關呼叫。
- 判斷：本任務尚未完成。它不是 EPIC1 核心功能閉環的第一優先，但在 `24b` project scan/boundary frontend flow、`20a` proposal frontend flow、`21a` detail scan frontend flow 完成後，應作為 EPIC1 收尾品質門檻或 EPIC1 freeze 前最後一個 contract hardening 任務。
- 近期處置：保留在 `unfinish`。Task 25 upload、Task 26 history、Task 27 DB storage 若明確延後到 EPIC2，本任務可以先以目前 EPIC1 route set 凍結；否則應等這些 API shape 決策後再做，避免 generated SDK churn。
- EPIC1 邊界：若時間有限，EPIC1 可以先靠手寫 client 收尾，但必須接受前後端 contract drift 風險；正式宣布 API freeze 前建議補上 OpenAPI export/generate/drift check。

## 目標

在 Epic 1 local API route 基本凍結後，導入 Schema-First API contract pipeline：由 FastAPI 匯出 OpenAPI schema，前端用 OpenAPI 產生 TypeScript 型別與 API client，讓 GUI 不再手寫 endpoint path / request / response 型別。

## 為什麼要獨立做這個

FastAPI 目前已能在 runtime 產生 `/openapi.json` 與 Swagger UI，但 repo 還沒有把 OpenAPI schema 當成 versioned contract，也沒有把它接到 frontend SDK generation / CI。

這件事應該放在 Epic 1 後段，而不是等到 Epic 2：

- Epic 1 已經定義 local API contract：map、scan、detail scan、mapping proposal、manual mapping、query trace、scan boundary review、template import、upload、session history。
- 若等 Epic 2 GUI 深入開發後才導入 generated SDK，前端會先累積大量手寫 fetch / 型別，再回頭重構。
- 但也不適合太早做；Task 24/25/26 仍會新增或調整 API route，太早導入會讓 SDK churn 太高。

本任務是 Epic 1 API contract freeze / generated SDK 收尾任務。

## 承接 Task 16 / 18 / 20 / 21 / 22 / 24 / 25 / 26 延後功能

- Task 16 建立 local API shell，但前端仍可手寫 route 呼叫。
- Task 18 建立 viewer projection，但未建立 generated frontend client。
- Task 20/21/22 新增 proposal/detail/trace APIs，尚未進入 OpenAPI codegen pipeline。
- Task 24/25/26 會繼續新增 final Epic 1 API route；本任務應在這些 route shape 穩定後執行。
- 本任務將 API guide / scripts / Pydantic models / OpenAPI schema / generated frontend client 對齊成同一份 contract。

## 前置需求

- Task 23 baseline hardening 已完成。
- Task 24 final scan boundary review / template import APIs 已完成或 route shape 已凍結。
- Task 25 project upload ingestion API 若屬 Epic 1 scope，需先完成或明確排除。
- Task 26 persistent session store / scan history API 若屬 Epic 1 scope，需先完成或明確排除。
- Frontend 已有穩定 package manager 與 TypeScript build/test command。

## 實作範圍

- 固定 FastAPI route `operation_id` 命名策略，避免每次 refactor function name 都造成 generated SDK 破壞。
- 建立 OpenAPI schema export script，例如 `scripts/export_openapi_schema.py` 或 equivalent CLI。
- 將匯出的 schema 存成 versioned artifact，例如 `frontend/src/api/openapi.json` 或 `schemas/openapi.local-api.json`。
- 選擇 TypeScript generation 工具：
  - 優先評估 `openapi-typescript` 產生型別 + 薄 client wrapper。
  - 若需要完整 generated client，再評估 `openapi-generator-cli`。
- 建立 frontend generated API client / types，供 GUI 使用。
- 將至少一條核心 frontend API flow 改用 generated client，例如 map load 或 project import + scan。
- 建立 CI / test 檢查：OpenAPI schema 與 generated types/client 不可 drift。
- 更新 `docs/API-GUIDE.md` 與 `docs/work/Timmy/design/epic1-local-api-guide.md`，說明 OpenAPI schema 是 machine-readable contract，Markdown guide 是 human-readable contract。

## 不包含範圍

- 不改 API behavior，只做 contract generation 與 frontend integration。
- 不把 generated SDK 當成後端 Pydantic model 的替代品。
- 不移除 `docs/API-GUIDE.md`；人讀文件仍保留設計意圖、side-effect warning、local-only security rules。
- 不產生多語言 SDK；Epic 1 只需要 TypeScript frontend client。
- 不把 OpenAPI schema 當成 canonical scanner truth；scanner truth 仍是 validated `ai_system_map.json`。

## 建議實作步驟

1. 盤點目前 FastAPI routes，確認每個 route 的 `response_model`、request schema、error response 是否足以生成 OpenAPI。
2. 為 routes 補 stable `operation_id` 或集中設定 operation id generator。
3. 建立 OpenAPI export script，測試可在不啟動 server 的情況下從 `create_app()` 匯出 schema。
4. 寫 contract test：匯出的 schema 包含主要 Epic 1 endpoints，且沒有明顯 unstable operation id。
5. 選擇 frontend codegen 工具，新增 package script，例如 `npm run api:generate`。
6. 產生 TypeScript API types/client，將 generated files 放到明確目錄並標註不得手改。
7. 改一條 frontend API flow 使用 generated client，驗證 dev build / typecheck。
8. 新增 CI check：重新 export/generate 後 git diff 必須乾淨。
9. 更新 API guide、design doc、dev prompt，記錄 OpenAPI pipeline 使用方式。

## 預期輸出

- `scripts/export_openapi_schema.py` 或等價 script。
- `schemas/openapi.local-api.json` 或等價 OpenAPI artifact。
- frontend OpenAPI codegen config。
- frontend generated API types/client。
- 至少一個 frontend API caller 改用 generated client。
- `tests/contracts/test_openapi_schema.py`。
- 更新 `docs/API-GUIDE.md`。
- 更新 `docs/work/Timmy/design/epic1-local-api-guide.md`。

## 驗收標準

- OpenAPI schema 可由 repo command 穩定產生。
- schema 包含 Epic 1 local API endpoints，且主要 route 有穩定 operation id。
- TypeScript types/client 可由 frontend command 產生。
- 前端至少一條 API flow 使用 generated client，不再手寫 path / response 型別。
- CI 或本地 verification 可偵測 schema/client drift。
- Markdown API guide 與 generated schema 的定位清楚：一個給人讀，一個給機器生成 SDK。
- 不破壞現有 `scripts/trace_*.sh` smoke examples；shell scripts 仍作為可執行 API examples。

## 可能風險與注意事項

- 太早導入會造成 generated SDK churn；應等 Task 24/25/26 route shape 穩定後做。
- FastAPI 預設 operation id 可能跟 Python function name 綁太緊，必須避免 refactor 造成 frontend client breaking change。
- Pydantic `Any` 或寬鬆 response 欄位會讓 generated TypeScript 型別太弱；若發現這類問題，應優先收斂 schema，而不是在 frontend 補 `any`。
- Error response 在 OpenAPI 中容易缺文件；至少要記錄主要 404/400/422 contract。
- Generated code 不應手改；客製行為放在 thin wrapper。

## 新手提示

現在 FastAPI 已經會自動吐 `/openapi.json`，但那只是「有規格」。本任務是把規格變成正式開發流程：匯出、產生前端型別/client、檢查同步，讓前端少寫錯 endpoint 或 response 型別。

## 視覺化說明

```text
┌──────────────────────┐
│ FastAPI routes        │
│ + Pydantic schemas    │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ OpenAPI export        │
│ openapi.local-api.json│
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ TypeScript codegen    │
│ types + API client    │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ Frontend API calls    │
│ generated client      │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ CI drift check        │
│ schema/client synced  │
└──────────────────────┘
```
