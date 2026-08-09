# `rag-core-v1` 退場 — 歸屬索引（不是實作計畫）

> **這份文件的用途：** `rag-core-v1` 模板的退場工作**沒有單一計畫**，散在
> `refactor/`、`s2-ua-integration/` 與「無人認領」三處。本索引把每個滲透點
> 對應到擁有者，讓缺口可見、不再遺忘。**它不含可執行 Task**（Task 在各自
> 的計畫裡），只有一個例外：§4 的交接修正已於 2026-08-06 執行完畢。
>
> 建立日期：2026-08-06（依當日四路平行程式碼查核結果）
> 維護規則：任一滲透點易主或完成時更新本表；全部清空即可刪除本檔。

---

## 0. 先分清楚兩種 v1（最常見的誤解）

| | `rag-core-v1` **template** | `ai-system-map/v1` **schema** |
|---|---|---|
| 實體 | `core/templates/rag-core-v1.json`（13 slots / 2 flows，凍結） | `RagSystemMap` / 舊 map JSON |
| 職責 | Step 4 把掃到的碎片**歸類** | 整份 map 檔案的**形狀** |
| active path | **仍在執行** | 零執行（僅 operator rollback / 讀舊檔） |
| 退場計畫 | **本索引** | `refactor/06`（寫入路徑，不受 Gate-4 約束）+ `refactor/15`（讀取／相容路徑，受 Gate-4 約束） |

**Plan 15 不碰 template**——其第 17 行明文允許 `rag-core-v1@1.0.0` 保留為
scanner 內部 grounding。本索引處理的是「把它從 active path 移除」這件事。

---

## 1. 七個滲透點與擁有者

| # | 滲透點 | 位置 | 擁有者 | 可否現在做 |
|---|---|---|---|---|
| C1 | **13-slot 偵測 keyspace** 與 detected/missing/not_applicable 三態 | `system_map_v2_materialization_service.py:89` → `component_detection_service.py:121-156` | **無人認領** ⚠️ | ❌ 得先解掉 C2（16G，硬前置 16C→16D）的 slot_order 依賴 |
| C2 | **模板假邊**：`flows[].slot_order` 相鄰配對 → `edges[]`；`RELATIONSHIPS` 12 條寫死語意 | `…materialization:126-129` → `flow_derivation_service.py:68-96`、`:18-30` | **16G** | ❌ 硬前置 16C → 16D |
| C3a | ~~`components[].layer`（slot → `SLOT_LAYER_BY_ID` 查表 → 投影 `plane_id`）~~ → 已改為 `canonical_type` → capability node → `node.plane_id` 推導 | `system_map_v2_normalize_service.py:150`（`self._plane_resolver.plane_for(instance.kind)`）＋ `canonical_type_plane_map.py` | **`refactor/07`** | ✅ **已完成**（2026-08-07，#277，commit `fb65e27`） |
| C3b | `metadata.legacy_slot` / `required_for_rag` 寫進每顆 repo component | `system_map_v2_normalize_service.py:156-157` | **無人認領** ⚠️ | ❌ `legacy_slot` 消費者含 public 契約，見 §2 |
| C4 | `available_slots`：13 slot 進 LLM evidence packet 與前端 ProposalModal | `manual_mapping_support.py:20` → `mapping_proposal_routes.py:87` | **無人認領** ⚠️ | ⏸ 需先做產品決策，見 §3 |
| C5 | `EXISTING_SLOT.target_slot` 白名單 = 13 slot | `manual_mapping_support.py:20` → `manual_mapping_service.py:50,171-174` | **無人認領** ⚠️ | ⏸ 同 C4 |
| C6 | ~~使用者可見文案含 `"rag-core-v1"` 字樣~~ → 已改為中性措辭（`"Required core slot was not detected..."`） | `risk_hint_rules.toml:61` + `risk_hint_service.py:122-130` | **`refactor/07` Task 4** | ✅ **已完成**（2026-08-07，#277，commit `fb65e27`） |
| C7 | `RUNTIME_CRITICAL_SLOTS` / `RAG_TRUST_CRITICAL_SLOTS` 兩組硬編碼 slot 名單驅動 public `recommended_next_checks[]` | `recommended_next_check_service.py:42-58,166,208` | **無人認領** ⚠️ | ❌ 綁在 C1 上 |

**現況小結（2026-08-07 更新）：** **C3a 與 C6 已由 `refactor/07` 完成**
（commit `fb65e27`）——`SLOT_LAYER_BY_ID` 在 active v2 路徑零 import，降為
v1→v2 adapter 專用的 migration-only 表；使用者可見文案不再含 `rag-core-v1`
字樣，並由 `test_packaged_risk_copy_never_names_the_legacy_template` 擋回寫。

剩下五項：C2 有計畫但被前置（16C → 16D → 16G）擋住；
**C1 / C3b / C4 / C5 / C7 仍沒有任何計畫**，且**沒有一項現在可執行**——
C1／C7 卡在 C2，C3b 卡在 public 契約（見 §2），C4／C5 卡在產品決策（見 §3）。

`refactor/07` 完成後 slot 對**投影平面**已無任何影響，但仍決定
`ComponentInstance.id` 的 slug（`component:<slot>:<name>`）與 graph node id
——那部分屬 C1 射程。另注意 `layer` 有**第二個消費者**：plane-based lens
membership（`graph_lens_projector`），已隨本次一併寫進
`MODEL-CONTRACT.md` §5.1.1 並加上 regression。

---

## 2. C3b 為什麼不能單獨拔

`metadata.legacy_slot` 在 active v2 路徑有**三個消費檔（五處讀取）**，逐一都要
有替代來源才動得了：

