# Phase 2 Plan 13 ai-system-map/v2 Active Cutover Report

**Date:** 2026-07-17  
**Status:** backend complete / frontend handoff required  
**Scope:** Plan 13 backend Tasks 1-7；frontend維持原始版本

## 結論

正常 CLI/API build 已切為 `ai-system-map/v2`，`MapBuildResult.ai_system_map` 是唯一
normalized canonical truth。Historical v1 仍經 `CanonicalMapLoader` + adapter 可讀；v1 writer
只留在預設關閉的 process-level operator rollback boundary，一般 request 指定 v1 會回
`legacy_output_not_selectable`。

Initial scan、Apply 與 Detail Scan 共用 `BuildCommitService`：10 個 public siblings 先寫入
same-parent staging，通過 required-set／scope／reference／schema validation後才 rename，接著
保存 complete manifest，最後以 revision CAS promote latest。Supported history/latest reader
不掃 raw output directory，因此看不到 partial set。

依使用者後端ownership指示，本輪曾做的7個tracked frontend修改與3個新增frontend檔案已
全部還原；`git diff -- frontend`為空。Backend contract仍維持v2與legacy request fail-closed，
但原始frontend仍有5筆active legacy hits，因此本報告不再宣稱full-stack cutover complete。

## Gate 與 executable consumer census

- Stage A gate：native v1/v2 reload、non-object root、雙向 manifest badge mismatch、paired
  canonical/readiness equivalence皆已通過。
- Executable scope：`src/kai_mind/**/*.py` AST、
  `frontend/src/**/*.{ts,tsx,json}` text、`scripts/**/*.sh` operational text。
- Records / actual hits：`35 / 35`，無 unknown、無 stale。
- Classification：`migrate=5`、`migration_only=22`、`operator_rollback=8`。
- 5筆`migrate`全部位於frontend原始檔案，removal plan明確交由frontend owner；backend無
  未分類active legacy hit。
- Digest payload：依 allowlist tuple 順序，把四欄 record 轉為 sorted-key compact JSON。
- Census SHA-256：
  `59fa4f066a0e37c9f73ce488e64da96cccab7c8a9e6a429b0c073a738544714b`。

## Persisted legacy mapping migration

以一筆含 legacy extension edge 的 fixture 實跑：

| Run | scanned | converted | already_migrated | requires_manual_review | failed | 寫入 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| default dry-run | 1 | 1 | 0 | 0 | 0 | 0 |
| explicit `--apply` | 1 | 1 | 0 | 0 | 0 | atomic replace + backup |
| 第二次 `--apply` | 1 | 0 | 1 | 0 | 0 | 0 |

- Confirmed完整 row 轉為 `non_baseline_capability_candidate`，不升格為 detected reference
  capability。
- `extension_edges` 不轉 canonical edge；只保留 digest、opaque quarantine ref 與 warning。
- 缺必要 extension 欄位的 confirmed row 回 `requires_manual_review`，不猜值。
- Backup/index owner-only mode 為 `0600`；project lock、replace failure、restart idempotence、
  secret/error redaction皆有 regression。
- Active backend API立即拒絕`new_extension_component`；frontend原始UI仍可組出legacy
  request，但backend會以`legacy_mapping_type_read_only` fail closed。

## Active producer、consumer 與 rollback

- Normal producer 直接 materialize／validate `AiSystemMapV2`；top-level 不含 `extensions`，也
  沒有 RAG-only hard requirement。
- Viewer、detail scan、query trace、profile/readiness、static execution、renderers、CLI/Web
  都接 v2 或 `GraphViewModel`；schema dispatch仍只由 `CanonicalMapLoader` 擁有。
- `MarkdownSummaryService` 與其 orphan v1 test 已移除；現行 Markdown只走
  `GraphMarkdownRenderer`。
- Public CLI/API v1 selection：CLI exit `1`，API `422`，stable detail
  `legacy_output_not_selectable`。
- Invalid `KAI_MIND_CANONICAL_OUTPUT_VERSION` 阻止 startup，stable error
  `invalid_canonical_output_version`。
- Operator v1 rollback：同一 build只寫一個 v1 canonical artifact；manifest/warning 標示
  `active_schema_version=ai-system-map/v1`、`operator_rollback_active=true`，process內立即
  normalize成 v2供 consumer 使用。v2-only enrichment以
  `legacy_rollback_not_representable` fail closed。
- 移除 operator env後再次產生 v2；10 個 artifacts 去除 run identity/time後逐檔 deterministic
  comparison為 `10/10 equal`，沒有 rollback state leakage。

## 10-artifact atomic visibility

Phase2 P0 artifact set固定為 `phase2-p0/v1`：

```text
JSON (7)
  ai_system_map.json
  profile_signals.json
  readiness_report.json
  call_graph.json
  dataflow_hints.json
  execution_paths.json
  evidence_table.json

Render (3)
  ai_system_map.md
  system_map.mmd
  execution_map.mmd
```

- 10 個 siblings與 manifest共用 `scan_id`、`build_id`、`environment_id`、
  `artifact_set_version`；manifest保存每檔 digest、size、schema status。
- 10 個逐檔 write boundary全數 fault inject；失敗時 final/manifest/latest不可見。
- Scope mismatch、dangling evidence、invalid sibling schema、rename failure皆 fail closed。
- Rename後 manifest前的 orphan final set不進 supported reader；可受控清除/恢復。
- Manifest後 pointer前可由 build-id/history讀完整 non-latest build；latest仍指舊 build。
- CAS stale回 `stale_latest_revision`，不覆蓋較新的 latest。
- Initial／Apply／Detail在 post-commit session projection failure時都保留 committed build，回
  `session_projection_save_failed` warning。

