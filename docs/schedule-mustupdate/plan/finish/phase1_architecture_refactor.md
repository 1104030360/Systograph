# Phase 1: 架構重構

**時程**: 2-3 週
**優先級**: 必須執行
**目標**: 建立分層架構，不破壞現有功能

---

## 問題定義

**當前系統問題**:
1. Analysis.py 過於龐大 (2615 行)，職責不清
2. 業務邏輯散落各處，修改風險高
3. 無依賴注入機制，測試困難
4. 錯誤處理格式不一致
5. 資料存取邏輯重複

**預期成果**:
- Analysis.py 從 2615 行降至 <500 行
- 建立清晰的 API → Services → Repositories 三層架構
- 統一錯誤處理格式
- 為 Phase 2 測試奠定基礎

---

## Week 1: 建立骨架

### 目標
建立基礎目錄結構與核心框架

### 任務清單

#### 1.1 建立目錄結構
- [ ] 創建 `api/` 目錄 (Blueprints 層)
- [ ] 創建 `services/` 目錄 (業務邏輯層)
- [ ] 創建 `repositories/` 目錄 (資料存取層)
- [ ] 創建 `utils/` 目錄 (工具函數)
- [ ] 創建 `core/` 目錄 (核心基礎設施)

**檔案結構**:
```
/
├── api/
│   ├── __init__.py
│   ├── upload_routes.py
│   ├── chat_routes.py
│   ├── cluster_routes.py
│   ├── config_routes.py
│   └── history_routes.py
├── services/
│   ├── __init__.py
│   ├── ticket_service.py
│   ├── rag_service.py
│   ├── risk_service.py
│   ├── cluster_service.py
│   └── kb_service.py
├── repositories/
│   ├── __init__.py
│   ├── ticket_repo.py
│   ├── config_repo.py
│   ├── chat_repo.py
│   ├── faiss_repo.py
│   ├── category_repo.py
│   └── sentence_db_repo.py
├── core/
│   ├── __init__.py
│   ├── error_handler.py
│   ├── config_loader.py
│   ├── database.py
│   └── logger.py
└── utils/
    ├── __init__.py
    ├── ai_utils.py (整合現有 gpt_utils.py)
    ├── excel_utils.py
    ├── vector_utils.py
    └── validation_utils.py
```

#### 1.2 實作 5 個 Blueprints

**1.2.1 upload_routes.py**
- [ ] 創建 Blueprint: `upload_bp`
- [ ] 遷移路由: `/upload`, `/preview`, `/api/upload/analyze`
- [ ] 整合 TicketService 呼叫
- [ ] 參數驗證與錯誤處理

**1.2.2 chat_routes.py**
- [ ] 創建 Blueprint: `chat_bp`
- [ ] 遷移路由: `/chat`, `/api/chat/query`, `/api/chat/sessions/*`
- [ ] 整合 RAGService 呼叫
- [ ] 會話管理邏輯

**1.2.3 cluster_routes.py**
- [ ] 創建 Blueprint: `cluster_bp`
- [ ] 遷移路由: `/cluster`, `/api/cluster/analyze`, `/cluster-results`
- [ ] 整合 ClusterService 呼叫

**1.2.4 config_routes.py**
- [ ] 創建 Blueprint: `config_bp`
- [ ] 遷移路由: `/config`, `/api/config/weight`, `/api/config/prompt`
- [ ] 配置 CRUD 操作

**1.2.5 history_routes.py**
- [ ] 創建 Blueprint: `history_bp`
- [ ] 遷移路由: `/history`, `/results/*`, `/delete-result/*`
- [ ] 歷史記錄查詢與刪除

#### 1.3 實作統一錯誤處理器

**core/error_handler.py**
- [ ] 定義統一錯誤回應格式:
  ```python
  {
      "status": "error",
      "code": "FILE_TOO_LARGE",
      "message": "檔案大小超過 10MB",
      "details": {...}  # 可選
  }
  ```
- [ ] 實作全域錯誤處理器:
  - `@app.errorhandler(400)` - 客戶端錯誤
  - `@app.errorhandler(500)` - 伺服器錯誤
  - 自定義例外類別 (ValidationError, AIServiceError 等)
- [ ] 錯誤碼定義表 (參考 architecture_design.md 4.3 節)

#### 1.4 實作 ConfigLoader

**core/config_loader.py**
- [ ] 集中載入所有配置:
  - 環境變數 (.env)
  - JSON 配置檔 (權重、提示詞等)
  - 檔案路徑配置
- [ ] 配置驗證邏輯:
  - 必要配置檢查
  - 權重總和驗證
  - 路徑存在性檢查
