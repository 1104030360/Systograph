# Multimodal RAG Scanner Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 讓 scanner 能以 extension/unmapped evidence 表達 multimodal RAG signals，而不破壞 `rag-core-v1` core slot contract。

**Architecture:** 第一版只掃 synthetic text/config/dependency signals，不放真實圖片、音訊、影片，不做 multimodal inference。若需要新增 core slots，必須另做 schema migration；本計畫預設使用 extension components。

**Tech Stack:** Existing providers, rule catalogs, pytest fixtures, optional future AST facts.

---

## 最新狀態（2026-06-18）

- Task 4 將 multimodal ingestion 明確延後。
- Task 31 先擴 advanced text RAG fixtures；Task 39 在那之後補 multimodal-specific signals。
- 目前 `rag-core-v1` 未把 image/audio/video ingestion 作為 core slot。

## Scope

- 建立 `multimodal_rag_signals/` fixture。
- 新增 dependencies/config/code rules for CLIP-like embedding、image loader、OCR/document layout parser、multimodal retriever。
- Component detection 先產生 extension/unmapped components，不硬塞進 `embedding_model` 或 `retriever`。
- Risk hints 說明 multimodal data privacy 與 unsupported modality uncertainty。

## Out of scope

- 不放真實 media files。
- 不執行 OCR、image embedding、audio/video inference。
- 不下載 multimodal model。
- 不新增 core slots without migration。

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

### Task 3: Map to extension/unmapped components

**Files:**
- Modify: `src/kai_mind/core/services/component_detection_service.py`
- Test: `tests/unit/core/test_component_detection_service.py`
- Test: `tests/integration/test_phase13_component_detection_behaviors.py`

- [ ] **Step 1: Add tests that multimodal signals become extension components**
- [ ] **Step 2: Assert core `embedding_model` is not detected solely from multimodal dependency**
- [ ] **Step 3: Preserve evidence ids and uncertainty reasons**

### Task 4: Add risk hints and frontend handoff

**Files:**
- Modify: `src/kai_mind/core/rules/risk_hint_rules.toml`
- Modify: `docs/API-GUIDE.md`
- Modify: `frontend/API_CONTRACT.md`
- Test: `tests/unit/core/test_risk_hint_service.py`

- [ ] **Step 1: Add multimodal unsupported/uncertain modality hint**
- [ ] **Step 2: Add privacy note for image/audio/video ingestion**
- [ ] **Step 3: Document extension rendering guidance for frontend**

## Verification

```bash
.venv/bin/pytest tests/unit/test_rag_project_fixtures_contract.py tests/unit/core/test_component_detection_service.py tests/integration/test_phase13_component_detection_behaviors.py -v
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

## Acceptance Criteria

- Multimodal signals are detected as extension/unmapped evidence without schema break.
- No real media or personal data is added to fixtures.
- Scanner output clearly states unsupported/uncertain modality boundaries.
- Canonical `rag-core-v1` core slots remain stable.

