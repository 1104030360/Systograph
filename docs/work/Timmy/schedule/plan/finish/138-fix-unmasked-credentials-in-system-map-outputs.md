# GitHub #138 Unmasked Credentials Implementation Plan

> **Execution rule:** Follow TDD. Every production behavior change must first
> have a focused failing regression test.

**GitHub Issue:** https://github.com/1104030360/Local-AI-Health-Doctor/issues/138

**Goal:** 補齊 secret masking，避免 DSN URL userinfo、`PASSWD` / `PWD`、
無底線 `APIKEY` 等機密以明文進入 `ai_system_map.json`、Markdown、
Viewer、trace、proposal evidence、logs 或 snapshots。

**Architecture:** 保留 shared `SecretMaskingService` 公開介面；在 Python
內建立不可移除的 masking baseline，並新增獨立於 masking 判斷的
URL credential validation。此 issue 不將安全基線外部化成可覆寫 TOML。

**Tech Stack:** Python `urllib.parse`, bounded regex discovery, Pydantic v2,
pytest, existing scanner/output pipeline.

---

## 評估結論（2026-06-22）

原始計畫方向正確，但不足以直接執行，已補強以下缺口：

1. URL credential 不應只依賴單一 regex replacement；應比照 pip，
   使用 `urlsplit()` / `urlunsplit()` 結構化處理 netloc。
2. 除了 `user:password@host`，也要處理 username-only token
   `token@host`；有 password 時可保留 username，沒有 password 時
   username 本身視為 credential。
3. Canonical validation 必須有獨立 URL credential detector，不能只
   再呼叫 `SecretMaskingService.contains_unmasked_secret()`。
4. Acceptance criteria 提到的 JSON、Markdown、Viewer、trace、
   proposal、logs、snapshots 必須測真正 consumer path。
5. `QueryTraceService` 的 error message 目前沒有經 masking，需納入修補。
6. 不把 #153 的短 secret 顯示比例與 #154 的 entropy detector 混入
   本次；避免擴大 Critical hotfix。

### 外部與開源實作依據

- OWASP Logging Cheat Sheet：session identifiers、access tokens、
  authentication passwords、database connection strings、encryption keys
  等不得直接寫入 logs，應移除、遮罩或 sanitize；共用 logging module
  必須可完整測試。
  - https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html
- pip `redact_auth_from_url()`：使用 `urlsplit()` / `urlunsplit()` 處理
  URL netloc；有 password 時保留 username 並遮罩 password，只有
  username 時遮罩 username。
  - https://github.com/pypa/pip/blob/main/src/pip/_internal/utils/misc.py
- Yelp `detect-secrets`：
  - `KeywordDetector` 明確涵蓋 `api_?key`、`passwd`、`pwd`。
  - `BasicAuthDetector` 將 `scheme://user:password@host` 視為 credential。
  - https://github.com/Yelp/detect-secrets/blob/master/detect_secrets/plugins/keyword.py
  - https://github.com/Yelp/detect-secrets/blob/master/detect_secrets/plugins/basic_auth.py
- Gitleaks 支援 TOML rules，但 custom config 可取代、覆寫或停用 default
  rules。KAI-Mind 的輸出安全基線不可由被掃描專案或一般 runtime config
  弱化，因此本 issue 不採 Gitleaks 的可覆寫模式。
  - https://github.com/gitleaks/gitleaks#configuration

---

## 問題摘要

### 白話結論

> 遮罩器只認得部分憑證長相；沒認出的憑證又會通過使用相同規則的
> 安全驗證，最後被當成普通文字寫進所有輸出。

### 資料流

```text
.env / YAML / Compose / runtime error
        ↓
解析出 key + value
        ↓
SecretMaskingService 沒認出
        ↓
明文進入 Evidence / Endpoint / Trace error
        ↓
Validation 使用相同規則，也沒認出
        ↓
JSON / API / Viewer / Markdown / proposal / logs / snapshots
```

### 根本原因

1. `SECRET_KEY_MARKERS` 缺少 `PASSWD`、`PWD`、無底線 `APIKEY` 等變形。
2. Key 比對只做 `key.upper()` 後 substring，未移除 `_`、`-`、`.`。
3. 沒有處理 URL userinfo。
4. Canonical validation 與 masking 共用相同 blind spot。
5. Trace error message 未走 shared masking path。

---

## 設計決策

### Python vs TOML

本次維持 Python 安全基線：

- `src/kai_mind/core/services/secret_masking_service.py`
- `src/kai_mind/core/services/secret_validation_service.py`

理由：

