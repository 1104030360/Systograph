# Phase 3: 增強功能

**時程**: 1-2 週
**優先級**: 可選執行
**目標**: 實作待規格化功能與進階功能

---

## 問題定義

**當前系統待實作功能**:

1. 會話列表分頁與搜尋 (已規格化)
2. 會話標題驗證 (已規格化)
3. 刪除確認對話框 (已規格化)
4. 權重總和雙重驗證 (已規格化)
5. 群集名稱截斷邏輯 (已規格化)
6. 召回率測試集建立 (已規格化)

**進階功能需求**:

1. 任務佇列 (多使用者並發處理)
2. 跨平台支援 (移除 win32com 依賴)
3. 使用者認證 (Flask-Login)

**預期成果**:

- 提升使用者體驗
- 增強系統穩定性
- 為未來擴展奠定基礎

> **2025-11-15 狀態**
> - ⚠️ `templates/chat.html` 目前沒有分頁/搜尋 UI，也未見 `search-title` 或相關控制項；`api/chat_routes.py` 亦僅提供舊有 list API，未實作 `/api/chat/sessions` 分頁參數。
> - ⚠️ 會話標題驗證、刪除確認、權重雙重驗證、群集名稱截斷等邏輯在現有程式碼中仍是 TODO（如 `services/config_service.py` 僅檢查基本欄位），本階段尚未啟動。
> - ⚠️ 召回率測試集、任務佇列、使用者認證等進階需求完全未開發。

---

## 優先順序排序

根據業務價值與實作成本，功能優先順序如下:

| 優先級 | 功能名稱 | 業務價值 | 實作成本 | 建議時機 |
|-------|---------|---------|---------|---------|
| **P0** | 會話列表分頁與搜尋 | 高 | 低 | Week 1 |
| **P0** | 會話標題驗證 | 高 | 低 | Week 1 |
| **P0** | 刪除確認對話框 | 高 | 低 | Week 1 |
| **P1** | 權重總和雙重驗證 | 中 | 低 | Week 1-2 |
| **P1** | 群集名稱截斷邏輯 | 中 | 低 | Week 1-2 |
| **P2** | 召回率測試集建立 | 中 | 中 | Week 2 |
| **P2** | 任務佇列 (RQ) | 低 (當前 <10 使用者) | 中 | 需求明確後 |
| **P2** | 跨平台支援 (openpyxl) | 低 (僅 Windows 部署) | 高 | 需求明確後 |
| **P2** | 使用者認證 (Flask-Login) | 低 (內部工具) | 中 | 需求明確後 |

---

## Week 1: P0 高優先級功能

### 目標

實作影響使用者體驗的核心功能

### 任務清單

#### 1.1 會話列表分頁與搜尋

**對應規格**: `features/對話會話管理.feature`

**前端實作 (templates/chat.html)**

- [ ] **分頁控制項**:

  ```html
  <div class="pagination">
    <button id="prev-page">上一頁</button>
    <span>第 <span id="current-page">1</span> 頁，共 <span id="total-pages">5</span> 頁</span>
    <button id="next-page">下一頁</button>
  </div>
  ```

  - 每頁顯示 20 筆會話
  - 前端 JavaScript 處理分頁邏輯

- [ ] **搜尋功能**:

  ```html
  <div class="search-bar">
    <input type="text" id="search-title" placeholder="搜尋標題關鍵字...">
    <input type="date" id="search-date-start" placeholder="開始日期">
    <input type="date" id="search-date-end" placeholder="結束日期">
    <button id="search-btn">搜尋</button>
  </div>
  ```

  - 按標題關鍵字搜尋 (不區分大小寫)
  - 按日期範圍篩選

**後端實作 (api/chat_routes.py)**

- [ ] **新增 API: `/api/chat/sessions`**:

  ```python
  @chat_bp.route('/api/chat/sessions', methods=['GET'])
  def list_sessions():
      page = request.args.get('page', 1, type=int)
      page_size = request.args.get('page_size', 20, type=int)
      title_filter = request.args.get('title', '', type=str)
      date_start = request.args.get('date_start', '', type=str)
      date_end = request.args.get('date_end', '', type=str)

      sessions = chat_repo.list_sessions(
          page=page,
          page_size=page_size,
          title_filter=title_filter,
          date_start=date_start,
          date_end=date_end
      )

      return jsonify({
          "status": "success",
          "sessions": sessions['items'],
          "pagination": {
              "current_page": page,
              "total_pages": sessions['total_pages'],
              "total_count": sessions['total_count']
          }
      })
  ```

