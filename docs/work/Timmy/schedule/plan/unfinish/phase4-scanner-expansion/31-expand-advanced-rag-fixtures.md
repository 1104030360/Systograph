# Advanced RAG Fixtures Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立 advanced AI/RAG capability regression corpus，支援後續 dependency、
Compose、AST、specialized capability detection與 contextual security engine演進；fixtures
只提供 scanner evidence，不延續 active v1 extension product contract。

**Architecture:** Fixtures 只提供 deterministic scanner signals，不執行真實 RAG pipeline、不放真實資料、不放 secret。每個 fixture 都要能說明它要保護哪一種 scanner behavior，並透過 unit/integration tests 固定。

**Tech Stack:** pytest fixtures, existing providers, TOML rule catalogs, synthetic project files.

---

## 最新狀態（2026-06-18）

- Task 4 fixture framework 已完成。
- 已有 `reranker_extension_rag/`、`graph_rag_extension_rag/` 等 legacy-named fixture
  paths；檔名可在 migration期間保留，但 expected output必須對齊 generic v2
  components/profile capabilities，不可繼續建立 active `ExtensionComponent`。
- Task 11-15、12a、14a、25 都已完成；本計畫已改成基於現有 provider/rule catalog/map pipeline 的下一步 fixture 擴充。
- 目前仍缺完整 document loader、chunking、observability、hybrid retrieval、guardrail taxonomy 的 regression corpus；governance/observability實際 detector由 Task 39A擁有。

## Scope

- 擴充或新增 synthetic fixtures，覆蓋 document loader、chunking、observability、guardrails、citation、hybrid graph/vector retrieval。
- 補 provider/rule catalog tests，確保新 signals 被掃成 facts/evidence。
- 補 canonical component / capability profile / unmapped regression，避免新 signals被誤判成
  legacy v1 slots 或 active extension。

## Out of scope

- 不建立可執行 RAG pipeline。
- 不下載模型、資料集或外部 dependency。
- 不放真實醫療資料、個資、圖片、音訊或影片。
- 不新增或修改 `ai-system-map/v1` core slot；Phase4 active behavior以 generic v2與
  profile sidecar為準。

### Task 1: Add document loader and chunking fixture

**Files:**
- Create: `tests/fixtures/rag_projects/document_loader_chunking_rag/`
- Modify: `tests/unit/test_rag_project_fixtures_contract.py`
- Test: `tests/integration/test_phase11_code_pattern_provider_behaviors.py`

- [ ] **Step 1: Create synthetic fixture files**

Required files:

```text
README.md
requirements.txt
config.yaml
src/loaders.py
src/chunking.py
docs/synthetic_policy.md
```

Signals:

```text
PyPDFLoader
UnstructuredLoader
WebBaseLoader
RecursiveCharacterTextSplitter
chunk_size
chunk_overlap
```

- [ ] **Step 2: Add fixture contract test**

Assert no file contains real PHI/PII, secrets, binary payload, or model weights.

- [ ] **Step 3: Add provider integration test**

Assert code/config/dependency facts exist and evidence file paths are project-relative POSIX paths.

### Task 2: Add observability and guardrail fixture coverage for Task 39A

**Files:**
- Modify: `tests/fixtures/rag_projects/healthcare_rag_minimal/`
- Test: `tests/unit/test_rag_project_fixtures_contract.py`
- Test: `tests/integration/test_governance_observability_capabilities.py`（由 Task 39A 建立）

- [ ] **Step 1: Add observability-only signals**

Signals:

```text
OpenTelemetry tracer provider setup
LangSmith-like tracing config without real API key
metrics/logging config with fake endpoint
```

- [ ] **Step 2: Add guardrail taxonomy signals**

Signals:

```text
input_guardrail
output_guardrail
medical_no_diagnosis_policy
emergency_escalation_policy
```

- [ ] **Step 3: Define expected deterministic evidence and unified five-state profile rows for Task 39A**

Plan 31只擁有 synthetic corpus。Rule/provider/profile/projection implementation屬 Task 39A；
不得在本計畫建立第二套 detector。Guardrail/observability signals不可硬塞進 legacy v1 slots，
也不可建立 active extension。

### Task 3: Add hybrid graph/vector retrieval capability regression

**Files:**
- Modify: `tests/fixtures/rag_projects/graph_rag_extension_rag/`
- Test: `tests/integration/test_phase14_endpoints_risk_hints_flows_behaviors.py`

- [ ] **Step 1: Add hybrid retrieval source file**

Include deterministic signals:

```text
Neo4jGraph
vector_retriever
entity_extraction
graph_traversal
hybrid_retrieval
```

- [ ] **Step 2: Assert graph retrieval becomes evidence-backed `graph-retrieval` / `hybrid-retrieval` capability findings**

It must not incorrectly satisfy legacy v1 slots without deterministic wiring evidence，且不得
materialize成 active `ExtensionComponent`。

### Task 4: Update coverage matrix

**Files:**
- Modify: `docs/work/Timmy/schedule/plan/finish/04-build-test-fixtures-and-contract-baseline.md`
- Modify: `docs/API-GUIDE.md` only if API examples change

- [ ] **Step 1: Add a table of advanced fixture coverage**
- [ ] **Step 2: Mark multimodal as separate Task 39**
- [ ] **Step 3: Mark governance/observability detector ownership as separate Task 39A**
- [ ] **Step 4: Document that advanced fixtures are scanner signals, not runnable sample apps**

## Verification

```bash
.venv/bin/pytest tests/unit/test_rag_project_fixtures_contract.py tests/integration/test_phase4_rag_fixture_behaviors.py tests/integration/test_phase11_code_pattern_provider_behaviors.py tests/integration/test_phase13_component_detection_behaviors.py -v
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

## Acceptance Criteria

- Advanced fixture coverage includes document loader, chunking, observability, guardrails, citation, and hybrid retrieval signals；Task 39A owns governance/observability detection。
- New fixtures contain only synthetic text and scanner signals.
- New signals do not create false detected core dimensions或 active legacy extensions。
- All fixture paths and evidence paths remain project-relative POSIX paths.

## Dependencies and Follow-ups

- 依賴 Phase2 Plan 14 deterministic fixture contract與 active v2/profile status semantics。
- Task 34可增強 AST evidence；Task 39擁有 multimodal capability detection；Task 39A擁有
  governance/observability capability detection；Task 35只解讀 contextual security risk。
- Phase5 Task 42消費 backend projection，不直接讀 fixtures或 rule names。
