# AssessmentOrchestrator Candidate Flow 實作計畫

Status: **deferred**（2026-07-07 同日修訂：Step 6 取消 AI 編排，回歸純 Python 評估；
重啟時另案評估。依據 `phase4-scanner-expansion/00-phase2-pipeline-ascii-map.md` 決策
#2 / #3 / #5 與本資料夾 README staged rollout）

> **執行者注意：** 本計畫 **不在 Phase2 執行範圍**，不阻擋 Plan 14 / 18 / 15。
> Plan 02 `ProfileInferenceService.infer(...)` 保留 optional `validated_candidates`
> 接縫、預設為空；重啟本計畫時不需改動 deterministic 定案邏輯。以下 task 內容
> 保留供未來重啟評估使用。逐 task 實作時使用 checkbox（`- [ ]`）語法以便追蹤。

## 目標

本計畫 deferred，不屬於 Phase2 active path。未來若重啟，才新增 Step 6 專屬 thin
`AssessmentOrchestrator`，把 reserved nullable UA semantic sidecar 轉成 plane/component
candidates，驗證後交給 `ProfileInferenceService`。AI 只產 candidate + reason +
evidence_ids；五態仍由 Python `ProfileInferenceService` 唯一定案。

## 架構

```text
ScanSnapshot.ua_analysis_result.semantic
  -> SemanticCandidateAdapter
       UA path + line -> existing evidence_id
       unresolved / ambiguous -> drop or unresolved
  -> AI candidate agents（workflow 設定可擴充）
       plane/component candidate + reason + evidence_ids
  -> CandidateContractValidator
       evidence_id / node id / boundary / status semantics
  -> ProfileInferenceService.infer(validated_candidates=...)
       五態定案
```

`AssessmentOrchestrator` 不是 pipeline 總控；Step 1～5 / 7～9 仍由既有 Python services 與
`MapBuildService` 負責。

## 依賴

- 依賴 `02-implement-stackable-profile-inference.md`：提供 `ProfileInferenceService`
  validated candidate input contract。
- 依賴 `04-separate-profile-inference-from-mapping-proposal.md`：鎖定 proposal / profile /
  orchestrator 分離。
- 依賴 `16-implement-understand-anything-sidecar-service.md`：未來重啟時才提供
  deferred `ua-analysis-result` semantic sidecar 與 canonical evidence refs。

## Task 1：定義 candidate contract models

**Files**

- Create: `src/kai_mind/core/models/assessment_candidate.py`
- Test: `tests/unit/core/test_assessment_candidate_models.py`

**Steps**

- [ ] 定義 `SemanticAssessmentCandidate`，包含 `candidate_id`、`target_kind`、
  `reference_node_id` 或 `canonical_component_type`、`reason`、`evidence_ids`、`source`。
- [ ] `source` 至少支援 `ua_semantic_candidate` 與 future workflow agent names。
- [ ] 禁止 `confidence`、raw source snippet、absolute path、unknown fields。
- [ ] Candidate 本身不得包含五態 status；最多有 `suggested_relationship` 或
  `candidate_kind`。

## Task 2：實作 `SemanticCandidateAdapter`

**Files**

- Create: `src/kai_mind/core/services/semantic_candidate_adapter.py`
- Test: `tests/unit/core/test_semantic_candidate_adapter.py`

**Steps**

- [ ] 讀取 `ua-analysis-result.semantic.nodes[] / edges[]`。
- [ ] 以 UA semantic node/edge 的 project-relative path + line range 對回 Step 3 已建立的
  canonical `evidence_id`。
- [ ] 找到唯一 evidence 才產 candidate input；找不到或多筆對應時標記 unresolved 或丟棄。
- [ ] Adapter 不得臨時產生新的可信 evidence，也不得把 summary 當 evidence。
- [ ] Boundary 外檔案、unknown path、缺 line range、缺 evidence 的 candidate 必須被拒絕。

## Task 3：新增 workflow 設定檔

**Files**

- Create: `src/kai_mind/core/rules/assessment_orchestrator_workflow.toml`
- Create: `src/kai_mind/core/services/assessment_workflow_loader.py`
- Test: `tests/unit/core/test_assessment_workflow_loader.py`

**Steps**

- [ ] Workflow TOML 僅保存 metadata：agent id、prompt version、enabled flag、
  input schema version、output schema version。
- [ ] Loader reject executable fields，例如 `condition`、`threshold`、`status_weight`、
  `mapping_type`、`accept_action`、`provider_secret`。
- [ ] Missing required agent metadata fail closed。
- [ ] Workflow 設定不得決定五態或寫 canonical facts。

## Task 4：實作 candidate agents interface

**Files**

- Create: `src/kai_mind/core/services/assessment_candidate_agent.py`
- Modify: `src/kai_mind/core/configs/llm_proposal.toml`（只有必要時新增共用 provider note）
- Test: `tests/unit/core/test_assessment_candidate_agent.py`

