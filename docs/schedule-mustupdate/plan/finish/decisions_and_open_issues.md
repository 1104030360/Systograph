# 開放問題與決策點

**文件版本**: v1.0
**建立日期**: 2025-11-04
**狀態**: 待決策

本文件列出架構重構過程中的開放問題與關鍵決策點，需要與團隊討論並達成共識。

---

## 1. 技術債處理優先順序

### 問題描述

當前系統存在多項技術債，需確定處理優先順序：

| 技術債 | 影響 | 優先級 | 建議處理時機 |
|--------|------|--------|-------------|
| Analysis.py 過於龐大 (2615 行) | 維護困難，職責不清 | ⭐⭐⭐ 高 | Phase 1 |
| 無自動化測試 | 回歸測試成本高，重構風險大 | ⭐⭐⭐ 高 | Phase 2 |
| 錯誤訊息不統一 | 除錯困難，使用者體驗差 | ⭐⭐ 中 | Phase 1 |
| win32com 依賴 (僅支援 Windows) | 無法跨平台部署 | ⭐ 低 | Phase 3 |
| 並發上傳無佇列機制 | 多使用者同時上傳可能衝突 | ⭐ 低 | Phase 3 |

### 決策建議

**建議**: Phase 1-2 專注於高優先級技術債，低優先級延後至 Phase 3

**理由**:
1. Analysis.py 重構是基礎，必須先完成才能進行測試
2. 測試框架建立後，才能安全進行其他重構
3. 跨平台支援與任務佇列當前需求不急迫 (使用者 <10 人，僅部署於 Windows)

### 待決策事項

- [ ] **確認優先順序排序** (與團隊討論)
- [ ] **確認 Phase 1-2 時程是否合理** (2-3 週 + 2-3 週)
- [ ] **確認低優先級技術債是否可延後** (Phase 3 或更晚)

---

## 2. 跨平台支援必要性

### 問題描述

當前系統依賴 win32com (Windows 限定)，若要支援 macOS/Linux，需遷移至 openpyxl。

### 方案比較

| 方案 | 優點 | 缺點 | 適用場景 |
|------|------|------|---------|
| **保持 win32com** | 功能完整，無需重構 | 僅支援 Windows，需安裝 Excel | 當前環境 (Windows Server) |
| **遷移至 openpyxl** | 跨平台，無需 Excel，效能快 5-10 倍 | 需重寫 Excel 處理邏輯，功能較少 | 未來跨平台需求 |

### 決策建議

**建議**: **Phase 3 評估後再決定**

**理由**:
1. 當前系統僅部署於 Windows Server，短期內無跨平台需求
2. openpyxl 遷移成本中等 (需重寫 Excel 處理邏輯)
3. 效能提升明顯 (5-10 倍)，但需實測驗證

**實測計畫** (Phase 2 Week 4):
```python
# tests/performance/test_excel_libraries.py
def test_compare_excel_libraries():
    # 測試 win32com vs openpyxl 效能
    # 若 openpyxl 快 ≥5 倍，則建議遷移
```

### 待決策事項

- [ ] **確認是否有跨平台需求** (與 IT 團隊確認)
- [ ] **確認是否有 macOS/Linux 開發環境** (影響測試成本)
- [ ] **若效能提升 <3 倍，是否仍要遷移** (投入產出比)

---

## 3. 任務佇列選型

### 問題描述

當前系統無任務佇列機制，若多使用者同時上傳檔案，可能發生衝突。

### 方案比較

| 方案 | 優點 | 缺點 | 適用場景 |
|------|------|------|---------|
| **Celery** | 功能強大，支援分散式 | 需 Redis/RabbitMQ，複雜度高 | >20 並發使用者 |
| **RQ (Redis Queue)** | 簡單易用，Python 原生 | 需 Redis | 10-20 並發使用者 |
| **內建 threading** | 無額外依賴，輕量 | 無持久化，重啟丟失 | <10 並發使用者 |
| **不實作** | 無開發成本 | 多使用者並發可能衝突 | 當前狀態 (單一使用者) |

### 決策建議

**建議**: **Phase 3 使用 RQ (視需求決定)**

