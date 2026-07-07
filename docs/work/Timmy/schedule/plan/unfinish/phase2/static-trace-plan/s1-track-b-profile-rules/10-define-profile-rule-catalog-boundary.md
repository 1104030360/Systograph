# Profile Rule Catalog Boundary 實作計畫

> **執行者注意：** 逐 task 實作本計畫。步驟使用 checkbox（`- [ ]`）語法以便追蹤。

**目標：** 定義 raw detector rules、component taxonomy、grounding policy、
capability registry、semantic inference 與 optional LLM assist 的 ownership，確保
Two-Phase Analysis 不被 proposal/provider lifecycle 污染。

**架構：** Phase A 先由既有 TOML-backed providers emit primary typed
`ScanFact`/`Evidence`；Gate-1 通過並完成 Plan 16 後，Phase B 才由 UA sidecar +
`UaStructuralAdapter` 接手 primary，TOML-backed providers 轉為 parity-only。Step 4 bridge 1
在兩階段都由 Python `component_bridge_registry.py`
把 raw facts 分流為 repo component / unmapped / candidate input；Step 6 bridge 2
由 Python `ProfileInferenceService` 對 normalized v2 map 做 10 planes / 52 reference
nodes 對位、status、coverage、depth 與 related-ref decisions。Plan 11 外移 registry
metadata，但 executable thresholds 仍在 Python。AI semantic candidate flow 屬於 Plan 17
`AssessmentOrchestrator`（**deferred**；Phase2 不實作，Step 6 無 AI 編排）；若未來重啟，
它只能讀 bounded fact packet、輸出 candidate + reason +
evidence_ids，不能創造 canonical facts 或單獨提升 status。

**Tech Stack：** Python 3.11、Pydantic v2、pytest、Ruff、mypy。本 MVP plan 不引入 TOML loader 或 profile TOML catalog。

---

## 2026-07-06 Confirmed Python / TOML Boundary

本節取代本文較早的三態、`detected/not-detected thresholding` 與由 Plan 10 擁有
graph projection 的描述。

- 固定 reference map 使用 10 planes / 52 nodes：`input_intent`、`control`、
  `ingestion_indexing`、`retrieval`、`extension_subsystems`、`evidence`、`generation`、
  `memory_state`、`governance_observability`、`deployment_topology`。Governance lens 可跨
  plane 顯示，但 canonical governance/observability facts 屬
  `governance_observability`。
- Python 擁有可執行語意：五態 `detected` / `partial` / `undetermined` /
  `not_detected` / `conflicted`、`activation`、direct / indirect / explicit-negative
  evidence 分類、field-specific conflict、`not_detected` coverage gate、assessment scope
  (`build_id`、`scan_id`、`environment_id`) 與 Mapping Completeness 計算；`scan_id` 識別
  immutable scan snapshot，不另設 `snapshot_id`。
- `detected` 必須有 direct evidence；indirect-only 一律 `partial`，多個 convergent indirect
  signals 也不能升級。Explicit negative 只接受明確 disabled/bypassed/forbidden 等；
  absence 不是 negative evidence。
- `not_applicable` 只在 catalog metadata 宣告 node 本質上沒有 activation 語意時使用；
  不是 backend 對目前 system/scope 的 applicability 判斷。
- `not_detected` 只有在該 reference capability 的 coverage gate 通過後才成立；尚未完整
  檢查時必須是 `undetermined`，不能因「沒有找到」直接判成 `not_detected`。
- Mapping Completeness 是可重算的 coverage metric，不是 confidence：`detected=1`、
  `not_detected=1`、`partial=0.5`、其餘為 `0`，再除以 catalog 內全部固定
  reference nodes；activation/not_applicable 不改變 denominator。
- TOML 只能保存固定 plane / reference node 的 label、description、order、legend wording、
  uncertainty 與 recommended next-check metadata；不得保存上述判斷規則或權重。
- Step 4 component bridge 的 `rule_id -> component / unmapped / candidate input` 規則
  屬於 Plan `01B` 的 Python registry；不得移入 `profile_registry.toml`、
  `capability_reference_map.toml` 或任何第三份 bridge TOML。
