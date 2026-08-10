# 16G — 模板猜測邊退役（刪除 `FlowDerivationService`）

> 📖 **第一次看？** 先讀 [`README.md`](./README.md)（閱讀順序 + 名詞對照表）。
> **白話一句話：** 等 UA 的真實呼叫邊證明夠用之後，把「照模板猜出來的邊」整段程式碼刪掉，
> 不是關掉、不是留著當備援。
> **Review 重點看 §1（刪什麼／不刪什麼）與 §5（憑什麼說「沒問題」）。**

Status: planned — **blocked until [`16D`](./16D-call-priority-consumer-cutover.md) 完成
且 §5 全部門檻通過**

> **2026-08-10 修訂：** v1 阻擋點作廢（#277 已移除 v1 寫入路徑）、`RELATIONSHIPS` 消費者補列、
> 開關名凍結為 `SYSTOGRAPH_TEMPLATE_FLOW_EDGES`，見
> [`CLARIFICATIONS-2026-08-10.md`](./CLARIFICATIONS-2026-08-10.md) Q8／Q15。

> **執行者注意：** 逐 task 實作本計畫。步驟使用 checkbox（`- [ ]`）語法以便追蹤。
>
> **⚠️ 硬前置（缺一不可）：**
>
> | 前置 | 為什麼是前置 |
> |------|--------------|
> | [`16C`](./16C-component-attribution-and-edge-derivation.md) 全篇 | 沒有 L1/L2 真實邊之前刪掉 L3，圖上會一條邊都不剩 |
> | [`16D`](./16D-call-priority-consumer-cutover.md) Task 1～5 | 下游必須先改成「呼叫優先」，否則消費端還在假設模板邊存在 |
> | `16D` Task 4 的 `off` 開關 | **本計畫的量測工具**——沒有它就無法在刪除前先觀察「沒有 L3 會怎樣」 |
> | §5 六道門檻全過 | 「再確認沒問題」的具體定義；任一項未過即不得開工 |

---

## 1. 「模板猜測」的精確範圍

`rag-core-v1` 模板同時被拿去做**兩件不相干的事**。這份計畫只刪其中一件。
弄混會刪錯東西，所以先講清楚。

### 1.1 要刪的：模板相鄰推導出來的「邊」

```text
rag-core-v1.json
  flows[].slot_order = [document_loader, chunking, embedding_model, vector_store, ...]
        |
        v
FlowDerivationService._derive_edges()
  zip(slot_order, slot_order[1:])        <- 把清單裡「前後相鄰」當成「有連線」
        |
        v
RELATIONSHIPS[(from_slot, to_slot)]      <- flow_derivation_service.py:18，12 條寫死
        |
        v
Edge(relationship="stores_vectors", ...)
```

**這就是「猜」的全部內容**：它從頭到尾沒有讀過目標 repo 的任何一行程式碼。
只要模板清單上 A 排在 B 前面，而 A、B 兩個 slot 都各自有元件，就畫一條邊。

### 1.2 **不**要刪的：模板的 slot 清單

```text
rag-core-v1.json
  slots[]  ->  ComponentDetectionService:127 / :141
               { slot.id: [] for slot in template.slots }
               用來把掃到的元件歸類到 13 個 slot
```

這條路是**元件分類**，不是邊推導，**本計畫不碰**。
`CLAUDE.md` 也明文：「Slot 只指 legacy `rag-core-v1` 模板的 13 個 slot」。

> **交接更正（2026-08-06）：** 本節原記載 slot 退場「屬 13.7 的射程」。
> 經查核，[`13.7`](../../../../finish/s1-v2-cutover/13.7.md) **已完成並移入
> `finish/`**，但它交付的是**能力對照**那半（`capability_type_node_map.toml`、
> 清除 `_LEGACY_SLOT_TO_NODES`），**未涵蓋 Step 4 的 13-slot 偵測 keyspace**。
> 該項目前**無人認領**，且其前提是本資料夾 [`16C`](./16C-component-attribution-and-edge-derivation.md)
> 的 typed 覆蓋先就緒。完整歸屬見
> [`refactor/RAG-CORE-V1-RETIREMENT-INDEX.md`](../../../refactor/RAG-CORE-V1-RETIREMENT-INDEX.md)（滲透點 C1）。

### 1.3 一張表講完

