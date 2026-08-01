# 重構 Review Scanner Suggestions 與 Non-Baseline Capability Decisions 實作計畫

> **2026-07-11 backend execution status：** capability candidate、durable mapping
> decisions、proposal conversion、legacy compatibility 與 evidence review state 已完成並
> 測試。依使用者 backend-only 邊界，frontend copy／互動未實作；完成證據見
> `docs/work/Timmy/schedule/report/2026-07-11-phase2-s1-pipeline-core-REP.md`。

> **執行者注意：** 逐 task 實作本計畫。步驟使用 checkbox（`- [ ]`）語法以便追蹤。

**目標：** 將「confirm as extension」改成 generic component mapping 或 confirmed
non-baseline capability candidate，供 canonical v2 build 與 capability inference
使用；v1 extension path 只保留 compatibility。

**架構：** User-facing UI 名稱改為 **Review scanner suggestions**
（中文：**檢查 scanner 建議**）。`ManualMappingService` / `manual_mapping` 仍是
durable user decision lifecycle 的內部名稱——產品 copy 與 domain 內部名刻意分離：
UI 強調「複核 scanner 建議」，service 名強調「誰擁有可持久化決策」。

使用者對 ambiguous evidence 只有三條正式出路（另可 skip / needs more information）：

1. 對應到 **generic canonical component type/layer**（結構層，可進 map）
2. 對應到 **conditional grounding dimension**（僅在 grounding applicable 時）
3. 確認為 **`non_baseline_capability_candidate`**（確認有訊號，但**不是** map 拓樸節點；交給 capability / profile 路徑）

新的正式命名不含 `rag_variant`；舊 `new_extension_component` 與舊 candidate
aliases 僅供 v1 records 讀取，新 API / 新 proposal **不得**再 emit。

Candidate 本身不是 `detected` capability/profile，也不直接寫入 canonical map；
它必須先經 Plan 01A reference-node mapping 與 Plan 02 evidence assessment。

**Tech Stack：** Python 3.11、Pydantic v2、FastAPI routes、pytest，以及現有的 `ComponentDetectionService`、`ManualMappingService`、`MappingProposalService`、`MapBuildService`。

## 2026-07-10 Glossary：`non_baseline` 不是「還在用 rag-core-v1 baseline」

本計畫契約字串仍使用 `non_baseline_capability_candidate`（相容與實作穩定），但
**產品語意必須依下表解讀**，避免把「已退役的 RAG baseline」與「map 結構層」混為一談：

| 用語 | 意思 | 不是什麼 |
|---|---|---|
| **UI：Review scanner suggestions / 檢查 scanner 建議** | Scanner 已掃過；使用者只複核 high-impact 模糊項 | 不是「請使用者從頭畫架構 / Manual Mapping 產品名」 |
| **Internal：`manual_mapping` / `ManualMappingService`** | Durable user decision lifecycle 的技術擁有者 | 不是主要 UI 文案 |
| **結構層 / map component（舊口語常叫 baseline component）** | 會進 canonical system map 的 generic component（或過渡期 legacy v1 slot） | 不是「產品仍以 `rag-core-v1` 當分類器」 |
| **`non_baseline_capability_candidate`** | 使用者確認「這是真實訊號」，但**不屬於** canonical map 拓樸／grounding component；只當 capability overlay 輸入 | 不是 `detected` profile；不是 extension；不是 `rag_variant`；**不是**「我們還有一套 RAG baseline 產品」 |
| **`rag-core-v1` baseline / hard slots** | Legacy-only template（Plan 00 凍結）；migration / compatibility input | Active product verdict、readiness lens、frontend summary |

白話對照：

```text
non_baseline_capability_candidate
  ≈ 「非 map 結構層的能力候選」
  ≠ 「還在用舊 RAG baseline，這是 baseline 外的變體」
```

較貼近現在產品、但**本計畫不改契約字串**的同義說法（僅文件／對內溝通用）：
`non_map_capability_candidate`、`capability_overlay_candidate`、
`confirmed_capability_signal`（仍不是 `detected`）。

決策分流（Phase2 active）：

```text
ambiguous evidence
  -> 對到 generic component type/layer     # 進 canonical map（結構層）
  -> 對到 conditional grounding dimension  # grounding applicable 時
  -> non_baseline_capability_candidate     # 不進 map；給 Plan 02
  -> needs more information / skip
```

所有權邊界：

```text
Plan 01（本計畫）  人怎麼確認、怎麼持久化 decision
Plan 01A           對到哪個 reference node（能力地圖節點）
Plan 02            evidence assessment → 五態 / profile（才可能 detected）
Plan 03A           Apply / build lineage（不得在 proposal route 內重做）
```

## Contract source of truth

| 主題 | Source |
|---|---|
| HTTP 端點與 payload | `docs/API-GUIDE.md` §5 Manual Mappings、§6 Mapping Proposals |
| `ManualMappingType` / candidate 欄位 | `docs/MODEL-CONTRACT.md` Manual Mapping & Proposal contract |
| Apply 後 materialize 新 `build_id` | `03A-implement-apply-build-lineage-and-local-json-persistence.md`；`POST /api/map-builds/{base_build_id}/apply` |
| JSON 範例 | `docs/work/Timmy/design/EPIC1/frontend-json-handoff/step-09-review-apply/` |

本計畫擁有 durable decision lifecycle；**不得**在 proposal route 內實作 build lineage 或
直接 patch `ai_system_map.json`。

---

## 執行摘要

### 目標

把「建立 extension」改成三個明確結果：對應 generic component taxonomy（結構層）、
對應 grounding dimension，或確認為 non-baseline capability candidate（非 map 結構層
的能力候選，見上方 glossary）。

### 背景

現行 router/reranker proposal 會直接走 `NEW_EXTENSION`，使使用者確認、canonical map
與後續 capability inference 混成同一個產品概念。Phase2 要拆成：durable decision ≠
map materialization ≠ capability assessment。

### 目前 code 狀態

`mapping.py`、`MappingProposalService`、`ManualMappingService`、`ComponentDetectionService` 與 proposal routes 都以 extension-first contract 運作；frontend `types.ts` 仍只接受 `existing_slot` / `new_extension`。UI copy 目前也容易讓使用者把 review 誤解為 scanner 尚未完成判斷。

### 相關檔案

- `src/systograph/core/models/mapping.py`
- `src/systograph/core/services/mapping_proposal_service.py`
- `src/systograph/core/services/manual_mapping_service.py`
- `src/systograph/core/services/component_detection_service.py`
- `src/systograph/web/routes/mapping_proposal_routes.py`
- `frontend/src/types.ts`
- `frontend/src/components/proposal/ProposalModal.tsx`

### 實作步驟

先新增 typed candidate/decision contract 與 tests，再 materialize confirmed decisions、停止建立新 extension candidates、更新 route/API/frontend parsing，最後驗證 backward compatibility。

### 驗收標準

新 proposal 不再要求建立 extension；confirmed non-baseline decision 可穩定重播並輸入
profile inference（仍不是直接 `detected`）；舊 `new_extension_component` records 仍可讀。

### 風險與注意事項

- 不得把 `capability_candidate` / `non_baseline_capability_candidate` 解讀成互斥 RAG
  類型、`rag_variant`、或 canonical topology 節點。
