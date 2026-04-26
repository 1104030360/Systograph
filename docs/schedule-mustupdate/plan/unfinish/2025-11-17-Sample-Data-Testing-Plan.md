# 假資料端到端測試計劃

**建立日期**: 2025-11-17
**目標**: 使用真實假資料 (sample_incident_10.xlsx) 建立完整的端到端測試
**優先級**: P2 - 重要
**預估時間**: 6-8 小時

---

## 📋 執行摘要

### 目標
使用 `test-docs/sample_incident_10.xlsx` 假資料建立完整的端到端測試，驗證從上傳分析到資料庫存儲的完整流程。

### 範圍
1. **上傳分析流程**：Excel 上傳 → 驗證 → 分析 → 結果產出
2. **資料庫操作**：分析結果 → SQLite 存儲 → FAISS 索引建立
3. **查詢驗證**：資料庫查詢 → FAISS 搜尋 → 結果正確性驗證
4. **端到端整合**：完整流程串接測試

### 現狀分析

#### 假資料資訊
**檔案**: `test-docs/sample_incident_10.xlsx`
- **資料筆數**: 10 筆工單
- **欄位數量**: 11 個
- **欄位內容**:
  ```
  - Incident number (工單編號)
  - Configuration item (配置項目)
  - Role/Component (角色/組件)
  - Subcategory (子類別)
  - Short description (簡短描述)
  - Description (詳細描述)
  - Work note (工作註記)
  - Close notes (結案註記)
  - Opened (開啟時間)
  - Caller (報案人)
  - Location (地點)
  ```

#### 資料庫結構
**表名**: `metadata`
- **主鍵**: `internalId` (自動遞增)
- **唯一鍵**: `id` (工單編號)
- **關鍵欄位**:
  ```
  - id TEXT UNIQUE (對應 Incident number)
  - text TEXT (綜合描述文本)
  - subcategory TEXT (對應 Subcategory)
  - configurationItem TEXT (對應 Configuration item)
  - roleComponent TEXT (對應 Role/Component)
  - location TEXT (對應 Location)
  - opened TEXT (對應 Opened)
  - analysisTime TEXT (分析時間戳)
  - solution TEXT (解決方案，從 Close notes 或 Work note)
  ```

#### 現有測試覆蓋
**✅ 已覆蓋**:
- `/api/v2/preview` - Mock 測試
- `/api/v2/upload` - Mock 測試（沒有真實資料）
- `/api/v2/progress` - Mock 測試
- TicketService 單元測試 - Mock 測試

**❌ 未覆蓋** (本次計劃重點):
- 使用真實 Excel 檔案的端到端測試
- 資料庫實際寫入驗證
- FAISS 索引建立驗證
- 完整工作流程整合測試

### 代辦事項（2025-11-17 補充）
- [ ] 建立「測試資料重設」流程：執行測試前移除或備份 `resultDB.db`、`kb_index.faiss`、`kb_texts.pkl` 等測試產物，測試後清理暫存檔，確保每輪皆從乾淨狀態開始。
- [ ] 所有需讀取資料的測試一律使用 `test-docs/sample_incident_10.xlsx`，不得以 mock Excel 內容取代，必要時僅允許 mock 外部 API（如 GPT、Power Automate）。
- [ ] 在 Phase 1 fixture 設計中加入「sample Excel 複製到臨時目錄」與「測試結束後刪除臨時 DB/FAISS」步驟，將上述流程自動化。

---

## 🎯 測試計劃

### Phase 1: 測試基礎建設（2 小時）

#### 1.1 建立測試 Fixture
**檔案**: `tests/conftest.py`（擴充）

**任務**:
- [x] 創建 `sample_excel_file` fixture
  - 讀取 `test-docs/sample_incident_10.xlsx`
  - 提供給所有測試使用

- [x] 創建 `temp_db` fixture
  - 建立臨時測試資料庫
  - 測試後自動清理

- [x] 創建 `faiss_test_env` fixture
  - 建立臨時 FAISS 索引環境
  - 測試後自動清理

> **Note**：`sample_excel_file` fixture 需於測試開始時將 `test-docs/sample_incident_10.xlsx` 複製到 pytest 的暫存目錄中供各測試使用，測試結束後刪除相關臨時檔，以確保「重設測試資料」流程自動化且不依賴 mock Excel 資料。

