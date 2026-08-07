# 2026-06-08 Phase21 Progressive Detail Scan Report

## 完成內容

已依照 `docs/work/Timmy/schedule/plan/unfinish/21-implement-progressive-detail-scan.md` 完成 Task 21 backend / API 範圍：

- 建立 L2 `ComponentDetailScanService`：只讀 target-related Python files，使用 Python `ast` 抽取 imports、class/function signatures、decorators。
- 建立 L3 `CodePathScanService`：抽取 static call-like hints，所有 code path step 皆標示 `best_effort=true`，不宣稱 runtime path 已確認。
- 建立 `DetailScanService` dispatcher：負責 target validation、L2/L3 dispatch、追加 evidence、更新 target `evidence_ids`、append `detail_scans[]`，並在保存前重新 validate 整份 map。
- 建立 FastAPI route：
  - `POST /api/detail-scans`
  - `GET /api/detail-scans/{detail_scan_id}`
- 更新 `MappingEvidencePacketBuilder` 的 signal 判斷，避免 `custom_router` 因 substring 被誤判成 `route` signal。
- 更新 `ai-system-map/v1` model 與 JSON Schema，補上 detail scan 需要的 `best_effort`、`context_limits`、code path `evidence_id` / `line_end`。
- 更新 `docs/work/Timmy/design/epic1-local-api-guide.md`，補 detail scan request / response、target id 規則、lazy loading 與 evidence 追加行為。

## 實作邏輯

Detail scan 執行後會同時寫入三個地方：

1. `detail_scans[]`：前端 lazy loading 顯示 findings、code path、warnings 與 context limits。
2. `evidence[]`：把 L2/L3 signal 變成 canonical `Evidence`。
3. target 的 `evidence_ids`：讓 Task 20 `MappingEvidencePacketBuilder` 不需要讀 `detail_scans[]`，也能自動取得細掃 evidence。

目前支援 target type：

- `component_slot` / `slot`
- `component_instance` / `component`
- `extension`
- `unmapped_component` / `unmapped`
- `edge`
- `evidence`

安全邊界：

- 不做 whole-repo LLM scan。
- 不執行 target project。
- 不使用 `sys.settrace`。
- 不呼叫 runtime endpoint。
- 不接受 client 提供 arbitrary file path。
- 所有 snippet / value 寫入前都經過 `SecretMaskingService`。

## 步驟

1. 先閱讀 `phase21.md`、`AGENTS.md`、Linus rule、Task 21 plan、現有 system map model、validation、session store、proposal route 與 packet builder。
2. 先寫紅燈測試：
   - `tests/unit/core/test_detail_scan_service.py`
   - `tests/web/test_detail_scan_routes.py`
   - 更新 `tests/unit/core/test_mapping_evidence_packet_builder.py`
3. 確認紅燈原因是 `detail_scan_service` 尚不存在。
4. 實作 L2/L3/detail dispatcher 與 web routes。
5. 更新 schema、API guide 與 session store 查詢方法。
6. 跑相關測試、ruff、mypy、完整 pytest。

## 遇到的問題與解法

- 問題：`MappingEvidencePacketBuilder` 用 substring 判斷 `route` signal，導致 `custom_router` 被誤判。
  - 解法：改成 token-based 判斷，`router` 不再被當成 `route`。
- 問題：`DetailScanFinding` / `CodePathStep` 原本缺少 L3 所需欄位。
  - 解法：補 `best_effort`、`context_limits`、`line_end`、`evidence_id`，並同步 JSON Schema。
- 問題：invalid target 不應污染 loaded map。
  - 解法：`DetailScanService` 先 deep copy map，validate 成功後 route 才保存新的 build result。

## 測試方式

已執行：

```bash
.venv/bin/pytest tests/unit/core/test_detail_scan_service.py tests/unit/core/test_mapping_evidence_packet_builder.py tests/contracts/test_ai_system_map_schema.py tests/web/test_detail_scan_routes.py tests/web/test_mapping_proposal_routes.py
.venv/bin/ruff check src tests
.venv/bin/mypy
.venv/bin/pytest
```