- Plan 06 是 backend projection 與 minimal viewer contract 的唯一 owner。Plan 10 只定義
  Python rule semantics 和 TOML 邊界，不實作 graph projection。

## 2026-07-07 UA 整合對齊

本計畫的 TOML/Python 邊界新增兩個 metadata-only 分類：

- **UA mapping 對應表**：若未來為 UA `rule_id` / symbol kind / import kind 提供文件化對應表，
  TOML 只能保存名稱、描述、來源類型與 migration alias；`rule_id + evidence -> component /
  unmapped / candidate` 的 executable 判定仍在 Python `component_bridge_registry.py` /
  `UaStructuralAdapter`。
- **AssessmentOrchestrator workflow 設定**（deferred，隨 Plan 17 重啟才建立）：可描述
  啟用哪些 candidate agent、prompt 版本、
  bounded input packet shape 與輸出 schema version；不得定五態、不得寫 canonical facts、
  不得觸發 `MappingProposalService`。

Phase A 的 Step 3 主掃描來源是 `code_pattern`、`dependency_manifest`、`docker_image` 與
config TOML providers；Gate-1 通過並完成 Plan 16 後，Phase B 的主掃描來源才切換為 UA
sidecar，上述 providers 轉為 Plan 18 前的 parity-only 路徑。

## 執行摘要

### 目標

固定 detector、taxonomy、readiness、profile trigger、metadata 與 LLM semantic
output 的 ownership，防止 catalog 變成不可審查 DSL。

### 背景

現有 scan、risk、proposal 使用不同 TOML/Python pattern；若未先定界，profile inference 容易把 raw pattern matching、status threshold 與 wording 混在同一 catalog。

### 目前 code 狀態

`RuleCatalogLoader` 尚無 profile catalog；profile service 也尚未存在。現有 `risk_hint_rules.toml` 與 `llm_proposal.toml` 都不適合承載 profile trigger logic。

### 相關檔案

- `src/kai_mind/core/services/profile_inference_service.py`（02 新增）
- `src/kai_mind/core/services/rule_catalog_loader.py`
- `src/kai_mind/core/services/risk_hint_service.py`
- `src/kai_mind/core/services/mapping_proposal_service.py`
- `tests/unit/core/test_profile_inference_boundaries.py`

### 實作步驟

先以 Python hard-code registry-driven ids/metadata/trigger，增加 dependency 與 weak-evidence tests，再由 11 只抽出 wording/static metadata。

### 驗收標準

Python 保有 status/coverage/depth/related-ref 決策；profile inference 不呼叫
proposal/manual lifecycle；optional LLM output 不進 canonical/profile status truth。

## 需求概念與本 repo 實作對照

| 產品規格概念 | Phase2 source of truth |
|---|---|
| HTTP API 端點與錯誤碼 | `docs/API-GUIDE.md` |
| 欄位語意、五態、activation、artifact schema | `docs/MODEL-CONTRACT.md` |
| 設計意圖與 staged rollout | `docs/design/epic1-phase2.md` |
| `scan_config.json` | CLI/API options + `pyproject.toml [tool.kai-mind.scan]`；不新增第二套重複設定 |
| `component_taxonomy.json` | v2 typed model/schema + package metadata catalog |
| `profile_registry.json` | Plan 11 從 hand-authored `profile_registry.toml` 產生的 read-only JSON projection；不是第二份可手改 source |
| `detector_rules.json` | 既有 `*_rules.toml` raw matching catalogs |
| `readiness_policy.json` | Readiness finding display metadata；source traceability 由 readiness finding 表達；不得包含 executable policy |
| `visualization_views.json` | Plan 06 backend projection/renderer contract |

格式可以沿用 repo 的 TOML/Python 慣例，但每個概念必須有單一 owner、schema 與
測試；不得同時維護內容相同的 JSON/TOML truth。

### 風險與注意事項

不可將 `condition`、regex、threshold 或 scoring 搬進 TOML。Profile status 是 evidence semantics，不是設定檔調參結果。

## 為何需要本計畫