| 對象 | 檔案 | 本計畫 |
|------|------|--------|
| `RELATIONSHIPS` 12 條關係表 | `flow_derivation_service.py:18` | **刪** |
| slot_order 相鄰配對邏輯 | `flow_derivation_service.py._derive_edges` | **刪** |
| `FlowDerivationService` 整支 | 同上 | **刪** |
| L3 分級與 `template_adjacency_only` | 16C Task 5 產物 | **刪**（連同 `undetermined_reason` 的該值） |
| `SYSTOGRAPH_TEMPLATE_FLOW_EDGES` 開關 | 16D Task 4 產物 | **刪**（沒有 L3 就不需要開關） |
| `template.slots` → 元件分類 | `component_detection_service.py:127,141` | **保留**——該退場項**無人認領**（見 [`RAG-CORE-V1-RETIREMENT-INDEX.md`](../../../refactor/RAG-CORE-V1-RETIREMENT-INDEX.md) 滲透點 C1；以 §1.2 的 2026-08-06 更正段為準） |
| `RagTemplate` / `RagTemplateService` / `rag-core-v1.json` | `core/models/template.py` 等 | **保留**（見 §4） |
| L1 / L2 邊推導 | `ua_edge_derivation_service.py`（16C） | **保留**，本計畫的存在理由 |

---

## 2. 現況表面積（2026-08-04 實測，2026-08-10 對 HEAD `52931d6` 校正行號）

| 位置 | 內容 |
|------|------|
| `flow_derivation_service.py:18-31` | `RELATIONSHIPS`，12 個 `(from_slot, to_slot) -> relationship` |
| `flow_derivation_service.py` `derive()` | 逐 `template.flows` 產 `Flow`，內含 `_derive_edges` |
| `system_map_v2_materialization_service.py:89` | `RagTemplateService.load("rag-core-v1")` |
| `system_map_v2_materialization_service.py:126-129` | `flow_derivation_service.derive(...)` → `flows=flows` |
| `tests/unit/core/test_flow_derivation_service.py` | 專屬測試 |
| `tests/integration/test_phase14_endpoints_risk_hints_flows_behaviors.py` | 涵蓋 flows 行為 |

> **2026-08-10 刪列：** 本表原有一列「v1 materialization 路徑同樣呼叫」。該檔已隨 #277
> 的 v1 寫入路徑移除而刪除，v2 是今天唯一的呼叫端（見 §4）。
>
> **另有 4 個 `RELATIONSHIPS` 消費者**（本節原漏列，2026-08-10 親驗補上）：詳見
> Task 3 的 Files 清單——它們不是「產生模板邊」的路徑，而是「引用那 12 個關係名」的路徑，
> 刪表時必須一起改，否則 import 直接斷。

---

## 3. 為什麼刪得掉（三個結構性理由）

**① v2 對外契約根本沒有 `flows`。**
`schemas/ai-system-map.v2.schema.json` 的頂層欄位是
`components / edges / evidence / endpoints / risk_hints / unmapped_components /
candidate_facts / recommended_next_checks`——**沒有 `flows`**。
`Flow` 在 v2 只是記憶體中間物，最後被 normalize 成 `edges`。
刪掉它**不動任何公開 schema**。

**② 畫布不會變空。**
16C §3.5 保留 L3 的理由是「空 repo 仍有參考骨架」。但骨架其實不是 L3 給的——
Step 7 的 `reference_capability` **永遠 emit 52 格**（含 `not_detected` /
`undetermined`），這是 `MODEL-CONTRACT` 的固定行為。
L3 消失後，空 repo 看到的仍是完整的 52 格底圖，只是上面沒有 repo overlay 的邊——
**那才是誠實的畫面**。

**③ 它現在正在說謊，而且是產品層級的謊。**
`system_map_v2_normalize_service.py:183`（`_edges`，:165-186）今天把每一條邊無條件標成 `observed`，
而這些邊全部來自那 12 條寫死的表。16C Task 5 讓它降級成 `undetermined` 是止血；
**本計畫是根治**。留著一個永遠 `undetermined` 又不帶任何 repo 資訊的邊，
對 `CLAUDE.md`「Findings must be evidence-based」沒有任何貢獻，只增加消費端的分支。

---

## 4. v1 阻擋點已由 #277 解除

**本計畫在 v1 側不再有任何動工前決策點。**

原本唯一的阻擋點是：v1 materialization 路徑也呼叫 `FlowDerivationService`，
而 v1 schema 的 `flows` 是 required 欄位——刪掉服務會讓 v1 路徑產不出 `flows`。

該前提在 **#277（HEAD `52931d6`，「v1 寫入路徑移除」）已消失**：
v1 materialization service 連同整條 v1 寫入路徑一併刪除，`ai-system-map.v1` 只剩
**讀取／遷移**用途，公開請求若指名 v1 會得到 `legacy_output_not_selectable`
（見根 `CLAUDE.md`「Authoritative Contract Docs」與 `docs/MODEL-CONTRACT.md`）。

