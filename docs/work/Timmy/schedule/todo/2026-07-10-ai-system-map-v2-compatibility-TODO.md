# 2026-07-10 AI System Map V2 Compatibility Migration TODO

## 目標

完整實作
`docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/s0-contract-compatibility/00A-introduce-ai-system-map-v2-compatibility-migration.md`。

前置 Plan 00（rag-core-v1 legacy boundary）已完成 standalone adapter 與 legacy
metadata；本階段補齊 generic v2 contract、dual-read loader、opt-in build、workflow
provider 與 compatibility gate。**不切換 active output。**

## 現況盤點（開始前）

| 項目 | 狀態 | 說明 |
|------|------|------|
| Plan 00 legacy boundary | 已完成 | `rag_template_service` + adapter + tests |
| `AiSystemMapV2CompatibilityView` | 已有 | Plan 00 compatibility view，非完整 canonical |
| `SystemMapV1ToV2Adapter` | 已有 | 輸出 compatibility view；需接到 canonical / loader |
| `schemas/ai-system-map.v2.schema.json` | 缺口 | 尚未建立 |
| `CanonicalComponent` / `AiSystemMapV2` | 缺口 | 需依 MODEL-CONTRACT + 00A 補齊 |
| Assessment / activation / evidence kind | 缺口 | 五態、六態、三種 evidence kind |
| 10-plane / 52-node reference catalog | 缺口 | 需可獨立 validate |
| `CanonicalMapLoader` | 缺口 | dual-read 唯一 owner |
| Opt-in v2 build | 缺口 | 預設仍 v1 |
| `workflow_json_provider` | 缺口 | 僅 validated object shape |
| Compatibility gate / report | 缺口 | 需產出 report |

## 實作邏輯

1. **Never break userspace**：預設 map build / API / viewer 仍讀寫 v1。
2. **Expand-and-contract**：先新增平行 v2 contract 與 dual-read；不 silent cutover。
3. **資料流**：
   `v1 artifact → validate → adapter → AiSystemMapV2 normalized view`
   或 `v2 artifact → validate → AiSystemMapV2`。
4. **Adapter 責任**：保留 facts；不產生 release verdict / profile / readiness。
5. **CanonicalMapLoader**：唯一 schema branching owner；routes 不各自判斷 version。
6. **Reference map ≠ repo components**：catalog 與 overlay 分開 validate。
7. **TDD**：每個行為先寫失敗測試，再寫最小實作。

## 步驟

### Phase A — v1 characterization baseline（Task 1）

1. 確認既有 v1 contract / validation / viewer tests 全綠。
2. 必要時補 semantic snapshot（components / flows / evidence / risks / endpoints），
   不做整份 JSON 字串 snapshot。

### Phase B — Generic v2 model + schema（Task 2）

1. 先寫 contract tests：grounded RAG、non-grounded LLM app、tool agent、workflow。
2. 新增 canonical models：`CanonicalComponent`、`CanonicalEdge`、
   `CanonicalEvidenceLocation`、`GroundingReadiness`、`AiSystemMapV2`。
3. 新增 assessment / activation / evidence-kind / conflict / scope models。
4. 新增 10-plane / 52-node reference catalog + overlay validation。
5. `extra="forbid"`；遞迴拒絕 `confidence`。
6. 產生 `schemas/ai-system-map.v2.schema.json`。
7. 新增 `WorkflowJsonProvider`（validated node/edge shape + JSON pointer evidence）。

### Phase C — Adapter → canonical（Task 3）

1. 保留既有 compatibility view 行為與 Plan 00 tests。
2. Adapter 提供 normalized `AiSystemMapV2`（或 loader 內轉換），不遺失 evidence /
   endpoints / risks / unmapped / legacy extension facts。
3. 不輸出 product verdict。

### Phase D — Dual-read loader + opt-in build（Task 4）

1. 實作 `CanonicalMapLoader`。
2. `MapBuildRequest` 增加 explicit opt-in schema selection；預設 v1。
3. CLI/API 可回報 active schema version 與 migration warnings（最小必要整合）。
4. Viewer / routes 不各自判斷 schema version（透過 loader）。

### Phase E — Compatibility gate（Task 5）

1. Evidence id / location 可解析。
2. 四象限 fixtures 不被強迫填 RAG slots。
3. Windows/macOS path fixtures。
4. 產出 compatibility report。
5. 相關 unit / integration / contract tests 全綠。

## 測試策略

- Unit：`tests/unit/core/test_ai_system_map_v2*.py`、adapter、loader、workflow provider
- Contract：`tests/contracts/test_ai_system_map_v2_schema.py`
- Integration：`tests/integration/` dual-read / opt-in build
- Regression：既有 v1 schema / validation / viewer / Plan 00 adapter tests
- 驗證命令：
  ```bash
  uv run pytest tests/unit/core/test_system_map_v1_to_v2_adapter.py \
    tests/unit/core/test_rag_template_service.py \
    tests/contracts/test_ai_system_map_schema.py \
    tests/contracts/test_ai_system_map_v2_schema.py \
    tests/unit/core/test_canonical_map_loader.py \
    tests/unit/core/test_workflow_json_provider.py \
    tests/integration/test_ai_system_map_v2_compatibility.py -q
  ```

## 驗收條件（對照 00A Acceptance Criteria）

- [x] v1 remains readable and test-covered
- [x] v2 schema 可表示四象限 AI systems 與 workflow artifacts
- [x] v2 assessment 支援五態、六態 activation、field-specific conflict、三種 evidence kind、scope
- [x] 固定 10-plane / 52-node reference map 與 per-repo overlay 可分開 validate
- [x] v1-to-v2 adapter deterministic、read-only、無 evidence loss
- [x] Dual-read loader 是 schema branching 的唯一 owner
- [x] 未通過 compatibility gate 前，active output 不切換至 v2
- [x] Compatibility report 已產生，供 Plan 13 依賴
- [x] 相關測試全綠；無關失敗另記
- [ ] Plan 14 實際驗證（後續計畫）

## 風險

- 既有 `AiSystemMapV2CompatibilityView` 與 target `AiSystemMapV2` 欄位不完全相同；
  需明確轉換邊界，避免破壞 Plan 00 tests。
- Frontend sample 的 layer 命名（`*_layer`）與 MODEL-CONTRACT plane ids 不一致；
  以 MODEL-CONTRACT / 00A 為準。
- Opt-in build 不得 silent 改寫預設 artifact。