- 不得把契約字串裡的 `non_baseline` 解讀成「產品仍以 `rag-core-v1` 當 baseline」；
  見 **2026-07-10 Glossary**。
- Durable source of truth 仍是 manual decision lifecycle；sidecar 只是 build
  materialization，canonical component/edge 必須另有 deterministic evidence。
- Frontend 不得用 review state（Confirmed / Skipped）推導 capability 五態。

## 2026-07-03 Generic AI System 對齊

本節覆蓋本文任何仍以「legacy v1 slot / 非 v1 slot」作為唯一二分法
的舊例子。**Active 二分法**是「是否屬於 canonical map 結構／grounding component」，
不是「是否屬於 `rag-core-v1` slot」：

```text
ambiguous evidence
  -> generic component mapping              # map 結構層
  -> optional grounding-dimension mapping
  -> non-baseline capability candidate      # 非 map 結構層；能力 overlay 輸入
  -> needs more information / skip
```

正式 target contract（字串穩定；語意見 glossary）：

```text
ManualMappingType.NON_BASELINE_CAPABILITY_CANDIDATE
value = "non_baseline_capability_candidate"
# 讀作：non-map / capability-overlay candidate；不是「RAG baseline 外變體」
```

舊 variant-candidate enum/value 若已存在於外部 records，只能由 compatibility parser
轉成新名稱，不得繼續由新 API emit。

Generic mapping 至少支援 component taxonomy layers：input、knowledge、retrieval、
context、control、generation、ops。Profile inference 只 consume confirmed candidate
與 validated facts；**candidate confirmation 不等於 profile `detected`**。

## 2026-07-04 UI 命名邊界

本計畫不得把 **Manual Mapping** 當作主要使用者可見名稱，避免使用者誤解成 scanner
沒有完成工作、必須靠人工重新判斷。語意對照見 **2026-07-10 Glossary**。

| Surface | Name |
|---|---|
| Main UI / CTA / modal title | `Review scanner suggestions` |
| 中文 UI | `檢查 scanner 建議` |
| High-impact badge | `Needs review` |
| Low-impact ambiguous badge | `Unclear` |
| Accepted decision | `Confirmed` |
| Skipped decision | `Skipped` |
| Internal persisted lifecycle | `manual_mapping` / `ManualMappingService` |
| Candidate action（契約 label 可保留） | `Mark as non-baseline capability` |
| Candidate action helper（必備白話） | 「確認這是能力訊號，但不是系統底圖上的結構元件」 |

Review lifecycle copy（不要與五態 assessment 混用）：

- `Detected`：scanner 已有足夠 evidence 自動定案。
- `Not detected`：scanner 沒看到該能力或 readiness evidence。
- `Unclear`：evidence 模糊但不需要使用者立刻處理；保留在 details /
  `evidence_table.json`。
- `Needs review`：high-impact ambiguous item，會影響 map、readiness、profile 或
  execution path。
- `Confirmed`：使用者已確認 scanner suggestion 或 mapping decision。
- `Skipped`：使用者略過，scanner 保留原本自動結果與 warning。

Capability assessment copy 由 backend projection 統一提供：`已確認 / 部分確認 /
無法判斷 / 未偵測到 / 證據衝突`。Frontend 不得由 review state 推導
`detected / partial / undetermined / not_detected / conflicted`。

## 2026-07-06 Pipeline Bridge Alignment

本計畫承接 Step 4 產出的 `unmapped_components[]` / non-baseline candidate input，
但不擁有 Step 4 的 raw fact matching table。`rule_id + evidence` 的 deterministic
component bridge 由 `01B-extract-step4-component-bridge-registry.md` 的
`component_bridge_registry.py` 擁有。

```text
Step 4-1 component bridge（Plan 01B）
  -> component candidate                 # 直接進 canonical map
  -> unmapped needs_review               # Review scanner suggestions 的候標
  -> non-baseline capability input       # 不寫 canonical map

Step 9 review（本計畫 + Plan 03A）
  -> MappingProposalService 產 pending candidates
  -> 使用者 accept / edit / reject / skip
  -> ManualMappingService 持久化 confirmed decision
  -> Apply 同 snapshot replay Step 4～7，建立新 build_id
```

Plan 01 的重點是 **proposal / manual decision lifecycle** 與 confirmed
`non_baseline_capability_candidate` 的 durable contract。它不得把 Step 4 registry
改成 proposal generator，也不得讓 proposal 直接設定 Step 6 profile status。

## 2026-07-07 UA 整合對齊

本計畫的 capability candidate 與 manual decision 語意不變。同日修訂後 Step 6 **無 AI
編排**：Plan 17 `AssessmentOrchestrator` deferred，UA semantic sidecar 是 reserved nullable slot，
Phase2 active path 不產生、不消費（未來重啟時才會經 adapter、AI candidate agents 與 validator 產出 validated
candidates）。本計畫仍只擁有使用者觸發的
Step 9 proposal / manual mapping lifecycle，不直接消費或寫入 `ua-analysis-result`。

## Legacy v1 compatibility slots

本文凡提到舊的 **RAG slot**、**legacy slot**，
或 `EXISTING_SLOT` 的對應目標，
皆指 legacy `rag-core-v1` template。它只作 migration / compatibility input，不是產品分類器、readiness lens
或 frontend summary。

### Legacy v1 slots

```text
Indexing flow
  data_sources
    -> document_loader
    -> chunking
    -> embedding_model
    -> vector_store

Query-answer flow
  app_api_or_orchestrator
    -> retriever
    -> vector_store          # shared with indexing
    -> prompt_builder
    -> llm
    -> citation_or_response_composer
```

對應 `ManualMappingType.EXISTING_SLOT`：使用者確認 ambiguous evidence **屬於上述
某一格** 時，才寫入 `components_by_slot` / canonical map。

注意：`citation_or_response_composer` 是 v1 compatibility slot，用於保留 response
synthesis / composer 類 evidence；它不代表 citation / source mapping 是 active
product hard requirement。來源可追溯性另由 readiness finding 表達。

### 不屬於 map 結構層的 evidence（改走 capability candidate）

Phase2 不再把 legacy v1 slot completeness 當作 active product verdict。舊 template
中不適合成為 generic component（map 結構層）的 evidence，應改走 capability candidate
或保留為 unmapped evidence——**即使歷史上它們曾掛在某個 v1 slot id 上**。

下表的 Slot id 只是 **legacy 對照**（migration 時可能還看得到），不是 active 產品分類：

| Legacy slot id（對照用） | 典型例子 | 本計畫處置 |
|---|---|---|
| `query_processing` | query rewrite、router、filter | 確認後 → `non_baseline_capability_candidate`（不進 map） |
| `guardrails` | safety / policy / output filter | 同上 |
| `observability` | trace、metrics、eval hook | 同上 |

scanner 若看到 reranker、router 等類似訊號，**不得**再自動建成 `ExtensionComponent`；
應留在 unmapped / capability candidate 路徑，等使用者確認後由 Plan 02 做 evidence
assessment。確認 ≠ `detected`；也不等於寫入 canonical map。

### 與 extension 的關係（分階段退役）