- [ ] 配置快取機制 (避免重複讀取)

### 驗收標準

```bash
# 1. 目錄結構檢查
ls -R api/ services/ repositories/ utils/ core/

# 2. Blueprints 註冊檢查
python -c "from Analysis import app; print(app.blueprints.keys())"
# 應輸出: dict_keys(['upload_bp', 'chat_bp', 'cluster_bp', 'config_bp', 'history_bp'])

# 3. 錯誤處理器測試
curl -X POST http://127.0.0.1:5000/upload -F "file=@large_file.xlsx"
# 應回傳統一格式: {"status": "error", "code": "...", "message": "..."}

# 4. 配置載入測試
python -c "from core.config_loader import load_config; print(load_config())"
# 應成功載入所有配置
```

---

## Week 2: 抽取業務邏輯

### 目標
將 Analysis.py 中的業務邏輯抽取到 Services 層

### 任務清單

#### 2.1 實作 TicketService

**services/ticket_service.py**
- [ ] 實作 `process_uploaded_file(file_path)`:
  - Excel 讀取 (欄位優先順序處理)
  - 重複工單檢查 (≥80% 判定為重複)
  - 問題摘要提取 (呼叫 AI)
  - 解決方案提取 (呼叫 AI + 可操作性驗證)
  - 風險評分 (呼叫 RiskService)
  - 儲存到 SQLite (呼叫 TicketRepository)
- [ ] 實作 `validate_uploaded_file(file)`:
  - 檔案格式檢查 (.xlsx)
  - 檔案大小檢查 (<10MB)
  - Excel 結構驗證 (必要欄位)
- [ ] 實作 `get_upload_progress(session_id)`:
  - 進度百分比
  - 當前處理步驟
- [ ] 依賴注入: TicketRepository, RiskService, AIUtils

#### 2.2 實作 RiskService

**services/risk_service.py**
- [ ] 實作 `calculate_risk_score(ticket)`:
  - 載入權重配置 (ConfigRepository)
  - 計算 severityScore:
    - 高風險關鍵字檢測 (火災、電力、安全)
    - 語意相似度計算 (閾值 0.7)
  - 計算 frequencyScore:
    - 重複率計算
    - 多使用者影響判斷
  - impactScore = severityScore × w1 + frequencyScore × w2
- [ ] 實作 `determine_risk_level(scores)`:
  - 動態聚類條件判斷:
    - 資料量 ≥4 AND 範圍 >5.0 AND 標準差 >3.0 → KMeans(K=4)
    - 否則 → 固定門檻 [70,100]高 [50,70)中 [30,50)低 [0,30)忽略
- [ ] 整合 SmartScoring.py 邏輯
- [ ] 依賴注入: ConfigRepository, VectorUtils

#### 2.3 實作 RAGService

**services/rag_service.py**
- [ ] 實作 `query(user_query, session_id)`:
  - 載入對話歷史 (最多 10 輪) - ChatRepository
  - 呼叫 gptChat.py 多代理系統
  - 儲存對話記錄
  - 格式化回應 (包含參考來源)
- [ ] 實作 `create_session(title)`:
  - 標題驗證 (≤100 字，禁止特殊字元)
  - 產生 session_id (UUID)
  - 初始化會話檔案
- [ ] 實作 `list_sessions(page, page_size)`:
  - 分頁查詢 (每頁 20 筆)
  - 按標題/日期篩選
- [ ] 依賴注入: ChatOrchestrator (gptChat.py), ChatRepository

#### 2.4 實作 ClusterService

**services/cluster_service.py**
- [ ] 實作 `perform_clustering(method)`:
  - 載入工單資料 (TicketRepository)
  - Rule-based 聚類 (configurationItem + aiCategory)
  - AI 生成群集名稱:
    - 限制 30 字 + 省略號
    - 呼叫 LLM 摘要
  - 生成 Excel 報表:
    - 2 色交替上色
    - 每批次不同顏色
- [ ] 實作 `get_cluster_results(cluster_id)`:
  - 查詢群集詳情
  - 統計資訊 (工單數、平均風險分數)
- [ ] 依賴注入: TicketRepository, AIUtils, VectorUtils

#### 2.5 實作 KBService

**services/kb_service.py**
- [ ] 實作 `sync_knowledge_base()`:
  - 檢查 `kb_building.lock` 檔案鎖
  - 備份 SQLite (僅保留最近 1 個)
  - Excel → SQLite:
    - 關閉 Excel (COM 自動化)
    - 增量更新 (以 analysisTime 判斷)
  - SQLite → FAISS:
    - 全量重建 (384 維)
    - 產生 kb_metadata.json
  - 清理鎖檔案
