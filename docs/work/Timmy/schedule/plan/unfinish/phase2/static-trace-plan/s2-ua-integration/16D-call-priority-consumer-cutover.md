# 16D — Call-Priority Consumer Cutover（消費者改 call 優先）

> 📖 **第一次看？** 先讀 [`README.md`](./README.md)（閱讀順序 + 名詞對照表）。
> **白話一句話：** 16C 把三種等級的邊都推導出來之後，讓下游（產出檔案、profile 判定、
> 前端圖）真的**以「看到的呼叫」為主**，模板猜測退為備援。
> **Cutover = 切換**，指正式把主力從舊做法換成新做法。

Status: planned — **依賴 Plan 16 Gate-2 structural path + [`16C`](./16C-component-attribution-and-edge-derivation.md) L1/L2/L3 邊推導落地之後**

> **執行者注意：** 逐 task 實作；步驟使用 checkbox（`- [ ]`）以便追蹤。
>
> **本檔補的缺口：** [`16A`](./16A-q3-lv2-call-graph-flow-visualization.md) §3.2 右欄寫
> 「FlowDerivation 從模板假想改 call 優先的完整行為切換」——**不在 Plan 16 一次做完**。
> [`16C`](./16C-component-attribution-and-edge-derivation.md) 已定義檔案層→元件層的
> L1/L2/L3 推導與模板邊降級標籤；本檔負責 **materialization / static execution /
> profile 消費路徑正式以 call 邊為主**，完成 16A §6 第 3～5 步。
>
> **與 16C 的分工（避免重複實作）：**
>
> | 計畫 | 做什麼 | 不做什麼 |
> |------|--------|----------|
> | **16C** | `ComponentResidenceIndex`、`UaEdgeDerivationService`、關係 TOML、L3 標 `undetermined` | 不改 materialization 誰是 primary；不收斂 profile 文案；不 polish 前端 |
> | **16D（本檔）** | Step 4～7 消費順序改 call 優先；static execution siblings 吃同一批邊；profile／G5c 驗收；可選關閉 L3；viewer 煙測／虛線 | 不重寫 UA sidecar；不發明新 reference node |

---

## 1. 目標

> **白話版：** 16C 會產出三種可信度的線（看到呼叫 / 只有 import / 只是模板猜的）。
> 這份計畫負責讓**下游全部改用同一批線**，而且優先採信可信度最高的那種。
> 「下游」指三個地方：產出的地圖檔、靜態執行的那幾個檔案、以及 15 張 profile 卡的判定。
> 現在的問題是它們**各算各的**，這份要讓它們統一。

讓 canonical（正規版，系統認定的唯一標準）edges 的**真相順序**變成：

```text
L1 ua_call_hint  → observed        （唯一算 profile 接線證據的級別）
L2 ua_import     → undetermined + import_only_no_call_site
L3 template      → undetermined + template_adjacency_only（可關閉；16G 刪除）

（2026-08-04 選項 B：兩級制。L2 從 detected 改為 undetermined，
  代表它不再進 profile 卡的接線證據；detected 在邊上已無生產者。）
```

並讓下列消費者**同一套邊集合**（不得各算各的）：

1. `ai_system_map.json` / `GraphViewModel` 的 flow 邊  
2. Static execution siblings（`call_graph.json`、`execution_paths.json`、`execution_map.mmd`）  
3. Step 6 profile relationship 證據（含 `context_flow` / rag-grounding＝G5c）

**仍標** `runtime_verified=false`；不得宣稱 runtime proof。

---

## 2. 為什麼不併進 Plan 16 / 16C

| 若硬併 | 後果 |
|--------|------|
| 併進 Plan 16 | Gate-2 只要 structural + fail-closed + parity；綁完整 consumer cutover 會拖垮閘門 |
| 併進 16C | 16C 已夠大（residence + 兩級推導 + model status 欄位）；再加 materialization／profile／FE 會變成不可 review 的巨型 PR |
| 獨立 16D | 可在 16C 有 fixture 產出 `observed` 邊後，單獨驗「誰當 primary」與 profile 翻綠 |

---

## 3. 架構與呼叫鏈（目標態）

