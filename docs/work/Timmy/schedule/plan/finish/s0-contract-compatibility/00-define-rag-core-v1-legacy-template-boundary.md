# rag-core-v1 Legacy Template Boundary 實作計畫

> **2026-07-06 決策：** 本計畫已重新命名為 legacy template boundary。
> 內容已改為 legacy template boundary。Phase2 target product surface 由 generic v2
> map、profiles、readiness findings 與 evidence artifacts 組成。

## 目標

凍結目前 `rag-core-v1` 作為 `ai-system-map/v1` 的 legacy template input，讓 00A
能 deterministic 地將舊 artifact 轉成 generic `ai-system-map/v2` facts。

本計畫不再把 `rag-core-v1` 定義成 Phase2 target product model、分類器、
frontend summary 或 capability plane 的來源；current runtime 在 Plan 13 cutover 前仍讀寫 v1。

## 背景

Phase2 的 target 主模型已定案為 Capability Map：

```text
deterministic facts
  -> generic components / edges / evidence
  -> fixed capability reference map + repo overlay
  -> profile_signals.json
  -> readiness_report.json findings
  -> GraphViewModel projection
```

因此舊 v1 template 的職責只剩：

- 讀取既有 `ai-system-map/v1` artifact；
- 保留舊 slot、flow、evidence ids 供 00A adapter 映射；
- 提供 characterization tests，避免 migration 遺失 evidence；
- 在 13/15 cutover 前維持 legacy compatibility。

Plan 13 cutover 後，**Phase2 active 新 build 不再以 template 填格產 map。** Target path
改由 Step 3 facts/evidence 經 Step 4 **確定性 bridge rule**
（`component_bridge_registry.py`）materialize generic `ai-system-map/v2` 的
`components[]` / `edges[]`。Current runtime 仍維持 v1 build path。

## 目前 code 狀態

目前 source code 仍直接產生 v1 map（Plan 00 / 13 完成前的過渡現況）：

- `MapBuildService` 載入 `RagTemplateService.load("rag-core-v1")`；
- `SystemMapNormalizeService` 建立 `schema_version="ai-system-map/v1"`、
  `system_type="rag"`；
- `rag-core-v1.json` 在 cutover 前仍被 scanner 載入，但 Plan 00 目標是標記為
  **legacy-only** 並 **凍結** `@1.0.0` 內容（不修改 slots/flows/version）；
- 多個 service、tests、fixtures 仍消費 `RagSystemMap`。

這些不是本計畫要長期保留的產品語意，而是 00A/13/15 之前的 migration input。

## Scope

本計畫只做 legacy characterization 與 migration boundary：

- 鎖定目前 v1 template、fixtures、viewer load、Markdown render 與 validation 行為；
  **2026-07-08 grill-me Q2：** 此「鎖定」= **characterization only**（golden baseline，
  保護 00A/13/15 migration）；**不是** Phase2 target UX surface。Plan 13 cutover 後的
  viewer/report surface 才使用 generic `ai-system-map/v2` + sidecars
  （見 `epic1-phase2.md`、`MODEL-CONTRACT.md`）。
  **freeze 範圍包含** `version`、`slots[]`、`flows[]` 現有內容；v1→v2 遷移只讀不改 template；
- 確認 v1 slots / flows / evidence / endpoints / risks 可被 00A adapter 完整讀取；
- 標記 `rag-core-v1` 為 legacy-only scanner template；
- 移除或避免新增任何 active product copy，避免 frontend 或 report 把它當作能力分類。

## 不在範圍內

- 不建立新的 legacy applicability 判定。
- 不建立 compatibility-derived check、score、summary card 或 report section。
- 不要求把所有 AI system 對齊 v1 slot model。
- 不改 profile inference、Capability Map plane、GraphViewModel 或 runtime trace 語意。

## Implementation Tasks

> 2026-07-09 執行紀錄：
> `docs/work/Timmy/schedule/report/2026-07-09-rag-core-v1-legacy-boundary-REP.md`
> 已完成本計畫的 legacy boundary / standalone adapter boundary。後續 00A 仍需補
> `CanonicalMapLoader`、v2 schema gate 與 compatibility gate；Plan 13 才切 active v2 write path。

### Task 1：鎖定 v1 characterization

- [x] 為 current v1 fixtures 補 schema / runtime validation / viewer load tests。
- [x] 確認 `rag-core-v1` 的 slots、flows、evidence refs、risk hints、endpoints 都可被
      00A adapter 讀取。
- [x] 測試 legacy v1 artifact 可載入，但新產品語意不得依賴 v1 slot completeness。

### Task 2：標記 legacy-only 邊界

- [x] 在 template service / docs / tests 的命名與註解中標示 `rag-core-v1` 是
      legacy template input。
- [x] 新增 regression test，避免新 code 把 v1 slot completeness 寫成 active readiness
      verdict、profile status 或 frontend summary。
- [x] 若保留舊 flow ids，只允許作 migration/debug evidence，不作 active capability graph
      的唯一來源。

### Task 3：提供 00A 使用的 standalone adapter boundary

- [x] Standalone adapter 接收 v1 map 後，輸出 generic components、edges、evidence、endpoints、
      risk hints 與 unmapped/candidate facts。
- [x] adapter 必須 deterministic、read-only、不讀 filesystem、不呼叫 LLM、不寫 artifact。
- [x] adapter 不輸出 compatibility-derived product verdict。

## Acceptance Criteria

- [x] `rag-core-v1` 仍可讀取既有 v1 artifacts。
- [x] Phase2 **target** product contract 已定義為 generic v2 map、profiles、readiness
      findings 與 evidence artifacts；本項不代表 current runtime 已完成 cutover。
- [x] v1-to-v2 adapter 不遺失 evidence ids、locations、endpoints、risks 或 unmapped facts。
- [ ] Plan 13 cutover 後，Capability Map / profile / readiness findings 成為 active
      assessment surface。
- [ ] Plan 13 cutover 後，Frontend 不從 `rag-core-v1` 推論 classification、readiness
      或 canvas state。
- [ ] 00A、13、14、15 的 compatibility / cutover / validation gates 證明可逐步移除 v1
      active output，而不需要先新增 compatibility-derived
      product contract。

> Current runtime truth：`MapBuildService`、`SystemMapNormalizeService`、CLI/API 與 viewer
> 仍使用 `ai-system-map/v1`。上面三個未完成項目不得在 Plan 13 前重新勾選。

## Verification Commands

```bash
.venv/bin/pytest tests/contracts/test_ai_system_map_schema.py \
  tests/unit/core/test_system_map_validation.py \
  tests/unit/core/test_viewer_session_service.py \
  tests/unit/core/test_rag_template_service.py \
  tests/unit/core/test_system_map_v1_to_v2_adapter.py -q
git diff --check
```

## 後續依賴

- 00A：建立 generic v2 model、v1-to-v2 adapter 與 compatibility gate。
- 13：active v2 cutover。
- 14：fixtures 與 real-world validation。
- 15：在 compatibility 通過後退役 v1 active write path。
