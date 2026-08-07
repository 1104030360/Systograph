# 2026-07-10 AI System Map V2 Compatibility Migration Report

## 目標

完成 00A：在不切換 active output 的前提下，引入 `ai-system-map/v2`、dual-read
loader、opt-in build、workflow provider 與 compatibility gate。

前置 Plan 00（rag-core-v1 legacy boundary）已存在；本階段不重做已通過的
legacy metadata / compatibility view tests，而是接到完整 canonical contract。

## 實作邏輯

1. **Never break userspace**：`ai_system_map.json` active writer 仍是 v1。
2. **Expand-and-contract**：平行新增 v2 model/schema/loader；cutover 留給 Plan 13。
3. **資料流**：
   - v1 payload → `SystemMapValidationService` → adapter → `AiSystemMapV2`
   - v2 payload → `SystemMapV2ValidationService` → `AiSystemMapV2`
   - schema branching 只允許發生在 `CanonicalMapLoader`
4. Adapter 保留 facts，不產生 release verdict / profiles。
5. Opt-in `system_map_schema_version=v2` 只影響 requested contract 與 warnings，
   不改寫 active artifact。

## 步驟

1. 盤點 Plan 00 已完成項與 00A 缺口；寫 TODO。
2. Task 1：確認 v1 characterization baseline 全綠。
3. Task 2（TDD）：
   - 四象限 v2 fixtures + contract tests
   - canonical models / assessment / reference catalog
   - `schemas/ai-system-map.v2.schema.json`
   - `WorkflowJsonProvider`
4. Task 3：adapter 新增 `adapt_to_canonical()` / `to_canonical()`。
5. Task 4：`CanonicalMapLoader`、MapBuild opt-in、CLI/API schema warnings。
6. Task 5：integration compatibility gate + consumer matrix report。
7. 全套相關 regression、ruff、mypy。

## 主要變更檔案

### Backend models / schema

- `src/systograph/core/models/ai_system_map_v2.py`
- `src/systograph/core/models/map_build.py`
- `schemas/ai-system-map.v2.schema.json`

### Services / providers

- `src/systograph/core/services/system_map_v1_to_v2_adapter.py`
- `src/systograph/core/services/system_map_v2_validation_service.py`
- `src/systograph/core/services/canonical_map_loader.py`
- `src/systograph/core/services/map_build_service.py`
- `src/systograph/core/providers/workflow_json_provider.py`
- `src/systograph/core/services/system_map_normalize_service.py`（文件註記）
- `src/systograph/core/services/system_map_validation_service.py`（文件註記）

### CLI / Web

- `src/systograph/cli/map_command.py`
- `src/systograph/web/schemas.py`
- `src/systograph/web/routes/scan_routes.py`

### Tests / fixtures / docs

- `tests/fixtures/ai_system_map/v2/*.json`
- `tests/contracts/test_ai_system_map_v2_schema.py`
- `tests/unit/core/test_canonical_map_loader.py`
- `tests/unit/core/test_workflow_json_provider.py`
- `tests/unit/core/test_map_build_schema_selection.py`
- `tests/unit/core/test_system_map_v1_to_v2_adapter.py`
- `tests/integration/test_ai_system_map_v2_compatibility.py`
- `docs/work/Timmy/schedule/todo/2026-07-10-ai-system-map-v2-compatibility-TODO.md`
- `docs/work/Timmy/schedule/report/2026-07-10/2026-07-10-ai-system-map-v2-compatibility-gate.md`
- `docs/work/Timmy/schedule/plan/.../00A-...md`（驗收勾選）

## 測試方式

```bash
.venv/bin/pytest \
  tests/unit/core/test_system_map_v1_to_v2_adapter.py \
  tests/unit/core/test_canonical_map_loader.py \
  tests/unit/core/test_workflow_json_provider.py \
  tests/unit/core/test_map_build_schema_selection.py \
  tests/contracts/test_ai_system_map_v2_schema.py \
  tests/integration/test_ai_system_map_v2_compatibility.py \
  tests/contracts/test_ai_system_map_schema.py \
  tests/unit/core/test_system_map_validation.py \
  tests/unit/core/test_viewer_session_service.py \
  tests/unit/core/test_rag_template_service.py \
  tests/integration/test_map_build_service.py -q

.venv/bin/pytest tests/unit tests/contracts tests/integration tests/web tests/cli -q
.venv/bin/ruff check <changed files>
.venv/bin/mypy <changed core/cli files>
```

## 問題與解法

1. **Plan 00 CompatibilityView ≠ canonical AiSystemMapV2**  
   解法：保留 compatibility view 與既有 tests；新增 `adapt_to_canonical()` 轉換，
   避免破壞 Plan 00。

2. **Design sample 使用 `*_layer`，MODEL-CONTRACT 使用 plane ids**  
   解法：runtime contract 以 MODEL-CONTRACT / 00A 為準。

3. **Opt-in v2 可能被誤解成切換 active artifact**  
   解法：`MapBuildResult.active_schema_version` 固定 v1；requested=v2 只加
   migration warning。

4. **Workflow provider 若直接接入 ProjectScanService 會改變預設掃描行為**  
   解法：00A 只新增 provider + tests，不 silent 接入預設 scan aggregation。

## 測試結果

- 00A focused + baseline：108 passed（初版）
- 全套 `tests/unit` + `contracts` + `integration` + `web` + `cli`：561 passed（初版）
- Ruff（變更範圍）：**初版宣稱通過，但 review 發現
  `tests/unit/core/test_system_map_v1_to_v2_adapter.py` E501 未過**
- Mypy（變更 core/cli）：**初版宣稱通過，但 review 發現
  `tests/contracts/test_ai_system_map_v2_schema.py` 使用 `Literal.__args__` 未過**
- 無關失敗：無

> 2026-07-10 review follow-up：上述 Ruff/Mypy「通過」宣稱不實，已改由
> `2026-07-10-00a-review-p1-fixes-REP.md` 重新驗證。不可把本 REP 當 Gate-0 已通過證據。

## 00A 驗收對照

| 驗收項 | 狀態 |
|--------|------|
| v1 readable + test-covered | 通過 |
| v2 四象限 + workflow | 通過 |
| 五態 / 六態 activation / evidence kinds / scope | 通過 |
| 10-plane / 52-node + overlay | 通過 |
| adapter deterministic / no evidence loss | 初版宣稱通過；review 發現 slot order 非 deterministic、candidate 升格問題，見 P1 fixes |
| CanonicalMapLoader 唯一 schema branching owner | 通過 |
| active output 未切 v2 | 通過 |
| compatibility report 供 Plan 13 | 通過 |
| Viewer / profile / readiness 改讀 normalized | **未完成**（仍 v1；plan Task 4 已改回 `[ ]`） |
| readiness findings equivalence | **deferred**（plan Task 5 已改回 `[ ]`） |
| Ruff / Mypy gate | **初版未真正通過**；見 P1 fixes REP |
| Plan 14 實際執行 | 未做（後續計畫；fixtures/gate 已備妥） |

## 剩餘風險

- Viewer / Markdown / Mapping 仍直接吃 v1；Plan 13 前必須改走
  `CanonicalMapLoader`，不可在 routes 各自判斷 version。
- Workflow provider 尚未接入預設 scan pipeline。
- Profile / readiness sidecars 不在 00A 範圍。
- Frontend 無需本次切換；仍消費既有 v1 sample/API。
- Review P1 findings（secret/path、workflow ID/masking、edge evidence、
  candidate_facts、precondition schema）見
  `2026-07-10-00a-review-p1-fixes-REP.md`。
