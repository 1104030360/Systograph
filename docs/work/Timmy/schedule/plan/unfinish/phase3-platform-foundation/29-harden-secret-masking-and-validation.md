# Secret Masking and Validation Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修補 shared secret masking 的漏網情境，並建立獨立於 masking 規則的 canonical validation defense。

**Architecture:** `SecretMaskingService` 仍是 providers、reports、viewer、query trace、mapping proposal 共用的遮罩入口；`SystemMapValidationService` 需增加第二道偵測，不可和 masking 完全共用同一套 blind spot。此任務不是完整 secret scanner、DLP 或 secret rotation 產品。

**Tech Stack:** Python regex, Pydantic v2, pytest, existing `SecretMaskingService`, `SystemMapValidationService`.

---

## 最新狀態（2026-07-05）

- Critical #138 已有完成計畫與現行 `SecretValidationService` / canonical validation整合；
  本段舊狀態不得再當成「尚無 independent validation」的 current fact。
- #153/#154 的完整短 secret policy與 independent defense仍應以實際 code/tests重新
  characterization，不能只依 2026-06-18 report重做既有修補。
- Phase2 Plan 03A新增 atomic local JSON repositories、build lineage與 persisted artifact
  metadata；Task 27後續再增加 PostgreSQL adapter。這些新 persistence boundaries都必須套用
  同一套 masking + independent validation contract。
- OWASP LLM Top 10 2025 將 sensitive information disclosure 列為核心風險；本 repo 的 scanner output、proposal prompt、assistant context 都必須先修這條防線。

## Phase2 03A persistence boundary correction

- Plan 03A擁有 local JSON persistence與 complete-build atomic promotion；本計畫不另建
  persistence adapter。
- 本計畫擁有「寫入前安全 gate」：project/scan/build/mapping/history metadata在 local JSON
  或 PostgreSQL落地前，必須經 path redaction、masking與 independent secret validation。
- Validation failure不得留下 partial build、更新 `latest_build_id` 或把 rejected raw value
  寫入 error/log。
- Task 27 PostgreSQL adapter必須重用相同 validation service，不得只相信 DB欄位型別或
  JSONB serialization。

## Scope

- 修補 key marker normalization：`APIKEY`、`PASSWD`、`PWD`、`CREDENTIAL`、`ACCESS_KEY`、`PRIVATE_KEY`、`SESSION`、`COOKIE`。
- 修補 URL userinfo：`postgres://user:pass@host`、`redis://:pass@host`、`mongodb://user:pass@host`。
- 短 secret policy：長度小於等於 16 的 secret-like value 一律 full mask。
- Validation 端增加獨立啟發式，例如 URL userinfo detector、high entropy detector、key/value shape detector。
- 補完整 map build regression，確保 config、compose、proposal、trace、report output 都不含原始 secret。
- 補 local JSON project/scan/build/mapping/history與 PostgreSQL adapter persistence regression。

## Out of scope

- 不掃 git history；該方向需要獨立 issue 與 performance budget。
- 不做企業 DLP 整合。
- 不做 secret rotation 或 remediation。
- 不讓 AI/LLM 判斷 secret。
- 不重作 Plan 03A repository、Apply/build lineage或 Task 27 database adapter。

### Task 1: Extend masking rules with RED tests

**Files:**
- Modify: `src/kai_mind/core/services/secret_masking_service.py`
- Test: `tests/unit/core/test_secret_masking_service.py`

- [ ] **Step 1: Add failing parametrized tests for missed key markers**

Test cases:

```python
@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("DB_PASSWD", "abc123SECRET"),
        ("DB_PWD", "abc123SECRET"),
        ("MYAPIKEY", "sk-example-secret"),
        ("ACCESSKEY", "AKIA1111111111111111"),
        ("SESSION_COOKIE", "session-secret-value"),
    ],
)
def test_secret_key_marker_variants_are_masked(key: str, value: str) -> None:
    service = SecretMaskingService()

    masked = service.mask_value(key=key, value=value)

    assert value not in masked
    assert "[MASKED]" in masked or "..." in masked
```

- [ ] **Step 2: Add failing URL userinfo tests**

```python
@pytest.mark.parametrize(
    "raw",
    [
        "DATABASE_URL=postgresql://admin:SuperSecret123@db:5432/app",
        "REDIS_URL=redis://:MyRedisPass@cache:6379/0",
        "MONGODB_URI=mongodb://root:RootPass99@mongo:27017/db",
        "url: http://admin:pass@qdrant:6333",
    ],
)
def test_url_userinfo_password_is_masked(raw: str) -> None:
    masked = SecretMaskingService().mask_text(raw)

    assert "SuperSecret123" not in masked
    assert "MyRedisPass" not in masked
    assert "RootPass99" not in masked
    assert "admin:pass@" not in masked
```

- [ ] **Step 3: Implement normalized marker matching and URL userinfo masking**

Implementation requirements:

```text
normalize key by uppercasing and removing non-alphanumeric separators
match both API_KEY and APIKEY style markers
mask only password/userinfo segment, preserve scheme and host where safe
never include full original value in parse errors or repr output
```