**理由**:
1. 當前使用者 <10 人，內建 threading 足夠
2. 若未來使用者增至 10-20 人，遷移至 RQ
3. RQ 實作成本低，遷移容易

**實作範例** (Phase 3):
```python
# core/queue.py
from redis import Redis
from rq import Queue

redis_conn = Redis(host='localhost', port=6379)
task_queue = Queue('ticket_analysis', connection=redis_conn)

# 將任務加入佇列
job = task_queue.enqueue(
    'services.ticket_service.process_uploaded_file',
    file_path=f"uploads/{file_id}.xlsx",
    timeout=600
)
```

### 待決策事項

- [ ] **確認當前使用者數量** (是否 <10 人)
- [ ] **確認未來使用者增長預期** (1 年內是否會超過 10 人)
- [ ] **確認是否有 Redis 環境** (影響 RQ 可行性)
- [ ] **若當前 <10 人，是否延後實作** (Phase 4 或更晚)

---

## 4. 測試覆蓋率目標

### 問題描述

需確定測試覆蓋率目標，平衡測試成本與品質保證。

### 業界標準

| 覆蓋率 | 評價 | 投入產出比 |
|-------|------|-----------|
| 60% | 基本 | 中 |
| 70% | 良好 | 高 |
| 80% | 優秀 | 中 |
| 90%+ | 過度追求 | 低 |

### 建議覆蓋率分配

| 模組 | 目標覆蓋率 | 理由 |
|------|-----------|------|
| **Services 層** | 80% | 核心業務邏輯，必須充分測試 |
| **Agents 層** | 80% | RAG 核心，錯誤影響大 |
| **Repositories 層** | 70% | CRUD 邏輯較簡單 |
| **Utilities 層** | 70% | 工具函數，邊界條件多 |
| **API 層** | 60% | 薄層，主要測試整合 |
| **總覆蓋率** | 70% | 平衡測試成本與品質 |

### 決策建議

**建議**: **總覆蓋率 70%** (Phase 2 目標)

**理由**:
1. 70% 是業界良好標準，投入產出比高
2. Services 層與 Agents 層是核心，必須達 80%+
3. API 層是薄層，60% 即可 (主要測試整合)

### 待決策事項

- [ ] **確認團隊測試撰寫經驗** (影響時程評估)
- [ ] **確認是否接受 70% 目標** (與管理層討論)
- [ ] **若時程不足，最低覆蓋率目標** (60%?)

---

## 5. 效能瓶頸識別

### 問題描述

需識別系統效能瓶頸，優化關鍵流程。

### 預期瓶頸 (需 Phase 2 實測驗證)

| 瓶頸 | 當前效能 | 目標效能 | 優化方向 |
|------|---------|---------|---------|
| **LLM 呼叫** | 1-3 秒/次 | <1 秒 | 增加語意快取命中率，批次合併 |
| **Embedding 計算** | 1000 筆 ≈ 10 秒 | <5 秒 | 批次處理 (batch_size=32)，GPU 加速 (可選) |
| **Excel 讀寫** | 100 筆 ≈ 50 秒 (win32com) | <10 秒 | 遷移至 openpyxl (快 5-10 倍) |
| **FAISS 搜尋** | 1000 筆 <100ms | 保持 | 已達標 |

### 決策建議

**建議**: **Phase 2 Week 4 實測驗證**

**實測計畫**:
1. 使用 cProfile 分析效能瓶頸
2. 識別 Top 3 最耗時函數
3. 評估優化成本與效益
4. 優先優化高投資報酬率項目 (LLM 快取、Excel 讀寫)

**優化優先順序**:
1. **P0 (必須)**: LLM 快取優化 (調整閾值 0.92 → 0.90)
2. **P1 (建議)**: Excel 讀寫優化 (遷移至 openpyxl)
3. **P2 (可選)**: Embedding 批次處理 (batch_size=32)
4. **P3 (延後)**: GPU 加速 (需 CUDA 環境，成本高)

### 待決策事項

- [ ] **確認當前效能是否可接受** (與使用者確認)
- [ ] **確認效能目標是否合理** (是否需要更高效能)
- [ ] **確認是否有 GPU 環境** (影響 GPU 加速可行性)

