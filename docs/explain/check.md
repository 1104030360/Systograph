# IT_Ticket_System 前端與資料流檢查紀錄

## 1. FrontEnd.js（共用前端邏輯）

### 1.1 檔案用途與主要功能

- 首頁/上傳頁的共用腳本，處理拖曳/選檔、權重計算與驗證、重複檢查、預覽、送出分析、歷史清單載入、同步路徑驗證與 KB 建庫狀態提示。

### 1.2 功能 → 後端 → 資料庫 路徑檢查

- 上傳流程：表單送出 `POST /api/v2/upload`（附 weights、resolution_priority、summary_priority）→ `services/ticket_service.upload_and_analyze` → 儲存 `uploads/`、輸出 `json_data/`，回傳 uid/data；欄位與前端需求一致。
- 預覽：`POST /api/v2/preview` → `ticket_service.preview_file` 讀前 50 筆；欄位 columns/rows 符合。
- 重複檢查：`GET /api/v2/files`、`POST /api/v2/compare-file` → `ticket_service` 列檔/MD5 比對；流程相符。
- 路徑設定：`POST /api/v2/validate-path`、`POST /api/v2/storage-address` → `config_service.validate_path/update_storage_address`（檢查並寫入同步路徑）；參數對應。
- 歷史載入：`GET /api/v2/history-list` → `history_service.list_history`（檔案型紀錄，欄位 uid/file_name/created_at）；前端使用 file_name/summary/time 對應。
- KB 狀態：`GET /api/v2/kb-status` → `kb_service.get_kb_status`，前端以 building/is_building 判斷；對應。

### 1.3 發現的問題 / 潛在風險

- [阻斷性｜會造成問題] `static/js/FrontEnd.js` 上傳提交時使用 `submitBtn.disabled` 但未在該 submit handler 作用域宣告 `submitBtn`，會觸發 `ReferenceError` 而中止送出。  
  - 處理結果：已在提交函式內取得 `submitBtn`，避免未定義錯誤。
- [回傳欄位不符｜會造成問題] 一鍵清空資料夾 (`static/js/FrontEnd.js` → `POST /api/v2/clear-folder`) 以 `data.success` 判斷；後端 `services/config_service.clear_folder` 回傳鍵為 `status`，成功會被誤判為失敗且 UI 不重新整理。  
  - 處理結果：前端改讀 `status === 'success'`，邏輯已對齊。
- [參數不符｜會造成問題] 清空資料夾傳入鍵如 `cluster_excels`、`unclustered` 等，後端預期實際存在的資料夾路徑，若不存在會回傳 `FOLDER_NOT_FOUND`，前端未顯示原因，實際不會清除也無提示。  
  - 處理結果：前端改用實際路徑清單；後端 `clear_folder` 對不存在資料夾會自動建立並回傳成功，避免失敗。
- [可讀性風險] `updateSharePointStatus` / `updateDatabaseCount` 在檔案內各被定義兩次，前者僅以路徑存在判定連線，未檢查後端回傳的 `writable`，易造成狀態判讀混淆。

### 1.4 API key / URL 相關

- 未發現占位符或缺漏的 API key / URL。

---

## 2. Chat 頁面（chat.html / static/js/chat_ui.js）

### 2.1 檔案用途與主要功能

- 離線聊天 UI：歷史會話列表（搜尋/分頁）、標題編輯/刪除、訊息送出與顯示、模型選擇。

### 2.2 功能 → 後端 → 資料庫 路徑檢查

- 歷史列表：`GET /api/v2/chat/sessions` → `services/rag_service.list_sessions`（讀取 `chat_history/*.json`），欄位 id/title/last_message_time/message_count 對應。
- 取得會話：`GET /api/v2/chat-history/<chat_id>` → `rag_service.get_session`，回傳 history 陣列，前端逐條渲染。
- 標題編輯/刪除：`POST /api/v2/rename-chat`、`DELETE /api/v2/delete-chat/<id>` → `rag_service` 更新/刪除會話檔；參數對應。

### 2.3 發現的問題 / 潛在風險

