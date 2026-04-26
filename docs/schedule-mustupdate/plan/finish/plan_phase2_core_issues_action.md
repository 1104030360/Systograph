# Phase 2 核心問題整合行動計劃

**最新更新**: 2025-11-15  
**實際狀態**: ⏳ 尚未啟動（僅完成測試收集，覆蓋率/CI/效能測試皆未建立）

- 2025-11-15 執行 `pytest --collect-only -q` → **999 tests collected**, 0 errors
- 覆蓋率：未量測 (`coverage run` 尚未執行)
- 缺漏：`tests/unit/utils/test_ai_utils.py`、`tests/unit/utils/test_vector_utils.py`、`tests/unit/agents/test_followup_agent.py`、`tests/integration/test_rag_system.py`、`tests/performance/` 仍為空
- 依據 `2025-11-14-report.md`，Priority 1 缺陷（Autogen 回傳、Repositories/DI、Blueprint 瘦身、Logging/Error Handling）尚未動工

| 2025-11-14 報告項目 | 現況 | 行動 |
|---------------------|------|------|
| 測試統計/文檔落差 | CLAUDE/AGENTS 已更新為 999 測試 | ✅ structsync 完成 |
| Plan/Report 差異 | COMMIT_STATUS 更新、report 同步中 | ⏳ planfix 階段執行 |
| Priority 1 核心缺陷 | 未開始 | ➡️ corefix 階段負責 |
| Priority 2 測試 & CI | 未開始 | ➡️ testlayer 階段負責 |
| Priority 3 AI Builder | 未開始 | ➡️ aibuilder 階段負責 |

---

## 2025-11-07 規劃（Archived）
> 以下章節保留 2025-11-07 v1.0 規劃，以供追溯；所有覆蓋率/完成度敘述不再代表現況。

**創建日期**: 2025-11-07  
**計劃版本**: v1.0  
**整合來源**:
- Phase 2 測試優化檢查 (2025-11-07-Phase2-Complete-Status-Check-REP.md)
- 代碼審查核心問題 (g.md)

---

## 📋 執行摘要（Archived）

### 當前狀態（2025-11-07）
- **Phase 2 測試覆蓋率**: 92% (目標 95%)
- **架構問題**: 發現 4 個核心問題需立即處理
- **整體完成度**: 78% (Phase 2 測試優化) + 新增架構優化需求
- **剩餘工作量**: 約 16.5-23.5 小時

### 優先級分佈
- 🔴 **高優先級**: 3 項任務 (7-10 小時) ← **本週完成**
- 🟡 **中優先級**: 3 項任務 (5-7 小時) ← **下週完成**
- 🟢 **低優先級**: 4 項任務 (4.5-6.5 小時) ← **未來迭代**

---

## 🔴 高優先級任務 (本週完成)

### Task 1: 重構 SmartScoring.py 全域模型載入

**問題編號**: g.md Issue #1
**嚴重性**: 🔴 高
**預估時間**: 2-3 小時

#### 當前問題
```python
# SmartScoring.py - 問題代碼
import SmartScoring  # ← 立即載入 BERT、KeyBERT、spaCy (~3-5秒, ~500MB+)
```

**影響**:
- ❌ Import 時就觸發耗時 I/O (3-5 秒)
- ❌ 單元測試必須大量 monkeypatch 繞過模型載入
- ❌ 即使不使用也佔用 500MB+ 記憶體
- ❌ 違反 Python 最佳實踐 (import 不應有副作用)

#### 解決方案

**步驟 1: 建立 ScoringEngine 類別** (1 小時)
```python
# SmartScoring.py - 重構後架構
class ScoringEngine:
    """風險評分引擎 - 延遲載入模型"""

    _instance = None  # Singleton pattern
    _models_loaded = False

    def __init__(self):
        self._bert_model = None
        self._keybert_model = None
        self._spacy_nlp = None

    @classmethod
    def get_instance(cls):
        """獲取單例實例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_models(self):
        """延遲載入模型 - 首次使用時才初始化"""
        if not self._models_loaded:
            logger.info("Loading AI models for risk scoring...")
            self._bert_model = SentenceTransformer('all-MiniLM-L6-v2')
            self._keybert_model = KeyBERT(model=self._bert_model)
            self._spacy_nlp = spacy.load('zh_core_web_sm')
            self._models_loaded = True
            logger.info("Models loaded successfully")

    def calculate_risk(self, text: str) -> Dict:
        """計算風險 - 自動觸發模型載入"""
        self._load_models()  # 首次呼叫時才載入
        # ... 原有計算邏輯
```

