# Backend Architecture Overview

分析日期：2026-04-26  
專案路徑：`/Users/linjunting/Desktop/IT_Ticket_System_最新版`

## 審查規則摘要

兩份規則的核心原則可整理為：

- 資料結構優先：先弄清資料如何流動、誰擁有、誰修改，再談程式碼。
- 簡潔與好品味：消除特殊情況，比增加 if/else 補丁更好；函式與模組應短小、直白、可讀。
- 實用主義：解決真實生產問題，避免為理論場景增加複雜抽象。
- 不破壞既有使用者：重構需保留 API、檔案格式與資料相容性。
- 效能與可靠性：不能用不必要的抽象、全域狀態或背景流程讓穩定性倒退。
- 安全不是裝飾：檔案操作、外部呼叫、LLM 產出與設定 API 必須有明確邊界。

## 後端技術棧

| 類型 | 技術 |
|---|---|
| Web framework | Flask 3.x、Blueprint |
| API 型態 | JSON API、SSE streaming、檔案下載 |
| AI / RAG | AutoGen agentchat、Ollama cloud/local、Power Automate AI Builder、sentence-transformers、CrossEncoder |
| 資料處理 | pandas、numpy、openpyxl、scikit-learn KMeans、HDBSCAN、UMAP |
| 向量搜尋 | FAISS、pickle text mapping、JSON metadata |
| 資料庫 | SQLite `resultDB.db`，手寫 SQL，無 ORM / migration |
| 檔案儲存 | `uploads/`、`json_data/`、`chat_history/`、`excel_result_*`、`cluster_excels/`、`config/*.json` |
| 設定 | `.env`、`core/config_loader.py`、JSON config |
| 測試 | pytest、pytest-cov、unit / integration / performance scaffold |
| 執行 | `python run_analysis.py` 啟動 Flask，`python build_kb.py` 重建 KB |

## 後端候選範圍

以下檔案與資料夾被列入後端範圍：

| 路徑 | 判斷 |
|---|---|
| `Analysis.py`、`run_analysis.py` | Flask app 建立、Blueprint 註冊、啟動流程 |
| `api/` | Controller / route / request parsing |
| `services/` | Business workflow：上傳分析、RAG、分群、設定、歷史、KB |
| `repositories/` | SQLite、FAISS、JSON session/progress 存取 |
| `core/` | DI、設定、錯誤處理、SQLite connection、logging |
| `agents/`、`gptChat.py`、`gpt_utils.py`、`SmartScoring.py` | RAG / AI orchestration 與風險評分核心 |
| `utils/` | Excel client、resource manager、validation、sync、prompt、sentence、Ollama client |
| `build_kb.py`、`query_sqlite.py` | KB 建置與 SQLite 查詢工具 |
| `tests/` | 後端單元、整合、效能測試 |
| `config/`、`StorageAddress/`、`gpt_data/`、`data/sentences/` | 後端設定與模型提示資料 |
| `templates/`、`static/` | 主要是前端，但 route 會 render template，因此列為相依資源 |

## 主要目錄職責

```text
.
├── Analysis.py                 # Flask app factory-like entry, blueprint registration
├── run_analysis.py             # Launcher: start Analysis.py, wait /ping, open browser
├── api/                        # Flask Blueprint routes
├── services/                   # Business workflows
├── repositories/               # File / SQLite / FAISS access
├── core/                       # Config, DB, DI, logger, error handling
├── agents/                     # SQL, Semantic, Hybrid, Follow-up agents
├── utils/                      # Excel, sync, validation, AI client, prompt helpers
├── config/                     # risk / weight / prompt JSON configs
├── data/sentences/             # risk sentence sources
├── gpt_data/                   # GPT prompt catalog and mapping
├── chat_history/               # Chat session JSON files
├── json_data/                  # Analysis result JSON files
├── excel_result_Unclustered/   # Raw analysis Excel output
├── excel_result_Clustered/     # Clustered details and summary Excel output
├── StorageAddress/             # Sync target path JSON
└── tests/                      # pytest suite
```

## 核心模組

### Application / API

- `Analysis.py` 直接載入 config、初始化目錄、註冊 logger/error handler，並把 `api/*_routes.py` 掛到 `/api/v2`。
- `api/upload_routes.py` 負責 Excel preview、upload、progress、uploaded files、duplicate compare。
- `api/chat_routes.py` 負責 RAG query、chat sessions、SSE streaming、local Ollama model list。
- `api/cluster_routes.py` 負責分群、cluster progress、clustered/summary downloads、KB status、legacy action。
- `api/config_routes.py` 負責權重、風險語句、Prompt、儲存路徑、資料夾清空。
- `api/history_routes.py` 負責歷史結果列表、下載、刪除與清空。
- `api/page_routes.py` 負責 template rendering。

### Service Layer

- `TicketService`：上傳檔案驗證、Excel 分析、AI 摘要/解法、風險分數、JSON/Excel 輸出、觸發 KB rebuild。
- `RAGService`：讀寫 chat history，呼叫 `gptChat.run_offline_gpt()` 或 `run_offline_gpt_with_status()`。
- `ClusterService`：讀取 unclustered Excel、逐列 AI 分類、輸出 clustered details / summary Excel。
- `ConfigService`：管理 JSON config、sentence DB、prompt catalog、sync path、資料夾清空。
- `HistoryService`：讀取 `json_data/`，管理 result / Excel / original upload 下載與刪除。
- `KBService`：用 lock file 包住 `build_kb.py`，重建 SQLite + FAISS。
- `RiskService`：計算 severity / frequency / impact score，用 KMeans 或固定門檻判斷風險。