**Repository 實作 (repositories/chat_repo.py)**

- [ ] **更新 `list_sessions()` 方法**:

  ```python
  def list_sessions(
      self,
      page: int = 1,
      page_size: int = 20,
      title_filter: str = '',
      date_start: str = '',
      date_end: str = ''
  ) -> Dict:
      """
      列出會話清單 (分頁 + 搜尋)

      Args:
          page: 頁碼 (從 1 開始)
          page_size: 每頁筆數 (預設 20)
          title_filter: 標題關鍵字 (模糊搜尋)
          date_start: 開始日期 (YYYY-MM-DD)
          date_end: 結束日期 (YYYY-MM-DD)

      Returns:
          {
              'items': [會話清單],
              'total_pages': 總頁數,
              'total_count': 總筆數
          }
      """
      # 讀取所有會話檔案
      all_sessions = self._load_all_sessions()

      # 篩選邏輯
      filtered = [
          s for s in all_sessions
          if (not title_filter or title_filter.lower() in s['title'].lower())
          and (not date_start or s['created_at'] >= date_start)
          and (not date_end or s['created_at'] <= date_end)
      ]

      # 排序 (按建立時間倒序)
      filtered.sort(key=lambda x: x['created_at'], reverse=True)

      # 分頁
      total_count = len(filtered)
      total_pages = math.ceil(total_count / page_size)
      start_idx = (page - 1) * page_size
      end_idx = start_idx + page_size
      items = filtered[start_idx:end_idx]

      return {
          'items': items,
          'total_pages': total_pages,
          'total_count': total_count
      }
  ```

**測試實作 (tests/unit/repositories/test_chat_repo.py)**

- [ ] `test_list_sessions_pagination()` - 分頁功能
- [ ] `test_list_sessions_title_filter()` - 標題搜尋
- [ ] `test_list_sessions_date_filter()` - 日期篩選
- [ ] `test_list_sessions_combined_filters()` - 組合篩選

#### 1.2 會話標題驗證

**對應規格**: `features/對話會話管理.feature`

**前端驗證 (static/js/chat.js)**

- [ ] **標題長度驗證**:

  ```javascript
  function validateSessionTitle(title) {
      // 檢查長度 ≤100 字
      if (title.length > 100) {
          showError("標題長度不可超過 100 字");
          return false;
      }

      // 檢查特殊字元 (禁止 /\:*?"<>|)
      const invalidChars = /[\/\\:*?"<>|]/;
      if (invalidChars.test(title)) {
          showError("標題不可包含特殊字元: / \\ : * ? \" < > |");
          return false;
      }

      return true;
  }

  // 即時驗證
  document.getElementById('session-title').addEventListener('input', function() {
      const title = this.value;
      validateSessionTitle(title);
  });
  ```

**後端驗證 (services/rag_service.py)**

- [ ] **更新 `create_session()` 方法**:

  ```python
  def create_session(self, title: str) -> Dict:
      """
      建立新會話 (包含標題驗證)

      Raises:
          ValidationError: 標題驗證失敗
      """
      # 驗證標題長度
      if len(title) > 100:
          raise ValidationError("SESSION_TITLE_TOO_LONG", "標題長度不可超過 100 字")

      # 驗證特殊字元
      invalid_chars = r'[/\\:*?"<>|]'
      if re.search(invalid_chars, title):
          raise ValidationError(
              "SESSION_TITLE_INVALID_CHARS",
              "標題不可包含特殊字元: / \\ : * ? \" < > |"
          )

      # 建立會話
      session_id = str(uuid.uuid4())
      session = {
          'session_id': session_id,
          'title': title,
          'created_at': datetime.now().isoformat(),
          'history': []
      }

      self.chat_repo.save_session(session)
      return session
  ```

**測試實作 (tests/unit/services/test_rag_service.py)**

- [ ] `test_create_session_valid_title()` - 有效標題
- [ ] `test_create_session_title_too_long()` - 超過 100 字
- [ ] `test_create_session_invalid_chars()` - 特殊字元
- [ ] `test_create_session_edge_cases()` - 邊界情況 (100 字、空白)

#### 1.3 刪除確認對話框

**對應規格**: `features/系統配置管理.feature`