**步驟 2: 重構現有函式** (30 分鐘)
```python
# 公開 API - 向後兼容
def is_high_risk(text: str) -> bool:
    """向後兼容的 API"""
    engine = ScoringEngine.get_instance()
    result = engine.calculate_risk(text)
    return result['is_high_risk']

def calculate_smart_score(text: str, sentences_db) -> Dict:
    """向後兼容的 API"""
    engine = ScoringEngine.get_instance()
    return engine.calculate_smart_score(text, sentences_db)
```

**步驟 3: 更新測試** (30 分鐘)
```python
# tests/unit/utils/test_smartscoring.py
@pytest.fixture
def mock_scoring_engine(monkeypatch):
    """提供 mock 的 ScoringEngine"""
    engine = ScoringEngine()
    engine._models_loaded = True
    engine._bert_model = Mock()
    engine._keybert_model = Mock()
    monkeypatch.setattr(ScoringEngine, 'get_instance', lambda: engine)
    return engine

def test_calculate_risk_with_mock(mock_scoring_engine):
    # 無需載入真實模型，測試運行速度快
    result = is_high_risk("火災緊急事件")
    assert result is True
```

**步驟 4: 更新 services/risk_service.py** (30 分鐘)
```python
# services/risk_service.py
from SmartScoring import ScoringEngine

class RiskService:
    def __init__(self):
        self.scoring_engine = ScoringEngine.get_instance()

    def calculate_risk_level(self, text: str):
        # 自動觸發延遲載入
        return self.scoring_engine.calculate_risk(text)
```

#### 驗收標準
- [ ] 所有模型載入邏輯從檔案頂層移除
- [ ] `ScoringEngine` 類別實現延遲載入
- [ ] 所有現有測試通過 (無需修改太多)
- [ ] Import SmartScoring 時間從 3-5 秒降至 <0.1 秒
- [ ] 向後兼容性: 舊代碼無需修改即可運行

#### 影響範圍
- **修改檔案**: `SmartScoring.py` (~289 lines)
- **測試檔案**: `tests/unit/utils/test_smartscoring.py`
- **服務層**: `services/risk_service.py`
- **向後兼容**: ✅ 完全兼容，無需修改呼叫端

---

### Task 2: 覆蓋率提升至 95%

**問題編號**: Phase 2-F (未完成項)
**嚴重性**: 🔴 高
**預估時間**: 3-4 小時

#### 當前狀態
- **整體覆蓋率**: 92% (11,382 statements, 925 miss)
- **目標**: 95% (~340 lines 需補充測試)

#### 關鍵缺口分析

**優先修補區域** (按影響力排序):

| 模組 | 當前覆蓋率 | 目標覆蓋率 | 預估時間 | 優先級 |
|------|------------|------------|----------|--------|
| repositories layer | 26-38% | 85% | 1.5 小時 | 🔴 高 |
| build_kb.py | 71% | 85% | 1 小時 | 🔴 高 |
| services/ticket_service.py | 74% | 90% | 1 小時 | 🟡 中 |
| utils/excel_utils.py | 73% | 85% | 0.5 小時 | 🟡 中 |

#### 執行計劃

**Phase A: Repositories 層覆蓋率提升** (1.5 小時)

```python
# tests/unit/repositories/test_config_repository.py (新建)
"""
目標: 從 26% 提升至 85%
重點: CRUD 操作、異常處理、邊界條件
"""

def test_save_config_success(config_repo, sample_config):
    """測試配置保存成功"""
    result = config_repo.save(sample_config)
    assert result['success'] is True

def test_save_config_duplicate_key(config_repo):
    """測試重複 key 處理"""
    # ... 實現

def test_load_config_not_found(config_repo):
    """測試載入不存在的配置"""
    with pytest.raises(ConfigNotFoundError):
        config_repo.load('non_existent_key')

def test_delete_config_cascade(config_repo):
    """測試刪除配置的級聯效應"""
    # ... 實現

# 預計新增: ~150 lines, 15 test cases
```

**Phase B: build_kb.py 覆蓋率提升** (1 小時)

