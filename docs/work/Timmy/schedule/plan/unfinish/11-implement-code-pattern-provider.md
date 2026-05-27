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
- 每個 match 輸出 rule_id、file、path/line、masked snippet。

## 不包含範圍
- 不做完整 AST。
- 不整合 Semgrep 作為必要依賴。
- 不做 whole-repo call graph。
- 不讓 AI 產生 scanner facts。

## 建議實作步驟
1. 建立 `src/kai_mind/core/providers/code_pattern_provider.py`。
2. 定義 pattern rule model：rule_id、language/file extensions、regex、fact kind。
3. 只讀 FileInventory 中的 source files。
4. 對大檔、binary、generated files skip with reason。
5. 對每個 match 建立 evidence，包含 safe snippet。
6. 測試 fixture 中 route、retriever、prompt、LLM call。
7. 測試沒有 evidence 時不產生 component，只產生 facts。

## 預期輸出
- `src/kai_mind/core/providers/code_pattern_provider.py`
- `src/kai_mind/core/providers/code_patterns.py`
- `tests/core/test_code_pattern_provider.py`

## 驗收標準
- source pattern match 產生 deterministic evidence id inputs。
- safe snippet 經過 masking 且限長。
- 大檔案不被讀入，並記錄 skipped reason。
- AI 不參與 canonical fact generation。

## 可能風險與注意事項
- regex rules 容易誤判，因此初始規則要保守。
- 不要把 import package 當成 detected component 的唯一 evidence。
- 參考依據：Semgrep 官方 rule docs 支援可版本化 rule-based matching；Tree-sitter 可留到 L2/L3 bounded AST extraction。

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