**範例代碼**:
```python
@pytest.fixture
def sample_excel_file():
    """提供假資料 Excel 檔案路徑"""
    file_path = "test-docs/sample_incident_10.xlsx"
    if not os.path.exists(file_path):
        pytest.skip(f"Sample file not found: {file_path}")
    return file_path

@pytest.fixture
def temp_db(tmp_path):
    """建立臨時測試資料庫"""
    db_path = tmp_path / "test_resultDB.db"
    conn = sqlite3.connect(str(db_path))

    # 建立 metadata 表
    conn.execute('''
        CREATE TABLE metadata (
            internalId INTEGER PRIMARY KEY AUTOINCREMENT,
            id TEXT UNIQUE,
            text TEXT,
            subcategory TEXT,
            configurationItem TEXT,
            roleComponent TEXT,
            location TEXT,
            opened TEXT,
            analysisTime TEXT,
            solution TEXT
        )
    ''')
    conn.commit()

    yield str(db_path)

    conn.close()
    if db_path.exists():
        db_path.unlink()

@pytest.fixture
def faiss_test_env(tmp_path):
    """建立臨時 FAISS 測試環境"""
    faiss_dir = tmp_path / "faiss_test"
    faiss_dir.mkdir()

    yield {
        "index_path": str(faiss_dir / "kb_index.faiss"),
        "texts_path": str(faiss_dir / "kb_texts.pkl"),
        "metadata_path": str(faiss_dir / "kb_metadata.json")
    }

    # 清理
    import shutil
    if faiss_dir.exists():
        shutil.rmtree(faiss_dir)
```

#### 1.2 建立測試輔助函數
**檔案**: `tests/helpers/data_helpers.py`（新建）

**任務**:
- [x] `load_sample_data(excel_path)` - 載入並驗證假資料
- [x] `verify_db_record(db_path, incident_id)` - 驗證資料庫記錄
- [x] `verify_faiss_index(index_path, expected_count)` - 驗證 FAISS 索引

**範例代碼**:
```python
def load_sample_data(excel_path: str) -> pd.DataFrame:
    """載入假資料並返回 DataFrame"""
    df = pd.read_excel(excel_path)
    assert len(df) == 10, f"Expected 10 records, got {len(df)}"
    assert 'Incident number' in df.columns
    return df

def verify_db_record(db_path: str, incident_id: str) -> dict:
    """驗證資料庫中的記錄存在且正確"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM metadata WHERE id = ?", (incident_id,))
    row = cursor.fetchone()
    conn.close()

    assert row is not None, f"Record {incident_id} not found in database"

    # 返回欄位對應字典
    columns = ['internalId', 'id', 'text', 'subcategory',
               'configurationItem', 'roleComponent', 'location',
               'opened', 'analysisTime', 'solution']
    return dict(zip(columns, row))

def verify_faiss_index(index_path: str, expected_count: int):
    """驗證 FAISS 索引正確建立"""
    import faiss
    assert os.path.exists(index_path), f"FAISS index not found: {index_path}"

    index = faiss.read_index(index_path)
    actual_count = index.ntotal
    assert actual_count == expected_count, \
        f"Expected {expected_count} vectors, got {actual_count}"
```

---

### Phase 2: 上傳分析測試（2 小時）

#### 2.1 Excel 預覽測試
**檔案**: `tests/integration/test_upload_sample_data.py`（新建）

**測試案例**:
```python
def test_preview_sample_excel(client, sample_excel_file):
    """測試預覽假資料 Excel 檔案"""

    with open(sample_excel_file, 'rb') as f:
        data = {'file': (f, 'sample_incident_10.xlsx')}
        response = client.post('/api/v2/preview',
                              data=data,
                              content_type='multipart/form-data')

    assert response.status_code == 200
    result = response.get_json()

    # 驗證回應結構
    assert 'columns' in result
    assert 'rows' in result

    # 驗證欄位
    expected_columns = ['Incident number', 'Configuration item',
                       'Role/Component', 'Subcategory', ...]
    for col in expected_columns:
        assert col in result['columns']

    # 驗證資料筆數（預覽最多 50 筆）
    assert len(result['rows']) == 10  # 只有 10 筆資料
```