```python
# tests/unit/test_build_kb.py (擴充)
"""
目標: 從 71% 提升至 85%
重點: Excel 同步異常、FAISS 索引失敗、備份機制
"""

def test_sync_knowledge_base_excel_locked(monkeypatch):
    """測試 Excel 被鎖定時的處理"""
    # Mock win32com 返回檔案被鎖定
    # 驗證降級至 openpyxl 或拋出友善錯誤

def test_build_faiss_index_dimension_mismatch():
    """測試 FAISS 索引維度不匹配"""
    # 預期應拋出 DimensionMismatchError

def test_backup_rotation_max_backups():
    """測試備份輪轉達到上限"""
    # 驗證舊備份被刪除

def test_excel_to_sqlite_encoding_error():
    """測試 Excel 編碼錯誤處理"""
    # 使用包含特殊字符的測試檔案

# 預計新增: ~100 lines, 10 test cases
```

**Phase C: ticket_service.py 覆蓋率提升** (1 小時)

```python
# tests/unit/services/test_ticket_service.py (擴充)
"""
目標: 從 74% 提升至 90%
重點: 異步處理異常、LLM 失敗、批次中斷恢復
"""

def test_process_uploaded_file_llm_timeout(ticket_service, mock_llm):
    """測試 LLM 超時時的處理"""
    mock_llm.side_effect = TimeoutError()
    result = ticket_service.process_uploaded_file('test.xlsx')
    # 驗證降級至規則基礎處理
    assert result['fallback_used'] is True

def test_extract_ai_analysis_all_providers_fail(ticket_service):
    """測試所有 LLM 提供者都失敗"""
    # Mock Power Automate + Ollama 都失敗
    # 驗證返回友善錯誤訊息

def test_batch_processing_resume_from_checkpoint(ticket_service):
    """測試批次處理從中斷點恢復"""
    # 模擬處理到一半崩潰
    # 驗證可從檢查點繼續

# 預計新增: ~120 lines, 12 test cases
```

**Phase D: excel_utils.py 覆蓋率提升** (0.5 小時)

```python
# tests/unit/utils/test_excel_utils.py (擴充)
"""
目標: 從 73% 提升至 85%
重點: COM 操作異常、跨平台兼容
"""

def test_close_excel_if_open_com_error(monkeypatch):
    """測試 COM 操作異常"""
    # Mock win32com 拋出 COM 異常
    # 驗證降級至檔案系統操作

def test_read_excel_on_non_windows(monkeypatch):
    """測試非 Windows 平台讀取"""
    monkeypatch.setattr('platform.system', lambda: 'Darwin')
    # 驗證自動使用 openpyxl

# 預計新增: ~50 lines, 5 test cases
```

#### 驗收標準
- [ ] 整體覆蓋率達到 95% (當前 92%)
- [ ] repositories 層覆蓋率從 26-38% 提升至 85%
- [ ] build_kb.py 覆蓋率從 71% 提升至 85%
- [ ] ticket_service.py 覆蓋率從 74% 提升至 90%
- [ ] 所有新測試必須通過
- [ ] 覆蓋率報告自動生成 (coverage report -m)

#### 影響範圍
- **新增測試檔案**: `tests/unit/repositories/test_config_repository.py`
- **擴充測試檔案**: 4 個現有測試檔案
- **預計新增代碼**: ~420 lines (純測試)
- **預計新增測試案例**: ~42 個

---

### Task 3: 補強核心模組異常測試

**問題編號**: g.md Issue #3 + Phase 2 檢查
**嚴重性**: 🔴 高
**預估時間**: 2-3 小時

#### 問題描述
雖然整體覆蓋率達 92%，但**關鍵邏輯分支**和**異常場景**測試不足。

#### 執行計劃

**Phase A: SmartScoring.py 分支測試** (1 小時)

```python
# tests/unit/utils/test_smartscoring.py (補強)

def test_is_high_risk_all_scenarios():
    """測試所有風險等級場景"""
    # 高風險: score >= 7.0
    assert is_high_risk("火災緊急事件") is True

    # 中風險: 4.0 <= score < 7.0
    assert is_high_risk("系統運行緩慢") is False

    # 低風險: score < 4.0
    assert is_high_risk("一般查詢") is False

def test_is_escalated_no_database():
    """測試無語句庫可比對時的處理"""
    result = is_escalated("測試文本", sentences_db=[])
    # 預期應降級至關鍵字檢測
    assert result['fallback_used'] is True

def test_is_multi_user_boundary_values():
    """測試多用戶檢測邊界值"""
    # 邊界值: 2 users (threshold)
    assert is_multi_user("兩位同事無法登入") is True

    # 邊界值: 1 user
    assert is_multi_user("我無法登入") is False

    # 邊界值: 大量用戶
    assert is_multi_user("全公司 500 人都無法連線") is True

def test_calculate_risk_with_malformed_input():
    """測試畸形輸入處理"""
    # 空字串
    result = calculate_smart_score("", [])
    assert result['error'] is not None

    # 純符號
    result = calculate_smart_score("@#$%^&*()", [])
    assert result['default_score'] == 5.0

# 預計新增: ~80 lines, 8 test cases
```

