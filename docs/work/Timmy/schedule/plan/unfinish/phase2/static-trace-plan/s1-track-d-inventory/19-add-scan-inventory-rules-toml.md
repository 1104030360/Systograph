# Scan Inventory Rules TOML 實作計畫

Status: planned（ASCII map Step 2 📦 擴充點的 owner plan；2026-07-07 對齊時補建）

**2026-07-08 grill-me Q4：** `max_file_size_bytes` 等**數值 scan 門檻**先留 Python（對齊 Plan 10
threshold 不進 TOML）。TOML 的 `inventory_limit_metadata` 只放 binary/oversize **描述**，不決定
是否掃描。

> **執行者注意：** 逐 task 實作本計畫。步驟使用 checkbox（`- [ ]`）語法以便追蹤。
> 本計畫是 `phase4-scanner-expansion/00-phase2-pipeline-ascii-map.md` Step 2 標示
> 「📦 `scan_inventory_rules.toml` 待建」的唯一 owner。

## 目標

建立 `scan_inventory_rules.toml`，把 Step 2 file inventory 的 include / ignore /
掃描邊界 **metadata** 從 hardcoded Python 常數外部化為 TOML catalog。TOML 只描述
「哪些路徑可掃、哪些預設忽略」；boundary 決策 lifecycle 與 runtime policy overlay
仍由既有 Python services 擁有。

## 架構

```text
scan_inventory_rules.toml（include / ignore patterns、binary/oversize **描述 metadata**；
數值 scan 門檻留 Python — 見 2026-07-08 grill-me Q4）
  -> ScanInventoryRuleLoader（fail-closed schema validation）
  -> FilesystemProvider.build_inventory（套用 default include / ignore）
  -> ScanBoundaryReviewService / InventoryPolicyOverlay（runtime 決策 overlay，不變）
  -> FileInventory（含 skipped audit trail）
```

TOML / Python 邊界（對照 ASCII map「各步擴充點速查」）：

| 放進 TOML | 不放進 TOML |
|---|---|
| include / ignore glob patterns | component 對位、`rule_id` 匹配條件 |
| binary / oversize / generated 的 **描述 metadata**（`inventory_limit_metadata`） | **`max_file_size_bytes` 等數值 scan 門檻**（留 Python；對齊 Plan 10 threshold 不進 TOML） |
| 描述文案（為何預設忽略） | boundary 決策邏輯（blocked / completed 仍在 Python） |
| path / glob / reason / category / message | executable scan fact 條件、profile threshold |

## 依賴

- 無 hard gate；可與 S1 Track（`05`+）並行。
- 建議在 Plan 16 前完成：UA request 的 `files[]` allowlist 來自同一份 KAI approved
  inventory，先固定 Step 2 邊界 metadata 可減少 parity 噪音。
- 不影響 Plan 18 退役範圍；`scan_inventory_rules.toml` 屬 Plan 18 明列的**保留項**。

## Task 1：定義 TOML schema 與 loader

**Files**

- Create: `src/kai_mind/core/rules/scan_inventory_rules.toml`
- Create: `src/kai_mind/core/services/scan_inventory_rule_loader.py`
- Test: `tests/unit/core/test_scan_inventory_rule_loader.py`

**Steps**

- [ ] 定義 TOML schema：`schema_version`、`ignore[]`（pattern + reason）、
  `include_overrides[]`、`inventory_limit_metadata`（binary/oversize **描述**；**不含**
  `max_file_size_bytes` 等會影響是否掃描的數值門檻 — grill-me Q4 留 Python）。
- [ ] Loader 對 unknown fields、缺 `schema_version`、非法 pattern fail closed。
- [ ] Reject executable fields：`rule_id`、`component_type`、`plane_id`、regex 匹配
  scan fact 條件一律拒絕。
- [ ] Loader 為 read-only；不寫檔、不觸碰 target repo。

## Task 2：遷移 hardcoded 預設值並保持行為不變

**Files**

- Modify: `src/kai_mind/core/providers/filesystem_provider.py`
- Test: `tests/unit/core/test_filesystem_provider.py`

**Steps**

- [ ] 以 characterization tests 先固定現有 inventory 行為（含 skipped audit trail）。
- [ ] 將 hardcoded ignore / include 預設值搬進 `scan_inventory_rules.toml`，
  `FilesystemProvider` 改為注入 loader 結果。
- [ ] TOML 缺失或無效時 fail closed，不 fallback 到隱藏預設值。
- [ ] Windows 與 macOS path 分隔符與大小寫行為有明確測試。

## Task 3：與 boundary policy 整合

**Files**

- Modify: `src/kai_mind/core/services/scan_boundary_review_service.py`（只有必要時）
- Test: `tests/unit/core/test_scan_boundary_review_service.py`

**Steps**

- [ ] TOML 提供 default 邊界 metadata；`ScanBoundaryReview` blocked / completed 決策
  流程與 `InventoryPolicyOverlay` runtime 覆寫不變。
- [ ] Policy overlay 與 TOML 衝突時，runtime policy 優先且留審計紀錄。
- [ ] Binary、large、generated、ignored files 的 skip audit trail 全數保留。

## Task 4：文件對照更新

**Files**

- Modify: `docs/work/Timmy/schedule/plan/unfinish/phase4-scanner-expansion/00-phase2-pipeline-ascii-map.md`
- Modify: `docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/README.md`

**Steps**

- [ ] 實作完成後把 ASCII map Step 2 的「待建」標示改為現況。
- [ ] README 計畫一覽同步 gate 狀態。

## Acceptance Criteria

- [ ] `scan_inventory_rules.toml` 是 Step 2 include / ignore metadata 的唯一 source of
  truth；`FilesystemProvider` 不再保留 hardcoded 邊界清單。
- [ ] TOML 不含 component 對位、scan fact 匹配規則、`plane_id` / `reference_node_id`。
- [ ] Invalid / 缺失 TOML fail closed，並有測試。
- [ ] Skip audit trail 與既有 inventory 行為（characterization tests）不變。
- [ ] Windows / macOS path 行為有測試。

## 邊界 / 不做事項

- 不改 boundary decision lifecycle（blocked → proposals / completed → inventory_policy）。
- 不新增 scan fact 匹配規則；Step 3 掃描來源（UA sidecar 與過渡期 providers）不受影響。
- 不把 TOML 變成第三份 scan rule DSL。
- 不寫 target repo；scanner 維持 read-only。