- 這是所有 output 都不可繞過的安全 invariant，不是可由使用者調整的
  detection metadata。
- 現有 `RuleCatalogLoader` 對缺少 section 會回傳空 list；若直接套用
  secret catalog，存在 semantic fail-open 風險。
- TOML rule extraction 可另開 safe refactor，但只能 additive，不能移除
  Python baseline，也不能由 scanned project override。

### Key marker policy

Key 先 uppercase，再移除非英數字元：

```text
DB_PASSWD       -> DBPASSWD
MYAPIKEY        -> MYAPIKEY
openai-api-key  -> OPENAIAPIKEY
```

本 issue 必須涵蓋：

- `APIKEY`
- `TOKEN`
- `SECRET`
- `PASSWORD`
- `PASSWD`
- `PWD`
- `BEARER`
- `AUTH`
- `CREDENTIAL`
- `PRIVATEKEY`
- `ACCESSKEY`

不在本 issue 廣泛加入 `SESSION` 或 `COOKIE` marker，避免把
`SESSION_COOKIE_NAME`、`COOKIE_DOMAIN` 等非機密設定整體遮罩。更廣泛的
heuristics 由 #154 另行處理。

### URL credential policy

- `scheme://user:password@host`：
  保留 scheme、username、host，password 改成 `[MASKED]`。
- `scheme://:password@host`：
  保留空 username 與 host，password 改成 `[MASKED]`。
- `scheme://token@host`：
  username 本身可能是 token，改成 `[MASKED]`。
- 支援 PostgreSQL、Redis、MongoDB、HTTP(S) 及合法的
  `scheme+driver://`。
- 保留 path、query、fragment，讓 release-readiness evidence 仍可判讀。
- malformed URL 不得造成 scanner crash，也不得在錯誤訊息回顯 raw value。

### Out of scope

- Git history secret scanning。
- Enterprise DLP。
- Secret rotation。
- LLM secret classification。
- #153 的 9–16 字元 full-mask policy。
- #154 的 entropy / opaque value heuristic。
- Runtime user-provided masking catalog。

---

## Task 1: Write RED regression tests

### 1.1 Secret key normalization

**Modify:** `tests/unit/core/test_secret_masking_service.py`

Add parametrized cases:

- `DB_PASSWD`
- `DB_PWD`
- `MYAPIKEY`
- `ACCESSKEY`
- `PRIVATE-KEY`
- `SERVICE.CREDENTIAL`

Assertions:

- raw value does not remain。
- key name remains visible where input is key/value text。
- `CLIENT_SECRET` existing behavior remains protected。

### 1.2 URL userinfo masking

**Modify:** `tests/unit/core/test_secret_masking_service.py`

Add cases:

- PostgreSQL `user:password@host`
- Redis `:password@host`
- MongoDB `user:password@host`
- HTTP service URL
- username-only token
- percent-encoded password
- IPv6 host
- URL embedded in arbitrary error/config text

Add non-secret controls:

- `http://localhost:6333`
- URL without userinfo
- route/model/component identifiers

### 1.3 Independent canonical validation

**Modify:** `tests/unit/core/test_system_map_validation.py`

- Raw URL credentials in `Evidence.value` and `Evidence.snippet` are rejected。
- Validation error includes only JSON path/type，不得包含 raw credential。
- Inject a deliberately blind masking service and prove URL credentials are
  still rejected by the independent validator。
- Masked URL userinfo remains accepted。

### 1.4 Consumer-path regressions

**Modify/Create:**

- `tests/integration/test_map_build_service.py`
- `tests/unit/core/test_query_trace_service.py`
- `tests/unit/core/test_mapping_evidence_packet_builder.py`
- `tests/unit/core/test_logging_service.py`
- `tests/contracts/test_secret_snapshot_safety.py`
- fixture under
  `tests/fixtures/rag_projects/secret_masking_regression_rag/`

Assert synthetic raw credentials are absent from:

- canonical JSON artifact
- `MapBuildResult` API serialization
- Viewer payload and evidence details
- Markdown endpoint output
- query trace error event
- mapping proposal evidence packet
- structured log `event_data`
- snapshot safety input

### RED verification

```bash
.venv/bin/pytest \
  tests/unit/core/test_secret_masking_service.py \
  tests/unit/core/test_system_map_validation.py \
  tests/unit/core/test_query_trace_service.py \
  tests/unit/core/test_mapping_evidence_packet_builder.py \
  tests/unit/core/test_logging_service.py \
  tests/contracts/test_secret_snapshot_safety.py \
  tests/integration/test_map_build_service.py -v
```