| 階段 | extension 狀態 |
|---|---|
| **Plan 01（本計畫）** | 停止新建 extension proposal；舊 `new_extension_component` records 仍可讀 |
| **Plan 00A～12** | 舊 extension 經 adapter 轉成 v2 `legacy_extension` compatibility metadata |
| **Plan 13** | active output 不再建立 top-level `extensions`；`NEW_EXTENSION` 僅限 v1 reader / fixture |

本計畫的 `capability_candidate_components` **不寫入** `ai_system_map.json`；由 Plan
`02-implement-stackable-profile-inference.md` 消費並 materialize 到
`profile_signals.json`。

### 前置依賴與目前 code 差距

- **前置：** Plan `00` 完成後，`rag-core-v1.json` 被視為 legacy-only template；
  Plan `00A` 提供 generic v2 normalized view。本計畫在 v1/v2 過渡期仍可運作，
  但 legacy slot 不再是長期 product contract。
- **目前 code（2026-07-03）：** `src/systograph/core/templates/rag-core-v1.json` 仍為
  `1.0.0`、13 slots；implementation 完成 Plan 00 前，tests 可能仍引用含
  `query_processing` / `guardrails` / `observability` 的 legacy flow order。

## Code Trace 摘要

目前程式碼對 non-baseline decisions 採 extension-first 做法：

- `ManualMappingType.NEW_EXTENSION = "new_extension_component"` 定義於 `src/systograph/core/models/mapping.py`。
- `ManualMappingCreate` 持有 `extension_id`、`extension_name`、`extension_kind`、`extension_edges`。
- `MappingCandidateType.NEW_EXTENSION` 與 `MappingCandidate` 持有 `proposed_extension_id`、`proposed_extension_name`、`proposed_extension_kind`。
- `MappingProposalService._deterministic_candidates()` 將 router / reranker candidates 輸出為 `NEW_EXTENSION`。
- `MappingProposalService._candidate_to_manual_mapping()` 將被接受的 `NEW_EXTENSION` candidates 轉成 `ManualMappingType.NEW_EXTENSION`。
- `ManualMappingService.apply()` 遇到 `NEW_EXTENSION` 時呼叫 `_apply_extension()`，將 confirmed `ExtensionComponent` 寫入 `ComponentDetectionResult.extensions`。
- `ComponentDetectionService._extension_candidate()` 將 reranker-like static evidence 直接輸出為 `ExtensionComponent(status="candidate")`。
- `mapping_proposal_routes.py` 將 `system_map.extensions` 的 `available_extensions` 傳入 `MappingEvidencePacket`。
- `ViewerSessionService._GraphNodeBuilder` 將 `system_map.extensions` 渲染為 graph nodes。
- 現有 integration tests 斷言 confirmed extension mappings 會 replay 到 `result.extensions`。
- `SystemMapNormalizeService` 僅將 `components.extensions` 與 `components.unmapped_components` 寫入 canonical `RagSystemMap`；本計畫不得將 `capability_candidate_components` 加入 `ai-system-map/v1`。
- `FlowDerivationService`、`EndpointDetectionService`、`RiskHintService` 接受 `ComponentDetectionResult`，但本計畫不需要它們理解 capability candidates。
- 多個 tests 直接 instantiate `ComponentDetectionResult`。新欄位必須以 dataclass `default_factory` 保持 backward-compatible，而非強制每個舊 fixture 都傳 `capability_candidate_components=[]`。

這與新的 Phase2 product flow 衝突：

```text
unmapped / ambiguous component
  -> user confirms:
       (a) maps to generic component type/layer
           （過渡期亦可對到 legacy v1 slot → existing_slot_mapping）
       (b) maps to conditional grounding dimension（若 applicable）
       (c) is NOT a map topology/grounding component
           → non_baseline_capability_candidate
  -> Plan 01 只持久化 decision；不寫 canonical map topology
  -> Plan 01A / Plan 02 之後才做 reference-node mapping 與五態 assessment
  -> profile inference 才可能得到 detected / partial / undetermined /
     not_detected / conflicted（確認本身 ≠ detected）
```

目前受影響的 backend call flow：

```text
MapBuildService._detect_components(...)
  -> ComponentDetectionService.detect(...)
       -> _component_candidates(...)      # known legacy v1 slot / generic component
       -> _extension_candidate(...)       # reranker currently becomes extension
       -> _unmapped_candidate(...)        # router / weak signals need confirmation
       -> ManualMappingService.apply(...)
            -> EXISTING_SLOT  -> _apply_existing_slot(...)
            -> NEW_EXTENSION  -> _apply_extension(...)
  -> SystemMapNormalizeService.build(...)
       -> RagSystemMap.extensions
       -> RagSystemMap.unmapped_components
  -> ViewerSessionService._GraphNodeBuilder
       -> extension graph nodes
       -> unmapped graph nodes

POST /api/mapping-proposals
  -> MappingEvidencePacketBuilder.build(...)
       -> available_slots
       -> available_extensions            # legacy compatibility metadata
  -> MappingProposalService.create_proposal(...)
       -> _deterministic_candidates(...)
            -> router/reranker currently emit NEW_EXTENSION
  -> MappingProposalService.decide(...)
       -> _candidate_to_manual_mapping(...)
            -> NEW_EXTENSION becomes ManualMappingType.NEW_EXTENSION
```

目標受影響的 backend call flow：

```text
ComponentDetectionService.detect(...)
  -> known legacy v1 facts still map into components_by_slot during migration
  -> reranker/router-like non-baseline facts stay unmapped until confirmation
  -> ManualMappingService.apply(...)
       -> EXISTING_SLOT maps into legacy v1 slot
       -> NON_BASELINE_CAPABILITY_CANDIDATE materializes CapabilityCandidateComponent
       -> legacy NEW_EXTENSION remains readable only for compatibility

ProfileInferenceService.infer(...)
  -> consumes capability_candidate_components
  -> emits profile_signals.json
  -> does not mutate ai_system_map.json
```

## 設計決策

新的 durable decision type：

```text
ManualMappingType.NON_BASELINE_CAPABILITY_CANDIDATE
value = "non_baseline_capability_candidate"
# 語意：非 map 結構層的能力候選（見 2026-07-10 Glossary）
# 本計畫不 rename 契約字串；文件／UI 說明必須帶白話對照
```

新的 proposal candidate type：

```text
MappingCandidateType.NON_BASELINE_CAPABILITY_CANDIDATE
value = "non_baseline_capability_candidate"
```

新的內部 materialized component：

```text
CapabilityCandidateComponent
status = "confirmed_non_baseline"   # confirmed decision materialization，不是五態 detected
```

這不會寫入 `ai_system_map.json`。它由 `ComponentDetectionResult` 攜帶，之後由
`02-implement-stackable-profile-inference.md` 的 `ProfileInferenceService` 寫入
`profile_signals.json.capability_candidate_components`。

分層契約（不得混成一步）：

| 層 | 產出 | 擁有者 |
|---|---|---|
| Durable decision | confirmed / rejected / skip mapping record | Plan 01 / `ManualMappingService` |
| Map topology | `components[]` / `edges[]`（需 deterministic evidence） | Step 4 bridge + normalize；generic mapping 才進 |
| Capability overlay input | `capability_candidate_components` | Plan 01 materialize → Plan 02 consume |
| Assessment 五態 / profile | `detected` / `partial` / … | Plan 01A + Plan 02；**不是** Plan 01 按確認就寫 |

