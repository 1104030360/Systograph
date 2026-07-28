# Retire Systograph Scan TOML Providers After Parity 實作計畫

Status: planned（Plan 14 UA parity gate 通過後執行）

> **執行者注意：** 本計畫只能在 Plan 14 留下通過的 UA parity / fail-closed /
> Apply no-UA-rerun validation report 後執行。逐 task、逐 provider 退役，不得一次刪光。

## 目標

在 UA sidecar 已成為 Step 3 primary 掃描來源且 parity gate 通過後，退役 Systograph scan TOML
providers 的主掃描路徑，避免同一掃描事實長期由兩套系統維護。

## 架構

```text
Before Plan 18
  UA sidecar primary
  Systograph TOML providers parity-only

After Plan 18
  UA sidecar primary
  UaStructuralAdapter owns scan facts / evidence mapping
  retired providers unavailable in main scan path
  retained TOML catalogs only for metadata or inventory policy
```

退役範圍：

- `code_pattern`
- `dependency_manifest`
- `docker_image`
- config patterns 作為主掃描路徑

保留項：

- `risk_hint_rules.toml`
- `recommended_next_check_rules.toml`
- `scan_inventory_rules.toml`
- profile/reference metadata TOML
- `llm_proposal.toml` optional Step 9 provider config

## 依賴

- 依賴 Plan 14 通過並保存 parity report。
- 依賴 Plan 16 UA structural path 已覆蓋主掃描 facts。
- 依賴 Plan 01B bridge registry 已支援 UA `rule_id`。

## Parity Gate 標準

Plan 14 report 必須至少包含：

| 指標 | Gate |
|---|---|
| 覆蓋率 | Tier A fixtures 代表性 facts 必須有 UA 等價輸出；缺口需有 accepted degradation 理由 |
| Evidence 等價性 | UA facts 必須能對回 project-relative path + line/config/json pointer evidence |
| 安全性 | UA output 不含 unmasked secrets、raw source、absolute local paths |
| Fail-closed | invalid schema / Node missing / required batch failed 不進 Step 4 |
| Apply regression | B1→B2 不重跑 UA 或 parity providers，只使用 `ScanSnapshot.scan_result` 重跑 Step 4～7；semantic sidecar 不消費 |
| Rule id migration | Step 4 bridge registry 可處理代表性 UA `rule_id` |

任何 blocker 未解時，本計畫維持 pending。

## Task 1：凍結 parity report 與退役清單

**Files**

- Modify: `docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/14-local-project-import-and-test.md`
- Create: `docs/work/Timmy/schedule/report/ua-parity-retirement-YYYY-MM-DD.md`
- Test: documentation review

**Steps**

- [ ] 收集 Plan 14 parity report 路徑、執行日期、target / fixture 清單。
- [ ] 將每個 Systograph provider rule 分類為 `covered_by_ua`、`accepted_gap`、`needs_ua_adapter_fix`、
  `retain_as_metadata`。
- [ ] 未分類或 `needs_ua_adapter_fix` 不得退役。
- [ ] 記錄回退方案與 owner。

## Task 2：建立 provider usage inventory

**Files**

- Test: `tests/unit/core/test_scan_provider_retirement_boundaries.py`
- Tooling: `rg` inventory（實作時執行）

**Steps**

- [ ] 搜尋 `CodePatternProvider`、`DependencyManifestProvider`、`DockerComposeProvider`、
  config provider 直接被 `ProjectScanService` / `MapBuildService` 使用的位置。
- [ ] 搜尋 tests / fixtures 依賴舊 `rule_id` 的位置。
- [ ] 將 usage 分類為 main scan path、parity harness、legacy fixture、metadata-only、
  migration test。
- [ ] 新增 source guardrail：main scan path 不得 import retired providers。

## Task 3：切換 main scan path

**Files**

- Modify: `src/systograph/core/services/project_scan_service.py`
- Modify: `src/systograph/core/services/ua_structural_adapter.py`
- Test: `tests/unit/core/test_project_scan_service.py`
- Test: `tests/integration/test_map_build_service.py`

**Steps**

- [ ] `ProjectScanService` main path 只呼叫 `UnderstandAnythingAnalysisService` 與
  `UaStructuralAdapter`。