#### 2.2 完整上傳分析測試
**測試案例**:
```python
@pytest.mark.integration
def test_upload_and_analyze_sample_data(client, sample_excel_file, temp_db, monkeypatch):
    """測試完整上傳分析流程（使用真實假資料）"""

    # Mock 資料庫路徑指向臨時資料庫
    monkeypatch.setattr('build_kb.SQLITE_DB', temp_db)

    with open(sample_excel_file, 'rb') as f:
        data = {
            'file': (f, 'sample_incident_10.xlsx'),
            'weights': json.dumps({
                'severity_weight': 0.6,
                'frequency_weight': 0.4
            }),
            'resolution_priority': json.dumps(['Close notes', 'Work note']),
            'summary_priority': json.dumps(['Short description', 'Description'])
        }

        response = client.post('/api/v2/upload',
                              data=data,
                              content_type='multipart/form-data')

    # 驗證 API 回應
    assert response.status_code == 200
    result = response.get_json()

    assert 'analysis_results' in result or 'status' in result
    assert result.get('status') != 'error'

    # 驗證分析結果數量
    if 'analysis_results' in result:
        assert len(result['analysis_results']) == 10
```

#### 2.3 進度追蹤測試
**測試案例**:
```python
def test_progress_tracking_during_upload(client, sample_excel_file):
    """測試上傳過程中的進度追蹤"""

    import threading
    import time

    progress_values = []

    def check_progress():
        """在背景持續檢查進度"""
        for _ in range(10):
            response = client.get('/api/v2/progress')
            if response.status_code == 200:
                data = response.get_json()
                progress_values.append(data.get('percentage', 0))
            time.sleep(0.5)

    # 啟動進度檢查執行緒
    progress_thread = threading.Thread(target=check_progress)
    progress_thread.start()

    # 執行上傳
    with open(sample_excel_file, 'rb') as f:
        data = {'file': (f, 'sample_incident_10.xlsx')}
        response = client.post('/api/v2/upload',
                              data=data,
                              content_type='multipart/form-data')

    progress_thread.join()

    # 驗證進度有變化
    assert len(progress_values) > 0
    assert any(p > 0 for p in progress_values)
```

---

### Phase 3: 資料庫操作測試（2 小時）

#### 3.1 資料庫寫入驗證
**檔案**: `tests/integration/test_db_operations.py`（新建）

**測試案例**:
```python
@pytest.mark.integration
def test_sample_data_written_to_db(sample_excel_file, temp_db):
    """驗證假資料正確寫入資料庫"""

    from services.ticket_service import TicketService
    from build_kb import sync_excel_to_sqlite

    # 模擬上傳並分析（簡化版）
    df = pd.read_excel(sample_excel_file)

    # 將資料寫入資料庫（使用實際的同步函數）
    sync_excel_to_sqlite(sample_excel_file, temp_db)

    # 驗證資料庫
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()

    # 檢查總筆數
    cursor.execute("SELECT COUNT(*) FROM metadata")
    count = cursor.fetchone()[0]
    assert count == 10, f"Expected 10 records, got {count}"

    # 檢查第一筆資料
    cursor.execute("SELECT * FROM metadata WHERE id = 'INC20000'")
    row = cursor.fetchone()
    assert row is not None, "First record not found"

    # 驗證欄位內容
    columns = ['internalId', 'id', 'text', 'subcategory',
               'configurationItem', 'roleComponent', 'location',
               'opened', 'analysisTime', 'solution']
    record = dict(zip(columns, row))

    assert record['id'] == 'INC20000'
    assert record['configurationItem'] == 'Mail-Server'
    assert record['subcategory'] == 'Queue Stuck'
    assert record['location'] == 'TAIPEI C2'

    conn.close()

def test_all_sample_records_in_db(temp_db, sample_excel_file):
    """驗證所有假資料記錄都在資料庫中"""

    df = load_sample_data(sample_excel_file)

    # 假設資料已寫入
    sync_excel_to_sqlite(sample_excel_file, temp_db)

    conn = sqlite3.connect(temp_db)

    for idx, row in df.iterrows():
        incident_id = row['Incident number']

        # 驗證每筆記錄
        db_record = verify_db_record(temp_db, incident_id)

        # 驗證關鍵欄位
        assert db_record['id'] == incident_id
        assert db_record['configurationItem'] == row['Configuration item']
        assert db_record['subcategory'] == row['Subcategory']
        assert db_record['location'] == row['Location']

    conn.close()

def test_db_text_field_generation(temp_db, sample_excel_file):
    """驗證資料庫 text 欄位正確生成（組合多個描述欄位）"""

    sync_excel_to_sqlite(sample_excel_file, temp_db)

    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()

    cursor.execute("SELECT id, text FROM metadata WHERE id = 'INC20000'")
    row = cursor.fetchone()

    assert row is not None
    incident_id, text = row

    # text 欄位應包含：Short description, Description, Work note 等
    assert '系統延遲' in text  # Short description
    assert 'VPN 憑證過期' in text  # Description

    conn.close()
```