Tests must fail because the current implementation leaks the synthetic values。

---

## Task 2: Implement shared masking behavior

**Modify:** `src/kai_mind/core/services/secret_masking_service.py`

1. Add one canonical key normalization helper。
2. Remove duplicated hard-coded marker matching from `KEY_VALUE_RE`; capture
   assignment-like keys generically and decide through `_is_secret_key()`。
3. Discover URL-like spans with a bounded regex，then parse and reconstruct each
   URL using `urllib.parse.urlsplit()` / `urlunsplit()`。
4. Fully mask URL password/token userinfo; do not use the short-secret
   prefix/suffix policy for URL credentials。
5. Ensure `mask_value()`、`mask_text()`、`mask_json_like()` and
   `contains_unmasked_secret()` use the corrected behavior。
6. Preserve existing public method signatures and deterministic output。

---

## Task 3: Add independent URL credential validation

**Create:** `src/kai_mind/core/services/secret_validation_service.py`

**Modify:** `src/kai_mind/core/services/system_map_validation_service.py`

1. Implement a small deterministic validator that detects unmasked URL userinfo
   without calling `SecretMaskingService`。
2. Run it for every string leaf before accepting canonical output。
3. Treat `[MASKED]` URL userinfo as safe。
4. Fail closed with sanitized path-only errors。
5. Keep the existing masker-backed token/key checks as a separate first-line
   detector；this task only makes URL credential defense independent。

---

## Task 4: Close remaining output bypass

**Modify:** `src/kai_mind/core/services/query_trace_service.py`

- Mask provider `error_type` and `error_message` before putting them into
  `QueryTraceEvent.error`。
- Preserve stable generic errors such as `Timeout after 30s`。
- Do not include raw endpoint credentials in any trace event。

Other consumers already call `SecretMaskingService`; their regression tests
prove the shared fix reaches them without adding duplicate masking logic。

---

## Task 5: Documentation and handoff

**Create:**

- `docs/work/Timmy/schedule/todo/2026-06-22-phase138-secret-masking-TODO.md`
- `docs/work/Timmy/schedule/report/2026-06-22-phase138-secret-masking-REP.md`

**Update when implementation completes:**

- Move this plan from `plan/unfinish/` to `plan/finish/`。
- Record exact RED/GREEN/full-suite commands and results。
- Do not update `AGENTS.md`；project structure and long-term rules do not change。
- No API contract documentation change is required because no endpoint or JSON
  schema is added/removed；only unsafe values become masked/rejected。

---

## Verification

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -p no:cacheprovider \
  tests/unit/core/test_secret_masking_service.py \
  tests/unit/core/test_system_map_validation.py \
  tests/unit/core/test_query_trace_service.py \
  tests/unit/core/test_mapping_evidence_packet_builder.py \
  tests/unit/core/test_logging_service.py \
  tests/contracts/test_secret_snapshot_safety.py \
  tests/integration/test_map_build_service.py -v

PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -p no:cacheprovider
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

Re-run the original synthetic reproduction and assert:

- build status remains `ok` for valid projects。
- raw regression credentials are absent from JSON、Markdown、Viewer、trace、
  proposal、logs、snapshots。
- raw URL credential submitted directly to canonical validation is rejected
  before artifact write。

---

## Acceptance Criteria

- Raw DSN passwords、username-only URL tokens、`DB_PASSWD`、`DB_PWD`、
  `MYAPIKEY` values do not appear in any declared output surface。
- Existing `CLIENT_SECRET` and known token signatures remain protected。
- URL without userinfo and ordinary localhost endpoints remain unchanged。
- Canonical validation independently rejects raw URL credentials before write。
- Validation and error messages never echo the raw credential。
- No public API/schema change and no TOML masking override are introduced。
- Focused tests、full test suite、Ruff、mypy、`git diff --check` all pass。

---

## Completion record（2026-06-22）

- Plan was refined before implementation because URL structural masking、
  independent validation、QueryTrace error masking、and consumer-path tests were
  missing from the original version.
- Implementation completed on branch `fix/138-secret-masking` in an isolated
  worktree.
- Report: `docs/work/Timmy/schedule/report/2026-06-22-phase138-secret-masking-REP.md`
- Full verification:
  - RED focused suite: `21 failed, 104 passed in 0.96s`
  - GREEN focused suite: `139 passed in 0.87s`
  - Full pytest: `468 passed in 5.03s`
  - Ruff: `All checks passed!`
  - Mypy: `Success: no issues found in 142 source files`
  - `git diff --check`: passed
