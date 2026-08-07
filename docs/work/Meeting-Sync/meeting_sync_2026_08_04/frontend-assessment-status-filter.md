# 前端 — 五態篩選（Assessment status filter）可行性與範圍（2026-08-04）

Status: **product decision pending**（不是既定待補項）；若決定要做 → **純前端，backend 零改動**

問題來源：討論「五態篩選是不是後端做好、前端欠補？」
結論先講：**不是半套交接**。後端該給的資料早就在，前端也早就把狀態畫在卡片上；
缺的是「依狀態篩選」這個**尚未做的產品決定**。決定要做的話，工作全在 `frontend/`。

---

## 先看結論

| 問題 | 答案 |
| --- | --- |
| 後端要改嗎？ | **不用**。`graph_view_model.nodes[].status` 已載五態 |
| 前端要補嗎？ | **要**，但補的量很小——既有 dim 機制多接一個條件 + legend 變可點 |
| 有沒有前置地雷？ | **有一個，必修**：`utils/assessment.ts:52` 的 fallback 是 `"detected"`（見下節） |
| 該先做什麼？ | 先定三個產品決定（詞彙／dim-vs-hide／組合語意），再寫程式 |
| 優先級 | 低—中。沒有它不會壞任何東西；有它才有「只看沒查到的格子」這種讀圖方式 |

---

## 現況核對（2026-08-04 逐行核對程式碼）

做這個功能需要的零件，**五件裡有四件已經存在**：

| 需要的東西 | 現況 | 位置 |
| --- | --- | --- |
| 每個 node 帶五態 | ✅ 已有 | `frontend/src/types.ts:39`（`graphNodeSchema.status`，型別 `nullableString`） |
| 五態 → 顯示 key 的映射 | ✅ 已有 | `frontend/src/utils/assessment.ts:42` `nodeStatusKey()` |
| 六格狀態 legend | ✅ 已渲染，但**純展示、不可點** | `components/ArchitectureViewNav.tsx:87-95` ← `utils/assessment.ts:29-36` `PHASE2_STATUS_LEGEND` |
| 卡片上顯示狀態（色點＋文字） | ✅ 已有 | `components/ArchitectureMap.tsx:65, 87-88`（`dr-status-dot s-${status}`） |
| 「不符合條件就 dim」的機制 | ✅ 已有（view + search 正在用） | `components/ArchitectureMap.tsx:126-128` `nodeMatches()` → `:256` / `:289` 的 `dimmed` prop |
| **依狀態篩選的 UI 與狀態** | ❌ **沒有** | — |

所以實作 = 把 legend 從展示變 toggle，再讓 `nodeMatches()` 多吃一個條件。不是從零長一個篩選系統。

---

## ⚠️ 前置修復（必做，否則篩選會說謊）

`frontend/src/utils/assessment.ts:42-53`：

```ts
export function nodeStatusKey(data) {
  if (data.status && PHASE2_STATUSES.has(data.status)) return data.status;
  if (hasNodeLevelRisk(data)) return "risk";
  // ... 五個 legacy 值 ...
  return "detected";        // ← :52 fallback
}
```

`graphNodeSchema.status` 是 `nullableString`。後端沒給、或給了不在 `PHASE2_STATUSES`
裡的值時，前端會把這個 node 畫成 **detected**。

- **今天的傷害**：顏色偏樂觀，但使用者還能點進 Detail 自己判斷。
- **做了篩選之後的傷害**：使用者勾「只看 detected」→ 這些**沒有直接證據**的 node
  會被當成有證據的留在畫面上。這直接違反 `docs/MODEL-CONTRACT.md` 的
  「`detected` requires direct evidence」與「absence of evidence ≠ negative evidence」。

篩選會把一個「顯示偏差」升級成「契約謊言」，因為篩選的語意是**斷言**（我留下的就是 detected），
而色點只是提示。

**改法**：fallback 改成 `"undetermined"`。

這就是 `../meeting_sync_2026_07_28/frontend-v2-cutover-handoff.md` 第 3 批的
**3-3（RC-10）**，當時列在「不急」的第 3 批，**至今未做**（2026-08-04 核對，`:52` 仍是 `"detected"`）。
做五態篩選之前必須先收掉——順序不能顛倒。

---

## 要先定的三個產品決定

寫程式前先決定，否則會做到一半才發現語意不對。

### 決定 1：篩選的詞彙是幾格？

三套詞彙目前並存：

| 來源 | 內容 |
| --- | --- |
| MODEL-CONTRACT 五態 | `detected` / `partial` / `undetermined` / `not_detected` / `conflicted` |
| `PHASE2_STATUS_LEGEND`（`utils/assessment.ts:29-36`） | 上面五個 **＋ `needs_review`** = 6 格 |
| `nodeStatusKey()` 實際可能回傳（`utils/assessment.ts:3-16`） | 上面六個 ＋ `confirmed_non_baseline` ＋ `risk` ＋ 5 個 legacy（`not_applicable` / `not_configured` / `missing` / `confirmed` / `needs_confirmation`） |

**建議**：chips 用 **legend 的 6 格**。理由是使用者眼睛看到的 legend 就是 6 格——
只給 5 個 chip 會讓人以為漏掉一種。其餘回傳值不給 chip，歸「未列入」且不受篩選影響（永遠顯示）。

⚠️ 別做的事：不要在前端自己重新分類或合併狀態。五態的唯一擁有者是後端
`ProfileInferenceService`（見 `CLAUDE.md` 契約不變式）。

### 決定 2：dim 還是 hide？

