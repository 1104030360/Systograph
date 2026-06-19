# GitHub #141 Compose Validation Isolation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**GitHub Issue:** https://github.com/1104030360/Local-AI-Health-Doctor/issues/141

**Goal:** 避免合法 docker-compose volume 造成 validation crash，並讓 volumes、env_file、image 等非 environment evidence 經一致遮罩與路徑安全處理。

**Architecture:** Compose provider facts 必須先完成 masking/path redaction，再進 normalize/validate。`MapBuildService` 對 normalize/validate/write failure 應回 structured error，不應向 CLI/web 冒 traceback。

**Tech Stack:** PyYAML, pytest, existing `DockerComposeProvider`, `MapBuildService`, `OutputArtifactProvider`.

---

## Source

- GitHub issue #141, assignee Timmy.
- Origin: Backend findings H-3.
- Primary files: `src/kai_mind/core/providers/docker_compose_provider.py`, `src/kai_mind/core/services/map_build_service.py`.

### Task 1: Reproduce compose crash

**Files:**
- Modify: `tests/unit/core/test_docker_compose_provider.py`
- Modify: `tests/integration/test_map_build_service.py`

- [ ] **Step 1: Add compose fixture with `./secrets:/run/secrets:ro`**
- [ ] **Step 2: Assert build does not raise `SystemMapValidationError`**
- [ ] **Step 3: Assert evidence value is masked/redacted and still useful**

### Task 2: Mask non-env compose fields

**Files:**
- Modify: `src/kai_mind/core/providers/docker_compose_provider.py`

- [ ] **Step 1: Apply masking to volumes, env_file, image, networks, and parse messages**
- [ ] **Step 2: Apply path redaction to host-like paths**
- [ ] **Step 3: Keep service names and container paths only when safe**

### Task 3: Isolate validation failures

**Files:**
- Modify: `src/kai_mind/core/services/map_build_service.py`
- Modify: `src/kai_mind/core/providers/output_artifact_provider.py`
- Test: `tests/unit/core/test_output_artifact_provider.py`

- [ ] **Step 1: Catch validation failures at build boundary**
- [ ] **Step 2: Return structured safe error result**
- [ ] **Step 3: Write safe failure artifact without traceback or raw evidence**

## Verification

```bash
.venv/bin/pytest tests/unit/core/test_docker_compose_provider.py tests/integration/test_map_build_service.py tests/unit/core/test_output_artifact_provider.py -v
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

## Acceptance Criteria

- Legitimate compose volume strings do not crash validation.
- Non-env compose evidence never leaks raw secret-like values or unmanaged absolute paths.
- Validation failure returns safe structured result.

