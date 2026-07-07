# Governance and Observability Capability Detection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:test-driven-development` to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** 以 deterministic code/config/dependency/workflow evidence 偵測 target AI system
中的 governance 與 observability capabilities，讓 Phase5 Graph Studio 可顯示 policy、
approval、guardrail、trace、eval、cost/latency 等 evidence-backed overlay。

**Architecture:** 本計畫擴充 scanner facts、profile inference 與 backend projection，不執行
target app、不呼叫 LLM、不從 frontend label 推論能力。Dependency/name-only等 indirect
signals只能為 `partial`；只有可回溯的 wiring/config/code direct evidence才可 `detected`。
Scanner coverage或 mapping不足才使用 `undetermined`。所有 capability
輸出統一使用 `detected / partial / undetermined / not_detected / conflicted` 五態。

**Tech Stack:** Existing providers, Python AST facts from Task 34 when available,
TOML rule metadata, Pydantic v2, pytest fixtures.

---

## Ownership Boundary

### 本計畫擁有

- target repo 的 governance capability facts：approval gate、policy check、input/output
  guardrail、PII/ACL enforcement、rate/budget/stop policy、audit hook。
- target repo 的 observability capability facts：trace instrumentation、eval harness、
  cost/token/latency metrics、structured event/span emission。
- deterministic evidence、profile status、related refs與 GraphViewModel overlay membership。

### 與 Task 35 的分工

`35-build-contextual-security-engine.md` 消費 components、flows、AST observations 與本計畫
提供的 governance evidence，評估 prompt injection、excessive agency、sensitive disclosure 等
contextual **risk hints**。Task 35 不重做 capability detection；本計畫也不宣稱漏洞、severity
或 exploit reachability。

### 與 GitHub #156 / Final Hardening 156 的分工

`156-add-masked-ai-proposal-observability.md` 觀測的是 **KAI-Mind 自己的 mapping proposal
provider**：masked request lifecycle、provider outcome、latency與 safe logs。本計畫掃描的是
**target repo 是否具有 observability/governance architecture**。兩者不得共用 raw prompt、
provider payload 或 secret-bearing telemetry。

## Scope

- Governance / observability 是固定十個 plane之一；39A 產生的 canonical governance
  capability assessments 對位 `governance_observability`。若同一 evidence 同時影響
  `control`、`generation`、`memory_state` 或其他 plane，backend 另提供 cross-plane
  governance lens memberships，不複製 canonical facts。
- Synthetic governance/observability fixtures，不放真實 token、PHI/PII 或外部 endpoint。
- Dependency/config/code/AST rules與 deterministic profile inference。
- 統一 `detected / partial / undetermined / not_detected / conflicted` 五態與
  evidence-strength/depth semantics；review與 confirmed是 lifecycle/decision，不是第六、
  第七個 capability state。
- Backend graph/detail/filter projection；frontend只 render backend result。

## Out of Scope

- 不做 runtime trace、OpenTelemetry collector、eval execution 或 cost billing。
- 不做完整 SAST、DLP、policy engine、compliance certification 或漏洞 exploit proof。
- 不建立 active `ExtensionComponent`；extension subsystems 使用 v2 facts/profile overlay。
- 不更改 KAI-Mind 自身 proposal-provider logging；該工作屬 #156。

## Implementation Tasks

### Task 1: Add deterministic fixtures

**Files:**
- Create: `tests/fixtures/ai_systems/governance_observability_system/`
- Modify: `tests/unit/test_rag_project_fixtures_contract.py`
- Test: `tests/integration/test_governance_observability_capabilities.py`

- [ ] 建立 approval/guardrail/policy/audit/trace/eval/metric synthetic signals。
- [ ] 建立 dependency/name-only fixture，預期 `partial` 而非 `detected`。
- [ ] 建立只覆蓋部分 wiring的 fixture，預期 `partial`；建立正反證據衝突 fixture，預期
  `conflicted`。
- [ ] 建立已完整檢查且無相關 evidence的 fixture，預期 `not_detected`。
- [ ] Fixture 不執行程式、不連網、不含真實 secret或個資。

