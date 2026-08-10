# 前端 — 邊的證據等級視覺化（observed 實線／undetermined 虛線）（2026-08-10）

Status: **planned — frontend-only task**（2026-08-10 裁定自 16D §8 Q3：不塞進 16D 的 PR，另開）
前置：**16C Task 5 合併後才有意義**（今天後端把每條邊無條件蓋成 `observed`，畫虛線也沒有差異可畫）

問題來源：S2 UA 整合後，圖上的邊將分兩級——`observed`（有真實呼叫點）／`undetermined`
（只有 import 或模板推定）。16D Task 6 提到「可選 polish：undetermined 虛線或降透明度」，
裁定紀錄（`s2-ua-integration/CLARIFICATIONS-2026-08-10.md` Q14③）決定**另開 frontend-only task**，本檔即該 task 的計畫。

---

## 先看結論

| 問題 | 答案 |
| --- | --- |
| 後端要改嗎？ | **不用**。`graph_view_model.edges[].status` 已在契約（`frontend/src/types.ts:75`） |
| 前端要補嗎？ | **要**，量很小——edge render 依 `status` 切換樣式，純 CSS／render 層 |
| 何時能做？ | **16C Task 5 之後**（normalize 改為沿用 `Edge.status`，資料才變真） |
| 禁區 | 不新增 GraphViewModel 欄位；前端不得自組 nodes/edges（16A ④、16D Task 6 契約原則） |
| 優先級 | 低。沒有它功能不壞；有它使用者才能一眼分辨「看到的線」vs「推的線」 |

---

## 現況核對（2026-08-10 逐行核對程式碼）

| 需要的東西 | 現況 | 位置 |
| --- | --- | --- |
| edge 契約帶 `status` | ✅ 已有（nullable） | `frontend/src/types.ts:66-78` `graphEdgeSchema.status` |
| edge 渲染點 | ✅ 單一入口 | `components/SystemGraph.tsx:76`（`BaseEdge ... style={style}`） |
| 資料真的分兩級 | ❌ **還沒有** | 後端 `system_map_v2_normalize_service.py:183` 目前硬蓋 `status="observed"`；16C Task 5 修 |
| 依 status 切樣式的邏輯 | ❌ 沒有 | — |

⚠️ 順手修一行註解：`types.ts:74` 寫 `// Compatibility field used by legacy projections only.`
——16C Task 5 之後這個欄位就是**現役語意**（兩級證據），該註解到時要一併更新，避免誤導。

---

## 規格草案

| status | 樣式 |
| --- | --- |
| `observed` | 實線（現行樣式不動） |
| `undetermined` | 虛線 ＋ 降透明度（具體參數實作時定） |
| `null`／其他 | 視同現行預設（不炸、不猜） |

- 只動 render 層（`SystemGraph.tsx` 的 edge style 分支＋CSS）；`git diff` 不得出現 `types.ts` 或任何 schema 變更。
- **不做**：依 `undetermined_reason` 顯示 tooltip——該欄位不在 edge 契約內，要做屬契約變更，明確不在本案範圍。
- Sample mode（靜態 JSON）需同步確認不壞：sample 資料的邊若無 `status`，落在「視同預設」分支。

## 驗收

- [ ] API mode 載入含兩級邊的 build：實線／虛線肉眼可辨，無 schema 錯誤
- [ ] 契約零變更（`git diff frontend/src/types.ts` 為空）
- [ ] Sample mode 正常渲染
- [ ] `types.ts:74` 註解隨資料變真一併修正

## 排程觸發點

16C Task 5（normalize 沿用 `Edge.status`）合併 → 本 task 可開工。與 16D Task 6 的煙測互補：
煙測驗「資料變真沒壞圖」，本案做「兩級視覺可辨」。