#### 3.2 重複資料檢測測試
**測試案例**:
```python
def test_duplicate_detection(temp_db, sample_excel_file):
    """測試重複上傳檢測"""

    # 第一次寫入
    sync_excel_to_sqlite(sample_excel_file, temp_db)

    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM metadata")
    count_first = cursor.fetchone()[0]

    # 第二次寫入（應該不會重複）
    sync_excel_to_sqlite(sample_excel_file, temp_db)

    cursor.execute("SELECT COUNT(*) FROM metadata")
    count_second = cursor.fetchone()[0]

    # 資料筆數應該相同（因為 id 是 UNIQUE）
    assert count_first == count_second == 10

    conn.close()
```

---

### Phase 4: FAISS 索引測試（1.5 小時）

#### 4.1 FAISS 索引建立測試
**檔案**: `tests/integration/test_faiss_with_sample_data.py`（新建）

**測試案例**:
```python
@pytest.mark.integration
def test_faiss_index_creation_from_sample_data(temp_db, sample_excel_file, faiss_test_env):
    """測試從假資料建立 FAISS 索引"""

    from build_kb import sync_faiss_with_sqlite

    # 先將資料寫入資料庫
    sync_excel_to_sqlite(sample_excel_file, temp_db)

    # 建立 FAISS 索引
    with patch('build_kb.KB_INDEX', faiss_test_env['index_path']):
        with patch('build_kb.KB_TEXTS', faiss_test_env['texts_path']):
            sync_faiss_with_sqlite(temp_db)

    # 驗證索引檔案建立
    assert os.path.exists(faiss_test_env['index_path'])
    assert os.path.exists(faiss_test_env['texts_path'])

    # 驗證索引內容
    verify_faiss_index(faiss_test_env['index_path'], expected_count=10)

    # 驗證 texts 內容
    with open(faiss_test_env['texts_path'], 'rb') as f:
        texts = pickle.load(f)
    assert len(texts) == 10

def test_faiss_search_sample_data(temp_db, sample_excel_file, faiss_test_env):
    """測試使用 FAISS 搜尋假資料"""

    from sentence_transformers import SentenceTransformer

    # 建立索引（與上個測試相同的準備步驟）
    sync_excel_to_sqlite(sample_excel_file, temp_db)

    with patch('build_kb.KB_INDEX', faiss_test_env['index_path']):
        with patch('build_kb.KB_TEXTS', faiss_test_env['texts_path']):
            sync_faiss_with_sqlite(temp_db)

    # 載入索引和模型
    index = faiss.read_index(faiss_test_env['index_path'])
    model = SentenceTransformer('all-MiniLM-L6-v2')

    # 搜尋測試：查詢「VPN 憑證」
    query = "VPN 憑證問題"
    query_embedding = model.encode([query])

    distances, indices = index.search(query_embedding, k=3)

    # 驗證搜尋結果
    assert len(indices[0]) == 3
    assert all(idx >= 0 for idx in indices[0])  # 有找到結果

    # 載入 texts 驗證結果相關性
    with open(faiss_test_env['texts_path'], 'rb') as f:
        texts = pickle.load(f)

    top_result = texts[indices[0][0]]
    assert 'VPN' in top_result or '憑證' in top_result
```

---

### Phase 5: 端到端整合測試（2.5 小時）

#### 5.1 完整工作流程測試
**檔案**: `tests/integration/test_e2e_sample_workflow.py`（新建）