### Repository / Data Access

- `BaseRepository`：SQLite cursor wrapper。
- `TicketRepository`：目前只儲存 upload progress JSON。
- `ChatRepository`：以 JSON 檔儲存 chat session。
- `ConfigRepository`：早期 JSON config wrapper，實際多數設定走 `ConfigLoader`。
- `FAISSRepository`：lazy load FAISS index、metadata、texts，提供 KB stats。

## API 請求完整流程

1. 使用者瀏覽器呼叫 Flask route，例如 `/api/v2/upload`。
2. `api/*_routes.py` 解析 request、做基本參數檢查。
3. route 透過 `core.dependencies.get_service()` 取得 singleton service。
4. service 執行 business workflow，必要時呼叫 repository / utils / agents。
5. 若需 AI，流程會走 Power Automate、雲端 Ollama、地端 Ollama fallback。
6. 結果寫入 JSON、Excel、SQLite 或 FAISS metadata。
7. route 回傳 JSON、SSE event stream 或 `send_file()`。
8. Exception 由 route try/except 或 `core/error_handler.py` 統一格式化。

## 資料流

### 上傳分析資料流

`xlsx upload -> uploads/original_*.xlsx -> pandas DataFrame -> TicketService row analysis -> RiskService + gpt_utils -> json_data/result_*.json -> excel_result_Unclustered/result_*_Unclustered.xlsx -> background build_kb.py -> SQLite + FAISS`

### RAG 查詢資料流

`query -> RAGService -> chat_history/{chat_id}.json -> gptChat AutoGen classifier -> SQLAgent / SemanticAgent / HybridQueryAgent -> SQLite + FAISS + LLM -> answer -> chat_history append`

### 分群資料流

`excel_result_Unclustered/*.xlsx -> ClusterService -> AI category memory cluster_excels/*_categories.json -> excel_result_Clustered/Details/*.xlsx -> excel_result_Clustered/Summaries/*.xlsx -> optional sync path`

## 錯誤處理與 logging

- `core/error_handler.py` 定義 `ValidationError`、`AIServiceError`、`DatabaseError` 與統一 error response。
- 多數 route 仍有本地 try/except，將 service exception 轉成 JSON。
- `core/logger.py` 設定 console + rotating file logs：`logs/app.log`、`logs/error.log`。
- Service 層大量使用 `log_info()`、`log_error()`，但部分長流程仍用 `print()`。

## 認證、授權與安全流程

目前程式碼沒有實作登入、API token、RBAC、CSRF 或 per-route authorization。`Analysis.py` 設定 Flask `SECRET_KEY`，但沒有實際登入狀態或權限模型。這代表所有 API 預設是「能連到服務的人都能操作」。

高風險 API 包含：

- `/api/v2/config/storage-address`
- `/api/v2/validate-path`
- `/api/v2/clear-folder`
- `/api/v2/open-clustered`
- `/api/v2/delete-result/<uid>`
- `/api/v2/clear-history`

## 資料庫互動方式

- SQLite schema 在 `core/database.py` 與 `build_kb.py` 內以字串建立，無 Alembic 或 migration。
- `metadata` 是 RAG/SQL 查詢主表，欄位包含 `id`、`text`、`subcategory`、`configurationItem`、`roleComponent`、`location`、`opened`、`analysisTime` 等。
- `high_risk_sentences` 是 SQLite 表，但風險語句實際也存在 `data/sentences/*.json`。
- SQLAgent 由 LLM 產生 SELECT SQL，透過 pandas `read_sql_query()` 查 SQLite。

## 第三方服務與外部系統

- Power Automate AI Builder：`POWERAUTOMATE_URL`、`POWERAUTOMATEANALYSIS_URL`、`POWERAUTOMATE_CLASSIFY_URL`、`POWERAUTOMATE_SUMMARY_URL`。
- Ollama cloud：`OLLAMA_CLOUD_BASE_URL`、`OLLAMA_API_KEY`、`OLLAMA_DEFAULT_MODEL`。
- Local Ollama：`OLLAMA_LOCAL_BASE_URL`、`OLLAMA_LOCAL_MODEL`。
- OneDrive / SharePoint-like sync path：`StorageAddress/SyncAddress.json`，目前以 manual sync strategy 為主。

## 測試架構

- `pytest.ini` 指定 `tests/`，啟用 strict markers，預設未啟用 coverage。
- `tests/unit/` 覆蓋 core、repositories、services、agents、utils。
- `tests/integration/` 覆蓋 API routes、RAG、upload、history、cluster、complete workflow。
- `tests/performance/` 有 RAG performance scaffold。
- `htmlcov/status.json` 顯示目前既有 HTML coverage 主要包含 `utils/*`，statement coverage 約 91.34%，branch coverage 約 86.02%；這不是全後端覆蓋率。

## 部署與執行

- 開發啟動：`python run_analysis.py`。
- `run_analysis.py` 會用 subprocess 啟動 `Analysis.py`，輪詢 `http://127.0.0.1:3333/ping`，再開瀏覽器。
- `Analysis.py` 目前在 `__main__` 使用 `debug=True`、`use_reloader=True`、port `3333`。
- 未找到 Dockerfile、docker-compose、GitHub Actions 或正式 CI/CD pipeline。

