# 2026-07-10 00A Code Review P1 Fixes Report

## 目標

依 code review findings 修正 00A compatibility migration 的 Standards P1 /
Spec P1 / Spec P2 問題；維持 active output 為 v1；不 commit/push。

## 實作邏輯

1. **Secret/path boundary**：抽出 `SystemMapSecretBoundary`，v1/v2 validator 共用；
   native v2 拒絕 absolute `project.root_path`、unmasked secrets、非
   project-relative evidence path。
2. **v1→v2 absolute root_path**：adapter 在 canonical 化時把 absolute root_path
   清成 `null` 並加 migration warning，避免 dual-read loader 被 v1 absolute mode
   打爆（userspace 不破）。
3. **Workflow provider**：label 經 `SecretMaskingService.mask_text`；component/edge
   ID 納入 project-relative path；單檔 duplicate node/edge id → ParseIssue。
4. **Edge evidence**：`observed`/`detected` 必須有 evidence；`undetermined` 無
   evidence 時需 `undetermined_reason`。
5. **Candidate 語意**：未確認 extension → `undetermined`/`unknown`；confirmed 才
   `confirmed`/`enabled`；canonical `AiSystemMapV2.candidate_facts` 保留
   `confirmed_by_user`。
6. **Determinism**：slot 依 slot id 排序後再 emit components。
7. **Precondition error**：保留 request 的 `requested_schema_version`。
8. **文件誠實**：00A plan Task 4/5 未完成項改回 `[ ]`；舊 REP 更正假通過宣稱。

## 步驟

1. 寫 TODO；先補失敗測試（TDD red）。
2. 實作 secret boundary、v2 validator、workflow、adapter、model/schema、
   map_build precondition。
3. 修正 plan/REP 勾選衝突。
4. 跑 ruff / mypy / 相關 pytest 至全綠。
5. 寫本 REP。

## 測試

```bash
uv run pytest \
  tests/unit/core/test_system_map_v2_validation.py \
  tests/unit/core/test_workflow_json_provider.py \
  tests/unit/core/test_system_map_v1_to_v2_adapter.py \
  tests/unit/core/test_map_build_schema_selection.py \
  tests/unit/core/test_canonical_map_loader.py \
  tests/unit/core/test_system_map_validation.py \
  tests/unit/core/test_rag_template_service.py \
  tests/contracts/test_ai_system_map_v2_schema.py \
  tests/contracts/test_ai_system_map_schema.py \
  tests/integration/test_ai_system_map_v2_compatibility.py \
  tests/integration/test_map_build_service.py \
  tests/unit/core/test_viewer_session_service.py \
  tests/web tests/cli -q

uv run ruff check <touched>
uv run ruff format --check <touched>
uv run mypy <touched>
```

## 問題與解法

| 問題 | 解法 |
|------|------|
| v2 缺 secret scan | 抽出共用 `SystemMapSecretBoundary` |
| absolute root_path 在 v1 absolute mode 合法 | adapter 清成 null + warning；native v2 仍拒 |
| label 含 secret | `mask_text` 後再寫 evidence.value |
| workflow ID 跨檔碰撞 | `component:workflow:{path}:{id}` |
| edge 無 evidence | validator 強制；undetermined 需 reason |
| E501 / Literal.__args__ | 換行 + `typing.get_args` |
| slot dict 順序不穩 | `sorted(components_by_slot)` |
| candidate 自動 confirmed | `_extension_assessment_state` |
| candidate_facts 在 canonical 消失 | 加 `AiSystemMapV2.candidate_facts` |
| precondition 改回 v1 | 傳入 request schema |
| plan 假勾選 | Task 4 viewer/profile、Task 5 readiness 改回 `[ ]` |

## 結果

### Finding 對照

| # | Finding | 狀態 |
|---|---------|------|
| 1 | native v2 secret/path boundary | **fixed** |
| 2 | WorkflowJsonProvider label masking | **fixed** |
| 3 | Workflow ID namespace + duplicate reject | **fixed** |
| 4 | observed/detected edge evidence required | **fixed** |
| 5 | Ruff/Mypy gate | **fixed** |
| 6 | adapter deterministic slot sort | **fixed** |
| 7 | legacy candidate + candidate_facts | **fixed** |
| 8 | 00A Task 4/5 勾選與 REP 衝突 | **fixed**（文件） |
| 9 | precondition requested_schema_version | **fixed** |

### 驗證

- 相關 pytest：177 passed
- Ruff check + format check（touched）：通過
- Mypy（touched 12 files）：Success
- 正面確認：active output 仍 v1；CLI help 仍註明尚未 Plan 13 cutover
- 無關失敗：無

### 主要改動檔案

- `src/kai_mind/core/services/system_map_secret_boundary.py`（新）
- `system_map_validation_service.py` / `system_map_v2_validation_service.py`
- `system_map_v1_to_v2_adapter.py` / `map_build_service.py`
- `workflow_json_provider.py` / `ai_system_map_v2.py`
- `schemas/ai-system-map.v2.schema.json`
- 相關 unit/contract tests + fixtures 行為
- `00A` plan、舊 REP、本 TODO/REP

## 剩餘風險

- Viewer / profile / readiness 仍未改讀 normalized view（plan 已誠實標 `[ ]`）。
- readiness findings equivalence 仍 deferred。
- Workflow provider 仍未接入預設 scan pipeline。
- `candidate_facts` 現為 canonical 相容擴充；下游 consumer 需知此欄位存在但非
  capability detected 宣告。
