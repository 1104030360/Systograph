# 2026-06-02 Phase11 Code Pattern Provider TODO

## 階段目標

依照
`docs/work/Timmy/schedule/plan/unfinish/11-implement-code-pattern-provider.md`
實作 initial `CodePatternProvider`，從 `FileInventory` 中的 eligible source
files 做 bounded deterministic pattern scan，輸出 RAG code signals 的
`ScanFact`、`Evidence` 與 `ParseIssue`。

本階段只做保守 regex-based scanner facts：

- 不做完整 AST。
- 不整合 Semgrep binary 或外部必要依賴。
- 不做 whole-repo call graph。
- 不讓 AI 產生 scanner facts。
- 不直接建立 detected component。
- 不把 raw secret 放進 facts、evidence、issues、logs 或 test snapshots。

## 實作邏輯

1. 延續 Task 7 的 inventory-first 邊界：
   `CodePatternProvider` 只處理 `FileInventory.files` 內的 source files，
   不自行遞迴掃描 project root。
2. 延續 Task 8 / Task 9 / Task 10 的 provider-local output pattern：
   回傳 `ProviderScanResult`，包含 `ScanFact[]`、`Evidence[]`、
   `ParseIssue[]`。
3. 新增 `code_patterns.py`：
   - 使用 frozen dataclass 定義 `PatternRule`。
   - 欄位包含 `rule_id`、`languages`、`extensions`、`regex`、
     `fact_kind`。
   - regex 欄位明確命名為 `regex`，不假裝支援 Semgrep AST pattern。
4. 初版 rule catalog 保守偵測：
   - `OpenAIEmbeddings`
   - `QdrantClient`
   - `Chroma`
   - `as_retriever`
   - `PromptTemplate`
   - `ChatOpenAI`
   - FastAPI / Flask route decorators
   - Express route method chains
5. 每個 match 產生：
   - `ScanFact.kind`
   - `ScanFact.file`
   - `ScanFact.path`
   - `ScanFact.value`
   - `ScanFact.rule_id`
   - matching `Evidence`，含 `line_start`、`line_end`、masked snippet。
6. snippet policy：
   - 預設只取 match line 前後少量 context lines。
   - 經過 `SecretMaskingService.mask_text()`。
   - 限制總長度，避免 report 過大與 secret exposure。
7. 大檔案 policy：
   - 讀檔前檢查 `FileRecord.size_bytes`。
   - 超過 provider max file size 時不讀檔。
   - 用 provider-local `ParseIssue` 記錄 skipped reason。
8. Unreadable / decode error policy：
   - 不 crash。
   - 產生 `ParseIssue` 與 parse error evidence。
   - issue message 也先 mask。

## TDD / BDD 步驟

### 1. RED：先寫 unit tests

- 測 provider 只讀 `FileInventory.files` 中的 source files。
- 測 Python patterns 會產生 deterministic facts / evidence。
- 測 TypeScript / JavaScript Express routes。
- 測 snippet 會遮罩 quoted secret、Bearer token、OpenAI key-like token。
- 測 snippet context lines 與總長度有限制。
- 測大檔案不被讀入，且記錄 skipped reason。
- 測 unreadable / decode error 會回傳 structured issue。
- 測 import-only 不產生 detected component，只產生 provider-local facts。

### 2. GREEN：實作最小 provider

- 新增 `src/kai_mind/core/providers/code_patterns.py`。
- 新增 `src/kai_mind/core/providers/code_pattern_provider.py`。
- 擴充 `ParseIssue.scan_stage`，增加 `code_pattern_scan`。
- 實作 source file extension filter。
- 實作 bounded UTF-8 text read。
- 實作 regex match line/column/path 計算。
- 實作 fact/evidence builder 與 issue builder。

### 3. BDD-style integration tests

- 使用 `basic_qdrant_ollama_rag` fixture 驗證 FastAPI route 與 Qdrant
  code pattern signals。
- 使用 `openai_external_provider_rag` fixture 驗證 FastAPI route 與 OpenAI
  embedding call signals。
- 使用 fixture inventory 驗證 scanner 行為仍是 read-only deterministic。

### 4. Verification

Targeted verification：

```bash
.venv/bin/python -m pytest tests/unit/core/test_code_pattern_provider.py tests/integration/test_phase11_code_pattern_provider_behaviors.py
.venv/bin/ruff check src/kai_mind/core/models/scan.py src/kai_mind/core/providers/code_patterns.py src/kai_mind/core/providers/code_pattern_provider.py tests/unit/core/test_code_pattern_provider.py tests/integration/test_phase11_code_pattern_provider_behaviors.py
.venv/bin/mypy src/kai_mind/core/models/scan.py src/kai_mind/core/providers/code_patterns.py src/kai_mind/core/providers/code_pattern_provider.py tests/unit/core/test_code_pattern_provider.py tests/integration/test_phase11_code_pattern_provider_behaviors.py
```

Full verification：

```bash
.venv/bin/python -m pytest
.venv/bin/ruff check .
.venv/bin/mypy
```

## 驗收清單

- [x] `CodePatternProvider` 只吃 `FileInventory`。
- [x] 只掃描 Python / TypeScript / JavaScript source files。
- [x] 讀檔前檢查 provider max file size。
- [x] 大檔案不被讀入，並記錄 skipped reason。
- [x] Decode / read failure 不 crash，並記錄 structured issue。
- [x] `OpenAIEmbeddings` pattern 可產生 fact / evidence。
- [x] `QdrantClient` pattern 可產生 fact / evidence。
- [x] `Chroma` pattern 可產生 fact / evidence。
- [x] `as_retriever` pattern 可產生 fact / evidence。
- [x] `PromptTemplate` pattern 可產生 fact / evidence。
- [x] `ChatOpenAI` pattern 可產生 fact / evidence。
- [x] FastAPI route pattern 可產生 fact / evidence。
- [x] Flask route pattern 可產生 fact / evidence。
- [x] Express route pattern 可產生 fact / evidence。
- [x] 每個 match 有 `rule_id`、`file`、`path`、`line_start`、
  `line_end`、masked snippet。
- [x] Evidence id inputs deterministic。
- [x] snippet 經過 `SecretMaskingService.mask_text()`。
- [x] snippet context lines 與總長度有限制。
- [x] 不產生 detected component；component detection 留到 Task 13。
- [x] AI 不參與 canonical fact generation。
- [x] Targeted verification 通過。
- [x] Full verification 通過。