```text
ScanSnapshot.scan_result
  ├─ ua_call_hint_* / ua_import_* / ua_symbol_*   ← Plan 16 adapter
  └─ （過渡）既有 TOML facts                     ← parity only；非本檔主題
        │
        ▼
16C  UaEdgeDerivationService
        L1/L2/L3 Edge[]（已帶 status）
        │
        ▼
16D  MapBuildPipeline / SystemMapV2Materialization
        ① 合併邊：L1 > L2 > L3（同 pair 不重複）
        ② FlowDerivationService 僅作 L3 來源（非唯一 primary）
        ③ Normalize 沿用 Edge.status（禁止無條件寫 observed）
        │
        ├─▶ StaticExecutionArtifactService   ← 同一批 edges
        ├─▶ ProfileInferenceService          ← relationship 端點約束（13.8）
        └─▶ GraphProjectionService           ← frontend 只 render
```

錨點（實作前再確認行號）：

- `system_map_v2_materialization_service.py`（今日呼叫 `FlowDerivationService`）
- `system_map_v2_normalize_service.py`（今日硬寫 `status="observed"`；16C Task 5 應已修）
- `flow_derivation_service.py`
- `static_execution_artifact_service.py`（或 Track-C `dynamic/00` 對應服務）
- `profile_finding_assembler.py` / `ProfileInferenceService`

---

## 4. 依賴與閘門（Gate：驗收關卡）

**硬前置（缺一不可）**

| 前置 | 原因 |
|------|------|
| Plan 16 Gate-2 | 沒有穩定 `ua_call_hint_*` 就沒有可優先的 call 邊 |
| 16C Task 3～5 完成 | 需已有 L1/L2 邊與 L3 `undetermined` 標籤 |
| 13.8 Task 1 端點約束 | call 邊量級上升後，無端點約束會假陽性翻綠 |
| 13.7 bridge 字彙 | 元件對不到 52 格則邊推再準也點不亮 |

**建議排程位置（static-trace README）**

```text
Gate-2（Plan 16）──► 16C（邊推導）──► 16D（本檔 cutover）
                              │
                              └──可與 Plan 14 驗證重疊：14 應納入
                                 「call-priority edges + Apply no-UA-rerun」
                                 作為 validation corpus 的一部分
```

- **不阻擋** Plan 14 開跑的最低條件：仍是 Gate-2。  
- **建議**：Plan 14 final report 若宣稱 Lv2 flow，應附 16D 驗收證據；否則報告只能寫「structural UA 已接、flow 仍部分模板」。

---

## 5. Task 清單

### Task 1 — 產出階段（Materialization 物化）：邊的來源改為「多來源合併」，而非只靠模板

**Files（預期）**

- Modify: `src/systograph/core/services/system_map_v2_materialization_service.py`
- Modify: `src/systograph/core/services/map_build_pipeline.py`（若邊合併點在此）
- Test: `tests/unit/core/test_system_map_v2_materialization_*.py` 或新增對應測試
- Test: `tests/integration/` 既有 map-build fixture 路徑

**Steps**

- [ ] 確認 16C 的 `UaEdgeDerivationService`（或等價）在 materialize 路徑被呼叫。
- [ ] Canonical `edges[]` 合併規則固定為 **L1 > L2 > L3**；同 `(from, to, relationship)` 只留最高級。
- [ ] `FlowDerivationService.derive` **不再**是唯一寫入 canonical edges 的來源；它只供應 L3。
- [ ] 當 L1/L2 為空時，仍可輸出 L3——除非 Task 4 flag 關閉 L3。
      （**注意**：L3 不是「骨架」來源，52 格底圖由 Step 7 永遠 emit；理由見
      [`16G`](./16G-retire-template-flow-derivation.md) §3②）
- [ ] 單元測試：只有模板 → 全 `undetermined`；有 call → `observed` 覆蓋同 pair 的模板邊。
- [ ] 單元測試：L2 與 L3 都是 `undetermined` 時，靠 `undetermined_reason` 可區分，
      且合併規則仍正確保留 L2（`import_only_no_call_site`）而非 L3。

### Task 2 — 正規化階段（Normalize）：防止「無條件標成 observed」的舊行為復發

**Files**

