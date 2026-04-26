# Excel 上傳到知識庫的全流程（視覺化解釋版）

## 一、核心概念總覽（WHAT）
透過前端拖曳上傳 Excel，後端 Flask API 呼叫 TicketService 完成驗證、AI 風險評分、JSON/Excel 輸出與同步，並觸發知識庫重建，最後把前 100 筆結果回傳給使用者與後續 RAG/Chat 使用。

```
┌──────────┐   ┌───────────────────┐   ┌────────────────┐   ┌─────────────┐   ┌───────────────┐
│ 使用者   │→ │ 前端頁面+JS        │→ │ Flask API       │→ │ TicketService │→ │ 儲存&同步      │
└──────────┘   │ (FrontEnd.html    │   │ (/api/v2/upload│   │ + Risk/AI    │   │ JSON/Excel/KV │
               │  + static/js)     │   │  /preview ...) │   │ + ExcelClient│   └────┬──────────┘
               └─────────┬─────────┘   └────────┬──────┘   └───────┬──────┘        │
                         │                      │                   │               │
                         ↓                      ↓                   ↓               ↓
                  進度/重複檢查           儲存原檔            AI 分析與風險       build_kb.py
                                                             （gpt_utils、        → SQLite/FAISS
                                                             SmartScoring）        → RAG/Chat
```

## 二、現況分析（WHY）
目前採「前端表單 → API Blueprint → Service → Repository/Utility → 檔案+DB」的分層模式，保持前端輕薄、後端邏輯集中，同步跨平台（OpenPyXL + manual sync）。

```
分層關聯
┌─────────────┐  UI：templates/FrontEnd.html + static/js/FrontEnd.js
│ 前端 (Jinja)│  功能：拖曳上傳、權重/欄位設定、重複檢查、進度條、結果表格
└─────┬───────┘
      │ AJAX /api/v2/*
┌─────▼───────┐  API：api/upload_routes.py（上傳/預覽/進度/重複）
│ Flask Routes│       api/page_routes.py（頁面），其他：chat/cluster/config/history
└─────┬───────┘
      │ 依賴注入 core.get_service("ticket")
┌─────▼────────────┐ Service：services/ticket_service.py
│ TicketService    │ 負責驗證、Pandas 讀檔、AI 風險分析、儲存、觸發 KB
└─────┬────────────┘
      │ 借用 utils + repositories
┌─────▼──────────────┐ Utilities：excel_client / resource_manager / sync_strategy
│ ExcelClient(OpenPyXL│           gpt_utils, SmartScoring, config_utils
└─────┬──────────────┘
      │ 抽象存取
┌─────▼─────────┐ Repository：repositories/ticket_repository.py
│ Progress JSON │ 儲存進度 upload_progress.json
└──────────────┘
```

## 三、解決方案/概念詳解（HOW）

### 1) 前端互動（FrontEnd.html + static/js/FrontEnd.js）
```
拖曳/選檔 → 填欄位優先序 + 權重 → 兩段重複檢查
  ├─ GET /api/v2/files       （比對檔名）
  └─ POST /api/v2/compare-file（比對檔案內容 MD5）
合格後 → XHR POST /api/v2/upload
  - formData：file + weights + resolution_priority + summary_priority
  - 進度條：監聽 xhr.upload.onprogress
  - 回傳後：顯示前 100 筆表格、啟動 KB 狀態輪詢
```

### 2) API 層（api/upload_routes.py）
```
/preview         → TicketService.preview_file()（簡易讀檔）
/upload          → TicketService.upload_and_analyze()（主流程）
/progress        → TicketService.get_upload_progress()（讀 progress JSON）
/files           → TicketService.list_uploaded_files()（列舉 uploads/）
/compare-file    → MD5 比對檔案內容
```

### 3) TicketService 主流程（services/ticket_service.py）
```
upload_and_analyze()
  1. 基本驗證：檔名、格式（utils.validation_utils）、大小（10MB）
  2. 儲存原檔：uploads/original_<timestamp>.xlsx
  3. process_uploaded_file():
     a. validate_uploaded_file()：副檔名/大小/Pandas 讀檔檢查
     b. _process_uploaded_file_async():
        - 載入風險語句嵌入（SmartScoring.load_embeddings）
        - 合併欄位（_combine_fields_with_priority，Resolution/Summary）
        - 逐列分析 _analyze_row_async：
          ・RiskService: keyword/multi_user/escalation + frequency 計算
          ・AI：gpt_utils.analyze_with_ai_builder_then_fallback（Power Automate → Ollama）
          ・產出 impactScore/riskLevel/problem/solution 等
        - 進度寫入 TicketRepository.save_progress() → upload_progress.json
  4. save_analysis_files():
     - JSON：json_data/<uid>.json（序列化後供 KB/歷史下載）
     - Excel (Unclustered)：excel_result_Unclustered/<uid>_Unclustered.xlsx
       ・ExcelClient(OpenPyXL) + resource_manager.safe_excel_operation
       ・欄位重命名/去重（utils.data_utils.FIELD_MAPPING, deduplicate_by_id_and_time）
     - 手動同步：sync_strategy.sync_to_cloud() → 目標路徑 get_sync_target_path()
       ・成功/待人工/失敗都包成 response.sync 給前端
  5. 觸發知識庫重建：_trigger_kb_rebuild() 背景呼叫 build_kb.py
  6. 回傳：data 前 100 筆 + uid/jsonFilename + sync 狀態
```

