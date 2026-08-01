# map-error.json Failure Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增 machine-readable `map-error.json`，讓 CLI/CI 能穩定解析 scan failure，而不只依賴人類閱讀的 `map-error.md`。

**Architecture:** JSON 與 Markdown 必須來自同一個 structured error object，避免兩份輸出 drift。`map-error.json` 是 failure artifact，不取代 canonical successful `ai_system_map.json`。

**Tech Stack:** Pydantic v2, JSON Schema, pytest, existing `OutputArtifactProvider`, `MapBuildService`.

---

## 最新狀態（2026-06-18）

- `OutputArtifactProvider` 目前只有 `map-error.md`。
- `PreconditionError` 已存在，但後續 validation/provider failure 還未形成完整 JSON failure contract。
- GitHub #141、#148、#158 會影響錯誤碼與 failure shape；本任務要在這些錯誤模型穩定後實作。
- 需求來源：Task 6 曾明確延後 `map-error.json`，並要求 JSON/Markdown 來自同一個 structured error object。

## Scope

- 定義 `MapErrorArtifact` model 與 schema。
- `OutputArtifactProvider` 同時寫 `map-error.md` 與 `map-error.json`。
- CLI 與 web route 的 failure handling 可引用同一個 error object。
- 錯誤內容不可包含 full secret、raw source、未遮罩本機絕對路徑、Python exception string。

## Out of scope

- 不改 successful `ai_system_map.json` schema。
- 不建立 GUI error renderer。
- 不把 `map-error.json` 當成 security scan report。

### Task 1: Define the error artifact model

**Files:**
- Create: `src/systograph/core/models/map_error.py`
- Test: `tests/unit/core/test_map_error_model.py`

- [ ] **Step 1: Write failing model tests**

```python
def test_map_error_artifact_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        MapErrorArtifact.model_validate({"schema_version": "map-error/v1", "extra": True})
```

- [ ] **Step 2: Add stable model fields**

Required fields:

```text
schema_version = "map-error/v1"
status = "error"
failure_stage
failure_reason
safe_message
error_code
project_path = "<redacted>" or null
artifacts = object with nullable paths
warnings = []
```

- [ ] **Step 3: Add tests for secret/path rejection**

The model or serializer must reject values containing `/Users/`, `/home/`, `sk-`, URL userinfo, or unmasked bearer tokens.

### Task 2: Write JSON and Markdown from one structured object

**Files:**
- Modify: `src/systograph/core/providers/output_artifact_provider.py`
- Test: `tests/unit/core/test_output_artifact_provider.py`

- [ ] **Step 1: Add failing test that both files are written**

```python
def test_output_provider_writes_json_and_markdown_from_same_error(tmp_path: Path) -> None:
    provider = OutputArtifactProvider()
    output_run = provider.create_run(tmp_path)
    artifact = MapErrorArtifact(...)

    provider.write_map_error(output_run, artifact)

    assert output_run.map_error_path.read_text()
    assert output_run.map_error_json_path.read_text()
```

- [ ] **Step 2: Add `map_error_json_path` to `OutputRun`**

Keep path naming stable:

```text
outputs/<run-id>/map-error.md
outputs/<run-id>/map-error.json
```

- [ ] **Step 3: Make Markdown renderer consume `MapErrorArtifact`**

Do not let markdown build a second independent interpretation.

### Task 3: Integrate with build failure paths

**Files:**
- Modify: `src/systograph/core/services/map_build_service.py`
- Modify: `src/systograph/cli/map_command.py`
- Test: `tests/integration/test_map_build_service.py`
- Test: `tests/cli/test_map_command.py`

- [ ] **Step 1: Write tests for precondition failure JSON**
- [ ] **Step 2: Write tests for validation failure JSON after #141 is fixed**
- [ ] **Step 3: Ensure CLI exits non-zero and prints only safe summary**
- [ ] **Step 4: Assert JSON has stable `error_code` and no exception string**

### Task 4: Add contract artifact and docs

**Files:**
- Create: `schemas/map-error.v1.schema.json`
- Modify: `docs/API-GUIDE.md`
- Test: `tests/contracts/test_map_error_schema.py`

- [ ] **Step 1: Export JSON Schema deterministically**
- [ ] **Step 2: Add contract tests for valid and invalid examples**
- [ ] **Step 3: Document CI usage**

Example CI contract:

```bash
jq -e '.status == "error" and .error_code != null' outputs/*/map-error.json
```

## Verification

```bash
.venv/bin/pytest tests/unit/core/test_map_error_model.py tests/unit/core/test_output_artifact_provider.py tests/contracts/test_map_error_schema.py tests/cli/test_map_command.py -v
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

## Acceptance Criteria

- Every failure that writes `map-error.md` also writes `map-error.json`.
- JSON and Markdown are rendered from the same object.
- `map-error.json` has schema and contract tests.
- Failure artifacts contain no full secret, raw source, unmanaged absolute path, or Python traceback.