- Verify/Modify: `src/systograph/core/services/system_map_v2_normalize_service.py`
- Test: contract / unit 斷言 `observed ⇒ 至少一個 direct evidence`

**Steps**

- [ ] 確認 16C Task 5 的修正仍在；若被 revert 則在本 task 修復。
- [ ] 新增 regression test：模板-only fixture 不得出現無 direct evidence 的 `observed` 邊。
- [ ] 更新 `docs/MODEL-CONTRACT.md` 邊 `status` 三態語意（若 16C 未寫完則本 task 補完）。

### Task 3 — 靜態執行產出檔（siblings 同層檔案）改吃同一批「呼叫優先」的邊

**Files**

- Modify: static execution 相關 service（Track-C / `StaticExecutionArtifactService`）
- Test: integration 對 `call_graph.json` / `execution_paths.json` / `execution_map.mmd`

**Steps**

- [ ] 三個 sibling 的邊集合 ⊆ canonical `edges[]`（或可追溯到同一 evidence 集合）；禁止另算一套「假想路徑」。
- [ ] 路徑優先走 `status=observed`；`undetermined`（L2／L3）可進圖但必須可辨識
      （靠 `undetermined_reason` 區分 `import_only_no_call_site` 與
      `template_adjacency_only`）。**不再有 `detected` 這一層**（選項 B）。
- [ ] 全部 artifact 維持 `runtime_verified=false`。
- [ ] Fixture：`basic_qdrant_ollama_rag`、`pgvector_openai_rag` 各跑一次，記錄 observed 路徑數 vs 基線（16A §2.3）。

### Task 4 — 讓 L3 模板邊可以整個關掉（完整「呼叫優先」開關）

> **這個開關的下游用途（2026-08-04 新增）：** 它是
> [`16G`](./16G-retire-template-flow-derivation.md) 的**量測工具**——16G 要在
> `off` 與 `on` 之間做對照，證明六道門檻全過之後，才把 `FlowDerivationService`
> 整支刪掉（連同這個開關本身）。所以本 task 的測試要留下**可重跑的對照資料**，
> 不只是斷言「off 時沒有 L3 邊」。

**決策預設（可在動工前覆寫）：**

- 預設：**保留 L3**（與 16C §3.5 一致：本階段還沒有 L1/L2 的實測覆蓋數據，
  不宜同步拔掉舊來源）。
  **注意**：舊文寫的「空 repo 仍有參考骨架」理由已於 2026-08-04 作廢——
  骨架來自 Step 7 永遠 emit 的 52 格底圖，不是 L3。
- 增加明確開關（建議 env 或 build option，名稱待實作時定，例如 `SYSTOGRAPH_TEMPLATE_FLOW_EDGES=off`）：
  - `on`（預設）：L3 作為 `undetermined` fallback  
  - `off`：不輸出 L3；僅 L1/L2  

**Steps**

- [ ] 實作開關；預設 `on`。
- [ ] 測試：`off` 時無 `template_adjacency_only` 邊；`on` 時行為同 16C。
- [ ] Plan 14 / demo 腳本註明何時建議 `off`（例如 call 覆蓋已足夠的內部 fixture）。

### Task 5 — Profile / G5c（rag-grounding · `context_flow`）收斂

**Files**

- Verify: `profile_rule_definitions.py`、`profile_finding_assembler.py`
- Test: `tests/integration/test_profile_card_status_baseline.py`（預期在真實 call 證據下可更新快照）
- Docs: readiness / finding 文案若仍寫「模板 flow」則改為「static call-derived / undetermined template」

**Steps**

- [ ] 至少一張依賴 relationship 的卡（優先 `rag-grounding` / `context_flow`）在指定 fixture 上，因 **L1 `observed` 邊** 而從基線狀態前進（`undetermined`→`partial` 或 `partial`→`detected`，以實際證據為準）。
- [ ] 端點約束生效：亂掛同名 relationship 不得翻綠（13.8 回歸）。
- [ ] **記錄「因兩級改制而不再前進」的 fixture**（16C §2.2 的已知取捨）：
      L2 邊不再算接線證據後，只有 import 沒有呼叫點的 fixture 其卡片會停在
      `undetermined`。逐一列出並註明是否屬 16E 的 G1／G2 缺口，
      **避免後續 review 誤判成回歸**。