### 4) 知識庫與資料庫（build_kb.py + core/database.py）
```
資料來源：json_data/*.json（分析結果）→ build_kb.py
處理：
  - 合併/格式化 → SQLite resultDB.db 表 metadata
  - 生成/更新 FAISS 向量檔：kb_index.faiss + kb_texts.pkl
  - 維護同步路徑（IncidentAnalysisDB.xlsx）供 SharePoint/OneDrive
用途：
  - RAG/Chat：gptChat.py、services/rag_service.py 從 SQLite/FAISS 檢索
  - 歷史/頁面：history_routes、頁面 result.html/history.html 讀取 json/DB
```

### 5) 回應前端與後續互動
```
API 回傳 → 前端表格顯示前 100 筆 + 風險徽章
KB 重建 → 前端輪詢 KB 狀態條（cluster_routes 提供 KB state）
歷史下載 → 前端存 localStorage + History 頁面讀 json_data/<uid>.json
Chat/RAG → 使用更新後的 SQLite/FAISS 提供語意回答
```

## 四、具體案例（時間軸示例）
```
T0 使用者拖曳 incident.xlsx，填欄位順序與權重 → 按「上傳」
T1 JS 檢查重複：/files 檢查檔名；/compare-file 檢查內容 → OK
T2 XHR /api/v2/upload 上傳，進度條顯示傳輸進度
T3 後端驗證/讀檔 → 逐列 AI 分析 → upload_progress.json 持續更新
T4 儲存：
   - uploads/original_<ts>.xlsx（原檔）
   - json_data/<uid>.json（分析結果）
   - excel_result_Unclustered/<uid>_Unclustered.xlsx（報表）
   - sync_result：寫入同步路徑或標記需人工
T5 build_kb.py 背景跑 → 更新 resultDB.db + kb_index.faiss
T6 API 回傳前 100 筆 → 前端 DataTable 顯示，提示「完整請到歷史」
T7 Chat/搜尋使用新的 KB；使用者可到 SharePoint/OneDrive 查看同步檔
```

## 五、優劣對比

| 面向           | 現況優點                                                     | 注意事項/限制                                   |
| -------------- | ------------------------------------------------------------ | ----------------------------------------------- |
| 前端體驗       | 拖曳上傳、即時進度、重複檢查、權重/欄位自訂                  | 需要正確設定同步路徑；僅顯示前 100 筆           |
| 後端架構       | Blueprint+Service 分層清楚；DI get_service；OpenPyXL 跨平台  | TicketService 邏輯集中較大，易變成巨石          |
| 資料輸出       | JSON+Excel 雙格式；去重與欄位映射一致；manual sync 狀態回傳 | sync_to_cloud 為手動策略，需人工確認             |
| 知識庫         | 自動觸發 build_kb → SQLite+FAISS 供 RAG/Chat                | build_kb 背景程序失敗時需檢查 kb_log.txt/lock   |
| 測試/偵錯      | progress 檔案易觀測；模組化 utils（excel_client/resource）  | AI 相關（gpt_utils）仍仰賴外部服務需 mock/隔離 |

## 六、實施建議
```
短期（新手上路）
  - 先確定同步路徑（/api/v2/storage-address 驗證），避免 sync 失敗
  - 上傳前用 /api/v2/preview 看欄位是否齊全（尤其 Opened/Description）
  - 若結果沒出現，先查 upload_progress.json 與 logs/kb_log.txt

中期（優化）
  - 將 TicketService 拆分：檔案驗證、AI 分析、儲存/同步 各自成類
  - 在前端顯示 KB 重建狀態與錯誤（讀 kb_log.txt 或 lock）
  - 對 build_kb 加入重試與告警，並在 history 頁提供「重建 KB」按鈕

長期（可靠性）
  - 將 sync_strategy 接 OneDrive SDK 或 Webhook，減少人工
  - 在 SQLite/FAISS 建立健康檢查路由，CI 中加入 pytest -q smoke 測試
  - 把 AI 分析結果寫入資料庫表，再定時匯出 Excel，簡化雙檔管理
```