目前 codebase 使用多種 rule-storage patterns：

- Scan providers 大量使用 TOML catalogs 做 raw-source matching，例如 `code_pattern_rules.toml`、`dependency_manifest_rules.toml`、`docker_image_rules.toml`。
- `RiskHintService` 使用 hybrid model：Python 決定何時 emit risk；`risk_hint_rules.toml` 存放 type、severity、rationale、uncertainty 等 metadata。
- `MappingProposalService` 不使用 TOML 作 mapping detection catalog；其 TOML 用途僅限 optional LLM proposal provider config（`llm_proposal.toml`）；deterministic proposal candidates 是 hard-coded Python heuristics。
- `ManualMappingService` 是 hard-coded Python 加上 bundled `rag-core-v1.json` slot metadata；它是 user-confirmation lifecycle，不是 rule catalog。
- Profile inference 在 `src/kai_mind/` 尚不存在；目前規劃於 `02-implement-stackable-profile-inference.md`。

本計畫避免常見錯誤：把 mapping proposal TOML、risk hint TOML 與 future profile inference rules 視為同一種機制。

## 目前證據

- `src/kai_mind/core/services/llm_proposal_config_loader.py` 僅為 optional LLM proposal provider defaults 載入 `llm_proposal.toml`。
- `src/kai_mind/core/services/mapping_proposal_service.py` 含 vector stores、routers、rerankers、needs-more-information、skip-for-now candidates 的 deterministic proposal heuristics。
- `src/kai_mind/core/services/manual_mapping_service.py` 驗證並持久化 user mapping decisions；allowed slots 來自 `RagTemplateService.load("rag-core-v1")`。
- `src/kai_mind/core/services/component_detection_service.py` 在 Python 中將 scan `rule_id` 對應到 slots/providers。
- `src/kai_mind/core/services/risk_hint_service.py` 在 Python emit risks，再從 `risk_hint_rules.toml` lookup metadata。
- `src/kai_mind/` 中目前沒有 `ProfileInferenceService`、`profile_signal.py` 或 `profile_registry.toml`。

## 決策

Phase 2B MVP：

- Profile inference 的 target input 是 00A normalized `AiSystemMapV2`；v1 先經 adapter。
- Component taxonomy 對齊固定 10-plane / 52-node reference map；不得再用 input/knowledge/context/ops
  七層分類作 active contract。

- 將 profile detection rules 保留在 `ProfileInferenceService` 或 closely related helper modules 的 Python 中。
- MVP 階段將 profile ids、display labels、feature-axis metadata、default uncertainty text、recommended next check strings、related-ref defaults 保留在 Python。
- 不重用 `llm_proposal.toml`、`mapping_proposal.v1.yaml`、`risk_hint_rules.toml`、`recommended_next_check_rules.toml` 做 profile detection。
- 本計畫不建立或載入 `profile_registry.toml`。
- Profile inference 不呼叫 `MappingProposalService`、`ManualMappingService` 或 proposal routes。
- AI candidate agents（deferred，屬 Plan 17）不得接收 raw source tree，只能接收 bounded
  deterministic fact
  packet；結果必須經 Plan 17 validator，且只作 candidate input。
- 不讓 risk hints 直接決定 `status="detected"`。Risk hints 可透過
  `related_risk_hint_ids` 附加供 navigation/provenance，但 weak risk 或 unmapped evidence
  alone 不足以判為 detected。若 weak evidence 與 profile 相關，emit `undetermined`；若
  無關，也只有在 profile-specific coverage gate 通過後才可 emit `not_detected`，否則仍是
  `undetermined`。
- 不要求 non-baseline evidence 先變成 user-facing `extension`，profile inference 才能評估。新 Phase2 flow 以 non-baseline capability candidate inputs 處理 confirmed non-baseline components；legacy `extensions` 僅 compatibility。
- `10` 本身不建立 `profile_registry.toml`，但 2026-07-02 使用者決定
  `11-migrate-profile-rule-metadata-to-toml-catalog.md` 進入目前 00-14 path。該 catalog
  只放 wording/metadata 與 static axis labels；Python 仍擁有五態、activation、evidence
  classification、coverage gate、conflict、scope validation、Mapping Completeness、
  implementation depth 與 related-ref selection。Graph projection 由 Plan 06 擁有。

