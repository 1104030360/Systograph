# Stackable Profile Inference 實作計畫

> **2026-07-11 backend execution status：** normalized-v2 deterministic inference、52
> assessments、15 profiles、five-state validation、related refs、Mapping Completeness 與
> sidecar/API serialization 已完成並測試。Frontend Zod／degraded UI 已依使用者要求還原，
> 對應 frontend-only checkboxes 保持未完成；後端證據見
> `docs/work/Timmy/schedule/report/2026-07-11-phase2-s1-pipeline-core-REP.md`。

> **執行者注意：** 逐 task 實作本計畫。步驟以 checkbox（`- [ ]`）語法追蹤進度。

**目標：** 從 generic canonical AI system map 產生 registry-driven、可疊加、
evidence-backed capability overlays；不把 repo 分成單一 RAG 類型，也不 mutate
`ai-system-map/v1` 或 v2 canonical facts。

**架構：** `ProfileInferenceService` 消費 00A loader 提供的 normalized v2 map、confirmed
non-baseline capability candidates 與 optional validated candidates（預設為空；
Plan 17 deferred），作為
**橋接 2（Step 6）** 把 repo components / unmapped refs / candidate inputs 對位到
10 planes / 52 reference nodes，再 emit `profile-signals/v1`。AI semantic candidate
flow 屬於 deferred 的 `AssessmentOrchestrator`（Plan 17），不是 `ProfileInferenceService`
內部流程；candidate
不得創造 canonical component、edge、evidence 或單獨把 status 提升為 `detected`。
Sidecar 缺失時 viewer degraded load，canonical graph 仍可用。

**Tech Stack：** Python 3.11、Pydantic v2、FastAPI schemas、pytest、Ruff、mypy。

---

## 2026-07-05 Confirmed Assessment and Ownership Override

本節取代本文後續任何三態 status、`not_detected` 不需 coverage gate、或由本計畫實作
artifact writer / graph projection / frontend renderer 的舊內容。完整決策見
[`../../capability-map-assessment-decision-summary.md`](../../capability-map-assessment-decision-summary.md)。

本計畫唯一職責是 capability assessment/profile inference：

- 從 validated v2 repo facts、evidence、coverage 與 confirmed non-baseline candidates 產生
  assessment result。
- 五態為 `detected`、`partial`、`undetermined`、`not_detected`、`conflicted`。
- `activation` 為 `enabled`、`disabled`、`conditional`、`unknown`、
  `conflicted`、`not_applicable`。只有 catalog 宣告 node 本質上沒有 activation 語意時
  才可 `not_applicable`。
- Evidence 分成 `direct`、`indirect`、`explicit_negative`；`detected` 必須有 direct
  evidence，只有 indirect evidence 一律 `partial`，多個 convergent indirect signals 也
  不得升級。只有明確 disabled/bypassed/forbidden 等才是 explicit negative；absence 不是。
- Assessment 綁定 `build_id`、`scan_id`、environment；`scan_id` 識別 immutable scan
  snapshot，conflict 必須 field-specific。
- `not_detected` 必須通過 capability-specific coverage gate，否則為 `undetermined`。
- Mapping Completeness weights 為 detected=1、not_detected=1（coverage gate 通過）、
  partial=0.5、undetermined/conflicted=0；denominator 是全部固定 reference nodes，
  activation/not_applicable 不排除 node。它是 derived metric，不是 confidence。

Ownership 明確分離：

- **Plan 02**：models、validation、Python deterministic assessment rules、同 build 的 result。
- **Plan 03**：`profile_signals.json` path/writer、artifact publish、`MapBuildResult` 與
  same-build lifecycle 的唯一 owner。
- **Plan 06**：fixed reference map + repo overlay、`GraphViewModel`、profile/reference
  projection、最小 frontend consumption contract 的唯一 owner。
- 本文舊 Task 3.5 writer、Task 4 projection 與 Task 5.5 frontend snippets只保留為歷史背景，
  **不得實作**；執行時依 Plan 03/06 取代。

## 2026-07-06 Bridge 2 Ownership

本計畫是 **Step 6 橋接 2** 的 executable owner。Step 4 只產生 repo component /
unmapped / candidate input；Step 5 只建立 lookup。從本計畫開始，才允許把 repo facts
解讀成 reference node assessment：

```text
validated ai_system_map.json
  + SystemMapIndex
  + confirmed non-baseline capability candidates
  + capability_reference_map.toml（10 planes / 52 nodes metadata）
  + profile_registry.toml（profile label / axis metadata，Plan 11）
  -> ProfileInferenceService.infer(...)
       reference_node_assessments 五態
       profile findings / capability overlays
       Mapping Completeness
       related component / unmapped / candidate / risk refs
```

規則放置原則：

- `capability_reference_map.toml` 只提供 plane/node id、label、順序與
  `activation_applicable` 等 metadata。
- `profile_registry.toml` 只提供 profile 顯示 metadata、axis、default wording。
- Python `ProfileInferenceService` 才能判斷 repo evidence 是否支撐某個
  `reference_node_id`、五態、activation、coverage gate、conflict 與 completeness。
- Frontend 與 `GraphProjectionService` 都不得重算本計畫的 assessment；Plan 06 只消費
  本計畫的結果來畫 fixed reference map + repo overlay。

## 2026-07-07 UA 整合對齊

同日修訂（ASCII map 決策 #2 / #3 / #5）：Step 6 **無 AI 編排**，Plan 17
`AssessmentOrchestrator` deferred，UA semantic sidecar 是 reserved nullable slot，Phase2
active path 不產生、不消費。
`ProfileInferenceService` 的輸入契約保留 optional `validated_candidates` 接縫、
**預設為空**；Plan 14 前不會有任何 AI candidate 進入本計畫。本計畫是五態與 52 格
assessment 的唯一 Python owner；未來重啟 Plan 17 時，semantic-only candidate 不能把
reference node 升為 `detected`，最多支撐 `partial` / `undetermined`，且 `detected`
仍必須有 direct evidence。

## 執行摘要

### 目標

從 validated generic system map 與 confirmed non-baseline capability candidates，
產生 evidence-backed、可堆疊且非 canonical 的 registry-driven capability overlays。

### 背景

AI-Mind 的差異化不是讓使用者組裝 flow，而是掃描既有 AI system repo 後回答：
grounding、agent control、retrieval、tools、memory、workflow、evaluation 等能力實際
有哪些，證據在哪裡，哪些仍無法確定。

### 目前 code 狀態

backend 尚無 profile models、inference service、sidecar writer 或 profile-aware viewer payload；frontend 有未接線的 profile 型別雛形，但與實際 backend mapping/viewer contract 不一致。

### 相關檔案

- `src/systograph/core/models/profile_signal.py`（新增）
- `src/systograph/core/services/profile_inference_service.py`（新增）
- `src/systograph/core/services/profile_signal_validation_service.py`（新增）
- `src/systograph/core/services/map_build_service.py`
- `src/systograph/core/services/viewer_session_service.py`
- `frontend/src/types.ts`
- `frontend/src/services/viewerApi.ts`
- `frontend/src/hooks/useViewerPayload.ts`

### 實作步驟

依序建立 typed models、cross-reference validation、deterministic inference、coverage gate、
activation/conflict/scope contract，再把同一 validated result 交給 Plan 03 artifact lifecycle
與 Plan 06 projection；最後以 fixtures 與 contract tests 驗證。

### 驗收標準

每次成功 build 依 active profile registry 產生完整 assessment checklist；五態、activation、
evidence kinds、coverage gate、field-specific conflict 與 scope 都通過 validation；canonical
map 不被修改。Plan 03 負責將同一 result 寫入 `profile_signals.json`。

**2026-07-08 hard gate（52 格覆蓋）：**

- [ ] `profile_signals.json` 的 `reference_capability_assessments` 陣列 **必須 exactly 52 rows**
      （對齊 `capability_reference_map.toml` 固定 reference nodes）。
- [ ] `mapping_completeness.denominator` **必須等於 52**；numerator / status counts 與五態 weights
      一致。
- [ ] schema validation、fixtures 與 contract tests 覆蓋 denominator=52；不得只驗「有輸出」而不驗
      row count。
- [ ] Mapping Completeness 唯一定案 owner = 本計畫 Step 6-1 `ProfileInferenceService`；Plan 06
      Step 7 只 surface / project，不重算。

### 風險與注意事項

不得用 dependency 名稱、檔名或一般字串命中直接宣告 `detected`。規則應優先消費 AST/Regex/config parser 產生的 typed facts、confirmed decisions 與可追溯 flow evidence。

## 最新狀態

- 2026-07-05 assessment contract 決策：本條覆蓋下方所有舊三態紀錄。Active output
  使用五態 assessment + 獨立 activation state，並維持禁止任意數字 `confidence`。

- 2026-06-26 使用者決策：選 **B**，表示 Phase 2 MVP 正式納入 stackable profile inference。
- 2026-06-26 後續決策：選 **C**，表示 Phase 2B 寫入 durable `profile_signals.json` sidecar，且 API/viewer payload 暴露同一份已驗證 profile 結果。
- 2026-06-30 viewer load 修正決策：profile sidecar 不是 viewer 必要條件。一般 viewer/API 載入既有 `ai_system_map.json` 時，若 sibling `profile_signals.json` 缺失或 invalid，仍必須載入 base graph，並回傳 profile enrichment unavailable 的 warning / degraded state；只有 map build validation、CI contract validation 或明確 strict mode 才可因 profile sidecar invalid fail closed。Viewer load 不得在 load-time 做 transient profile inference。
- 2026-06-26 profile coverage 後續決策：選 **C**，表示 Phase 2B MVP 必須區分設計文件 capability overlay matrix 中的每一列。這是單層 profile finding coverage，不是完整 runtime topology 重建。
- 2026-06-26 profile output 後續決策：選 **B**，表示 `profile_signals.json` 永遠 emit 所有 MVP profile 列；無 evidence 的列使用 `not_detected`。
- 2026-06-26 `not_detected` recommendation 後續決策：選 **A**，表示 `not_detected` 列維持 `recommended_next_checks=[]`。
- 2026-06-29 三態紀錄已被 2026-07-05 決策取代。新 contract 使用
  `detected / partial / undetermined / not_detected / conflicted`；`activation` 獨立。