---

## 6. 依賴注入方案

### 問題描述

需選擇依賴注入 (DI) 方案，解耦模組依賴。

### 方案比較

| 方案 | 優點 | 缺點 | 適用場景 |
|------|------|------|---------|
| **手動 DI** | 簡單，無額外依賴 | 初始化程式碼較長 | 中小型應用 (當前系統) |
| **Flask-Injector** | 自動注入，程式碼簡潔 | 增加依賴，學習曲線 | 大型應用 (>20 個 Service) |
| **Python-Dependency-Injector** | 功能強大，支援多種注入方式 | 複雜度高 | 複雜應用 (微服務) |

### 決策建議

**建議**: **手動 DI** (Phase 1)

**理由**:
1. 當前系統僅 5 個 Service，手動 DI 足夠
2. 避免過度工程，保持簡單
3. 若未來擴展至 >20 個 Service，再考慮 Flask-Injector

**實作範例** (Analysis.py):
```python
def create_app():
    # 1. 初始化 Repositories
    ticket_repo = TicketRepository(db_connection)
    config_repo = ConfigRepository()
    chat_repo = ChatRepository()
    faiss_repo = FAISSRepository()

    # 2. 初始化 Services
    risk_service = RiskService(config_repo, vector_utils)
    ticket_service = TicketService(ticket_repo, ai_utils, risk_service)
    rag_service = RAGService(chat_orchestrator, chat_repo)
    cluster_service = ClusterService(ticket_repo, ai_utils, vector_utils)
    kb_service = KBService(ticket_repo, faiss_repo)

    # 3. 註冊到 Blueprint
    upload_bp.ticket_service = ticket_service
    chat_bp.rag_service = rag_service
    # ...

    return app
```

### 待決策事項

- [ ] **確認團隊對 DI 的熟悉度** (影響實作難度)
- [ ] **確認是否接受手動 DI** (初始化程式碼較長)
- [ ] **若未來擴展，何時考慮 Flask-Injector** (>20 個 Service?)

---

## 6.1 Repository 抽象層實作決策 (2025-11-15 已決策)

### 問題描述

Phase 1 計畫中提出實作完整的 Repository 層 (TicketRepository, ChatRepository, FAISSRepository 等)，用於抽象化資料存取邏輯。當前 `core/dependencies.py` 中服務初始化仍使用 `ticket_repo=None`, `ai_utils=None` 佔位。

### 方案比較

| 方案 | 優點 | 缺點 | 複雜度 |
|------|------|------|-------|
| **完整實作 Repository 層** | 高度解耦，測試隔離度高 | 增加抽象層，程式碼量+30% | 高 |
| **Services 直接呼叫 Utilities** | 簡單直接，易於理解 | 測試時需 mock utilities | 低 |
| **混合方案** | ConfigRepository 已實作，保持現狀 | 架構不一致 | 中 |

### 最終決策

**決策**: **不實作額外 Repository 層，保持 Services 直接呼叫 Utilities** ✅

**決策日期**: 2025-11-15
**決策者**: Development Team (基於 Linus Torvalds 開發哲學)

**理由**:

1. **Simple > Complex** (Linus 準則)
   - 當前 Services 層已提供足夠的業務邏輯抽象
   - 直接呼叫 `gpt_utils`, `core.database` 更簡潔明瞭
   - Repository 層會增加 ~30% 程式碼量但無實質益處

2. **Fix Real Problems** (Linus 準則)
   - 系統已有 997 tests, 98.6% 通過率
   - 測試可直接 mock `gpt_utils` 等模組，無測試障礙
   - 未發現因缺少 Repository 層導致的實際問題

3. **Abstraction for abstraction's sake is bad** (Linus 準則)
   - ConfigRepository 存在是因為需要檔案持久化邏輯
   - TicketRepository/ChatRepository 只會是 database.py 的薄包裝
   - FAISSRepository 只會是 kb_loader.py 的薄包裝
   - 這些抽象不解決實際問題

4. **Never Break Userspace** (Linus 準則)
   - 當前架構運作良好，功能完整
   - 重構為 Repository 模式會引入風險
   - 測試需全部改寫，投入產出比低