- [ ] **Step 4: Run focused tests**

```bash
.venv/bin/pytest tests/unit/core/test_secret_masking_service.py -v
```

### Task 2: Fix short secret masking policy

**Files:**
- Modify: `src/kai_mind/core/services/secret_masking_service.py`
- Test: `tests/unit/core/test_secret_masking_service.py`

- [ ] **Step 1: Add failing tests for 9-16 character secrets**

```python
@pytest.mark.parametrize("secret", ["secretpw1", "abc123SECRET", "shortToken123456"])
def test_short_secret_values_are_fully_masked(secret: str) -> None:
    masked = SecretMaskingService().mask_value(key="PASSWORD", value=secret)

    assert secret not in masked
    assert masked == "[MASKED]"
```

- [ ] **Step 2: Change `mask_secret_value()` policy**

Expected policy:

```text
len(value) <= 16 -> [MASKED]
len(value) > 16 -> keep at most 4 prefix and 4 suffix
masked middle must never be shorter than 3 mask characters
```

- [ ] **Step 3: Re-run existing Phase 5 integration tests**

```bash
.venv/bin/pytest tests/unit/core/test_secret_masking_service.py tests/integration/test_phase5_secret_masking_behaviors.py -v
```

### Task 3: Add independent validation defense

**Files:**
- Modify: `src/kai_mind/core/services/system_map_validation_service.py`
- Create: `src/kai_mind/core/services/secret_validation_service.py`
- Test: `tests/unit/core/test_system_map_validation.py`

- [ ] **Step 1: Write failing validator tests for masking blind spots**

```python
def test_validation_rejects_url_userinfo_even_if_masking_missed_it() -> None:
    system_map = valid_minimal_system_map_with_evidence_value(
        "postgresql://admin:SuperSecret123@db:5432/app"
    )

    with pytest.raises(SystemMapValidationError):
        SystemMapValidationService().validate(system_map)
```

- [ ] **Step 2: Implement `SecretValidationService`**

Validation heuristics:

```text
reject URL userinfo with non-empty password
reject key/value shapes where key marker is secret-like and value is not masked
reject high-entropy opaque strings only in fields named value/snippet/detail/message
do not reject localhost URLs, model names, component ids, or route ids
```

- [ ] **Step 3: Wire validation service into `SystemMapValidationService`**

The validation path must run after normal cross-reference checks and before serialization artifacts are considered safe.

- [ ] **Step 4: Run validation tests**

```bash
.venv/bin/pytest tests/unit/core/test_system_map_validation.py -v
```

### Task 4: Add end-to-end regression fixtures

**Files:**
- Modify/Create fixture under: `tests/fixtures/rag_projects/secret_masking_regression_rag/`
- Test: `tests/integration/test_phase5_secret_masking_behaviors.py`
- Test: `tests/integration/test_map_build_service.py`

- [ ] **Step 1: Create fixture with config, env, compose, and source snippets**

Fixture signals:

```text
.env.example with DATABASE_URL and DB_PASSWD
config.yaml with qdrant URL userinfo
docker-compose.yml with REDIS_URL
src/app.py with a fake Authorization bearer string in a comment/string
```

- [ ] **Step 2: Assert `MapBuildService().build()` output contains no raw secret**

Raw strings to reject:

```text
SuperSecret123
MyRedisPass
RootPass99
abc123SECRET
admin:pass@
```

- [ ] **Step 3: Assert scanner still emits useful evidence**

The fix must not solve leakage by deleting all evidence. Assert at least one config fact, one compose fact, and one code pattern fact still exist with masked values.

- [ ] **Step 4: Persist a B1→Apply→B2 lineage through the Plan 03A local JSON adapter and assert project/scan/build/mapping/history files contain no raw regression secret**
- [ ] **Step 5: Add the same repository-contract assertion to Task 27 PostgreSQL adapter tests when that adapter exists**

### Task 5: Update docs and issue handoff notes

**Files:**
- Modify: `docs/API-GUIDE.md`
- Modify: `docs/work/Timmy/schedule/fable-5/find-error/report/2026-06-12-backend-security-ai-findings.md` only if adding resolution notes is explicitly part of that branch

- [ ] **Step 1: Document masking guarantees**
- [ ] **Step 2: Document remaining non-goals: git history, DLP, rotation**
- [ ] **Step 3: Mention that validation is independent from masking patterns**

## Verification

```bash
.venv/bin/pytest tests/unit/core/test_secret_masking_service.py tests/unit/core/test_system_map_validation.py tests/integration/test_phase5_secret_masking_behaviors.py tests/integration/test_map_build_service.py -v
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

## Acceptance Criteria

- `ai_system_map.json`, markdown report, viewer payload, query trace, and mapping proposal evidence never contain the raw regression secrets.
- Short secret values are full masked.
- Validation catches at least one secret-like value that masking would not have caught before this task.
- Existing non-secret localhost endpoints, model names, route names, and component ids are not over-masked.
- No AI/LLM is involved in secret detection.
- Local JSON/PostgreSQL persistence rejects unsafe values before commit and never advances latest build on validation failure.