**測試案例**:
```python
@pytest.mark.e2e
@pytest.mark.slow
def test_complete_workflow_with_sample_data(
    client,
    sample_excel_file,
    temp_db,
    faiss_test_env,
    monkeypatch
):
    """
    端到端測試：上傳 → 分析 → 資料庫 → FAISS → 查詢

    完整模擬使用者工作流程：
    1. 上傳 sample_incident_10.xlsx
    2. 系統分析並生成結果
    3. 資料寫入 SQLite
    4. 建立 FAISS 索引
    5. 使用 RAG 查詢驗證
    """

    # 設定臨時環境
    monkeypatch.setattr('build_kb.SQLITE_DB', temp_db)
    monkeypatch.setattr('build_kb.KB_INDEX', faiss_test_env['index_path'])
    monkeypatch.setattr('build_kb.KB_TEXTS', faiss_test_env['texts_path'])

    # ===== Step 1: 上傳檔案 =====
    with open(sample_excel_file, 'rb') as f:
        upload_data = {
            'file': (f, 'sample_incident_10.xlsx'),
            'weights': json.dumps({'severity_weight': 0.6, 'frequency_weight': 0.4}),
            'resolution_priority': json.dumps(['Close notes']),
            'summary_priority': json.dumps(['Short description'])
        }

        upload_response = client.post('/api/v2/upload',
                                     data=upload_data,
                                     content_type='multipart/form-data')

    assert upload_response.status_code == 200
    upload_result = upload_response.get_json()
    assert upload_result.get('status') != 'error'

    # ===== Step 2: 驗證資料庫寫入 =====
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM metadata")
    db_count = cursor.fetchone()[0]
    assert db_count == 10, f"Expected 10 records in DB, got {db_count}"
    conn.close()

    # ===== Step 3: 建立 FAISS 索引 =====
    from build_kb import sync_faiss_with_sqlite
    sync_faiss_with_sqlite(temp_db)

    assert os.path.exists(faiss_test_env['index_path'])
    verify_faiss_index(faiss_test_env['index_path'], expected_count=10)

    # ===== Step 4: RAG 查詢測試 =====
    # 模擬使用者查詢「郵件系統問題」
    chat_data = {
        'user_id': 'test_user',
        'query': '郵件系統相關問題',
        'model': 'gpt-4'
    }

    chat_response = client.post('/api/v2/chat',
                               data=json.dumps(chat_data),
                               content_type='application/json')

    assert chat_response.status_code == 200
    chat_result = chat_response.get_json()

    # 驗證查詢結果包含相關工單
    assert 'answer' in chat_result or 'response' in chat_result

    # ===== Step 5: 驗證搜尋結果相關性 =====
    # 查詢應該找到 INC20000 (Mail-Server 相關)
    # 這需要根據實際 RAG 回應格式調整驗證邏輯

def test_workflow_error_handling(client, monkeypatch):
    """測試工作流程中的錯誤處理"""

    # 測試上傳無效檔案
    invalid_data = {'file': (BytesIO(b'invalid'), 'test.txt')}
    response = client.post('/api/v2/upload',
                          data=invalid_data,
                          content_type='multipart/form-data')

    assert response.status_code in [400, 500]
    assert 'error' in response.get_json() or 'code' in response.get_json()

def test_workflow_with_progress_monitoring(client, sample_excel_file):
    """測試帶進度監控的完整工作流程"""

    import time
    from concurrent.futures import ThreadPoolExecutor

    progress_snapshots = []

    def monitor_progress():
        """背景監控進度"""
        for _ in range(20):
            response = client.get('/api/v2/progress')
            if response.status_code == 200:
                data = response.get_json()
                progress_snapshots.append({
                    'percentage': data.get('percentage', 0),
                    'message': data.get('progress', ''),
                    'timestamp': time.time()
                })
            time.sleep(0.3)

    # 啟動進度監控
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(monitor_progress)

        # 執行上傳
        with open(sample_excel_file, 'rb') as f:
            data = {'file': (f, 'sample_incident_10.xlsx')}
            response = client.post('/api/v2/upload',
                                  data=data,
                                  content_type='multipart/form-data')

        assert response.status_code == 200

        future.result()  # 等待監控完成

    # 驗證進度有持續更新
    assert len(progress_snapshots) > 0
    percentages = [s['percentage'] for s in progress_snapshots]
    assert any(p > 0 for p in percentages)
```

---

## 📊 測試覆蓋矩陣

### 功能覆蓋