- [ ] 實作 `check_kb_status()`:
  - 鎖檔案檢查
  - 索引更新時間
  - 記錄數統計
- [ ] 整合 build_kb.py 邏輯
- [ ] 依賴注入: TicketRepository, FAISSRepository

### 驗收標準

```bash
# 1. Services 獨立測試
python -c "
from services.ticket_service import TicketService
service = TicketService(...)
result = service.validate_uploaded_file('test.xlsx')
print(result)
"

# 2. 業務邏輯完整性測試 (手動)
python run_analysis.py
# 上傳檔案 → 檢查是否正常分析

# 3. 程式碼行數檢查
wc -l services/*.py
# 每個 Service 應 <300 行
```

---

## Week 3: Repositories 層與依賴注入

### 目標
實作資料存取層，完成依賴注入，重構 Analysis.py

### 任務清單

#### 3.1 實作 6 個 Repositories

**3.1.1 repositories/ticket_repo.py**
- [ ] `save_ticket(ticket)` - 插入或更新工單
- [ ] `get_tickets_by_time_range(start, end)` - 按時間查詢
- [ ] `get_tickets_by_ids(ids)` - 按 ID 批次查詢
- [ ] `get_all_tickets()` - 查詢所有工單
- [ ] `delete_ticket(ticket_id)` - 刪除工單
- [ ] SQLite 連接管理 (使用 core/database.py)

**3.1.2 repositories/config_repo.py**
- [ ] `get_weight_config()` - 讀取權重配置 (JSON)
- [ ] `save_weight_config(config)` - 儲存權重 (驗證總和=1.0)
- [ ] `get_prompt_config(prompt_type)` - 讀取提示詞
- [ ] `save_prompt_config(prompt_type, content)` - 儲存提示詞
- [ ] JSON 檔案讀寫處理

**3.1.3 repositories/chat_repo.py**
- [ ] `save_session(session)` - 儲存對話會話
- [ ] `load_session(session_id)` - 載入對話歷史 (最多 10 輪)
- [ ] `list_sessions(page, page_size)` - 分頁列表
- [ ] `delete_session(session_id)` - 刪除會話
- [ ] JSON 檔案操作 (chat_history/ 目錄)

**3.1.4 repositories/faiss_repo.py**
- [ ] `build_index(texts, metadata)` - 建構 FAISS 索引
  - 使用 all-MiniLM-L6-v2 (384 維)
  - IndexFlatL2 + IndexIDMap
  - SHA-256 hash 映射
- [ ] `search(query, top_k)` - 向量檢索
- [ ] `load_index()` - 載入索引
- [ ] `save_index()` - 儲存索引

**3.1.5 repositories/category_repo.py**
- [ ] `get_all_categories()` - 讀取類別對照表 (JSON)
- [ ] `update_category_mapping(mapping)` - 更新類別映射
- [ ] JSON 檔案操作

**3.1.6 repositories/sentence_db_repo.py**
- [ ] `get_high_risk_sentences()` - 讀取高風險句子庫
- [ ] `add_high_risk_sentence(sentence)` - 新增高風險句子
- [ ] SQLite 操作

#### 3.2 實作依賴注入

**Analysis.py 初始化區塊**
- [ ] 實作依賴容器 (簡單版 DI):
  ```python
  # 初始化 Repositories
  ticket_repo = TicketRepository(db_connection)
  config_repo = ConfigRepository()
  chat_repo = ChatRepository()
  faiss_repo = FAISSRepository()
  category_repo = CategoryRepository()
  sentence_db_repo = SentenceDBRepository(db_connection)

  # 初始化 Services
  risk_service = RiskService(config_repo, vector_utils)
  ticket_service = TicketService(ticket_repo, ai_utils, risk_service)
  rag_service = RAGService(chat_orchestrator, chat_repo)
  cluster_service = ClusterService(ticket_repo, ai_utils, vector_utils)
  kb_service = KBService(ticket_repo, faiss_repo)

  # 註冊到 Blueprint
  upload_bp.ticket_service = ticket_service
  chat_bp.rag_service = rag_service
  # ...
  ```
- [ ] 確保所有依賴都通過建構函數注入
- [ ] 移除全域變數 (改為注入)

#### 3.3 重構 Analysis.py

**目標: 從 2615 行降至 <500 行**