- 2026-06-29 classification flow 修正決策：新流程不再把非 baseline 能力先產品化為 `extension`。掃描後先確認「這是不是 grounding component」；若使用者確認不是，該 component 進入 non-baseline capability candidate input，由 profile inference 判斷 capability overlay finding 或維持 `undetermined`。
- 2026-06-29 durable decision 修正決策：使用者確認「這段 evidence 不應映射為 legacy v1 slot」的 durable source of truth 應由 manual mapping / confirmation lifecycle 擁有；`profile_signals.json.capability_candidate_components` 只是 map build 後的 materialized sidecar output，不是唯一持久化來源，也不寫回 canonical `ai_system_map.json`。
- 2026-06-29 dependency 修正決策：本計畫依賴 `01-rework-manual-mapping-capability-candidates.md`。`ProfileInferenceService` 消費 `ComponentDetectionResult.capability_candidate_components` / `profile_signals.json.capability_candidate_components`，但不自行建立 manual mapping decision lifecycle。
- 2026-06-29 legacy compatibility 決策：既有 `ai-system-map/v1.extensions` 欄位先保留為舊 artifact / 舊 mapping repository 相容層，但 Phase2 新流程、profile inference 與 frontend UI 不應要求使用者先建立 extension。
- 2026-06-26 detected threshold 後續決策：選 **B**，表示 high-specificity code/config evidence 可為 `detected`；僅 dependency-only、naming-only 與 unmapped candidate evidence 不可。
- 2026-06-29 related references 修正決策：profile findings 可帶 `related_unmapped_component_ids`、`related_capability_candidate_component_ids`、`related_risk_hint_ids`，指向同一份已驗證輸入。`related_extension_ids` 僅能作 legacy compatibility，不作為新 frontend contract 必要欄位。
- 2026-07-05 `not_detected` 修正：必須有 completed coverage gate。它可以帶
  coverage/evidence refs 與 explicit negative evidence；weak/ambiguous signal 或 coverage
  不足仍為 `undetermined`。
- 2026-06-26 graph presentation 後續決策：profile findings 可 render 為視覺上 distinct 的 profile attachment nodes；query trace 可 render 為明確 opt-in 的 transient replay overlay。兩者皆不得建立 permanent graph nodes/edges，或 mutate `ai_system_map.json` / `profile_signals.json`。
- 2026-06-26 projection ownership 後續決策：profile attachment nodes 由 backend `GraphViewModel` projection 產生。Frontend render 已 emit 的 contract，不得從 `profile_inference_result` 獨立 infer graph nodes。
- 2026-06-26 graph node contract 後續決策：profile attachment nodes 在 `GraphViewModel.nodes[]` 內 emit，含明確 semantic fields，如 `semantic_kind="profile_attachment"`、`profile_id`、`anchor_node_ids`；不得僅 overload 既有 `type` 作為 renderer semantic。
- 2026-06-26 anchor contract 後續決策：每個 profile attachment node 必須含 `primary_anchor_node_id` 與 `anchor_node_ids`。若 backend projection 無法識別 reliable primary anchor，profile 仍留在 details/reporting，但不 emit graph attachment node。
- 2026-06-26 anchor selection 後續決策：backend projection 以 deterministic priority 選 `primary_anchor_node_id`：direct evidence component node 優先，其次 profile-specific slot priority，若無 reliable anchor 則不 emit graph attachment node。
- 2026-07-05 graph emission 決策取代舊 detected-only attachment 規則：Plan 06 投影固定
  reference nodes 並以五態/activation 標示 repo overlay。Repo component 與 reference node
  必須是不同 semantic kinds；本計畫不 emit graph nodes。
- 2026-06-26 connector contract 後續決策：backend 不在 `GraphViewModel.edges[]` 建立 profile attachment 到 anchor 的 synthetic edge。
- 2026-06-29 trace boundary 修正決策：Profile graph 只表達 static map / profile projection。Runtime Query Trace 另由 `12-add-runtime-component-trace-contract.md` 定義為本輪 0～14 的 deferred boundary，必須依 target runtime 回報的 `trace_steps` / `component_ref` highlight graph，不得用 static profile inference 假裝知道 query 實際經過哪些元件。
- 2026-06-26 profile filter contract 已移交 Plan 06；本計畫只提供 assessment data。
- 2026-06-26 label contract 後續決策：backend graph projection 透過 `GraphNodeModel.label` 提供 compact canvas label；完整 profile metadata 保留在 details payload。
- 2026-06-29 legacy profile catalog 決策：曾採一組 RAG-family variants；此決策已由 2026-07-03 registry-driven generic capability contract 取代，只保留作 migration alias 依據。
- 2026-06-30 profile 層級修正決策：profile contract 維持單層，參考 n8n node 心智模型；frontend 只看到 profile row / profile attachment node，不需要 render nested profile node 或第二層分類。`reranking` 與 `modular-composition` 仍可保留為單層 profile，但 detected 條件必須比一般 wording 更窄，避免成為 fallback bucket。
- 2026-07-01 product-scope 修正決策：Phase 2 profile inference 是 release-readiness gate 的 pre-runtime enrichment，不是完整任意 repo runtime topology reconstruction。Static map/profile projection 回答「哪些 components、grounding dimensions、capabilities、risks 看起來存在，證據是什麼」；若要回答「這次 query 實際跑過哪些 component」，只能依 `12-add-runtime-component-trace-contract.md` 的 opt-in trace，而不得從 static profile 假裝推論 runtime path。
- 2026-07-01 runtime / query trace scope 決策：runtime / query trace 不屬於 `02`、`03`、`06` 或 `14` 的 blocker；`12-add-runtime-component-trace-contract.md` 在 0～14 內只保留 contract boundary。
- 2026-07-02 0～14 scope correction：本計畫不使用 EPIC2 / EPIC3 工作包作為差異化依據。`profile` 在本文一律代表 capability overlay finding，不是互斥 RAG variant classifier。`capability_candidate_components` 若保留為欄位名稱，只是 implementation naming，產品語意為 non-baseline capability candidate。
- 2026-07-01 open decision queue：未定產品/排序問題保存於 `docs/work/Timmy/design/EPIC1/Phase2/epic1-phase2/epic1-phase2-open-decisions.md`。Worker 實作本計畫前應先檢查該 queue；若 queue 與本 plan 衝突，以已確認的 `MODEL-CONTRACT.md` contract 為準，未確認的項目不得當成已決策 scope。
- Frontend runtime trace replay 由 deferred Plan 12 處理。Profile artifact lifecycle 由 Plan 03，
  projection 與最小 frontend consumption contract 由 Plan 06；Plan 02 不修改 frontend。
- 安全邊界：Phase 2 MVP 維持 **local-only deterministic**。LLM providers、third-party adapters 與 runtime trace imports 仍為明確 opt-in 後續項目。
- 既有相關工作：
  - `../phase4-scanner-expansion/37-add-scan-profile-catalog.md` 為 metadata catalog 計畫，不是 profile inference。
  - `../phase4-scanner-expansion/31-expand-reranking-fixtures.md` 提供 profile inference 可消費的 fixture expansion。
  - `ViewerSessionService` 已投影 standard slots、legacy extensions、unmapped components 與 risk hints，且不將 graph 資料寫回 `ai_system_map.json`。

## MVP Capability Overlay Registry

Phase 2B 不再固定「12 種 RAG」。`ProfileInferenceService` 必須依 package-bundled
registry emit 完整 checklist；每一列都是可疊加能力，不是互斥分類。

MVP registry：

- `rag-grounding`
- `agentic-control`
- `tool-calling`
- `memory`
- `workflow-orchestration`
- `hybrid-retrieval`
- `reranking`
- `corrective-retrieval`
- `self-reflection`
- `graph-retrieval`
- `hierarchical-retrieval`
- `contextual-retrieval`
- `multimodal-grounding`
- `modular-composition`
- `multi-query-retrieval`

Evaluation/observability、deployment、cache、permission filter 先保留為 generic
components/readiness findings；citation / source mapping 由
`readiness_report.json` 的 `source_traceability` finding 表達。只有形成穩定且可獨立
驗證的能力 bundle 時才加入 profile registry。Frontend 不得硬編碼 profile 數量或順序。

Legacy ids（例如 `rag-grounding`、`agentic-control`、`reranking`、`modular-composition`、
`multi-query-retrieval`）只存在於 migration alias/fixture。新 output 應使用上列 capability
ids；legacy alias 不能同時再 emit 一列，避免重複計數。

### Single-Level Profile Rules

Profile contract 必須維持一層：

```text
profile_id -> status -> evidence/reason/details
```

不要新增這種正式 contract：

```text
profile_id -> nested signal groups -> nested status
```

原因：前端的 canvas 心智模型要像 n8n node，一個 profile finding 對應一種 profile attachment / detail row。細節可放在 evidence reason、`uncertainty`、`recommended_next_checks` 或 detail panel 文案，不要讓 frontend 需要處理第二層分類。

### Feature-Axis Profile Metadata

Capability profiles 不是單一 taxonomy。Phase 2B 採用「單層 profile finding +
feature-axis metadata」：

```text
ProfileFinding(profile_id, status, primary_axis, secondary_axes, implementation_depth_level, evidence...)
```

`primary_axis` / `secondary_axes` 只用來說明 capability overlay 主要改動哪個面向，不新增 nested profile node、nested signal array 或第二層 frontend classification。

Default axis catalog：

| `profile_id` | `primary_axis` |
|---|---|
| `rag-grounding` | `grounding` |
| `agentic-control` | `agent_control` |
| `tool-calling` | `tool_use` |
| `memory` | `memory` |
| `workflow-orchestration` | `workflow_orchestration` |
| `hybrid-retrieval` | `retrieval_strategy` |
| `reranking` | `retrieval_strategy` |
| `corrective-retrieval` | `agent_control` |
| `self-reflection` | `agent_control` |
| `graph-retrieval` | `knowledge_structure` |
| `hierarchical-retrieval` | `knowledge_structure` |
| `contextual-retrieval` | `context_enrichment` |
| `multimodal-grounding` | `data_modality` |
| `modular-composition` | `design_paradigm` |
| `multi-query-retrieval` | `retrieval_strategy` |

Implementation depth 是 per-profile observed implementation scope，不是 confidence：

| Level | Meaning |
|---:|---|
| 0 | 沒有觀察到該 profile 實作 |
| 1 | 只有概念、README claim、命名、prompt、dependency 或 config-only signal |
| 2 | 有模組 / artifact 雛形，但沒有證明進入 query / answer end-to-end path |
| 3 | 該 profile 的完整 pipeline 已進入 query / answer path |
| 4 | Level 3 加上 eval、benchmark、tests、fallback、observability 或 production hardening |

Status、activation 與 depth 分工：

- `detected` 通常為 level 3 或 4，且必須通過 capability-specific detected gate。
- `partial` 通常為 level 1～3；已有直接 evidence，但 required signals/path coverage 不完整。
- `undetermined` 通常為 level 0～2；只有 indirect/ambiguous signal，或 scanner coverage 不足。
- `not_detected` 通常為 level 0，且必須通過 capability-specific coverage gate；可以帶
  coverage refs 或 explicit-negative evidence。
- `conflicted` 保留已觀察 depth，但必須指出發生衝突的欄位及互斥 evidence ids。
- `activation` 獨立描述 enabled/disabled/conditional/unknown/conflicted/not_applicable；
  status 不自動決定 activation。
