# Phase 2：Environment Scanner（Module 1）

**預估時間：** 2 週  
**前置條件：** Phase 1 完成

**目的：** 幫使用者診斷本機 AI 環境是否準備好，自動偵測硬體、服務狀態與模型運行情況。

---

## 🎯 核心目標

> 使用者能知道：local AI stack 是否正確啟動、模型是否載入、模型在哪裡執行、環境是否基本健康。

---

## ✅ Checklist

### 2.1 後端 — 系統資訊偵測 API

- [ ] 建立 `/api/diagnostics/environment` endpoint
- [ ] 偵測 OS（類型、版本）
- [ ] 偵測 CPU（型號、核心數）
- [ ] 偵測 RAM（總量、已使用、可用）
- [ ] 偵測 GPU / VRAM（如果可取得，例如透過 `nvidia-smi` 或 macOS `system_profiler`）
- [ ] 偵測 Docker 是否可用（`docker info`）
- [ ] 偵測 Ollama 是否安裝並運行（`curl http://localhost:11434/api/version`）
- [ ] 偵測 Qdrant 是否啟動（`curl http://localhost:6333/healthz`）

### 2.2 後端 — 模型狀態偵測 API

- [ ] 取得 Ollama models list（`/api/tags`）
- [ ] 取得目前 loaded model 狀態（`/api/ps`）
- [ ] 判斷模型目前是 CPU / GPU / hybrid 執行
- [ ] 回傳結構化 JSON 結果

### 2.3 後端 — 健康分數計算

- [ ] 定義 Environment Health Score 計算規則（0–100 分）
  - 例如：OS 偵測成功 +10，RAM ≥ 16GB +15，Ollama running +20，GPU available +20 ...
- [ ] 分級：Healthy（≥ 80）、Warning（50–79）、Critical（< 50）
- [ ] 根據結果生成 recommendations 列表

### 2.4 前端 — Environment 頁面

- [ ] 呼叫後端 API 取得環境資訊
- [ ] 顯示系統資訊卡片（OS、CPU、RAM、GPU）
- [ ] 顯示服務狀態卡片（Docker、Ollama、Qdrant）— 用 ✅ / ❌ / ⚠️ 圖示
- [ ] 顯示模型列表與當前 loaded model
- [ ] 顯示 Health Score（大數字 + 進度環或色條）
- [ ] 顯示 Recommendations 列表

### 2.5 測試

- [ ] 寫單元測試：各偵測函式在服務不可用時的 graceful fallback
- [ ] 寫整合測試：API endpoint 回傳正確結構
- [ ] 測試 Ollama 未啟動時的行為
- [ ] 測試 Qdrant 未啟動時的行為

---

## 📋 範例輸出（供 UI 參考）

```text
Environment Health: 78/100

Detected:
- OS: macOS
- RAM: 16 GB
- Ollama: Installed
- Docker: Installed
- Qdrant: Running
- Loaded model: llama3.1:8b
- Processor: 100% GPU

Recommendation:
- Suitable for 7B–8B local models
- Avoid 32B models
- Keep context length under 8K
```

---

## 📌 完成標準

- [ ] 打開 Environment 頁面能看到完整的系統資訊
- [ ] 各服務狀態即時反映（Ollama 停掉就顯示 ❌）
- [ ] Health Score 有數字且有分級顏色
- [ ] 有合理的 Recommendations
- [ ] 測試全部通過

---

## ➡️ 下一步

完成後前往 → [Phase 3：Model Fit Advisor + Performance Benchmark](./phase-3-model-fit-benchmark.md)