## 架構對照

```text
Scan rules
  Phase A: TOML-backed providers emit primary ScanFact/Evidence
  Phase B: UA sidecar + Python adapter emit primary ScanFact/Evidence
           TOML-backed providers run only for parity until Plan 18

Risk hints
  Python decides when to emit
  TOML stores metadata/rationale/uncertainty

Component bridge（Step 4）
  Python component_bridge_registry.py owns rule_id + evidence -> component/unmapped/candidate
  No TOML bridge rules, no plane/reference-node ids

Mapping proposal
  TOML stores optional LLM provider config only
  Python owns deterministic candidate heuristics and lifecycle

Profile inference MVP
  Python owns deterministic bridge 2: repo facts -> reference-node assessment
  Python also owns profile wording/metadata/static axes at first
  No TOML catalog in 10
  Confirmed non-baseline components enter as non-baseline capability candidates,
  not as required extension records

Profile inference current-scope follow-up 11
  TOML may store profile wording/metadata/static axes
  Python still owns status, activation, evidence, conflict, coverage, scope and depth

Assessment orchestration
  Workflow metadata may describe candidate agents and prompt versions
  Python owns adapter, validation, candidate filtering and ProfileInference handoff
```

## 優先檢視的檔案

- `docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/02-implement-stackable-profile-inference.md`
- `docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/04-separate-profile-inference-from-mapping-proposal.md`
- `docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/05-add-read-only-system-map-index.md`
- `src/kai_mind/core/services/llm_proposal_config_loader.py`
- `src/kai_mind/core/services/mapping_proposal_service.py`
- `src/kai_mind/core/services/manual_mapping_service.py`
- `src/kai_mind/core/services/component_detection_service.py`
- `src/kai_mind/core/services/risk_hint_service.py`
- `src/kai_mind/core/services/rule_catalog_loader.py`
- `src/kai_mind/core/rules/risk_hint_rules.toml`
- `src/kai_mind/core/rules/recommended_next_check_rules.toml`

## 範圍

本計畫處理 rule ownership 與 catalog boundaries。它不自行實作所有 Phase 2B profile inference rules；那仍由 `02-implement-stackable-profile-inference.md` 擁有。

包含：

- 定義 MVP profile rule storage 決策。
- 鎖定 MVP 決策：所有 profile wording/metadata 也保留在 Python hard-coded。
- 新增 tests 或 guardrails，保持 profile inference 獨立於 mapping proposal 與 LLM provider config。
- 定義 `11` 引入 `profile_registry.toml` 時的邊界。
- 定義 future profile catalog 可與不可包含的內容。
- 文件化 profile inference 如何 reference 既有 risk hints，而不變成 risk-rule-driven。
- 文件化 `undetermined` 是 relevant but insufficient profile evidence 的正確狀態。

不包含：

- 不新增 LLM-backed profile inference。
- 不讓 profile findings 變成 user-confirmable mapping proposals。
- 不將 profile findings 持久化到 `ai_system_map.json`。
- 不使用 `extension` 作為 non-baseline components 的必要新分類。
- 不將 scan provider TOML rules 移入 profile inference。
- 不將 risk hint metadata 移入 profile rules。
- 不在 `10` 建立 `src/kai_mind/core/rules/profile_registry.toml`。
- 不在 `10` 新增 `RuleCatalogLoader.load_profile_registry()`。

## 實作 Tasks

### Task 1：記錄 Rule-Ownership Boundary

**檔案：**

- Modify: `docs/design/epic1-phase2.md`（canonical design）
- Test: 僅 documentation review

