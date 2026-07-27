# DeepResearch Icon Inventory（2026-07-13）

> 依據 `docs/work/Meeting-Sync/meeting_sync_2026_07_07/frontend-deepresearch-icon-migration.md`。
> Source：`DeepResearch/index.html`、`styles.css`、`script.js`。
> Target：`frontend/src/`。每項標 `migrated` / `not applicable` / `blocked` 與原因。
>
> 實作落點：icon registry 在 `frontend/src/icons/registry.ts`（單一 mapping，lens 與 plane
> 語意都從這裡取）；brand 圖記在 `frontend/src/icons/BrandMark.tsx`。

## 1. Brand icon 與 favicon

| Source | 語意 | Target | 狀態 | 說明 |
|---|---|---|---|---|
| `index.html` `.brand-mark` inline SVG（十字＋斜線＋四節點圓） | 產品識別：node graph 記號 | `frontend/src/icons/BrandMark.tsx`，用於 `Sidebar.tsx` brand 區 | migrated | 重繪為 currentColor 單色 SVG（實心節點），吃 `.brand-mark` 既有 token 配色；不複製示意稿藍/綠/橘/紫色票。原本佔位的 lucide `Sparkles` 讓給 generation plane 語意。 |
| `index.html` data-URI favicon（同記號，彩色） | 瀏覽器分頁識別 | `frontend/index.html` `<link rel="icon">` | migrated | 正式前端原本沒有 favicon。以同一記號重繪，色值取自正式 design tokens（light `--accent-strong` #4d7c0f、dark `--accent` #84cc16，經 `prefers-color-scheme` 切換），不用示意稿色票。 |

## 2. 頁首操作（示意稿用 Unicode 字元）

| Source | 語意 | Target | 狀態 | 說明 |
|---|---|---|---|---|
| `▦` Plan 14 Examples | 開啟 example simulator | — | not applicable | Examples simulator 是示意頁專屬功能，正式前端無此 surface；不為不存在的功能建按鈕。 |
| `↥` Import System | 匯入專案 | `DataSourceControl.tsx`（lucide `Server` + Start scan 流程）、`ScanTemplatePage.tsx` | migrated | 匯入操作在正式前端已存在且已用 lucide 呈現；`↥` 不搬。正式前端沒有任何 Unicode 操作字元殘留。 |
| `✦` Auto-map | 觸發自動 mapping | — | not applicable | Auto-map 在正式流程是 scan pipeline 的 backend 階段（ProgressStrip 顯示進度），沒有獨立操作。 |
| `◈` Validate | 驗證系統 | `App.tsx` Readiness 按鈕（lucide `ClipboardCheck`） | migrated | 語意對應 backend readiness findings，已用 lucide 呈現。 |
| `▶` Run Trace | 執行 runtime trace | — | not applicable（deferred） | Runtime trace 持續 deferred（handoff 2026-07-12 §5.5）。舊 `ReplayTimeline` 用 lucide `Play/Pause`，等 legacy retirement 一併處理。 |

## 3. Filter Views（16 個 CSS 偽元素圖形）

正式前端的對應 surface 是六 lens rail（`LensPanel.tsx`，Meeting Sync 07-07 定案）與
10-plane band（`PlaneBandNode.tsx`）。lens icon 由 `getLensIcon()`、plane icon 由
`getPlaneIcon()` 提供，皆出自 registry。

| Source view | Target | 狀態 | Icon（lucide） |
|---|---|---|---|
| Overview | — | not applicable | lens 全關即 overview（highlight/dim only，不刪節點），無獨立按鈕。 |
| Data Flow | lens `data` | migrated | `ArrowRightLeft` |
| Agent Control | lens `control`；plane `control` | migrated | `Workflow`（lens 與 plane 同語意共用） |
| Ingestion & Indexing | plane `ingestion_indexing` | migrated | `FileInput`（非六 lens，語意轉移到 plane band 標頭） |
| Retrieval & Evidence | lens `evidence`；plane `retrieval`、`evidence` | migrated | lens/evidence plane 用 `FileSearch`；retrieval plane 用 `Search` |
| Memory & State | plane `memory_state` | migrated | `Database` |
| Governance & Observability | lens `governance`；plane `governance_observability` | migrated | `ShieldCheck` |
| Runtime | — | not applicable | runtime trace deferred，無 runtime lens/plane。 |
| Variants | — | not applicable | 無對應功能。 |
| Known Nodes | — | not applicable | known/extension/unmapped 分類在正式版由五態 assessment 與 backend filters 呈現，無此 view。 |
| Extension Systems | plane `extension_subsystems` | migrated | `Puzzle` |
| Unmapped | — | not applicable | unmapped 由 scan summary 數字與 backend 提供的 View filters 呈現，不建 view 按鈕。 |
| Reasoning Mode | — | not applicable | 無對應功能。 |
| Topology | plane `deployment_topology` | migrated | `Network` |
| Source Map | lens `source` | migrated | `Code` |
| Risk Lens | lens `risk` | migrated | `AlertTriangle`（與既有 risk 語意一致） |

其餘 plane：`input_intent` 用 `MessageSquareText`、`generation` 用 `Sparkles`（示意稿無對應
view，為補齊 10-plane registry 而加，仍由 backend `plane_id` 驅動）。unassigned 帶與未知
plane id 不顯示 icon（`getPlaneIcon` 回傳 undefined），不做前端推論。

## 4. Node Inspector detail icon

