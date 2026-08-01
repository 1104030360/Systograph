# 2026-06-22 Phase138 Secret Masking REP

## 結論

- 原始 plan 方向正確，但直接執行會漏掉 URL credential 結構化處理、
  username-only token、independent validation、QueryTrace error masking、
  以及真正 consumer path 的 regression tests。
- 已 refine plan，並依 refine 後的 plan 完成 implementation。
- 本 issue 不改成 TOML rule baseline。TOML 可以是後續 additive catalog，
  但不可取代 Python 內不可繞過的 output-safety invariant。
- 變更沒有新增或移除 public API / JSON schema 欄位；只讓 unsafe raw
  credential 被遮罩或被 canonical validation 拒絕。

## 外部與開源依據

- OWASP Logging Cheat Sheet：authentication passwords、access tokens、
  database connection strings、encryption keys 等不得直接記錄，應移除、
  遮罩或 sanitize。
  - https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html
- OWASP AI Agent Security Cheat Sheet：對 sensitive leakage 需要獨立驗證、
  fail closed 與 output filtering。
  - https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html
- pip `redact_auth_from_url()`：使用 `urlsplit()` / `urlunsplit()` 對 URL
  userinfo 做結構化 redaction；有 password 時保留 username，username-only
  token 則遮罩 username。
  - https://github.com/pypa/pip/blob/main/src/pip/_internal/utils/misc.py
- Yelp detect-secrets：
  - `KeywordDetector` 涵蓋 `api_?key`、`passwd`、`pwd` 等 key pattern。
  - `BasicAuthDetector` 偵測 `scheme://user:password@host`。
  - https://github.com/Yelp/detect-secrets/blob/master/detect_secrets/plugins/keyword.py
  - https://github.com/Yelp/detect-secrets/blob/master/detect_secrets/plugins/basic_auth.py
- Gitleaks 支援 TOML config，但 custom config 可以 replace / extend /
  disable default rules；因此不適合拿來當不可繞過的 Systograph output-safety
  baseline。
  - https://github.com/gitleaks/gitleaks#configuration

## 問題原因

白話來說，舊實作只認得一部分 secret 長相。像 `PASSWORD`、`TOKEN` 這類
比較標準的 key 容易被遮罩，但 `PASSWD`、`PWD`、無底線 `APIKEY`、URL
裡的 `user:password@host` 或 `token@host` 沒有被完整識別。

更大的問題是 canonical validation 也依賴同一套 blind spot。也就是說：

```text
掃描到 raw credential
        ↓
SecretMaskingService 沒認出
        ↓
Evidence / Trace / output model 帶著 raw value
        ↓
SystemMapValidationService 用相同規則檢查，也沒認出
        ↓
JSON / Markdown / API / Viewer / proposal / log / snapshot 可能都外洩
```

另外，`QueryTraceService` 在記錄 provider error type / message 時，原本沒有
在組出 trace event 前先走 shared masking path，會形成另一條 bypass。

## 實作內容

### Production code

- `src/systograph/core/services/secret_masking_service.py`
  - 將 key 判斷正規化為 uppercase 後移除非英數字元。
  - 補齊 `APIKEY`、`PASSWD`、`PWD`、`PRIVATEKEY`、`ACCESSKEY`、
    `CREDENTIAL` 等 marker。
  - 新增 URL candidate discovery，並用 `urlsplit()` / `urlunsplit()`
    結構化遮罩 URL userinfo。
  - 支援 `user:password@host`、`:password@host`、`token@host`、
    percent-encoded password、IPv6 host、embedded URL text。
- `src/systograph/core/services/secret_validation_service.py`
  - 新增獨立 URL credential validator，不呼叫 masking service。
  - canonical validation 可在 masker blind spot 時仍拒絕 raw URL userinfo。
- `src/systograph/core/services/system_map_validation_service.py`
  - validation 先用 independent validator 檢查 URL credentials，再跑既有
    key/token-based secret check。
  - error message 維持 path-only，不回顯 raw credential。
- `src/systograph/core/services/query_trace_service.py`
  - provider error type / message 進 trace event 與 error reason 前先遮罩。
- `src/systograph/core/services/path_safety_service.py`
  - 修正 Windows path regex，避免把 `postgresql://...` 這類 URL scheme
    誤判成 Windows drive path，造成 URL 被 path redaction 打壞。

### Tests / fixtures

- `tests/unit/core/test_secret_masking_service.py`
- `tests/unit/core/test_system_map_validation.py`
- `tests/unit/core/test_query_trace_service.py`
- `tests/unit/core/test_mapping_evidence_packet_builder.py`
- `tests/unit/core/test_logging_service.py`
- `tests/unit/core/test_cross_platform_paths.py`
- `tests/contracts/test_secret_snapshot_safety.py`
- `tests/integration/test_map_build_service.py`
- `tests/unit/test_rag_project_fixtures_contract.py`
- `tests/fixtures/rag_projects/secret_masking_regression_rag/`
- `tests/helpers/fixtures.py`