Legacy 行為：

- 保留 `NEW_EXTENSION` models 與 service path，供舊 API clients / 舊 tests / 舊 artifacts 使用。
- 不再以 `NEW_EXTENSION` 輸出新的 deterministic proposal candidates。
- Phase2 non-baseline decisions 不要求 frontend 建立 extensions。

## 需修改的檔案

- `src/systograph/core/models/capability_candidate.py`
  - 新增 non-canonical Pydantic model，用於 materialized confirmed non-baseline candidates。
- `src/systograph/core/models/mapping.py`
  - 新增 mapping/candidate type 與 capability candidate fields。
- `src/systograph/core/services/component_detection_service.py`
  - 在 `ComponentDetectionResult` 新增 `capability_candidate_components`。
  - 停止將新的 reranker evidence 輸出為 `ExtensionComponent(candidate)`；改輸出 unmapped / non-baseline candidate 待確認。
- `src/systograph/core/services/manual_mapping_service.py`
  - 驗證並持久化 `NON_BASELINE_CAPABILITY_CANDIDATE`。
  - 將 confirmed non-baseline decisions apply 到 `ComponentDetectionResult.capability_candidate_components`。
  - 保留 legacy `NEW_EXTENSION`。
- `src/systograph/core/services/mapping_proposal_service.py`
  - 對 router/reranker evidence 輸出 non-baseline capability candidates，而非 new extension candidates。
  - 將被接受的 non-baseline candidates 轉換為新的 manual mapping type。
- `src/systograph/core/services/mapping_evidence_packet_builder.py`
  - 僅將 legacy `available_extensions` 保留為 compatibility metadata。
- `src/systograph/web/routes/mapping_proposal_routes.py`
  - 停止將現有 `system_map.extensions` 視為 preferred proposal target set。
- `src/systograph/web/schemas.py`
  - 若 web schemas 需要，re-export 新 model types。
- `tests/unit/core/test_component_detection_service.py`
  - 將 reranker expectation 從 extension candidate 改為 unmapped confirmation candidate。
- `tests/unit/core/test_mapping_proposal_service.py`
  - 更新 deterministic router/reranker proposal 與 accept-path assertions。
- `tests/web/test_mapping_proposal_routes.py`
  - 更新 API candidate payload assertions。
- 下方列出的 tests。

## 不在範圍內

- 不移除 `ai-system-map/v1` 中的 `ExtensionComponent`。
- 不刪除 `ManualMappingType.NEW_EXTENSION`。
- 全面移除 legacy extension contract 屬於後續 breaking migration，已拆到 `13-retire-legacy-extension-contract.md`；它在 0～14 內只作 compatibility boundary，不是 `01` 的 blocker。
- 不在此實作 profile inference rules；那屬於 `02-implement-stackable-profile-inference.md`。
- 不重設整套 frontend UX；但本計畫必須同步 `frontend/src/types.ts`、proposal API parsing 與現有 modal 的 candidate type，避免 backend contract 已變更而 frontend 無法讀取。Meeting-Sync 文件只作補充紀錄。
- 不將 capability candidates 寫入 canonical `ai_system_map.json`。

## Task 1：新增 Capability Candidate Model 與 Mapping Contract

**檔案：**

- Create: `src/systograph/core/models/capability_candidate.py`
- Modify: `src/systograph/core/models/mapping.py`
- Test: `tests/unit/core/test_manual_mapping_service.py`
- Create: `tests/unit/core/test_mapping_models.py`

- [ ] **Step 1：撰寫 failing model tests**

建立 `tests/unit/core/test_mapping_models.py`：

```python
from __future__ import annotations

import pytest
from pydantic import ValidationError

from systograph.core.models.mapping import (
    MappingCandidate,
    MappingCandidateType,
    ManualMappingCreate,
    ManualMappingDecision,
    ManualMappingType,
)


def test_non_baseline_manual_mapping_accepts_capability_candidate_fields() -> None:
    mapping = ManualMappingCreate(
        project_id="project:demo",
        mapping_type=ManualMappingType.NON_BASELINE_CAPABILITY_CANDIDATE,
        decision=ManualMappingDecision.CONFIRMED,
        source_unmapped_id="unmapped:router",
        source_file="src/router.py",
        observed_kind="routing_orchestration",
        evidence_ids=["evidence:router"],
        capability_candidate_id="capability-candidate:router",
        capability_candidate_name="Query Router",
        capability_candidate_kind="routing_orchestration",
    )

    assert mapping.mapping_type == ManualMappingType.NON_BASELINE_CAPABILITY_CANDIDATE
    assert mapping.capability_candidate_id == "capability-candidate:router"


def test_non_baseline_manual_mapping_rejects_target_slot_and_extension_fields() -> None:
    with pytest.raises(ValidationError, match="must not include target_slot"):
        ManualMappingCreate(
            project_id="project:demo",
            mapping_type=ManualMappingType.NON_BASELINE_CAPABILITY_CANDIDATE,
            decision=ManualMappingDecision.CONFIRMED,
            source_unmapped_id="unmapped:router",
            evidence_ids=["evidence:router"],
            target_slot="retriever",
            capability_candidate_id="capability-candidate:router",
            capability_candidate_name="Query Router",
            capability_candidate_kind="routing_orchestration",
        )

    with pytest.raises(ValidationError, match="must not include extension fields"):
        ManualMappingCreate(
            project_id="project:demo",
            mapping_type=ManualMappingType.NON_BASELINE_CAPABILITY_CANDIDATE,
            decision=ManualMappingDecision.CONFIRMED,
            source_unmapped_id="unmapped:router",
            evidence_ids=["evidence:router"],
            extension_id="extension:router",
            capability_candidate_id="capability-candidate:router",
            capability_candidate_name="Query Router",
            capability_candidate_kind="routing_orchestration",
        )


def test_non_baseline_mapping_candidate_requires_variant_fields() -> None:
    candidate = MappingCandidate(
        candidate_type=MappingCandidateType.NON_BASELINE_CAPABILITY_CANDIDATE,
        proposed_capability_candidate_id="capability-candidate:reranker",
        proposed_capability_candidate_name="Reranker",
        proposed_capability_candidate_kind="reranker",
        label="Mark as non-baseline capability candidate",
        rationale=(
            "Reranker-like evidence is not a canonical map topology/grounding "
            "component; confirm as capability overlay candidate (not detected)."
        ),
        evidence_ids=["evidence:reranker"],
        rank=1,
        recommendation_level="plausible_candidate",
        uncertainty_reason="Static evidence only.",
    )

    assert (
        candidate.candidate_type
        == MappingCandidateType.NON_BASELINE_CAPABILITY_CANDIDATE
    )
```

- [ ] **Step 2：執行 model tests 並確認失敗**

執行：

```bash
.venv/bin/pytest tests/unit/core/test_mapping_models.py -q
```

預期：失敗，因為 `NON_BASELINE_CAPABILITY_CANDIDATE` 與 capability candidate fields 尚不存在。

- [ ] **Step 3：新增 `CapabilityCandidateComponent`**

建立 `src/systograph/core/models/capability_candidate.py`：

