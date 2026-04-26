# Phase 5：RAG Quality Inspector（Module 5）

**預估時間：** 2 週  
**前置條件：** Phase 4 完成

**目的：** 幫使用者判斷 RAG 回答到底可不可信，找出 retrieval 和 generation 的品質問題。

---

## 🎯 核心目標

> 使用者能知道：RAG 是否找對資料、回答是否有 citation、哪些句子沒有來源支持、RAG pipeline 可以怎麼改善。

---

## ✅ Checklist

### 5.1 後端 — RAG Quality Analysis API

- [ ] 建立 `/api/diagnostics/rag-quality` endpoint
- [ ] 接受一個 query + 回答 + retrieved chunks 作為輸入
- [ ] 顯示 retrieved chunks 內容
- [ ] 分析回答引用了哪些 chunk
- [ ] 計算 citation coverage（回答中有多少比例被 chunk 支持）
- [ ] 偵測 unsupported claims（回答中沒有來源支持的句子）
- [ ] 判斷 retrieval 是否找錯資料（relevance scoring）
- [ ] 計算整體 RAG quality score（0–100）

### 5.2 後端 — 改善建議引擎

- [ ] 根據分析結果產生改善建議：
  - 調整 chunk size
  - 調整 top_k
  - 啟用 reranking
  - 更換 embedding model
  - 補充 metadata
  - 清理重複文件
- [ ] 建議要有優先順序排列

### 5.3 前端 — RAG Quality 頁面

- [ ] 提供測試介面：輸入 query → 顯示 RAG 回答 + 品質分析
- [ ] 顯示 retrieved chunks（可展開 / 收合）
- [ ] 標示哪些 chunk 被用在回答中
- [ ] 顯示 citation coverage（百分比 + 視覺化）
- [ ] 高亮 unsupported claims（紅色標示）
- [ ] 顯示 RAG quality score
- [ ] 顯示改善建議列表

### 5.4 報告匯出

- [ ] 基本 report export（JSON 或 Markdown 格式）
- [ ] 包含所有診斷數據與建議

### 5.5 測試

- [ ] 單元測試：citation coverage 計算邏輯
- [ ] 單元測試：unsupported claim 偵測邏輯
- [ ] 整合測試：完整 RAG quality 分析流程
- [ ] 測試：沒有 retrieved chunks 時的 graceful handling

---

## 📋 範例輸出

```text
RAG Quality:
- Retrieved chunks: 5
- Relevant chunks: 3
- Chunks used in answer: 3
- Citation coverage: 85%
- Unsupported claims: 1

Recommendation:
1. Enable reranking
2. Reduce chunk size from 1000 to 500
3. Improve document metadata
```

---

## 📌 完成標準

- [ ] RAG Quality 頁面能完整顯示分析結果
- [ ] 能正確偵測 unsupported claims
- [ ] citation coverage 計算合理
- [ ] 改善建議有實際幫助
- [ ] 能匯出基本報告
- [ ] 測試通過

---

## ➡️ 下一步

完成後前往 → [Phase 6：工程品質與履歷包裝](./phase-6-polish-resume.md)