- [ ] 更新 baseline 快照時，commit／PR 說明必須指名哪一條 call-site evidence。
- [ ] Readiness / profile finding 文案去掉「模板即接線」的誤導語句（若有）。

### Task 6 — 前端冒煙測試（煙測：只驗基本功能沒壞）與可選的視覺微調

**契約原則：** 不新增 GraphViewModel 欄位也可完成 MVP（沿用 `status`）。

**Steps**

- [ ] API mode 載入含 L1/L2/L3 的 build：Flow filter / execution 圖有邊，且無前端 schema 錯誤。
- [ ] （可選 polish）`undetermined` 邊虛線或降透明度；`observed` 實線——**僅 CSS／render，不改契約**。
- [ ] `git diff` 若改 frontend：限於 render 層；禁止前端自組 nodes/edges。

### Task 7 — Apply（重放快照）／Rescan（重新掃描）回歸測試

**Steps**

- [ ] Apply：同 `scan_id` 重放，call-priority edges 與 evidence id **位元級穩定**（16B 規則 C）。
- [ ] Rescan：新 snapshot 可改變邊集合；不得默默沿用舊 call 邊。
- [ ] 不重跑 UA 的 Apply path 不得呼叫 sidecar。

---

## 6. 驗收條件

| # | 條件 | 量測 |
|---|------|------|
| 1 | Canonical edges 的 primary 來源是 16C 推導結果，不是「只 FlowDerivation」 | materialization 單元／整合測試 |
| 2 | 存在至少一條 `observed` 邊，且其 evidence 含 call-site（file+line） | fixture E2E |
| 3 | 無 direct evidence 的邊不得為 `observed` | contract test |
| 4 | Static execution 三 sibling 與 map edges 同源 | artifact diff／測試 |
| 5 | 至少一張 relationship 卡因 call 邊前進 | profile baseline 有意更新 |
| 6 | Apply 不重跑 UA、邊集合穩定 | integration |
| 7 | `runtime_verified=false` 全線維持 | artifact 欄位斷言 |

---

## 7. 不在本計畫範圍

| 項目 | 歸屬 |
|------|------|
| UA sidecar / adapter / parity harness | Plan 16 |
| Residence index、L1/L2/L3 演算法本體 | 16C |
| 模組頂層／class body 建構補抓 | 16C 風險 1 所述獨立 provider |
| 退役 TOML scan providers | Plan 18 |
| AI AssessmentOrchestrator / semantic candidates | Plan 17 deferred |
| 使用者自增 reference catalog node | **不做**（見 custom-node 架構評估） |
| Runtime trace | `deferred/12` / dynamic 後續 |

---

## 8. 待裁定問題（Open Questions；動工前拍板）

- [ ] Q1：Plan 14 final validation 是否 **硬性要求** 16D 完成，還是允許報告標記「flow 仍部分 L3」？
- [ ] Q2：預設環境要不要在 CI fixture 上開 `template_flow_edges=off`，強制暴露 call 覆蓋缺口？
- [ ] Q3：Frontend 虛線 polish 是否納入本 PR，或另開 frontend-only task？

---

## 9. 相關檔案

| 檔案 | 角色 |
|------|------|
| [`16-implement-understand-anything-sidecar-service.md`](./16-implement-understand-anything-sidecar-service.md) | 上游：structural facts |
| [`16A-q3-lv2-call-graph-flow-visualization.md`](./16A-q3-lv2-call-graph-flow-visualization.md) | 決策：Lv2；§3.2 / §6 定義本檔範圍 |
| [`16B-ua-sidecar-io-adapter-reference.md`](./16B-ua-sidecar-io-adapter-reference.md) | Adapter 硬規則 |
| [`16C-component-attribution-and-edge-derivation.md`](./16C-component-attribution-and-edge-derivation.md) | 邊推導本體（本檔的直接上游） |
| [`../s3-validation/14-local-project-import-and-test.md`](../s3-validation/14-local-project-import-and-test.md) | 建議納入 call-priority 驗證證據 |
| `docs/MODEL-CONTRACT.md` | 邊 status／evidence 語意 |