- 永不新增任意數字 `confidence`；evidence kind、strength、depth、coverage 與 conflicts
  解釋判斷。
- Graph/reference-node projection 與 frontend legend 由 Plan 06 擁有。

`reranking` 防止變成垃圾桶的規則：

- 不得作為 fallback bucket；「不知道屬於哪個 profile」應該是 `undetermined`，不是 `reranking`。
- 只有在 normalized v2 components / edges / evidence 顯示明確 retrieval enhancement path
  時才可 `detected`；legacy v1 slot evidence 可作 migration context，但不是 profile
  detection 的唯一 truth。
- 若 evidence 更精準符合 `hybrid-retrieval`、`corrective-retrieval`、`agentic-control`、`graph-retrieval`、`hierarchical-retrieval`、`contextual-retrieval`、`multimodal-grounding` 或 `multi-query-retrieval`，應優先歸到那些 profile；`reranking` 只承接沒有更精準 profile 的 retrieval enhancement。
- 若 repo 已 detected `hybrid-retrieval`、`contextual-retrieval`、`graph-retrieval` 或其他更精準 profile，不要再把同一份 evidence roll up 成 `reranking=detected`。若 report 需要說明「具備 advanced features」，放在 summary wording，不放進 profile row。
- 合格 examples：reranker / cross-encoder rerank、query rewrite、query decomposition、retrieval compression、metadata-aware retrieval optimization。
- 不合格 examples：只有 LangChain / LlamaIndex dependency、只有 generic retriever class、只有 `advanced` / `optimized` 命名。

`modular-composition` 保留為單層 profile，但 detected threshold 必須很高：

- 不得因為使用 LangChain / LlamaIndex / class-based code 就 `detected`。
- 必須看到 RAG pipeline component 可替換的結構，例如 provider registry、plugin catalog、config-driven retriever/vector store/LLM selection、或同一 slot 存在多個可切換 implementation。
- 若只看到單一路徑 pipeline，即使程式碼拆成多個 class，也不構成 `modular-composition=detected`。
- 若 evidence 顯示「可能有模組化」但沒有可替換 contract，狀態應為 `undetermined`。

輸出為完整 checklist，不是 sparse list。`ProfileInferenceService` 必須永遠 emit 上述所有列。
每列都要帶 build/snapshot/environment scope、activation、evidence-kind breakdown 與 coverage
結果。`not_detected` 只在 coverage gate completed 時合法；否則 emit `undetermined`。
`ProfileInferenceService` 不得呼叫 `ManualMappingService`；confirmed baseline mappings 已由
map build/component detection pipeline 更早套用。

Detection threshold：

- High-specificity direct code/config/wiring evidence 可產生 `detected`。
- 已反映在 validated detected slot 或 confirmed non-baseline capability candidate 的 confirmed decisions，仍需滿足 profile-specific path / depth 條件才可產生 `detected`。
- 多個獨立 deterministic signals 若全部仍是 indirect evidence，只能產生 `partial`，
  不得因 convergent 而升級成 `detected`。
- 僅 dependency-only、naming-only、raw unmapped candidate、capability candidate、risk hint
  或 recommended check evidence 本身不足以成為 `detected`；若它們是可回溯的 indirect
  positive evidence，status 一律為 `partial`。
- 只有 module / artifact 雛形但沒有 query / answer path direct evidence 時，status 應為
  `partial` 且 `implementation_depth_level=2`，不是 detected。
- 例如 repo 宣稱 GraphRAG，且有 entity extraction / graph storage，但 retrieval 仍只走普通 vector search：`graph-retrieval` 應為 `undetermined`、depth 2；必須看到 graph traversal、community / relation artifacts 或 graph-derived retrieval 進入 answer path，才可 detected。
- Agentic RAG 不得只靠 tool calling 判定。至少需要看到 LLM/controller-driven routing、retrieve tool selection、planner/agent loop、state graph / conditional edge、tool result 回到 LLM，或同等的 multi-step control-flow evidence。
- `reranking` 不得吃掉更精準 profile 的 evidence；只有 retrieval enhancement evidence 無法更精準歸類時，才可產生 `reranking=detected`。
- `modular-composition` 必須有可替換 component / registry / config-driven module evidence；一般 framework usage 或 class decomposition 不足。
- Related ids 可指向 weak 或 suspicious evidence 供 navigation，但 related ids alone 不足以使 profile 為 `detected`。
- `not_detected` 列不得帶 weak related ids；那些 related refs 應掛在 `undetermined` profile。
- Plan 02 不建立 `GraphViewModel` nodes/edges/filters。Plan 06 消費本計畫的 validated
  assessment result，投影 fixed reference nodes 與 repo components。
- Query trace replay 不由本計畫定義。Runtime trace 必須依 `12-add-runtime-component-trace-contract.md` 的 observed `component_ref` / `trace_steps` 進行 transient highlight；不得建立 trace edges 或 persist trace-derived profile evidence。`12` 在 0～14 內只作 deferred contract boundary，不阻擋本計畫。
- Filter、legend、graph details 與 frontend consumption contract 由 Plan 06 擁有；API 仍不提供
  profile-level confirmation 或 mutation action。
- Backend projection 只提供 anchor semantics，不提供 pixel coordinates，也不把 attachment 放進 canonical topology。
- Frontend 顯示與互動 contract 由 Plan 06 與對應 Hardy plan 負責；Plan 03 只提供 artifact
  lifecycle，Plan 02 不修改 frontend。Meeting-Sync 文件不得取代可執行 plan。

## 檔案結構

新增：

- `src/systograph/core/models/profile_signal.py`
  - `profile-signals/v1` 的 Pydantic models。
  - 禁止 `confidence`、raw source snippets、absolute paths 與 unknown fields。
  - 從 `src/systograph/core/models/capability_candidate.py` 匯入 `CapabilityCandidateComponent`；不要在 `profile_signal.py` 內重新定義 capability candidate model。
- `src/systograph/core/services/profile_signal_validation_service.py`
  - Profile evidence ids 與 artifact safety 的 cross-reference validator。
- `src/systograph/core/services/profile_inference_service.py`
  - 從 validated map facts、non-baseline capability candidate components、legacy extensions、unmapped components、risk hints 與 evidence metadata 的 deterministic inference rules。
- `tests/unit/core/test_profile_signal_models.py`
- `tests/unit/core/test_profile_signal_validation_service.py`
- `tests/unit/core/test_profile_inference_service.py`
- Viewer/projection tests 由 Plan 06 擁有，不在本計畫新增。

修改：

- `src/systograph/core/services/map_build_service.py`
  - Infer profiles 一次並 validate；把 result 交給 Plan 03 lifecycle，不自行寫 artifact 或投影 graph。
- `docs/work/Timmy/design/EPIC1/Phase2/epic1-phase2/epic1-phase2-design.md`
  - 若實作改變 planned contract，保持 decision record 一致。

Frontend 檔案、Zod contract、renderer、layout、detail panel、filter 與 trace replay 工作不屬
本計畫；由 Plan 06 與對應 Meeting-Sync/Hardy plan 擁有：

- `docs/work/Meeting-Sync/meeting_sync_2026_07_07/frontend-profile-attachment-ui.md`

本計畫不修改：

- `src/systograph/core/models/system_map.py`，除非另批准 schema migration。
- `src/systograph/core/templates/rag-core-v1.json`，除非另批准 template contract migration。
- Runtime trace persistence behavior；另由 `12-add-runtime-component-trace-contract.md` 作 deferred boundary 設計。
- External provider 或 adapter configuration。

## Task 1：定義 `profile-signals/v1` Models

**檔案：**
- Create：`src/systograph/core/models/profile_signal.py`
- Test：`tests/unit/core/test_profile_signal_models.py`

- [ ] **Step 1：先寫 model tests**

建立 `tests/unit/core/test_profile_signal_models.py`：

```python
from __future__ import annotations

import pytest
from pydantic import ValidationError

from systograph.core.models.profile_signal import (
    ProfileFinding,
    ProfileInferenceResult,
)


def test_profile_inference_result_accepts_minimal_detected_profile() -> None:
    result = ProfileInferenceResult(
        source_schema_version="ai-system-map/v2",
        profiles=[
            ProfileFinding(
                profile_id="reranking",
                label="Reranking",
                primary_axis="retrieval_strategy",
                secondary_axes=[],
                implementation_depth_level=3,
                implementation_depth_reason=(
                    "reranker is wired into the retrieval-to-answer path"
                ),
                status="detected",
                evidence_ids=["evidence:code_pattern:reranker"],
                evidence_strength="static_single_signal",
                uncertainty=None,
                related_unmapped_component_ids=[],
                related_capability_candidate_component_ids=[
                    "capability-candidate:config-yaml:reranker"
                ],
                related_risk_hint_ids=[],
                recommended_next_checks=["review reranker code path"],
            )
        ],
    )

    assert result.schema_version == "profile-signals/v1"
    assert result.profiles[0].profile_id == "reranking"
    assert result.profiles[0].status == "detected"
    assert result.profiles[0].primary_axis == "retrieval_strategy"
    assert result.profiles[0].implementation_depth_level == 3


def test_profile_model_rejects_confidence_field() -> None:
    with pytest.raises(ValidationError, match="extra_forbidden"):
        ProfileFinding(
            profile_id="hybrid-retrieval",
            label="Hybrid RAG",
            primary_axis="retrieval_strategy",
            secondary_axes=[],
            implementation_depth_level=3,
            status="detected",
            evidence_ids=["evidence:dependency:rank-bm25"],
            evidence_strength="static_single_signal",
            uncertainty="dependency evidence only",
            recommended_next_checks=[],
            confidence=0.8,
        )


def test_profile_model_rejects_empty_direct_evidence_for_detected() -> None:
    with pytest.raises(ValidationError, match="detected profiles require direct evidence"):
        ProfileFinding(
            profile_id="rag-grounding",
            label="RAG Grounding",
            primary_axis="grounding",
            secondary_axes=[],
            implementation_depth_level=3,
            status="detected",
            evidence_ids=["evidence:dependency:rag-package"],
            indirect_evidence_ids=["evidence:dependency:rag-package"],
            direct_evidence_ids=[],
            evidence_strength="static_multiple_signals",
            uncertainty=None,
            recommended_next_checks=[],
        )


def test_profile_model_accepts_not_detected_after_coverage_gate() -> None:
    finding = ProfileFinding(
        profile_id="graph-retrieval",
        label="GraphRAG",
        primary_axis="knowledge_structure",
        secondary_axes=[],
        implementation_depth_level=0,
        status="not_detected",
        evidence_ids=[],
        evidence_strength="not_detected",
        uncertainty="no deterministic evidence found",
        not_detected_coverage_gate_passed=True,
        recommended_next_checks=[],
    )

    assert finding.status == "not_detected"
    assert finding.evidence_ids == []


def test_profile_model_rejects_not_detected_without_coverage_gate() -> None:
    with pytest.raises(ValidationError, match="completed coverage gate"):
        ProfileFinding(
            profile_id="reranking",
            label="Reranking",
            primary_axis="retrieval_strategy",
            secondary_axes=[],
            implementation_depth_level=0,
            status="not_detected",
            evidence_ids=[],
            evidence_strength="not_detected",
            uncertainty="scan coverage incomplete",
            recommended_next_checks=[],
        )


def test_profile_model_requires_field_refs_for_conflicted() -> None:
    with pytest.raises(ValidationError, match="field-specific conflicts"):
        ProfileFinding(
            profile_id="reranking",
            label="Reranking",
            primary_axis="retrieval_strategy",
            secondary_axes=[],
            implementation_depth_level=2,
            status="conflicted",
            evidence_ids=["evidence:enabled", "evidence:disabled"],
            evidence_strength="static_multiple_signals",
            uncertainty="activation evidence conflicts",
            recommended_next_checks=[],
        )


def test_profile_model_rejects_raw_snippet_like_fields() -> None:
    with pytest.raises(ValidationError, match="extra_forbidden"):
        ProfileFinding(
            profile_id="agentic-control",
            label="Agentic Control",
            primary_axis="agent_control",
            secondary_axes=[],
            implementation_depth_level=3,
            status="detected",
            evidence_ids=["evidence:code_pattern:tool"],
            evidence_strength="static_single_signal",
            uncertainty="tool decorator exists; runtime use not confirmed",
            recommended_next_checks=["confirm tool permission boundary"],
            raw_source="agent.run(tool='delete_file')",
        )
```