今天 `FlowDerivationService` 的呼叫端**只有 v2 一處**（§2 表），
刪除它不會讓任何仍在服役的寫入路徑少一個 required 欄位。

> **歷史注記（保留決策脈絡，勿據此動工）：** 本節原以
> `system_map_materialization_service.py` 為前提，列出選項 A（v1 固定輸出 `flows: []`
> ＋ `migration_warning`，本計畫預設）與選項 B（等 v1 rollback 整體退役再做本計畫，
> 代價是無限期等待），並要求動工前二選一拍板。
> **兩案於 2026-08-10 一併作廢**——理由不是「選了另一案」，而是**該檔案與該路徑已不存在**，
> 選項所要保護的對象消失了。當時另外驗證過的「v1 `flows` 無 `minItems`，空陣列可過驗證」
> 也隨之失去用途，不必再測。（作廢依據：`CLARIFICATIONS-2026-08-10.md` F2／Q8）

---

## 5. 「確認沒問題」的六道門檻

本計畫的觸發條件不是時間，是證據。**六道全過才開工**，任一項未過即維持 blocked。

以下全部在 `16D` Task 4 的開關切到 `off` 的狀態下量測，並與 `on` 的結果對照。

- [ ] **門檻 1 — 邊沒有消失。**
      對 `tests/fixtures/rag_projects/` 全部 fixture，`off` 模式下 L1+L2 邊數 > 0。
      逐 fixture 記錄兩級邊數量，對照 16C Task 7 建立的基線。

- [ ] **門檻 2 — 關係語彙覆蓋足夠，且必須來自 L1。**
      16A §7.2 列出的 12 張 profile 卡所需 relationship，在 `off` 模式下**都有 L1 邊**
      能提供。
      **⚠️ 這裡不能用 L2 充數**——選項 B 之後 L2 是 `undetermined`，
      `profile_finding_assembler.py:214` 的閘門不收它（16C §2.2）。
      缺哪一個就逐一記錄；缺口多半來自 16E 的 G1／G2，補完前不得刪。

- [ ] **門檻 3 — 沒有卡片退步。**
      15 張 profile 卡在 `off` vs `on` 的五態差異，**只允許 `undetermined` 減少**。
      出現任何 `detected → partial`、`partial → undetermined` 即為退步，必須先查明原因。

- [ ] **門檻 4 — 空 repo 不炸。**
      拿一個只有 config、沒有可辨識程式碼的 fixture（例如 `malformed_config_rag`）跑
      `off` 模式，確認 Step 7 仍 emit 完整 52 格底圖、viewer 正常載入、
      `GraphViewModel` 不含 0 個節點的退化情形。

- [ ] **門檻 5 — Apply / Rescan 不受影響。**
      `off` 模式下跑一次 Apply（同 `scan_id` 新 `build_id`）與一次 Rescan，
      確認 lineage 與 evidence id 穩定性不變。

- [ ] **門檻 6 — 有人簽字。**（2026-08-10 起為**確認性項目**，不再是待決事項）
      ① 確認 #277 已移除 v1 寫入路徑——**已成立**，見 §4；此項只需複查 HEAD 仍無
      v1 materialization service，不需要任何設計抉擇。
      ② owner 簽字啟動刪除：門檻 1～5 的報告已閱、接受刪除不可逆（回滾靠 git，見 §7）。

---

## 6. Task 清單

### Task 1 — 前置量測與門檻報告

- [ ] 建立 `off` vs `on` 的對照量測腳本或 harness（可沿用 16D Task 4 的測試設施）
- [ ] 對全部 `tests/fixtures/rag_projects/` fixture 產出對照表：
      各級邊數量（依 `status` + `undetermined_reason` 分組）、15 張卡五態、
      relationship 覆蓋清單（**須註明每個 relationship 是由 L1 還是 L2 提供**）
- [ ] 把結果寫成報告，逐項對應 §5 六道門檻並標記通過與否
- [ ] **任一門檻未過 → 停在這裡**，把缺口回報成 16C/16D 的後續 task，不進 Task 2

### Task 2 — v1 側確認（原「v1 路徑決策落地」，2026-08-10 縮為確認）

原 task 的四個步驟全部圍繞已被 #277 刪除的 v1 寫入路徑（見 §4），沒有東西可做。
保留本 task 只為留下一道**開工當日的複查**，避免憑舊記憶跳過。