### 實作細節

**保留現狀**:
```python
# core/dependencies.py
ticket_service = TicketService(
    ticket_repo=None,  # ✅ Intentionally None - uses gpt_utils directly
    ai_utils=None,     # ✅ Intentionally None - uses gpt_utils directly
    risk_service=risk_service
)
```

**Services 直接呼叫 Utilities**:
```python
# services/ticket_service.py
from gpt_utils import extract_resolution_suggestion, extract_problem_with_custom_prompt
from core.database import get_connection

# 直接使用，無需 Repository 包裝
async def _analyze_row_async(self, row):
    suggestion = await extract_resolution_suggestion(row['text'])
    # ...
```

### 緩解測試問題

雖不實作 Repository，但測試仍可輕鬆進行:

```python
# tests/unit/services/test_ticket_service.py
@patch('services.ticket_service.extract_resolution_suggestion')
async def test_analyze_row(mock_extract):
    mock_extract.return_value = "建議重啟"
    result = await ticket_service._analyze_row_async(row)
    assert "建議重啟" in result
```

### 待決策事項

- [x] **確認團隊是否接受此決策** (已接受，2025-11-15)
- [x] **文檔化決策理由** (已完成，本文件)
- [ ] **未來若需要，何時重新評估** (當 Services >20 個時)

---

## 6.2 Blueprint 瘦身決策 (2025-11-15 已決策)

### 問題描述

當前 `api/config_routes.py` (378 lines) 與 `api/cluster_routes.py` (278 lines) 含有部分厚邏輯（如檔案操作、send_file、Power Automate 呼叫），理論上應移至 services/utils 層，讓 routes 僅處理 HTTP request/response。

### 當前狀態分析

**已完成的分離**:
- ✅ 所有業務邏輯已移至 Services 層
- ✅ Routes 主要職責：request 驗證、service 調用、response 格式化
- ✅ 無複雜演算法或業務規則在 routes 中

**仍在 Routes 的邏輯**:
- 檔案下載 (`send_file()`)
- 簡單的檔案讀寫（配置 JSON）
- HTTP response 構建
- Power Automate webhook 呼叫（簡單 HTTP POST）

### 最終決策

**決策**: **保持當前狀態，不強求 routes <30 行目標** ✅

**決策日期**: 2025-11-15
**決策者**: Development Team (基於 Linus Torvalds 開發哲學)

**理由**:

1. **Good Taste - Knowing When to Stop** (Linus 準則)
   - 當前 routes 已清晰分離關注點
   - 業務邏輯在 Services，HTTP 處理在 Routes
   - 進一步拆分會降低可讀性

2. **Simple > Complex** (Linus 準則)
   - `send_file()` 屬於 Flask 框架層，放 routes 合理
   - 簡單檔案操作（2-3 行）無需包裝成 service 方法
   - 過度抽象會增加間接層級

3. **Fix Real Problems** (Linus 準則)
   - 未發現因 routes 過厚導致的實際問題
   - 測試覆蓋率 90%+，routes 可測試性良好
   - 維護成本可接受

### 範例：合理的 "厚邏輯"

