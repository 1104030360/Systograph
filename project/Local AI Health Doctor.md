# KAI-Mind 專案定案：Local AI Health Doctor

日期：2026-04-25

---

## 1. 專案最終定位

KAI-Mind 不再定位成一般的 local document chatbot，也不是 OpenClaw 類型的高權限 AI agent。

KAI-Mind 的新定位是：

> **KAI-Mind — Local AI Health Doctor**
>
> 一個本機 AI 健檢與診斷平台，幫助使用者判斷自己的 local AI 環境是否能穩定、安全、有效地運行。

英文一句話版本：

> **KAI-Mind is a local AI health diagnostics platform that helps users evaluate hardware compatibility, model runtime performance, privacy exposure, and RAG answer quality when running private LLM workflows on their own machines.**

中文一句話版本：

> **KAI-Mind 是一個本機 AI 健檢工具，幫助使用者診斷自己的電腦是否適合跑 local AI、為什麼模型變慢、設定是否安全，以及 RAG 回答是否可信。**

---

## 2. 為什麼選這個方向

目前市面上已經有很多 local document chat / local RAG / private AI workspace 工具，例如：

- AnythingLLM
- Open WebUI
- LM Studio
- Ollama-based chatbot
- 各種 Obsidian / local RAG plugin

如果 KAI-Mind 只是做：

> 上傳文件 → 本地 RAG → AI 問答

那很容易被取代，差異化不足。

所以 KAI-Mind 要改成：

> **不是幫使用者聊天，而是幫使用者診斷 local AI 到底能不能穩定、安全、可信地運行。**

---

## 3. 主要解決的使用者痛點

KAI-Mind 要解決的不是「整理資料」而已，而是 local AI 使用者真正遇到的痛點：

### 3.1 不知道自己的電腦能跑什麼模型

使用者常見問題：

- 我的電腦能跑 7B / 8B / 14B / 32B 模型嗎？
- 我的 RAM / VRAM 夠不夠？
- 模型現在是跑在 CPU、GPU，還是 hybrid？
- context length 設太大會不會爆記憶體？
- 我應該用什麼模型做摘要、問答、RAG、coding？

---

### 3.2 不知道 local AI 為什麼變慢

使用者常見問題：

- 為什麼回覆突然很慢？
- 是模型太大？
- 是 context length 太長？
- 是跑到 CPU 了？
- 是 retrieval 慢？
- 是 embedding 慢？
- 是 Qdrant / vector DB 慢？
- 是文件太多？

---

### 3.3 以為本地 AI 很安全，但其實設定錯

使用者常見問題：

- Ollama server 有沒有暴露到區網或外網？
- Qdrant endpoint 有沒有被其他人連到？
- cloud fallback 有沒有不小心開啟？
- `.env` 裡是不是有外部 API key？
- query 或文件有沒有被送到外部 API？
- 這次回答到底是不是完全本地生成？

---

### 3.4 不知道 RAG 回答可不可信

使用者常見問題：

- RAG 有沒有找對資料？
- 回答是不是根據文件？
- citation 是否真的支持答案？
- 有沒有 unsupported claims？
- 是 retrieval 出錯，還是模型亂編？
- chunk size、top_k、reranker 設定是否合理？

---

### 3.5 local AI 工具太分散，使用者不知道哪裡壞

使用者常需要自己拼：

- Ollama
- Qdrant
- Docker
- embedding model
- local LLM
- RAG pipeline
- frontend / backend
- vector DB
- prompt template
- reranker

KAI-Mind 要扮演的是：

> **local AI stack 的診斷層，而不是又一個聊天介面。**

---

## 4. 產品核心價值

KAI-Mind 要回答四個問題：

1. **跑不跑得動？**
   - 硬體是否適合？
   - 模型是否太重？
   - context length 是否合理？

2. **為什麼慢？**
   - 是 generation 慢？
   - retrieval 慢？
   - embedding 慢？
   - CPU fallback？
   - memory pressure？

3. **安不安全？**
   - 是否真的 local？
   - 是否暴露 endpoint？
   - 是否啟用外部 API？
   - 是否有 cloud fallback？

4. **答案可不可信？**
   - 有沒有 citation？
   - citation 是否支持回答？
   - 有沒有 hallucination / unsupported claims？
   - retrieval 是否找對資料？

---

## 5. MVP 核心模組

8 月前只做 5 個核心模組。

---

### Module 1：Local AI Environment Scanner

#### 目標

幫使用者診斷本機 AI 環境是否準備好。

#### 功能