- [ ] 新增 decision note：Phase 2B MVP profile detection 是 Python deterministic logic，不是 TOML catalog。
- [ ] 新增 decision note：Phase 2B MVP profile labels、feature-axis metadata、default uncertainty、recommended next check strings 也是 Python hard-coded。
- [ ] 說明 mapping proposal TOML 僅為 optional LLM provider config，不得重用於 profile inference。
- [ ] 說明 risk hint TOML 是 emitted risk hints 的 metadata，不得成為 profile detection catalog。
- [ ] 說明 current-scope `profile_registry.toml` 僅能透過 `11-migrate-profile-rule-metadata-to-toml-catalog.md` 引入，且僅作 dedicated profile metadata / static axis catalog，不擁有 detected/depth threshold。

### Task 2：新增 Profile Dependency Guardrails

**檔案：**

- Create or modify: `tests/unit/core/test_profile_inference_boundaries.py`
- Future source under test: `src/kai_mind/core/services/profile_inference_service.py`

- [ ] 新增 focused import/dependency test，證明 profile inference 不 import `MappingProposalService`、`ManualMappingService`、`llm_proposal_config_loader` 或 provider-backed proposal modules。
- [ ] 新增 focused test，證明 profile inference 不 load `llm_proposal.toml`、`mapping_proposal.v1.yaml`、`risk_hint_rules.toml`、`recommended_next_check_rules.toml`、`profile_registry.toml`。
- [ ] 新增 focused test，證明 `related_risk_hint_ids` 是 optional references，本身不足以使 profile 為 `detected`。
- [ ] 新增 focused test，證明 weak but profile-relevant evidence 使用 `undetermined`；
  無 profile relevance 也必須在 coverage gate 通過後才可使用 `not_detected`；只有
  profile-specific Python rules 識別出 high-specificity evidence 時才可 `detected`。
- [ ] 新增 focused tests 覆蓋 `partial`、field-specific `conflicted`、六種
  `activation`、direct / indirect / explicit-negative evidence 與 assessment scope。
- [ ] 新增 Mapping Completeness 重算 test，固定權重為 detected 1、not_detected 1、
  partial 0.5、undetermined/conflicted 0，並證明它不接受 TOML 權重覆寫。

### Task 3：MVP Profile Rules 保留在 Python

**檔案：**

- Modify: `src/kai_mind/core/services/profile_inference_service.py`（Phase 2B implementation 建立後）
- Test: `tests/unit/core/test_profile_inference_service.py`

- [ ] MVP 將 `MVP_CAPABILITY_PROFILE_IDS` 或等效 profile checklist 保留在 Python。
- [ ] MVP 將 `MVP_PROFILE_METADATA` 或等效 profile metadata registry 保留在 Python。
- [ ] 將 detection thresholds 保留在 Python，包含 high-specificity evidence requirements 與 dependency-only/naming-only rejection。
- [ ] MVP 將 profile `display_name`、`short_label`、`primary_axis`、`secondary_axes`、default `uncertainty`、default `recommended_next_checks` 保留在 Python。
- [ ] MVP 將 `implementation_depth_level` 判斷留在 Python；future TOML 不得用 declarative score 直接決定 depth。
- [ ] Mapping decisions 間接影響：confirmed mappings 僅因 map build 已 apply 到 normalized `AiSystemMapV2` 而影響 profile inference。
- [ ] 可用時使用 `SystemMapIndex` 做 lookup，但 profile rules 留在 index 之外。
- [ ] 為每個 MVP profile row 新增 test cases：`rag-grounding`、`agentic-control`、`tool-calling`、`memory`、`workflow-orchestration`、`hybrid-retrieval`、`reranking`、`corrective-retrieval`、`self-reflection`、`graph-retrieval`、`hierarchical-retrieval`、`contextual-retrieval`、`multimodal-grounding`、`modular-composition`、`multi-query-retrieval`。

### Task 4：定義 Future Profile Catalog Trigger

**檔案：**

- Modify: 當 trigger 成立時更新本 plan 或 Phase 2 design doc
- Future create: `src/kai_mind/core/rules/profile_registry.toml`
- Future modify: `src/kai_mind/core/services/rule_catalog_loader.py`
- Future test: `tests/unit/core/test_rule_catalog_loader.py`