**前端實作 (templates/*.html)**

- [ ] **統一刪除確認對話框 (Bootstrap Modal)**:

  ```html
  <!-- base.html -->
  <div class="modal fade" id="deleteConfirmModal" tabindex="-1">
    <div class="modal-dialog">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">確認刪除</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
          <p id="delete-confirm-message">確定要刪除此項目嗎?此操作無法復原。</p>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
          <button type="button" class="btn btn-danger" id="confirm-delete-btn">刪除</button>
        </div>
      </div>
    </div>
  </div>
  ```

- [ ] **刪除按鈕綁定 (static/js/common.js)**:

  ```javascript
  function showDeleteConfirm(message, onConfirm) {
      // 設定訊息
      document.getElementById('delete-confirm-message').innerText = message;

      // 綁定確認事件
      document.getElementById('confirm-delete-btn').onclick = function() {
          onConfirm();
          $('#deleteConfirmModal').modal('hide');
      };

      // 顯示對話框
      $('#deleteConfirmModal').modal('show');
  }

  // 使用範例
  document.querySelectorAll('.delete-btn').forEach(btn => {
      btn.addEventListener('click', function() {
          const itemId = this.dataset.itemId;
          const itemName = this.dataset.itemName;

          showDeleteConfirm(
              `確定要刪除 "${itemName}" 嗎?此操作無法復原。`,
              () => deleteItem(itemId)
          );
      });
  });
  ```

**應用範圍**:

- [ ] 會話刪除 (chat.html)
- [ ] 歷史記錄刪除 (history.html)
- [ ] 配置刪除 (config.html)
- [ ] 聚類結果刪除 (cluster.html)

**測試實作 (tests/e2e/test_delete_confirm.py - Selenium)**

- [ ] `test_delete_session_with_confirm()` - 會話刪除確認
- [ ] `test_delete_cancel()` - 取消刪除
- [ ] `test_delete_all_types()` - 所有刪除類型

#### 1.4 權重總和雙重驗證

**對應規格**: `features/系統配置管理.feature`

**前端驗證 (static/js/config.js)**

- [ ] **即時權重驗證**:

  ```javascript
  function validateWeightSum() {
      const severityWeight = parseFloat($('#severity-weight').val());
      const frequencyWeight = parseFloat($('#frequency-weight').val());
      const sum = severityWeight + frequencyWeight;

      const tolerance = 0.0001;  // 容忍誤差
      const isValid = Math.abs(sum - 1.0) < tolerance;

      // 顯示警告
      if (!isValid) {
          $('#weight-warning').text(`權重總和 ${sum.toFixed(4)} ≠ 1.0，請調整`).show();
          $('#save-weight-btn').prop('disabled', true);
      } else {
          $('#weight-warning').hide();
          $('#save-weight-btn').prop('disabled', false);
      }

      return isValid;
  }

  // 綁定輸入事件
  $('#severity-weight, #frequency-weight').on('input', validateWeightSum);
  ```

**後端驗證 (repositories/config_repo.py)**

- [ ] **更新 `save_weight_config()` 方法**:

  ```python
  def save_weight_config(self, config: WeightConfiguration) -> Dict:
      """
      儲存權重配置 (雙重驗證)

      Raises:
          ValidationError: 權重總和 ≠ 1.0
      """
      # 驗證權重總和
      total = config['severityWeight'] + config['frequencyWeight']
      tolerance = 0.0001

      if abs(total - 1.0) > tolerance:
          raise ValidationError(
              "WEIGHT_SUM_INVALID",
              f"權重總和 {total:.4f} ≠ 1.0 (容忍誤差 ±{tolerance})"
          )

      # 寫入 JSON 檔案
      with open(self.weight_config_path, 'w', encoding='utf-8') as f:
          json.dump(config, f, ensure_ascii=False, indent=2)

      return {"status": "success", "message": "權重配置已儲存"}
  ```

**測試實作 (tests/unit/repositories/test_config_repo.py)**

- [ ] `test_save_weight_config_valid()` - 有效權重 (總和=1.0)
- [ ] `test_save_weight_config_invalid_sum()` - 無效權重 (總和≠1.0)
- [ ] `test_save_weight_config_tolerance()` - 容忍誤差 (±0.0001)

#### 1.5 群集名稱截斷邏輯

**對應規格**: `features/工單聚類.feature`

**Service 實作 (services/cluster_service.py)**

- [ ] **更新 `_generate_cluster_name()` 方法**:

  ```python
  def _generate_cluster_name(self, cluster_tickets: List[Ticket]) -> str:
      """
      生成群集名稱 (限制 30 字 + 省略號)

      Returns:
          截斷後的群集名稱 (最多 30 字 + "...")
      """
      # 呼叫 LLM 生成摘要
      summary = self.ai_utils.call_llm(
          prompt=f"請為以下工單群集生成簡短名稱 (30字以內):\n{cluster_tickets}"
      )

      # 截斷邏輯
      max_length = 30
      if len(summary) > max_length:
          summary = summary[:max_length] + "..."

      # 檔名系統相容性檢查 (移除特殊字元)
      summary = re.sub(r'[/\\:*?"<>|]', '_', summary)

      return summary
  ```

**測試實作 (tests/unit/services/test_cluster_service.py)**

- [ ] `test_generate_cluster_name_short()` - 名稱 <30 字
- [ ] `test_generate_cluster_name_truncate()` - 名稱 >30 字 (截斷)
- [ ] `test_generate_cluster_name_special_chars()` - 特殊字元替換

### 驗收標準

```bash
# 1. 功能驗證 (手動測試)
python run_analysis.py

# 測試 1.1: 會話列表分頁
# - 檢查每頁 20 筆
# - 測試標題搜尋
# - 測試日期篩選

# 測試 1.2: 會話標題驗證
# - 嘗試輸入 101 字標題 → 應被阻擋
# - 嘗試輸入特殊字元 → 應顯示錯誤

# 測試 1.3: 刪除確認
# - 點擊任何刪除按鈕 → 應顯示確認對話框

# 測試 1.4: 權重驗證
# - 輸入總和 ≠ 1.0 → 應禁用儲存按鈕
# - 輸入總和 = 1.0 → 應啟用儲存按鈕

# 測試 1.5: 群集名稱截斷
# - 生成超長群集名稱 → 應截斷為 30 字 + "..."

# 2. 測試覆蓋率
pytest tests/unit/services/ tests/unit/repositories/ --cov --cov-report=term
# 新功能覆蓋率應 ≥80%

```text

---

## Week 1-2: P1 中優先級功能

### 任務清單

#### 2.1 召回率測試集建立

**對應規格**: `features/RAG對話查詢.feature`

**目標**: 建立 100 組人工標註查詢與相關工單，用於召回率評估

**測試集格式 (tests/fixtures/recall_test_set.json)**

```json
[
  {
    "query_id": 1,
    "query": "如何解決電腦無法開機問題?",
    "relevant_tickets": ["INC001", "INC023", "INC045"],
    "category": "硬體故障",
    "difficulty": "easy"
  },
  {
    "query_id": 2,
    "query": "網路連線不穩定該怎麼處理?",
    "relevant_tickets": ["INC012", "INC034"],
    "category": "網路問題",
    "difficulty": "medium"
  }
  // ... (共 100 組)
]

```text

**任務**:

- [ ] 從歷史工單中選取 100 組代表性查詢:
  - 簡單查詢 (30 組): 直接關鍵字匹配
  - 中等查詢(50 組): 需語意理解
  - 困難查詢 (20 組): 需多步推理

- [ ] 人工標註相關工單 (每個查詢 2-5 個相關工單)
- [ ] 標註類別與難度

**召回率評估腳本 (tests/performance/test_recall.py)**

- [ ] **實作召回率計算**:

  ```python
  def calculate_recall(test_set: List[Dict]) -> Dict:
      """
      計算召回率

      Returns:
          {
              'overall_recall': 整體召回率,
              'recall_by_category': 各類別召回率,
              'recall_by_difficulty': 各難度召回率
          }
      """
      results = []

      for item in test_set:
          query = item['query']
          relevant_ids = set(item['relevant_tickets'])

          # 呼叫 RAG 系統
          response = rag_service.query(query, session_id="test")
          retrieved_ids = set([s['id'] for s in response['sources']])

          # 計算召回率
          recall = len(relevant_ids & retrieved_ids) / len(relevant_ids)
          results.append({
              'query_id': item['query_id'],
              'recall': recall,
              'category': item['category'],
              'difficulty': item['difficulty']
          })

      # 彙總統計
      overall_recall = sum(r['recall'] for r in results) / len(results)

      return {
          'overall_recall': overall_recall,
          'recall_by_category': _group_by_category(results),
          'recall_by_difficulty': _group_by_difficulty(results)
      }
  ```

- [ ] **實作定期監控**:

  ```bash
  # 每週執行一次召回率測試
  pytest tests/performance/test_recall.py -v
  ```

**驗收標準**:

- 整體召回率 ≥95%
- 簡單查詢召回率 ≥98%
- 中等查詢召回率 ≥95%
- 困難查詢召回率 ≥85%

---

## Week 2: P2 低優先級功能 (視時間而定)

### 任務清單

#### 3.1 任務佇列 (RQ)

**使用情境**: 多使用者 (10-20 人) 同時上傳檔案

**技術選型**: Redis Queue (RQ)

**實作步驟**:

- [ ] **安裝依賴**:

  ```bash
  pip install redis rq
  # 啟動 Redis: redis-server
  ```

- [ ] **實作佇列管理器 (core/queue.py)**:

  ```python
  from redis import Redis
  from rq import Queue

  redis_conn = Redis(host='localhost', port=6379)
  task_queue = Queue('ticket_analysis', connection=redis_conn)

  def enqueue_task(func, *args, **kwargs):
      """將任務加入佇列"""
      job = task_queue.enqueue(func, *args, **kwargs, timeout=600)
      return job.id
  ```

- [ ] **修改上傳路由 (api/upload_routes.py)**:

  ```python
  @upload_bp.route('/api/upload/analyze', methods=['POST'])
  def analyze_tickets():
      file_id = request.json['file_id']

      # 將任務加入佇列
      job_id = enqueue_task(
          'services.ticket_service.process_uploaded_file',
          file_path=f"uploads/{file_id}.xlsx"
      )

      return jsonify({"status": "success", "task_id": job_id})
  ```

- [ ] **實作任務狀態查詢**:

  ```python
  @upload_bp.route('/api/tasks/<task_id>', methods=['GET'])
  def get_task_status(task_id):
      job = task_queue.fetch_job(task_id)

      return jsonify({
          "status": job.get_status(),
          "result": job.result if job.is_finished else None
      })
  ```

- [ ] **啟動 Worker**:

  ```bash
  # 啟動 1 個 Worker
  rq worker ticket_analysis
  ```

**驗收標準**:

- 5 個使用者同時上傳檔案 → 依序處理，無衝突
- 任務狀態可查詢 (pending, started, finished, failed)

#### 3.2 跨平台支援 (openpyxl)

**目標**: 移除 win32com 依賴，改用 openpyxl

**實作步驟**:

- [ ] **效能評估**:

  ```python
  # tests/performance/test_excel_libraries.py
  def test_compare_excel_libraries():
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

      # 若 openpyxl 快 ≥5 倍,則遷移
      assert openpyxl_time * 5 < win32com_time
  ```

- [ ] **實作 openpyxl 版本 (utils/excel_utils.py)**:

  ```python
  import openpyxl
  from openpyxl.styles import PatternFill

  def read_excel_openpyxl(file_path: str) -> List[Dict]:
      """使用 openpyxl 讀取 Excel"""
      wb = openpyxl.load_workbook(file_path)
      ws = wb.active

      headers = [cell.value for cell in ws[1]]
      data = []

      for row in ws.iter_rows(min_row=2, values_only=True):
          data.append(dict(zip(headers, row)))

      return data

  def write_excel_openpyxl(data: List[Dict], file_path: str):
      """使用 openpyxl 寫入 Excel"""
      wb = openpyxl.Workbook()
      ws = wb.active

      # 寫入表頭
      headers = list(data[0].keys())
      ws.append(headers)

      # 寫入資料 + 上色邏輯
      for i, row in enumerate(data):
          ws.append(list(row.values()))
          # 2 色交替上色
          fill = PatternFill(start_color="FFFF00" if i % 2 == 0 else "00FFFF",
                            end_color="FFFF00" if i % 2 == 0 else "00FFFF",
                            fill_type="solid")
          for cell in ws[i+2]:
              cell.fill = fill

      wb.save(file_path)
  ```

- [ ] **替換所有 win32com 呼叫**:
  - `Analysis.py` - Excel 讀取邏輯
  - `build_kb.py` - Excel 關閉邏輯 (改用 openpyxl 不需要)
  - `services/cluster_service.py` - Excel 寫入邏輯

- [ ] **測試相容性**:
  - Windows 測試
  - macOS 測試 (若有環境)
  - Linux 測試 (若有環境)

**驗收標準**:

- 所有功能正常運作 (Windows, macOS, Linux)
- 效能提升 ≥5 倍 (openpyxl vs win32com)

#### 3.3 使用者認證 (Flask-Login)

**目標**: 實作基礎使用者認證 (Admin/User 兩種角色)

**實作步驟**:

- [ ] **安裝依賴**:

  ```bash
  pip install flask-login
  ```

- [ ] **實作 User 模型 (models/user.py)**:

  ```python
  from flask_login import UserMixin

  class User(UserMixin):
      def __init__(self, user_id, username, role):
          self.id = user_id
          self.username = username
          self.role = role  # 'admin' or 'user'
  ```

- [ ] **實作登入系統 (api/auth_routes.py)**:

  ```python
  from flask import Blueprint, request, redirect, url_for
  from flask_login import LoginManager, login_user, logout_user, login_required

  auth_bp = Blueprint('auth', __name__)
  login_manager = LoginManager()

  @auth_bp.route('/login', methods=['GET', 'POST'])
  def login():
      if request.method == 'POST':
          username = request.form['username']
          password = request.form['password']

          # 驗證使用者 (簡單版,實務應使用資料庫 + hash)
          if username == 'admin' and password == 'admin123':
              user = User(1, 'admin', 'admin')
              login_user(user)
              return redirect(url_for('index'))

      return render_template('login.html')

  @auth_bp.route('/logout')
  @login_required
  def logout():
      logout_user()
      return redirect(url_for('auth.login'))
  ```

- [ ] **實作權限裝飾器**:

  ```python
  from functools import wraps
  from flask_login import current_user

  def admin_required(f):
      @wraps(f)
      def decorated_function(*args, **kwargs):
          if not current_user.is_authenticated or current_user.role != 'admin':
              return jsonify({"error": "需要管理員權限"}), 403
          return f(*args, **kwargs)
      return decorated_function

  # 使用範例
  @config_bp.route('/api/config/weight', methods=['POST'])
  @admin_required
  def update_weight():
      # 僅管理員可修改權重
  ```

- [ ] **保護路由**:
  - 配置管理 (僅 Admin)
  - 知識庫同步 (僅 Admin)
  - 工單上傳 (Admin + User)
  - RAG 查詢 (Admin + User)
  - 歷史記錄 (僅自己的記錄)

**驗收標準**:

- 未登入無法存取任何功能
- User 無法存取配置管理
- Admin 可存取所有功能

---

## 交付物

### 必須完成 (P0)

1. ✅ **會話列表分頁與搜尋**

   - 前端分頁控制項 (每頁 20 筆)
   - 標題關鍵字搜尋
   - 日期範圍篩選
   - 後端 API 支援

2. ✅ **會話標題驗證**

   - 前端即時驗證 (≤100 字，禁止特殊字元)
   - 後端 API 驗證
   - 統一錯誤訊息

3. ✅ **刪除確認對話框**

   - 統一 Bootstrap Modal
   - 所有刪除操作顯示確認
   - 防止誤刪除

### 建議完成 (P1)

4. ✅ **權重總和雙重驗證**

   - 前端即時驗證 (總和 = 1.0)
   - 後端 API 驗證
   - 禁用儲存按鈕邏輯

5. ✅ **群集名稱截斷邏輯**

   - 限制 30 字 + 省略號
   - 特殊字元替換
   - 檔名系統相容性

### 視情況完成 (P2)

6. ⚠️ **召回率測試集**

   - 100 組人工標註查詢
   - 召回率評估腳本
   - 定期監控機制

7. ⚠️ **任務佇列 (RQ)**

   - Redis Queue 整合
   - 非同步檔案處理
   - 任務狀態查詢

8. ⚠️ **跨平台支援 (openpyxl)**

   - 移除 win32com 依賴
   - macOS/Linux 相容性
   - 效能提升 ≥5 倍

9. ⚠️ **使用者認證 (Flask-Login)**

   - 登入/登出
   - Admin/User 權限管理
   - 路由保護

---

## 風險與緩解

### 風險 1: P0 功能耗時超出預期

**緩解**:

- 聚焦於 P0 功能，P1-P2 可延後
- 會話列表分頁與搜尋是最優先 (使用者最需要)

### 風險 2: 召回率測試集標註成本高

**緩解**:

- 減少測試集數量 (100 → 50 組)
- 使用 LLM 輔助標註 (人工審核)

### 風險 3: openpyxl 遷移破壞現有功能

**緩解**:

- 先完整評估效能差異
- 保留 win32com 作為備用方案
- 若效能提升 <3 倍，不遷移

### 風險 4: 使用者認證需求不明確

**緩解**:

- 與業務方確認需求
- 若當前無需求，延後至未來實作

---

## 下一階段

完成 Phase 3 後:

- **持續維護**: 根據使用者回饋優化功能
- **效能監控**: 定期執行召回率測試與效能測試
- **功能擴展**: 根據新需求評估是否進入 Phase 4
