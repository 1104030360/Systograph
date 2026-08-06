# 前端 — 舊 filter UI 是死碼，不是待下架功能（2026-08-04）

Status: **tech debt，可清理**；優先級低；**零使用者可見影響**

問題來源：討論「舊 filter UI 是不是要刪掉的現役功能？」

**校正**：使用者畫面上早就沒有那排 filter 按鈕了。程式裡留著的是一整棵
**沒有任何檔案 import** 的樹，約 1,800 行。所以這不是「功能下架」，是**死碼清理**。

比喻：不是「畫面上還掛著一個準備刪的按鈕」，是「舊遙控器的零件還放在抽屜」。

---

## 先看結論

| 項目 | 內容 |
| --- | --- |
| 使用者現在看得到嗎？ | **看不到**。`App.tsx` 沒有 import `Sidebar`，主畫面走 `ArchitectureViewNav` |
| 從什麼時候開始？ | commit `25f2223`（2026-07-27，#258 "finalize Systograph v2 frontend integration"）把 `Sidebar` 從 `App.tsx` 移除 |
| 死碼規模 | 兩個 orphan root ＋ 被它們拉住的 10 個檔，約 **1,789 行**，另加 `styles.css` 的 `.sidebar` 區塊 |
| 有擋到什麼嗎？ | **沒有**。不擋功能、不影響 bundle 正確性（tree-shaking 會丟掉），也沒有 runtime 成本 |
| 真正的代價 | **持續誤導閱讀者** — 已經害過一次文件寫錯（見下方〈已經造成的實害〉） |
| 建議 | 開一個獨立 PR，只刪碼、零行為改動 |

---

## 死碼樹（2026-08-04 逐檔核對）

### 兩個 orphan root（全 repo 沒有任何檔案 import）

| 檔案 | 行數 |
| --- | --- |
| `frontend/src/components/Sidebar.tsx` | 141 |
| `frontend/src/components/SystemGraph.tsx` | 409 |

`Sidebar` 只在 `styles.css` 還有 CSS class 對應（`:196` `--sidebar-w`、`:202`、`:1322-1327`）。

### 只被上面兩個 root 拉住的檔案

| 檔案 | 行數 | 被誰拉住 |
| --- | --- | --- |
| `components/LensPanel.tsx` ＋ `.test.tsx` | 66 ＋ 83 | Sidebar |
| `components/SystemNode.tsx` ＋ `.test.tsx` | 89 ＋ 57 | SystemGraph |
| `components/PlaneBandNode.tsx` ＋ `.test.tsx` | 26 ＋ 66 | SystemGraph |
| `utils/graph.ts` ＋ `.test.ts` | 358 ＋ 164 | SystemGraph（**但見例外 1**） |
| `utils/lenses.ts` ＋ `.test.ts` | 121 ＋ 95 | graph.ts / LensPanel / icons/registry.ts |
| `icons/registry.ts` ＋ `.test.tsx` | 63 ＋ 51 | LensPanel / PlaneBandNode |

`utils/graph.ts` 的 9 個 export **全部**沒有 SystemGraph 以外的 live consumer——
包含 `createProgressTargets`（`:325`）與 `resolveProgressTargetId`（`:332`），
這兩個現在是**零 consumer**（連 SystemGraph 都沒在用）。

### store 殘留（`store/viewerStore.ts`，零 live consumer）

| 欄位 / action | 位置 |
| --- | --- |
| `activeFilterIds`（預設 `["filter:flow:query_answer"]`） | `:12`, `:48` |
| `toggleFilter` | `:26`, `:63` |
| `clearFilters` | `:28`, `:73` |
| `activeLensId` | `:13`, `:49` |
| `toggleLens` | `:27`, `:69` |

`:48` 那行預設值 `["filter:flow:query_answer"]` 是整棵樹裡**最會騙人的一行**：
讀 store 的人會以為主畫面預設開著一個 flow filter，實際上沒有任何 component 讀它。

---

## 兩個不能整檔刪的例外

### 例外 1 — `utils/planes.ts`（176 行）是混的，要部分清

| 狀態 | 內容 | 誰在用 |
| --- | --- | --- |
| **活著** | `hasBackendPlaneProjection`（`:41`） | `App.tsx:88`、`ArchitectureMap.tsx:107` |
| **活著** | `planeLabel`（`:68`） | `ArchitectureMap.tsx:242`、`DetailPanel.tsx:475` |
| **活著** | `PLANE_PRESENTATION_ORDER`（`:10`） | `ArchitectureMap.tsx:230` |
| **死了** | `layoutPlaneBands`（`:83`）、`PlaneBandModel`（`:45`）、`import type { FlowNodeData } from "./graph"`（`:3`） | 只有 SystemGraph |

→ `planes.ts` **不能刪檔**，只能拆掉死的那半。那個 `FlowNodeData` import 是
`utils/graph.ts` 唯一的活口，拆掉之後 graph.ts 才能整檔刪。

### 例外 2 — `utils/planes.test.ts`（139 行）要改寫，不是刪