| Source | Target | 狀態 | 說明 |
|---|---|---|---|
| `.detail-icon ${node.layer}`（依 layer 上色的圓形記號） | `DetailPanel.tsx` inspector head 的 plane chip（icon + 文字標籤） | migrated | 依 backend `node.plane_id` 經 `getPlaneIcon()` 選 icon，附 `planeLabel()` 文字（不只靠顏色/圖形）。`plane_id` 缺（Plan 06 未發布前的常態）→ 不顯示，不推論。`profile_attachment` 已另有 `Anchor` icon（backend `semantic_kind` 驅動）。 |

## 5. Edge legend（8 種線型標記）

| Source | Target | 狀態 | 說明 |
|---|---|---|---|
| `data / control / evidence / tool_call / memory_write / approval / telemetry / deployment` legend-line | — | **blocked** | 現行 contract 的 edge 只有自由字串 `relationship`，GraphViewModel 沒有 typed-edge taxonomy；前端不得自行把 relationship 推導成八類（關鍵決策 #2）。等 backend 發布 edge type taxonomy 後再做 edge legend。建議列入下次 Meeting-Sync 向 Timmy 提出。 |

## 6. 其他視覺元素（非 icon，記錄以示盤點完整）

- Canvas controls（Reset / Fit / Export）：示意稿為純文字按鈕、無 icon；正式版 zoom/fit 已用 lucide `Plus/Minus/Maximize`。not applicable。
- Example tabs、example-button 左框線色塊、hero metrics、status-card、search-box、skip-link：無 icon。not applicable。
- node-card 的 `·` 分隔符：排版符號，非操作 icon。not applicable。

## 驗收對照

以下項目由程式碼與自動測試確認，維持完成：

- [x] 全部 icon 完成 source-to-target inventory（本文件）。
- [x] 有對應 surface 的 icon 完成搬移；正式前端無 Unicode 操作字元。
- [x] Icon 經 `frontend/src/icons/` registry 使用，無重複貼上 SVG markup。
- [x] Custom SVG（BrandMark）用 currentColor 與既有 tokens；favicon 用正式 token 色值並宣告 dark scheme（`prefers-color-scheme` 寫在 data URI 內；分頁列實際渲染未以工具驗證，見下方 QA 狀態）。
- [x] Icon-only 控制項維持既有 aria-label；裝飾性 icon 一律 `aria-hidden="true"`；lens/plane 語意皆有文字標籤，不只靠顏色。
- [x] Regression tests：registry mapping 覆蓋測試（`frontend/src/icons/registry.test.tsx`）＋ LensPanel per-lens icon 測試（`LensPanel.test.tsx`）＋ PlaneBandNode plane icon 測試（`PlaneBandNode.test.tsx`：canonical plane 顯示 registry icon、unassigned/unknown plane 不顯示、icon `aria-hidden`）＋ DetailPanel plane chip 測試（`DetailPanel.test.tsx`：有 `plane_id` 顯示 icon＋文字、缺 `plane_id` 不顯示 chip、unknown plane 只顯示文字不補 icon）。
- [x] 未引入 DeepResearch 的 hard-coded data、schema、inference 或 runtime 行為；未新增 icon library/CDN。

## 視覺 QA 狀態（2026-07-13，Sample mode）

> 前置限制：目前 frontend 預設 Sample payload 是 **ai-system-map/v1**，viewer 因此走 legacy
> auto/whiteboard layout——plane-band（`PlaneBandNode`）與 DetailPanel plane chip 在 Sample
> mode 完全不會出現（實測 DOM：`.plane-band` 0 個、`.plane-chip` 0 個）。這兩個 surface 的
> 完整視覺 QA 需等 v2 payload／Plan 06 contract integration 之後才能進行。
>
> 本輪 QA 於 dev server（port 5174）以 DOM／computed style／keyboard 實測；本機瀏覽器
> 截圖工具持續逾時，故無 pixel-level 截圖佐證，凡需人眼確認的項目標 partial。

| 項目 | 狀態 | 說明 |
|---|---|---|
| Sidebar BrandMark | partial | DOM 確認 `.brand-mark svg` 存在、`aria-hidden`、stroke=currentColor；light（tile #4d7c0f/白 mark）與 dark（tile #84cc16/深色 mark）computed color 皆符合 token。無截圖佐證。 |
| 六 lens icons | partial | DOM 確認 6 個 distinct lucide glyph（arrow-right-left / workflow / file-search / shield-check / code / triangle-alert），皆 `aria-hidden`；v1 Sample 下 6 顆按鈕皆 disabled（tooltip「Backend projection has not published membership for this lens.」），disabled 顏色 token 於 light/dark 均有生效。無截圖佐證。 |
| Light/dark theme 切換 | partial | 以 More tools → Dark theme 切換，`data-theme` 與 body/brand/lens computed colors 正確跟隨 token；無截圖做整頁對比。 |
| Hover / active 狀態 | pending | 需 pixel-level 目視確認，本輪未執行。 |
| Keyboard focus | partial | Tab 實測 `:focus-visible` 產生 2px accent outline（offset 2px），程式化確認可見樣式存在；未逐一掃過全部控制項。 |
| 窄螢幕（390px） | partial | 無水平 overflow（scrollWidth=clientWidth=390）；BrandMark 與 6 個 lens icon 皆完整渲染未裁切。無截圖佐證。 |
| Favicon | pending | `<link rel="icon">` data URI 存在且含 `prefers-color-scheme` 切換；瀏覽器分頁列實際渲染無法以現有工具確認。 |
| Plane-band header icon | pending（blocked on v2） | Sample 是 v1，plane band 不渲染。行為已由 `PlaneBandNode.test.tsx` 覆蓋，視覺確認待 Plan 06。 |
| DetailPanel plane chip | pending（blocked on v2） | 同上；行為已由 `DetailPanel.test.tsx` 覆蓋，視覺確認待 Plan 06。 |
