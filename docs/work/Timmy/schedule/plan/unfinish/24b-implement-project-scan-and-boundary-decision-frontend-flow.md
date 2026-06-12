# Task 24b: Implement Project Scan and Boundary Decision Frontend Flow

## 目標

把目前前端 API mode 從「只能讀 `/api/map` 顯示既有 viewer payload」推進成 EPIC1 可用的正式 project-scoped scan flow：

```text
選擇 / 輸入本機 project path
  -> POST /api/projects/import
  -> POST /api/scans
     -> completed：更新 graph viewer
     -> requires_boundary_decision：顯示本次掃描範圍確認
        -> 使用者選 scan_this_run / skip_this_run
        -> 再 POST /api/scans 帶 boundary_decisions[]
  -> GET /api/map 顯示 graph_view_model
```

本任務是 EPIC1 frontend 收尾必做項。它不是 Project Mapping Profile Page；也不是 project archive upload。

## 為什麼需要新增這個任務

Task 24 backend 已完成 scan-boundary same-run gate。`POST /api/scans` 可能回：

```text
status = "requires_boundary_decision"
build_result = null
boundary_proposals = [...]
available_boundary_actions = ["scan_this_run", "skip_this_run"]
```

目前前端實際狀態仍是：

- `frontend/src/services/viewerApi.ts` 只支援 `GET /api/map`、`GET /map`、`GET /api/scan/events`。
- `frontend/src/App.tsx` 有 sample/API viewer mode，但沒有 project import、scan create、boundary decision state machine。
- `frontend/src/store/viewerStore.ts` 沒有 `project_id`、`scan_id`、boundary proposals、boundary decisions state。
- `frontend/API_CONTRACT.md` 尚未記錄 project import、`POST /api/scans`、boundary decision response。

若沒有本任務，前端只能展示已存在的 map，不能從使用者選定的 project 走完整 EPIC1 掃描閉環。

## 前置需求

- Task 16：local API / `POST /api/projects/import` / `POST /api/scans` 已存在。
- Task 18：`GET /api/map` viewer payload projection 已存在。
- Task 23：local API hardening 已完成。
- Task 24：scan-boundary review backend/API 已完成。

## 實作範圍

- 擴充 `frontend/src/types.ts`：
  - `ProjectImportRequest` / `ProjectImportResponse`
  - `ScanCreateRequest` / `ScanCreateResponse`
  - `ScanBoundaryProposal`
  - `ScanBoundaryDecisionRequest`
  - `ScanBoundaryDecisionAction = "scan_this_run" | "skip_this_run"`
- 擴充 `frontend/src/services/viewerApi.ts`：
  - `importProject(baseUrl, request)`
  - `createScan(baseUrl, request)`
  - 保留 `loadApiViewerPayload(baseUrl)`
- 在 frontend store 補 project/scan workflow state：
  - current project id
  - current project path/display name
  - latest scan id
  - pending boundary proposals
  - selected boundary decisions
  - scan workflow status
- 建立 project path input / import control。
- 建立 scan action，正式流程使用 `POST /api/scans`，不要用 `POST /api/map/build`。
- 建立 boundary decision modal / drawer：
  - 顯示 proposal target path、fingerprint、masked evidence packet summary、reason。
  - 每個 proposal 必須選 `scan_this_run` 或 `skip_this_run`。
  - 完成後用同一個 endpoint 再送 `boundary_decisions[]`。
- `completed` 後 refetch `GET /api/map`，更新 graph viewer。
- `error` / 404 / 422 / 413 / masked 500 都要有可讀狀態。
- 更新 `frontend/API_CONTRACT.md`，同步記錄正式 project session scan flow。
- 補 frontend tests；若 test runner 尚未建立，與 Task 20a / 21a 共用 Vitest + React Testing Library setup。

## 不包含範圍

- 不做 project archive upload；那是 Task 25。
- 不做 persistent scan history；那是 Task 26 / Task 27。
- 不做 mapping profile page；那是 Task 24a。
- 不做 manual mapping UI；那是 Task 20a / 24a 相關後續。
- 不在前端讀本機 project files。
- 不支援舊 scan-boundary actions：`always_skip`、`metadata_only`、`masked_summary_only`、`scan_normally`。
- 不把 boundary decision 保存成下次 scan preference；後端 decision 只對本次 scan request 生效。

## 建議實作步驟

1. RED：補 frontend type/schema tests，覆蓋 `requires_boundary_decision` response。
2. 補 `viewerApi.importProject()` / `viewerApi.createScan()`。
3. 在 store 加入 project session 與 scan workflow state。
4. 建立 project path import UI，取得 `project_id`。
5. 建立正式 scan button，呼叫 `POST /api/scans`。
6. 處理 `completed`：保存 `scan_id`，refetch `GET /api/map`。
7. 處理 `requires_boundary_decision`：顯示 modal/drawer，不更新 graph。
8. 在 modal/drawer 中收集每個 proposal 的 `scan_this_run` / `skip_this_run`。
9. 送出 decisions 後再次 `POST /api/scans`。
10. 處理 typed error response：404 project missing、422 invalid decision、413 request too large、500 masked internal error。
11. 更新 `frontend/API_CONTRACT.md`。
12. 跑 `cd frontend && pnpm build` 與 frontend tests。

## 驗收標準

- API mode 可以從使用者輸入的 local path 取得 `project_id`。
- API mode 可以使用 `POST /api/scans` 完成 project-scoped scan。
- 當後端回 `requires_boundary_decision` 時，前端顯示安全確認 UI，不更新 graph，不假裝 scan 完成。
- 每個 boundary proposal 都能選 `scan_this_run` 或 `skip_this_run`。
- 決策送出後，前端會再次呼叫 `POST /api/scans` 並帶 `boundary_decisions[]`。
- scan completed 後 refetch `GET /api/map`，Graph viewer 顯示最新 `graph_view_model`。
- UI 文案清楚說明 decision 只影響本次 scan，不是永久設定。
- 前端不使用 `/api/map/build` 來支援需要 `project_id` 的互動功能。
- `frontend/API_CONTRACT.md` 已同步正式 project scan / boundary decision flow。

## 新手提示

現在前端像是只能打開一張已經做好的地圖。本任務要讓使用者真的從「選專案」開始掃描；如果掃描前遇到可能敏感的檔案，就先問使用者這次要不要掃。

## 視覺化說明

```text
API mode
  -> import project path
  -> project_id
  -> create scan
       ├─ completed
       │    -> GET /api/map
       │    -> render graph
       └─ requires_boundary_decision
            -> boundary modal
            -> scan_this_run / skip_this_run
            -> create scan again with decisions
            -> completed
            -> GET /api/map
```