| 功能模組 | 單元測試 | 整合測試 | E2E測試 | 使用假資料 |
|---------|---------|---------|---------|-----------|
| 檔案上傳 | ✅ | ✅ | ✅ | ✅ |
| Excel 預覽 | ✅ | ✅ | ✅ | ✅ |
| 資料驗證 | ✅ | ✅ | ✅ | ✅ |
| 分析處理 | ✅ | ⚠️ | ✅ | ✅ |
| 風險評分 | ✅ | ❌ | ⚠️ | ⚠️ |
| 資料庫寫入 | ⚠️ | ❌ | ✅ | ✅ |
| FAISS 索引 | ⚠️ | ❌ | ✅ | ✅ |
| RAG 查詢 | ✅ | ✅ | ✅ | ⚠️ |
| 進度追蹤 | ✅ | ⚠️ | ✅ | ✅ |

**圖例**:
- ✅ 已完整覆蓋
- ⚠️ 部分覆蓋
- ❌ 未覆蓋（本次計劃重點）

### 資料流覆蓋

```
假資料 Excel
    ↓ [✅ 預覽測試]
檔案驗證
    ↓ [✅ 上傳測試]
分析處理
    ├─ [✅ 風險評分測試]
    ├─ [✅ 去重檢測測試]
    └─ [✅ 結果產出測試]
    ↓ [❌ 資料庫寫入測試] ← 本次重點
SQLite 資料庫
    ├─ [❌ 查詢測試] ← 本次重點
    └─ [❌ 完整性測試] ← 本次重點
    ↓ [❌ FAISS 建立測試] ← 本次重點
FAISS 索引
    ├─ [❌ 搜尋測試] ← 本次重點
    └─ [❌ 相關性測試] ← 本次重點
    ↓ [⚠️ RAG 整合測試]
查詢結果
```

---

## 🛠️ 實作細節

### 檔案結構

```
tests/
├── conftest.py                          # [擴充] 新增 fixtures
├── helpers/
│   └── data_helpers.py                  # [新建] 資料驗證輔助函數
├── integration/
│   ├── test_upload_sample_data.py      # [新建] 上傳測試（真實資料）
│   ├── test_db_operations.py           # [新建] 資料庫操作測試
│   ├── test_faiss_with_sample_data.py  # [新建] FAISS 索引測試
│   └── test_e2e_sample_workflow.py     # [新建] 端到端工作流程測試
└── fixtures/
    └── sample_data_fixtures.py          # [新建] 假資料專用 fixtures

test-docs/
└── sample_incident_10.xlsx              # [現有] 假資料檔案
```

### 測試命名規範

**命名格式**: `test_<功能>_<場景>_<預期結果>`

**範例**:
- `test_upload_sample_data_success` - 成功上傳假資料
- `test_db_write_sample_records_all_present` - 所有假資料記錄寫入資料庫
- `test_faiss_search_sample_query_relevant_results` - FAISS 搜尋返回相關結果

### Mock vs Real Data 策略

**使用 Mock**:
- 外部 API 呼叫（Power Automate、Ollama）
- 耗時操作（大型模型載入）
- 不穩定服務（網路請求）

**使用真實資料**:
- 檔案讀取（sample_incident_10.xlsx）
- 資料庫操作（臨時 SQLite）
- FAISS 索引（臨時索引檔案）
- 資料處理邏輯（pandas、numpy）

---

## 🔍 驗證檢查清單

### Phase 1 驗證 ✅
- [ ] `sample_excel_file` fixture 可正確讀取假資料
- [ ] `temp_db` fixture 可建立臨時資料庫
- [ ] `faiss_test_env` fixture 可建立臨時 FAISS 環境
- [ ] `data_helpers.py` 所有輔助函數正常運作

### Phase 2 驗證 ✅
- [ ] 預覽測試：回傳 10 筆資料，欄位正確
- [ ] 上傳測試：API 回應 200，無錯誤
- [ ] 進度測試：進度百分比從 0 增加到 100

### Phase 3 驗證 ✅
- [ ] 資料庫寫入：10 筆記錄全部存在
- [ ] 欄位對應：Incident number → id, Configuration item → configurationItem
- [ ] text 欄位：組合 Short description + Description + Work note
- [ ] 重複檢測：相同資料不會重複寫入

### Phase 4 驗證 ✅
- [ ] FAISS 索引：包含 10 個向量
- [ ] texts.pkl：包含 10 段文本
- [ ] 搜尋功能：查詢「VPN」找到 INC20000