- [ ] **Step 2：執行 red test**

執行：

```bash
.venv/bin/pytest tests/unit/core/test_profile_signal_models.py -v
```

預期：FAIL，`ModuleNotFoundError: No module named 'systograph.core.models.profile_signal'`。

- [ ] **Step 3：新增 model 實作**

建立 `src/systograph/core/models/profile_signal.py`：

```python
"""Non-canonical profile signal models for Phase 2 inference."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from systograph.core.models.capability_candidate import CapabilityCandidateComponent

ProfileSignalSchemaVersion = Literal["profile-signals/v1"]
SourceSchemaVersion = Literal["ai-system-map/v1", "ai-system-map/v2"]
ProfileStatus = Literal[
    "detected",
    "partial",
    "undetermined",
    "not_detected",
    "conflicted",
]
ActivationState = Literal[
    "enabled",
    "disabled",
    "conditional",
    "unknown",
    "conflicted",
    "not_applicable",
]
EvidenceKind = Literal[
    "direct",
    "indirect",
    "explicit_negative",
]
EvidenceStrength = Literal[
    "static_multiple_signals",
    "static_single_signal",
    "weak_or_ambiguous_signal",
    "not_detected",
]
ProfileAxis = Literal[
    "grounding",
    "agent_control",
    "tool_use",
    "memory",
    "workflow_orchestration",
    "retrieval_strategy",
    "knowledge_structure",
    "context_enrichment",
    "data_modality",
    "design_paradigm",
]
ImplementationDepthLevel = Literal[0, 1, 2, 3, 4]


class ProfileSignalModel(BaseModel):
    """Base model that forbids silent profile contract drift."""

    model_config = ConfigDict(extra="forbid")


class ProfileFinding(ProfileSignalModel):
    profile_id: str
    label: str
    description: str | None = None
    status: ProfileStatus
    activation: ActivationState = "unknown"
    primary_axis: ProfileAxis
    secondary_axes: list[ProfileAxis] = Field(default_factory=list)
    implementation_depth_level: ImplementationDepthLevel
    implementation_depth_reason: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    negative_evidence_ids: list[str] = Field(default_factory=list)
    direct_evidence_ids: list[str] = Field(default_factory=list)
    indirect_evidence_ids: list[str] = Field(default_factory=list)
    explicit_negative_evidence_ids: list[str] = Field(default_factory=list)
    conflict_fields: list[str] = Field(default_factory=list)
    conflict_evidence_ids: list[str] = Field(default_factory=list)
    detected_signals: list[str] = Field(default_factory=list)
    missing_signals: list[str] = Field(default_factory=list)
    coverage_detected: int = 0
    coverage_total: int = 0
    not_detected_coverage_gate_passed: bool = False
    evidence_strength: EvidenceStrength
    uncertainty: str | None = None
    related_unmapped_component_ids: list[str] = Field(default_factory=list)
    related_capability_candidate_component_ids: list[str] = Field(
        default_factory=list
    )
    related_risk_hint_ids: list[str] = Field(default_factory=list)
    recommended_next_checks: list[str] = Field(default_factory=list)
    source: Literal["deterministic_static"] = "deterministic_static"

    @model_validator(mode="after")
    def require_evidence_for_detected_status(self) -> "ProfileFinding":
        if self.status == "detected":
            if not self.direct_evidence_ids:
                raise ValueError("detected profiles require direct evidence")
            if self.implementation_depth_level < 3:
                raise ValueError(
                    "detected profiles require implementation depth >= 3"
                )
        if self.coverage_total < self.coverage_detected:
            raise ValueError("coverage_detected cannot exceed coverage_total")
        if self.status == "not_detected" and not self.not_detected_coverage_gate_passed:
            raise ValueError("not_detected profiles require completed coverage gate")
        if self.status == "conflicted" and not self.conflict_fields:
            raise ValueError("conflicted profiles require field-specific conflicts")
        if self.status == "not_detected" and self.implementation_depth_level != 0:
            raise ValueError(
                "not_detected profiles require implementation depth 0"
            )
        if (
            self.status == "undetermined"
            and self.implementation_depth_level == 0
            and self.not_detected_coverage_gate_passed
        ):
            raise ValueError(
                "undetermined depth 0 must describe incomplete scan coverage"
            )
        if self.status == "undetermined" and not (
            self.evidence_ids
            or self.related_unmapped_component_ids
            or self.related_capability_candidate_component_ids
            or self.related_risk_hint_ids
        ):
            raise ValueError(
                "undetermined profiles require evidence or related references"
            )
        return self


class ProfileInferenceResult(ProfileSignalModel):
    schema_version: ProfileSignalSchemaVersion = "profile-signals/v1"
    source_schema_version: SourceSchemaVersion
    build_id: str
    scan_id: str
    environment_id: str
    capability_candidate_components: list[CapabilityCandidateComponent] = Field(
        default_factory=list
    )
    profiles: list[ProfileFinding] = Field(default_factory=list)
```

`coverage_*`、detected/missing signals、typed evidence ids 與 field-specific conflict refs
用來解釋一級 `partial` / `conflicted` 狀態。所有欄位只引用 deterministic facts；不得
放入任意數字 `confidence`。

- [ ] **Step 4：執行 model tests**

執行：

```bash
.venv/bin/pytest tests/unit/core/test_profile_signal_models.py -v
```

預期：PASS。

## Task 2：新增 Profile Validation

**檔案：**
- Create：`src/systograph/core/services/profile_signal_validation_service.py`
- Test：`tests/unit/core/test_profile_signal_validation_service.py`

- [ ] **Step 1：撰寫 validation tests**

建立 `tests/unit/core/test_profile_signal_validation_service.py`：

```python
from __future__ import annotations

import json
from pathlib import Path

import pytest

from systograph.core.models.profile_signal import (
    ProfileFinding,
    ProfileInferenceResult,
)
from systograph.core.models.system_map import UnmappedComponent
from systograph.core.services.profile_signal_validation_service import (
    ProfileSignalValidationError,
    ProfileSignalValidationService,
)
from systograph.core.services.system_map_validation_service import (
    SystemMapValidationService,
)


FIXTURE_PATH = Path("tests/fixtures/ai_system_map/valid_minimal.v1.json")


def load_map():
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return SystemMapValidationService().validate(data)


def test_validation_accepts_existing_evidence_ids() -> None:
    system_map = load_map()
    evidence_id = system_map.evidence[0].id
    result = ProfileInferenceResult(
        source_schema_version="ai-system-map/v2",
        profiles=[
            ProfileFinding(
                profile_id="rag-grounding",
                label="RAG Grounding",
                primary_axis="grounding",
                secondary_axes=[],
                implementation_depth_level=3,
                status="detected",
                evidence_ids=[evidence_id],
                evidence_strength="static_single_signal",
                uncertainty=None,
                recommended_next_checks=[],
            )
        ],
    )

    validated = ProfileSignalValidationService().validate(
        result,
        system_map=system_map,
    )

    assert validated.profiles[0].evidence_ids == [evidence_id]


def test_validation_rejects_unknown_evidence_ids() -> None:
    system_map = load_map()
    result = ProfileInferenceResult(
        source_schema_version="ai-system-map/v2",
        profiles=[
            ProfileFinding(
                profile_id="rag-grounding",
                label="RAG Grounding",
                primary_axis="grounding",
                secondary_axes=[],
                implementation_depth_level=3,
                status="detected",
                evidence_ids=["evidence:missing"],
                evidence_strength="static_single_signal",
                uncertainty=None,
                recommended_next_checks=[],
            )
        ],
    )

    with pytest.raises(ProfileSignalValidationError, match="unknown evidence"):
        ProfileSignalValidationService().validate(result, system_map=system_map)


def test_validation_rejects_unknown_related_ids() -> None:
    system_map = load_map()
    result = ProfileInferenceResult(
        source_schema_version="ai-system-map/v2",
        profiles=[
            ProfileFinding(
                profile_id="reranking",
                label="Reranking",
                primary_axis="retrieval_strategy",
                secondary_axes=[],
                implementation_depth_level=1,
                status="undetermined",
                evidence_ids=[],
                evidence_strength="weak_or_ambiguous_signal",
                uncertainty="weak signal only",
                related_unmapped_component_ids=["unmapped:missing"],
                recommended_next_checks=[],
            )
        ],
    )

    with pytest.raises(ProfileSignalValidationError, match="unknown related"):
        ProfileSignalValidationService().validate(result, system_map=system_map)


def test_validation_accepts_undetermined_with_known_related_ids() -> None:
    system_map = load_map().model_copy(deep=True)
    system_map.unmapped_components.append(
        UnmappedComponent(
            id="unmapped:src-agent-py:tool-registry",
            source_file="src/agent.py",
            observed_kind="agent_tool_signal",
            status="needs_confirmation",
            reason="Detected agent tool signal but runtime use is unconfirmed.",
            evidence_ids=[system_map.evidence[0].id],
            suggested_actions=["confirm_mapping"],
        )
    )
    result = ProfileInferenceResult(
        source_schema_version="ai-system-map/v2",
        profiles=[
            ProfileFinding(
                profile_id="agentic-control",
                label="Agentic Control",
                primary_axis="agent_control",
                secondary_axes=[],
                implementation_depth_level=1,
                implementation_depth_reason=(
                    "tool-registry signal exists, but no controller loop is proven"
                ),
                status="undetermined",
                evidence_ids=[],
                evidence_strength="weak_or_ambiguous_signal",
                uncertainty=(
                    "Confirmed as non-baseline evidence, but no known "
                    "profile rule can classify it yet."
                ),
                related_unmapped_component_ids=[
                    "unmapped:src-agent-py:tool-registry"
                ],
                recommended_next_checks=[],
            )
        ],
    )

    validated = ProfileSignalValidationService().validate(
        result,
        system_map=system_map,
    )

    assert validated.profiles[0].related_unmapped_component_ids


def test_validation_rejects_local_absolute_paths_in_profile_text() -> None:
    system_map = load_map()
    evidence_id = system_map.evidence[0].id
    result = ProfileInferenceResult(
        source_schema_version="ai-system-map/v2",
        profiles=[
            ProfileFinding(
                profile_id="agentic-control",
                label="Agentic Control",
                primary_axis="agent_control",
                secondary_axes=[],
                implementation_depth_level=3,
                status="detected",
                evidence_ids=[evidence_id],
                evidence_strength="static_single_signal",
                uncertainty="review /Users/example/private/app.py",
                recommended_next_checks=[],
            )
        ],
    )

    with pytest.raises(ProfileSignalValidationError, match="absolute path"):
        ProfileSignalValidationService().validate(result, system_map=system_map)
```