```python
"""Non-canonical capability candidate models for Phase2 profile inference."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CapabilityCandidateModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CapabilityCandidateComponent(CapabilityCandidateModel):
    id: str
    name: str | None = None
    observed_kind: str
    status: Literal["confirmed_non_baseline"] = "confirmed_non_baseline"
    evidence_ids: list[str] = Field(default_factory=list)
    source_unmapped_component_id: str | None = None
    source_file: str | None = None
    proposal_id: str | None = None
    decision_source: str | None = None
```

- [ ] **Step 4：擴充 mapping models**

修改 `src/systograph/core/models/mapping.py`：

```python
class ManualMappingType(StrEnum):
    EXISTING_SLOT = "existing_slot_mapping"
    NEW_EXTENSION = "new_extension_component"
    NON_BASELINE_CAPABILITY_CANDIDATE = "non_baseline_capability_candidate"
```

在 `ManualMappingCreate` 新增 fields：

```python
capability_candidate_id: str | None = None
capability_candidate_name: str | None = None
capability_candidate_kind: str | None = None
```

在 `ManualMappingUpdate` 新增 fields，使 proposal edit 能建立與 proposal accept 相同的 mapping shape：

```python
capability_candidate_id: str | None = None
capability_candidate_name: str | None = None
capability_candidate_kind: str | None = None
```

在 `ManualMappingCreate` 新增 shape validation：

```python
@model_validator(mode="after")
def validate_manual_mapping_shape(self) -> "ManualMappingCreate":
    if self.mapping_type == ManualMappingType.NON_BASELINE_CAPABILITY_CANDIDATE:
        if self.target_slot is not None:
            raise ValueError(
                "non_baseline_capability_candidate must not include target_slot"
            )
        if (
            self.extension_id is not None
            or self.extension_name is not None
            or self.extension_kind is not None
            or self.extension_edges
        ):
            raise ValueError(
                "non_baseline_capability_candidate must not include extension fields"
            )
        if (
            self.capability_candidate_id is None
            or self.capability_candidate_name is None
            or self.capability_candidate_kind is None
        ):
            raise ValueError(
                "non_baseline_capability_candidate requires capability candidate fields"
            )
    elif (
        self.capability_candidate_id is not None
        or self.capability_candidate_name is not None
        or self.capability_candidate_kind is not None
    ):
        raise ValueError(
            f"{self.mapping_type.value} must not include capability candidate fields"
        )
    return self
```

擴充 `MappingCandidateType`：

```python
class MappingCandidateType(StrEnum):
    EXISTING_SLOT = "existing_slot_mapping"
    NEW_EXTENSION = "new_extension_component"
    NON_BASELINE_CAPABILITY_CANDIDATE = "non_baseline_capability_candidate"
    NEEDS_MORE_INFORMATION = "needs_more_information"
    SKIP_FOR_NOW = "skip_for_now"
```

在 `MappingCandidate` 新增 fields：

```python
proposed_capability_candidate_id: str | None = Field(
    default=None,
    max_length=MAX_MAPPING_REF_CHARS,
)
proposed_capability_candidate_name: str | None = Field(
    default=None,
    max_length=MAX_COMPONENT_NAME_CHARS,
)
proposed_capability_candidate_kind: str | None = Field(
    default=None,
    max_length=MAX_COMPONENT_KIND_CHARS,
)
```

在 validators 中，對 `NON_BASELINE_CAPABILITY_CANDIDATE` 要求 capability candidate fields、拒絕 `target_slot`、拒絕 extension fields，並對無關 candidate types 拒絕 capability candidate fields。

- [ ] **Step 5：執行 model tests**

執行：

```bash
.venv/bin/pytest tests/unit/core/test_mapping_models.py -q
```

預期：通過。

## Task 2：Materialize Confirmed Non-Baseline Decisions，且不寫入 Extensions

**檔案：**

- Modify: `src/systograph/core/services/component_detection_service.py`
- Modify: `src/systograph/core/services/manual_mapping_service.py`
- Test: `tests/integration/test_manual_mapping_component_detection.py`
- Test: `tests/unit/core/test_manual_mapping_service.py`

- [ ] **Step 1：撰寫 failing integration test**

在 `tests/integration/test_manual_mapping_component_detection.py` 新增：

```python
def test_confirmed_non_baseline_mapping_replays_as_capability_candidate() -> None:
    fact, evidence = router_unmapped_candidate()
    manual_mapping_service = ManualMappingService(
        repository=InMemoryManualMappingRepository(),
        project_id="project:demo",
    )
    manual_mapping_service.create_mapping(
        ManualMappingCreate(
            project_id="project:demo",
            mapping_type=ManualMappingType.NON_BASELINE_CAPABILITY_CANDIDATE,
            decision=ManualMappingDecision.CONFIRMED,
            source_unmapped_id=(
                "unmapped:src_query_router_py:"
                "queryrouter_route:code_pattern_custom_router"
            ),
            source_file="src/query_router.py",
            observed_kind="routing_orchestration",
            evidence_ids=[evidence.id],
            capability_candidate_id="capability-candidate:query_router",
            capability_candidate_name="Query Router",
            capability_candidate_kind="routing_orchestration",
        )
    )

    result = ComponentDetectionService(
        manual_mapping_hook=manual_mapping_service,
    ).detect(
        template=RagTemplateService.load("rag-core-v1"),
        facts=[fact],
        evidence=[evidence],
    )

    assert result.unmapped_components == []
    assert result.extensions == []
    assert result.capability_candidate_components[0].id == (
        "capability-candidate:query_router"
    )
    assert result.capability_candidate_components[0].status == (
        "confirmed_non_baseline"
    )
```

- [ ] **Step 2：執行 failing integration test**

執行：

```bash
.venv/bin/pytest \
  tests/integration/test_manual_mapping_component_detection.py::test_confirmed_non_baseline_mapping_replays_as_capability_candidate \
  -q
```

預期：失敗，因為 `capability_candidate_components` 尚不存在。

- [ ] **Step 3：擴充 `ComponentDetectionResult`**

修改 `src/systograph/core/services/component_detection_service.py`。使用 `field(default_factory=list)`，讓既有的 tests 與 services 在建立 `ComponentDetectionResult` 時仍可運作，同時新 path 能攜帶 capability candidates：

```python
from dataclasses import dataclass, field

from systograph.core.models.capability_candidate import CapabilityCandidateComponent


@dataclass(frozen=True)
class ComponentDetectionResult:
    components_by_slot: dict[str, ComponentSlot]
    extensions: list[ExtensionComponent]
    unmapped_components: list[UnmappedComponent]
    capability_candidate_components: list[CapabilityCandidateComponent] = field(
        default_factory=list
    )
```

主 detection constructor 可因 default 而省略該 field，或為清晰起見明確傳入：

```python
result = ComponentDetectionResult(
    components_by_slot=components_by_slot,
    extensions=sorted(extensions.values(), key=lambda item: item.id),
    unmapped_components=sorted(unmapped.values(), key=lambda item: item.id),
    capability_candidate_components=[],
)
```

不要將 `capability_candidate_components` 加入 `SystemMapNormalizeService._build_system_map(...)` 輸出。它刻意為 non-canonical，屬於 `02-implement-stackable-profile-inference.md` 中的 profile sidecar。

- [ ] **Step 4：新增 manual mapping apply path**

