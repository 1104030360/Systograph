# Contextual Security Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 deterministic scanner evidence 與 bounded AST facts 上建立 contextual security risk engine，降低單純字串/元件存在造成的誤判。

**Architecture:** Security engine 消費現有 facts、AST observations、flow graph、risk hint rule catalog；它不重新掃檔案、不執行程式、不讓 AI 產生 scanner facts。輸出仍是 uncertainty-aware risk hints，不宣稱完整 SAST、完整漏洞掃描或 runtime exploit proof。

**Tech Stack:** Python rule evaluator, TOML/YAML policy catalog, pytest, existing `RiskHintService`, optional AST facts from Task 34.

---

## 最新狀態（2026-06-18）

- Task 14 與 14a 已完成 endpoint/risk hint/flows 與 risk hint rule metadata TOML。
- Task 34 尚未完成前，security engine 不應先做 taint/reachability。
- OWASP GenAI / LLM Top 10 2025 已將 prompt injection、sensitive disclosure、supply chain、excessive agency、vector/embedding weakness、unbounded consumption 列為核心風險來源。
- 本 repo 目前定位是 release-readiness gate，不是企業級 SAST 或完整資安掃描器。

## Ownership correction（2026-07-05）

- Task 34擁有 reusable bounded AST observations；Phase2 dynamic `00`擁有 call graph、
  dataflow與 execution path artifacts。本計畫只消費，不重建兩者。
- Task 39A擁有 target repo governance/observability capability detection與 profile/projection
  evidence。本計畫只判斷這些 facts放在特定 flow/context中可能造成的 security risk。
- Final Hardening #156擁有 Systograph mapping proposal provider本身的 masked telemetry與
  safe logs。本計畫不觀測 proposal runtime，也不保存 provider prompt/output。

## Scope

- 建立 versioned contextual security rule catalog。
- 將 risk hint 從「component exists」提升到「component + evidence + flow + AST observation」。
- 支援 prompt injection trust boundary、retrieved context handling、vector store access/privacy、tool/excessive agency、dependency/model supply chain 的 static checks。
- 每個 check 必須輸出 rationale、uncertainty、evidence refs、recommended next check。

## Out of scope

- 不做 full control-flow graph。
- 不做 whole-program taint analysis。
- 不做 runtime attack simulation。
- 不做 CVE vulnerability scanner。
- 不讓 LLM 決定 severity。
- 不重做 governance/observability capability detection或 Systograph proposal observability。

### Task 1: Define contextual rule catalog

**Files:**
- Create: `src/systograph/core/rules/contextual_security_rules.toml`
- Create: `src/systograph/core/services/contextual_security_rule_loader.py`
- Test: `tests/unit/core/test_contextual_security_rule_loader.py`

- [ ] **Step 1: Write schema validation tests**

Required rule fields:

```text
id
title
severity
llm_risk_category
required_evidence
optional_evidence
negative_evidence
rationale
uncertainty
recommendation
```

- [ ] **Step 2: Reject duplicate ids and unknown severity**
- [ ] **Step 3: Add initial OWASP-aligned rules**

Initial categories:

```text
prompt_injection
sensitive_information_disclosure
supply_chain
excessive_agency
vector_embedding_weakness
unbounded_consumption
```

### Task 2: Build evidence graph inputs

**Files:**
- Create: `src/systograph/core/services/security_evidence_graph_service.py`
- Test: `tests/unit/core/test_security_evidence_graph_service.py`

- [ ] **Step 1: Normalize components, endpoints, flows, evidence, AST observations into a read-only graph**
- [ ] **Step 1A: Consume Task 39A governance refs when present；absence不得由本 engine補造 capability facts**
- [ ] **Step 2: Ensure graph ids reference canonical map ids only**
- [ ] **Step 3: Reject dangling evidence refs in tests**
- [ ] **Step 4: Do not copy raw snippets into graph nodes**

### Task 3: Evaluate contextual risk hints

**Files:**
- Create: `src/systograph/core/services/contextual_security_engine.py`
- Modify: `src/systograph/core/services/risk_hint_service.py`
- Test: `tests/unit/core/test_contextual_security_engine.py`
- Test: `tests/integration/test_phase14_endpoints_risk_hints_flows_behaviors.py`

- [ ] **Step 1: Write failing tests for prompt injection trust boundary**
- [ ] **Step 2: Write failing tests for vector store privacy exposure**
- [ ] **Step 3: Write failing tests for excessive agency/tool action hints**
- [ ] **Step 4: Implement rule matching with explicit uncertainty**
- [ ] **Step 5: Ensure outputs are deterministic sorted by severity/id**

### Task 4: Add calibration fixtures

**Files:**
- Create: `tests/fixtures/rag_projects/security_engine_calibration_rag/`
- Test: `tests/integration/test_contextual_security_engine_behaviors.py`

- [ ] **Step 1: Add positive fixture with untrusted retrieved context to LLM**
- [ ] **Step 2: Add guarded fixture with input/output guardrails and citations**
- [ ] **Step 3: Add vector store fixture with local persistence and missing retention policy**
- [ ] **Step 4: Assert false-positive reducing negative evidence works**

### Task 5: Update report wording

**Files:**
- Modify: `docs/API-GUIDE.md`
- Modify: `docs/work/Timmy/schedule/plan/finish/14-derive-endpoints-risk-hints-and-flows.md`

- [ ] **Step 1: Document contextual hints as static readiness warnings**
- [ ] **Step 2: Avoid wording that claims vulnerability proof**
- [ ] **Step 3: Explain evidence/rationale/uncertainty to frontend**

## Verification

```bash
.venv/bin/pytest tests/unit/core/test_contextual_security_rule_loader.py tests/unit/core/test_contextual_security_engine.py tests/integration/test_contextual_security_engine_behaviors.py -v
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

## Acceptance Criteria

- Contextual rules are versioned, validated, and deterministic.
- Risk hints cite actual evidence/flow/AST observations.
- Guardrail/citation negative evidence can reduce severity only when deterministic evidence supports it.
- Engine does not read filesystem, call network, or ask an LLM.
- Output wording clearly states uncertainty.

## Dependencies and Follow-ups

- 依賴 Phase2 active v2/evidence contract與 dynamic `00` static execution semantics。
- Task 34提供 optional AST observations；Task 39A提供 governance/observability capability
  evidence。兩者缺失時只能降級/標 limitation，不能猜測。
- #156是 Systograph自身 proposal telemetry hardening，與 target repo security engine分離。
- Phase5 Task 42只 render backend risk/readiness projection，不在 frontend重算 security rules。
