# 2026-06-02 Phase2 Graph Interaction UX Report

## 實作摘要

本階段改善 Viewer graph interaction 與使用者可讀性，重點是讓 RAG graph
不只是靜態圖，而是可用於 replay / progress / detail drill-down 的互動視圖。

本次新增或改善：

- React Flow 自訂 node handles，修正 edges 不顯示問題。
- Edge arrow 與順序標記。
- Edge label 簡化為順序圓點。
- Edge lane routing，降低多分支重疊。
- Detail panel 改為 modal。
- 右側預留 local model chat panel。
- Follow focus toggle。
- Replay / progress 更新時不重新 layout，減少閃動。
- Replay panel 響應式與密度調整。

## 實作邏輯

主要設計決策：

- `graph_view_model` 是前端唯一 graph rendering input。
- Filter highlight 只改樣式，不刪除 nodes / edges。
- Follow focus 解析順序以目前 progress / trace target 為主，不被 filter
  highlight 干擾。
- Edge relationship 長文字放在 modal / hover title，graph 上只顯示順序。
- 同 source / target edge 加 lane offset，避免線條完全疊在一起。

## 遇到的問題與解法

### 1. Edge 沒有顯示

原因是自訂 `SystemNode` 沒有 React Flow source / target handles。

解法：

- 在 node 左右加入透明 handles。
- 保留現有 node 視覺樣式。

### 2. Highlight 播放時閃動

原因是 replay / progress 每一步都重新 layout / fitView。

解法：

- layout 僅在 graph structure 變更時重新計算。
- replay / progress 只更新 node / edge state。

### 3. Follow 有時不跟隨

原因是舊邏輯用 `isFocused` 猜目標，會被 filter highlight 干擾；edge step
也不一定能找到 node。

解法：

- 明確解析 progress target、trace component、trace edge target、selected target。
- edge target 轉成 target node 後再置中。

### 4. Edge 重疊

原因是多條分支共用同一條垂直 bus。

解法：

- 同 source edge 分配不同 route offset。
- 同 source / target edge 加上 y offset。

## 測試方式

```bash
pnpm run lint
pnpm run build
uv run pre-commit run --all-files
```

也使用本機 Edge headless 截圖做人工畫面檢查。Codex 內建 browser sandbox
在此 Windows 環境無法啟動，錯誤發生於 node_repl kernel 初始化，不屬於
專案程式碼問題。

## 測試結果

- Frontend lint：通過。
- Frontend build：通過。
- pre-commit hooks：通過。
- 本機 Edge headless 可載入 Viewer 並產生截圖。

## 後續注意

- Edge lane routing 是目前 sample graph 的 pragmatic fix；若未來 graph
  節點數增加，可能需要更完整的 collision avoidance。
- Follow focus 需要補自動化 regression test。
- Detail modal 需要補 keyboard / accessibility 行為。