**Phase B: agents/sql_agent.py 複雜查詢測試** (1 小時)

```python
# tests/unit/agents/test_sql_agent.py (補強)

def test_generate_sql_complex_join(sql_agent):
    """測試複雜 JOIN 查詢生成"""
    query = "查詢所有高風險案件的平均解決時間"
    sql = sql_agent.generate_sql(query)
    assert "JOIN" in sql
    assert "AVG" in sql
    assert "WHERE risk_level = 'high'" in sql

def test_generate_sql_group_by_having(sql_agent):
    """測試 GROUP BY + HAVING 查詢"""
    query = "找出案件數超過 10 件的類別"
    sql = sql_agent.generate_sql(query)
    assert "GROUP BY" in sql
    assert "HAVING COUNT(*) > 10" in sql

def test_generate_sql_multi_table_join(sql_agent, test_db):
    """測試多表關聯查詢"""
    # 建立測試用多表環境
    test_db.create_table('tickets')
    test_db.create_table('users')
    test_db.create_table('categories')

    query = "查詢各部門的案件統計"
    sql = sql_agent.generate_sql(query)
    # 驗證正確使用多表 JOIN

def test_execute_sql_injection_prevention(sql_agent):
    """測試 SQL 注入防護"""
    malicious_query = "刪除所有資料'; DROP TABLE metadata; --"
    with pytest.raises(SecurityError):
        sql_agent.execute(malicious_query)

# 預計新增: ~100 lines, 10 test cases
```

**Phase C: services/ticket_service.py 異常場景** (1 小時)

```python
# tests/unit/services/test_ticket_service.py (補強)

def test_process_uploaded_file_async_exception(ticket_service):
    """測試異步處理異常"""
    # Mock 異步任務拋出異常
    with pytest.raises(AsyncProcessingError):
        ticket_service.process_uploaded_file_async('test.xlsx')

def test_extract_ai_analysis_llm_failure_cascade(ticket_service, mock_llm):
    """測試 LLM 失敗級聯處理"""
    # Mock Power Automate 失敗
    mock_llm.power_automate.side_effect = TimeoutError()

    # Mock Ollama 也失敗
    mock_llm.ollama.side_effect = ConnectionError()

    result = ticket_service._extract_ai_analysis("test text")
    # 驗證降級至規則基礎分析
    assert result['method'] == 'rule_based'
    assert result['confidence'] < 0.5

def test_batch_processing_interrupt_recovery(ticket_service, tmp_path):
    """測試批次處理中斷恢復"""
    checkpoint_file = tmp_path / "checkpoint.json"

    # 模擬處理到 50% 時中斷
    ticket_service.start_batch_processing('test.xlsx', checkpoint_file)
    # ... 模擬中斷

    # 從檢查點恢復
    ticket_service.resume_batch_processing(checkpoint_file)
    # 驗證從 51% 繼續而非重頭開始

# 預計新增: ~90 lines, 9 test cases
```

#### 驗收標準
- [ ] SmartScoring 所有風險等級分支有測試覆蓋
- [ ] sql_agent 支援複雜 JOIN/GROUP BY 查詢
- [ ] ticket_service 異常場景有完整測試
- [ ] 新增測試案例至少 27 個
- [ ] 所有測試通過且覆蓋率提升 3-5%

#### 影響範圍
- **擴充測試檔案**: 3 個現有測試檔案
- **預計新增代碼**: ~270 lines (純測試)
- **預計新增測試案例**: 27 個

---

## 🟡 中優先級任務 (下週完成)

### Task 4: 完善 win32com 跨平台支持

**問題編號**: g.md Issue #2
**嚴重性**: 🟡 中
**預估時間**: 3-4 小時

#### 當前狀態
```python
# utils/excel_utils.py - 平台依賴現況
✅ 讀寫操作: openpyxl (跨平台)
❌ 檔案鎖定: win32com (Windows only)
❌ 刷新外部連結: win32com (Windows only)
```

#### 解決方案

**步驟 1: 評估資料流程重構** (1 小時)
- [ ] **選項 A**: 文檔說明 - 要求使用者上傳前手動刷新 Excel
- [ ] **選項 B**: 架構改變 - 直接從源資料庫獲取資料
- [ ] 與 stakeholders 確認需求

