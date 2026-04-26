# Phase 2: 測試與優化

**時程**: 2-3 週
**優先級**: 必須執行
**目標**: 達成 70% 測試覆蓋率，優化關鍵流程

---

## 問題定義

**當前系統問題**:
1. 無自動化測試，僅靠手動測試
2. 回歸測試成本高，重構風險大
3. 無效能監控機制
4. 潛在效能瓶頸未識別

**預期成果**:
- 測試覆蓋率達 70%
- 建立 CI/CD 自動化測試流程
- 識別並優化效能瓶頸
- 為未來功能擴展提供測試保障

> **2025-11-15 狀態**
> - ✅ `requirements-test.txt`、`tests/` 目錄、`tests/conftest.py` 等基礎測試架構已存在（fixtures/CI helper 亦在 `tests/conftest.py:192-467`，CI 範例寫於 `tests/README.md:40-208`）。
> - ⚠️ 覆蓋率目標與 CI pipeline 尚未實建（僅配置 `.coveragerc`，但沒有任何 CI 設定檔；未見 `coverage run` 報告）。
> - ⚠️ 規劃中的 `tests/e2e/` 與多數 E2E 腳本尚未建立，目前 `tests/` 下無 `e2e/` 目錄。
> - ⚠️ 效能與召回率測試僅有 `tests/performance/test_rag_performance.py`，仍未達文件內對「效能瓶頸識別」與「召回率測試集」的要求。

---

## Week 1: 建立測試框架

### 目標
建立完整的 pytest 測試基礎設施

### 任務清單

#### 1.1 安裝測試依賴

**requirements-test.txt**
- [ ] 創建 `requirements-test.txt`:
  ```
  pytest==7.4.3
  pytest-cov==4.1.0
  pytest-mock==3.12.0
  responses==0.24.1
  faker==20.1.0
  freezegun==1.4.0
  ```
- [ ] 安裝測試依賴: `pip install -r requirements-test.txt`

#### 1.2 建立測試目錄結構

```
tests/
├── __init__.py
├── conftest.py                # 共用 fixtures
├── unit/                      # 單元測試
│   ├── __init__.py
│   ├── services/
│   │   ├── test_ticket_service.py
│   │   ├── test_rag_service.py
│   │   ├── test_risk_service.py
│   │   ├── test_cluster_service.py
│   │   └── test_kb_service.py
│   ├── utils/
│   │   ├── test_ai_utils.py
│   │   ├── test_excel_utils.py
│   │   ├── test_vector_utils.py
│   │   └── test_validation_utils.py
│   └── agents/
│       ├── test_semantic_agent.py
│       ├── test_sql_agent.py
│       ├── test_hybrid_agent.py
│       └── test_followup_agent.py
├── integration/               # 整合測試
│   ├── __init__.py
│   ├── test_api_endpoints.py
│   ├── test_rag_system.py
│   ├── test_kb_sync.py
│   └── test_ticket_processing.py
├── e2e/                       # E2E 測試 (可選)
│   ├── __init__.py
│   └── test_user_workflows.py
├── performance/               # 效能測試
│   ├── __init__.py
│   └── test_bottlenecks.py
└── fixtures/                  # 測試資料
    ├── sample_tickets.xlsx
    ├── sample_config.json
    └── sample_chat_history.json
```

- [ ] 創建目錄結構
- [ ] 準備測試資料 (fixtures/)

#### 1.3 實作 conftest.py (共用 Fixtures)

