# Epic 1 Frontend Viewer Design

## 目標

Epic 1 前端 Viewer 的目標是把後端產出的 `viewer_load_result.graph_view_model`
渲染成可理解、可互動、可追溯的 RAG System Map。前端只負責呈現與互動，不
重新掃描 repo，也不自行推論 JSON 中不存在的 component。

## 使用者體驗原則

- 第一眼要能看懂 RAG 系統有哪些元件與資料流。
- Highlight 是聚焦，不是刪除 graph elements。
- Node / edge 的 detail 必須能追到 evidence 與 risk hints。
- Query replay 要讓不熟 RAG 的使用者看懂一個問題如何逐步變成答案。
- UI 預留 local model chat 區域，但 chat 不應干擾 graph viewer 的主要任務。

## 前端資料邊界

前端主要消費：

- `viewer_load_result.ai_system_map`
- `viewer_load_result.graph_view_model.nodes`
- `viewer_load_result.graph_view_model.edges`
- `viewer_load_result.graph_view_model.details`
- `viewer_load_result.graph_view_model.filters`
- `ai_system_map.query_trace_events`

前端不得：

- 重新讀 project folder。
- 自行判斷 slot 是否 detected。
- 補出 JSON 沒有的 canonical component。
- 顯示未遮罩的 secret。

## 技術選型

- React + Vite + TypeScript：快速建置 local web app。
- React Flow：處理 graph node / edge / zoom / pan / minimap。
- ELK：做 deterministic layered graph layout。
- Zustand：保存 viewer UI state。
- TanStack Query：載入 sample/API payload。
- Zod：在前端驗證 viewer payload shape。
- Lucide：一致的 icon button 與 macOS-like tool UI。

## UI 架構

```text
┌──────────────┐  ┌────────────────────────────┐  ┌──────────────┐
│ Sidebar      │  │ Workspace                  │  │ Chat Panel   │
│ filters      │  │ toolbar + progress + graph │  │ reserved     │
│ depth hints  │  │ replay timeline            │  │ local model  │
└──────────────┘  └────────────────────────────┘  └──────────────┘
                         │
                         ↓
                 node / edge click
                         │
                         ↓
                 Detail Modal
```

## Progressive Detail UX

Viewer 採三層漸進分析：

1. L1 System：整體 RAG 架構圖。
2. L2 Component：點 node / edge 後顯示元件細節與 evidence。
3. L3 Code Path：後續由後端提供 project-owned code path，前端以 modal
   或 drill-down view 呈現。

## Graph 設計決策

- Node 使用固定寬高，避免 replay/highlight 時 layout shift。
- Edge 使用順序圓點，完整 relationship 放在 detail modal 與 hover title。
- Edge routing 會分 lane，避免同 source 多分支重疊。
- Follow focus 預設開啟，播放 replay/progress 時置中目前聚焦 node。
- 使用者可關閉 Follow，避免自動移動畫面。

## API 對接策略

前端目前支援兩種資料來源：

- Sample：使用 committed `frontend-json-sample.json`。
- API：呼叫 local Python API，預設 `http://127.0.0.1:8000`。

API contract 詳見：

- `frontend/API_CONTRACT.md`

## 後續設計重點

- 等 Timmy 完成 `ViewerSessionService` 後，前端要改以正式 API response 為主。
- Query trace request 需明確 opt-in，missing endpoint 不得送出 query。
- Local model chat 需要獨立 API contract，不應和 graph detail modal 混在一起。
- 需要補 UI regression tests，保護 edge routing、follow focus、detail modal、
  filter highlight 與 replay controls。