```python
# api/history_routes.py - send_file 屬於 Flask 層，無需移至 service
@history_bp.route('/download/<path:filename>', methods=['GET'])
def download_result(filename):
    """下載分析結果檔案"""
    try:
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if not os.path.exists(file_path):
            return jsonify({"error": "檔案不存在"}), 404
        return send_file(file_path, as_attachment=True)  # ✅ 合理放在 route
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

### 緩解措施

雖不強求瘦身，但保持以下原則:
1. ✅ **新代碼優先**: 新增 routes 應優先呼叫 services
2. ✅ **明顯過長處理**: 若單一 route >100 行，則重構
3. ✅ **複雜邏輯抽離**: 若出現複雜演算法，立即移至 service

### 待決策事項

- [x] **確認團隊是否接受當前狀態** (已接受，2025-11-15)
- [x] **文檔化決策理由** (已完成，本文件)
- [ ] **未來若單一 route >100 行，觸發重構** (code review 規則)

---

## 6.3 Logging 統一決策 (2025-11-15 已決策)

### 問題描述

當前核心模組（如 `gptChat.py`）大量使用 `print()` 而非 `core.logger`，不利於生產環境監控與日誌管理。

### 當前狀態分析

**print() 使用情況**:
- gptChat.py: ~50 處 print()
- gpt_utils.py: ~30 處 print()
- SmartScoring.py: ~20 處 print()
- 總計: ~700+ lines 的 print() 語句

**core.logger 已實作**:
- ✅ core/logger.py 已完成 (165 lines)
- ✅ 提供 log_info(), log_error(), log_warning()
- ✅ 支援檔案輸出與控制台輸出

### 最終決策

**決策**: **漸進式改進 - 新代碼用 logger，舊代碼保持 print()** ✅

**決策日期**: 2025-11-15
**決策者**: Development Team (基於 Linus Torvalds 開發哲學)

**理由**:

1. **Never Break Userspace** (Linus 準則)
   - 當前系統已在生產環境穩定運行
   - 大規模改動 print() → logger 風險高
   - 可能引入 logging 配置問題

2. **Simple > Complex** (Linus 準則)
   - print() 對開發者友善，易於除錯
   - 小型應用（<10 使用者）print() 已足夠
   - logger 增加配置複雜度

3. **Fix Real Problems** (Linus 準則)
   - 未發現因使用 print() 導致的實際問題
   - 生產環境可透過 stdout 捕獲 print() 輸出
   - 當前監控需求不高

### 實作策略

**階段 1: 新代碼優先** (當前階段)
```python
# 新增功能使用 logger
from core.logger import log_info, log_error

def new_feature():
    log_info("Processing new feature...")
    # ...
```

**階段 2: 關鍵路徑遷移** (未來，視需求)
- 僅遷移錯誤處理相關的 print()
- 保留 debug 用的 print()

**階段 3: 全面遷移** (視需求，可能不執行)
- 若未來需要結構化日誌，再考慮

### 待決策事項

- [x] **確認團隊接受漸進式改進** (已接受，2025-11-15)
- [x] **文檔化決策理由** (已完成，本文件)
- [ ] **未來何時觸發全面遷移** (當使用者 >50 人 或 需要日誌分析時)

---

## 7. 錯誤處理標準化

### 問題描述

當前系統錯誤處理格式不一致，需統一錯誤回應格式。

### 建議統一格式

```json
{
  "status": "error",
  "code": "FILE_TOO_LARGE",
  "message": "檔案大小超過 10MB",
  "details": {
    "file_size": 12582912,
    "max_size": 10485760
  }
}
```

### 錯誤碼定義表

| HTTP 狀態碼 | 錯誤碼 | 中文訊息 | 使用場景 |
|-----------|-------|---------|---------|
| 400 | `FILE_TOO_LARGE` | 檔案大小超過 10MB | 檔案上傳 |
| 400 | `FILE_INVALID_FORMAT` | 檔案格式錯誤，僅支援 .xlsx | 檔案上傳 |
| 400 | `WEIGHT_SUM_INVALID` | 權重總和必須等於 1.0 | 權重配置 |
| 400 | `SESSION_TITLE_TOO_LONG` | 會話標題超過 100 字 | 會話建立 |
| 400 | `SESSION_TITLE_INVALID_CHARS` | 會話標題包含特殊字元 | 會話建立 |
| 404 | `SESSION_NOT_FOUND` | 找不到指定會話 | 會話載入 |
| 500 | `AI_SERVICE_ERROR` | AI 服務呼叫失敗 | LLM 呼叫 |
| 500 | `DATABASE_ERROR` | 資料庫操作失敗 | SQLite 操作 |
| 503 | `KB_BUILDING_IN_PROGRESS` | 知識庫同步中，請稍後再試 | 知識庫同步 |

### 決策建議

**建議**: **Phase 1 實作統一錯誤處理器**

**實作範例** (core/error_handler.py):
```python
from flask import jsonify

class ValidationError(Exception):
    def __init__(self, code, message, details=None):
        self.code = code
        self.message = message
        self.details = details