**步驟 2: 替換檔案鎖定機制** (1.5 小時)
```python
# utils/excel_utils.py - 跨平台檔案鎖定
import portalocker  # 跨平台檔案鎖定庫

def lock_excel_file(file_path):
    """跨平台檔案鎖定"""
    try:
        lock_file = portalocker.Lock(file_path, timeout=5)
        return lock_file
    except portalocker.exceptions.LockException:
        raise FileLockError(f"檔案被鎖定: {file_path}")

def close_excel_if_open(file_path):
    """跨平台關閉 Excel"""
    if platform.system() == 'Windows':
        try:
            # 嘗試使用 win32com
            _close_excel_com(file_path)
        except ImportError:
            # 降級至檔案鎖定檢查
            _close_excel_fallback(file_path)
    else:
        # macOS/Linux 使用檔案鎖定檢查
        _close_excel_fallback(file_path)
```

**步驟 3: 條件依賴配置** (0.5 小時)
```python
# requirements.txt
openpyxl>=3.0.0
portalocker>=2.0.0  # 跨平台檔案鎖定
pywin32>=306; platform_system=="Windows"  # 可選依賴
```

**步驟 4: 測試跨平台兼容** (1 小時)
```python
# tests/unit/utils/test_excel_utils.py
@pytest.mark.skipif(platform.system() != 'Windows', reason="Windows only")
def test_close_excel_com():
    """測試 COM 關閉機制 (僅 Windows)"""
    # ...

def test_close_excel_fallback():
    """測試降級關閉機制 (所有平台)"""
    # ...
```

#### 驗收標準
- [ ] 核心讀寫功能在 macOS/Linux 可運行
- [ ] 檔案鎖定使用 `portalocker` 實現跨平台
- [ ] win32com 設為可選依賴
- [ ] 文檔說明 Windows 特有功能
- [ ] CI/CD 在多平台測試通過

---

### Task 5: RAG System 整合測試

**問題編號**: Phase 2-E (未完成項)
**嚴重性**: 🟡 中
**預估時間**: 1-2 小時

#### 測試目標
驗證 RAG 系統多代理協作的端到端流程。

#### 執行計劃

```python
# tests/integration/test_rag_system.py (新建)

def test_rag_query_routing(test_client, kb_data):
    """測試查詢路由至正確 agent"""

    # SQL 查詢 → sql_agent
    response = test_client.post('/api/chat', json={
        'message': '最近一個月有多少案件?'
    })
    assert response.json['agent_used'] == 'sql_agent'

    # 語義查詢 → semantic_agent
    response = test_client.post('/api/chat', json={
        'message': '如何解決郵件無法發送的問題?'
    })
    assert response.json['agent_used'] == 'semantic_agent'

    # 混合查詢 → hybrid_agent
    response = test_client.post('/api/chat', json={
        'message': '找出高風險的網路問題案件及其平均解決時間'
    })
    assert response.json['agent_used'] == 'hybrid_agent'

def test_rag_multi_turn_conversation(test_client):
    """測試多輪對話上下文保持"""
    session_id = 'test_session_001'

    # 第一輪
    r1 = test_client.post('/api/chat', json={
        'message': '查詢所有印表機問題',
        'session_id': session_id
    })

    # 第二輪 (follow-up)
    r2 = test_client.post('/api/chat', json={
        'message': '這些問題中哪些是高風險的?',
        'session_id': session_id
    })

    # 驗證上下文被正確使用
    assert '印表機' in r2.json['query_context']

def test_rag_error_handling_cascade(test_client, monkeypatch):
    """測試 RAG 系統錯誤處理級聯"""
    # Mock FAISS 失敗
    monkeypatch.setattr('faiss.Index.search', Mock(side_effect=RuntimeError))

    response = test_client.post('/api/chat', json={
        'message': '查詢案件'
    })

    # 驗證降級至 SQL 或返回友善錯誤
    assert response.status_code == 200
    assert 'error' in response.json or 'fallback' in response.json

# 預計: ~150 lines, 10 test cases
```

#### 驗收標準
- [ ] 查詢正確路由至對應 agent
- [ ] 多輪對話上下文正確保持
- [ ] 錯誤時有友善降級機制
- [ ] 整合測試覆蓋所有 agent
- [ ] 測試運行時間 < 30 秒

---

### Task 6: 完整工作流程測試

**問題編號**: Phase 2-E (未完成項)
**嚴重性**: 🟡 中
**預估時間**: 1 小時

#### 測試目標
驗證完整的 Ticket 處理流程 (上傳 → 分析 → 聚類 → 導出)。