## Manual QA

### CLI

- `kai-mind --help`、`map --help`、`validate-map`、migration與trace help可用。
- Normal v2 canary產生正好10檔；7 JSON scope一致，v2 validate為
  `loaded=true / nodes=58 / edges=1`。
- Missing project回 `project_path_not_found`；raw query marker未出現在 trace output。
- Trace loopback endpoint被 egress policy擋下：`egress_policy_blocked`、`query_sent=false`。
- v1 rollback canary可由同 binary validate/load；unset env後正常 v2重新成立。

### Live FastAPI / restart

- Import → scan → viewer → detail → trace → history/latest完整走通。
- Initial與兩個 Detail child build各有完整10 artifacts；history含 initial + 2 children。
- Restart使用相同 state dir後，project、latest child、by-id與 `/api/map` 均可回讀；viewer
  `loaded=true`，child projection為61 nodes。
- Public v1 request回422；invalid env startup直接失敗，不留下服務半啟動狀態。

### Browser / Visual QA

- 先前Chrome DevTools／Playwright證據來自後來被還原的暫時frontend cutover，不能代表current
  worktree，因此不再列為完成證據。
- Current frontend只驗證原始Vitest／build／lint；frontend v2 sample、legacy proposal type與
  visual QA由frontend handoff承接。

## Regression 與 quality gates

| Gate | 結果 |
| --- | --- |
| Full backend `.venv/bin/pytest -q` | ownership修正後：`1031 passed in 162.60s` |
| Scoped contracts/unit/integration/web | ownership修正後：`977 passed in 155.81s` |
| Ruff `src tests` | `All checks passed!` |
| Mypy `src` | `Success: no issues found in 190 source files` |
| Frontend Vitest | 原始tree：`3 files / 7 tests passed` |
| Frontend TypeScript + Vite build | exit 0 |
| Frontend ESLint | exit 0；1個既有 Fast Refresh warning |
| `bash -n` all operational shell scripts | exit 0 |
| Consumer allowlist | `35 records / 35 hits`；5筆frontend `migrate` |

Full gate曾抓到兩個真實同步問題並修復：Pydantic model新增 `artifact_set_version` 後
checked-in JSON Schema未同步，以及 Mermaid scope comment放在 `flowchart LR` 前破壞穩定
first-line contract。Targeted RED可重現；補 schema property並將 comment移到第二行後，
schema sync `1 passed`、renderer `9 passed`，全套回到1031 passed。

## Review-work 與 runtime debugging audit

因使用者限制最多3個 subagent且本 goal已用滿，`review-work` 的5個 lane由主 agent依相同
準則逐項執行，沒有再委派：

| Lane | Verdict | Evidence |
| --- | --- | --- |
| Goal / constraints | BACKEND PASS | Backend Tasks 1-7通過；frontend依ownership還原並待handoff |
| Hands-on QA | BACKEND PASS | CLI、live FastAPI/curl；已撤回不屬current tree的frontend QA claim |
| Code quality | CONTRACT PASS / HYGIENE WARN | tests、Ruff check、Mypy src、build、lint通過；format與test typing另列warning |
| Security | PASS | migration + egress `18 passed`；production source（排除既有 test mocks）的 secret/unsafe TS/path scans零命中 |
| Context mining | PASS | Plan 00A/13、MODEL/API contracts、architecture、scripts、allowlist同步 |

三個 runtime hypotheses：

1. Partial staging可能被 supported reader看到：**refuted**，相關 fault/reader probes
   `12 passed`。
2. Session projection失敗可能遺失已 commit build：**refuted**，initial/apply/detail
   `3 passed`且仍可 query。
3. Operator env可能污染下一次 normal v2：**refuted**，config/cutover `12 passed`且 live
   rollback → unset → deterministic v2成立。

## Remaining warnings / boundary

- 本機實跑平台為 macOS。Windows path／replace／rename contract由平台中立程式碼與 fixtures
  覆蓋，但本輪沒有 Windows host/CI runner，不能宣稱 Windows live QA。
- Vite build仍有既有 `web-worker` external resolution與 >500 kB chunk warning；build exit 0，
  未觀察到本次 contract regression。
- ESLint仍有既有 `BoundaryDecisionModal.tsx` Fast Refresh warning；lint為0 errors。
- `.venv/bin/ruff format --check src tests`列出27個backend／test檔案待格式化；這不屬於
  frontend還原，未在本輪擴張處理。
- `.venv/bin/mypy src tests`在`test_endpoint_call_provider.py`有10個`Endpoint`對
  `CanonicalEndpoint`型別錯誤；production gate `.venv/bin/mypy src`為0 errors。
- 本機PATH沒有`uv`，因此`uv lock --check`未執行成功；未把它描述為通過。
- Frontend原始tree保留v1 sample與`new_extension_component`相關type/mock/UI branch，共5筆
  allowlisted `migrate` hit；這是明確frontend handoff，不得在backend report中標成已退場。
- Plan 15仍負責移除 operator v1 writer/env、migration DTO/command/quarantine與不再需要的 v1
  compatibility fixtures；frontend handoff不屬Plan 15 cleanup。