- [ ] **Step 2：執行 red test**

執行：

```bash
.venv/bin/pytest tests/unit/core/test_profile_signal_validation_service.py -v
```

預期：FAIL，缺少 `profile_signal_validation_service`。

- [ ] **Step 3：實作 validation**

建立 `src/systograph/core/services/profile_signal_validation_service.py`：

```python
"""Validation for non-canonical profile signal results."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from systograph.core.models.profile_signal import ProfileInferenceResult
from systograph.core.models.ai_system_map_v2 import AiSystemMapV2

ABSOLUTE_PATH_MARKERS = ("/Users/", "/home/", "C:\\\\", "\\\\\\\\")


class ProfileSignalValidationError(ValueError):
    """Raised when profile findings violate contract boundaries."""


class ProfileSignalValidationService:
    """Validate profile findings against the current canonical map."""

    def validate(
        self,
        result: ProfileInferenceResult,
        *,
        system_map: AiSystemMapV2,
    ) -> ProfileInferenceResult:
        known_evidence_ids = {evidence.id for evidence in system_map.evidence}
        known_unmapped_ids = {
            component.id for component in system_map.unmapped_components
        }
        known_capability_candidate_ids = {
            component.id
            for component in getattr(
                result,
                "capability_candidate_components",
                []
            )
        }
        known_risk_hint_ids = {risk.id for risk in system_map.risk_hints}
        for profile in result.profiles:
            unknown = sorted(set(profile.evidence_ids) - known_evidence_ids)
            if unknown:
                raise ProfileSignalValidationError(
                    "ProfileFinding "
                    f"'{profile.profile_id}' references unknown evidence: "
                    f"{', '.join(unknown)}"
                )
            self._reject_unknown_related_ids(
                profile.profile_id,
                "unmapped component",
                profile.related_unmapped_component_ids,
                known_unmapped_ids,
            )
            self._reject_unknown_related_ids(
                profile.profile_id,
                "capability candidate component",
                profile.related_capability_candidate_component_ids,
                known_capability_candidate_ids,
            )
            self._reject_unknown_related_ids(
                profile.profile_id,
                "risk hint",
                profile.related_risk_hint_ids,
                known_risk_hint_ids,
            )
        self._reject_local_absolute_paths(result.model_dump(mode="json"))
        return result

    def _reject_unknown_related_ids(
        self,
        profile_id: str,
        related_type: str,
        references: list[str],
        known_ids: set[str],
    ) -> None:
        unknown = sorted(set(references) - known_ids)
        if unknown:
            raise ProfileSignalValidationError(
                "ProfileFinding "
                f"'{profile_id}' references unknown related {related_type}: "
                f"{', '.join(unknown)}"
            )

    def _reject_local_absolute_paths(
        self,
        value: Any,
        path: str = "$",
    ) -> None:
        if isinstance(value, str):
            if any(marker in value for marker in ABSOLUTE_PATH_MARKERS):
                raise ProfileSignalValidationError(
                    f"Profile signal text contains an absolute path at {path}"
                )
            return
        if isinstance(value, Mapping):
            for key, child in value.items():
                self._reject_local_absolute_paths(child, f"{path}.{key}")
            return
        if isinstance(value, list):
            for index, child in enumerate(value):
                self._reject_local_absolute_paths(child, f"{path}[{index}]")
```

- [ ] **Step 4：執行 validation tests**

執行：

```bash
.venv/bin/pytest tests/unit/core/test_profile_signal_validation_service.py -v
```

預期：PASS。

## Task 3：實作 Deterministic Profile Inference

**檔案：**
- Create：`src/systograph/core/services/profile_inference_service.py`
- Test：`tests/unit/core/test_profile_inference_service.py`

- [ ] **Step 1：撰寫 inference tests**

建立 `tests/unit/core/test_profile_inference_service.py`：

```python
from __future__ import annotations

import json
from pathlib import Path

from systograph.core.models.system_map import (
    Evidence,
    UnmappedComponent,
)
from systograph.core.models.capability_candidate import CapabilityCandidateComponent
from systograph.core.services.profile_inference_service import (
    ProfileInferenceService,
)
from systograph.core.services.system_map_validation_service import (
    SystemMapValidationService,
)


MINIMAL_FIXTURE_PATH = Path("tests/fixtures/ai_system_map/valid_minimal.v1.json")
RICH_FIXTURE_PATH = Path(
    "tests/fixtures/ai_system_map/valid_rich_frontend_sample.v1.json"
)


def load_minimal_map():
    data = json.loads(MINIMAL_FIXTURE_PATH.read_text(encoding="utf-8"))
    return SystemMapValidationService().validate(data)


def load_rich_map():
    data = json.loads(RICH_FIXTURE_PATH.read_text(encoding="utf-8"))
    return SystemMapValidationService().validate(data)


def test_detects_grounding_baseline_from_core_retrieval_and_generation_evidence() -> None:
    system_map = load_rich_map()

    result = ProfileInferenceService().infer(
        system_map,
        capability_candidate_components=[
            CapabilityCandidateComponent(
                id="capability-candidate:fixture:reranker",
                observed_kind="reranker",
                status="confirmed_non_baseline",
                evidence_ids=["evidence:code_pattern:reranker"],
            )
        ],
    )

    profiles = {profile.profile_id: profile for profile in result.profiles}
    assert profiles["rag-grounding"].status == "detected"
    assert profiles["rag-grounding"].evidence_ids


def test_marks_advanced_rag_undetermined_from_reranker_without_path_evidence() -> None:
    system_map = load_minimal_map().model_copy(deep=True)
    system_map.evidence.append(
        Evidence(
            id="evidence:code_pattern:reranker",
            kind="config_value",
            file="config.yaml",
            path="reranker.provider",
            value="sentence_transformers",
            rule_id="config_yaml_value_detected",
        )
    )
    system_map = SystemMapValidationService().validate(
        system_map.model_dump(mode="json")
    )

    result = ProfileInferenceService().infer(
        system_map,
        capability_candidate_components=[
            CapabilityCandidateComponent(
                id="capability-candidate:config-yaml:reranker",
                name="Reranker",
                observed_kind="reranker",
                status="confirmed_non_baseline",
                evidence_ids=["evidence:code_pattern:reranker"],
            )
        ],
    )

    profiles = {profile.profile_id: profile for profile in result.profiles}
    assert profiles["reranking"].status == "undetermined"
    assert profiles["reranking"].implementation_depth_level == 2
    assert profiles["reranking"].evidence_ids == [
        "evidence:code_pattern:reranker"
    ]


def test_does_not_detect_advanced_rag_without_enhancement_signal() -> None:
    system_map = load_rich_map()

    result = ProfileInferenceService().infer(system_map)

    profiles = {profile.profile_id: profile for profile in result.profiles}
    assert profiles["reranking"].status == "not_detected"
    assert profiles["reranking"].implementation_depth_level == 0
    assert profiles["reranking"].evidence_ids == []


def test_marks_agentic_control_undetermined_from_confirmed_non_baseline_tool() -> None:
    system_map = load_minimal_map().model_copy(deep=True)
    system_map.evidence.append(
        Evidence(
            id="evidence:code_pattern:tool",
            kind="code_pattern",
            file="src/agent.py",
            path="tool_registry",
            value="retrieval_tool",
            rule_id="code_pattern_agent_tool_registry",
        )
    )
    system_map.unmapped_components.append(
        UnmappedComponent(
            id="unmapped:src-agent-py:tool-registry",
            source_file="src/agent.py",
            observed_kind="agent_tool_signal",
            status="needs_confirmation",
            reason="Detected agent tool signal but runtime use is unconfirmed.",
            evidence_ids=["evidence:code_pattern:tool"],
            suggested_actions=["confirm_mapping"],
        )
    )
    system_map = SystemMapValidationService().validate(
        system_map.model_dump(mode="json")
    )

    result = ProfileInferenceService().infer(
        system_map,
        capability_candidate_components=[
            CapabilityCandidateComponent(
                id="capability-candidate:src-agent-py:tool-registry",
                observed_kind="agent_tool_signal",
                status="confirmed_non_baseline",
                evidence_ids=["evidence:code_pattern:tool"],
                source_unmapped_component_id="unmapped:src-agent-py:tool-registry",
            )
        ],
    )

    profiles = {profile.profile_id: profile for profile in result.profiles}
    assert profiles["agentic-control"].status == "undetermined"
    assert profiles["agentic-control"].implementation_depth_level == 1
    assert profiles["agentic-control"].evidence_ids == []
    assert profiles["agentic-control"].related_capability_candidate_component_ids == [
        "capability-candidate:src-agent-py:tool-registry"
    ]
```

為其餘每個 MVP profile 各新增一個 focused test：

```python
def test_detects_hybrid_retrieval_from_dense_sparse_and_fusion_signals() -> None:
    ...


def test_marks_corrective_retrieval_from_evaluator_or_fallback_signal() -> None:
    ...


def test_marks_self_rag_from_reflection_or_self_critique_signal() -> None:
    ...


def test_marks_agentic_rag_undetermined_from_tool_calling_without_controller_loop() -> None:
    ...


def test_detects_graph_knowledge_rag_only_when_graph_retrieval_enters_answer_path() -> None:
    ...


def test_marks_hierarchical_rag_from_recursive_summary_tree_signal() -> None:
    ...


def test_detects_contextual_retrieval_from_contextualizer_or_chunk_context_signal() -> None:
    ...


def test_marks_multimodal_rag_from_modality_specific_retrieval_signal() -> None:
    ...


def test_detects_modular_rag_only_from_replaceable_component_contract() -> None:
    ...


def test_marks_multi_head_rag_from_multi_aspect_retrieval_signal() -> None:
    ...
```

