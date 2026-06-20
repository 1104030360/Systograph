# Task 2: Implement System Map Graph Viewer

## 目標

將 `graph_view_model.nodes` 與 `graph_view_model.edges` 渲染成可互動的 RAG
System Map，讓使用者能看懂 indexing flow 與 query_answer flow。

## 為什麼要做這個

Epic 1 的核心價值不是只產生 JSON，而是讓不熟 RAG 的使用者也能理解系統
架構。Graph Viewer 是前端第一個主要可交付畫面。

## 實作範圍

- React Flow graph canvas。
- ELK layered layout。
- 自訂 `SystemNode`。
- 自訂 ordered edge。
- Edge arrow / sequence label。
- Sidebar highlight filters。
- Zoom / pan / minimap / controls。

## 不包含範圍

- 不產生 backend graph projection。
- 不判斷 component 是否 detected。
- 不實作正式 graph algorithm recommendation。

## 建議實作步驟

1. 將 `graph_view_model.nodes` 轉成 React Flow nodes。
2. 將 `graph_view_model.edges` 轉成 React Flow edges。
3. 用 ELK 產生 deterministic positions。
4. 建立 node handles，確保 edges 可渲染。
5. 將 filter matches 轉成 highlight / dimmed 狀態。
6. 實作 edge lane routing，避免同 source 多分支重疊。
7. 實作 Follow focus，讓 replay/progress 可置中目前 node。

## 預期輸出

- `frontend/src/components/SystemGraph.tsx`
- `frontend/src/components/SystemNode.tsx`
- `frontend/src/utils/graph.ts`
- `frontend/src/components/Sidebar.tsx`

## 驗收標準

- graph 顯示 14 nodes / 10 edges sample。
- indexing 與 query_answer flow 都可辨識。
- edge 有箭頭與順序提示。
- 同 source 多分支不應完全疊在一起。
- filter 只高亮，不移除 graph。

## 可能風險與注意事項

- React Flow 自訂 node 必須提供 source / target handles。
- 播放 replay 時不得每一步重新 layout，否則會造成閃動。
- Edge label 不要用長文字壓在線中央。