它的 helper `flowNodes()`（`:6-19`）用 `createFlowElements` 造測試資料，
但測的是**活著的** `layoutPlaneBands` / `hasBackendPlaneProjection`。
graph.ts 一刪這個檔就編不過 → 要改成直接組 `Node<FlowNodeData>`，
或把 `FlowNodeData` 型別搬進 `planes.ts` 自己持有。

---

## ⚠️ lens **資料**沒有死，死的是舊 helper 與 UI

這是最容易刪過頭的地方。

| 東西 | 狀態 |
| --- | --- |
| `utils/lenses.ts`（helper 模組） | ❌ 死碼，可刪 |
| `components/LensPanel.tsx`（UI） | ❌ 死碼，可刪 |
| **`graph_view_model.filters.lenses`（後端資料 + zod schema）** | ✅ **現役，不准動** |

左側 Data Flow / Runtime / Source Map / Risk 幾個 view 就是靠 lens 資料算出來的——
`utils/architectureViews.ts:83-104` 的 `lensView()` 直接讀 `graph.filters.lenses`，
**沒有經過 `utils/lenses.ts`**。

→ 刪 `LensPanel` / `utils/lenses.ts` 時，**不要順手動 `filters.lenses` 的 zod schema 或後端契約**。

---

## 已經造成的實害

`../meeting_sync_2026_07_28/frontend-v2-cutover-handoff.md` 有兩處是把死碼當活的在寫：

| 位置 | 寫了什麼 | 實際 |
| --- | --- | --- |
| 2-2「Sidebar 全 unknown（RC-4）」 | 當成 API mode **現在就壞**的畫面，開了修復步驟 | `App.tsx` 沒 import Sidebar，使用者根本看不到。commit `25f2223`（2026-07-27）就移掉了，比該文件早一天 |
| 1-1 提到 `App.tsx:114` 的 `resolveProgressTargetId()` | 當成 highlight 路徑上的活函式 | `resolveProgressTargetId`（`utils/graph.ts:332`）現在全 repo **零 consumer**；`App.tsx:114` 是 `useState(chatOpen)` |

**這就是清理的真正理由**——不是省 bundle，是止血：每個讀這棵樹的人都會再誤判一次。
清完之後 2-2 那項不是「被修好」，是**連同 Sidebar 一起消失**。

---

## 建議做法

**一個獨立 PR，只刪碼，零行為改動。**

順序（讓 tsc 當嚮導，不要憑記憶刪）：

1. 刪兩個 root：`Sidebar.tsx`、`SystemGraph.tsx`
2. `pnpm build` → tsc 會指出還有誰在引用，逐層往下刪
3. 拆 `planes.ts` 的死半邊、改寫 `planes.test.ts`
4. 最後清 `viewerStore.ts` 的五個欄位／action 與 `styles.css` 的 `.sidebar` 區塊

### 驗收

- [ ] `cd frontend && pnpm lint && pnpm test && pnpm build` 三關全綠
- [ ] Sample / API 兩模式主畫面**與刪除前完全一樣**——因為這些 component 本來就沒渲染。
      **出現任何畫面差異 = 刪錯東西了，回頭查。**
- [ ] `rg "Sidebar|SystemGraph|LensPanel|activeFilterIds" frontend/src` → 0 命中
- [ ] `graph_view_model.filters.lenses` 的 zod schema 一個字沒動；左側 Data Flow /
      Runtime / Source Map / Risk 四個 view 仍算得出 node 數

### 優先級與時機

**低。** 沒有使用者可見影響，也沒擋任何功能。適合當成別的 frontend PR 的前置清場，
或在有人下次要改 viewer 結構之前先做掉。

**唯一該提前做的情況**：如果要接著做
`./frontend-assessment-status-filter.md` 的五態篩選——那份會改 `ArchitectureMap.tsx` /
`ArchitectureViewNav.tsx` / `App.tsx`，先清掉死碼可以避免又有人去改 `Sidebar` 裡那份
不會執行的 filter 邏輯。

---

## 附帶掃到的其他 orphan（**不屬於 filter UI，另案處理**）

同一次死碼掃描順手掃到，但跟 filter 無關，**不要混進同一個 PR**：

| 檔案 | 行數 | 備註 |
| --- | --- | --- |
| `components/MappingCompletenessPanel.tsx` | 47 | ⚠️ completeness **有在畫**，在 `MapStatusBar.tsx:28-33`。這個 panel 是另一個沒接上的版本 |
| `components/HistoricalBuildIndicator.tsx` | 24 | — |
| `components/SampleDataIndicator.tsx` | 16 | 由 #223「show persistent sample data indicator」引入，後來被 #258 斷線 |

**刪之前先確認不是「做好了忘記接線」。** 這三個都是曾經有人寫完的 UI，
跟舊 filter UI（被新設計取代）的性質不同——可能是該接回去，不是該刪。

---

## Source of truth

- 程式現況：本文所有 file:line 皆為 2026-08-04 逐檔核對（`frontend/src/`）
- 何時斷線：`git log -S 'components/Sidebar' -- frontend/src/App.tsx` → `25f2223`（2026-07-27, #258）
- 過期描述的出處：`../meeting_sync_2026_07_28/frontend-v2-cutover-handoff.md` 2-2 / 1-1
- 同批文件：`./frontend-assessment-status-filter.md`（五態篩選可行性）