每個 test 必須 assert：

- 預期的 `profile_id`；
- 僅當 deterministic evidence 足夠強時 status 為 `detected`；
- 已確認不是 legacy v1 slot、但 profile 規則不足時
  status 為 `undetermined`；
- 完全沒有 profile-relevant evidence 且 capability coverage gate 通過時，status 才是
  `not_detected`；coverage 不足時必須是 `undetermined`；
- 所有 `evidence_ids` 存在於同一 `AiSystemMapV2`；
- 沒有 profile 建立或修改 canonical `flows`、`components_by_slot`、`system_type` 或 `classification.selected_template`。
- dependency-only、naming-only、raw unmapped candidate 與 risk hints 等 weak signals 若與
  profile 相關但不足，維持 `undetermined`；沒有 relevant evidence 但 coverage 未完成也仍是
  `undetermined`。

- [ ] **Step 2：執行 red test**

執行：

```bash
.venv/bin/pytest tests/unit/core/test_profile_inference_service.py -v
```

預期：FAIL，缺少 `profile_inference_service`。

- [ ] **Step 3：實作 deterministic inference**

建立 `src/systograph/core/services/profile_inference_service.py`：

```python
"""Infer stackable non-canonical profile signals from validated maps."""

from __future__ import annotations

from collections.abc import Sequence

from systograph.core.models.profile_signal import (
    ProfileFinding,
    ProfileInferenceResult,
)
from systograph.core.models.capability_candidate import CapabilityCandidateComponent
from systograph.core.models.ai_system_map_v2 import AiSystemMapV2
from systograph.core.services.profile_signal_validation_service import (
    ProfileSignalValidationService,
)


class ProfileInferenceService:
    """Emit local-only deterministic profile findings."""

    def __init__(
        self,
        *,
        validation_service: ProfileSignalValidationService | None = None,
    ) -> None:
        self._validation_service = (
            validation_service or ProfileSignalValidationService()
        )

    def infer(
        self,
        system_map: AiSystemMapV2,
        *,
        build_id: str,
        scan_id: str,
        environment_id: str,
        capability_candidate_components: Sequence[
            CapabilityCandidateComponent
        ] = (),
    ) -> ProfileInferenceResult:
        detected_findings = [
            *self._grounding_baseline(system_map),
            *self._hybrid_retrieval(system_map),
            *self._advanced_rag_from_reranker(
                system_map,
                capability_candidate_components,
            ),
            *self._corrective_retrieval(system_map),
            *self._self_rag(system_map),
            *self._agentic_rag(system_map, capability_candidate_components),
            *self._graph_knowledge_rag(system_map),
            *self._hierarchical_rag(system_map),
            *self._contextual_retrieval(system_map),
            *self._multimodal_rag(system_map),
            *self._modular_rag(system_map),
            *self._multi_head_rag(system_map),
        ]
        findings = self._complete_profile_assessments(
            detected_findings,
            system_map=system_map,
        )
        result = ProfileInferenceResult(
            source_schema_version=system_map.schema_version,
            build_id=build_id,
            scan_id=scan_id,
            environment_id=environment_id,
            capability_candidate_components=list(capability_candidate_components),
            profiles=sorted(findings, key=lambda item: item.profile_id),
        )
        return self._validation_service.validate(result, system_map=system_map)

    def _complete_profile_assessments(
        self,
        findings: list[ProfileFinding],
        *,
        system_map: AiSystemMapV2,
    ) -> list[ProfileFinding]:
        by_id = {finding.profile_id: finding for finding in findings}
        for profile_id in MVP_CAPABILITY_PROFILE_IDS:
            coverage = self._coverage_for(profile_id, system_map)
            by_id.setdefault(
                profile_id,
                self._profile_finding(
                    profile_id=profile_id,
                    status=(
                        "not_detected" if coverage.gate_passed else "undetermined"
                    ),
                    evidence_ids=list(coverage.evidence_ids),
                    evidence_strength=(
                        "not_detected"
                        if coverage.gate_passed
                        else "weak_or_ambiguous_signal"
                    ),
                    implementation_depth_level=0,
                    uncertainty=coverage.reason,
                    not_detected_coverage_gate_passed=coverage.gate_passed,
                    recommended_next_checks=list(coverage.next_checks),
                ),
            )
        return list(by_id.values())

    def _profile_finding(
        self,
        *,
        profile_id: str,
        status: str,
        evidence_ids: list[str],
        evidence_strength: str,
        implementation_depth_level: int,
        uncertainty: str | None = None,
        implementation_depth_reason: str | None = None,
        related_capability_candidate_component_ids: list[str] | None = None,
        recommended_next_checks: list[str] | None = None,
    ) -> ProfileFinding:
        label, primary_axis = PROFILE_METADATA[profile_id]
        return ProfileFinding(
            profile_id=profile_id,
            label=label,
            primary_axis=primary_axis,
            secondary_axes=[],
            implementation_depth_level=implementation_depth_level,
            implementation_depth_reason=implementation_depth_reason,
            status=status,
            evidence_ids=evidence_ids,
            evidence_strength=evidence_strength,
            uncertainty=uncertainty,
            related_capability_candidate_component_ids=(
                related_capability_candidate_component_ids or []
            ),
            recommended_next_checks=recommended_next_checks or [],
        )

    def _grounding_baseline(
        self,
        system_map: AiSystemMapV2,
    ) -> list[ProfileFinding]:
        core_slots = {
            "embedding_model",
            "vector_store",
            "retriever",
            "llm",
        }
        detected_core_slots = {
            slot_name
            for slot_name in core_slots
            if system_map.components_by_slot.get(slot_name) is not None
            and system_map.components_by_slot[slot_name].status == "detected"
        }
        if detected_core_slots != core_slots:
            return []

        evidence_ids = sorted(
            {
                evidence_id
                for slot_name in detected_core_slots
                for instance in system_map.components_by_slot[
                    slot_name
                ].instances
                for evidence_id in instance.evidence_ids
            }
        )
        return [
            self._profile_finding(
                profile_id="rag-grounding",
                status="detected",
                evidence_ids=evidence_ids,
                evidence_strength="static_multiple_signals",
                implementation_depth_level=3,
                implementation_depth_reason=(
                    "core indexing, retrieval, and generation slots are detected"
                ),
                uncertainty=None,
                recommended_next_checks=[],
            )
        ]

    def _advanced_rag_from_reranker(
        self,
        system_map: AiSystemMapV2,
        capability_candidate_components: Sequence[CapabilityCandidateComponent],
    ) -> list[ProfileFinding]:
        candidate_evidence_ids = {
            evidence_id
            for candidate in capability_candidate_components
            if candidate.observed_kind == "reranker"
            and candidate.status == "confirmed_non_baseline"
            for evidence_id in candidate.evidence_ids
        }
        evidence_ids = sorted(candidate_evidence_ids)
        if not evidence_ids:
            return []
        return [
            self._profile_finding(
                profile_id="reranking",
                status="undetermined",
                evidence_ids=evidence_ids,
                evidence_strength="weak_or_ambiguous_signal",
                implementation_depth_level=2,
                implementation_depth_reason=(
                    "reranker component exists, but the query / answer path is "
                    "not proven end-to-end"
                ),
                uncertainty=(
                    "Reranker evidence exists, but runtime path is not confirmed."
                ),
                related_capability_candidate_component_ids=[
                    candidate.id
                    for candidate in capability_candidate_components
                    if candidate.observed_kind == "reranker"
                ],
                recommended_next_checks=["review reranker code path"],
            )
        ]

    def _agentic_rag(
        self,
        system_map: AiSystemMapV2,
        capability_candidate_components: Sequence[CapabilityCandidateComponent],
    ) -> list[ProfileFinding]:
        candidate_ids = [
            candidate.id
            for candidate in capability_candidate_components
            if candidate.observed_kind in {"agentic_rag", "retrieval_tool"}
        ]
        if not candidate_ids:
            return []
        return [
            self._profile_finding(
                profile_id="agentic-control",
                status="undetermined",
                evidence_ids=[],
                evidence_strength="weak_or_ambiguous_signal",
                implementation_depth_level=1,
                implementation_depth_reason=(
                    "agent/tool-like signal exists, but no controller loop is proven"
                ),
                uncertainty=(
                    "Confirmed non-baseline agent/tool-like evidence exists, "
                    "but MVP rules cannot classify it as a detected profile yet."
                ),
                related_capability_candidate_component_ids=[
                    *sorted(candidate_ids)
                ],
            )
        ]
```

以 deterministic facts 實作其餘 helper methods，對象為 normalized v2 components、
edges、non-baseline capability candidates、legacy compatibility
refs、risks 與 evidence metadata。不得在 profile layer 重新掃 raw source。

- 當 high-specificity code/config evidence、confirmed mapping output 或多個獨立 static signals 直接識別 capability 時使用 `detected`；
- dependency-only、naming-only、agent/tool-like 或 multi-agent orchestration hints 不足但與某 profile 相關時使用 `undetermined`；
- 完全沒有 profile-relevant evidence且 coverage gate 通過時才使用 `not_detected`；
  coverage 不足使用 `undetermined`；
- required signals 只完成一部分時使用 `partial`；同欄位可信 evidence 互斥時使用
  `conflicted` 並保存 field-specific refs；
- activation 狀態獨立推導，不以 assessment status 代替；
- suspicious evidence 留在 `unmapped_components`、non-baseline capability candidates、risk hints、mapping proposal 或 manual mapping UI；
- 必要時透過 `related_unmapped_component_ids`、`related_capability_candidate_component_ids` 或 `related_risk_hint_ids` 附加 suspicious object ids 供 navigation；
- profile inference 不要呼叫 `ManualMappingService`；
- 永不新增 `confidence`；
- 永不 mutate `system_map`。

在 service 附近定義單一 registry：

```python
PROFILE_METADATA: dict[str, tuple[str, str]] = {
    "rag-grounding": ("RAG Grounding", "grounding"),
    "agentic-control": ("Agentic Control", "agent_control"),
    "tool-calling": ("Tool Calling", "tool_use"),
    "memory": ("Memory", "memory"),
    "workflow-orchestration": ("Workflow Orchestration", "workflow_orchestration"),
    "hybrid-retrieval": ("Hybrid Retrieval", "retrieval_strategy"),
    "reranking": ("Reranking", "retrieval_strategy"),
    "corrective-retrieval": ("Corrective Retrieval", "agent_control"),
    "self-reflection": ("Self Reflection", "agent_control"),
    "graph-retrieval": ("Graph Retrieval", "knowledge_structure"),
    "hierarchical-retrieval": ("Hierarchical Retrieval", "knowledge_structure"),
    "contextual-retrieval": ("Contextual Retrieval", "context_enrichment"),
    "multimodal-grounding": ("Multimodal Grounding", "data_modality"),
    "modular-composition": ("Modular Composition", "design_paradigm"),
    "multi-query-retrieval": ("Multi-query Retrieval", "retrieval_strategy"),
}

MVP_CAPABILITY_PROFILE_IDS: tuple[str, ...] = (
    "rag-grounding",
    "agentic-control",
    "tool-calling",
    "memory",
    "workflow-orchestration",
    "hybrid-retrieval",
    "reranking",
    "corrective-retrieval",
    "self-reflection",
    "graph-retrieval",
    "hierarchical-retrieval",
    "contextual-retrieval",
    "multimodal-grounding",
    "modular-composition",
    "multi-query-retrieval",
)
```