#### 執行計劃

```python
# tests/integration/test_ticket_e2e.py (擴充)

def test_complete_ticket_workflow(test_client, sample_excel_file):
    """測試完整 Ticket 工作流程"""

    # Step 1: 上傳 Excel 檔案
    upload_response = test_client.post('/api/upload', data={
        'file': (sample_excel_file, 'test.xlsx')
    })
    assert upload_response.status_code == 200
    task_id = upload_response.json['task_id']

    # Step 2: 等待分析完成
    time.sleep(2)
    status_response = test_client.get(f'/api/task/{task_id}/status')
    assert status_response.json['status'] == 'completed'

    # Step 3: 執行聚類
    cluster_response = test_client.post('/api/cluster', json={
        'task_id': task_id,
        'method': 'kmeans',
        'n_clusters': 3
    })
    assert cluster_response.status_code == 200

    # Step 4: 導出結果
    export_response = test_client.get(f'/api/export/{task_id}')
    assert export_response.status_code == 200
    assert export_response.headers['Content-Type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

    # Step 5: 驗證輸出檔案
    output_file = f"excel_result_Clustered/test_{task_id}.xlsx"
    assert os.path.exists(output_file)

    # 驗證 Excel 內容
    df = pd.read_excel(output_file)
    assert 'cluster_id' in df.columns
    assert df['cluster_id'].nunique() == 3

def test_workflow_with_errors(test_client, malformed_excel_file):
    """測試工作流程異常處理"""
    # 上傳格式錯誤的檔案
    response = test_client.post('/api/upload', data={
        'file': (malformed_excel_file, 'bad.xlsx')
    })

    # 驗證友善錯誤訊息
    assert response.status_code == 400
    assert '格式錯誤' in response.json['error']

# 預計: ~100 lines, 5 test cases
```

#### 驗收標準
- [ ] 完整流程測試通過 (上傳→分析→聚類→導出)
- [ ] 異常場景有明確錯誤訊息
- [ ] 測試使用真實檔案格式
- [ ] 測試資料自動清理
- [ ] 測試運行時間 < 15 秒

---

## 🟢 低優先級任務 (未來迭代)

### Task 7: 建立 CI/CD 流程

**問題編號**: g.md Issue #4 + Phase 2 檢查
**嚴重性**: 🟢 低
**預估時間**: 1-2 小時

#### 執行計劃

**步驟 1: GitHub Actions 配置** (1 小時)
```yaml
# .github/workflows/test.yml (新建)
name: Run Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: ['3.12']

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-cov

      - name: Run tests with coverage
        run: |
          pytest tests/ --cov --cov-report=xml --cov-report=html

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

**步驟 2: 覆蓋率報告自動化** (0.5 小時)
```yaml
# .github/workflows/coverage.yml (新建)
name: Coverage Report

on:
  push:
    branches: [ main ]

jobs:
  coverage:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run coverage
        run: |
          pytest --cov --cov-report=html
      - name: Deploy coverage report
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./htmlcov
```

#### 驗收標準
- [ ] GitHub Actions 自動測試流程
- [ ] 多平台測試 (Ubuntu/Windows/macOS)
- [ ] 覆蓋率報告自動生成並上傳
- [ ] PR 時自動運行測試
- [ ] 測試失敗時阻止 merge

---

### Task 8: 補充 conftest.py Fixtures

**問題編號**: g.md Issue #4
**嚴重性**: 🟢 低
**預估時間**: 1 小時

#### 執行計劃

```python
# tests/conftest.py (擴充)

@pytest.fixture
def ticket_repo(test_db):
    """Ticket repository fixture"""
    from repositories.ticket_repository import TicketRepository
    return TicketRepository(test_db)

@pytest.fixture
def config_repo(test_db):
    """Config repository fixture"""
    from repositories.config_repository import ConfigRepository
    return ConfigRepository(test_db)

@pytest.fixture
def chat_repo(test_db):
    """Chat repository fixture"""
    from repositories.chat_repository import ChatRepository
    return ChatRepository(test_db)

@pytest.fixture
def mock_llm():
    """Mock LLM providers"""
    with patch('gpt_utils.call_power_automate') as mock_pa, \
         patch('gpt_utils.call_ollama') as mock_ollama:
        mock_pa.return_value = {"result": "Mocked response"}
        mock_ollama.return_value = "Mocked Ollama response"
        yield {'power_automate': mock_pa, 'ollama': mock_ollama}