修改 `src/systograph/core/services/manual_mapping_service.py`：

```python
from systograph.core.models.capability_candidate import CapabilityCandidateComponent
```

在 `apply()` 內：

```python
capability_candidates = list(result.capability_candidate_components)
```

新增 branch：

```python
elif (
    mapping.mapping_type
    == ManualMappingType.NON_BASELINE_CAPABILITY_CANDIDATE
):
    capability_candidates = self._apply_capability_candidate(
        mapping,
        capability_candidates,
    )
    unmapped = _remove_mapped_unmapped(mapping, unmapped)
```

Return：

```python
return ComponentDetectionResult(
    components_by_slot=components_by_slot,
    extensions=sorted(extensions, key=lambda item: item.id),
    unmapped_components=sorted(unmapped, key=lambda item: item.id),
    capability_candidate_components=sorted(
        capability_candidates,
        key=lambda item: item.id,
    ),
)
```

新增 helper：

```python
def _apply_capability_candidate(
    self,
    mapping: ManualMapping,
    capability_candidates: list[CapabilityCandidateComponent],
) -> list[CapabilityCandidateComponent]:
    if (
        mapping.capability_candidate_id is None
        or mapping.capability_candidate_kind is None
    ):
        return capability_candidates

    candidate = CapabilityCandidateComponent(
        id=mapping.capability_candidate_id,
        name=mapping.capability_candidate_name,
        observed_kind=mapping.capability_candidate_kind,
        status="confirmed_non_baseline",
        evidence_ids=sorted(mapping.evidence_ids),
        source_unmapped_component_id=mapping.source_unmapped_id,
        source_file=mapping.source_file,
        proposal_id=mapping.proposal_id,
        decision_source=mapping.decision_source,
    )
    return [
        item
        for item in capability_candidates
        if item.id != candidate.id
    ] + [candidate]
```

- [ ] **Step 5：驗證 confirmed non-baseline mappings**

新增 `_validate_capability_candidate()`：

```python
def _validate_capability_candidate(self, draft: ManualMappingCreate) -> None:
    _require_text("capability_candidate_id", draft.capability_candidate_id)
    _require_text("capability_candidate_name", draft.capability_candidate_name)
    _require_text("capability_candidate_kind", draft.capability_candidate_kind)
    if draft.target_slot is not None:
        raise ValueError(
            "non_baseline_capability_candidate must not include target_slot"
        )
    if (
        draft.extension_id is not None
        or draft.extension_name is not None
        or draft.extension_kind is not None
        or draft.extension_edges
    ):
        raise ValueError(
            "non_baseline_capability_candidate must not include extension fields"
        )
```

在 `_validate_create()` 中：

```python
if draft.mapping_type == ManualMappingType.EXISTING_SLOT:
    self._validate_existing_slot(draft)
    return
if draft.mapping_type == ManualMappingType.NON_BASELINE_CAPABILITY_CANDIDATE:
    self._validate_capability_candidate(draft)
    return
self._validate_extension(draft)
```

- [ ] **Step 6：保留 legacy `NEW_EXTENSION` tests**

重新命名既有 tests，但保留 assertions：

```python
def test_legacy_confirmed_extension_mapping_replays_live_candidate() -> None:
    ...


def test_legacy_confirmed_extension_mapping_replays_unmapped_candidate() -> None:
    ...
```

加上註解說明這些是 compatibility tests，而非 Phase2 的 preferred path。

- [ ] **Step 7：執行 tests**

執行：

```bash
.venv/bin/pytest \
  tests/unit/core/test_manual_mapping_service.py \
  tests/integration/test_manual_mapping_component_detection.py \
  -q
```

預期：通過。

## Task 3：停止為 Reranker Evidence 建立新的 Extension Candidates

**檔案：**

- Modify: `src/systograph/core/services/component_detection_service.py`
- Test: `tests/integration/test_phase13_component_detection_behaviors.py`
- Test: `tests/unit/core/test_component_detection_service.py`

- [ ] **Step 1：更新 failing behavior test**

將 extension-first expectation 改為 unmapped confirmation expectation：

```python
def test_reranker_fixture_creates_non_baseline_confirmation_candidate() -> None:
    result = detect_fixture("reranker_extension_rag")

    assert result.extensions == []
    assert result.unmapped_components
    assert result.unmapped_components[0].observed_kind in {
        "reranker_candidate",
        "code_pattern",
    }
    assert "confirm_mapping" in result.unmapped_components[0].suggested_actions
```

- [ ] **Step 2：執行 focused test**

執行：

```bash
.venv/bin/pytest \
  tests/integration/test_phase13_component_detection_behaviors.py::test_reranker_fixture_creates_non_baseline_confirmation_candidate \
  -q
```

預期：失敗，因為 `_extension_candidate()` 仍輸出 extension。

- [ ] **Step 3：替換 `_extension_candidate()` 用法**

在 `ComponentDetectionService.detect()` 中，從主 loop 移除 `_extension_candidate()` 呼叫（針對新 scan results）。讓 reranker-like facts 改走 `_unmapped_candidate()`：

```python
def _unmapped_candidate(
    self,
    fact: ScanFact,
    evidence_ids: tuple[str, ...],
) -> UnmappedComponent | None:
    if (
        self._is_weak_dependency_signal(fact)
        or self._looks_like_router(fact)
        or self._looks_like_reranker(fact)
    ):
        observed_kind = self._observed_kind(fact)
        if self._looks_like_reranker(fact):
            observed_kind = "reranker_candidate"
        ...
```

刪除 `_extension_candidate()` 與 `EXTENSION_CANDIDATE_STATUS`。保留 `ExtensionComponent` model 與 manual-mapping legacy apply support，供舊 artifacts / repository records 使用。

新增：

```python
def _looks_like_reranker(self, fact: ScanFact) -> bool:
    return (
        "reranker" in fact.path.lower()
        or "rerank" in (fact.value or "").lower()
        or "rerank" in (fact.rule_id or "").lower()
    )
```

- [ ] **Step 4：執行 component detection tests**

執行：

```bash
.venv/bin/pytest \
  tests/unit/core/test_component_detection_service.py \
  tests/integration/test_phase13_component_detection_behaviors.py \
  tests/integration/test_phase4_rag_fixture_behaviors.py \
  -q
```

預期：在更新將新 reranker evidence 描述為 extension candidates 的 expectations 後通過。

## Task 4：重構 Mapping Proposal Candidates

**檔案：**

- Modify: `src/systograph/core/services/mapping_proposal_service.py`
- Modify: `src/systograph/core/models/mapping.py`
- Test: `tests/unit/core/test_mapping_proposal_service.py`
- Test: `tests/web/test_mapping_proposal_routes.py`

- [ ] **Step 1：撰寫 non-baseline candidate 的 proposal tests**

在 `tests/unit/core/test_mapping_proposal_service.py` 新增或更新：