新增 tests，assert 每次 inference result 恰好包含此 profile id set：

```python
assert {profile.profile_id for profile in result.profiles} == set(MVP_CAPABILITY_PROFILE_IDS)
```

- [ ] **Step 4：執行 inference tests**

執行：

```bash
.venv/bin/pytest tests/unit/core/test_profile_inference_service.py -v
```

預期：PASS。

## Superseded Task 3.5：Sidecar Writer Handoff to Plan 03

> **Do not implement this section from Plan 02.** 以下內容只保留歷史脈絡。Sidecar path、
> writer、collision handling、publish ordering、CLI path output、`MapBuildResult` 與
> same-build artifact lifecycle 全部由 Plan 03 唯一擁有。Plan 02 只回傳 validated
> `ProfileInferenceResult`。

**檔案：**
- Modify：`src/systograph/core/models/scan.py`
- Modify：`src/systograph/core/providers/output_artifact_provider.py`
- Modify：`src/systograph/core/models/map_build.py`
- Modify：`src/systograph/core/services/map_build_service.py`
- Modify：`src/systograph/cli/map_command.py`
- Test：`tests/unit/core/test_output_artifact_provider.py`
- Test：`tests/integration/test_map_build_service.py`
- Test：`tests/cli/test_map_command.py`

- [ ] **Step 1：新增 failing sidecar tests**

擴充 map build 與 CLI tests，使 successful build assert：

```python
assert result.profile_signals_path is not None
assert result.profile_signals_path.name == "profile_signals.json"
assert result.profile_signals_path.is_file()
assert result.profile_signals_path.parent == result.map_json_path.parent
assert "profile_signals.json" in cli_result.stdout
```

同時 assert canonical map 未被污染：

```python
artifact_data = json.loads(result.map_json_path.read_text(encoding="utf-8"))
assert "profile_inference_result" not in artifact_data
assert "profiles" not in artifact_data
```

- [ ] **Step 2：新增 output path support**

修改 `OutputRun`：

```python
@property
def profile_signals_path(self) -> Path:
    return self.root_dir / "profile_signals.json"
```

將 `profile_signals.json` 加入 `ARTIFACT_FILENAMES`，使 timestamped output runs 避免覆寫先前 profile sidecars。

- [ ] **Step 3：新增 sidecar writer**

新增 `OutputArtifactProvider.write_profile_signals()`：

```python
def write_profile_signals(
    self,
    profile_result: ProfileInferenceResult,
    *,
    output_run: OutputRun,
) -> Path:
    output_run.root_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = output_run.profile_signals_path
    artifact_path.write_text(
        json.dumps(
            profile_result.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return artifact_path
```

- [ ] **Step 4：將 map build 接線為 infer 一次並重用**

`MapBuildService.build()` 應：

1. build 並 validate `system_map`；
2. infer 並 validate `profile_result`；
3. 寫入 `ai_system_map.json`；
4. 寫入 `profile_signals.json`；
5. 從 canonical map render Markdown；
6. 將同一 `profile_result` 傳入 viewer projection。

`MapBuildResult` 應暴露：

```python
profile_signals_path: Path | None = None
```

- [ ] **Step 5：執行 sidecar tests**

執行：

```bash
.venv/bin/pytest \
  tests/unit/core/test_output_artifact_provider.py \
  tests/integration/test_map_build_service.py \
  tests/cli/test_map_command.py \
  -v
```

預期：PASS。

## Superseded Task 4：Projection Handoff to Plan 06

> **Do not implement this section from Plan 02.** 以下舊 snippet 只保留歷史脈絡。
> `GraphViewModel`、fixed reference map、repo overlay、details、filters、legend、degraded
> viewer load 與 backend/frontend projection contract 全部由 Plan 06 唯一擁有。

**檔案：**
- Modify：`src/systograph/core/models/viewer.py`
- Modify：`src/systograph/core/services/viewer_session_service.py`
- Test：`tests/unit/core/test_viewer_profile_projection.py`

- [ ] **Step 1：撰寫 viewer projection tests**

建立 `tests/unit/core/test_viewer_profile_projection.py`：

```python
from __future__ import annotations

import json
from pathlib import Path

from systograph.core.services.system_map_validation_service import (
    SystemMapValidationService,
)
from systograph.core.services.viewer_session_service import ViewerSessionService


FIXTURE_PATH = Path(
    "tests/fixtures/ai_system_map/valid_rich_frontend_sample.v1.json"
)


def test_viewer_payload_includes_non_canonical_profile_result() -> None:
    system_map = SystemMapValidationService().validate(
        json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    )

    result = ViewerSessionService().build(system_map)

    profile_result = result.profile_inference_result
    assert profile_result is not None
    assert profile_result.schema_version == "profile-signals/v1"
    assert "profile_inference_result" not in result.ai_system_map
    assert "profile_inference_result" not in result.map_json


def test_graph_details_index_profile_findings_by_id() -> None:
    system_map = SystemMapValidationService().validate(
        json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    )

    graph = ViewerSessionService().project_to_graph(system_map)

    assert graph.details.profile_findings_by_id
    assert "rag-grounding" in graph.details.profile_findings_by_id
```

新增 sidecar-optional degraded load tests：

```python
def test_load_map_degrades_when_profile_sidecar_is_missing(
    tmp_path: Path,
) -> None:
    map_path = tmp_path / "ai_system_map.json"
    map_path.write_text(FIXTURE_PATH.read_text(encoding="utf-8"), encoding="utf-8")

    result = ViewerSessionService().load_map(map_path)

    assert result.loaded is True
    assert result.error_reason is None
    assert result.ai_system_map["schema_version"] == "ai-system-map/v1"
    assert result.graph_view_model.nodes
    assert result.profile_inference_result is None
    assert "profile_signals_missing" in result.warnings


def test_load_map_degrades_when_profile_sidecar_is_invalid(
    tmp_path: Path,
) -> None:
    map_path = tmp_path / "ai_system_map.json"
    map_path.write_text(FIXTURE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "profile_signals.json").write_text(
        '{"schema_version": "profile-signals/v1", "source_schema_version": "ai-system-map/v1", "profiles": [{"profile_id": "reranking", "label": "Reranking", "primary_axis": "retrieval_strategy", "secondary_axes": [], "implementation_depth_level": 3, "status": "detected", "evidence_ids": ["evidence:missing"], "evidence_strength": "static_single_signal"}]}',
        encoding="utf-8",
    )

    result = ViewerSessionService().load_map(map_path)

    assert result.loaded is True
    assert result.error_reason is None
    assert result.ai_system_map["schema_version"] == "ai-system-map/v1"
    assert result.graph_view_model.nodes
    assert result.profile_inference_result is None
    assert "profile_signals_invalid" in result.warnings
```

- [ ] **Step 2：執行 red test**

執行：

```bash
.venv/bin/pytest tests/unit/core/test_viewer_profile_projection.py -v
```

預期：FAIL，因為 `profile_inference_result`、`profile_findings_by_id`、`warnings` 與 sidecar-optional degraded load behavior 尚不存在。

- [ ] **Step 3：擴充 viewer models**

修改 `src/systograph/core/models/viewer.py`：

```python
from systograph.core.models.profile_signal import ProfileInferenceResult


class GraphDetailsModel(ViewerModel):
    evidence_by_id: dict[str, dict[str, Any]] = Field(default_factory=dict)
    risk_hints_by_id: dict[str, dict[str, Any]] = Field(default_factory=dict)
    profile_findings_by_id: dict[str, dict[str, Any]] = Field(
        default_factory=dict
    )


class ViewerLoadResult(ViewerModel):
    loaded: bool
    error_reason: str | None = None
    warnings: list[str] = Field(default_factory=list)
    map_json: str | None = None
    ai_system_map: dict[str, Any]
    graph_view_model: GraphViewModel
    profile_inference_result: ProfileInferenceResult | None = None
```

- [ ] **Step 4：將 profile inference 接線至 viewer projection**

修改 `src/systograph/core/services/viewer_session_service.py`：

```python
from collections.abc import Sequence

from systograph.core.models.profile_signal import ProfileInferenceResult
from systograph.core.services.profile_inference_service import (
    ProfileInferenceService,
)


class ViewerSessionService:
    def __init__(
        self,
        *,
        validation_service: SystemMapValidationService | None = None,
        profile_inference_service: ProfileInferenceService | None = None,
    ) -> None:
        self._validation_service = (
            validation_service or SystemMapValidationService()
        )
        self._profile_inference_service = (
            profile_inference_service or ProfileInferenceService()
        )

    def build(
        self,
        system_map: AiSystemMapV2,
        *,
        map_json_path: Path | None = None,
        profile_inference_result: ProfileInferenceResult | None = None,
        infer_profile_if_missing: bool = True,
        warnings: Sequence[str] = (),
    ) -> ViewerLoadResult:
        profile_result = profile_inference_result
        if profile_result is None and infer_profile_if_missing:
            profile_result = self._profile_inference_service.infer(system_map)
        graph = self.project_to_graph(
            system_map,
            map_json_path=map_json_path,
            profile_inference_result=profile_result,
        )
        system_map_data = system_map.model_dump(mode="json")
        return ViewerLoadResult(
            loaded=True,
            error_reason=None,
            warnings=list(warnings),
            map_json=json.dumps(system_map_data, ensure_ascii=False),
            ai_system_map=system_map_data,
            graph_view_model=graph,
            profile_inference_result=profile_result,
        )
```

為 `project_to_graph()` 新增 `profile_inference_result` 參數，並用於 `GraphDetailsModel`：

```python
profile_findings_by_id={
    profile.profile_id: profile.model_dump(mode="json")
    for profile in (profile_inference_result.profiles if profile_inference_result else [])
}
```

更新 `load_map()`，使其對既有 `ai_system_map.json` 永不執行 load-time transient profile inference；profile sidecar 缺失或 invalid 時仍載入 base graph：