**tests/conftest.py**
```python
import pytest
from unittest.mock import Mock, MagicMock
import sqlite3
import tempfile
import os

# ==================== Database Fixtures ====================
@pytest.fixture
def temp_db():
    """臨時 SQLite 資料庫"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 創建 metadata 表
    cursor.execute("""
        CREATE TABLE metadata (
            id INTEGER PRIMARY KEY,
            text TEXT,
            subcategory TEXT,
            configurationItem TEXT,
            roleComponent TEXT,
            location TEXT,
            opened TEXT,
            analysisTime TEXT
        )
    """)
    conn.commit()

    yield conn

    conn.close()
    os.unlink(db_path)

# ==================== Repository Fixtures ====================
@pytest.fixture
def ticket_repo(temp_db):
    """TicketRepository fixture"""
    from repositories.ticket_repo import TicketRepository
    return TicketRepository(temp_db)

@pytest.fixture
def config_repo(tmp_path):
    """ConfigRepository fixture"""
    from repositories.config_repo import ConfigRepository
    return ConfigRepository(config_dir=tmp_path)

@pytest.fixture
def chat_repo(tmp_path):
    """ChatRepository fixture"""
    from repositories.chat_repo import ChatRepository
    return ChatRepository(chat_history_dir=tmp_path)

# ==================== Mock Fixtures ====================
@pytest.fixture
def mock_llm_response():
    """Mock LLM 回應"""
    return {
        "status": "success",
        "response": "這是一個測試回應",
        "sources": [
            {"id": "INC001", "similarity": 0.95}
        ]
    }

@pytest.fixture
def mock_embedding_model():
    """Mock Sentence Transformer"""
    mock = MagicMock()
    mock.encode.return_value = [[0.1] * 384]  # 384 維向量
    return mock

@pytest.fixture
def mock_faiss_index():
    """Mock FAISS 索引"""
    mock = MagicMock()
    mock.search.return_value = (
        [[0.1, 0.2, 0.3]],  # distances
        [[1, 2, 3]]          # indices
    )
    return mock

# ==================== Sample Data Fixtures ====================
@pytest.fixture
def sample_ticket():
    """範例工單資料"""
    return {
        "id": "INC001",
        "text": "電腦無法開機，顯示藍屏錯誤",
        "subcategory": "硬體故障",
        "configurationItem": "Desktop PC",
        "roleComponent": "IT Support",
        "location": "Taipei Office",
        "opened": "2025-01-01 10:00:00",
        "analysisTime": "2025-01-01 10:05:00"
    }

@pytest.fixture
def sample_tickets_batch():
    """範例工單批次資料 (10 筆)"""
    from faker import Faker
    fake = Faker('zh_TW')

    tickets = []
    for i in range(10):
        tickets.append({
            "id": f"INC{i:03d}",
            "text": fake.text(max_nb_chars=100),
            "subcategory": fake.random_element(["硬體故障", "軟體問題", "網路問題"]),
            "configurationItem": fake.random_element(["Desktop PC", "Laptop", "Server"]),
            "location": fake.city()
        })
    return tickets

@pytest.fixture
def sample_weight_config():
    """範例權重配置"""
    return {
        "severityWeight": 0.6,
        "frequencyWeight": 0.4,
        "total": 1.0
    }

# ==================== Flask App Fixtures ====================
@pytest.fixture
def app():
    """Flask 測試應用"""
    from Analysis import create_app
    app = create_app()
    app.config['TESTING'] = True
    return app

@pytest.fixture
def client(app):
    """Flask 測試客戶端"""
    return app.test_client()
```

- [ ] 實作資料庫 fixtures
- [ ] 實作 Repository fixtures
- [ ] 實作 Mock fixtures (LLM, Embedding, FAISS)
- [ ] 實作範例資料 fixtures
- [ ] 實作 Flask 測試客戶端 fixtures

#### 1.4 建立 CI/CD 配置

**選項 1: GitHub Actions (.github/workflows/test.yml)**
```yaml
name: Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python 3.12
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt

      - name: Run tests
        run: |
          pytest tests/ -v --cov=. --cov-report=xml --cov-report=term

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

**選項 2: 本地腳本 (run_tests.bat)**
```batch
@echo off
echo Running tests...
pytest tests/ -v --cov=. --cov-report=html --cov-report=term
echo.
echo Coverage report generated at htmlcov/index.html
pause
```

- [ ] 選擇 CI/CD 方案 (GitHub Actions 或本地腳本)
- [ ] 創建配置檔案
- [ ] 測試 CI/CD 流程

### 驗收標準

```bash
# 1. 測試框架安裝檢查
pytest --version
# 應輸出: pytest 7.4.3

# 2. 目錄結構檢查
ls -R tests/

# 3. Fixtures 測試
pytest tests/conftest.py --collect-only
# 應列出所有 fixtures

