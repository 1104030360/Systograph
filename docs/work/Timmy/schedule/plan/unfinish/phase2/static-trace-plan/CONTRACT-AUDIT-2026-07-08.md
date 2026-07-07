# Static Trace Plan Contract Audit（2026-07-08）

> Read-only 查核 + `grill-me` Q1～Q5 拍板摘要。權威 contract 仍以
> `docs/design/epic1-phase2.md`、`docs/MODEL-CONTRACT.md`、`docs/API-GUIDE.md` 為準。

## 判定摘要

**不是 25 項 plan 全都仍是真問題。** 2026-07-07～08 已有一批 contract 文件修正（Apply
4-1/4-2、Step 4 禁 proposal、10+1 artifact 計數、Gate-1/Gate-4 消歧）。以下區分
**仍是真缺口**、**已修或只剩小修**、**判定措辭需修正**。

---

## 仍是真問題（P0/P1 方向成立）

### Plan 01 — reject/skip durable audit 與現行 code 衝突

- **Plan / contract 要求：** `rejected` / `skip_for_now` 建 durable `ManualMapping`（含
  `audit_metadata`），Web route 回傳 `manual_mapping`；見 Plan 01 Task 8、`MODEL-CONTRACT`。
- **現行 code：** `MappingProposalDecisionResult` 對 `REJECTED` / `SKIPPED` 仍要求
  `manual_mapping: null`；`MappingProposalService.decide(REJECT|SKIP_FOR_NOW)` 只更新
  proposal status。
- **Evidence：** `mapping.py` validator、`mapping_proposal_service.py` reject/skip 分支。
- **狀態：** **OPEN — 需改 code + tests**，Plan 01 Task 8 仍為 unchecked。

### Plan 02 — 驗收需硬性 52 格覆蓋

- **方向成立，但描述應調整：** Plan 02 已寫 52 格、Mapping Completeness、6-1 owner；缺口不是
  「完全沒寫」，而是驗收必須硬性要求：
  - `reference_capability_assessments[]` **exactly 52 rows**
  - `mapping_completeness.denominator == 52`
  - schema / fixture / contract tests 覆蓋 denominator=52
- **狀態：** **OPEN — plan 驗收條款已補強（見 Plan 02 §驗收標準）**

### Plan 14 — E2E hard gate 尚未收斂

- **現況：** direct import targets = **8**（不是 10）；artifact 驗收前段列 5～6 個，後段才補
  P0 execution artifacts。
- **缺口：** 缺少單一 E2E hard gate：**10 public sibling artifacts + 1 ephemeral
  `ViewerLoadResult.graph_view_model`**（對齊 `MODEL-CONTRACT` §3 / §9.1）。
- **狀態：** **OPEN — Plan 14 已補 E2E gate 章節**

---

## 已修或只剩小修

| 主題 | 狀態 | 權威位置 |
|------|------|----------|
| Apply 入口統一（跳 Step 3/UA → 4-1 → 4-2 → Step 4～7） | ✅ 已修 | `API-GUIDE.md`、`MODEL-CONTRACT.md`、Plan 03A 後段 |
| Step 4 禁止 proposal | ✅ 已修 | `MODEL-CONTRACT.md` §Step 4、static README |
| 10 public siblings + 1 ephemeral `GraphViewModel` | ✅ 已修 | `MODEL-CONTRACT.md` §3、static README |
| Gate-1 / Gate-4 消歧 | ✅ 已修 | static README、Plan 15 |
| Plan 03A 舊語「component detection replay」 | 🔧 小修 | 全文改寫為 4-1 + 4-2（同檔後段已正確） |
| Plan 11 `primary_axis` 缺 `allowed_fields` | 🔧 小修 | loader 範例補 `primary_axis` / `secondary_axes` |
| Plan 19 `limits` vs threshold 命名 | 🔧 小修 | 改 `inventory_limit_metadata`；數值門檻留 Python |

---

## 判定措辭修正

- **static README「缺 Step 8 / Rescan」：** Step 8 viewer load、Rescan vs Apply 邊界已
  **delegated** 到 `MODEL-CONTRACT.md` / `API-GUIDE.md` / `epic1-phase2.md` §6.1；README
  只保留 gate 與 pipeline ownership 摘要。
- **Plan 03A「component detection replay」：** 不是方向錯誤，應統一為 **4-1 bridge replay +
  4-2 confirmed mappings overlay**。
- **Plan 19 limits：** 允許 file size / binary **描述 metadata**；**禁止**把可執行 scan
  fact / profile threshold 放進 TOML；數值門檻（如 `max_file_size_bytes`）留 Python。

---

## Grill-me 拍板（2026-07-08）

| # | 題目 | 決策 |
|---|------|------|
| **Q1** | Gate-1 是否包含 initial scan 必跑 Step 9 | **否。** B1 initial build = Step 1→7 publish + Step 8 viewer；Step 9 是 review/apply path。**Gate-1 驗收**須**另驗** Step 9 decision + Apply B1→B2 |
| **Q2** | Plan 00 viewer/Markdown 鎖定 | **A：characterization only** — golden baseline 保護 00A/13/15；active surface = v2 + sidecars |
| **Q3** | Apply 是否每次重跑 4-1 再 4-2 | **是。** 精準用語：**replay 4-1 → overlay 4-2** → Step 4 normalize/validate → Step 5～7；epic ASCII「4-2 replay」易誤跳 4-1 |
| **Q4** | `max_file_size_bytes` 能否放 TOML | **否（先留 Python）。** TOML 放 path/glob/reason/category/message；Plan 19 修歧義 |
| **Q5** | Mapping Completeness 由誰算 | **Step 6-1 `ProfileInferenceService`**；Step 7 `GraphProjectionService` 只投影，不重算 |

---

## 驗證限制

本 audit 以 **read-only code inspection + 文件對齊**為主，未修改 production code。PR preflight
已執行：

```bash
.venv/bin/pytest tests/unit/core/test_mapping_proposal_service.py \
  tests/web/test_mapping_proposal_routes.py -q
```

現行測試通過，並確認 reject / skip 目前不建立 `ManualMapping`。Plan 01 code gap 的未來修復仍需
另增 unit / integration regression tests。