```python
profile_signals_path = map_json_path.with_name("profile_signals.json")
profile_result: ProfileInferenceResult | None = None
warnings: list[str] = []

if not profile_signals_path.is_file():
    warnings.append("profile_signals_missing")
else:
    try:
        profile_result = ProfileInferenceResult.model_validate_json(
            profile_signals_path.read_text(encoding="utf-8")
        )
        profile_result = ProfileSignalValidationService().validate(
            profile_result,
            system_map=system_map,
        )
    except (OSError, ValidationError, ProfileSignalValidationError):
        profile_result = None
        warnings.append("profile_signals_invalid")

return self.build(
    system_map,
    map_json_path=map_json_path,
    profile_inference_result=profile_result,
    infer_profile_if_missing=False,
    warnings=warnings,
)
```

當 sidecar 缺失或 invalid 時，不要在 `load_map()` 內 fallback 至 `ProfileInferenceService().infer(system_map)`。一般 viewer load 應顯示 base graph；只有 map build validation、CI contract validation 或明確 strict mode 可以因 invalid profile sidecar fail closed。

- [ ] **Step 5：執行 viewer projection tests**

執行：

```bash
.venv/bin/pytest tests/unit/core/test_viewer_profile_projection.py tests/unit/core/test_viewer_session_service.py -v
```

預期：PASS。

## Task 5：更新 Backend API Schema

**檔案：**

- Modify：`src/systograph/web/schemas.py`
- Test：`tests/web/test_viewer_routes.py`

- [ ] **Step 1：先寫 web schema / route serialization 測試**

在既有 viewer route tests 補一個 profile-enabled payload case，驗證 response 可包含：

```python
assert body["viewer_load_result"]["profile_inference_result"][
    "schema_version"
] == "profile-signals/v1"
```

- [ ] **Step 2：執行 red test**

```bash
.venv/bin/pytest tests/web/test_viewer_routes.py -v
```

預期：FAIL，因為 web schema 尚未 re-export profile models 或 route 尚未序列化該欄位。

- [ ] **Step 3：在 web schemas re-export profile models**

修改 `src/systograph/web/schemas.py`：

```python
from systograph.core.models.profile_signal import (
    ProfileFinding,
    ProfileInferenceResult,
)

__all__ = [
    "DetailScanCreateRequest",
    "DetailScanResponse",
    "MapBuildApiRequest",
    "MapBuildResult",
    "ManualMapping",
    "ManualMappingCreate",
    "ManualMappingListResponse",
    "ManualMappingUpdate",
    "MappingProposal",
    "MappingProposalCreateRequest",
    "MappingProposalDecisionRequest",
    "MappingProposalDecisionResult",
    "MappingProposalListResponse",
    "ProfileFinding",
    "ProfileInferenceResult",
    "ProjectImportRequest",
    "ProjectImportResponse",
    "ScanBoundaryDecisionRequest",
    "ScanBoundaryProposal",
    "ScanCreateRequest",
    "ScanCreateResponse",
    "ScanProgressEvent",
    "TraceCreateRequest",
    "ViewerLoadMapRequest",
    "ViewerPayload",
]
```

- [ ] **Step 4：執行 web tests**

```bash
.venv/bin/pytest tests/web/test_viewer_routes.py -v
```

預期：PASS。

### Superseded Task 5.5：Frontend Handoff to Plan 06 / Hardy

> **Do not implement this section from Plan 02.** Frontend parsing、renderer、layout、
> legend、filter 與 interaction work 由 Plan 06 的最小 consumption contract及對應 Hardy
> plan 擁有。

**檔案：**

- Modify：`frontend/src/types.ts`
- Modify：`frontend/src/services/viewerApi.ts`
- Modify：`frontend/src/hooks/useViewerPayload.ts`
- Modify：`frontend/src/App.tsx`

- [ ] 以 Zod 定義 `ProfileFinding`、`ProfileInferenceResult`、viewer `warnings` 與 optional `profile_inference_result`。
- [ ] 修正 mapping candidate schema，使 non-baseline candidate 的 nullable fields 與 backend contract 一致，且不再接受 canonical `confidence`。
- [ ] sidecar 缺失或 invalid 時顯示 non-blocking degraded state，base graph 仍可使用。
- [ ] frontend 不自行從 node 名稱、dependency 或 graph topology推論 profile。
- [ ] 執行 `pnpm build` 與 `pnpm lint`，並以 API mode 驗證 profile 有/無兩種 payload。

Meeting-Sync 文件只記錄跨團隊同步；Plan 02 不再持有 frontend implementation tasks。

## Task 6：新增 Profile-Aware Fixture Coverage

**檔案：**
- Modify：`tests/fixtures/ai_system_map/valid_rich_frontend_sample.v1.json`
- Modify：`tests/unit/core/test_profile_inference_service.py`
- 協調：`../phase4-scanner-expansion/31-expand-reranking-fixtures.md`

- [ ] **Step 1：為既有 rich fixture 新增 tests**

擴充 `tests/unit/core/test_profile_inference_service.py`：

```python
RICH_FIXTURE_PATH = Path(
    "tests/fixtures/ai_system_map/valid_rich_frontend_sample.v1.json"
)


def test_rich_fixture_emits_advanced_rag_from_reranker_capability_candidate() -> None:
    system_map = SystemMapValidationService().validate(
        json.loads(RICH_FIXTURE_PATH.read_text(encoding="utf-8"))
    )

    result = ProfileInferenceService().infer(system_map)

    profiles = {profile.profile_id: profile for profile in result.profiles}
    assert "reranking" in profiles
    assert profiles["reranking"].evidence_ids
    assert profiles["reranking"].primary_axis == "retrieval_strategy"
```

- [ ] **Step 2：執行 targeted tests**

執行：

```bash
.venv/bin/pytest tests/unit/core/test_profile_inference_service.py -v
```

預期：PASS。

- [ ] **Step 3：記錄 fixture coverage 邊界**

在 `../phase4-scanner-expansion/31-expand-reranking-fixtures.md` 更新此 note：

```markdown
Profile inference 會消費 advanced fixture signals，但 fixture expansion
仍是獨立計畫。本計畫僅需足夠 fixture coverage 以證明
`profile-signals/v1` 可 validate 且維持 non-canonical。
```

## Task 7：最終驗證

**檔案：**
- 除前述 tasks 外無新檔案。

- [ ] **Step 1：執行 backend targeted tests**

執行：

```bash
.venv/bin/pytest \
  tests/unit/core/test_profile_signal_models.py \
  tests/unit/core/test_profile_signal_validation_service.py \
  tests/unit/core/test_profile_inference_service.py \
  tests/unit/core/test_viewer_profile_projection.py \
  tests/unit/core/test_viewer_session_service.py \
  tests/unit/core/test_output_artifact_provider.py \
  tests/integration/test_map_build_service.py \
  tests/cli/test_map_command.py \
  -v
```

預期：PASS。

- [ ] **Step 2：執行 contract 與 snapshot safety tests**

執行：

```bash
.venv/bin/pytest \
  tests/contracts/test_ai_system_map_schema.py \
  tests/contracts/test_secret_snapshot_safety.py \
  -v
```

預期：PASS。

- [ ] **Step 3：執行 static quality checks**

執行：

```bash
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

預期：

```text
ruff：無 violations
mypy：success
git diff --check：無 whitespace errors
```

## 驗收標準

- `profile-signals/v1` 存在為 typed、validated、non-canonical contract。
- `ProfileInferenceService` 從 00A normalized v2 map emit deterministic local profile findings；v1 input 先經 adapter。
- Plan 02 產生帶 `build_id`、`scan_id`、environment 的 validated
  `ProfileInferenceResult`；Plan 03 負責 sidecar writer/lifecycle，Plan 06 負責 projection。
- 每個 active registry capability 在有 deterministic evidence 時可 emit 為獨立 profile finding。
- 每個 `ProfileInferenceResult` 包含 active registry 的全部 profile ids；coverage gate 通過且
  無 positive evidence 才可 `not_detected`，coverage 不足使用 `undetermined`。
- Registry 至少覆蓋 grounding、agent control、tool calling、memory、workflow orchestration、retrieval strategies 與 multimodal grounding。
- Status enum 為 `detected / partial / undetermined / not_detected / conflicted`；
  `activation` 使用六態並與 status 分離。
- Evidence 明確分為 direct、indirect、explicit negative；conflict 是 field-specific。
- `detected` threshold 保守：必須有 high-specificity direct code/config/wiring evidence；
  confirmed capability candidate 或多個獨立 deterministic signals 若仍只有 indirect
  evidence，一律只能是 `partial`。Dependency-only、naming-only、raw unmapped candidate、
  risk hint 與 recommended check evidence 不足。
- Profile findings 可含 related unmapped、capability candidate 與 risk hint ids 供 navigation；validation 拒絕 unknown related ids。
- `undetermined` 列可含 related ids，但不足以成為 `detected`。
- `not_detected` validation 必須檢查 coverage gate；可帶 coverage refs 與 explicit-negative
  evidence，不能把 weak positive evidence 當成 not detected。
- Backend related refs 僅提供 read-only navigation identifiers；API 不提供 profile-level confirmation 或 mutation actions。
- Agentic、single-agent 與 multi-agent evidence 只支撐單層 `agentic-control` finding，不建立 canonical topology 或新 templates。
- `GraphDetailsModel` 與 frontend consumption 由 Plan 06 擁有。
- `confidence` 不在 profile 與 canonical contracts 中。
- `ProfileInferenceService` standard path 完全 deterministic；Plan 17 deferred 期間
  `validated_candidates` 恆為空。未來重啟時，AI semantic candidate output 只能經
  `AssessmentOrchestrator` 驗證後作候選輸入，不能新增 canonical facts 或單獨提升 status。
- `detected` profile findings 需要來自同一 map 的既有 direct evidence ids。
- `not_detected` profile findings 必須有 completed coverage gate；coverage gate details 可提供
  evidence refs 與 recommended follow-up wording。
- `ProfileInferenceService` 不呼叫 `ManualMappingService`；它在 map build/component detection 已套用 confirmed mappings 後消費 validated map。
- Profile artifacts 不允許 raw source、raw prompt、full query/output、retrieved chunk raw text、full secrets 與 local absolute paths。
- 本計畫不引入 dynamic template、agent template 或 topology sidecar。

## P0 Execution Mapping 補充（2026-07-03）

Profile inference 可以消費 static execution artifacts 作為 **supporting evidence**，但不得把
static inferred path 當 runtime proof：

- `execution_paths.json` 可支撐 `rag-grounding`、`reranking`、`agentic-control` 等 profile 的
  related refs，但 `detected` 仍需要 high-specificity deterministic evidence。
- 僅有 call-like hint、dependency name、weak dataflow 或 incomplete scan coverage 時，profile
  status 應保持 `undetermined`；不得跳到 `not_detected`。
- `profile_signals.json` 不複製完整 call graph / dataflow；只保存 profile finding、evidence ids、
  related execution path ids 與 recommended next checks。
- Profile schema 仍不新增 `inferred` status；static inferred execution path 用
  `evidence_strength`、`implementation_depth_reason` 與 `uncertainty` 說明。