- [ ] `10` 不建立 `profile_registry.toml`。
- [ ] 2026-07-02 使用者決策：`11-migrate-profile-rule-metadata-to-toml-catalog.md` 納入目前 00-14 path，作為此 externalization 的唯一 follow-up plan。
- [ ] `11` 必須在 `02` 與本計畫（`10`）完成後執行。
- [ ] 若新增，TOML fields 保持 declarative 且 non-executable。
- [ ] 若日後新增，missing profile rule metadata 以 dedicated `ProfileRuleCatalogError` fail closed。
- [ ] 若日後新增，仍由 Python 擁有五態、activation、evidence classification、
  field-specific conflict、coverage gate、assessment scope、Mapping Completeness、
  implementation depth 與 related-ref strategy；graph projection 由 Plan 06 擁有。

Suggested future catalog shape：

```toml
[[profiles]]
profile_id = "reranking"
short_label = "Reranking"
display_name = "Reranking"
description = "Evidence suggests a reranker is connected to the retrieval path."
primary_axis = "retrieval_strategy"
secondary_axes = []
default_uncertainty = "Static evidence only; runtime path not confirmed."
allowed_evidence_kinds = ["code_pattern", "dependency", "config"]
related_rule_ids = ["code_pattern_reranker_detected"]
```

不要在此 catalog 放入 provider config、prompt templates、API endpoint settings、user-confirmation lifecycle state、detected threshold、implementation depth scoring 或 graph projection rules。

### Task 5：Align Risk References，但不 Coupling 到 Risk Rules

**檔案：**

- Modify: `src/kai_mind/core/services/profile_signal_validation_service.py`（建立後）
- Modify: `src/kai_mind/core/services/profile_inference_service.py`（建立後）
- Test: `tests/unit/core/test_profile_signal_validation_service.py`
- Test: `tests/unit/core/test_profile_inference_service.py`

- [ ] 僅當 ids 存在於 normalized `AiSystemMapV2` 時，允許 profile findings 包含 `related_risk_hint_ids`。
- [ ] 保持 `related_risk_hint_ids` 為 navigation/provenance references。
- [ ] 僅有 risk hints 支持 profile 時 reject 或保持 `undetermined`，除非另有
  high-specificity profile evidence；只有 coverage gate 通過後才可 `not_detected`。
- [ ] 新增 tests：risk hint 可出現在 related refs，但 profile-relevant evidence 不足時
  status 仍為 `undetermined`；risk hint 與該 profile 無關時，coverage gate 未通過仍為
  `undetermined`，通過後才為 `not_detected`。
- [ ] 新增 tests：detected profiles 需要來自同一 validated map 的 `evidence_ids`。

### Task 6：文件化 Mapping Contrast

**檔案：**

- Modify: `docs/design/epic1-phase2.md`（canonical design）
- Test: 僅 documentation review

- [ ] 新增簡短 comparison table：
  - `ManualMappingService`：hard-coded lifecycle + `rag-core-v1.json` slots。
  - `MappingProposalService`：optional LLM TOML config + Python deterministic candidates。
  - `ComponentDetectionService`：TOML-backed providers 的 scan facts + Python slot mapping。
  - `RiskHintService`：Python trigger logic + TOML metadata。
  - `ProfileInferenceService`：MVP Python deterministic enrichment；必要時 future profile-specific TOML metadata only。
- [ ] 明確說明 profile inference 不得暴露 accept/edit/reject 或 quick-confirm actions。
- [ ] 明確說明 profile rules 不 mutate canonical `ai_system_map.json`。

### Deferred Guardrail：Future Scan Mode Semantic Assist

**檔案：**

- Modify: `src/kai_mind/core/models/scan.py`
- Modify: `src/kai_mind/core/services/project_scan_service.py`
- Modify: `src/kai_mind/web/schemas.py`
- Test: `tests/unit/core/test_project_scan_service.py`

本節不是 Phase2 active task，不納入 Plan 14 acceptance。Phase2 Step 6 維持純 Python，且
Step 1～9 不新增 AI orchestration；Phase2 active path 不執行 UA `file-analyzer`。只有未來另案重啟 Plan 17 後，
才可重新評估 `fast` / `standard` / `deep` mode；屆時 semantic assist 必須 explicit opt-in、
只讀 bounded deterministic packets，且不得改 canonical/profile schema semantics。