- [ ] 複查 HEAD：`src/systograph/core/services/` 下無 v1 materialization service，
      且 `FlowDerivationService` 的呼叫端只有 v2 一處
- [ ] 若複查發現任何 v1 寫入路徑復活 → **停在這裡**，回頭重開 §4 的決策討論
      （復活代表 #277 的方向被推翻，屬架構層變更，不是本計畫能吸收的）
- [ ] 複查結果（日期＋git rev）寫進 Task 1 的門檻報告，對應 §5 門檻 6 的第 ① 項

### Task 3 — 刪除 `FlowDerivationService`

**Files**

- Delete: `src/systograph/core/services/flow_derivation_service.py`
- Delete: `tests/unit/core/test_flow_derivation_service.py`
- Modify: `src/systograph/core/services/system_map_v2_materialization_service.py`
- Modify: `src/systograph/core/services/map_build_service.py`（DI 參數）
- Modify: `src/systograph/core/services/map_build_pipeline.py`（若有轉傳）

**`RELATIONSHIPS` 的 4 個消費者**（2026-08-10 親驗補列；漏改任一項＝刪除當下 import 斷裂
或文件與程式碼失真）：

- Modify: `src/systograph/core/services/profile_relationship_alias_loader.py`
  ——`:18` `from ...flow_derivation_service import RELATIONSHIPS`、
  `:82` `known_relationships = set(RELATIONSHIPS.values())`（合法關係名的**唯一來源**）、
  `:112` 錯誤訊息 `"must be a FlowDerivationService.RELATIONSHIPS name"`
- Modify: `src/systograph/core/rules/profile_relationship_alias.toml`
  ——`:16` 註釋「values 對 `FlowDerivationService.RELATIONSHIPS` 驗證」
- Modify: `src/systograph/core/models/system_map.py`
  ——`:150`（`Edge` 的「被誰用」註解）、`:165`（`Flow` 的「被誰用」註解）
- Modify: `docs/MODEL-CONTRACT.md`
  ——`:457-460` `profile_relationship_alias.toml` 的規範句
  （`FlowDerivationService.RELATIONSHIPS` 字樣落在 `:459`）

**Steps**

- [ ] 移除 `FlowDerivationService` 的 import、DI 參數與所有呼叫點
- [ ] 移除 v2 materialization 的 `flows` 中間物產生與傳遞
- [ ] `RELATIONSHIPS` 12 條表隨檔案一併刪除，**不得搬到別處保存**
- [ ] **alias 驗證器的合法關係名來源改為 `edge_relationship_rules.toml`**
      （[`16C`](./16C-component-attribution-and-edge-derivation.md) Task 2 新表）——
      `profile_relationship_alias_loader.py` 改讀該表；**錯誤訊息（`:112`）與
      `MODEL-CONTRACT.md` 的敘述同步改指新表**，不得留下指向已刪常數的字串。
      驗證器維持 strict/fail-closed，行為不變、只換來源
- [ ] `mypy src tests` 與 `ruff check src tests` 全綠（DI 參數移除常留下未用 import）

### Task 4 — 清掉 L3 的殘留概念

- [ ] 移除 `undetermined_reason` 的 `template_adjacency_only` 值與其產生點
- [ ] 移除 `SYSTOGRAPH_TEMPLATE_FLOW_EDGES` 開關與相關分支
      （名稱已於 2026-08-10 凍結，見 `CLARIFICATIONS-2026-08-10.md` Q15——不再有別名可能）
- [ ] 刪除後 `undetermined` 的**唯一生產者是 L2**（`import_only_no_call_site`）——
      補一條契約測試釘住這件事，確保 `undetermined` 不會又變成死值
- [ ] `EdgeObservationStatus` enum **不動**（`observed` / `detected` / `undetermined`
      三值保留，`detected` 仍為 reserved-unused，避免舊 artifact 讀不回來）
- [ ] 全 repo 搜尋 `template_adjacency_only` / `模板相鄰` 確認零殘留
- [ ] **全 repo 搜刪要含變數名本身**——除 `template_adjacency_only` 外，另搜
      `SYSTOGRAPH_TEMPLATE_FLOW_EDGES`（含 CI 設定行、`.env` 範例、測試 monkeypatch、
      文件字面）確認零殘留。只搜 `template_adjacency_only` 會漏掉開關側的殘留

### Task 5 — 測試與 fixture 收斂

- [ ] `tests/integration/test_phase14_endpoints_risk_hints_flows_behaviors.py`：
      移除模板 flow 的斷言，改斷言 L1/L2 邊
