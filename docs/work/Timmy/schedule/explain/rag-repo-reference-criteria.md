# 適合參考的 RAG Repo 條件

## 核心原則

適合參考的 repo 不是「功能最完整」的，而是：

> RAG 訊號清楚、授權安全、檔案小、可重現、沒有 secret、適合轉成我們自己的最小 fixture。

建議做法：

```text
參考真實 repo 的結構與 patterns
↓
抽出 scanner 測試需要的 deterministic signals
↓
建立 project-owned minimal fixture
```

不建議：

```text
直接整包複製外部 repo 當測試 fixture
```

## 1. RAG 流程要清楚

最好能看出以下流程：

```text
data source
↓
document loader
↓
chunking / splitter
↓
embedding
↓
vector store
↓
retriever
↓
prompt builder
↓
LLM
↓
response / citation
```

適合：

- 有 `ingest.py`
- 有 `retriever.py`
- 有 `app.py` / `main.py`
- 有 vector store client
- 有 LLM call
- 有 prompt builder 或 response composer

不適合：

- 只有 notebook
- 只有 README
- 架構藏在大量 wrapper 裡
- 看不出 RAG 流程

## 2. 檔案數量要小，結構要簡單

適合：

- 小型 sample repo
- `src/` 結構清楚
- 主要檔案約 10-50 個以內
- 沒有大量無關模組

不適合：

- 大型 monorepo
- 包含大量 frontend、notebook、dataset、model 檔案
- 有很多跟 RAG scanner 無關的服務
- 歷史實驗程式碼太多

## 3. Dependency 要明確

最好有其中之一：

- `requirements.txt`
- `pyproject.toml`
- `package.json`

適合出現的 dependency signal：

- `langchain`
- `llama-index`
- `openai`
- `qdrant-client`
- `chromadb`
- `faiss`
- `ollama`
- `fastapi`
- `streamlit`

不適合：

- 沒有 dependency manifest
- 只在 README 裡手動列安裝步驟
- dependency 藏在 notebook 裡
- 需要先執行特殊 script 才知道依賴

## 4. Config / Docker / Env 線索要明確

適合有：

- `docker-compose.yml`
- `Dockerfile`
- `.env.example`
- `config.yaml`
- `config.yml`
- `settings.json`

適合的 scanner signals：

- `qdrant/qdrant` image
- `ollama/ollama` image
- published ports
- `OPENAI_API_KEY`
- `VECTOR_DB_URL`
- `MODEL_NAME`
- `EMBEDDING_MODEL`

不適合：

- 完全沒有 config
- 設定都藏在雲端平台
- 必須登入服務才看得到設定
- config 依賴本機 absolute path

## 5. 不能有真 Secret

不能有：

- 真 API key
- 真 token
- 真 password
- 真 `.env`
- 真 cloud credential
- 真 database credential

可以有：

- `.env.example`
- `OPENAI_API_KEY=sk-test-example`
- `FAKE_API_KEY=example-only`
- `TOKEN=replace-me`

如果 repo 有疑似真 secret，不適合直接拿來當 fixture 來源。

## 6. 不需要真的跑起來

Task 4 是 scanner fixture，不是 RAG demo。

適合：

- 不啟動 Docker 也能分析
- 不 call OpenAI 也能分析
- 不下載模型也能分析
- 不連資料庫也能分析
- 靠檔案內容就能提供 scanner signals

不適合：

- 一定要連外部 API 才看得出架構
- 一定要下載大型模型
- 一定要登入雲端平台
- 一定要啟動完整服務才能理解程式碼
- 一定要有真資料集才能看出 RAG 流程

## 7. 授權要清楚

優先參考：

- MIT
- Apache-2.0
- BSD
- 官方 examples / samples
- 明確允許使用與修改的 license

避免：

- 沒有 `LICENSE`
- 授權不明
- 禁止修改
- 禁止再散布
- 商業限制很重

即使授權允許，也建議只參考 pattern，不整包複製。

## 8. 技術棧最好貼近本專案要掃的 RAG 類型

優先：

- Python
- FastAPI
- LangChain
- LlamaIndex
- Qdrant
- Chroma
- FAISS
- Ollama
- OpenAI

可接受：

- Node.js / TypeScript RAG sample
- Next.js + LangChain
- Streamlit RAG demo

Task 4 初期建議優先 Python，因為後續 scanner providers 較容易測。

## 9. 最好有多種 Scanner Signal

理想 repo 長這樣：

```text
sample-rag/
├── README.md
├── requirements.txt
├── .env.example
├── docker-compose.yml
└── src/
    ├── app.py
    ├── ingest.py
    ├── retriever.py
    └── config.py
```

這種 repo 可以同時支援後續測試：

- filesystem inventory
- config parser
- docker compose parser
- dependency manifest parser
- code pattern scanner
- component detection
- endpoint detection
- flow derivation

## 10. 結構不要太魔法

適合：

- 清楚的 `app.py`
- 清楚的 `ingest.py`
- 清楚的 `retriever.py`
- 清楚的 config
- 明確的 function / class 名稱

不適合：

- 大量 dynamic import
- 大量 metaprogramming
- 設定藏在 framework plugin 裡
- 所有邏輯都在遠端平台
- scanner 很難用 deterministic rules 辨識

## 11. 不要太依賴特殊平台

避免：

- 只支援 Linux shell script
- 寫死 absolute path
- 依賴特定本機目錄
- 依賴特定雲端帳號
- 依賴私有服務

原因：

- 本專案需要兼顧 macOS / Windows。
- Scanner tests 應該跨平台可重現。

## 12. 安全狀態不要太糟

不適合參考：

- workflow 明顯危險
- 大量不明 binary
- 大量 secret-like 字串
- 依賴來源混亂
- 沒有維護跡象
- 會要求執行不明 install script

可以用 OpenSSF Scorecard 或 repo 維護狀態當輔助參考，但不是唯一標準。

## 挑選標準表

| 條件 | 適合 | 不適合 |
|---|---|---|
| 大小 | 小型 sample | 大型 monorepo |
| RAG 流程 | 清楚可讀 | 藏在抽象框架裡 |
| dependency | `requirements.txt` / `pyproject.toml` 明確 | 手動安裝、不完整 |
| config | 有 `docker-compose.yml` / `.env.example` | 完全沒有設定檔 |
| secret | 只有 fake / example key | 有真 key 或真 `.env` |
| 執行需求 | 不跑也能分析 | 必須連雲端或下載模型 |
| 授權 | MIT / Apache / BSD | 無 license 或限制不明 |
| 測試價值 | 多種 scanner signal | 只有單一 notebook |
| 跨平台 | 相對路徑、簡單檔案 | absolute path / OS-specific |
| 安全性 | 沒有明顯敏感資料 | secret-like 字串很多 |

## 最終建議

最適合參考的 repo 是：

- 小型
- Python 為主
- RAG 流程清楚
- 有 `requirements.txt` / `pyproject.toml`
- 有 `docker-compose.yml` 或 `.env.example`
- 沒有真 secret
- 授權清楚
- 不用真的跑起來
- 可以抽出 deterministic scanner signals

最後仍建議建立自己的 fixture：

```text
公開 RAG sample repo
↓
參考架構與 patterns
↓
轉寫成 project-owned minimal fixture
↓
放進 tests/fixtures/rag_projects/
```