- [阻斷性｜會造成問題] 送出訊息 payload 為 `{message, model, history, chatId}` (`static/js/chat_ui.js` submit handler)，後端 `api/chat_routes.py` 期望 `{query, chat_id, chat_title}`，缺少 `query` 會觸發 `INVALID_PARAMETER`，聊天無法運作。  
  - 處理結果：前端 payload 改為 `{query, chat_id, chat_title, model}`；後端同時接受 `message/chatId` 以維持相容。
- [回傳欄位不符｜會造成問題] 後端 `rag_service.query` 回傳 `answer`，前端採用 `data.reply || data.error` 取值 (`static/js/chat_ui.js`)，即使後端成功也會顯示「⚠️ 回應失敗」。  
  - 處理結果：前端改讀 `answer/reply`；後端補充 `reply` 鍵以相容。

### 2.4 API key / URL 相關

- 未發現缺漏。

---

## 3. 產生 Cluster 頁面（generate_cluster.html / static/js/cluster_trigger.js）

### 3.1 檔案用途與主要功能

- 觸發分群、顯示分群進度、列出已分群檔案/摘要、下載或開啟分群檔案。

### 3.2 功能 → 後端 → 資料庫 路徑檢查

- 分群觸發：預期 `POST /api/v2/cluster-excel` → `services/cluster_service.perform_clustering` → 讀 `excel_result_Unclustered/`、寫入 `excel_result_Clustered/`。
- 進度輪詢：`GET /api/v2/cluster-progress` → `cluster_service.get_cluster_progress`（回傳 progress 描述 + current/total 數值）。
- 清單載入：`GET /api/v2/clustered-files`、`GET /api/v2/summary-files` → `cluster_service.list_clustered_files/list_summary_files`。
- 檔案操作：`GET /api/v2/open-clustered?file_name=...`、`GET /api/v2/download-summary?file=...`。

### 3.3 發現的問題 / 潛在風險

- [阻斷性｜會造成問題] 觸發分群時 `fetch('/cluster-excel')` 未附帶 body（缺少 `json_file_name`/`method`），`api/cluster_routes.py` 內 `data = request.json` 為 `None`，會拋例外導致分群無法開始。  
  - 處理結果：前端送出 `{json_file_name:null, method:'rule-based'}`；後端放寬參數必填限制。
- [回傳欄位不符｜會造成問題] 進度輪詢使用 `data.progress` 作為數值並除以 `data.total` (`static/js/cluster_trigger.js`)，但後端數值在 `current`、`progress` 是文字描述，進度條顯示 `NaN%` 且永遠不會判定完成。  
  - 處理結果：前端改讀 `current/total`（回退至 progress 為數字時使用），百分比安全計算。
- [欄位名稱不符｜會造成問題] 檢查未分群檔案時前端讀 `data.exists`，後端回傳 `has_unclustered` (`api/cluster_routes.check_unclustered`)，按鈕會被誤判為「沒有未分群檔案」而禁用。  
  - 處理結果：前端改讀 `has_unclustered ?? exists`；後端新增 `exists` 相容鍵。
- [欄位名稱不符｜會造成問題] 開啟分群檔案請求 `open-clustered?file=...`，後端參數為 `file_name`；目前會回傳「未提供檔案名稱」。  
  - 處理結果：前端改用 `file_name`；後端同時接受 `file`。
- [資料缺漏｜會造成問題] `list_clustered_files` 回傳欄位未含 `rows`，但 UI 以 `f.rows` 顯示筆數，畫面會出現 `undefined`。  
  - 處理結果：後端回傳 rows（讀檔計算筆數，失敗則 None），前端並在缺值時顯示 `—`。

### 3.4 API key / URL 相關

- 未發現缺漏。

---

## 4. 歷史紀錄頁（history.html / static/js/history.js）

### 4.1 檔案用途與主要功能

- 分頁查看歷史分析紀錄、下載 JSON/Excel/原始檔、清除歷史、清空資料夾。

### 4.2 功能 → 後端 → 資料庫 路徑檢查