```python
def test_reranker_proposal_uses_non_baseline_capability_candidate() -> None:
    packet = MappingEvidencePacket(
        project_id="project:demo",
        source_unmapped_id="unmapped:reranker",
        observed_kind="reranker_candidate",
        reason="Detected reranker evidence.",
        evidence_ids=["evidence:reranker"],
        rule_ids=["code_pattern_reranker"],
        masked_evidence_values=["rerank"],
        available_slots=["retriever", "vector_store", "llm"],
    )

    proposal = MappingProposalService().create_proposal(packet)

    candidate = proposal.candidates[0]
    assert (
        candidate.candidate_type
        == MappingCandidateType.NON_BASELINE_CAPABILITY_CANDIDATE
    )
    assert candidate.proposed_capability_candidate_kind == "reranker"
    assert candidate.proposed_extension_id is None
```

新增 accept test：

```python
def test_accepting_non_baseline_candidate_creates_capability_manual_mapping() -> None:
    manual_mapping_service = ManualMappingService()
    service = MappingProposalService(
        manual_mapping_service=manual_mapping_service,
    )
    proposal = service.create_proposal(packet_for_reranker())

    result = service.decide(
        proposal.proposal_id,
        MappingProposalDecisionRequest(
            decision=MappingProposalDecisionAction.ACCEPT,
            candidate_id=proposal.candidates[0].candidate_id,
        ),
    )

    assert (
        result.manual_mapping.mapping_type
        == ManualMappingType.NON_BASELINE_CAPABILITY_CANDIDATE
    )
    assert result.manual_mapping.capability_candidate_kind == "reranker"
```

- [ ] **Step 2：執行 proposal tests 並確認失敗**

執行：

```bash
.venv/bin/pytest tests/unit/core/test_mapping_proposal_service.py -q
```

預期：失敗，因為 service 仍輸出 `NEW_EXTENSION`。

- [ ] **Step 3：更新 deterministic candidates**

替換 router branch：

```python
MappingCandidate(
    candidate_type=MappingCandidateType.NON_BASELINE_CAPABILITY_CANDIDATE,
    proposed_capability_candidate_id="capability-candidate:query_router",
    proposed_capability_candidate_name="Query Router",
    proposed_capability_candidate_kind="routing_orchestration",
    label="Mark as non-baseline capability candidate",
    rationale=(
        "Router-like evidence is outside the legacy v1 slot model and should "
        "be evaluated by profile inference."
    ),
    ...
)
```

替換 reranker branch：

```python
MappingCandidate(
    candidate_type=MappingCandidateType.NON_BASELINE_CAPABILITY_CANDIDATE,
    proposed_capability_candidate_id="capability-candidate:reranker",
    proposed_capability_candidate_name="Reranker",
    proposed_capability_candidate_kind="reranker",
    label="Mark as non-baseline capability candidate",
    rationale=(
        "Reranker-like evidence is outside the legacy v1 slot model and should "
        "be evaluated by profile inference."
    ),
    ...
)
```

將 fallback copy 從：

```text
slot or extension
```

改為：

```text
legacy v1 slot or non-baseline capability candidate
```

- [ ] **Step 4：更新 candidate validation 與 conversion**

在 `_validate_candidate()` 中驗證 capability candidate fields。

在 `_candidate_to_manual_mapping()` 中：

```python
if (
    candidate.candidate_type
    == MappingCandidateType.NON_BASELINE_CAPABILITY_CANDIDATE
):
    return ManualMappingCreate(
        project_id=proposal.project_id,
        mapping_type=ManualMappingType.NON_BASELINE_CAPABILITY_CANDIDATE,
        decision=ManualMappingDecision.CONFIRMED,
        source_unmapped_id=proposal.source_unmapped_id,
        source_file=packet.source_file,
        observed_kind=packet.observed_kind,
        evidence_ids=list(candidate.evidence_ids),
        capability_candidate_id=candidate.proposed_capability_candidate_id,
        capability_candidate_name=candidate.proposed_capability_candidate_name,
        capability_candidate_kind=candidate.proposed_capability_candidate_kind,
        proposal_id=proposal.proposal_id,
        decision_source="proposal_accept",
    )
```

- [ ] **Step 5：執行 unit 與 web proposal tests**

執行：

```bash
.venv/bin/pytest \
  tests/unit/core/test_mapping_proposal_service.py \
  tests/web/test_mapping_proposal_routes.py \
  -q
```

預期：在更新 expected payload fields 後通過。

## Task 5：保持 Routes 與 Packets 的 Backward Compatibility

**檔案：**

- Modify: `src/systograph/core/services/mapping_evidence_packet_builder.py`
- Modify: `src/systograph/web/routes/mapping_proposal_routes.py`
- Test: `tests/web/test_mapping_proposal_routes.py`

- [ ] **Step 1：新增 route test，證明不需要 extension target**

在 `tests/web/test_mapping_proposal_routes.py` 中，對 reranker/router proposal response 新增 assertion：

```python
candidate = payload["candidates"][0]
assert candidate["candidate_type"] == "non_baseline_capability_candidate"
assert candidate["proposed_extension_id"] is None
assert candidate["proposed_capability_candidate_id"].startswith(
    "capability-candidate:"
)
```

- [ ] **Step 2：將 `available_extensions` 僅保留為 legacy-only**

在 `mapping_proposal_routes.py` 中，繼續傳遞 `available_extensions` 供 legacy candidate validation，但勿讓 deterministic router/reranker candidates 依賴它。加上 code comment：

```python
# Legacy compatibility only. New Phase2 non-baseline decisions should
# become capability candidates, not extension confirmations.
available_extensions=[
    extension.id for extension in system_map.extensions
],
```

- [ ] **Step 3：執行 route tests**

執行：

```bash
.venv/bin/pytest tests/web/test_mapping_proposal_routes.py -q
```

預期：通過。

## Task 6：將 Capability Candidates 銜接至 Profile Inference 後續工作

**檔案：**

- Modify: `docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/02-implement-stackable-profile-inference.md`
- Modify: `docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/03-consolidate-profile-sidecar-lifecycle.md`
- Test: 僅 documentation review

- [ ] **Step 1：更新 `02` 以 consume 新 model**

將任何在 `profile_signal.py` 內建立 `CapabilityCandidateComponent` 的指示，替換為：

```text
Import and reuse `systograph.core.models.capability_candidate.CapabilityCandidateComponent`.
`profile-signals/v1` owns serialization of `capability_candidate_components`, but
the durable decision source is manual mapping / confirmation lifecycle.
```

- [ ] **Step 2：更新 sidecar lifecycle 用語**

在 `03-consolidate-profile-sidecar-lifecycle.md` 中說明：

```text
profile_signals.json materializes capability_candidate_components from confirmed
non-baseline manual decisions during map build. It is not the durable source of
truth for those decisions.
```

- [ ] **Step 3：新增 dependency note**

在 `02-implement-stackable-profile-inference.md` 中新增：

```text
Depends on 01-rework-manual-mapping-capability-candidates.md because profile
inference consumes capability_candidate_components produced by confirmed
non-baseline decisions.
```

## Task 8：持久化 Reject / Skip 的 Durable ManualMapping 與 Audit Trail

**2026-07-08 audit（OPEN code gap）：** 本 Task 的 plan/contract 方向成立，但現行
implementation 尚未對齊。`mapping.py` 的 `MappingProposalDecisionResult` validator 對
`REJECTED` / `SKIPPED` 仍要求 `manual_mapping: null`；`MappingProposalService.decide(REJECT|SKIP_FOR_NOW)`
只更新 proposal status、不回傳 durable mapping。完成本 Task 時須同時修 model validator、
service、web route 與下列 tests。