def register_error_handlers(app):
    @app.errorhandler(ValidationError)
    def handle_validation_error(e):
        return jsonify({
            "status": "error",
            "code": e.code,
            "message": e.message,
            "details": e.details
        }), 400

    @app.errorhandler(500)
    def handle_internal_error(e):
        return jsonify({
            "status": "error",
            "code": "INTERNAL_SERVER_ERROR",
            "message": "伺服器內部錯誤"
        }), 500
```

### 待決策事項

- [ ] **確認錯誤碼命名規則** (是否接受英文錯誤碼)
- [ ] **確認錯誤碼是否需要國際化** (i18n 支援)
- [ ] **確認 details 欄位是否必要** (除錯時有用)

---

## 8. 配置管理策略

### 問題描述

當前系統配置檔案散落，各配置獨立儲存，不保證原子性。

### 當前配置儲存方式

| 配置類型 | 儲存方式 | 檔案路徑 |
|---------|---------|---------|
| 權重配置 | JSON | `config/weight_config.json` |
| 提示詞配置 | JSON | `config/prompt_config.json` |
| 環境變數 | .env | `.env` |
| SharePoint 路徑 | JSON | `StorageAddress/SyncAddress.json` |
| 類別對照表 | JSON | `config/category_mapping.json` |

### 問題

1. **原子性問題**: 各配置獨立儲存，修改時可能部分失敗
2. **一致性問題**: 無法保證多個配置之間的一致性
3. **版本控制**: 無配置版本管理

### 方案比較

| 方案 | 優點 | 缺點 | 適用場景 |
|------|------|------|---------|
| **保持現狀 (JSON)** | 簡單，易讀寫 | 無原子性保證 | 當前系統 (已釐清為設計決策) |
| **遷移至 SQLite** | 原子性，一致性 | 讀寫較慢，配置難以版本控制 | 需要原子性保證 |
| **使用 Config Server** | 集中管理，版本控制 | 複雜度高，過度工程 | 大型分散式系統 |

### 決策建議

**建議**: **保持現狀 (JSON)**

**理由**:
1. **已釐清為設計決策** (系統配置管理.feature:69-79)
2. 當前系統配置修改頻率低，原子性問題影響小
3. JSON 檔案易讀寫，便於版本控制 (Git)

**緩解措施**:
- 配置修改時顯示警告: "修改配置後請重啟應用"
- 實作配置驗證 (啟動時檢查配置一致性)

### 待決策事項

- [ ] **確認配置修改頻率** (是否需要原子性)
- [ ] **確認是否可接受"修改後重啟"** (影響使用者體驗)
- [ ] **若未來需要原子性，何時遷移至 SQLite** (需求明確後)

---

## 9. 測試資料管理

### 問題描述

需確定測試資料管理策略，避免測試資料污染生產資料。

### 方案比較

| 方案 | 優點 | 缺點 | 適用場景 |
|------|------|------|---------|
| **Fixtures (JSON/Excel)** | 版本控制，可重現 | 需手動維護 | 單元測試 |
| **Faker 生成** | 自動生成，多樣性高 | 不可重現 (隨機) | 壓力測試 |
| **測試資料庫** | 隔離生產資料 | 需額外設定 | 整合測試 |
| **事務回滾** | 自動清理，速度快 | SQLite 不完全支援 | 整合測試 (可選) |

### 決策建議

**建議**: **Fixtures + Faker + 測試資料庫**

**實作策略**:
1. **單元測試**: 使用 Fixtures (tests/fixtures/)
2. **整合測試**: 使用測試資料庫 (tests/test.db)
3. **效能測試**: 使用 Faker 生成大量資料

**實作範例** (conftest.py):
```python
@pytest.fixture
def temp_db():
    """臨時測試資料庫"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    conn = sqlite3.connect(db_path)
    # 創建表結構
    cursor.execute(CREATE_TABLE_SQL)
    conn.commit()

    yield conn

    conn.close()
    os.unlink(db_path)
```

### 待決策事項

- [ ] **確認測試資料儲存位置** (tests/fixtures/ ?)
- [ ] **確認是否需要 Faker** (自動生成測試資料)
- [ ] **確認 SQLite 事務回滾可行性** (影響測試速度)

---

## 10. 潛在風險

### 風險 1: 重構過程中破壞現有功能

**可能性**: 中 (30%)
**影響**: 高 (系統不可用)

**緩解措施**:
1. ✅ **增量遷移**: 每遷移一個模組就測試
2. ✅ **Git 頻繁提交**: 確保可回滾
3. ✅ **保留備份**: `Analysis_backup.py`
4. ✅ **Phase 2 建立測試**: 回歸測試保障

### 風險 2: 時程延誤

**可能性**: 高 (50%)
**影響**: 中 (延後上線)

**緩解措施**:
1. ✅ **優先順序明確**: Phase 1-2 必須，Phase 3 可選
2. ✅ **緩衝時間**: 每個 Phase 預留 1 週緩衝
3. ✅ **最小可行產品 (MVP)**: Phase 1 完成後即可上線

### 風險 3: 測試撰寫耗時超出預期

**可能性**: 中 (40%)
**影響**: 中 (覆蓋率不足)

**緩解措施**:
1. ✅ **降低覆蓋率目標**: 70% → 60% (最低標準)
2. ✅ **優先核心模組**: Services 層 & Agents 層必須達 80%
3. ✅ **延後 E2E 測試**: Phase 3 或更晚

### 風險 4: 效能優化效果不明顯

**可能性**: 低 (20%)
**影響**: 低 (使用者體驗略差)

**緩解措施**:
1. ✅ **Phase 2 實測驗證**: 識別真正瓶頸
2. ✅ **聚焦高 ROI 優化**: LLM 快取、Excel 讀寫
3. ✅ **接受現狀**: 當前效能已可接受

### 風險 5: 依賴版本衝突

**可能性**: 低 (10%)
**影響**: 高 (系統無法啟動)

**緩解措施**:
1. ✅ **鎖定依賴版本**: requirements.txt 指定確切版本
2. ✅ **虛擬環境隔離**: venv 或 conda
3. ✅ **相容性測試**: 升級依賴前先測試

---

## 決策追蹤表

| 決策編號 | 決策項目 | 狀態 | 負責人 | 預計決策日期 | 實際決策日期 |
|---------|---------|------|-------|------------|------------|
| D1 | 技術債處理優先順序 | 待決策 | Tech Lead | 2025-11-10 | - |
| D2 | 跨平台支援必要性 | 待決策 | IT Manager | 2025-11-15 | - |
| D3 | 任務佇列選型 | 待決策 | Tech Lead | 2025-11-15 | - |
| D4 | 測試覆蓋率目標 | 待決策 | Tech Lead | 2025-11-10 | - |
| D5 | 依賴注入方案 | 待決策 | Dev Team | 2025-11-10 | - |
| D6 | 錯誤處理標準化 | 待決策 | Dev Team | 2025-11-10 | - |
| D7 | 配置管理策略 | 已決策 (保持現狀) | Tech Lead | - | 2025-10-30 |
| D8 | 測試資料管理 | 待決策 | QA Lead | 2025-11-15 | - |

---

## 下一步行動

### 立即行動 (本週內)

1. [ ] **召開決策會議** (與 Tech Lead, IT Manager 討論)
   - 確認 D1, D4, D5, D6 決策
   - 預計時間: 2025-11-10

2. [ ] **更新專案文件** (根據決策結果)
   - 更新 phase1_architecture_refactor.md
   - 更新 phase2_testing_optimization.md

3. [ ] **啟動 Phase 1 Week 1** (建立骨架)
   - 創建目錄結構
   - 實作 5 個 Blueprints

### 短期行動 (2 週內)

1. [ ] **Phase 2 實測驗證** (Week 4)
   - 效能瓶頸識別
   - openpyxl vs win32com 效能比較

2. [ ] **確認 D2, D3 決策** (與 IT Manager 討論)
   - 跨平台需求確認
   - 任務佇列需求確認

### 長期行動 (1 個月後)

1. [ ] **Phase 3 功能優先順序** (與業務方討論)
   - 確認 P0-P2 功能實作順序
   - 確認進階功能需求 (任務佇列、認證系統)

2. [ ] **持續優化與維護**
   - 根據使用者回饋調整
   - 定期效能監控與優化
