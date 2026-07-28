# Bounded AST Code Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在既有 regex code pattern provider 上加入 bounded AST extraction foundation，降低多行 call、decorator、method chain、註解/字串誤判。

**Architecture:** AST extraction 只處理 `FileInventory` 授權的小範圍檔案，不建立 whole-repo call graph，不讓 AI 產生 scanner facts。第一階段以 Python stdlib `ast` 建立安全基礎；Tree-sitter 為後續可選 adapter，必須先通過 dependency/CI/cross-platform gate。

**Tech Stack:** Python `ast`, optional Tree-sitter adapter later, pytest, TOML rule catalogs.

---

## 最新狀態（2026-06-18）

- `CodePatternProvider` 已使用 external TOML rule catalog + regex。
- Task 21 已有 bounded detail/code path scan，但不是 general AST provider。
- `pyproject.toml` 尚無 Tree-sitter、Semgrep 或 ast-grep dependency。
- Tree-sitter 官方 query 以 AST S-expression pattern 表達；Semgrep rule catalog 可作 rule schema 參考，但此任務不引入 Semgrep runtime。

## Ownership correction with Phase2 dynamic `00`（2026-07-05）

Phase2 dynamic `00` 已擁有 architecture-oriented static execution mapping：entrypoint、
bounded call graph、shallow dataflow、execution path recovery與
`call_graph.json` / `dataflow_hints.json` / `execution_paths.json`。Task 34不得建立第二套
call graph或 execution artifact truth。

Task 34只擁有 **reusable bounded AST observations**：imports、decorators、class/function/call
sites、source locations與 parse warnings，供 providers、dynamic `00`、Task 35與 specialized
capability detectors消費。實作前必須先檢查 dynamic `00` 已建立的 parser/helper/protocol：

- 已有可重用 boundary：extend / extract common module。
- 尚無 reusable boundary：新增 narrow AST observation service。
- 禁止同時保留兩套 Python AST visitor與不同 evidence id語意。

## Scope

- 新增 AST extraction protocol 與 Python AST adapter。
- 支援 FastAPI route decorator、class instantiation、function call、method call、import alias resolution 的 bounded evidence。
- Rule catalog 支援 `engine = "regex"` 與 `engine = "python_ast"`。
- Regex 與 AST facts 共用 `ProviderScanResult`、`ScanFact`、`Evidence` contract。

## Out of scope

- 不做 whole-repo call graph。
- 不輸出或擁有 `call_graph.json`、`dataflow_hints.json`、`execution_paths.json`、
  `execution_map.mmd`；這些屬 dynamic `00`。
- 不做 taint analysis；那屬 Task 35。
- 不引入外部 binary。
- 不讓 Semgrep/Tree-sitter output 直接變 canonical facts。
- 不移除所有 regex rule；需逐步遷移。

### Task 1: Reuse or introduce one AST observation protocol

**Files:**
- Create or extend: shared bounded AST observation service selected after dynamic `00` inventory
- Test: `tests/unit/core/test_ast_extraction_service.py`

- [ ] **Step 1: Characterize dynamic `00` AST helpers and prove no duplicate parser/service is introduced**
- [ ] **Step 2: Define shared AST observation result models**

Required fields:

```text
engine
rule_id
file
line_start
line_end
symbol
call_name
qualifier
snippet
parse_warnings
```

- [ ] **Step 3: Write tests for parse failure**

Malformed Python must return a parse warning, not exception, and must not fall back to AI guessing.

- [ ] **Step 4: Implement or extend the single Python AST visitor for imports, calls, decorators, class defs**

Keep snippets bounded through existing snippet/masking policy.

### Task 2: Extend rule catalog schema

**Files:**
- Modify: `src/systograph/core/services/rule_catalog_loader.py`
- Modify: `src/systograph/core/rules/code_pattern_rules.toml`
- Test: `tests/unit/core/test_rule_catalog_loader.py`

- [ ] **Step 1: Add failing tests for `engine = "python_ast"`**
- [ ] **Step 2: Validate required fields by engine**
- [ ] **Step 3: Reject unknown engine values**
- [ ] **Step 4: Keep existing regex rules backward-compatible**

### Task 3: Wire AST extraction into `CodePatternProvider`

**Files:**
- Modify: `src/systograph/core/providers/code_pattern_provider.py`
- Test: `tests/unit/core/test_code_pattern_provider.py`
- Test: `tests/integration/test_phase11_code_pattern_provider_behaviors.py`

- [ ] **Step 1: Add tests for multi-line calls and decorators**
- [ ] **Step 2: Add tests showing comments/strings no longer trigger AST rules**
- [ ] **Step 3: Emit AST facts with same evidence/id conventions as regex facts**
- [ ] **Step 4: Verify provider still respects file size, binary, and inventory path guards**

### Task 4: Migrate only high-value rules

**Files:**
- Modify: `src/systograph/core/rules/code_pattern_rules.toml`
- Test: `tests/integration/test_phase13_component_detection_behaviors.py`

- [ ] **Step 1: Migrate FastAPI route detection**
- [ ] **Step 2: Migrate common LLM call detection**
- [ ] **Step 3: Migrate retriever/vector store instantiation detection**
- [ ] **Step 4: Keep regex fallback for languages without AST adapter**

### Task 5: Document Tree-sitter/Semgrep future adapter boundary

**Files:**
- Modify: `docs/work/Timmy/schedule/plan/unfinish/phase4-scanner-expansion/35-build-contextual-security-engine.md`
- Modify: `docs/API-GUIDE.md` only if evidence fields change

- [ ] **Step 1: Document that Tree-sitter is optional and gated**
- [ ] **Step 2: Document no whole-repo call graph in this task**
- [ ] **Step 3: Document that AST facts are still static observations, not runtime proof**
- [ ] **Step 4: Document that dynamic `00` alone owns execution ordering and static execution artifacts**

## Verification

```bash
.venv/bin/pytest tests/unit/core/test_ast_extraction_service.py tests/unit/core/test_code_pattern_provider.py tests/integration/test_phase11_code_pattern_provider_behaviors.py -v
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

## Acceptance Criteria

- Python AST extraction reduces false positives from comments/strings for migrated rules.
- Multi-line calls/decorators are detected with bounded evidence.
- Existing regex behavior remains backward-compatible.
- No external binary or network access is required.
- No AI-generated scanner facts are introduced.
- Dynamic `00` and Task 34 share one bounded AST observation/evidence boundary；Task 34不建立第二套 call graph或 execution artifacts。
