# Multimodal RAG Scanner Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 讓 scanner以 generic v2 facts、`multimodal-grounding` capability finding與
unmapped evidence表達 multimodal AI/RAG signals，不建立 active v1 extension或硬塞 Naive
RAG core dimensions。

**Architecture:** 第一版只掃 synthetic text/config/dependency/optional AST signals，不放
真實圖片、音訊、影片，不做 multimodal inference。Python依 deterministic evidence產生
canonical facts與 profile status；dependency/name-only維持 `undetermined`。Frontend只 render
backend projection，完整 UX由 Task 42負責。

**Tech Stack:** Existing providers, rule catalogs, pytest fixtures, optional future AST facts.

---

## 最新狀態（2026-06-18）

- Task 4 將 multimodal ingestion 明確延後。
- Task 31 先擴 advanced text RAG fixtures；Task 39 在那之後補 multimodal-specific signals。
- Phase2 active contract使用 generic `ai-system-map/v2`與 one-level capability profiles；
  `rag-core-v1`只作 legacy compatibility，不能再新增 active extension。

## Scope

- 建立 `multimodal_rag_signals/` fixture。
- 新增 dependencies/config/code rules for CLIP-like embedding、image loader、OCR/document layout parser、multimodal retriever。
- Component detection產生 generic component/unmapped facts；profile inference依 wiring evidence
  產生 `multimodal-grounding`
  `detected/partial/undetermined/not_detected/conflicted`統一五態。
- Risk hints 說明 multimodal data privacy 與 unsupported modality uncertainty。

## Out of scope

- 不放真實 media files。
- 不執行 OCR、image embedding、audio/video inference。
- 不下載 multimodal model。
- 不修改 v1 core slots或建立 active `ExtensionComponent`。

### Task 1: Create multimodal fixture

**Files:**
- Create: `tests/fixtures/rag_projects/multimodal_rag_signals/`
- Test: `tests/unit/test_rag_project_fixtures_contract.py`

- [ ] **Step 1: Add synthetic-only fixture files**

Required:

```text
README.md
requirements.txt
config.yaml
src/image_ingestion.py
src/multimodal_retriever.py
docs/synthetic_manifest.md
```

Signals:

```text
CLIPModel
ImageBind
LlamaParse
UnstructuredImageLoader
OCR pipeline config
image_embedding_model
multimodal_retriever
```

- [ ] **Step 2: Assert no binary/media files exist**
- [ ] **Step 3: Assert no real PHI/PII or secrets exist**

### Task 2: Add provider rules

**Files:**
- Modify: `src/kai_mind/core/rules/code_pattern_rules.toml`
- Modify: `src/kai_mind/core/rules/dependency_manifest_rules.toml`
- Test: `tests/unit/core/test_rule_catalog_loader.py`
- Test: `tests/integration/test_phase11_code_pattern_provider_behaviors.py`

- [ ] **Step 1: Add dependency rules for multimodal libraries**
- [ ] **Step 2: Add code pattern rules for multimodal loaders/embeddings**
- [ ] **Step 3: Ensure rules produce bounded evidence and masked snippets**

### Task 3: Map to generic v2 facts and multimodal capability status

**Files:**
- Modify: `src/kai_mind/core/services/component_detection_service.py`
- Test: `tests/unit/core/test_component_detection_service.py`
- Test: `tests/integration/test_phase13_component_detection_behaviors.py`

- [ ] **Step 1: Add tests that multimodal signals become generic components/unmapped facts and `multimodal-grounding` findings**
- [ ] **Step 2: Assert core `embedding_model` is not detected solely from multimodal dependency**
- [ ] **Step 3: Preserve evidence ids and uncertainty reasons**
- [ ] **Step 4: Assert active outputs contain no new `ExtensionComponent` or `new_extension_component` path**

### Task 4: Add risk hints and backend projection handoff

**Files:**
- Modify: `src/kai_mind/core/rules/risk_hint_rules.toml`
- Modify: `docs/API-GUIDE.md`
- Modify: `frontend/API_CONTRACT.md` only for backend-emitted fields consumed by Task 42
- Test: `tests/unit/core/test_risk_hint_service.py`

- [ ] **Step 1: Add multimodal unsupported/uncertain modality hint**
- [ ] **Step 2: Add privacy note for image/audio/video ingestion**
- [ ] **Step 3: Document backend `Extension Subsystems Plane` projection and prohibit frontend inference from dependency names**

## Verification

```bash
.venv/bin/pytest tests/unit/test_rag_project_fixtures_contract.py tests/unit/core/test_component_detection_service.py tests/integration/test_phase13_component_detection_behaviors.py -v
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

## Acceptance Criteria

- Multimodal signals are represented as generic v2 facts/profile findings/unmapped evidence without active extension writes.
- No real media or personal data is added to fixtures.
- Scanner output clearly states unsupported/uncertain modality boundaries.
- Legacy `rag-core-v1` remains read-only compatibility；active v2/profile contracts remain stable。

## Dependencies and Follow-ups

- 依賴 Phase2 Plan 01A reference catalog、Plan 02 profile inference、Plan 06 backend projection
  與 Plan 14 validation semantics。
- Task 31提供 fixture corpus；Task 34可提供 optional AST observations；Task 39A可平行增加
  governance/observability capabilities。
- Phase5 Task 42 渲染 `Extension Subsystems Plane` 與 evidence details；本計畫不實作
  Graph Studio。