# 4. 範例測試執行
pytest tests/ -v
# 應至少有一個測試通過 (即使是 placeholder)
```

---

## Week 2: 單元測試

### 目標
為 Services、Utilities、Agents 層撰寫單元測試，達成 50% 覆蓋率

### 任務清單

#### 2.1 Services 層測試 (5 個服務)

**2.1.1 test_ticket_service.py**
- [ ] `test_validate_uploaded_file_success()` - 驗證有效檔案
- [ ] `test_validate_uploaded_file_invalid_format()` - 驗證無效格式
- [ ] `test_validate_uploaded_file_too_large()` - 驗證檔案過大
- [ ] `test_process_uploaded_file_complete_flow()` - 完整處理流程
- [ ] `test_check_duplicate_tickets_high_rate()` - 重複率 ≥80%
- [ ] `test_check_duplicate_tickets_low_rate()` - 重複率 <80%

**測試範例**:
```python
def test_validate_uploaded_file_success(ticket_service, tmp_path):
    # Arrange
    file_path = tmp_path / "test.xlsx"
    # 創建有效 Excel 檔案

    # Act
    result = ticket_service.validate_uploaded_file(file_path)

    # Assert
    assert result["valid"] == True
    assert "error" not in result

def test_process_uploaded_file_complete_flow(
    ticket_service,
    mock_llm_response,
    sample_tickets_batch,
    mocker
):
    # Mock AI 呼叫
    mocker.patch('utils.ai_utils.call_llm', return_value=mock_llm_response)

    # Act
    result = ticket_service.process_uploaded_file("test.xlsx")

    # Assert
    assert result["status"] == "success"
    assert result["processed_count"] == 10
    assert result["duplicate_rate"] < 0.8
```

**2.1.2 test_risk_service.py**
- [ ] `test_calculate_risk_score_high_risk()` - 高風險工單
- [ ] `test_calculate_risk_score_low_risk()` - 低風險工單
- [ ] `test_determine_risk_level_dynamic_clustering()` - 動態聚類條件
- [ ] `test_determine_risk_level_fixed_threshold()` - 固定門檻
- [ ] `test_semantic_similarity_detection()` - 語意相似度 ≥0.7

**2.1.3 test_rag_service.py**
- [ ] `test_query_with_empty_history()` - 無歷史記錄查詢
- [ ] `test_query_with_10_rounds_history()` - 最多 10 輪歷史
- [ ] `test_query_history_truncation()` - 超過 10 輪截斷
- [ ] `test_create_session_valid_title()` - 有效標題 (<100 字)
- [ ] `test_create_session_invalid_title()` - 無效標題 (特殊字元)
- [ ] `test_list_sessions_pagination()` - 分頁查詢 (每頁 20 筆)

**2.1.4 test_cluster_service.py**
- [ ] `test_perform_clustering_rule_based()` - Rule-based 聚類
- [ ] `test_generate_cluster_name_truncation()` - 名稱截斷 (30 字)
- [ ] `test_generate_excel_report_color_coding()` - Excel 2 色交替

**2.1.5 test_kb_service.py**
- [ ] `test_sync_knowledge_base_with_lock()` - 檔案鎖檢查
- [ ] `test_sync_knowledge_base_backup_creation()` - 備份建立 (僅保留 1 個)
- [ ] `test_sync_knowledge_base_incremental_update()` - 增量更新
- [ ] `test_sync_knowledge_base_faiss_rebuild()` - FAISS 全量重建
- [ ] `test_check_kb_status()` - 狀態檢查

#### 2.2 Utilities 層測試 (4 個工具模組)

**2.2.1 test_ai_utils.py**
- [ ] `test_semantic_cache_hit()` - 快取命中 (相似度 ≥0.92)
- [ ] `test_semantic_cache_miss()` - 快取未命中
- [ ] `test_call_llm_power_automate_success()` - Power Automate 成功
- [ ] `test_call_llm_fallback_to_ollama()` - Fallback 至 Ollama
- [ ] `test_call_llm_all_failed()` - 所有 LLM 失敗
- [ ] `test_text_preprocessing()` - 文字前處理

**2.2.2 test_excel_utils.py**
- [ ] `test_read_excel_with_priority_columns()` - 欄位優先順序
- [ ] `test_read_excel_missing_required_columns()` - 缺少必要欄位
- [ ] `test_write_excel_with_color_coding()` - Excel 上色邏輯
- [ ] `test_close_excel_if_open()` - 關閉 Excel (COM)

**2.2.3 test_vector_utils.py**
- [ ] `test_text_to_embedding()` - 文字向量化 (384 維)
- [ ] `test_cosine_similarity()` - 餘弦相似度計算
- [ ] `test_batch_embedding()` - 批次向量化

**2.2.4 test_validation_utils.py**
- [ ] `test_validate_weight_sum_correct()` - 權重總和 = 1.0
- [ ] `test_validate_weight_sum_incorrect()` - 權重總和 ≠ 1.0
- [ ] `test_validate_session_title_valid()` - 有效標題
- [ ] `test_validate_session_title_invalid_chars()` - 特殊字元
- [ ] `test_validate_session_title_too_long()` - 超過 100 字

#### 2.3 Agents 層測試 (4 個 Agent)

**2.3.1 test_semantic_agent.py**
- [ ] `test_semantic_search_top_k()` - Top-K 檢索 (3-20)
- [ ] `test_cross_encoder_reranking()` - Cross-Encoder 重排序
- [ ] `test_recursive_summarization()` - 遞迴摘要 (大結果集)

**2.3.2 test_sql_agent.py**
- [ ] `test_nl_to_sql_simple_query()` - 簡單查詢
- [ ] `test_nl_to_sql_complex_query()` - 複雜查詢 (JOIN, GROUP BY)
- [ ] `test_sql_execution_with_pandas()` - Pandas 過濾

**2.3.3 test_hybrid_agent.py**
- [ ] `test_sql_then_semantic_pipeline()` - SQL → Semantic 鏈
- [ ] `test_semantic_then_sql_pipeline()` - Semantic → SQL 鏈

**2.3.4 test_followup_agent.py**
- [ ] `test_context_aware_query_refinement()` - 上下文感知

### 驗收標準

```bash
# 1. 執行所有單元測試
pytest tests/unit/ -v

