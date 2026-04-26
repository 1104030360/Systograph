# IT Ticket System 主要流程與呼叫關係（視覺化＋新手版）

## 1) 系統入口與全域架構
```
┌──────────────────────┐
│ run_analysis.py      │  啟動 Flask, 呼叫 Analysis.py
└─────────┬────────────┘
          │
┌─────────▼────────────┐
│ Analysis.py          │  建立 Flask app，讀 config，註冊 Blueprint
│  - app.register_blueprint(upload_bp/chat_bp/...)         │
│  - index() → FrontEnd.html                               │
└─────────┬────────────┘
          │ (依路由分流)
┌─────────▼────────────┐
│ api/*.py Blueprints  │  upload / cluster / chat / config / history / page
└─────────┬────────────┘
          │ get_service("<name>") 來自 core.dependencies
┌─────────▼────────────┐
│ services/*_service.py│  核心業務邏輯（Ticket/RAG/Cluster/KB/Config/History）
└─────────┬────────────┘
          │ repositories + utils + external (AI/Excel/FAISS/DB)
┌─────────▼────────────┐
│ repositories/*.py    │  檔案/DB 存取（progress、chat history、FAISS/DB）
└──────────────────────┘
```

### 尚未實作 / 預留
- `services/ticket_service.py::_save_tickets_to_db`：預期將分析結果寫入 SQLite/DB，未實作。
- `services/rag_service.py::query`：sources 目前回傳空陣列，需補充引用來源。
- `api/cluster_routes.py` ⇄ `services/cluster_service.py`：多處 `pass`，流程跑得動但沒有錯誤處理/統計回填。

---

## 2) 上傳與分析主流程（前端 → 後端 → 儲存/同步 → 觸發 KB）
```
[前端頁面與JS]
templates/FrontEnd.html
static/js/FrontEnd.js
  表單送出 → XHR POST /api/v2/upload
  先 GET /api/v2/files、POST /api/v2/compare-file 做檔名/內容重複檢查
  監聽 upload 進度 → 顯示條、modal
        │
        ▼
[API]
api/upload_routes.py
  upload_file() → get_service("ticket")
        │
        ▼
[Service]
services/ticket_service.py
  upload_and_analyze()
    - 驗證副檔名/大小（utils.validation_utils）
    - 儲存原檔 uploads/original_<ts>.xlsx
    - process_uploaded_file()
        · validate_uploaded_file()（Pandas 讀檔）
        · _process_uploaded_file_async()
            ▸ SmartScoring.load_embeddings() 載入風險向量
            ▸ _combine_fields_with_priority() 合併欄位
            ▸ _analyze_row_async() 逐列：
                ◂ RiskService.calculate_* 分數/風險等級
                ◂ gpt_utils.analyze_with_ai_builder_then_fallback() 做摘要+解法
            ▸ TicketRepository.save_progress() → upload_progress.json
    - save_analysis_files()
        · json_data/<uid>.json
        · excel_result_Unclustered/<uid>_Unclustered.xlsx（ExcelClient+OpenPyXL）
        · sync_strategy.sync_to_cloud() 同步到指定路徑/雲端
    - _trigger_kb_rebuild() 背景呼叫 build_kb.py
    - _load_analysis_results() 讀回 JSON 前 100 筆回傳
        │
        ▼
[背景知識庫建置]
build_kb.py
  __main__ 或 KBService.sync_knowledge_base() 呼叫 build_kb()
  - sync_excel_row_to_sqlite_custom()：Excel → SQLite metadata
  - build_kb()：讀 json_data/*.json → 文字 + 向量 (SentenceTransformer) → FAISS index + kb_texts.pkl + kb_metadata.json + SQLite resultDB.db
```

### 白話步驟
1. 在首頁選檔/拖曳，前端先檢查「是否重複」再送出。
2. Flask `upload_file` 收到表單，交給 TicketService。
3. TicketService 先存原檔，再用 Pandas 讀檔，逐列跑 AI 風險/摘要/解法，並更新進度檔。
4. 結果存成 JSON + Unclustered Excel，再嘗試同步到你的 SharePoint 目錄；接著觸發建 KB 背景程式。
5. 前端收到回應，顯示前 100 筆；KB 重建完成後，可在 Chat/RAG 或歷史檔案使用。

### TODO/預留
- `_save_tickets_to_db`：應把 results 寫入 SQLite/DB，供後續查詢/報表。
- 同步策略目前 manual-first（`utils.sync_strategy`），可換成自動 OneDrive/Graph。
- 風險/AI 分析依賴外部服務（Power Automate/Ollama），測試需 mock。

---

## 3) 聚類流程（Unclustered → Clustered/Details）
```
[觸發點]
前端 generate_cluster.html → AJAX /api/v2/cluster-excel
        │
        ▼
api/cluster_routes.py
  cluster_excel() → get_service("cluster") → ClusterService.perform_clustering()
        │
        ▼
services/cluster_service.py
  perform_clustering() → cluster_excel()
    - 列出 excel_result_Unclustered/*_Unclustered.xlsx
    - 讀檔 → 逐列 _classify_summary_with_ai() 產生 aiCategory（PowerAutomate）
    - 去重 deduplicate_by_id_and_time()
    - 覆寫回 Unclustered Excel（ExcelClient+safe_excel_operation）
    - _cluster_excel_export():
        · 依 configurationItem + aiCategory 分群
        · 匯出 Clustered/Details 檔案（含同步到 sync_path/IncidentAnalysis_Clustered_File/Details）
        · 產生群組摘要 _summarize_group_to_excel()
    - 搬移原檔到 excel_result_Clustered/<uid>_Clustered.xlsx
        │
        ▼
[進度/檔案]
utils.cluster_utils.append_cluster_progress() → cluster_progress.json
api/cluster_routes.py::cluster_progress / clustered-files / download-clustered 提供查詢/下載
```