## 測試結果

- Targeted tests：28 passed
- Ruff：All checks passed
- Mypy：Success, no issues found in 117 source files
- Full pytest：372 passed

## 研究查證後補強（2026-06-08）

依照後續 research review，確認 Patchwork、IRIS-SAST、Semgrep rules、Python `ast`、Tree-sitter、OWASP Prompt Injection 與 Lost-in-the-middle 的方向大致正確；實作上補強兩個點：

- Python `ast.parse()` 失敗時不讓 detail scan 中斷。現在 L2 會標示 `detail_scan_ast_parse_failed:<file>`，並退回 regex fallback 抽取 import / function signature 類 signal。
- Source code snippet 視為 untrusted data。現在 detail scan snippet 會先遮蔽 secret，再把 Python string literal 正規化成 `[STRING]`、comment 正規化成 `[COMMENT]`，避免 prompt-like 字串或註解直接進入後續 AI proposal context。

新增測試：

- malformed Python fallback：`test_component_detail_scan_falls_back_to_regex_when_ast_parse_fails`
- prompt-like string literal redaction：`test_detail_scan_redacts_prompt_like_string_literals_from_snippets`

補強後驗證：

```bash
.venv/bin/pytest tests/unit/core/test_detail_scan_service.py tests/unit/core/test_mapping_evidence_packet_builder.py tests/contracts/test_ai_system_map_schema.py tests/web/test_detail_scan_routes.py tests/web/test_mapping_proposal_routes.py
.venv/bin/ruff check src tests
.venv/bin/mypy
.venv/bin/pytest
```

補強後測試結果：

- Targeted tests：30 passed
- Ruff：All checks passed
- Mypy：Success, no issues found in 117 source files
- Full pytest：374 passed

## Reviewer P1 測試缺口修正（2026-06-08）

Reviewer 指出 `DetailScanService` 實作了多個 scanner target type，但測試只覆蓋 `unmapped_component`，違反 AGENTS.md「Scanner 行為缺少測試時，視為 P1」。

已補 `tests/unit/core/test_detail_scan_service.py` 覆蓋下列 target resolution 與 evidence attachment 行為：

- `component_slot`：驗證 slot target 只掃該 slot instance 的 evidence file，並把新 evidence ids 掛回 component instance。
- `component_instance`：驗證 instance target 掃對應 source file，並把新 evidence ids 掛回該 component。
- `extension`：驗證 extension target 掃 extension evidence file，並把新 evidence ids 掛回 extension。
- `edge`：驗證 edge target 的 `code_path` 掃描會產生 best-effort code path steps，並把新 evidence ids 掛回 edge。
- `evidence`：驗證 evidence target 可從 canonical evidence file 觸發 detail scan，不會嘗試改寫原 evidence id。

補強後驗證：

```bash
.venv/bin/pytest tests/unit/core/test_detail_scan_service.py tests/web/test_detail_scan_routes.py tests/contracts/test_ai_system_map_schema.py
.venv/bin/ruff check src tests
.venv/bin/mypy
.venv/bin/pytest
```

補強後測試結果：

- Detail scan unit tests：11 passed
- Related tests：21 passed
- Ruff：All checks passed
- Mypy：Success, no issues found in 117 source files
- Full pytest：379 passed

## 驗收對照

- L2 只掃 target-related files：已由 unit test 驗證不掃 `src/other.py`。
- L3 call-like hints 標示 `best_effort`：已由 unit / route test 驗證。
- Snippet 不含 unmasked secret：已由 unit test 驗證。
- 新 evidence 同時進 `evidence[]` 與 target `evidence_ids`：已由 unit / route test 驗證。
- Task 20 packet 可吃到 detail scan evidence：已由 packet builder test 驗證。
- invalid target 回傳 422 且不寫入 map：已由 unit / route test 驗證。
- 追加後仍通過 `SystemMapValidationService.validate()`：已由 service 實作與 contract/full test 驗證。
- API guide 已同步：已更新 `docs/work/Timmy/design/epic1-local-api-guide.md`。