**Steps**

- [ ] 定義窄介面：`propose(packet) -> list[SemanticAssessmentCandidate]`。
- [ ] 可重用 Task 20 的 LLM provider 管線模式：`llm_proposal.toml` loading pattern、
  explicit opt-in、`NvidiaNimProposalProvider` error handling 與 timeout/redaction 思路。
- [ ] 可重用 `MappingEvidencePacketBuilder` 的 bounded masked context 打包模式，但不得
  import proposal lifecycle 或建立 `MappingProposal`。
- [ ] Agent output 只能是 candidate + reason + evidence_ids，不含 canonical map patch。

## Task 5：實作 `CandidateContractValidator`

**Files**

- Create: `src/kai_mind/core/services/candidate_contract_validator.py`
- Test: `tests/unit/core/test_candidate_contract_validator.py`

**Steps**

- [ ] `evidence_id` 必須存在於 current canonical map / index。
- [ ] `reference_node_id` 必須存在於 10 planes / 52 nodes catalog。
- [ ] `canonical_component_type` 必須在 approved taxonomy / bridge output set。
- [ ] 指向 boundary 外檔案、unknown evidence、unknown node id 的 candidate 拒絕。
- [ ] 無 evidence 的 detected/partial 建議拒絕；candidate 不得要求 status。
- [ ] AI 不得新增 canonical component、edge、evidence、risk hint 或 mapping decision。
- [ ] semantic-only candidate 最多支撐 `partial` / `undetermined`；`detected` 仍需 direct evidence
  由 `ProfileInferenceService` 檢查。

## Task 6：實作 `AssessmentOrchestrator`

**Files**

- Create: `src/kai_mind/core/services/assessment_orchestrator.py`
- Modify: `src/kai_mind/core/services/map_build_service.py`
- Test: `tests/unit/core/test_assessment_orchestrator.py`
- Test: `tests/integration/test_map_build_service.py`

**Steps**

- [ ] `AssessmentOrchestrator.run(system_map, index, ua_sidecar, workflow)` 回傳
  `ValidatedAssessmentCandidates`。
- [ ] Orchestrator 預設可在無 reserved nullable semantic sidecar 時回 empty candidate set + warning，但不得
  在 build-time profile validation 無聲降級成成功 detected。
- [ ] `MapBuildService` 只在 Step 6 呼叫 orchestrator；Step 1～5 / 7～9 不接 AI orchestration。
- [ ] Orchestrator 不寫 artifact、不更新 latest、不呼叫 `MappingProposalService`、
  不呼叫 `ManualMappingService`。
- [ ] `ProfileInferenceService` 接收同一 build 的 validated candidates 並定案五態。

## Task 7：邊界與 dependency guardrails

**Files**

- Create: `tests/unit/core/test_assessment_orchestrator_boundaries.py`
- Modify: `04-separate-profile-inference-from-mapping-proposal.md`（若實作發現需補文件）

**Steps**

- [ ] Source test 確認 `assessment_orchestrator.py` 不 import web routes、mapping proposal routes、
  manual mapping repository 或 artifact writer。
- [ ] Source test 確認 `ProfileInferenceService` 不 import `AssessmentOrchestrator`，避免反向依賴。
- [ ] Contract test 確認 candidate agents 無法產生 `confidence` 或 canonical patch fields。
- [ ] Integration test 覆蓋 UA semantic unresolved candidate 被丟棄，build 仍使用 deterministic facts。

## Acceptance Criteria

- [ ] `AssessmentOrchestrator` 是 Step 6 專屬 thin orchestrator，不是 pipeline 總控。
- [ ] `SemanticCandidateAdapter` 只能引用既有 evidence id；無唯一對應時不升格。
- [ ] Candidate agents 可由 workflow metadata 擴充，但 output contract 固定且 bounded。
- [ ] `CandidateContractValidator` 擋 unknown evidence、unknown reference node、boundary escape、
  無 evidence 的 detected/partial 建議與 canonical patch。
- [ ] `ProfileInferenceService` 是五態唯一 owner；AI candidate 不得直接設定 status。
- [ ] `MappingProposalService` 保留 Step 9；AssessmentOrchestrator 不觸發 proposal。

## 邊界 / 不做事項

- 不新增 profile-level accept/edit/reject action。
- 不將 UA semantic graph 寫入 `ai_system_map.json`。
- 不讓 workflow TOML 成為 scoring / threshold / status DSL。
- 不重寫 Task 20 mapping proposal 子系統；只重用 provider/config/packet 的安全模式。
- 不在 Apply 時重跑 candidate agents；Apply 使用同 `scan_id` 的
  `ScanSnapshot.scan_result` replay；semantic sidecar slot 保持 nullable 且不消費。