## 驗收標準

- [ ] Phase 2 design docs 清楚說明 MVP 階段 profile rules 的存放位置。
- [ ] Phase 2 design docs 清楚說明 `10` 將 profile wording/metadata 保留在 Python hard-coded。
- [ ] 本 plan 區分 scan TOML、risk metadata TOML、LLM proposal TOML 與 future profile catalog TOML。
- [ ] Profile inference dependency tests 防止 import mapping proposal services、manual mapping lifecycle services 與 LLM proposal config modules。
- [ ] Profile inference tests 顯示 risk hints、unmapped candidates、capability candidates 可作 related refs，但本身不足以成為 detected profiles；relevant insufficient evidence 應為 `undetermined`。
- [ ] `10` 不新增 `profile_registry.toml`。
- [ ] `11-migrate-profile-rule-metadata-to-toml-catalog.md` 存在，並已納入目前 00-14 path，作為將 profile wording/metadata 移到 TOML 的 task。
- [ ] `ProfileInferenceService` 保持 local-only deterministic。
- [ ] Standard mode 完全 deterministic；Phase2 無 AssessmentOrchestrator semantic candidate
  flow（Plan 17 deferred）；未來重啟時該 flow 必須可關閉、
  可重現輸入，且不能新增 canonical facts、status 或數字 `confidence`。
- [ ] 六個產品規格 config/catalog 概念都有唯一 owner，不建立重複 truth。

## 驗證

- [ ] `.venv/bin/pytest tests/unit/core/test_profile_inference_service.py -q`
- [ ] `.venv/bin/pytest tests/unit/core/test_profile_signal_validation_service.py -q`
- [ ] 僅在 future profile catalog 引入時執行 `.venv/bin/pytest tests/unit/core/test_rule_catalog_loader.py -q`。
- [ ] `rg -n "llm_proposal|mapping_proposal.v1|MappingProposalService|ManualMappingService" src/kai_mind/core/services/profile* tests/unit/core/test_profile*` 並確認任何 hit 僅為 intentional boundary-test text，非 runtime dependency。
- [ ] `rg -n "profile_registry" src tests docs` 並確認只有 Plan 11 建立/載入
  registry，且 catalog 不含 executable trigger logic。
- [ ] `git diff --check docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/10-define-profile-rule-catalog-boundary.md`

## 相依關係

- 概念上依賴 `04-separate-profile-inference-from-mapping-proposal.md`。
- 與 `05-add-read-only-system-map-index.md` 對齊；profile rules 可使用 `SystemMapIndex` 做 lookup，但 index 不得擁有 profile decision logic。
- 與 `02-implement-stackable-profile-inference.md` 對齊；本 plan 為較大 implementation 釐清 rule ownership 與 catalog boundaries。
- 後續為 `11-migrate-profile-rule-metadata-to-toml-catalog.md`；2026-07-02 使用者決定納入目前 00-14 path。在 `02` MVP 與本計畫（`10`）實作並測試後，將 hard-coded profile wording/metadata 移到 TOML。

## 不在範圍內

- 不在此實作 full profile inference。
- 不要只因其他 modules 有 TOML catalogs 就新增 TOML catalog。
- 不要將 profile rules 合併進 risk hint catalogs。
- 不要複製 mapping proposal deterministic heuristics 作為 profile detection architecture。
- 不要為 profile detection 新增 external providers、LLM calls 或 provider configuration。

## P0 Execution Mapping 補充（2026-07-03）

Rule ownership 需把 profile rules 與 execution extraction rules 分開：

- Profile rule catalog 判斷 capabilities；call graph / dataflow extraction rules 屬於 dynamic `00`
  的 static execution services。
- TOML metadata 可以描述 profile wording，但不得控制 AST call graph traversal、dataflow thresholds
  或 execution path ordering。
- Profile inference 可以讀 execution artifact summaries 作 supporting evidence，但不能反向要求
  call graph builder 產生特定 profile。
- AssessmentOrchestrator candidate agents 只能處理 bounded fact packets，不能新增 call edges 或 canonical facts。