- 偵測 OS
- 偵測 CPU
- 偵測 RAM
- 偵測 GPU / VRAM，如果可取得
- 偵測 Docker 是否可用
- 偵測 Ollama 是否安裝
- 偵測 Qdrant 是否啟動
- 列出本機 Ollama models
- 顯示目前 loaded model 狀態
- 顯示模型目前是 CPU / GPU / hybrid 執行

#### 範例輸出

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

### Module 2：Model Fit Advisor

#### 目標

幫使用者判斷自己的機器適合跑什麼模型與設定。

#### 功能

- 根據硬體推薦模型大小
- 根據任務推薦模型
- 建議 context length
- 警告模型過大
- 警告 context length 過大
- 警告 parallel request 可能造成記憶體壓力
- 推薦不同模式：
  - Fast Mode
  - Quality Mode
  - Low-resource Mode
  - RAG Mode
  - Coding Mode

#### 範例輸出

```text
Recommended Profile:
- Fast Mode: qwen2.5:7b, context 4096
- Quality Mode: llama3.1:8b, context 8192
- Coding Mode: qwen2.5-coder:7b, context 4096

Avoid:
- 14B+ models on current memory
- Context length above 16K
- Multiple parallel requests

Warning:
Your current context length is 32768.
This may cause CPU fallback and slow generation.
```

---

### Module 3：Performance Benchmark

#### 目標

幫使用者找出 local AI 慢在哪裡。

#### 功能

- 測量 first-token latency
- 測量 tokens/sec
- 測量 total generation time
- 測量 embedding latency
- 測量 retrieval latency
- 測量 vector DB query time
- 比較不同 context length 的效能
- 判斷 bottleneck：
  - model generation
  - retrieval
  - embedding
  - vector database
  - memory pressure
  - CPU fallback

#### 範例輸出

```text
Benchmark Result:
- First token latency: 1.2s
- Generation speed: 31 tokens/sec
- Total generation time: 4.8s
- Retrieval latency: 180ms
- Embedding latency: 420ms

Diagnosis:
- Generation is healthy
- Retrieval is acceptable
- Context length may be too high for large documents

Suggested Fix:
1. Reduce context length from 16384 to 8192
2. Use an 8B model instead of 14B
3. Disable parallel requests
```

---

### Module 4：Privacy / Security Guard

#### 目標

幫使用者確認 local AI 是否真的安全、真的沒有把資料送出去。

#### 功能

- 檢查 Ollama 是否只綁 localhost
- 檢查 Qdrant 是否只在本機可存取
- 檢查 cloud fallback 是否關閉
- 檢查是否存在外部 API key
- 檢查是否呼叫外部 provider
- 顯示 Data Leaves Device: Yes/No
- 顯示本機服務暴露風險
- 提供 security checklist

#### 範例輸出

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

### Module 5：RAG Quality Inspector

#### 目標

幫使用者判斷 RAG 回答到底可不可信。

#### 功能

- 顯示 retrieved chunks
- 顯示回答引用了哪些 chunk
- 顯示 citation coverage
- 檢查答案是否有 unsupported claims
- 檢查 retrieval 是否找錯資料
- 顯示 RAG quality score
- 提供改善建議：
  - 調整 chunk size
  - 調整 top_k
  - 啟用 reranking
  - 更換 embedding model
  - 補充 metadata
  - 清理重複文件

#### 範例輸出

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

## 6. 從原本 KAI-Mind 轉過去的方式

KAI-Mind 不需要砍掉重練，而是加上一層 diagnostics layer。

| 原本 KAI-Mind 功能 | 轉型後用途 |
| --- | --- |
| 文件上傳 | 用來測試 local RAG pipeline |
| RAG 問答 | 變成 RAG Quality Inspector 的測試對象 |
| Ollama provider | 變成 local model runtime scanner |
| Qdrant / vector DB | 變成 retrieval latency / index health 檢查 |
| No-cloud mode | 變成 Privacy Guard |
| Citation | 變成 answer trustworthiness report |
| Docker Compose | 變成 local AI stack 一鍵診斷環境 |
| Workspace | 變成不同 diagnosis profile |

---

## 7. 8 月前開發 Roadmap

---

### Phase 0：從零建構專案基礎

**時間：** 2.5–3 週  
**核心原則：** 先 service layer，後 LangGraph。先寫乾淨可測的 service function，後續再用 workflow 串起來。

**要做：**