### Task 2: Add bounded provider and AST rules

**Files:**
- Modify: `src/kai_mind/core/rules/code_pattern_rules.toml`
- Modify: `src/kai_mind/core/rules/dependency_manifest_rules.toml`
- Modify: `src/kai_mind/core/providers/code_pattern_provider.py`
- Test: `tests/unit/core/test_rule_catalog_loader.py`
- Test: `tests/integration/test_governance_observability_capabilities.py`

- [ ] Dependency signal單獨不能證明 runtime wiring。
- [ ] Config/code/AST evidence保留 project-relative path、line/JSON pointer與 rule id。
- [ ] Task 34 尚未可用時保留 regex/config fallback；不得用 AI 補 AST 缺口。

### Task 3: Add Python-owned inference

**Files:**
- Modify: `src/kai_mind/core/services/profile_inference_service.py`
- Modify: `src/kai_mind/core/rules/profile_registry.toml`
- Test: `tests/unit/core/test_profile_inference_service.py`

- [ ] Python實作 trigger、negative evidence、depth與統一五態 status判定。
- [ ] TOML只加入 label、description、axis、default uncertainty與 recommended checks。
- [ ] 不把 trigger conditions、thresholds或 rule chaining移入 TOML。
- [ ] Governance/observability profile rows不得因 capability reference map固定存在而自動
  `detected`。
- [ ] `partial`用於只有 indirect evidence或已有部分 direct evidence但能力 wiring不完整；
  `conflicted`只用於可回溯
  的正反 evidence衝突，兩者不得退化成 confidence score。

### Task 4: Project backend-owned overlays and details

**Files:**
- Modify: `src/kai_mind/core/services/graph_projection_service.py`
- Modify: `src/kai_mind/core/models/viewer.py`
- Test: `tests/unit/core/test_graph_projection_service.py`

- [ ] 提供 governance/observability lens filter memberships、evidence refs與 limitations。
- [ ] Frontend不從 node label、dependency name或 canvas位置自行推論。
- [ ] Static observability detection不得顯示成「這次 request 已被 trace」。

### Task 5: Calibrate with Task 35

- [ ] Task 35可讀取 capability refs，但 risk status/severity仍由 contextual security engine
  依 evidence graph計算。
- [ ] 有 guardrail/approval evidence不代表風險自動消失；必須有對應 flow/negative evidence。
- [ ] 同一 evidence id在 capability finding與 risk hint中可追溯，但不得複製 raw snippet。

## Verification

```bash
.venv/bin/pytest tests/integration/test_governance_observability_capabilities.py -q
.venv/bin/pytest tests/unit/core/test_profile_inference_service.py tests/unit/core/test_graph_projection_service.py -q
.venv/bin/ruff check src tests
.venv/bin/mypy src
git diff --check
```

## Acceptance Criteria

- Governance/observability一律輸出
  `detected / partial / undetermined / not_detected / conflicted`其中一態。
- `detected`均有 deterministic wiring/config/code direct evidence；只有 indirect evidence或
  不完整 direct evidence時使用 `partial`，coverage/mapping不足使用 `undetermined`，
  已完成相關 coverage的 absence使用 `not_detected`，正反證據衝突使用
  `conflicted`，不產生 opaque score。
- Task 35與 #156 ownership清楚，沒有重複 scanner或 telemetry implementation。
- Active v2 output不建立 legacy extension；Graph Studio所需狀態由 backend projection提供。
- Scanner保持 read-only、local-first、bounded且不執行 target system。

## Dependencies and Follow-ups

- 依賴 Phase2 `01A` reference catalog boundary、`02/03` profile lifecycle、`06` backend
  projection與 Plan 14 validation baseline。
- Task 31提供 synthetic fixture corpus；Task 34提供 optional AST facts；Task 35消費本計畫
  evidence做 contextual risk interpretation。
- Task 39可平行增加 multimodal capability evidence。
- Phase5 Task 42消費本計畫 backend projection建立 governance/observability lenses。