# 2. 檢查覆蓋率
pytest tests/unit/ --cov=services --cov=utils --cov=agents --cov-report=term
# Services 層應 ≥50%

# 3. 測試報告
pytest tests/unit/ --html=report.html
open report.html

# 4. 達成 50% 總覆蓋率
pytest tests/ --cov=. --cov-report=term
# 總覆蓋率應 ≥50%
```

---

## Week 3: 整合測試與優化

### 目標
完成整合測試，達成 70% 總覆蓋率

### 任務清單

#### 3.1 API Endpoints 測試

**tests/integration/test_api_endpoints.py**
- [ ] `test_upload_endpoint_success()` - 上傳成功
- [ ] `test_upload_endpoint_invalid_file()` - 上傳失敗 (無效檔案)
- [ ] `test_chat_query_endpoint()` - RAG 查詢
- [ ] `test_chat_sessions_list()` - 會話列表 (分頁)
- [ ] `test_cluster_endpoint()` - 聚類分析
- [ ] `test_config_weight_update()` - 權重配置更新
- [ ] `test_history_list_endpoint()` - 歷史記錄列表

**測試範例**:
```python
def test_upload_endpoint_success(client, tmp_path):
    # Arrange
    file_path = tmp_path / "test.xlsx"
    # 創建測試 Excel 檔案

    # Act
    with open(file_path, 'rb') as f:
        response = client.post(
            '/api/upload/analyze',
            data={'file': f},
            content_type='multipart/form-data'
        )

    # Assert
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'success'
    assert 'task_id' in data
```

#### 3.2 RAG 多代理協作測試

**tests/integration/test_rag_system.py**
- [ ] `test_query_classifier_routing()` - 查詢分類路由
- [ ] `test_semantic_agent_full_flow()` - Semantic Agent 完整流程
- [ ] `test_sql_agent_full_flow()` - SQL Agent 完整流程
- [ ] `test_hybrid_agent_full_flow()` - Hybrid Agent 完整流程
- [ ] `test_followup_agent_context_handling()` - Follow-up Agent 上下文
- [ ] `test_llm_fallback_chain()` - LLM Fallback 鏈

**測試範例**:
```python
def test_semantic_agent_full_flow(rag_service, mock_faiss_index, mocker):
    # Mock FAISS 搜尋
    mocker.patch('repositories.faiss_repo.FAISSRepository.search',
                 return_value=[(0.1, 'INC001'), (0.2, 'INC002')])

    # Mock LLM 回應
    mocker.patch('utils.ai_utils.call_llm',
                 return_value={"response": "測試回應"})

    # Act
    result = rag_service.query("如何解決電腦無法開機問題?", session_id="test")

    # Assert
    assert result['status'] == 'success'
    assert '測試回應' in result['response']
    assert len(result['sources']) > 0