- **Phase 0a（1 週）：專案骨架 + 協作基礎**
  - GitHub repo + branch protection + Project board + labels + issue template
  - 專案目錄結構（backend / frontend / docker）
  - FastAPI 後端 skeleton + `/healthz` endpoint
  - 前端 skeleton（Vite + React + Tailwind，基本 dashboard layout）
  - Docker Compose（backend + frontend + Qdrant）
  - **Environment Scanner 最小版**（OS / CPU / RAM / Ollama / Qdrant 狀態）
- **Phase 0b（1.5–2 週）：Service Layer + CI + 文件**
  - Ollama service（version / models / generate，graceful fallback）
  - Qdrant service（health / collections，graceful fallback）
  - 系統偵測擴展（GPU / Docker / loaded model 狀態）
  - Environment Health Score 計算（0–100 分）
  - 程式碼品質（black + ruff + eslint + prettier）
  - CI/CD（GitHub Actions: lint + test + gitleaks）
  - 測試框架 + smoke tests + service mock tests
  - README + CONTRIBUTING + LICENSE

**完成標準：**

> docker compose up 能啟動所有服務、Environment Scanner API 回傳完整系統資訊、每個 service function 獨立可測、CI 自動跑 lint + test、兩人都能跑全系統。

---

### Phase 1：重新定位與 UI 骨架

**時間：** 1 週

**要做：**

- README 改成 Local AI Health Doctor
- 專案首頁改成診斷 dashboard
- 建立 5 個主要頁面：
  - Environment
  - Model Fit
  - Performance
  - Privacy
  - RAG Quality
- 保留原本 KAI-Mind local RAG engine

**完成標準：**

使用者一進入專案就知道：

> 這不是文件聊天工具，而是 local AI diagnostics tool。

---

### Phase 2：Environment Scanner

**時間：** 2 週

**要做：**

- 偵測 OS
- 偵測 CPU / RAM
- 偵測 GPU / VRAM，如果可行
- 偵測 Docker
- 偵測 Ollama
- 偵測 Qdrant
- 取得 Ollama models list
- 取得 Ollama loaded model status
- 建立 environment health score

**完成標準：**

使用者能知道：

- local AI stack 是否正確啟動
- 模型是否載入
- 模型在哪裡執行
- 環境是否基本健康

---

### Phase 3：Model Fit Advisor + Performance Benchmark

**時間：** 2 週

**要做：**

- 模型推薦規則
- context length checker
- tokens/sec benchmark
- first-token latency
- total generation latency
- embedding latency
- retrieval latency
- bottleneck diagnosis

**完成標準：**

使用者能知道：

- 為什麼 local AI 慢
- 應該換什麼模型
- context length 應該怎麼調
- bottleneck 在哪一層

---

### Phase 4：Privacy / Security Guard

**時間：** 1–2 週

**要做：**

- localhost exposure check
- cloud fallback check
- provider log
- external API key warning
- Data Leaves Device status
- basic security checklist

**完成標準：**

使用者能確認：

- local AI 是否真的 local
- 是否有外部 API 風險
- 是否有 endpoint 暴露風險

---

### Phase 5：RAG Quality Inspector

**時間：** 2 週

**要做：**

- retrieved chunk viewer
- citation coverage
- unsupported claim check
- RAG quality score
- improvement recommendation
- basic report export

**完成標準：**

使用者能知道：

- RAG 是否找對資料
- 回答是否有 citation
- 哪些句子沒有來源支持
- RAG pipeline 可以怎麼改善

---

### Phase 6：工程品質與履歷包裝

**時間：** 1–2 週

**要做：**

- GitHub Actions
- pytest
- CodeQL
- Docker Compose
- README architecture diagram
- demo video
- sample diagnosis report
- API documentation
- issue / roadmap 整理

**完成標準：**

專案可以放進履歷，並且能支撐面試故事。

---

## 8. 最終 Demo 流程

8 月前最終 demo 應該長這樣：

1. 使用者啟動 KAI-Mind
2. Dashboard 自動掃描本機環境
3. 顯示 Ollama / Qdrant / Docker 狀態
4. 顯示本機可跑的模型建議
5. 跑一次 local LLM benchmark
6. 顯示 tokens/sec、retrieval latency、generation latency
7. Privacy Guard 顯示 Data Leaves Device: No
8. 使用者上傳文件並問問題
9. RAG Quality Inspector 顯示 citation coverage 與 unsupported claims
10. 匯出 diagnosis report

---

## 9. 8 月前最低可交付版本

如果時間不足，最低要完成：

- Environment Scanner
- Model Fit Advisor
- Performance Benchmark
- Privacy Guard
- RAG Quality Inspector 基礎版
- Docker Compose
- README
- Demo video
- GitHub Actions + pytest