**背景：** Plan 03A 規定 `rejected` / `skip_for_now` 不得進入 `applied_mapping_ids`。
`docs/MODEL-CONTRACT.md` 的 `ManualMappingCreate.decision` 已包含
`rejected | skip_for_now | not_applicable`，並要求 `audit_metadata`。目前
`MappingProposalService.decide(REJECT|SKIP_FOR_NOW)` 只更新 proposal status，未寫入
durable manual mapping。

**檔案：**

- Modify: `src/systograph/core/services/mapping_proposal_service.py`
- Modify: `src/systograph/core/services/manual_mapping_service.py`
- Test: `tests/unit/core/test_mapping_proposal_service.py`
- Test: `tests/unit/core/test_manual_mapping_service.py`
- Test: `tests/integration/test_manual_mapping_component_detection.py`
- Test: `tests/web/test_mapping_proposal_routes.py`

- [ ] `decide(REJECT)` 建立 durable `ManualMapping(decision=REJECTED)`，含
  `source_unmapped_id`、`evidence_ids`、`proposal_id`、`audit_metadata`（`acted_at`、
  `actor_surface`）。
- [ ] `decide(SKIP_FOR_NOW)` 建立 durable `ManualMapping(decision=SKIP_FOR_NOW)`；不得
  materialize `capability_candidate_components`；保留 unmapped + scanner warning。
- [ ] `rejected` / `skip_for_now` / `not_applicable` 不進入 Plan 03A 的
  `applied_mapping_ids`；Apply replay 只 materialize confirmed decisions。
- [ ] `evidence_table.json.review_state` 與 manual mapping decision 對齊（confirmed /
  rejected / needs_confirmation / not_required）；與 Plan 03 / dynamic `00` 接縫。
- [ ] Web route 在 reject/skip 時回傳 `manual_mapping` payload，不只回 proposal status。

## Task 7：最終驗證

- [ ] `.venv/bin/pytest tests/unit/core/test_mapping_models.py -q`
- [ ] `.venv/bin/pytest tests/unit/core/test_manual_mapping_service.py -q`
- [ ] `.venv/bin/pytest tests/unit/core/test_mapping_proposal_service.py -q`
- [ ] `.venv/bin/pytest tests/unit/core/test_component_detection_service.py -q`
- [ ] `.venv/bin/pytest tests/integration/test_manual_mapping_component_detection.py -q`
- [ ] `.venv/bin/pytest tests/integration/test_phase13_component_detection_behaviors.py -q`
- [ ] `.venv/bin/pytest tests/web/test_mapping_proposal_routes.py -q`
- [ ] `.venv/bin/pytest tests/web/test_mapping_routes.py -q`
- [ ] `.venv/bin/ruff check src/systograph/core/models/mapping.py src/systograph/core/services/manual_mapping_service.py src/systograph/core/services/mapping_proposal_service.py src/systograph/core/services/component_detection_service.py`
- [ ] `.venv/bin/mypy`
- [ ] `git diff --check`

## 驗收標準

- [ ] 新的 Phase2 confirmation 可持久化 `non_baseline_capability_candidate`。
- [ ] 文件／實作註解／UI helper text 不得把 `non_baseline` 解釋成「仍使用
  `rag-core-v1` baseline」；應解釋為「非 map 結構層的能力候選」。
- [ ] 新 API 不再 emit 含 `rag_variant` 的 candidate type；舊 records 可透過
  compatibility alias 讀取。
- [ ] Ambiguous components 可對應 generic canonical component type/layer，不要求
  repo 先被判定為 RAG。
- [ ] Grounding mapping 只在 grounding applicable 時顯示與驗證。
- [ ] Confirmed non-baseline decisions 會 replay 到 `ComponentDetectionResult.capability_candidate_components`。
- [ ] Confirmed non-baseline decisions 不會建立 `ExtensionComponent`，也不寫入
  canonical `ai_system_map.json` topology。
- [ ] Confirmed non-baseline decisions **不會**直接把 profile／reference-node 設成
  `detected`（那是 Plan 01A / 02）。
- [ ] `NEW_EXTENSION` 仍支援 legacy compatibility，但 deterministic proposal heuristics 不再輸出它。
- [ ] Reranker/router-like evidence 以 unmapped / non-baseline confirmation 呈現，而非 new extension candidate。
- [ ] Mapping proposal accept 會將 non-baseline candidates 轉換為新的 manual mapping type。
- [ ] Profile inference 計畫 `02` 從本計畫 consume `CapabilityCandidateComponent`，而非另建平行 model。
- [ ] Canonical `ai-system-map/v1` schema 不因本計畫而變更。
- [ ] `MappingProposalService.decide(REJECT|SKIP_FOR_NOW)` 會持久化 durable
  `ManualMapping`（含 `audit_metadata`），不只更新 proposal status。
- [ ] `rejected` / `skip_for_now` / `not_applicable` 不 materialize
  `capability_candidate_components`，也不進入 Plan 03A 的 `applied_mapping_ids`。

## 後續備註

- Frontend 應將 UI copy 從「Confirm as extension」改為
  `Review scanner suggestions` / `檢查 scanner 建議`。候選 action 契約值仍可為
  `Mark as non-baseline capability`，但 **helper / tooltip 必須白話說明**：
  「確認這是能力訊號，但不是系統底圖上的結構元件」——不得暗示還在做 RAG
  baseline 分類。不得要求使用者先判斷 RAG taxonomy。
- 僅在舊 artifacts 與 clients 不再依賴 `ExtensionComponent` 後，才可在未來 breaking schema migration 中考慮移除它。
- 若未來要 rename 契約字串（例如 `non_map_capability_candidate`），屬另開
  compatibility migration；**不在本計畫範圍**。本計畫只鎖定語意與行為。
- Confirmed decision 儲存後不得直接 mutate 目前載入的 map，也不得自動重新掃描
  repo。Plan `03A-implement-apply-build-lineage-and-local-json-persistence.md` 會提供
  「套用 N 項確認並建立新版本」流程：沿用原 `scan_id` snapshot，建立新的
  `build_id`，並把 exact `mapping_id` 列入 `applied_mapping_ids`。
- Plan 01 只擁有 decision lifecycle；Apply API、snapshot reuse、build lineage、latest
  Viewer atomic switch 與 local JSON persistence 一律由 Plan 03A 擁有，不得在 proposal
  route 內重複實作 build pipeline。

## P0 Execution Mapping 補充（2026-07-03）

Manual mapping 仍只處理 ambiguous evidence 的 durable decision，不直接確認 execution path：

- 使用者可確認某段 evidence 是 generic component、（過渡期）legacy v1 slot、或
  non-baseline capability candidate（非 map 結構層）；這不等於「該 component 位於
  某次 query path」，也不等於 capability `detected`。
- dynamic `00` 的 call graph / dataflow / execution path recoverer 可以引用已確認的
  component ids 或 candidate refs 作 anchors，但必須保留 static-only limitations。
- Mapping proposal 不新增「confirm execution step」或「confirm call edge」產品 action。
- 若 call graph evidence 與 manual mapping 衝突，優先保留 evidence 與 `undetermined`
  reason，不自動把 profile 或 readiness 升級為 `detected`。
