# 前端工作事項：搬移 DeepResearch Icon

Last updated: 2026-07-07（UA 整合決策對齊）

> 對象：Hardy／Frontend

2026-07-07 UA 整合決策：本文件範圍不受影響；icon 搬移不涉及 backend scan、public artifact
或 JSON schema 變更。

## 目的（Purpose）

將 `DeepResearch` 示意頁內使用的所有 icon，整理並搬到正式 React 前端
`frontend`，讓正式頁面沿用示意稿的視覺語意。

`DeepResearch` 只是視覺參考來源。本工作事項只搬移 icon 與其必要的呈現樣式，不搬移
示意頁的 HTML 結構、JavaScript 行為、hard-coded data、graph contract 或 inference logic。

## Source / Target

- Source：`DeepResearch/index.html`、`DeepResearch/styles.css`、
  `DeepResearch/script.js`
- Target：`frontend/src/` 內現有頁面與共用 UI components
- 正式前端目前已使用 `lucide-react`；通用操作 icon 應優先沿用此 dependency，示意稿特有的
  brand／filter icon 才建立可重用的 React SVG component。

## Icon Inventory

搬移前先建立 source-to-target mapping，至少涵蓋以下 icon／視覺符號：

1. Brand icon 與 favicon。
2. 頁首操作：Plan 14 Examples、Import System、Auto-map、Validate、Run Trace。
3. Filter Views：Overview、Data Flow、Agent Control、Retrieval & Evidence、
   Memory & State、Governance、Runtime、Variants、Known Nodes、Extension Systems、
   Unmapped、Reasoning Mode、Topology、Source Map、Risk Lens。
4. Node Inspector 的 detail icon；正式呈現需依 backend-provided node/layer metadata
   選擇 icon，不得由 frontend 自行推論 node 類型。
5. Edge legend 的 data、control、evidence、tool call、memory、approval、telemetry、
   deployment 視覺標記。

若盤點時發現 `DeepResearch` 還有未列出的 icon，也必須納入 mapping；不能只搬目前畫面上
最顯眼的一部分。

## 實作要求（Implementation Requirements）

- 建立單一、可搜尋的 icon registry 或 mapping，避免同一語意散落在多個 component。
- 對應現有正式前端功能與 backend contract；示意頁中正式前端尚未提供的操作，不得為了
  放置 icon 而建立假的可操作按鈕。
- 通用操作使用 `lucide-react` 的語意相符 icon；無對應圖示時才建立專案內 custom SVG。
- Custom SVG 使用 `currentColor` 與既有 design tokens，不 hard-code 示意頁色票。
- Icon 尺寸、stroke、hover、active、disabled、warning 與 dark theme 狀態需符合現有
  `frontend` 樣式系統。
- 裝飾性 icon 使用 `aria-hidden="true"`；icon-only button 必須有可理解的 `aria-label`
  與 focus state，狀態不可只靠顏色表達。
- 不新增 icon font、外部 CDN 或第二套通用 icon library。
- 不直接複製整段 `DeepResearch/styles.css`、`index.html` 或 `script.js` 到正式前端。

## 驗收標準（Acceptance Criteria）

- [ ] 已完成 `DeepResearch` 全部 icon 的 source-to-target inventory，且每個項目都有
      `migrated`、`not applicable` 或 `blocked` 狀態與原因。
- [ ] 正式前端已有對應 surface 的 icon 全部完成搬移，不再使用示意稿中的 Unicode
      字元作為正式操作 icon。
- [ ] Icon 透過共用 component／registry 使用，沒有在頁面中重複貼上相同 SVG markup。
- [ ] Light／dark theme、hover、active、disabled、warning 與 keyboard focus 狀態可辨識。
- [ ] Icon-only controls 具備 accessible name；狀態與分類不只依賴顏色。
- [ ] Desktop 與窄螢幕 viewport 下，icon 不會裁切、重疊或遮住文字與主要操作。
- [ ] Existing frontend component/integration tests 通過，並補上 icon mapping 與主要
      accessibility behavior 的 regression tests。
- [ ] 搬移沒有引入 `DeepResearch` 的 hard-coded data、schema、inference 或 runtime 行為。

## 不包含範圍（Out Of Scope）

- 重做整個 `DeepResearch` 頁面或直接取代目前 `frontend`。
- 搬移示意頁的 graph data、filter logic、node inference、runtime trace 或 simulator 行為。
- 為正式 frontend 尚不存在的功能建立假資料或無效操作。
- 修改 backend API、artifact schema 或 canonical graph contract。