- 清單：`GET /api/v2/history-list?page=...&pageSize=...` → `history_service.list_history`（讀 `json_data/`），欄位 uid/file_name/created_at 對應。
- 下載：`GET /api/v2/get-json|download-excel|download-original?uid=...` → `history_service` 取檔。
- 清除歷史：`POST /api/v2/clear-history` → `history_service.clear_all_history` 刪除 json/xlsx/原始檔。
- 清空資料夾：`POST /api/v2/clear-folder` → `config_service.clear_folder`（直接對資料夾路徑操作）。

### 4.3 發現的問題 / 潛在風險

- [回傳欄位不符｜會造成問題] `clearHistoryBtn` 以 `result.success` 判斷，但後端回傳鍵為 `status` (`static/js/history.js` × `api/history_routes.py`)，成功會被誤報失敗且 UI 不更新。  
  - 處理結果：改讀 `status === 'success'`。
- [回傳欄位不符｜會造成問題] 清空資料夾也檢查 `data.success`，後端回傳 `status`，成功會走失敗分支；若資料夾不存在會得到 `FOLDER_NOT_FOUND`，目前未顯示原因。  
  - 處理結果：前端改讀 `status`，同時共用後端 `clear_folder` 新行為（不存在資料夾會自動建立並回傳成功）。

### 4.4 API key / URL 相關

- 未發現缺漏。

---

## 5. 手動輸入頁（manual_input.html / static/js/manual_input.js）

### 5.1 檔案用途與主要功能

- 維護語意比對句庫（新增/編輯/刪除），按分類顯示。

### 5.2 功能 → 後端 → 資料庫 路徑檢查

- 讀取：`GET /api/v2/sentence-db?category=...` → `config_service.get_all_sentences`（檔案式存取）。
- 新增/刪除/編輯：`POST|DELETE|PUT /api/v2/sentence-db` → `config_service.add_sentence/delete_sentence/update_sentence`；欄位 category/sentence/old_sentence/new_sentence 對應。

### 5.3 發現的問題 / 潛在風險

- 目前未發現阻斷問題；若後端拋 ValidationError，UI 以 alert 呈現錯誤。

### 5.4 API key / URL 相關

- 未發現缺漏。

---

## 6. 結果頁（result.html / static/js/result.js）

### 6.1 檔案用途與主要功能

- 分批載入分析結果卡片、時間篩選、分數與圖表顯示。

### 6.2 功能 → 後端 → 資料庫 路徑檢查

- 取得結果：`GET /api/v2/get-results?start=...&limit=...&days=...` → `history_service.get_results_with_details`（讀 `json_data/`），字段 id/configurationItem/severityScore/frequencyScore/impactScore/riskLevel/weights 符合前端使用。
- 權重載入：首次同 API 取 weights，再分批載入更多資料；流程對應。

### 6.3 發現的問題 / 潛在風險

- 清除篩選時引用 `filterInput` (`static/js/result.js`)，頁面無此元素但因 null 檢查不致報錯，代表目前無文字搜尋功能（不會造成錯誤，僅缺功能）。  
  - 處理結果：維持現狀（非阻斷，未列為優先修正）。
- 其餘欄位對應正常，未見阻斷問題。

### 6.4 API key / URL 相關

- 未發現缺漏。

---

## 7. 系統設定頁（system_settings.html / static/js/system_settings.js）

### 7.1 檔案用途與主要功能

- 管理總體/細項權重、風險語句、AI 模型映射與 Prompt 模板。

### 7.2 功能 → 後端 → 資料庫 路徑檢查

- 總體權重：`GET/POST /api/v2/config/weight` → `config_service.get_weight_config/update_weight_config`（需總和=1）。
- 細項權重：`GET/POST /api/v2/config/risk-weights` → `config_service.get_risk_weights/update_risk_weights`。
- 風險語句：`GET/POST/PUT/DELETE /api/v2/config/risk-sentences` → `config_service` 對應 CRUD。
- 模型映射/Prompt：`GET/POST /api/v2/gpt-prompt-map`、`GET/POST/DELETE /api/v2/gpt-prompts` → `config_service`（欄位 prompt_name/prompt_text/prompt_map 對應）。

### 7.3 發現的問題 / 潛在風險

- 目前未發現欄位對應錯誤；若後端寫檔失敗僅以 toast 呈現，缺少更詳細錯誤提示。

### 7.4 API key / URL 相關

- 未發現缺漏。