```

#### 3.3 知識庫同步流程測試

**tests/integration/test_kb_sync.py**
- [ ] `test_excel_to_sqlite_sync()` - Excel → SQLite 同步
- [ ] `test_sqlite_to_faiss_sync()` - SQLite → FAISS 同步
- [ ] `test_incremental_update_logic()` - 增量更新邏輯
- [ ] `test_backup_rotation()` - 備份輪替 (僅保留 1 個)
- [ ] `test_lock_file_mechanism()` - 檔案鎖機制

#### 3.4 工單處理完整流程測試

**tests/integration/test_ticket_processing.py**
- [ ] `test_upload_to_analysis_flow()` - 上傳 → 分析 → 儲存
- [ ] `test_duplicate_detection_flow()` - 重複檢測流程
- [ ] `test_risk_scoring_flow()` - 風險評分流程
- [ ] `test_clustering_flow()` - 聚類分析流程
- [ ] `test_excel_output_generation()` - Excel 輸出生成

#### 3.5 覆蓋率優化

**目標: 70% 總覆蓋率**

- [ ] 執行覆蓋率報告: `pytest --cov=. --cov-report=html`
- [ ] 識別未覆蓋程式碼:
  ```bash
  open htmlcov/index.html
  # 查看紅色標記的未覆蓋程式碼
  ```
- [ ] 針對性補充測試:
  - 邊界條件測試 (空輸入、極端值)
  - 錯誤處理測試 (例外情況)
  - 分支覆蓋測試 (if/else 分支)

**覆蓋率目標分配**:
| 模組 | 目標覆蓋率 | 當前覆蓋率 (預估) | 需補充測試 |
|------|-----------|------------------|-----------|
| Services 層 | 80% | 60% (Week 2) | +20% |
| Agents 層 | 80% | 55% (Week 2) | +25% |
| Repositories 層 | 70% | 40% (Week 2) | +30% |
| Utilities 層 | 70% | 60% (Week 2) | +10% |
| API 層 | 60% | 30% (Week 2) | +30% |

### 驗收標準

```bash
# 1. 執行所有整合測試
pytest tests/integration/ -v

# 2. 檢查總覆蓋率
pytest tests/ --cov=. --cov-report=html --cov-report=term
# 總覆蓋率應 ≥70%

# 3. 覆蓋率報告
open htmlcov/index.html
# 檢查各模組覆蓋率是否符合目標

# 4. CI/CD 測試
# (GitHub Actions) 推送至 GitHub,檢查 Actions 執行結果
# (本地腳本) 執行 run_tests.bat,確認全部通過
```

---

## Week 4 (可選): 效能優化

### 目標
識別並優化效能瓶頸

### 任務清單

#### 4.1 效能測試建立

**tests/performance/test_bottlenecks.py**
- [ ] `test_ticket_processing_time()` - 100 筆工單處理時間
- [ ] `test_embedding_calculation_time()` - 1000 筆向量化時間
- [ ] `test_faiss_search_time()` - FAISS 搜尋時間
- [ ] `test_llm_call_time()` - LLM 呼叫時間 (Power Automate vs Ollama)
- [ ] `test_excel_read_write_time()` - Excel 讀寫時間 (win32com vs openpyxl)

**效能基準**:
| 操作 | 當前效能 | 目標效能 | 優化方向 |
|------|---------|---------|---------|
| 100 筆工單分析 | ~10 分鐘 | <5 分鐘 | 並發處理、快取 |
| FAISS 搜尋 (1000 筆) | <100ms | 保持 | 已達標 |
| Embedding (1000 筆) | ~10 秒 | <5 秒 | GPU 加速 (可選) |
| LLM 呼叫 (單次) | 1-3 秒 | <1 秒 | 快取、批次處理 |
| Excel 讀寫 (100 筆) | ~50 秒 | <10 秒 | 遷移至 openpyxl |

#### 4.2 效能瓶頸識別

**使用 cProfile**:
```python
import cProfile
import pstats

# 分析工單處理流程
profiler = cProfile.Profile()
profiler.enable()