### Phase 5 驗證 ✅
- [ ] E2E 流程：上傳 → DB → FAISS → 查詢全程無錯誤
- [ ] 進度監控：整個流程中進度正常更新
- [ ] 錯誤處理：無效檔案返回適當錯誤訊息

---

## ⏱️ 時程規劃

### Week 1: 基礎建設 + 上傳測試（3 天）
- **Day 1**: Phase 1（測試基礎建設）
  - 建立 fixtures
  - 建立輔助函數
  - 驗證測試環境

- **Day 2**: Phase 2（上傳分析測試）
  - Excel 預覽測試
  - 完整上傳測試
  - 進度追蹤測試

- **Day 3**: Code Review + 文檔
  - 審查測試代碼
  - 撰寫測試文檔
  - 修正發現的問題

### Week 2: 資料庫 + FAISS 測試（3 天）
- **Day 4**: Phase 3（資料庫操作測試）
  - 資料庫寫入驗證
  - 重複資料檢測
  - 查詢功能測試

- **Day 5**: Phase 4（FAISS 索引測試）
  - 索引建立測試
  - 搜尋功能測試
  - 相關性驗證

- **Day 6**: Phase 5（端到端整合測試）
  - 完整工作流程測試
  - 進度監控測試
  - 錯誤處理測試

### Week 3: 優化 + 文檔（2 天）
- **Day 7**: 測試優化
  - 提升測試覆蓋率
  - 優化測試執行速度
  - 加入參數化測試

- **Day 8**: 文檔完善
  - 更新測試文檔
  - 撰寫測試報告
  - 建立測試維護指南

---

## 📈 成功指標

### 量化指標
- [ ] 測試覆蓋率 ≥ 95%（包含假資料路徑）
- [ ] 所有 5 個 Phase 的測試全部通過
- [ ] E2E 測試執行時間 < 30 秒
- [ ] 零資料庫殘留（測試後自動清理）

### 質化指標
- [ ] 測試代碼清晰易懂
- [ ] 錯誤訊息具有可操作性
- [ ] 測試獨立可重複執行
- [ ] 文檔完整適合新手學習

### 📊 覆蓋率目標說明（為何同時有 70% 與 95%）

#### Phase 2（整體專案）
- 範圍：全部層級（API 8 個、Services 8 個、Agents 4 個、Utils 11 個、Core 7 個、Repositories 5 個，合計約 15,500 行）。
- 目標：≥70%（整體品質門檻），實際已達 92%，測試數量 1,001 個，顯示「廣度」已覆蓋。

#### 假資料測試計劃（特定端到端路徑）
- 範圍：`Excel 上傳 → 檔案驗證 → 分析處理 → SQLite 寫入 → FAISS 建立 → FAISS 搜尋 → RAG 查詢`，約 2,000 行核心路徑。
- 現況：真實資料僅覆蓋 2/6 步驟（約 33%），其餘僅有 Mock 測試，無法驗證實際整合。
- 目標：路徑覆蓋率提升至 ≥95%，確保這條高風險流程被真實資料驗證。

#### 為什麼不是 100%
- 允許 5% 未覆蓋區塊：外部 API（Power Automate/Ollama/SharePoint，約 2%）、極端錯誤案例（記憶體/磁碟/網路，約 2%）、平台特定 code（Windows 專屬邏輯，約 1%）。
- 95% 已涵蓋所有重要步驟；追求 100% 需大量 Mock/平台差異處理，邊際效益低且維護成本高。

#### 覆蓋率對照表
| 指標 | Phase 2（整體專案） | 假資料測試計劃 |
| --- | --- | --- |
| 目標 | ≥70% | ≥95% |
| 實際 | 92% | ⏳ 進行中 |
| 範圍 | 全專案（15,500 行） | 特定路徑（約 2,000 行） |
| 測試類型 | 單元 + 整合（多為 Mock） | E2E（真實資料） |
| 測試數量 | 1,001 個 | 預計新增 50~80 個 |
| 重點 | 廣度：全部模組 | 深度：上傳→DB→FAISS 全流程 |

> **結論**：70%（實際 92%）代表專案「廣度」合格，95% 則針對假資料工作流程補齊真實資料驗證「深度」，兩者互補、不衝突。

---

## 🚨 風險與緩解