### 白話步驟
1. 在「分群」頁按開始，後端找出所有 Unclustered Excel。
2. 每筆資料用 AI 判斷 aiCategory，補寫回同一檔案。
3. 依 Config Item + aiCategory 分群，輸出多個 Clustered/Details Excel，並嘗試同步到設定的 SharePoint 路徑。
4. 原 Unclustered 檔搬到 Clustered 資料夾，前端可下載查看。

### TODO/預留
- `cluster_service.py` 多處 `pass`（錯誤處理/日誌缺漏）。
- 若 AI 服務失敗目前默認 "uncategorized"，可增加重試或 fallback。

---

## 4) 知識庫同步與健康檢查（KBService）
```
api/cluster_routes.py::kb_status          → KBService.get_kb_status()
api/config_routes.py::sync-knowledge-base → KBService.sync_knowledge_base(force?)
        │
        ▼
services/kb_service.py
  sync_knowledge_base():
    - 鎖檔檢查/建立 → _backup_kb()
    - 呼叫 build_kb.build_kb()
    - 移除鎖 → 回傳統計
  get_kb_status():
    - 檢查 kb_index.faiss / kb_metadata.json / resultDB.db 是否存在
    - 回傳 last_sync_time / total_records (FAISSRepository)
```

### 白話步驟
1. 透過設定頁或 API 觸發「同步 KB」。
2. 如果沒鎖，先備份舊資料，再跑 build_kb（讀 JSON → 建 SQLite + FAISS）。
3. 跑完移除鎖；前端可用 `/kb-status` 看到是否在建置、資料筆數。

### TODO/預留
- 鎖檔以檔案實作，沒有跨機制；如有多機需改為共享鎖。
- FAISSRepository/SQLite 失敗時僅記 log，可加告警/重試。

---

## 5) RAG/對話流程
```
[UI]
templates/chat.html → fetch POST /api/v2/chat
        │
        ▼
api/chat_routes.py
  chat_with_model() → get_service("rag") → RAGService.query()
        │
        ▼
services/rag_service.py
  query():
    - load_history() (ChatRepository) 最近 N 輪
    - asyncio.run(gptChat.run_offline_gpt(message, history,...))
    - append_messages() 儲存到 chat_history/<id>.json
    - 回傳 answer + sources (TODO: currently [])
```

### 白話步驟
1. 在聊天頁輸入問題，送到 `/chat`。
2. RAGService 把同會話的歷史載入，呼叫 gptChat 做 RAG 回答。
3. 回答後把問答紀錄寫回檔案，下次聊天會帶入上下文。

### TODO/預留
- `sources` 尚未填入，可從 gptChat/agents 的檢索結果帶回。
- gptChat 內部依賴 agents/*，若要換模型/策略需同步調整。

---

## 6) 其他路由/流程（重點）
- 設定/儲存路徑：`api/config_routes.py` → ConfigService → utils.config_utils / StorageAddress/SyncAddress.json。
- 歷史列表：`api/history_routes.py` → HistoryService（讀 json_data / clustered 資料）。
- 前端靜態頁：`api/page_routes.py` 回傳 Jinja 模板。

---

## 未完成/預留清單（集中）
- `services/ticket_service.py::_save_tickets_to_db` 未實作：應把分析結果寫 SQLite（`core.database` 或 `repositories`）供報表/查詢。
- `services/rag_service.py::query` 的 `sources` 為 TODO：需從 gptChat/agents 傳回引用列表。
- `services/cluster_service.py` 多處 `pass`：缺少錯誤處理與日誌，失敗時不會中斷但也不會告知原因。
- 同步策略：`utils.sync_strategy` 為 manual-first，無真正雲端 API；待換成 OneDrive/SharePoint SDK 或 webhook。
- 測試覆蓋：AI/HTTP 相關需 mock；build_kb 背景流程目前無健康檢查 API。

---

## 小結（給新手的整體口語版）
1. **啟動**：跑 `run_analysis.py` → Flask 起來，首頁在 `Analysis.py`，路由交給各 Blueprint（upload/cluster/chat 等）。
2. **上傳分析**：前端檢查不重複 → `/api/v2/upload` → TicketService 做驗證、AI 風險、產出 JSON + Excel、嘗試同步，並啟動 KB 重建。
3. **建知識庫**：背景的 build_kb 讀所有 JSON，重建 SQLite + FAISS，提供後續查詢。
4. **分群**：有 Unclustered Excel 時，ClusterService 用 AI 分類、分群輸出 Clustered/Details，並同步到設定路徑。
5. **聊天/RAG**：聊天頁送到 RAGService，帶歷史呼叫 gptChat，回答後存回 chat_history。
6. **設定/歷史**：設定同步路徑、查看歷史檔案/結果都透過對應的 Blueprint + Service 完成。