- [ ] 移除所有路由定義 (已遷移至 Blueprints)
- [ ] 移除業務邏輯 (已遷移至 Services)
- [ ] 保留內容:
  - Flask app 初始化
  - 依賴注入容器
  - Blueprint 註冊
  - 錯誤處理器註冊
  - 靜態頁面路由 (`/`, `/index`)
  - 啟動邏輯 (`app.run()`)

**重構後結構**:
```python
# Analysis.py (預期 <500 行)
from flask import Flask, render_template
from core.config_loader import load_config
from core.error_handler import register_error_handlers
from core.database import init_database
# ... 其他 imports

def create_app():
    app = Flask(__name__)

    # 1. 載入配置
    config = load_config()
    app.config.update(config)

    # 2. 初始化資料庫
    db = init_database()

    # 3. 初始化依賴 (DI Container)
    repositories = init_repositories(db)
    services = init_services(repositories)

    # 4. 註冊 Blueprints
    register_blueprints(app, services)

    # 5. 註冊錯誤處理器
    register_error_handlers(app)

    # 6. 靜態頁面路由
    @app.route('/')
    def index():
        return render_template('index.html')

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
```

#### 3.4 驗證所有現有功能

**完整功能測試流程**:
1. [ ] 啟動應用: `python run_analysis.py`
2. [ ] 測試工單上傳:
   - 上傳 Excel 檔案
   - 驗證分析結果
   - 檢查 SQLite 儲存
3. [ ] 測試 RAG 查詢:
   - 建立新會話
   - 提交查詢
   - 驗證回應與參考來源
4. [ ] 測試聚類分析:
   - 執行聚類
   - 檢查 Excel 輸出
   - 驗證群集名稱
5. [ ] 測試配置管理:
   - 讀取權重配置
   - 修改並儲存
   - 驗證雙重驗證
6. [ ] 測試知識庫同步:
   - 執行同步
   - 驗證 FAISS 索引
   - 檢查備份檔案
7. [ ] 測試歷史記錄:
   - 查詢歷史記錄
   - 刪除記錄
   - 驗證刪除確認 (若已實作)

### 驗收標準

```bash
# 1. 程式碼行數檢查
wc -l Analysis.py
# 應 <500 行

# 2. 依賴關係檢查
python -c "
from Analysis import app
# 檢查所有 Services 都已注入
print(app.extensions)
"

# 3. 功能完整性測試 (手動)
# 依照上述測試流程全部執行一遍

# 4. 錯誤處理測試
curl -X POST http://127.0.0.1:5000/upload -F "file=@invalid.txt"
# 應回傳統一格式錯誤訊息

# 5. 效能回歸測試
# 上傳 100 筆工單，計時應與重構前相近 (允許 ±10%)
```

---

## 交付物

### 必須完成

1. ✅ **分層架構**
   - api/ (5 個 Blueprints)
   - services/ (5 個 Services)
   - repositories/ (6 個 Repositories)
   - core/ (4 個核心模組)
   - utils/ (4 個工具模組)

2. ✅ **Analysis.py <500 行**
   - 僅保留初始化與註冊邏輯
   - 所有業務邏輯已遷移

3. ✅ **統一錯誤處理**
   - 全域錯誤處理器
   - 統一回應格式
   - 錯誤碼對照表

4. ✅ **功能驗證通過**
   - 所有現有功能正常運作
   - 無回歸問題

### 可選完成

- ⚠️ 依賴注入容器 (簡單版已足夠)
- ⚠️ 配置檔案集中管理 (core/config_loader.py)

---

## 風險與緩解

### 風險 1: 重構過程中破壞現有功能
**緩解**:
- 採用**增量遷移策略**，每遷移一個模組就測試
- 保留 `Analysis_backup.py` 作為備份
- 使用 Git 頻繁提交，確保可回滾

### 風險 2: Analysis.py 無法降至 <500 行
**緩解**:
- 若仍超過 500 行，檢查是否有未抽取的業務邏輯
- 將初始化邏輯進一步抽取到 `core/app_factory.py`

### 風險 3: 依賴注入過於複雜
**緩解**:
- 使用**簡單的手動 DI**，不引入 Flask-Injector 等框架
- 僅在 Analysis.py 初始化時注入，避免過度設計

### 風險 4: 時程延誤
**緩解**:
- Week 1-2 若延誤，可將 Week 3 的 Repository 層簡化為優先實作核心 3 個 (ticket, config, chat)
- 其餘 3 個 (faiss, category, sentence_db) 可延後至 Phase 2

---

## 下一階段

完成 Phase 1 後，進入 **Phase 2: 測試與優化**
- 建立 pytest 測試框架
- 為 Services 層撰寫單元測試
- 達成 70% 測試覆蓋率