### 風險 1: 假資料與實際資料格式不一致
**影響**: 測試通過但實際使用失敗
**緩解**:
- 使用從實際系統匯出的假資料
- 定期更新假資料格式
- 加入格式驗證測試

### 風險 2: 測試環境與生產環境差異
**影響**: 測試環境通過但生產環境失敗
**緩解**:
- 使用與生產相同的依賴版本
- 模擬生產環境的檔案路徑
- 加入環境差異檢測

### 風險 3: 測試資料清理不完全
**影響**: 測試之間互相干擾
**緩解**:
- 使用 pytest fixtures 的自動清理
- 每個測試使用獨立的臨時目錄
- 加入測試前後的清理驗證

### 風險 4: FAISS 索引建立耗時
**影響**: 測試執行過慢
**緩解**:
- 使用小規模假資料（10 筆）
- 快取模型載入
- 使用 pytest-xdist 並行執行

---

## 📚 參考資源

### 相關文檔
- `CLAUDE.md` - 專案架構說明
- `tests/README.md` - 測試執行指南
- `backend-arch.md` - 後端架構文檔

### 相關代碼
- `api/upload_routes.py` - 上傳路由
- `services/ticket_service.py` - 工單服務
- `build_kb.py` - 知識庫建立
- `tests/conftest.py` - 現有 fixtures

### 相關測試
- `tests/unit/services/test_ticket_service.py` - 工單服務單元測試
- `tests/integration/test_upload_routes.py` - 上傳路由整合測試
- `tests/integration/test_complete_workflow.py` - 完整工作流程測試

---

## ✅ 執行檢查清單

### 開始前
- [ ] 確認 `test-docs/sample_incident_10.xlsx` 存在
- [ ] 確認 Python 虛擬環境啟動
- [ ] 確認所有依賴已安裝（pytest, pandas, faiss-cpu 等）
- [ ] 備份現有資料庫（如有）

### 執行中
- [ ] 每個 Phase 完成後執行測試驗證
- [ ] 記錄測試失敗原因
- [ ] 更新測試覆蓋率報告
- [ ] 提交代碼到 Git

### 完成後
- [ ] 所有測試通過
- [ ] 測試覆蓋率達標
- [ ] 文檔更新完成
- [ ] 提交最終報告

---

## 📝 附錄

### A. 假資料詳細資訊

**檔案**: `test-docs/sample_incident_10.xlsx`

**資料範例** (前 3 筆):
```
INC20000: Mail-Server / WebService / Queue Stuck
  - 系統延遲
  - VPN 憑證過期
  - 聯繫設備廠商 → 已修復

INC20001: FileShare-NAS / Security / Backup Failed
  - API 無法存取
  - 攝影機未錄影
  - 重新啟動服務 → 問題結案

INC20002: CCTV-System / Storage / Queue Stuck
  - 登入失敗
  - 郵件遭大量退件
  - 調整設定後改善 → 追蹤後無異常
```

### B. 測試執行命令

**執行所有假資料測試**:
```bash
pytest tests/integration/test_*sample*.py -v
```

**執行端到端測試**:
```bash
pytest tests/integration/test_e2e_sample_workflow.py -v --tb=short
```

**執行並產生覆蓋率報告**:
```bash
pytest tests/integration/test_*sample*.py --cov=. --cov-report=html
```

**執行特定測試**:
```bash
pytest tests/integration/test_upload_sample_data.py::test_preview_sample_excel -v
```

### C. 預期測試輸出

**成功案例**:
```
tests/integration/test_upload_sample_data.py::test_preview_sample_excel PASSED
tests/integration/test_db_operations.py::test_sample_data_written_to_db PASSED
tests/integration/test_faiss_with_sample_data.py::test_faiss_index_creation_from_sample_data PASSED
tests/integration/test_e2e_sample_workflow.py::test_complete_workflow_with_sample_data PASSED

======================== 15 passed in 12.34s ========================
```

**失敗案例處理**:
```
FAILED tests/integration/test_db_operations.py::test_sample_data_written_to_db
  AssertionError: Expected 10 records, got 8

解決方案: 檢查資料庫寫入邏輯，確認所有資料都正確處理
```

---

**計劃建立日期**: 2025-11-17
**計劃版本**: v1.0
**狀態**: ⏳ 待執行
**負責人**: 開發團隊
**預計完成**: 2025-11-24（1 週）