@pytest.fixture
def sample_excel_file(tmp_path):
    """生成測試用 Excel 檔案"""
    file_path = tmp_path / "test.xlsx"
    df = pd.DataFrame({
        'id': ['INC001', 'INC002'],
        'description': ['測試案件1', '測試案件2'],
        'category': ['網路', '系統']
    })
    df.to_excel(file_path, index=False)
    return file_path
```

#### 驗收標準
- [ ] 所有 repository fixtures 完整
- [ ] LLM mock fixtures 可重用
- [ ] 測試檔案生成 fixtures
- [ ] 測試資料清理自動化
- [ ] 文檔說明 fixture 使用方式

---

### Task 9: Performance 測試

**問題編號**: Phase 2-G (未完成項)
**嚴重性**: 🟢 低
**預估時間**: 2-3 小時

#### 執行計劃

```python
# tests/performance/test_performance.py (新建)

def test_ticket_processing_throughput():
    """測試 Ticket 處理吞吐量"""
    start = time.time()

    # 處理 100 筆案件
    for i in range(100):
        process_ticket(f"test_{i}")

    duration = time.time() - start
    throughput = 100 / duration

    # 基準: 每秒至少 10 筆
    assert throughput >= 10, f"Throughput {throughput:.2f} tickets/sec is below baseline"

def test_faiss_search_latency():
    """測試 FAISS 搜尋延遲"""
    query_embedding = np.random.rand(384).astype('float32')

    latencies = []
    for _ in range(100):
        start = time.time()
        faiss_index.search(query_embedding.reshape(1, -1), k=5)
        latencies.append(time.time() - start)

    avg_latency = np.mean(latencies)
    p95_latency = np.percentile(latencies, 95)

    # 基準: 平均 < 50ms, P95 < 100ms
    assert avg_latency < 0.05
    assert p95_latency < 0.1

def test_memory_leak_detection():
    """測試記憶體洩漏"""
    import tracemalloc
    tracemalloc.start()

    initial_memory = tracemalloc.get_traced_memory()[0]

    # 執行 1000 次查詢
    for _ in range(1000):
        process_rag_query("測試查詢")

    final_memory = tracemalloc.get_traced_memory()[0]
    memory_increase = (final_memory - initial_memory) / 1024 / 1024  # MB

    # 基準: 記憶體增長 < 50MB
    assert memory_increase < 50
```

#### 驗收標準
- [ ] 吞吐量基準測試
- [ ] 延遲基準測試
- [ ] 記憶體洩漏檢測
- [ ] 性能回歸檢測
- [ ] 性能報告自動生成

---

### Task 10: CI/CD 文檔

**問題編號**: Phase 2 檢查
**嚴重性**: 🟢 低
**預估時間**: 30 分鐘

#### 執行計劃

```markdown
# docs/testing/CI_CD_GUIDE.md (新建)

# CI/CD 測試指南

## 本地測試流程

### 運行所有測試
```bash
pytest tests/
```

### 運行特定層級測試
```bash
pytest tests/unit/        # 單元測試
pytest tests/integration/ # 整合測試
```

### 生成覆蓋率報告
```bash
pytest --cov --cov-report=html
open htmlcov/index.html
```

## GitHub Actions 自動測試

### 觸發條件
- Push to main/develop
- Pull Request to main

### 測試矩陣
- OS: Ubuntu, Windows, macOS
- Python: 3.12

### 查看測試結果
https://github.com/<your-repo>/actions

## 覆蓋率要求
- 整體覆蓋率: >= 95%
- 新代碼覆蓋率: >= 90%
- PR merge 條件: 所有測試通過