- [ ] 移除或 feature-flag 退役 providers 的 default registration。
- [ ] Parity harness 可保留顯式 dry-run 入口，但不在 production/default scan path 執行。
- [ ] `ProjectScanResult` ordering、dedup、masking 與 warnings 保持 deterministic。

## Task 4：遷移 fixture 與 rule_id expectations

**Files**

- Modify: `tests/fixtures/rag_projects/`
- Modify: `tests/unit/core/test_component_bridge_registry.py`
- Modify: `tests/integration/test_phase4_rag_fixture_behaviors.py`
- Test: focused fixture regressions

**Steps**

- [ ] Phase4 31 fixtures 轉成 UA parity corpus；保留 old/new expected facts 對照。
- [ ] 將 tests 中直接 assert 舊 TOML `rule_id` 的地方改為 UA `rule_id` 或 migration alias。
- [ ] `component_bridge_registry.py` 支援必要 UA `rule_id`。
- [ ] 舊 rule id 只在 parity report、migration fixtures 或 accepted compatibility tests 中出現。

## Task 5：保留 metadata TOML，移除 executable scan ownership

**Files**

- Modify: `src/systograph/core/services/rule_catalog_loader.py`（只有必要時）
- Test: `tests/unit/core/test_rule_catalog_loader.py`
- Test: `tests/unit/core/test_scan_provider_retirement_boundaries.py`

**Steps**

- [ ] 保留 `risk_hint` / `recommended_next_check` metadata loaders。
- [ ] 保留 `scan_inventory_rules.toml` 作 boundary / include-ignore metadata。
- [ ] 不移除 `llm_proposal.toml`；它屬 Step 9 optional provider config。
- [ ] Loader / docs 明確標示 retired scan TOML 不再是主掃描 source of truth。

## Task 6：回退方案

**Files**

- Modify: `docs/MODEL-CONTRACT.md` 或 implementation issue checklist（視實作安排）
- Test: `tests/unit/core/test_project_scan_service.py`

**Steps**

- [ ] 定義暫時恢復 providers 的 feature flag / config，例如 `SYSTOGRAPH_ENABLE_LEGACY_SCAN_PROVIDERS`。
- [ ] 回退預設為 off；啟用時必須在 logs / build warnings 明確標示 legacy scan fallback。
- [ ] 回退不得繞過 UA fail-closed；只有 UA 重大缺陷且經明確風險決策時可使用。
- [ ] 回退路徑有測試，並不更新 Plan 18 retirement report 為完成。

## Task 7：最終退役驗證

**Files**

- Test: `tests/unit/core/test_project_scan_service.py`
- Test: `tests/unit/core/test_component_bridge_registry.py`
- Test: `tests/integration/test_map_build_service.py`
- Test: `tests/contracts/test_secret_snapshot_safety.py`

**Steps**

- [ ] 跑 focused backend tests，確認 UA-only main scan path 通過。
- [ ] 跑 source guardrail，確認 retired providers 不在 default scan path。
- [ ] 跑 secret/path safety tests，確認退役後沒有 masking regression。
- [ ] 跑 Plan 14 Tier A fixture subset，確認 results deterministic。
- [ ] 更新 retirement report，記錄 retained metadata catalogs 與 fallback status。

## Acceptance Criteria

- [ ] Plan 14 parity report 通過且被本計畫引用。
- [ ] Default Step 3 main scan path 不再執行 `code_pattern`、`dependency_manifest`、
  `docker_image`、config patterns providers。
- [ ] UA structural facts 覆蓋代表性 dependency / config / docker / symbol / endpoint facts。
- [ ] Step 4 bridge registry 可處理 UA `rule_id`。
- [ ] Retained TOML catalogs 全部是 metadata / boundary / provider config，沒有主掃描 ownership。
- [ ] Legacy provider fallback 預設關閉，且有明確風險標示與測試。
- [ ] Fixture / rule_id migration 不破壞五態、52 列完整 emit、禁止 numeric confidence 等凍結契約。

## 邊界 / 不做事項

- 不退役 UA sidecar。
- 不刪除 `risk_hint` / `recommended_next_check` / `scan_inventory_rules` / profile metadata TOML。
- 不更動 `ProfileInferenceService` 五態語意。
- 不新增 public artifact 或 frontend 欄位。
- 不把 Plan 18 當成 Plan 14 的替代；沒有 Plan 14 parity report 不得執行。
