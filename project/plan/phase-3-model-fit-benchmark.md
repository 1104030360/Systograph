# Phase 3：Model Fit Advisor + Performance Benchmark（Module 2 & 3）

**預估時間：** 2 週  
**前置條件：** Phase 2 完成

**目的：** 幫使用者判斷適合跑什麼模型，並找出效能瓶頸。

---

## 🎯 核心目標

> 使用者能知道：為什麼慢、該換什麼模型、context length 怎麼調、bottleneck 在哪。

---

## ✅ Checklist

### 3.1 後端 — Model Fit Advisor API

- [ ] 建立 `/api/diagnostics/model-fit` endpoint
- [ ] 根據 RAM/VRAM 推薦模型大小（7B/8B/14B/32B）
- [ ] 根據任務推薦模型（摘要、問答、RAG、coding）
- [ ] 建議合理 context length
- [ ] 警告：模型過大、context length 過大、parallel request 記憶體壓力
- [ ] 推薦模式：Fast / Quality / Low-resource / RAG / Coding

### 3.2 後端 — Performance Benchmark API

- [ ] 建立 `/api/diagnostics/benchmark` endpoint
- [ ] 測量 first-token latency
- [ ] 測量 tokens/sec
- [ ] 測量 total generation time
- [ ] 測量 embedding latency
- [ ] 測量 retrieval latency
- [ ] 測量 vector DB query time

### 3.3 後端 — Bottleneck 診斷

- [ ] 判斷瓶頸：generation / retrieval / embedding / vector DB / memory / CPU fallback
- [ ] 產生 Suggested Fix 列表

### 3.4 前端 — Model Fit 頁面

- [ ] 顯示各模式推薦（模型 + context length）
- [ ] 顯示 Avoid 列表與 Warning

### 3.5 前端 — Performance 頁面

- [ ] 「Run Benchmark」按鈕 + 執行進度
- [ ] 顯示各項指標結果
- [ ] 視覺化 bottleneck（色條 / 紅黃綠燈）
- [ ] 顯示 Diagnosis 與 Suggested Fix

### 3.6 測試

- [ ] 單元測試：模型推薦邏輯、bottleneck 判斷
- [ ] 整合測試：API 正常 / 異常回傳

---

## 📌 完成標準

- [ ] Model Fit 頁面能根據硬體給出合理推薦
- [ ] Performance 頁面能跑 benchmark 並顯示結果
- [ ] 能正確識別 bottleneck 並給出建議
- [ ] 測試通過

---

## ➡️ 下一步

完成後前往 → [Phase 4：Privacy / Security Guard](./phase-4-privacy-guard.md)