# 執行工單處理
ticket_service.process_uploaded_file("test.xlsx")

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)  # 列出前 20 個最耗時函數
```

- [ ] 分析工單處理流程
- [ ] 分析知識庫同步流程
- [ ] 分析 RAG 查詢流程
- [ ] 識別 Top 3 瓶頸函數

#### 4.3 優化實作

**優化 1: LLM 快取命中率提升**
- [ ] 調整語意快取相似度閾值 (0.92 → 0.90)
- [ ] 增加快取容量 (3000 → 5000)
- [ ] 實作快取預熱 (常見查詢)

**優化 2: Embedding 批次處理**
- [ ] 實作批次向量化 (batch_size=32)
- [ ] 使用 GPU 加速 (若有 CUDA 環境)

**優化 3: Excel 讀寫優化**
- [ ] 評估 openpyxl 替代 win32com:
  ```python
  # 效能比較測試
  def benchmark_excel_libraries():
      # win32com
      start = time.time()
      read_excel_win32com("test.xlsx")
      win32com_time = time.time() - start

      # openpyxl
      start = time.time()
      read_excel_openpyxl("test.xlsx")
      openpyxl_time = time.time() - start

      print(f"win32com: {win32com_time:.2f}s")
      print(f"openpyxl: {openpyxl_time:.2f}s")
      print(f"Speedup: {win32com_time / openpyxl_time:.2f}x")
  ```
- [ ] 若 openpyxl 快 5 倍以上,遷移至 openpyxl (Phase 3)

**優化 4: FAISS 索引優化 (可選)**
- [ ] 評估 IndexIVFFlat (需 ≥10K 資料)
- [ ] 評估 GPU 版本 FAISS (需 CUDA)

#### 4.4 效能監控儀表板 (可選)

**實作簡單效能監控**:
```python
# core/performance_monitor.py
import time
from functools import wraps

def monitor_performance(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start

        # 記錄到日誌或資料庫
        log_performance(func.__name__, elapsed)

        return result
    return wrapper

# 使用範例
@monitor_performance
def process_uploaded_file(file_path):
    # ...
```

- [ ] 實作效能裝飾器
- [ ] 為關鍵函數添加監控
- [ ] 產生效能報表 (CSV 或圖表)

### 驗收標準

```bash
# 1. 執行效能測試
pytest tests/performance/ -v --durations=10

# 2. 檢查效能基準
# 100 筆工單處理應 <5 分鐘 (優化後)

# 3. 效能報表
python -c "from core.performance_monitor import generate_report; generate_report()"
# 應產生效能分析報表

# 4. 瓶頸識別報告
python -c "
import cProfile
# ... (執行分析)
"
# 應識別 Top 3 瓶頸函數
```

---

## 交付物

### 必須完成

1. ✅ **測試框架**
   - pytest 配置完成
   - conftest.py (共用 fixtures)
   - CI/CD 自動化測試

2. ✅ **測試覆蓋率 70%**
   - Services 層 ≥80%
   - Agents 層 ≥80%
   - Repositories 層 ≥70%
   - Utilities 層 ≥70%
   - API 層 ≥60%

3. ✅ **整合測試**
   - API Endpoints 測試
   - RAG 系統測試
   - 知識庫同步測試
   - 工單處理流程測試

### 可選完成

- ⚠️ **效能優化** (Week 4)
  - 效能瓶頸識別報告
  - LLM 快取優化
  - Embedding 批次處理
  - Excel 讀寫優化

- ⚠️ **E2E 測試** (可延後至 Phase 3)
  - Selenium 自動化測試
  - 使用者工作流程測試

---

## 風險與緩解

### 風險 1: 測試撰寫耗時超出預期
**緩解**:
- 優先撰寫 Services 層測試 (核心業務邏輯)
- 降低覆蓋率目標至 60% (最低可接受標準)
- 延後 E2E 測試至 Phase 3

### 風險 2: Mock 依賴複雜度高
**緩解**:
- 使用 `pytest-mock` 簡化 Mock 邏輯
- 為常用 Mock 建立 conftest.py fixtures
- 參考 pytest 官方文件範例

### 風險 3: CI/CD 設定困難
**緩解**:
- 優先使用本地腳本 (run_tests.bat)
- GitHub Actions 可延後至 Phase 3 設定

### 風險 4: 效能優化效果不明顯
**緩解**:
- 聚焦於高投資報酬率優化 (LLM 快取、Excel 讀寫)
- 低效益優化 (GPU 加速) 延後至未來需求明確時

---

## 下一階段

完成 Phase 2 後，進入 **Phase 3: 增強功能**
- 實作待規格化功能 (會話列表分頁、刪除確認等)
- 實作進階功能 (任務佇列、跨平台支援等)
- 持續優化效能與使用者體驗