**建議 dim**（沿用現有 `is-dimmed`），理由有二：

1. 主圖是**固定 52 格參考能力地圖**，不是動態結果清單。hide 會讓格子憑空消失，
   破壞「這是一張固定的能力清單、沒查到也要留位子」的心智模型——那正是這張圖的重點。
2. plane 標題的計數 `focusedCount/total`（`ArchitectureMap.tsx:246`）需要 total 當分母。
   hide 之後分母沒有意義。

若真要 hide，額外要決定：plane 被篩空時顯示什麼。現有的 `dr-plane-empty` 文案是
「No backend node published in this plane.」（`ArchitectureMap.tsx:262`）——那是**後端沒給節點**，
跟「被你篩掉了」語意完全不同，不能沿用。

### 決定 3：跟現有 view / search 怎麼組合？

**建議 AND**（三者同時滿足才算 focused），與現行 view AND search 的作法一致
（`ArchitectureMap.tsx:126-128`）。

順帶要決定：左側 view 按鈕上的計數 `view.matchesNodeIds.length`
（`ArchitectureViewNav.tsx:80`）目前**不含** search 與 status。
**建議維持不變**——它的意義是「這個 view 本身涵蓋幾格」，讓它隨篩選跳動會讓人無法比較 view 大小。

---

## 實作範圍（決定之後）

純前端，5 個檔，backend 與 schema 零改動。

| 檔案 | 改什麼 |
| --- | --- |
| `utils/assessment.ts:52` | **前置修復**：fallback `"detected"` → `"undetermined"` |
| `App.tsx`（`:116` `nodeSearch` 旁） | 加 `const [statusFilter, setStatusFilter] = useState<NodeStatusKey[]>([])`；空陣列 = 不篩 |
| `App.tsx:450-482` | `ArchitectureViewNav` 多傳 `statusFilter` / `onStatusFilterChange`；`ArchitectureMap` 多傳 `statusFilter` |
| `ArchitectureViewNav.tsx:87-95` | legend 的 `<span>` 改 `<button aria-pressed={...}>`；加「清除篩選」路徑（點掉全部 = 回到不篩） |
| `ArchitectureMap.tsx:126-128` | `nodeMatches()` 多一個 clause：`(statusFilter.length === 0 \|\| statusFilter.includes(nodeStatusKey(node)))` |

**邊（edge）不做狀態篩選。** `graphEdgeSchema.status`（`types.ts:64-76`）的註解已寫明
「Compatibility field used by legacy projections only」——邊沒有五態。
邊沿用現有「兩端 node 有沒有 match」的規則（`ArchitectureMap.tsx:163-174`），
不要為了對稱去發明一套邊的狀態篩選。

### 測試

| 檔案 | 補什麼 |
| --- | --- |
| `utils/assessment.test.ts` | `status` 為 `null` / 未知值時回傳 `undetermined`（不是 `detected`）——鎖住前置修復 |
| `components/ArchitectureMap.test.tsx` | 只勾 `partial` 時，detected 卡拿到 `is-dimmed`、partial 卡沒有；空陣列時全部不 dim |
| `components/ArchitectureViewNav.test.tsx` | legend chip 的 `aria-pressed` toggle 行為 |

### 驗收

- [ ] `cd frontend && pnpm lint && pnpm test && pnpm build` 三關全綠
- [ ] **API mode** 掃 fixture（建議 `tests/fixtures/rag_projects/pgvector_openai_rag`），
      只勾 `detected` → 隨機點三張留下來的卡，DetailPanel 都要看得到 direct evidence。
      **有任何一張沒有 direct evidence 卻被留下 = 前置修復沒收乾淨。**
- [ ] 切 view、打字搜尋、勾狀態三者交叉操作，plane 計數 `focusedCount/total` 不出現負數或超過 total
- [ ] ⚠️ 不要只在 **Sample mode** 驗收——sample 是否已重生為 v2 見
      `../meeting_sync_2026_07_28/frontend-v2-cutover-handoff.md` 3-1

---

## 明確不做

| 不做 | 為什麼 |
| --- | --- |
| 前端自行反推 / 覆寫五態 | `ProfileInferenceService` 是 52-node 評估的唯一擁有者（`CLAUDE.md` 契約不變式） |
| 「依 profile 篩選主圖」 | 那是另一條路徑。資料關聯方向是 **profile 卡 → `related_component_ids`**，沒有 node → 卡的反查投影；要做等於要後端加東西，不在本文範圍 |
| 前端自算 mapping completeness 來配合篩選 | completeness 以後端 `graph_view_model.mapping_completeness` 為準（`MapStatusBar.tsx:28-33`），不因篩選改變 |

---

## Source of truth

- 契約：`docs/MODEL-CONTRACT.md`（五態規則、`detected` 需 direct evidence、GraphViewModel 規則）
- 前置修復的原始出處：`../meeting_sync_2026_07_28/frontend-v2-cutover-handoff.md` 3-3（RC-10）
  ＋ `docs/work/Timmy/schedule/report/2026-07-28/2026-07-28-plan13-residue/residue-C-frontend.md`
- 程式現況（本文所有 file:line 皆為 2026-08-04 核對）：
  `frontend/src/utils/assessment.ts`、`frontend/src/components/ArchitectureMap.tsx`、
  `frontend/src/components/ArchitectureViewNav.tsx`、`frontend/src/App.tsx`、`frontend/src/types.ts`
- 同批文件：`./frontend-legacy-filter-ui-dead-code.md`（舊 filter UI 死碼清理）