- `graph_projection_service.py:179-180, 277-281, 325-326` — GraphNode id 的 slug
  前綴與 `slot` 標籤，以及 GraphEndpoint 的 `slot`（前端 `types.ts:38,100`
  有對應欄位）
- `detail_scan_service.py:227, 263` — `component_slot` target 解析與 evidence 回填
- `query_trace_service.py:328`

另兩處常被一起數進來，但它們讀的是 `ComponentDetectionResult.components_by_slot`
（Step 4 的 13-slot keyspace）而不是 map metadata，**屬 C1／C5 射程，拔 C3b 動不到**：

- `system_map_v2_normalize_service._risk_hints`（`:198`）— `target_type ==
  "component_slot"` 反查 `components_by_slot` 才能把 risk 綁回 component
- `manual_mapping_service.py:50, 171-174` / `manual_mapping_materializer.py:61`

C3b 的另一半 `metadata.required_for_rag` **零讀取點**（`src/`、`frontend/src/`
全域查無消費者；v2 schema 的 `metadata` 是 `additionalProperties: true`），
只有 v2 fixture 帶著它——這半可與 `legacy_slot` 分開拔。注意
`risk_hint_service.py:123` 讀的是 `ComponentSlot.required_for_rag`（Step 4 偵測
結果，屬 C1），不是這個 metadata key。

其中 `detail_scan_service` 的 `component_slot` 是 **public 契約**
（`docs/API-GUIDE.md:680` 明列它為合法的 detail-scan `target_type`），改動需契約
決策，不只是重構。risk hint 則相反：v2 的 `CanonicalRiskHint.target_type` 只有
`component / endpoint / evidence / file`（`ai_system_map_v2.py:69`），
`component_slot` 在 normalize 時已被解析成 `component` 或 `evidence`，**不進公開
產物**；真正把 `component_slot` 寫進公開產物的是 C7 的 `recommended_next_checks[]`
（`MODEL-CONTRACT:336`）。

---

## 3. C4 / C5 的阻塞是產品決策，不是技術

Mapping UI 目前讓使用者「選 slot」。要換成「選 capability／canonical
component」需要先拍板：

- Proposal 給 LLM 的 `available_slots` 換成什麼詞彙（52 格 capability？
  canonical type？）
- `ManualMapping.mapping_type` 的 `EXISTING_SLOT` 語意是否重新定義
- 既有已確認 mapping 的 `target_slot` 值如何解讀（歷史資料相容）

**決策未定之前不應寫實作計畫。** 相關前端工作若啟動，走
`docs/work/Meeting-Sync/` handoff。

---

## 4. 交接斷點（**已於 2026-08-06 修正**）

`16G` §1.2 原本寫：slot 清單的退場「屬 `13.7` 的射程，本計畫不碰」。

但 **13.7 已完成並移入 `finish/`**，且它交付的是**能力對照**那半
（`capability_type_node_map.toml`、清除 `_LEGACY_SLOT_TO_NODES`），
**未涵蓋 Step 4 的 13-slot 偵測**。交接對象關門、包裹沒人收——這正是
C1 長期無人認領的根因。

已將 16G §1.2 的指標更正為指向本索引。

---

## 5. 回歸保護缺口（跨切面）

`tests/contracts/test_v2_cutover_consumer_allowlist.py` 的 `LEGACY_LITERALS`
**完全不含** `rag-core-v1` 相關詞彙（`RagTemplateService`、`RagTemplate`、
`"rag-core-v1"`、`legacy_slot`、`components_by_slot`、`SLOT_LAYER_BY_ID`）。
其 `src/systograph` 那條走 Python AST（`:320-347`），字串常數只比對**完整相等**
（`node.value in LEGACY_LITERALS`），子字串形式一律逃脫；`frontend/src` 與
`scripts` 那條走的是 word-boundary regex（`:304-317`），能命中較長文字內的子字串
——所以「子字串逃脫」只適用於 Python 路徑。掃描根目錄也不含 `tests/`，副檔名只
收 `.ts/.tsx/.json/.sh/.py`，**`core/rules/*.toml` 完全不在射程**（C6 的文案就在
那裡）。

**後果：C1–C7 目前沒有任何回歸保護**，gate 全綠不代表 legacy 已退場。
補測試的工作已列為 **`refactor/15` Task 0**（純增測試、不受 Gate-4 約束、
現在就能做）——建議在動任何 C 項之前先完成它。

---

## 6. 建議順序

```text
已完成
  └─ refactor/07          C3a 投影平面 + C6 文案（2026-08-07, fb65e27）

現在可做
  └─ refactor/15 Task 0   補 census 盲區（給後續改動上保險）

s2-ua-integration（refactor 全部完成後才進）
  16 → 16C → 16D → 16G   解鎖 C2

待 16G 落地後才有意義
  C1（13-slot keyspace）→ 連帶解鎖 C3b、C7

獨立於技術進度
  C4 / C5  需先做 mapping UI 的產品決策
```

**別誤讀 16C：** 它是**邊**推導（`ComponentResidenceIndex` + L1/L2），輸入是
Step 4 已產出的 `ComponentInstance`（16C §3.1），**不生產也不取代元件分類**。
C1 卡在 16 系列的真正理由是 C2：`FlowDerivationService` 直接 key 在
`slot_order` 上，那條沒拆掉之前 13-slot keyspace 動不了。替代詞彙則已由 13.7
的 `capability_type_node_map.toml` 備好。

## 7. 完成定義

七項全部清空後：`rag-core-v1.json` 不再被 active path 載入
（`RagTemplateService.load` 僅剩 migration/測試用途或一併退役），
`grep -rn "rag-core-v1\|legacy_slot\|components_by_slot" src/systograph` 只
剩 legacy migration 路徑。屆時本索引可刪除。
