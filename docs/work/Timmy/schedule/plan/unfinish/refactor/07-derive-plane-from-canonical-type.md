# 投影平面改由 canonical type 推導（退役 slot→layer 查表）實作計畫

Status: **planned**（2026-08-06 起草；GitHub issue #277。**與 UA 零相依，可在
s2-ua-integration 之前執行**——這是「slot 殘餘職責」中目前唯一能先做的一項；
有計畫承接的另一項（模板假邊）屬 16C→16D→16G 鏈，留在 s2-ua-integration，
見下方「與 16G 的邊界」）

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:subagent-driven-development` (recommended) or
> `superpowers:executing-plans` to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**GitHub Issue:** #277（umbrella：Web 邊界收斂後端先行，2026-08-07 回填）

**Goal:** 讓 repo component 的 `layer`（投影時的 `plane_id`）由
`canonical_type → capability node → node 所屬 plane` 推導，取代現行的
`slot → SLOT_LAYER_BY_ID` 查表。完成後，slot 誤填不再造成「畫錯帶」，
投影與評估共用同一條 type-driven 語意鏈。

**Architecture:** 純 backend 語意變更 + 前端視覺驗證。輸出契約不變
（`components[].layer` 與 `GraphViewModel.plane_id` 欄位與值域照舊——值域
本來就是 canonical plane id），變的只有**每個元件落在哪個值**。不新增
mapping 表：推導鏈全部用既有資料（`capability_type_node_map.toml` +
52-node catalog 的 per-node plane）。

**Tech Stack:** Python 3.11、pytest、既有 TOML loaders、Playwright MCP
（前端 before/after 視覺驗證）。

---

## 與 16G 的邊界（為什麼 16G 不搬進 refactor）

「slot 殘餘職責」目前只有兩項有實作計畫承接（其餘見文末索引）：

| 殘餘 | 歸屬 | 為什麼 |
|---|---|---|
| **投影平面**（slot→layer→plane） | **本計畫**，UA 零相依 | 推導鏈只需要 13.7 已交付的 type→node 表 + catalog 的 per-node plane |
| **模板假邊**（flows 相鄰） | **16G**，留在 s2-ua-integration | 16G 硬前置 16C（L1/L2 真邊）與 16D（呼叫優先 cutover）；沒有真邊之前刪假邊，圖上一條邊都不剩（16G 自述）。整條鏈本質是 UA 工作，不可先於 Plan 16 |

依使用者工作順序（refactor 全部完成 → 才開始 s2-ua-integration），把 16G
搬進 refactor 會使它先於自己的硬前置執行，屬依賴倒置——**不搬**。

## Source（判準基線，2026-08-06 對程式碼查核，均有行號證據）

- 現行寫入：`system_map_v2_normalize_service.py:121`
  `layer=SLOT_LAYER_BY_ID.get(slot.slot, "undetermined")`；`:120`
  `canonical_type=instance.kind`。
- 現行投影：`graph_projection_service.py:186` `plane_id=component.layer`
  （`:193` subtitle 同源）。
- 評估已是 type-driven：`reference_capability_assessment_service.py:107`
  `self._type_to_nodes.get(component.canonical_type, ())`——投影平面是最後
  一個還掛在 slot 上的主開關。
- catalog 具備 per-node plane：`reference_capability_assessment_service.py`
  `_assessment(node_id, plane_id, ...)` 簽名即證明（plane 由 catalog 提供）。
- `SLOT_LAYER_BY_ID`（`legacy_slot_layer_map.py:19-33`）有兩個消費者：
  active v2 normalize（本計畫切走）與 v1→v2 adapter（migration-only，留）。
- 多對一收斂實例：`vector_db` / `vector_store` / `http_vector_store` /
  `local_persistent_vector_store` / `vector_db_config` 五個 type 全部 →
  `index_builder` 節點——type 詞彙比 52 格細，映射是收斂式的。

## 範圍外

- **模板邊退役**（16G）與任何 UA 相關工作。
- **`metadata.legacy_slot` 的移除**——它另有消費者（graph projection 的
  node id slug 與 node／endpoint `slot` 標籤、detail scan 的
  `component_slot` target、query trace），退場受 16 系列（13-slot
  keyspace）與 public 契約（detail-scan `component_slot`）阻擋，目前
  無人認領。本計畫**不動**這個欄位。
- **Mapping UI 從選 slot 改選 capability**（產品層決策，另案）。

---

## Task 0: 裁定兩條推導規則（**先拍板再動工**）

**(a) 多 node 型別的主平面**：type 可對到多個 node（如
`api_input = ["user_input", "api_server"]`），節點可能跨 plane。

- [ ] **Step 1: 採「陣列第一個 node = primary」的確定性慣例**，並把慣例
  寫進 `capability_type_node_map.toml` 檔頭註解（維護者排序時即決定主平面）；
  或改折衷方案（TOML 加 primary 欄）——擇一並記錄理由

**(b) 對不到表的 type 的 fallback**：`canonical_type` 不在表裡時
（manual mapping 的 `component_kind` 是自由文字，可能產生任意 kind）。

- [ ] **Step 2: fallback = `"undetermined"`**（與現行 slot 查表的 fallback
  同語意），**不得**退回 slot 查表——那會把 slot 依賴從後門帶回來
- [ ] **Step 3: 覆蓋審計**——枚舉 bridge 全部 kind 值與既有 mappings 的
  `component_kind`，比對 TOML key 空間；缺列的補進 TOML（純詞彙擴充，
  不改程式），避免切換當下一批元件掉進 undetermined

## Task 1: 實作 type→plane 推導

**Files:**
- Modify: `src/systograph/core/services/system_map_v2_normalize_service.py`
- Create or extend: type→plane helper（建議放在
  `capability_type_node_map_loader.py` 旁，複用同一份載入與驗證）

- [ ] **Step 1: helper：`canonical_type → primary node → node.plane_id`**，
  查無 type 回 `"undetermined"`
- [ ] **Step 2: `system_map_v2_normalize_service.py:121` 改用 helper**，
  輸入從 `slot.slot` 換成 `instance.kind`（即 canonical_type）
- [ ] **Step 3: 移除該檔對 `SLOT_LAYER_BY_ID` 的 import**
- [ ] **Step 4: `legacy_slot_layer_map.py` 檔頭更新**——它從「雙消費者」
  降為 migration-only（v1 adapter 專用）；順手修正檔頭第 6 行「新的 v2
  元件不應該擴充這張表」的過時語境（現在是真的不會再被 v2 讀到）

## Task 2: 測試

- [ ] **Step 1: helper 單元測試**——單 node、多 node（取 primary）、
  查無 type（undetermined）、TOML 缺列審計案例
- [ ] **Step 2: 關鍵 regression：「slot 誤填不再影響平面」**——構造
  slot 錯、`canonical_type` 對的元件，斷言 plane 正確（這是本計畫的
  行為承諾，也是與現況的可觀察差異）
- [ ] **Step 3: 更新受影響的 normalize / projection 既有測試與 fixtures**；
  其中 `tests/unit/core/test_legacy_slot_layer_map.py:7-10` 的
  `CONSUMER_MODULES` 斷言「v1 adapter 與 v2 normalize 綁同一份 dict」，
  Task 1 Step 3 移除 import 後必然失敗，需縮成只剩 v1 adapter
- [ ] **Step 4: v1 adapter 的 layer 輸出不動**——`SLOT_LAYER_BY_ID` 在
  migration 路徑產出的 layer 值由既有測試鎖住，不得跟著改

## Task 3: 前端視覺驗證（不改前端程式碼）

plane 值域不變，前端 zod 與元件無需修改；但**元件實際落帶會移動**，
需人眼確認新佈局合理。

- [ ] **Step 1: 以 fixture 專案（如 `basic_qdrant_ollama_rag`）跑
  before/after，用 Playwright MCP 截圖比對**
- [ ] **Step 2: 逐一確認移動的元件「新帶位」與其 capability 歸屬一致**
  （例：vector_db → index_builder 所屬 plane）
- [ ] **Step 3: 差異記錄進 PR 描述**（哪些元件從哪帶移到哪帶、為什麼）

## Task 4: 順手清理（小而獨立，可拆單獨 commit）

- [ ] **Step 1: `risk_hint_rules.toml:61` 使用者可見文案去除 "rag-core-v1"
  字樣**（「Required rag-core-v1 slot was not detected...」→ 中性措辭）；
  對應測試同步

## Task 5: 契約文件

- [ ] **Step 1: `docs/MODEL-CONTRACT.md` 中若有描述 layer/plane 來源為
  slot 查表的敘述，更新為 type→node→plane 推導**（執行時 grep `layer` /
  `SLOT_LAYER_BY_ID` / `plane` 相關段落確認）
- [ ] **Step 2: 檔頭呼叫鏈註解**——`legacy_slot_layer_map.py`（Task 1
  Step 4 已含）；`system_map_v2_normalize_service.py` 目前**沒有**檔頭註解
  （第 1 行即 import），依 CLAUDE.md 慣例補上責任／呼叫鏈並寫明 layer 來源

---

## 驗收標準

1. `components[].layer` / `GraphViewModel.plane_id` 值域不變（仍為
   canonical plane id），前端無需改動即可渲染。
2. slot 誤填不再影響平面（Task 2 Step 2 的 regression 鎖住）。
3. `SLOT_LAYER_BY_ID` 在 active v2 路徑零 import；v1 adapter（migration）
   行為不變。
4. Task 0 Step 3 的覆蓋審計完成：切換後 fixture 專案無元件因「type 缺列」
   掉進 undetermined。
5. 視覺 before/after 已比對並記錄；使用者可見文案無 "rag-core-v1" 字樣。
6. `uv run pytest`、`ruff`、`mypy`、`pnpm test` 全綠。

## 風險

- **畫面佈局移動**：這是預期行為不是 bug，但對熟悉舊佈局的使用者是視覺
  變化；以 Task 3 的記錄與 PR 說明對沖。
- **多 node 主平面慣例**：一旦採「第一個 node = primary」，TOML 陣列順序
  就變成語意（重排即改畫面）；檔頭必須寫明，review 時視為 P2 檢查點。
- **自由文字 kind 掉 undetermined**：manual mapping 可寫任意
  `component_kind`；Task 0 Step 3 的審計 + fallback 讓它可見（undetermined
  帶）而非錯置，屬可接受的顯性化。

## 完成後 slot 還剩什麼（供後續追蹤）

本計畫完成後，slot 的殘餘職責只剩：`metadata.legacy_slot` 標籤、模板假邊
（16G）、manual mapping 的 `target_slot` 白名單與 `available_slots`、
`recommended_next_check_service` 的硬編碼 slot 名單，以及 13-slot 偵測
keyspace 本身。**屆時 slot 對投影平面已無任何影響**（graph node id 的 slug
與 `GraphNodeModel.slot` 仍取自 `metadata.legacy_slot`）。

完整歸屬與各項可否動工，見
[`RAG-CORE-V1-RETIREMENT-INDEX.md`](./RAG-CORE-V1-RETIREMENT-INDEX.md)
——注意其中 **C1 / C3b / C4 / C5 / C7 目前無人認領**（本計畫涵蓋 C3a 與 C6）。
