# Phase 4：Privacy / Security Guard（Module 4）

**預估時間：** 1–2 週  
**前置條件：** Phase 3 完成

**目的：** 幫使用者確認 local AI 是否真的安全、資料是否真的沒有送出去。

---

## 🎯 核心目標

> 使用者能確認：local AI 是否真的 local、是否有外部 API 風險、是否有 endpoint 暴露風險。

---

## ✅ Checklist

### 4.1 後端 — Privacy Scan API

- [ ] 建立 `/api/diagnostics/privacy` endpoint
- [ ] 檢查 Ollama 是否只綁 localhost（解析 `OLLAMA_HOST` 或偵測 listen address）
- [ ] 檢查 Qdrant 是否只在本機可存取
- [ ] 檢查 cloud fallback 是否關閉
- [ ] 掃描 `.env` 或 config 中是否存在外部 API key（OpenAI、Anthropic 等）
- [ ] 檢查是否有呼叫外部 provider 的程式碼路徑
- [ ] 判斷 Data Leaves Device: Yes / No
- [ ] 評估本機服務暴露風險等級（Low / Medium / High）

### 4.2 後端 — Security Checklist

- [ ] 定義 security checklist 項目（至少 8–10 項）
- [ ] 每項回傳 PASS / FAIL / WARNING
- [ ] 產生整體 Risk Level（Low / Medium / High / Critical）

### 4.3 前端 — Privacy 頁面

- [ ] 顯示 Data Leaves Device 狀態（大字 Yes/No + 顏色）
- [ ] 顯示各項 check 結果（Ollama localhost、Qdrant localhost、cloud fallback 等）
- [ ] 用 ✅ / ❌ / ⚠️ 圖示標示每項檢查
- [ ] 顯示整體 Risk Level（帶顏色的標籤）
- [ ] 顯示 security checklist 完整列表

### 4.4 測試

- [ ] 單元測試：各項檢查邏輯
- [ ] 測試：Ollama 綁 `0.0.0.0` 時正確偵測為 FAIL
- [ ] 測試：存在外部 API key 時正確警告
- [ ] 整合測試：API 回傳正確結構

---

## 📋 範例輸出

```text
Privacy Status:
- Data leaves device: No
- Cloud fallback: Disabled
- Ollama localhost only: PASS
- Qdrant localhost only: PASS
- External API keys detected: None
- Public exposure risk: Low

Risk Level: Low
```

---

## 📌 完成標準

- [ ] Privacy 頁面清楚顯示所有安全檢查結果
- [ ] 能正確偵測不安全的設定
- [ ] Risk Level 分級合理
- [ ] 測試通過

---

## ➡️ 下一步

完成後前往 → [Phase 5：RAG Quality Inspector](./phase-5-rag-quality.md)