- [ ] 加一條 regression：**任何邊都必須有 evidence**，不存在無來源的邊
- [ ] 更新受影響的 baseline 快照；PR 說明必須指名哪些卡的狀態變了、為什麼

### Task 6 — 文件同步

- [ ] `docs/MODEL-CONTRACT.md`：移除 `template_adjacency_only` 的說明
      （兩級分類本身在 16C 已定案，此處只清模板殘留）
- [ ] `docs/work/.../phase4-scanner-expansion/00-phase2-pipeline-ascii-map.md`：
      Step 4「4-5 edges / flows FlowDerivationService」改為 UA 邊推導
- [ ] `CLAUDE.md`：`FlowDerivationService` 若出現在 pipeline 描述中，一併移除
- [ ] [`16F`](./16F-new-modules-and-pipeline-delta.md)：AFTER 圖裡
      `template edges linger as undetermined until 16G deletes them` 那一行刪掉
- [ ] `README.md` §5.4：刪掉 L3 那一列與過渡期說明

### Task 7 — 端到端驗收

- [ ] 全部 fixture 重跑，結果與 Task 1 的 `off` 模式量測**逐項一致**
      （若不一致，代表刪除過程動到了不該動的東西）
- [ ] `uv run pytest` 全綠，coverage 不低於 85% 分支門檻
- [ ] Viewer 手動確認：52 格底圖完整、repo overlay 的邊都點得到 evidence

---

## 7. 回滾策略

刪除是不可逆的操作，所以**回滾靠 git，不靠 feature flag**。

- 本計畫必須是**獨立分支、獨立 PR**，不與 16D 混在同一批
- PR 描述附上 Task 1 的門檻報告連結
- 合併後若發現退步，`git revert` 整個 PR 即可還原（因為沒有 schema 變更、
  沒有 state 遷移、沒有 artifact 格式改變）

**不要**為了「保險」留一個關掉的 `FlowDerivationService` ——
那正是本計畫要消除的東西。

---

## 8. 邊界 / 不做事項

- **不**刪 `rag-core-v1.json`、`RagTemplate`、`RagTemplateService`
  （`template.slots` 的元件分類還在用；該退場項**無人認領**，見
  [`refactor/RAG-CORE-V1-RETIREMENT-INDEX.md`](../../../refactor/RAG-CORE-V1-RETIREMENT-INDEX.md)
  C1，以本檔 2026-08-06 更正段（§1.2）為準）
- **不**改任何公開 schema（v2 本來就沒有 `flows`；v1 已無寫入路徑，見 §4）
- **不**動 `CanonicalEdge.status` 的三態定義，只是不再有 L3 來源
- **不**碰前端契約（16A：資料變真即可，欄位不變）
- **不**在本計畫順手做 `rag-core-v1` 的其餘退場項（13.7 已完成的是能力對照那半；
  Step 4 的 13-slot keyspace 另有歸屬，見 §1.2）

---

## 9. 相關文件

| 檔案 | 為什麼要知道 |
|------|--------------|
| [`16C`](./16C-component-attribution-and-edge-derivation.md) | 兩級證據（L1/L2）的定義來源；本計畫刪掉過渡期殘留的 L3 |
| [`16D`](./16D-call-priority-consumer-cutover.md) | Task 4 的開關是本計畫的量測工具 |
| [`16F`](./16F-new-modules-and-pipeline-delta.md) | 新增模組清單；本計畫是它的反向操作（刪除清單） |
| [`../../../../finish/s1-v2-cutover/13.5.md`](../../../../finish/s1-v2-cutover/13.5.md) | v1 rollback 曾被刻意保留的出處；**該保留已由 #277 終結**，§4 的歷史注記由此而來 |
| [`../../../../finish/s1-v2-cutover/13.7.md`](../../../../finish/s1-v2-cutover/13.7.md) | 已完成，交付的是**能力對照**那半；**未**涵蓋 `template.slots` 的 13-slot keyspace（見 §1.2） |
| [`../../../refactor/RAG-CORE-V1-RETIREMENT-INDEX.md`](../../../refactor/RAG-CORE-V1-RETIREMENT-INDEX.md) | `rag-core-v1` 全部滲透點的歸屬總表；`template.slots`（C1）目前無人認領 |
| [`CLARIFICATIONS-2026-08-10.md`](./CLARIFICATIONS-2026-08-10.md) | Q8（§4 作廢＋消費者補列）／Q15（開關名凍結）的裁定出處 |
| `docs/MODEL-CONTRACT.md` | 邊的三態語意正式定義 |