## 常見問題排除
...
```

#### 驗收標準
- [ ] CI/CD 流程文檔完整
- [ ] 本地測試指南清晰
- [ ] 常見問題有排除步驟
- [ ] 覆蓋率要求有明確標準
- [ ] 文檔包含實際範例

---

## 📊 整體時間估算

| 優先級 | 任務數 | 預估時間 | 累計時間 |
|--------|--------|----------|----------|
| 🔴 高 | 3 | 7-10 小時 | 7-10 小時 |
| 🟡 中 | 3 | 5-7 小時 | 12-17 小時 |
| 🟢 低 | 4 | 4.5-6.5 小時 | 16.5-23.5 小時 |

**總計**: 16.5-23.5 小時 (~2-3 個工作日)

---

## 🎯 執行建議

### Week 1 (本週)
**目標**: 完成所有高優先級任務

**Day 1-2**:
- ✅ Task 1: 重構 SmartScoring.py (2-3 小時)
- ✅ Task 2: 覆蓋率提升 Phase A-B (2.5 小時)

**Day 3-4**:
- ✅ Task 2: 覆蓋率提升 Phase C-D (1.5 小時)
- ✅ Task 3: 核心模組異常測試 (2-3 小時)

**Day 5**:
- 🔍 整體驗收和覆蓋率檢查
- 📝 更新狀態報告

### Week 2 (下週)
**目標**: 完成所有中優先級任務

**Day 1-2**:
- Task 4: win32com 跨平台支持 (3-4 小時)

**Day 3-4**:
- Task 5: RAG 整合測試 (1-2 小時)
- Task 6: 完整工作流程測試 (1 小時)

**Day 5**:
- 🔍 整合測試驗收
- 📝 Phase 2 完成報告

### Future Iterations
**目標**: 完成所有低優先級任務 (時間允許時)

- Task 7: CI/CD 流程 (1-2 小時)
- Task 8: conftest fixtures (1 小時)
- Task 9: Performance 測試 (2-3 小時)
- Task 10: CI/CD 文檔 (30 分鐘)

---

## 📈 進度追蹤

### 檢查點

**Checkpoint 1 (Week 1 - Day 2)**
- [ ] SmartScoring.py 重構完成
- [ ] repositories 層覆蓋率達 85%
- [ ] build_kb.py 覆蓋率達 85%

**Checkpoint 2 (Week 1 - Day 4)**
- [ ] ticket_service.py 覆蓋率達 90%
- [ ] excel_utils.py 覆蓋率達 85%
- [ ] 整體覆蓋率達 95%

**Checkpoint 3 (Week 1 - Day 5)**
- [ ] 所有核心模組異常測試完成
- [ ] 高優先級任務全部完成
- [ ] Week 1 狀態報告產出

**Checkpoint 4 (Week 2 - Day 4)**
- [ ] win32com 跨平台支持完成
- [ ] RAG 整合測試完成
- [ ] 完整工作流程測試完成

**Final Checkpoint (Week 2 - Day 5)**
- [ ] 中優先級任務全部完成
- [ ] Phase 2 測試優化完成
- [ ] Phase 2 完成報告產出

---

## 🚀 快速啟動

### 立即開始 Task 1 (SmartScoring 重構)

```bash
# 1. 建立特性分支
git checkout -b refactor/smartscoring-lazy-loading

# 2. 備份現有檔案
cp SmartScoring.py SmartScoring.py.backup

# 3. 運行現有測試確保基準
pytest tests/unit/utils/test_smartscoring.py -v

# 4. 開始重構 (參考 Task 1 詳細步驟)
# ... 編輯 SmartScoring.py

# 5. 運行測試驗證
pytest tests/unit/utils/test_smartscoring.py -v

# 6. 測量 import 時間改善
python -m timeit -n 1 -r 1 "import SmartScoring"
# Before: ~3-5 seconds
# After: <0.1 seconds (預期)

# 7. Commit 並推送
git add SmartScoring.py tests/
git commit -m "refactor: implement lazy loading for SmartScoring models"
git push origin refactor/smartscoring-lazy-loading
```

---

## 📝 報告模板

每個 Checkpoint 後使用以下模板更新進度：

```markdown
# Phase 2 進度報告 - Checkpoint X

**日期**: YYYY-MM-DD
**完成任務**: Task X, Task Y
**累計時間**: X 小時

## ✅ 已完成
- [ ] 任務描述
- [ ] 驗收標準達成

## 🚧 進行中
- [ ] 任務描述
- [ ] 當前進度 X%

## ❌ 阻礙
- 問題描述
- 解決方案

## 📊 覆蓋率變化
- Before: X%
- After: Y%
- Delta: +Z%

## ⏭️ 下一步
1. 任務 A
2. 任務 B
```

---

## 🎯 成功標準

### Phase 2 完成標準
- ✅ 整體測試覆蓋率達到 95%
- ✅ 所有高優先級架構問題解決
- ✅ RAG 系統整合測試通過
- ✅ 完整工作流程測試通過
- ✅ 核心模組異常場景有充分測試
- ✅ SmartScoring 模型延遲載入實現
- ✅ 所有測試通過 (757+ passing)

### 架構優化完成標準
- ✅ SmartScoring import 時間 < 0.1 秒
- ✅ win32com 跨平台降級機制實現
- ✅ 測試基礎建設完善 (fixtures, CI/CD)
- ✅ 性能基準測試建立

---

**計劃擁有者**: Phase 2 開發團隊
**審核者**: 架構負責人
**最後更新**: 2025-11-07
