# 2026-06-01 Phase1 Viewer Frontend Foundation Report

## 實作摘要

本階段建立 Epic 1 Viewer 前端基礎，讓 Hardy 可以在後端 API 尚未完成前，
使用 Timmy 提供的 sample JSON 開發與驗證 graph viewer。

本次新增：

- `frontend/` Vite React TypeScript app。
- pnpm workflow。
- React Flow / ELK graph rendering dependencies。
- Zustand viewer state。
- TanStack Query payload loading。
- Zod viewer payload schema。
- macOS-like app shell。

## 實作邏輯

前端採 sample-first / API-ready 策略：

1. Sample mode 直接讀 committed `frontend-json-sample.json`。
2. API mode 預留 local Python API base URL。
3. Viewer 渲染 `graph_view_model`，不重新掃描 repo。
4. UI state 與 backend canonical facts 分離。

## 實作步驟

1. 建立 frontend package 與 dependencies。
2. 建立 Zod schema 與 sample loader。
3. 建立 sidebar / toolbar / workspace / replay 基礎布局。
4. 建立 React Flow graph canvas。
5. 執行 lint / build。

## 測試方式

```bash
pnpm run lint
pnpm run build
```

## 測試結果

- Frontend lint：通過。
- Frontend build：通過。

## 後續注意

- build 目前有大型 chunk warning，後續可評估 manual chunks。
- API mode 仍需等 Timmy 正式 endpoint。
