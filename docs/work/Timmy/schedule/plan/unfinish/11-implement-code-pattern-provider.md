# Task 11: Implement Code Pattern Provider

## 目標
實作 initial `CodePatternProvider`，對 eligible source files 做 bounded pattern scan，找出 loaders、splitters、embeddings、vector store clients、retrievers、prompt templates、LLM calls、route endpoints 等明確 RAG code signals。

## 為什麼要先做這個
僅靠 Docker/config/dependency 不足以建立 evidence-based RAG map。Code pattern 是 component detection 的重要來源，但必須先用可測、可解釋的 deterministic rules，不能讓 AI 直接讀 code 產生 facts。

## 前置需求
- Task 7 已完成 file inventory。
- Task 5 已完成 secret masking。
- Task 10 已有 dependency facts 可供後續交叉比對。

## 實作範圍
- 掃描 Python/TypeScript/JavaScript source files。
- 設定 max file size 與 skip reason。
- 初始 patterns：`OpenAIEmbeddings`、`QdrantClient`、`Chroma`、`as_retriever`、`PromptTemplate`、`ChatOpenAI`、FastAPI/Flask/Express routes。
- 每個 match 輸出 `rule_id`、`file`、`path` / `line_start` / `line_end`、`masked snippet`。
- 輸出沿用現有 provider-local model：`ProviderScanResult`、`ScanFact`、`Evidence`，不要另外發明自由格式 JSON。
- `Evidence.snippet` 必須先通過 `SecretMaskingService.mask_text()`，且限制 context lines 與總長度。

## 不包含範圍
- 不做完整 AST。
- 不整合 Semgrep 作為必要依賴。
- 不做 whole-repo call graph。
- 不讓 AI 產生 scanner facts。
- 不在 Task 11 實作 Tree-sitter、ast-grep、Griffe 或自製 tokenizer；這些放到 future plan。

## 查證後設計收斂

### 1. understand-anything 參考方式
`understand-anything` 的重點不是「讓 LLM 自己讀 code 猜結構」，而是先用 deterministic extractor 產生結構事實，再讓 LLM 在受限資料上補 semantic summary / graph fragment。

對 Task 11 的可借鏡點：
- 先產生 deterministic facts / evidence，再交給後續 component detection。
- source path、line、rule id、snippet 都要可追溯。
- scanner 失敗或 skip 要明確記錄，不能讓 AI 補 scanner facts。

不要照搬的部分：
- Task 11 初版不做 full structural extraction、call graph 或 Tree-sitter parser registry。
- Task 11 只需要保守 code pattern signals，不需要建立完整 code knowledge graph。

repo 參考文件：
- `docs/work/Timmy/reference/understand-anything-backend-review.md`

### 2. gitdiagram 參考方式
`gitdiagram` 可以借鏡 schema validation 與 deterministic compiler 的邊界：不要讓 LLM 直接輸出 Mermaid，而是先要求 structured graph JSON，再由程式編譯 / 驗證。

但它不是 Task 11 deterministic scanner 的直接範本，因為 `gitdiagram` 的 structured graph JSON 仍由 LLM 產生，只是被 Pydantic / Zod schema 約束。Task 11 的 scanner facts 必須完全由 deterministic rules 產生。

對 Task 11 的可借鏡點：
- 強型別 output model。
- evidence 可追溯。
- 後續 normalization / validation 再決定 component，不在 provider 內直接宣布完整 component。

repo 參考文件：
- `docs/work/Timmy/reference/gitdiagram-backend-review.md`

### 3. Semgrep 只作 rule schema 參考
Semgrep 官方 rule syntax 支援 `rules`、`id`、`languages`、`pattern-regex`，可作為 `code_patterns.py` 的命名參考。

Task 11 初版應使用輕量 Python dataclass / Pydantic-style rule model，例如：

```python
PatternRule(
    rule_id="code_pattern_llm_chat_openai",
    languages=("python",),
    extensions=(".py",),
    regex=r"\bChatOpenAI\s*\(",
    fact_kind="llm_call",
)
```

注意：
- Semgrep 的 `pattern` 是結構化 pattern，不等於 Python `re`。
- 若初版只用 `re.finditer()`，欄位應命名為 `regex` 或 `pattern_regex`，避免暗示已支援 Semgrep AST pattern。
- Semgrep 不作必要依賴，也不在 Task 11 呼叫外部 Semgrep binary。

官方來源：
- https://semgrep.dev/docs/writing-rules/rule-syntax

### 4. Safe snippet 是必要條件
Code pattern match 的同一行或上下文可能包含 API key、Authorization header、connection string 或 private key。

實作要求：
- snippet context 預設最多只取 match line 前後少量行數。
- snippet 必須經過 `SecretMaskingService.mask_text()`。
- evidence value / snippet 不可印出完整 secret。
- 測試要覆蓋 quoted secret、Bearer token、OpenAI key-like token 出現在 match 附近時仍被遮罩。

## 建議實作步驟
1. 建立 `src/kai_mind/core/providers/code_pattern_provider.py`。
2. 建立 `src/kai_mind/core/providers/code_patterns.py`，定義保守 pattern rule catalog。
3. 定義 pattern rule model：`rule_id`、language / file extensions、`regex`、fact kind。
4. 只讀 FileInventory 中的 source files。
5. 讀檔前先檢查 `FileRecord.size_bytes`，超過 provider max file size 時 skip with reason，不要讀入內容。
6. 對每個 match 建立 evidence，包含 safe snippet。
7. 對 binary / unreadable / decode error 使用 structured issue 或 provider-local skip result 記錄，訊息也要 masking。
8. 測試 fixture 中 route、retriever、prompt、LLM call。
9. 測試沒有 evidence 時不產生 component，只產生 facts。
10. 測試 import-only 不足以產生 detected component；component detection 留到 Task 13。

## 預期輸出
- `src/kai_mind/core/providers/code_pattern_provider.py`
- `src/kai_mind/core/providers/code_patterns.py`
- `tests/unit/core/test_code_pattern_provider.py`

## 驗收標準
- source pattern match 產生 deterministic evidence id inputs。
- safe snippet 經過 masking 且限長。
- 大檔案不被讀入，並記錄 skipped reason。
- AI 不參與 canonical fact generation。

## 可能風險與注意事項
- regex rules 容易誤判，因此初始規則要保守。
- 不要把 import package 當成 detected component 的唯一 evidence。
- route detection 要保守處理 decorator / method chain，不要把任意字串中的 `/api` 當 route endpoint。
- Python / TypeScript / JavaScript 的多行 call 可能造成 regex 漏判；初版接受漏判，優先避免誤判與 secret exposure。
- 若需要新增 `ParseIssue.scan_stage`，要同步更新 `src/kai_mind/core/models/scan.py` 的 Literal 與相關測試。
- 參考依據：Semgrep 官方 rule docs 支援可版本化 rule-based matching；Tree-sitter、ast-grep、Griffe 放入 future plan，不阻塞 Task 11。

## 新手提示
這一步不是寫 AI code reader，而是寫「可測的關鍵字/模式偵測器」。每條規則都要能說明為什麼 match。

## 視覺化說明
```text
┌──────────────┐
│ Source files │
└──────┬───────┘
       ↓
┌──────────────┐
│ Pattern rules │
└──────┬───────┘
       ↓
┌──────────────┐
│ Rule matches │
└──────┬───────┘
       ↓
┌──────────────┐
│ Evidence     │
└──────┬───────┘
       ↓
┌──────────────────────────┐
│ Component detection later │
└──────────────────────────┘
```
