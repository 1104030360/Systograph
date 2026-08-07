# 2026-06-02 Phase11 Code Pattern Provider Report

## 階段目標

依照
`docs/work/Timmy/schedule/plan/unfinish/11-implement-code-pattern-provider.md`
完成 initial `CodePatternProvider`，讓 scanner 可以從 `FileInventory` 中的
Python / TypeScript / JavaScript source files 做 bounded deterministic pattern
scan，輸出 RAG code signals 的 `ScanFact`、`Evidence` 與 `ParseIssue`。

本階段沒有做完整 AST、沒有整合 Semgrep binary、沒有建立 whole-repo call
graph、沒有讓 AI 產生 scanner facts，也沒有把 provider-local facts 直接轉成
detected component。

## 實作邏輯

1. Provider 延續 inventory-first 邊界：
   `CodePatternProvider.collect()` 只處理 `FileInventory.files` 中的 source
   files，不自行遞迴搜尋 project root。
2. Output 延續 provider-local contract：
   回傳 `ProviderScanResult`，包含 `ScanFact[]`、`Evidence[]`、
   `ParseIssue[]`。
3. 新增 deterministic rule catalog：
   `src/systograph/core/providers/code_patterns.py`
   - 使用 frozen dataclass `PatternRule`。
   - 欄位包含 `rule_id`、`languages`、`extensions`、`regex`、
     `fact_kind`。
   - 使用 `regex` 命名，避免暗示已支援 Semgrep AST pattern。
4. 初版 pattern rules：
   - `OpenAIEmbeddings`
   - `embeddings.create`
   - `QdrantClient`
   - `Chroma`
   - `as_retriever`
   - `PromptTemplate`
   - `ChatOpenAI`
   - FastAPI route decorators
   - Flask route decorators
   - Express route method chains
5. Bounded scan policy：
   - 讀檔前先檢查 `FileRecord.size_bytes`。
   - 超過 provider max file size 時不讀檔，改回傳 skipped issue。
   - Decode / read failure 不 crash，改回傳 structured issue。
6. Safe snippet policy：
   - 預設只取 match line。
   - 可設定少量 context lines。
   - snippet 先經過 `SecretMaskingService.mask_text()`。
   - snippet 有 max chars 限制，過長時優先保留 match line。
7. Evidence contract：
   - 每個 match 都有 deterministic evidence id。
   - Evidence 包含 `rule_id`、`file`、`path`、`line_start`、`line_end`、
     `snippet`。

## 實作步驟

1. 先新增 TODO：
   `docs/work/Timmy/schedule/todo/2026-06-02-phase11-code-pattern-provider-TODO.md`。
2. 先寫 unit tests：
   `tests/unit/core/test_code_pattern_provider.py`。
3. 先寫 BDD-style integration tests：
   `tests/integration/test_phase11_code_pattern_provider_behaviors.py`。
4. 執行 targeted pytest，確認 RED：
   provider module 尚未存在，測試 collection 失敗。
5. 新增：
   `src/systograph/core/providers/code_patterns.py`。
6. 新增：
   `src/systograph/core/providers/code_pattern_provider.py`。
7. 擴充：
   `src/systograph/core/models/scan.py` 的 `ParseIssue.scan_stage`，增加
   `code_pattern_scan`。
8. 修正兩個測試假設：
   - Secret masking 已正確遮罩，但遮罩格式是 partial mask，不一定是
     `[MASKED]`。
   - `basic_qdrant_ollama_rag` fixture 的 `src/ingest.py` 也有合法
     `QdrantClient` signal，所以 integration test 不應只允許
     `src/retriever.py`。
9. 將 TODO 驗收清單全部勾選完成。

## 測試方式

Targeted verification：

```bash
.venv/bin/python -m pytest tests/unit/core/test_code_pattern_provider.py tests/integration/test_phase11_code_pattern_provider_behaviors.py
.venv/bin/ruff check src/systograph/core/models/scan.py src/systograph/core/providers/code_patterns.py src/systograph/core/providers/code_pattern_provider.py tests/unit/core/test_code_pattern_provider.py tests/integration/test_phase11_code_pattern_provider_behaviors.py
.venv/bin/mypy src/systograph/core/models/scan.py src/systograph/core/providers/code_patterns.py src/systograph/core/providers/code_pattern_provider.py tests/unit/core/test_code_pattern_provider.py tests/integration/test_phase11_code_pattern_provider_behaviors.py
```

Full verification：

```bash
.venv/bin/python -m pytest
.venv/bin/ruff check .
.venv/bin/mypy
```

## 遇到的問題與處理方式

### 1. Read-only sandbox 無法讓 pytest 建立 temp file

第一次執行 pytest 時，sandbox 沒有可用 temp directory，pytest 還沒進入 test
collection 就失敗。這不是程式碼 regression。

處理方式：
- 使用 escalated pytest 重新執行。
- 重新執行後得到真正的 TDD RED：provider module 尚未存在。

### 2. 測試對 masking display format 假設太窄

`SecretMaskingService` 對較長 secret 使用 partial mask，例如
`Bear...cret` 或 `sk-d...cret`，不是每次都輸出 `[MASKED]`。

處理方式：
- 測試改成驗證 raw secret 不出現在 snippet，且有 masked marker。
- 不改 masking service 行為。

### 3. Fixture 中合法 Qdrant signal 不只一個檔案

`basic_qdrant_ollama_rag` 的 `src/retriever.py` 與 `src/ingest.py` 都有
`QdrantClient` signal。

處理方式：
- Integration test 改成確認至少包含 `src/retriever.py`。
- 保留 provider 對每個 match 產生 evidence 的行為。

## 測試結果

Targeted verification：

- `.venv/bin/python -m pytest tests/unit/core/test_code_pattern_provider.py tests/integration/test_phase11_code_pattern_provider_behaviors.py`
  - 結果：`10 passed`
- `.venv/bin/ruff check src/systograph/core/models/scan.py src/systograph/core/providers/code_patterns.py src/systograph/core/providers/code_pattern_provider.py tests/unit/core/test_code_pattern_provider.py tests/integration/test_phase11_code_pattern_provider_behaviors.py`
  - 結果：`All checks passed!`
- `.venv/bin/mypy src/systograph/core/models/scan.py src/systograph/core/providers/code_patterns.py src/systograph/core/providers/code_pattern_provider.py tests/unit/core/test_code_pattern_provider.py tests/integration/test_phase11_code_pattern_provider_behaviors.py`
  - 結果：`Success: no issues found in 5 source files`

Full verification：

- `.venv/bin/python -m pytest`
  - 結果：`149 passed`
- `.venv/bin/ruff check .`
  - 結果：`All checks passed!`
- `.venv/bin/mypy`
  - 結果：`Success: no issues found in 47 source files`

## 驗收結果

- 掃描 Python / TypeScript / JavaScript source files：完成。
- Max file size 與 skipped reason：完成。
- `OpenAIEmbeddings`、`QdrantClient`、`Chroma`、`as_retriever`、
  `PromptTemplate`、`ChatOpenAI`：完成。
- FastAPI / Flask / Express routes：完成。
- `rule_id`、`file`、`path`、`line_start`、`line_end`、masked snippet：完成。
- `Evidence.snippet` 經過 `SecretMaskingService.mask_text()`：完成。
- Snippet context lines 與總長度限制：完成。
- Decode / read failure structured issue：完成。
- 不產生 detected component：完成。
- AI 不參與 canonical fact generation：完成。
- Targeted verification：通過。
- Full verification：通過。
