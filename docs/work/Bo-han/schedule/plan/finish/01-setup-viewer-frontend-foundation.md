# Task 1: Setup Viewer Frontend Foundation

## 目標

建立 Epic 1 Viewer 的前端專案骨架，讓 RAG System Map Viewer 可以在 local
web app 中獨立啟動、開發與 build。

## 為什麼要先做這個

Epic 1 的產品入口優先順序已偏向 GUI / local web UI。前端需要先有可試用
的 Viewer shell，才能在後端 API 完成前使用 sample payload 驗證 UX 與
資料邊界。

## 前置需求

- 已確認前端只渲染 `graph_view_model`，不重新掃描 repo。
- 已確認技術棧使用 React + Vite + TypeScript。
- 已確認套件管理使用 pnpm。
- 已確認後端主語言為 Python，前後端分開跑。

## 實作範圍

- 建立 `frontend/` Vite React app。
- 設定 TypeScript、ESLint、Vite build。
- 加入 React Flow、ELK、Zustand、TanStack Query、Zod、Lucide。
- 建立 sample payload 載入流程。
- 建立基礎 app shell。

## 不包含範圍

- 不實作後端 scanner。
- 不實作正式 `kai-mind viewer` CLI。
- 不實作 query trace request API。
- 不實作 local model chat API。

## 建議實作步驟

1. 建立 `frontend/package.json` 與 pnpm lockfile。
2. 建立 Vite React TypeScript 專案。
3. 加入 graph / state / data loading 所需 dependencies。
4. 建立 `src/types.ts`，以 Zod 定義 viewer payload shape。
5. 建立 `src/data/sampleMap.ts`，讀取 Timmy 的 sample JSON。
6. 建立 `App.tsx` 與基礎 shell layout。
7. 執行 `pnpm run lint` 與 `pnpm run build`。

## 預期輸出

- `frontend/package.json`
- `frontend/src/App.tsx`
- `frontend/src/types.ts`
- `frontend/src/data/sampleMap.ts`
- `frontend/src/styles.css`

## 驗收標準

- `pnpm run dev` 可啟動 local web app。
- `pnpm run lint` 通過。
- `pnpm run build` 通過。
- Viewer 可使用 sample payload，不依賴 backend API。

## 可能風險與注意事項

- 不要把 scanner logic 放進 frontend。
- 不要在 frontend 自行補 canonical facts。
- 前端 sample shape 必須和 Timmy 的 handoff JSON 對齊。