Coverage 包含 canonical JSON artifact、Markdown、`MapBuildResult` API
serialization、`ai_system_map` model dump、Viewer payload、QueryTrace error、
mapping proposal evidence packet、structured log `event_data`、snapshot safety。

## TDD 與驗證紀錄

### Baseline

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -p no:cacheprovider
438 passed in 6.88s
```

### RED

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -p no:cacheprovider \
  tests/unit/core/test_secret_masking_service.py \
  tests/unit/core/test_system_map_validation.py \
  tests/unit/core/test_query_trace_service.py \
  tests/unit/core/test_mapping_evidence_packet_builder.py \
  tests/unit/core/test_logging_service.py \
  tests/contracts/test_secret_snapshot_safety.py \
  tests/integration/test_map_build_service.py \
  tests/unit/test_rag_project_fixtures_contract.py -q

21 failed, 104 passed in 0.96s
```

Failures 對應 key marker 變形、URL userinfo、independent validation、
trace error、proposal/log/snapshot/integration consumer path，符合預期。

### GREEN focused

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -p no:cacheprovider \
  tests/unit/core/test_secret_masking_service.py \
  tests/unit/core/test_system_map_validation.py \
  tests/unit/core/test_query_trace_service.py \
  tests/unit/core/test_mapping_evidence_packet_builder.py \
  tests/unit/core/test_logging_service.py \
  tests/unit/core/test_cross_platform_paths.py \
  tests/contracts/test_secret_snapshot_safety.py \
  tests/integration/test_map_build_service.py \
  tests/unit/test_rag_project_fixtures_contract.py -q

139 passed in 0.87s
```

### Full verification

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -p no:cacheprovider
468 passed in 5.03s
```

```text
.venv/bin/ruff check .
All checks passed!
```

```text
.venv/bin/mypy src tests
Success: no issues found in 142 source files
```

```text
git diff --check
passed
```

### Smoke reproducer

Re-run a boolean-only synthetic leak reproducer without printing raw secret values:

```json
{
  "direct_mask_blocks_raw": true,
  "map_outputs_block_raw": true,
  "validation_error_safe": true,
  "validation_rejects_raw_url": true
}
```

### Raw synthetic value scan

Changed-file scan confirmed raw synthetic credentials are only present in
allowed test / fixture / plan files and not in generated artifacts or diagnostics:

```json
{
  "ok": true,
  "raw_synthetic_values_outside_allowed_test_or_plan_files": []
}
```

## Subagent 狀態

- 已依使用者要求嘗試派發 `security-privacy` 與 `architecture-design` subagents。
- 兩個 subagent 都因目前環境使用量限制而失敗，沒有產生可採信 review output。
- 本次結論不依賴 subagent 輸出，而是依實際 code trace、外部來源、RED/GREEN
  測試與完整驗證結果。

## 最終狀態

- GitHub #138 的已知 raw credential output bypass 已用 regression tests 固定。
- Mandatory masking baseline 留在 Python，不引入 TOML override。
- Canonical validation 對 URL credential 有 independent fail-closed guard。
- QueryTrace、proposal、log、snapshot、JSON、Markdown、API、Viewer output
  都有測試覆蓋。
- 原始 checkout 的既有 user change 未被覆寫；本次變更位於 isolated worktree
  `fix/138-secret-masking`。

## PR review follow-up（2026-06-22）

- Addressed reviewer P2 finding for Windows double-slash drive paths.
- Root cause: `WINDOWS_LOCAL_PATH_RE` used `(?!/)` to avoid treating
  URL schemes as Windows drive paths, but that also skipped valid Windows
  absolute paths such as `D://work/project/src/api.py`.
- Fix: keep the existing negative lookbehind that prevents matching inside
  multi-letter URL schemes, and remove the broad double-slash exclusion so
  single-letter Windows drive paths remain redacted.
- Added regression coverage proving `D://work/project/src/api.py` is redacted
  while `postgresql://demo:[MASKED]@db.example:5432/app` stays intact.

Validation:

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -p no:cacheprovider \
  tests/unit/core/test_cross_platform_paths.py::test_path_redaction_keeps_windows_double_slash_drive_paths_masked -q
1 failed before fix
```

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -p no:cacheprovider \
  tests/unit/core/test_cross_platform_paths.py -q
15 passed in 0.02s

PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -p no:cacheprovider
469 passed in 4.81s

.venv/bin/ruff check .
All checks passed!

.venv/bin/ruff format --check src tests
156 files already formatted

.venv/bin/mypy src tests
Success: no issues found in 142 source files

git diff --check
passed
```
