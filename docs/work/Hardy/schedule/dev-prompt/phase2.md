# Phase2 Dev Prompt: Graph Viewer and Detail Modal

請實作 RAG System Map graph viewer 與 detail modal。

## 任務

- 用 React Flow render `graph_view_model.nodes` / `edges`。
- 用 ELK 做 layered layout。
- 自訂 node / edge styles。
- 點 node / edge 顯示 detail modal。
- Sidebar filter 只高亮，不隱藏 graph。
- Edge 必須有箭頭與順序標記。

## 驗收

- Sample graph nodes / edges 都可見。
- Node / edge 可點擊。
- Detail modal 顯示 evidence / risk hints。
- Filter 不會刪除 graph elements。
