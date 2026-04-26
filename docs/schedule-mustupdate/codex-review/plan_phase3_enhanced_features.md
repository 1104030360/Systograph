# Phase 3: Enhanced Features 計畫落實狀況分析（2025-11-19）

**分析日期**: 2025-11-19
**分析範圍**: `docs/schedule-mustupdate/plan/unfinish/plan_phase3_enhanced_features.md`
**分析方法**: 逐項對照計畫文件與實際程式碼實作
**分析人員**: Claude Code (Codex Review Agent)

---

## 📋 執行摘要

### 主要發現

1. **整體完成度**: **27.8%** （9 個功能中，1 個已完成、4 個部分完成、4 個未實作）

2. **P0 高優先級功能嚴重落後**:
   - 會話列表分頁與搜尋：40% 完成
   - 會話標題驗證：0% 完成
   - 刪除確認對話框：20% 完成

3. **意外發現**: P2.3 跨平台支援已在 Phase 1-1 完成，但計畫文件未同步更新

4. **建議行動**: 優先補齊 P0 功能，預估需 2 個工作日（14 小時）

---

## 1. Phase 3 計畫需求總整理

根據 `docs/schedule-mustupdate/plan/unfinish/plan_phase3_enhanced_features.md`，Phase 3 包含 **9 個主要功能**，分為三個優先級：

### P0 高優先級（Week 1，必須完成）

#### 1.1 會話列表分頁與搜尋
- **前端需求**:
  - 分頁控制項（每頁 20 筆）
  - 標題關鍵字搜尋（不區分大小寫）
  - 日期範圍篩選（開始日期、結束日期）
- **後端需求**:
  - API `/api/chat/sessions` 支援 `page`, `page_size`, `title`, `date_start`, `date_end` 參數
  - Repository `list_sessions()` 支援分頁與篩選邏輯
- **驗收標準**:
  - 每頁顯示 20 筆
  - 標題搜尋即時生效
  - 日期篩選準確

#### 1.2 會話標題驗證
- **前端驗證**: 即時驗證（≤100 字，禁止特殊字元 `/\:*?"<>|`）
- **後端驗證**: `services/rag_service.py` 的 `create_session()` 與 `rename_session()` 方法驗證標題
- **錯誤處理**: 統一的 ValidationError
- **驗收標準**:
  - 輸入 101 字標題應被阻擋
  - 輸入特殊字元應顯示錯誤訊息

#### 1.3 刪除確認對話框
- **統一 Modal**: `templates/base.html` 新增 `#deleteConfirmModal`
- **前端工具函式**: 實作 `showDeleteConfirm()` 工具函式
- **應用範圍**: 會話刪除、歷史記錄、配置、聚類結果
- **驗收標準**:
  - 所有刪除操作顯示確認對話框
  - 取消操作不執行刪除
  - 確認後正確刪除

### P1 中優先級（Week 1-2，建議完成）

#### 1.4 權重總和雙重驗證
- **前端驗證**: 即時驗證（總和 = 1.0，容忍誤差 ±0.0001）
- **後端驗證**: `services/config_service.py` 已實作
- **UI 互動**: 總和不等於 1.0 時禁用儲存按鈕
- **驗收標準**:
  - 輸入總和 ≠ 1.0 應禁用儲存按鈕
  - 輸入總和 = 1.0 應啟用儲存按鈕

#### 1.5 群集名稱截斷邏輯
- **Service 實作**: `services/cluster_service.py` 的 `_generate_cluster_summary()`
- **截斷規則**: 限制 30 字 + "..."
- **檔名相容性**: 特殊字元替換為 "_"
- **驗收標準**:
  - 超過 30 字的名稱應截斷
  - 特殊字元應被替換

### P2 低優先級（Week 2，視情況完成）

#### 2.1 召回率測試集建立
- **需求**: 100 組人工標註查詢（簡單 30、中等 50、困難 20）
- **測試腳本**: `tests/performance/test_recall.py`
- **驗收標準**: 整體召回率 ≥95%

#### 2.2 任務佇列（RQ）
- **需求**: Redis Queue 整合、非同步檔案處理、任務狀態查詢
- **觸發條件**: 同時上傳使用者數量 ≥10 人

#### 2.3 跨平台支援（openpyxl）
- **需求**: 移除 win32com 依賴、macOS/Linux 相容性
- **狀態**: ✅ **已在 Phase 1-1 完成（2025-11-19）**

#### 2.4 使用者認證（Flask-Login）
- **需求**: 登入/登出、Admin/User 權限管理、路由保護
- **觸發條件**: 系統需要對外開放或需要權限區分

---

## 2. 計畫 vs 實作對照表

### 2.1 總覽表

| 優先級 | 功能名稱 | 狀態 | 完成度 | 實作位置 | 缺失項目 |
|-------|---------|------|-------|---------|---------|
| **P0** | **1.1 會話列表分頁與搜尋** | ⚠️ 部分完成 | **40%** | `api/chat_routes.py:79-105`<br>`repositories/chat_repository.py:27-44`<br>`templates/chat.html:38-46`<br>`static/js/chat_ui.js:453-459` | 缺少篩選參數、分頁控制項 |
| **P0** | **1.2 會話標題驗證** | ❌ 未實作 | **0%** | N/A | 前端與後端驗證邏輯完全缺失 |
| **P0** | **1.3 刪除確認對話框** | ⚠️ 部分完成 | **20%** | `static/js/chat_ui.js:434` | 使用原生 confirm，非 Bootstrap Modal |
| **P1** | **1.4 權重總和雙重驗證** | ⚠️ 部分完成 | **50%** | `services/config_service.py:94-104` | 後端已完成，前端驗證缺失 |
| **P1** | **1.5 群集名稱截斷邏輯** | ⚠️ 部分完成 | **30%** | `services/cluster_service.py:59` | 有常數定義，無實際截斷邏輯 |
| **P2** | **2.1 召回率測試集** | ❌ 未實作 | **0%** | N/A | 完全未開發 |
| **P2** | **2.2 任務佇列（RQ）** | ❌ 未實作 | **0%** | N/A | 完全未開發 |
| **P2** | **2.3 跨平台支援** | ✅ **已完成** | **100%** | `utils/excel_client_openpyxl.py`<br>`utils/resource_manager.py` | Phase 1-1 已完成（53 個測試通過） |
| **P2** | **2.4 使用者認證** | ❌ 未實作 | **0%** | N/A | 完全未開發 |

**整體完成度**: **27.8%**

---

### 2.2 詳細對照

#### 2.2.1 會話列表分頁與搜尋（40% 完成）

**✅ 已實作部分**:
- `api/chat_routes.py:79-105` - API endpoint `/chat/sessions` 存在
- `repositories/chat_repository.py:27-44` - `list_sessions()` 方法存在
- `templates/chat.html:44` - 搜尋框 UI 存在
- `static/js/chat_ui.js:453-459` - 搜尋邏輯存在

**❌ 缺失部分**:
- **Repository**: `list_sessions()` 不接受 `title_filter`, `date_start`, `date_end` 參數
- **API**: 僅支援 `page`, `limit` 參數，缺少 `title`, `date_start`, `date_end`
- **前端**: 搜尋僅在前端過濾，無伺服器端篩選
- **前端**: 無分頁控制項（上一頁、下一頁按鈕）

**現有程式碼範例**:
```python
# repositories/chat_repository.py:27-44
def list_sessions(self) -> List[Dict]:
    """Return sorted session metadata (latest first)."""
    sessions: List[Dict] = []
    for path in self.history_dir.glob("*.json"):
        try:
            data = self._read_json(path)
            # ... 載入邏輯
            sessions.append({...})
        except Exception as exc:
            log_error(f"Failed to load chat session {path.name}: {exc}")
    sessions.sort(key=lambda item: item.get("last_message_time", ""), reverse=True)
    return sessions  # ← 無分頁、無篩選
```

---

#### 2.2.2 會話標題驗證（0% 完成）

**❌ 完全缺失**:
- `services/rag_service.py` 無標題驗證邏輯
- `static/js/chat_ui.js` 無前端即時驗證
- 無錯誤訊息處理

**現有重新命名邏輯** (`static/js/chat_ui.js:412-431`):
```javascript
li.querySelector(".rename-btn").onclick = async () => {
    const newTitle = prompt("輸入新的話題名稱", item.title || item.id);
    if (!newTitle) return;  // ← 僅檢查空值，無長度、特殊字元驗證

    try {
        const res = await fetch(apiUrl('/rename-chat'), {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ chat_id: item.id, new_title: newTitle })
        });
        // ...
    } catch (err) {
        alert("發送錯誤：" + err.message);
    }
};
```

---

#### 2.2.3 刪除確認對話框（20% 完成）

**✅ 已實作部分**:
- `static/js/chat_ui.js:434` - 刪除會話使用 `confirm()`

**❌ 缺失部分**:
- `templates/base.html` 無統一的 Bootstrap Modal
- 無 `showDeleteConfirm()` 工具函式
- 其他刪除操作（歷史記錄、配置、聚類）未統一

**現有刪除邏輯**:
```javascript
li.querySelector(".delete-btn").onclick = async () => {
    if (!confirm(`是否刪除這個話題？\n「${item.title || item.id}」`)) return;
    // ← 使用原生 confirm，非 Bootstrap Modal
    // ...
};
```

---

#### 2.2.4 權重總和雙重驗證（50% 完成）

**✅ 已實作部分** (`services/config_service.py:94-104`):
```python
def update_weight_config(self, severity_weight: float, frequency_weight: float) -> Dict:
    # Validate weight sum
    total = severity_weight + frequency_weight
    if abs(total - 1.0) > 0.0001:
        raise ValidationError(
            "WEIGHT_SUM_INVALID",
            f"權重總和 {total:.4f} ≠ 1.0 (容忍誤差 ±0.0001)",
            details={...}
        )
    # ... 儲存邏輯
```

**❌ 缺失部分**:
- 無前端即時驗證 JavaScript
- 無禁用儲存按鈕邏輯
- 無警告訊息顯示

---

#### 2.2.5 群集名稱截斷邏輯（30% 完成）

**✅ 已實作部分** (`services/cluster_service.py:59`):
```python
self.MAX_CLUSTER_NAME_LENGTH = 30  # ← 常數定義存在
```

**❌ 缺失部分**:
- 無實際截斷邏輯（未使用 `MAX_CLUSTER_NAME_LENGTH`）
- 無特殊字元替換邏輯
- `_generate_cluster_summary()` 方法未實作截斷

---

## 3. 改善與實作計畫

### 3.1 P0 功能補強計畫（必須完成）

---

#### 【補強 1.1】會話列表分頁與搜尋

**修改檔案**:
1. `repositories/chat_repository.py`
2. `services/rag_service.py`
3. `api/chat_routes.py`
4. `templates/chat.html`
5. `static/js/chat_ui.js`

**實作步驟**:

##### Step 1: 更新 Repository 支援篩選（repositories/chat_repository.py）

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
    列出會話清單（分頁 + 搜尋）

    Args:
        page: 頁碼（從 1 開始）
        page_size: 每頁筆數（預設 20）
        title_filter: 標題關鍵字（模糊搜尋，不區分大小寫）
        date_start: 開始日期（ISO 8601 格式，如 "2025-01-01"）
        date_end: 結束日期（ISO 8601 格式）

    Returns:
        {
            'items': [會話清單],
            'total_pages': 總頁數,
            'total_count': 總筆數,
            'current_page': 當前頁碼
        }
    """
    from core import log_info, log_error

    sessions: List[Dict] = []
    for path in self.history_dir.glob("*.json"):
        try:
            data = self._read_json(path)
            chat_id = path.stem
            history = data.get("history", [])

            # 建立會話物件
            session = {
                "id": chat_id,
                "title": data.get("edit_title") or data.get("title") or chat_id,
                "last_message_time": data.get("timestamp", ""),
                "message_count": len([msg for msg in history if msg.get("role") == "user"]),
                "created_at": data.get("timestamp", "")  # 用於日期篩選
            }

            # 篩選邏輯
            if title_filter and title_filter.lower() not in session['title'].lower():
                continue
            if date_start and session['created_at'] < date_start:
                continue
            if date_end and session['created_at'] > date_end:
                continue

            sessions.append(session)
        except Exception as exc:
            log_error(f"Failed to load chat session {path.name}: {exc}")

    # 排序（按最後訊息時間倒序）
    sessions.sort(key=lambda item: item.get("last_message_time", ""), reverse=True)

    # 分頁
    import math
    total_count = len(sessions)
    total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    items = sessions[start_idx:end_idx]

    return {
        'items': items,
        'total_pages': total_pages,
        'total_count': total_count,
        'current_page': page
    }
```

##### Step 2: 更新 Service 層（services/rag_service.py）

```python
def list_sessions(
    self,
    page: int = 1,
    page_size: int = 20,
    title_filter: str = '',
    date_start: str = '',
    date_end: str = ''
) -> Dict:
    """列出會話清單（分頁 + 搜尋）"""
    return self.chat_repo.list_sessions(
        page=page,
        page_size=page_size,
        title_filter=title_filter,
        date_start=date_start,
        date_end=date_end
    )
```

##### Step 3: 更新 API 支援篩選參數（api/chat_routes.py）

```python
@chat_bp.route('/chat/sessions', methods=['GET'])
def chat_history_list():
    """List all chat sessions with pagination and filters"""
    try:
        rag_service = get_service("rag")

        # 取得查詢參數
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        title_filter = request.args.get('title', '', type=str)
        date_start = request.args.get('date_start', '', type=str)
        date_end = request.args.get('date_end', '', type=str)

        # 參數驗證
        if page < 1:
            page = 1
        page_size = min(max(page_size, 1), 100)  # 限制 1-100

        # 呼叫 Service
        result = rag_service.list_sessions(
            page=page,
            page_size=page_size,
            title_filter=title_filter,
            date_start=date_start,
            date_end=date_end
        )

        return jsonify({
            "status": "success",
            "sessions": result['items'],
            "pagination": {
                "current_page": result['current_page'],
                "total_pages": result['total_pages'],
                "total_count": result['total_count'],
                "page_size": page_size
            }
        }), 200

    except Exception as e:
        log_error(f"List chat history error: {str(e)}")
        return make_error_response("INTERNAL_SERVER_ERROR", "取得會話列表失敗", status_code=500)
```

##### Step 4: 更新前端 UI（templates/chat.html）

在 `<aside class="chat-history" id="chatHistorySidebar">` 區域新增篩選與分頁控制項：

```html
<aside class="chat-history" id="chatHistorySidebar">
  <div class="history-header">
    <h3>歷史對話</h3>
    <button id="showHistoryBtn" class="btn btn-outline-sm">收合</button>
  </div>

  <!-- 新增：篩選區域 -->
  <div class="search-wrapper">
    <input type="text" id="historySearchInput" class="form-control styled-search mb-2"
           placeholder="搜尋標題關鍵字..." />
    <div class="row g-2 mb-2">
      <div class="col-6">
        <input type="date" id="dateStartFilter" class="form-control form-control-sm"
               placeholder="開始日期" />
      </div>
      <div class="col-6">
        <input type="date" id="dateEndFilter" class="form-control form-control-sm"
               placeholder="結束日期" />
      </div>
    </div>
    <button id="applyFilterBtn" class="btn btn-sm btn-primary w-100 mb-2">套用篩選</button>
  </div>

  <ul id="historyListUI" class="list-group list-group-flush"></ul>

  <!-- 新增：分頁控制項 -->
  <div class="pagination-controls mt-3 p-2 border-top">
    <div class="d-flex justify-content-between align-items-center">
      <button id="prevPageBtn" class="btn btn-sm btn-outline-secondary" disabled>
        <i class="bi bi-chevron-left"></i> 上一頁
      </button>
      <span class="text-muted small">
        第 <strong id="currentPageNum">1</strong> 頁，共 <strong id="totalPagesNum">1</strong> 頁
      </span>
      <button id="nextPageBtn" class="btn btn-sm btn-outline-secondary">
        下一頁 <i class="bi bi-chevron-right"></i>
      </button>
    </div>
  </div>
</aside>
```

##### Step 5: 更新前端 JavaScript（static/js/chat_ui.js）

在檔案開頭新增分頁邏輯：

```javascript
// ==================== 會話列表分頁與搜尋 ====================

let currentPage = 1;
let totalPages = 1;
const pageSize = 20;

/**
 * 載入會話列表（支援分頁與篩選）
 * @param {number} page - 頁碼（預設 1）
 */
async function loadSessionList(page = 1) {
  const titleFilter = document.getElementById('historySearchInput').value.trim();
  const dateStart = document.getElementById('dateStartFilter').value;
  const dateEnd = document.getElementById('dateEndFilter').value;

  const params = new URLSearchParams({
    page: page,
    page_size: pageSize,
    ...(titleFilter && { title: titleFilter }),
    ...(dateStart && { date_start: dateStart }),
    ...(dateEnd && { date_end: dateEnd })
  });

  const listUI = document.getElementById('historyListUI');
  listUI.innerHTML = `<li class="list-group-item">載入中...</li>`;

  try {
    const res = await fetch(`${apiUrl('/chat/sessions')}?${params}`);
    const payload = await res.json();

    if (!res.ok || payload.error) {
      listUI.innerHTML = `<li class="list-group-item text-warning">載入失敗：${payload.error || '未知錯誤'}</li>`;
      return;
    }

    const sessions = payload.sessions || [];
    const pagination = payload.pagination || {};

    // 更新分頁資訊
    currentPage = pagination.current_page || 1;
    totalPages = pagination.total_pages || 1;
    document.getElementById('currentPageNum').textContent = currentPage;
    document.getElementById('totalPagesNum').textContent = totalPages;
    document.getElementById('prevPageBtn').disabled = (currentPage <= 1);
    document.getElementById('nextPageBtn').disabled = (currentPage >= totalPages);

    // 渲染會話列表
    if (sessions.length === 0) {
      listUI.innerHTML = `<li class="list-group-item text-muted">無符合條件的歷史紀錄</li>`;
      return;
    }

    listUI.innerHTML = "";
    sessions.forEach(item => {
      const li = document.createElement("li");
      li.className = "list-group-item";
      const lastTime = item.last_message_time ? new Date(item.last_message_time).toLocaleString() : "—";
      const title = item.title || "（無標題）";
      const subtitle = `${lastTime} · ${item.message_count || 0} 則訊息`;

      li.innerHTML = `
        <div class="d-flex justify-content-between align-items-start">
          <div class="history-click-target" style="cursor: pointer;">
            <strong>${title}</strong><br>
            <small class="text-muted">${subtitle}</small>
          </div>
          <div class="dropdown">
            <button class="btn btn-sm btn-link text-muted dropdown-toggle dropdown-toggle-no-caret"
                    type="button" data-bs-toggle="dropdown">⋯</button>
            <ul class="dropdown-menu dropdown-menu-end">
              <li><a class="dropdown-item rename-btn" href="#">編輯標題</a></li>
              <li><a class="dropdown-item text-danger delete-btn" href="#">刪除話題</a></li>
            </ul>
          </div>
        </div>
      `;

      // 綁定點擊事件
      bindSessionEvents(li, item);
      listUI.appendChild(li);
    });

    listUI.dataset.loaded = "true";

  } catch (err) {
    listUI.innerHTML = `<li class="list-group-item text-danger">載入失敗：${err.message}</li>`;
    console.error("[載入歷史錯誤]", err);
  }
}

/**
 * 綁定會話項目的事件（載入、重新命名、刪除）
 */
function bindSessionEvents(li, item) {
  // 點擊載入會話
  li.querySelector(".history-click-target").onclick = async () => {
    const res = await fetch(`${apiUrl('/chat-history')}/${item.id}`);
    const json = await res.json();
    chatHistory = json.history || [];
    localStorage.setItem("chatHistory", JSON.stringify(chatHistory));
    localStorage.setItem("currentChatId", json.id);

    document.querySelectorAll('#historyListUI .list-group-item').forEach(el => el.classList.remove('active'));
    li.classList.add('active');

    const box = document.getElementById("chatBox");
    box.innerHTML = "";
    chatHistory.forEach(entry => {
      const div = document.createElement("div");
      div.className = "msg " + (entry.role === "user" ? "user" : "bot");
      div.innerHTML = `${entry.role === "user" ? "使用者" : "系統"} ${renderMessage(entry.content)}`;
      box.appendChild(div);
    });
    scrollToBottom();
  };

  // 重新命名（後續會補強標題驗證）
  li.querySelector(".rename-btn").onclick = async () => {
    const newTitle = prompt("輸入新的話題名稱", item.title || item.id);
    if (!newTitle) return;

    try {
      const res = await fetch(apiUrl('/rename-chat'), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chat_id: item.id, new_title: newTitle })
      });
      const result = await res.json();
      if (res.ok && (result.status === 'success' || result.success)) {
        alert("標題已更新");
        loadSessionList(currentPage);  // 重新載入當前頁
      } else {
        alert("無法更新標題：" + (result.message || result.error || ""));
      }
    } catch (err) {
      alert("發送錯誤：" + err.message);
    }
  };

  // 刪除（後續會改為統一 Modal）
  li.querySelector(".delete-btn").onclick = async () => {
    if (!confirm(`是否刪除這個話題？\n「${item.title || item.id}」`)) return;
    try {
      const res = await fetch(`${apiUrl('/delete-chat')}/${item.id}`, { method: "DELETE" });
      const result = await res.json();
      const ok = res.ok && (result.status === 'success' || result.success);
      if (ok) {
        alert("話題已刪除");
        loadSessionList(currentPage);  // 重新載入當前頁
      } else {
        alert("刪除失敗：" + (result.message || result.error || ""));
      }
    } catch (err) {
      alert("發送錯誤：" + err.message);
    }
  };
}

// 綁定分頁按鈕事件
document.addEventListener('DOMContentLoaded', function() {
  document.getElementById('prevPageBtn')?.addEventListener('click', () => {
    if (currentPage > 1) {
      loadSessionList(currentPage - 1);
    }
  });

  document.getElementById('nextPageBtn')?.addEventListener('click', () => {
    if (currentPage < totalPages) {
      loadSessionList(currentPage + 1);
    }
  });

  // 綁定篩選按鈕事件
  document.getElementById('applyFilterBtn')?.addEventListener('click', () => {
    loadSessionList(1);  // 重置到第一頁
  });

  // 頁面載入時自動載入第一頁
  loadSessionList(1);
});

// 更新原有的 showHistoryBtn 邏輯（移除舊的載入邏輯，改為呼叫 loadSessionList）
const historyToggleBtn = document.getElementById("showHistoryBtn");
if (historyToggleBtn) {
  historyToggleBtn.addEventListener("click", async () => {
    const wrapper = document.getElementById("chatHistorySidebar");
    const collapsed = wrapper.classList.toggle("collapsed");
    historyToggleBtn.innerText = collapsed ? "展開" : "收合";

    if (!collapsed) {
      const listUI = document.getElementById("historyListUI");
      if (listUI.dataset.loaded !== "true") {
        loadSessionList(1);
      }
    }
  });
}
```

**測試建議**:
```bash
# 單元測試
pytest tests/unit/repositories/test_chat_repository.py::test_list_sessions_pagination -v
pytest tests/unit/repositories/test_chat_repository.py::test_list_sessions_title_filter -v
pytest tests/unit/repositories/test_chat_repository.py::test_list_sessions_date_filter -v
pytest tests/unit/repositories/test_chat_repository.py::test_list_sessions_combined_filters -v
```

---

#### 【補強 1.2】會話標題驗證

**修改檔案**:
1. `services/rag_service.py`
2. `api/chat_routes.py`
3. `static/js/chat_ui.js`

**實作步驟**:

##### Step 1: 後端驗證邏輯（services/rag_service.py）

在 `RAGService` 類別中新增驗證方法：

```python
import re
from core import ValidationError

def _validate_session_title(self, title: str):
    """
    驗證會話標題

    Args:
        title: 會話標題

    Raises:
        ValidationError: 標題驗證失敗
    """
    if not title or not title.strip():
        raise ValidationError("INVALID_PARAMETER", "標題不能為空")

    title = title.strip()

    # 驗證長度
    if len(title) > 100:
        raise ValidationError(
            "SESSION_TITLE_TOO_LONG",
            f"標題長度不可超過 100 字（目前 {len(title)} 字）",
            details={"title_length": len(title), "max_length": 100}
        )

    # 驗證特殊字元
    invalid_chars_pattern = r'[/\\:*?"<>|]'
    invalid_chars_found = re.findall(invalid_chars_pattern, title)
    if invalid_chars_found:
        raise ValidationError(
            "SESSION_TITLE_INVALID_CHARS",
            f"標題不可包含特殊字元: {', '.join(set(invalid_chars_found))}",
            details={
                "invalid_chars": list(set(invalid_chars_found)),
                "allowed_chars_info": "不可包含 / \\ : * ? \" < > |"
            }
        )

def rename_session(self, chat_id: str, new_title: str) -> Dict:
    """
    重新命名會話（包含標題驗證）

    Args:
        chat_id: 會話 ID
        new_title: 新標題

    Returns:
        {"status": "success", "message": "會話標題已更新"}

    Raises:
        ValidationError: 標題驗證失敗或會話不存在
    """
    # 驗證標題
    self._validate_session_title(new_title)

    # 重新命名
    if not self.chat_repo.rename_session(chat_id, new_title):
        raise ValidationError("SESSION_NOT_FOUND", "找不到指定會話", status_code=404)

    log_info(f"Renamed session {chat_id} to: {new_title}")
    return {"status": "success", "message": "會話標題已更新"}
```

##### Step 2: 前端即時驗證（static/js/chat_ui.js）

新增標題驗證工具函式：

```javascript
/**
 * 驗證會話標題
 * @param {string} title - 標題文字
 * @returns {{valid: boolean, errors: string[]}}
 */
function validateSessionTitle(title) {
    const errors = [];

    if (!title || !title.trim()) {
        errors.push("標題不能為空");
        return { valid: false, errors: errors };
    }

    title = title.trim();

    // 檢查長度
    if (title.length > 100) {
        errors.push(`標題長度不可超過 100 字（目前 ${title.length} 字）`);
    }

    // 檢查特殊字元
    const invalidCharsPattern = /[\/\\:*?"<>|]/g;
    const matches = title.match(invalidCharsPattern);
    if (matches) {
        const uniqueChars = [...new Set(matches)].join(', ');
        errors.push(`標題不可包含特殊字元: ${uniqueChars}`);
    }

    return {
        valid: errors.length === 0,
        errors: errors
    };
}

/**
 * 顯示驗證錯誤訊息
 * @param {string[]} errors - 錯誤訊息陣列
 */
function showValidationErrors(errors) {
    const errorMsg = errors.join('\n');
    alert(`標題驗證失敗:\n\n${errorMsg}`);
}
```

更新重新命名邏輯（在 `bindSessionEvents` 函式中）：

```javascript
// 在 bindSessionEvents 函式中更新 rename-btn 邏輯
li.querySelector(".rename-btn").onclick = async () => {
    const newTitle = prompt("輸入新的話題名稱", item.title || item.id);
    if (!newTitle) return;

    // 前端驗證
    const validation = validateSessionTitle(newTitle);
    if (!validation.valid) {
        showValidationErrors(validation.errors);
        return;
    }

    try {
        const res = await fetch(apiUrl('/rename-chat'), {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ chat_id: item.id, new_title: newTitle })
        });
        const result = await res.json();

        if (res.ok && (result.status === 'success' || result.success)) {
            alert("標題已更新");
            loadSessionList(currentPage);
        } else {
            // 顯示後端驗證錯誤
            alert("無法更新標題：\n" + (result.message || result.error || "未知錯誤"));
        }
    } catch (err) {
        alert("發送錯誤：" + err.message);
    }
};
```

**測試建議**:
```bash
# 單元測試
pytest tests/unit/services/test_rag_service.py::test_validate_session_title_valid -v
pytest tests/unit/services/test_rag_service.py::test_validate_session_title_too_long -v
pytest tests/unit/services/test_rag_service.py::test_validate_session_title_invalid_chars -v
pytest tests/unit/services/test_rag_service.py::test_validate_session_title_edge_cases -v
```

**手動測試**:
1. 嘗試輸入 101 字標題 → 應被前端阻擋
2. 嘗試輸入特殊字元（如 `/`, `*`, `?`）→ 應顯示錯誤
3. 輸入有效標題（≤100 字，無特殊字元）→ 應成功更新

---

#### 【補強 1.3】刪除確認對話框

**修改檔案**:
1. `templates/base.html`
2. `static/js/chat_ui.js`

**實作步驟**:

##### Step 1: 在 base.html 新增統一 Modal（templates/base.html）

在 `{% block after_app_shell %}` 之前新增：

```html
<!-- 統一刪除確認對話框 -->
<div class="modal fade" id="deleteConfirmModal" tabindex="-1" aria-labelledby="deleteConfirmLabel" aria-hidden="true">
  <div class="modal-dialog modal-dialog-centered">
    <div class="modal-content shadow-lg border-0 rounded-4">
      <div class="modal-header border-0 pb-0">
        <h5 class="modal-title fw-bold text-danger" id="deleteConfirmLabel">
          <i class="bi bi-exclamation-triangle-fill me-2"></i>確認刪除
        </h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
      </div>
      <div class="modal-body py-4">
        <div class="text-center mb-3">
          <i class="bi bi-trash3-fill text-warning" style="font-size: 3rem;"></i>
        </div>
        <p class="text-center mb-0" id="deleteConfirmMessage">確定要刪除此項目嗎？此操作無法復原。</p>
      </div>
      <div class="modal-footer border-0 pt-0">
        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
        <button type="button" class="btn btn-danger" id="confirmDeleteBtn">
          <i class="bi bi-trash3 me-1"></i>刪除
        </button>
      </div>
    </div>
  </div>
</div>

{% block after_app_shell %}{% endblock %}
```

##### Step 2: 新增統一的刪除確認工具函式（static/js/chat_ui.js）

在檔案開頭新增：

```javascript
// ==================== 統一刪除確認對話框 ====================

/**
 * 顯示刪除確認對話框
 * @param {string} message - 確認訊息
 * @param {Function} onConfirm - 確認後的回調函式
 */
function showDeleteConfirm(message, onConfirm) {
    // 設定訊息
    const messageEl = document.getElementById('deleteConfirmMessage');
    if (messageEl) {
        messageEl.innerText = message;
    }

    // 綁定確認事件（移除舊的事件監聽器，避免重複綁定）
    const confirmBtn = document.getElementById('confirmDeleteBtn');
    if (confirmBtn) {
        const newConfirmBtn = confirmBtn.cloneNode(true);
        confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);

        newConfirmBtn.onclick = async function() {
            // 禁用按鈕，防止重複點擊
            newConfirmBtn.disabled = true;
            newConfirmBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>刪除中...';

            try {
                await onConfirm();
                // 關閉 Modal
                const modalEl = document.getElementById('deleteConfirmModal');
                const modal = bootstrap.Modal.getInstance(modalEl);
                if (modal) {
                    modal.hide();
                }
            } catch (err) {
                console.error("刪除操作失敗:", err);
                alert("刪除失敗：" + err.message);
                // 恢復按鈕狀態
                newConfirmBtn.disabled = false;
                newConfirmBtn.innerHTML = '<i class="bi bi-trash3 me-1"></i>刪除';
            }
        };
    }

    // 顯示對話框
    const modalEl = document.getElementById('deleteConfirmModal');
    if (modalEl) {
        const modal = new bootstrap.Modal(modalEl);
        modal.show();
    }
}
```

##### Step 3: 更新刪除按鈕使用統一 Modal

在 `bindSessionEvents` 函式中更新 delete-btn 邏輯：

```javascript
// 在 bindSessionEvents 函式中更新 delete-btn 邏輯
li.querySelector(".delete-btn").onclick = () => {
    const itemTitle = item.title || item.id;

    // 使用統一的刪除確認對話框
    showDeleteConfirm(
        `確定要刪除話題「${itemTitle}」嗎？\n此操作無法復原。`,
        async () => {
            const res = await fetch(`${apiUrl('/delete-chat')}/${item.id}`, { method: "DELETE" });
            const result = await res.json();

            if (res.ok && (result.status === 'success' || result.success)) {
                // 刪除成功後重新載入列表
                loadSessionList(currentPage);
                // 顯示成功訊息（可選）
                // alert("話題已刪除");
            } else {
                throw new Error(result.message || result.error || "刪除失敗");
            }
        }
    );
};
```

同理更新「清空聊天」按鈕：

```javascript
document.getElementById("clearChatBtn")?.addEventListener("click", () => {
    showDeleteConfirm(
        "你確定要清空當前聊天紀錄？此操作無法復原。",
        async () => {
            localStorage.removeItem("chatHistory");
            chatHistory = [];
            const box = document.getElementById("chatBox");
            box.innerHTML = "";
            scrollToBottom();
            // 顯示成功訊息（可選）
            // alert("聊天紀錄已清空");
        }
    );
});
```

**測試建議**:
- **手動測試**:
  1. 點擊任何刪除按鈕 → 應顯示 Bootstrap Modal
  2. 點擊「取消」→ 不執行刪除
  3. 點擊「刪除」→ 執行刪除並關閉 Modal
  4. 快速連續點擊多個刪除按鈕 → 應只顯示一個 Modal

---

### 3.2 P1 功能補強計畫（建議完成）

---

#### 【補強 1.4】權重總和雙重驗證 - 前端部分

**修改檔案**:
1. `templates/generate_cluster.html`（或配置頁面）
2. 新增 `static/js/config.js`

**實作步驟**:

##### Step 1: 新增配置頁面的 HTML（templates/generate_cluster.html 或 config.html）

在權重配置區域新增：

```html
<div class="weight-config-section">
    <h3>風險權重配置</h3>
    <p class="text-muted">調整嚴重度與頻率的權重比例，總和必須等於 1.0</p>

    <div class="mb-3">
        <label for="severity-weight" class="form-label">
            嚴重度權重
            <span class="badge bg-info ms-2">Severity Weight</span>
        </label>
        <input type="number" class="form-control" id="severity-weight"
               step="0.01" min="0" max="1" value="0.6">
        <div class="form-text">影響問題嚴重程度的權重</div>
    </div>

    <div class="mb-3">
        <label for="frequency-weight" class="form-label">
            頻率權重
            <span class="badge bg-info ms-2">Frequency Weight</span>
        </label>
        <input type="number" class="form-control" id="frequency-weight"
               step="0.01" min="0" max="1" value="0.4">
        <div class="form-text">影響問題發生頻率的權重</div>
    </div>

    <!-- 警告/成功訊息 -->
    <div id="weight-warning" class="alert" style="display:none;" role="alert"></div>

    <button id="save-weight-btn" class="btn btn-primary" disabled>
        <i class="bi bi-save me-2"></i>儲存權重配置
    </button>
</div>
```

##### Step 2: 新增前端驗證邏輯（static/js/config.js）

```javascript
// static/js/config.js

/**
 * 驗證權重總和
 * @returns {boolean} 是否有效
 */
function validateWeightSum() {
    const severityWeightEl = document.getElementById('severity-weight');
    const frequencyWeightEl = document.getElementById('frequency-weight');
    const warningEl = document.getElementById('weight-warning');
    const saveBtn = document.getElementById('save-weight-btn');

    if (!severityWeightEl || !frequencyWeightEl || !warningEl || !saveBtn) {
        return false;
    }

    const severityWeight = parseFloat(severityWeightEl.value) || 0;
    const frequencyWeight = parseFloat(frequencyWeightEl.value) || 0;
    const sum = severityWeight + frequencyWeight;

    const tolerance = 0.0001;  // 容忍誤差
    const isValid = Math.abs(sum - 1.0) < tolerance;

    // 更新 UI
    if (!isValid) {
        warningEl.textContent = `⚠️ 權重總和 ${sum.toFixed(4)} ≠ 1.0，請調整`;
        warningEl.className = 'alert alert-warning';
        warningEl.style.display = 'block';
        saveBtn.disabled = true;
    } else {
        warningEl.innerHTML = `<i class="bi bi-check-circle-fill me-2"></i>權重總和 = 1.0 ✓`;
        warningEl.className = 'alert alert-success';
        warningEl.style.display = 'block';
        saveBtn.disabled = false;
    }

    return isValid;
}

/**
 * 儲存權重配置
 */
async function saveWeightConfig() {
    const severityWeight = parseFloat(document.getElementById('severity-weight').value);
    const frequencyWeight = parseFloat(document.getElementById('frequency-weight').value);

    // 再次驗證
    if (!validateWeightSum()) {
        alert("權重總和不等於 1.0，無法儲存");
        return;
    }

    try {
        const response = await fetch('/api/config/weight', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                severity_weight: severityWeight,
                frequency_weight: frequencyWeight
            })
        });

        const result = await response.json();

        if (response.ok && (result.status === 'success' || result.success)) {
            alert("權重配置已儲存");
        } else {
            alert("儲存失敗：" + (result.message || result.error || "未知錯誤"));
        }
    } catch (err) {
        alert("發送錯誤：" + err.message);
    }
}

// 頁面載入時初始化
document.addEventListener('DOMContentLoaded', function() {
    const severityInput = document.getElementById('severity-weight');
    const frequencyInput = document.getElementById('frequency-weight');
    const saveBtn = document.getElementById('save-weight-btn');

    if (severityInput && frequencyInput && saveBtn) {
        // 綁定輸入事件
        severityInput.addEventListener('input', validateWeightSum);
        frequencyInput.addEventListener('input', validateWeightSum);

        // 綁定儲存按鈕
        saveBtn.addEventListener('click', saveWeightConfig);

        // 頁面載入時驗證一次
        validateWeightSum();
    }
});
```

##### Step 3: 在模板中引入 JS 檔案

在 `templates/generate_cluster.html` 或相關配置頁面的 `{% block scripts %}` 區塊中新增：

```html
{% block scripts %}
  {{ super() }}
  <script src="{{ url_for('static', filename='js/config.js') }}"></script>
{% endblock %}
```

**測試建議**:
- **手動測試**:
  1. 輸入 0.6 + 0.4 → 應顯示綠色成功訊息，啟用儲存按鈕
  2. 輸入 0.7 + 0.4 → 應顯示黃色警告訊息，禁用儲存按鈕
  3. 調整至總和 = 1.0 → 應即時更新 UI 並啟用按鈕

---

#### 【補強 1.5】群集名稱截斷邏輯

**修改檔案**: `services/cluster_service.py`

**實作步驟**:

在 `ClusterService` 類別中修改 `_generate_cluster_summary()` 方法（約在第 368-405 行附近）：

```python
def _generate_cluster_summary(self, group_df: pd.DataFrame, config_item: str, ai_category: str) -> str:
    """
    生成群集摘要（限制 30 字 + 省略號）

    Args:
        group_df: 群集 DataFrame
        config_item: 配置項目名稱
        ai_category: AI 分類名稱

    Returns:
        截斷後的群集名稱（最多 30 字 + "..."）
    """
    # 原有的 AI 摘要生成邏輯
    summaries = group_df['problemSummary'].tolist()[:5]  # 最多取前5筆
    combined_text = "\n".join(summaries)

    # 呼叫 AI 生成摘要
    try:
        if self.POWERAUTOMATE_SUMMARY_URL:
            response = requests.post(
                self.POWERAUTOMATE_SUMMARY_URL,
                json={"text": combined_text},
                timeout=30
            )
            if response.status_code == 200:
                summary = response.json().get("summary", f"{config_item}_{ai_category}_群組")
            else:
                log_error(f"AI summary generation failed with status {response.status_code}")
                summary = f"{config_item}_{ai_category}_群組"
        else:
            summary = f"{config_item}_{ai_category}_群組"
    except Exception as e:
        log_error(f"AI summary generation failed: {str(e)}")
        summary = f"{config_item}_{ai_category}_群組"

    # ✅ 新增：截斷邏輯
    max_length = self.MAX_CLUSTER_NAME_LENGTH
    if len(summary) > max_length:
        summary = summary[:max_length] + "..."
        log_info(f"Truncated cluster name to {max_length} chars: {summary}")

    # ✅ 新增：檔名系統相容性檢查（移除特殊字元）
    # 將檔案系統不允許的字元替換為底線
    invalid_chars_pattern = r'[/\\:*?"<>|]'
    original_summary = summary
    summary = re.sub(invalid_chars_pattern, '_', summary)

    if summary != original_summary:
        log_info(f"Replaced invalid chars in cluster name: {original_summary} -> {summary}")

    return summary.strip()
```

**測試建議**:
```bash
# 單元測試
pytest tests/unit/services/test_cluster_service.py::test_generate_cluster_summary_short -v
pytest tests/unit/services/test_cluster_service.py::test_generate_cluster_summary_truncate -v
pytest tests/unit/services/test_cluster_service.py::test_generate_cluster_summary_special_chars -v
```

**手動測試**:
1. 建立一個包含超長摘要的群集 → 確認名稱被截斷為 30 字 + "..."
2. 建立一個包含特殊字元的群集 → 確認特殊字元被替換為 "_"

---

### 3.3 P2 功能評估（視情況實作）

---

#### 【P2.1】召回率測試集建立

**狀態**: ❌ 未實作
**建議**: **延後至實際需求明確後再實作**

**理由**:
1. **需要大量人工標註工作**: 100 組查詢 × 2-5 個相關工單 = 至少 200-500 筆人工標註
2. **標註品質影響評估準確性**: 需要領域專家參與，確保標註的相關性判斷正確
3. **當前系統尚未明確定義召回率問題**: 無使用者反饋「找不到相關工單」

**替代方案**:
- **Phase 3A**: 先建立小型測試集（20-30 組）進行初步評估
- **Phase 3B**: 使用現有查詢日誌分析常見查詢模式
- **Phase 4**: 待 Phase 3 完成後再規劃完整的評估體系

**如需實作，參考計畫**:
```markdown
1. 從歷史工單中選取代表性查詢:
   - 簡單查詢 (30 組): 直接關鍵字匹配
   - 中等查詢 (50 組): 需語意理解
   - 困難查詢 (20 組): 需多步推理

2. 建立測試集檔案: `tests/fixtures/recall_test_set.json`

3. 實作評估腳本: `tests/performance/test_recall.py`

4. 設定驗收標準:
   - 整體召回率 ≥95%
   - 簡單查詢召回率 ≥98%
   - 中等查詢召回率 ≥95%
   - 困難查詢召回率 ≥85%
```

---

#### 【P2.2】任務佇列（RQ）

**狀態**: ❌ 未實作
**建議**: **暫不實作，當前架構已足夠**

**理由**:
1. **當前使用者數量 <10 人**: 根據 CLAUDE.md，系統為內部工具，使用者數量有限
2. **同步處理體驗良好**: 單一使用者上傳檔案時，同步處理提供即時反饋
3. **增加部署複雜度**: 需要額外部署 Redis 服務，增加維護成本

**觸發條件**:
- 同時上傳使用者數量 ≥10 人
- 出現明顯的並發處理瓶頸（如多人同時上傳導致超時）
- 需要更細緻的任務狀態追蹤（如任務佇列、進度查詢）

**如需實作，技術方案**:
```markdown
1. 安裝依賴:
   pip install redis rq

2. 實作佇列管理器: `core/queue.py`

3. 修改上傳路由: `api/upload_routes.py`
   - 將任務加入佇列
   - 返回 task_id

4. 新增任務狀態查詢 API: `/api/tasks/<task_id>`

5. 啟動 Worker:
   rq worker ticket_analysis
```

---

#### 【P2.3】跨平台支援（openpyxl）

**狀態**: ✅ **已在 Phase 1-1 完成（2025-11-19）**

**完成項目**:
- ✅ 完全移除 win32com 依賴
- ✅ 使用 OpenPyXL 實作 Excel 讀寫
- ✅ 使用 portalocker 進行跨平台檔案鎖定
- ✅ 支援 macOS、Linux、Windows
- ✅ 測試覆蓋率 87.87%（53 個測試全數通過）

**實作位置**:
- `utils/excel_client_openpyxl.py` - OpenPyXL 實作（369 行）
- `utils/excel_client.py` - 統一介面（Factory Pattern）
- `utils/resource_manager.py` - 檔案鎖定管理

**備註**: 此項目計畫文件中仍列為 P2 未完成，是因為文件未同步更新。

---

#### 【P2.4】使用者認證（Flask-Login）

**狀態**: ❌ 未實作
**建議**: **暫不實作，當前無明確需求**

**理由**:
1. **系統定位為內部工具**: CLAUDE.md 明確標示「內部工具，無使用者認證」
2. **通常部署於內網**: 已有網路層級的存取控制
3. **影響使用體驗**: 引入認證需要使用者記憶密碼、管理 session

**觸發條件**:
- 系統需要對外開放（如透過公網存取）
- 需要區分 Admin 與 User 權限
- 合規需求要求記錄操作者身份
- 需要審計日誌（Audit Log）

**如需實作，技術方案**:
```markdown
1. 安裝依賴:
   pip install flask-login

2. 實作 User 模型: `models/user.py`

3. 實作登入系統: `api/auth_routes.py`
   - /login (GET, POST)
   - /logout

4. 實作權限裝飾器: `@admin_required`

5. 保護路由:
   - 配置管理（僅 Admin）
   - 知識庫同步（僅 Admin）
   - 工單上傳（Admin + User）
   - RAG 查詢（Admin + User）
```

**替代方案**:
- 使用反向代理（Nginx）進行基本認證（HTTP Basic Auth）
- 使用 SSO（Single Sign-On）整合企業帳號系統（如 LDAP、Active Directory）

---

## 4. 技術疑慮與解決方案

### 4.1 會話列表分頁 - 效能疑慮

**問題描述**:
目前 `ChatRepository.list_sessions()` 採用「讀取所有 JSON → 記憶體篩選 → 分頁」的方式。當會話數量 >1000 時，可能出現效能瓶頸。

**問題位置**: `repositories/chat_repository.py:27-44`

**原因分析**:
```python
# 每次查詢都會讀取所有 JSON 檔案
for path in self.history_dir.glob("*.json"):
    data = self._read_json(path)  # ← 磁碟 I/O
    # ...
```

**風險評估**:
| 會話數量 | 風險等級 | 預期延遲 | 影響 |
|---------|---------|---------|------|
| <100 | 低 | <100ms | 無明顯延遲 |
| 100-500 | 中 | 1-2 秒 | 可接受 |
| >1000 | 高 | >5 秒 | 使用者體驗差 |

**解決方案**:

#### 方案 A: 快取優化（推薦，短期方案）

在 `ChatRepository` 中新增快取機制：

```python
class ChatRepository:
    def __init__(self, history_dir: Optional[str] = None):
        # ... 原有初始化
        self._session_cache = None
        self._cache_timestamp = None
        self._cache_ttl = 60  # 快取 60 秒

    def _get_cached_sessions(self) -> List[Dict]:
        """取得快取的會話列表"""
        import time
        now = time.time()

        if (self._session_cache is None or
            self._cache_timestamp is None or
            (now - self._cache_timestamp) > self._cache_ttl):
            # 快取過期，重新載入
            self._session_cache = self._load_all_sessions()
            self._cache_timestamp = now
            log_info(f"Reloaded session cache: {len(self._session_cache)} sessions")

        return self._session_cache

    def _load_all_sessions(self) -> List[Dict]:
        """載入所有會話（私有方法）"""
        sessions = []
        for path in self.history_dir.glob("*.json"):
            try:
                data = self._read_json(path)
                # ... 原有載入邏輯
                sessions.append({...})
            except Exception as exc:
                log_error(f"Failed to load chat session {path.name}: {exc}")
        return sessions

    def list_sessions(self, page, page_size, title_filter, date_start, date_end):
        """使用快取的會話列表進行篩選與分頁"""
        all_sessions = self._get_cached_sessions()

        # 篩選邏輯
        filtered = [s for s in all_sessions if ...]

        # 分頁邏輯
        # ...
```

**優點**:
- 實作簡單，對現有架構影響小
- 效能提升明顯（快取命中時 <10ms）
- 無需引入新的依賴

**缺點**:
- 快取期間新增的會話不會立即顯示
- 多程序部署時快取不同步（但通常是單一使用者操作，可接受）

**建議快取策略**:
- TTL: 60 秒（可配置）
- 快取清除: 當 `save_session()` 或 `delete_session()` 被呼叫時清除快取

---

#### 方案 B: SQLite 索引（長期方案）

如果未來會話數量持續增長（>5000），建議引入輕量級資料庫：

```python
# 建立索引表
CREATE TABLE chat_sessions (
    session_id TEXT PRIMARY KEY,
    title TEXT,
    created_at TEXT,
    last_message_time TEXT,
    message_count INTEGER
);

CREATE INDEX idx_created_at ON chat_sessions(created_at);
CREATE INDEX idx_title ON chat_sessions(title);

# 查詢範例
SELECT * FROM chat_sessions
WHERE title LIKE '%關鍵字%'
  AND created_at >= '2025-01-01'
  AND created_at <= '2025-01-31'
ORDER BY last_message_time DESC
LIMIT 20 OFFSET 0;
```

**優點**:
- 支援高效的索引查詢
- 可處理大量會話（>10,000）
- 支援複雜的篩選條件

**缺點**:
- 需要維護資料一致性（JSON 檔案 vs SQLite）
- 增加架構複雜度

**決策建議**:
- **短期（會話數 <1000）**: 採用方案 A（快取）
- **長期（會話數 >1000）**: 評估引入方案 B（SQLite）

---

### 4.2 會話標題驗證 - 字元計算問題

**問題描述**:
標題長度限制「100 字」，但中文、英文、emoji 的字元計算方式不同，可能導致顯示寬度與限制不符。

**潛在問題**:
```python
# 問題案例 1: 中文字
title = "測試" * 50  # 100 個中文字
len(title)  # → 100 ✅ 通過驗證
# 實際顯示寬度：約 200 個英文字元寬度

# 問題案例 2: Emoji
title = "🚀" * 50  # 50 個 emoji
len(title)  # → 50 ✅ 通過驗證
# 實際顯示寬度：約 100 個英文字元寬度

# 問題案例 3: 混合
title = "Test測試🚀" * 20  # 混合
len(title)  # → 120 ❌ 不通過
# 但實際顯示可能不長
```

**解決方案**:

#### 方案 A: 使用視覺寬度計算（推薦，精確方案）

```python
def get_display_width(text: str) -> int:
    """
    計算文字的視覺顯示寬度

    規則:
    - 全形字元（中文、日文等）: 寬度 = 2
    - 半形字元（英文、數字等）: 寬度 = 1
    - Emoji: 寬度 = 2
    """
    import unicodedata
    width = 0
    for char in text:
        ea_width = unicodedata.east_asian_width(char)
        if ea_width in ('F', 'W'):  # Fullwidth, Wide
            width += 2
        elif ea_width in ('N', 'Na', 'H', 'A'):  # Narrow, Halfwidth, Ambiguous
            width += 1
        else:
            width += 2  # 預設為全形
    return width

def _validate_session_title(self, title: str):
    """驗證會話標題（使用視覺寬度）"""
    if not title or not title.strip():
        raise ValidationError("INVALID_PARAMETER", "標題不能為空")

    title = title.strip()

    # 使用視覺寬度而非字元數
    display_width = get_display_width(title)
    max_width = 200  # 相當於 100 個全形字或 200 個半形字

    if display_width > max_width:
        raise ValidationError(
            "SESSION_TITLE_TOO_LONG",
            f"標題顯示寬度不可超過 {max_width}（目前 {display_width}）",
            details={
                "display_width": display_width,
                "max_width": max_width,
                "char_count": len(title)
            }
        )

    # ... 其他驗證邏輯
```

**優點**:
- 精確控制顯示效果
- 支援多語言與 emoji
- 使用標準 Python 庫（unicodedata）

**缺點**:
- 邏輯稍複雜
- 需要同步更新前端驗證邏輯

---

#### 方案 B: 簡單限制（簡化方案）

```python
# 將限制調整為 50 字，避免極端情況
MAX_TITLE_LENGTH = 50

def _validate_session_title(self, title: str):
    if len(title) > MAX_TITLE_LENGTH:
        raise ValidationError(
            "SESSION_TITLE_TOO_LONG",
            f"標題長度不可超過 {MAX_TITLE_LENGTH} 字（目前 {len(title)} 字）"
        )
```

**優點**:
- 實作簡單
- 前後端邏輯一致

**缺點**:
- 無法精確控制顯示效果
- 英文使用者可能覺得限制過於嚴格（50 個英文字符較短）

---

**決策建議**:
- **如果不需要支援多語言**: 採用方案 B（簡單限制）
- **如果需要精確控制顯示效果**: 採用方案 A（視覺寬度）

---

### 4.3 刪除確認對話框 - 非同步操作競爭問題

**問題描述**:
當使用者快速連續點擊多個刪除按鈕時，可能出現 Modal 狀態錯亂。

**問題場景**:
```
1. 使用者點擊「刪除會話 A」→ Modal 顯示「確定刪除 A？」
2. 使用者未確認，直接點擊「刪除會話 B」→ Modal 內容更新為「確定刪除 B？」
3. 使用者點擊「確認」→ 實際刪除的是 B
4. 使用者可能以為刪除的是 A → 造成困惑
```

**解決方案**:

在 `showDeleteConfirm()` 函式中新增鎖定機制：

```javascript
// 新增鎖定變數
let deleteModalLocked = false;

function showDeleteConfirm(message, onConfirm) {
    // 檢查是否已鎖定
    if (deleteModalLocked) {
        console.warn("刪除對話框已開啟，請先處理當前操作");
        return;
    }

    // 鎖定
    deleteModalLocked = true;

    // 設定訊息
    document.getElementById('deleteConfirmMessage').innerText = message;

    // 綁定確認事件
    const confirmBtn = document.getElementById('confirmDeleteBtn');
    const newConfirmBtn = confirmBtn.cloneNode(true);
    confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);

    newConfirmBtn.onclick = async function() {
        try {
            await onConfirm();
            const modal = bootstrap.Modal.getInstance(document.getElementById('deleteConfirmModal'));
            modal.hide();
        } catch (err) {
            console.error("刪除操作失敗:", err);
            alert("刪除失敗：" + err.message);
        } finally {
            deleteModalLocked = false;  // 解鎖
        }
    };

    // 監聽 Modal 關閉事件，解鎖
    const modalEl = document.getElementById('deleteConfirmModal');
    modalEl.addEventListener('hidden.bs.modal', function() {
        deleteModalLocked = false;
    }, { once: true });  // 只監聽一次

    // 顯示對話框
    const modal = new bootstrap.Modal(modalEl);
    modal.show();
}
```

**優點**:
- 防止重複觸發
- 確保使用者操作一致性
- 邏輯簡單

**缺點**:
- 略微降低操作流暢性（使用者必須等待當前 Modal 關閉）

**決策建議**: 建議採用，避免使用者困惑。

---

### 4.4 群集名稱截斷 - 中文字元與 Emoji 處理

**問題描述**:
直接使用 `summary[:30]` 截斷可能會切斷 emoji 或組合字元（如「👨‍👩‍👧‍👦」），導致顯示為 `�`。

**問題案例**:
```python
summary = "電腦無法開機問題處理🚀" * 3  # 包含 emoji
truncated = summary[:30]  # 可能切在 emoji 中間
print(truncated)  # → 電腦無法開機問題處理🚀電腦無法開機問題處理�
```

**解決方案**:

#### 方案 A: 使用 grapheme 庫（推薦，精確方案）

```python
def truncate_safely(text: str, max_length: int) -> str:
    """
    安全截斷文字，避免切斷 emoji 或組合字元

    Args:
        text: 原始文字
        max_length: 最大長度（以 grapheme 為單位）

    Returns:
        截斷後的文字（如果超過長度，會加上 "..."）
    """
    if len(text) <= max_length:
        return text

    try:
        import grapheme
        # 將文字分解為 grapheme clusters
        clusters = list(grapheme.graphemes(text))
        if len(clusters) <= max_length:
            return text
        # 取前 max_length 個 grapheme
        truncated = ''.join(clusters[:max_length])
        return truncated + "..."
    except ImportError:
        # 降級方案：使用簡單截斷（可能切斷 emoji）
        log_warning("grapheme library not installed, using simple truncation")
        return text[:max_length] + "..."

# 在 _generate_cluster_summary() 中使用
def _generate_cluster_summary(self, group_df: pd.DataFrame, config_item: str, ai_category: str) -> str:
    # ... AI 生成邏輯

    # 使用安全截斷
    max_length = self.MAX_CLUSTER_NAME_LENGTH
    summary = truncate_safely(summary, max_length)

    # ... 特殊字元替換邏輯
    return summary.strip()
```

**安裝依賴**:
```bash
pip install grapheme
```

**優點**:
- 精確處理 emoji 與組合字元
- 不會產生亂碼
- 支援所有 Unicode 標準

**缺點**:
- 需要額外依賴（grapheme）
- 略微增加處理時間（但可忽略不計）

---

#### 方案 B: 簡單截斷（降級方案）

維持原方案，但避免使用 emoji：

```python
def _generate_cluster_summary(self, group_df: pd.DataFrame, config_item: str, ai_category: str) -> str:
    # ... AI 生成邏輯

    # 簡單截斷
    max_length = self.MAX_CLUSTER_NAME_LENGTH
    if len(summary) > max_length:
        summary = summary[:max_length] + "..."

    # 移除 emoji（選擇性）
    summary = re.sub(r'[^\u0000-\uFFFF]', '', summary)

    # ... 特殊字元替換邏輯
    return summary.strip()
```

**優點**:
- 無需額外依賴
- 邏輯簡單

**缺點**:
- 可能切斷 emoji 導致亂碼
- 無法正確處理組合字元

---

**決策建議**:
- **如果不需要支援 emoji**: 採用方案 B（簡單截斷）
- **如果需要支援 emoji**: 採用方案 A（grapheme 庫）

---

## 5. 執行順序建議

### 5.1 優先執行項目（必須完成）

| 順序 | 項目 | 預估工時 | 風險等級 | 相依性 | 驗收方式 |
|-----|------|---------|---------|-------|---------|
| 1 | 補強 1.2 - 會話標題驗證 | 2 小時 | 低 | 無 | 手動測試 + 單元測試 |
| 2 | 補強 1.3 - 刪除確認對話框 | 3 小時 | 低 | 無 | 手動測試 |
| 3 | 補強 1.5 - 群集名稱截斷邏輯 | 1 小時 | 低 | 無 | 手動測試 + 單元測試 |
| 4 | 補強 1.4 - 權重驗證前端 | 2 小時 | 低 | 需要配置頁面 | 手動測試 |
| 5 | 補強 1.1 - 會話列表分頁與搜尋 | 6 小時 | 中 | 需先完成 1.2、1.3 | 手動測試 + 單元測試 |

**總計**: 14 小時（約 2 個工作日）

**建議排程**:
- **Day 1 上午（4 小時）**: 完成項目 1、2
- **Day 1 下午（4 小時）**: 完成項目 3、4
- **Day 2 全天（6 小時）**: 完成項目 5

---

### 5.2 執行順序說明

#### 為何先做標題驗證？
- **無相依性**: 可獨立實作與測試
- **風險低**: 邏輯簡單，不影響現有功能
- **效益高**: 防止無效標題進入系統

#### 為何刪除確認排第二？
- **統一 Modal 可重用**: 其他功能（如項目 5）也會使用
- **提升使用者體驗**: 防止誤刪除

#### 為何分頁搜尋排最後？
- **相依性高**: 需要先完成標題驗證（影響搜尋邏輯）與刪除確認（影響列表操作）
- **工時最長**: 涉及三層架構（Repository、Service、API、前端）

---

### 5.3 選擇性執行項目（可延後）

| 項目 | 建議時機 | 觸發條件 |
|------|---------|---------|
| P2.1 召回率測試集 | Phase 4 | 使用者反饋「找不到相關工單」 |
| P2.2 任務佇列（RQ） | Phase 4 | 同時上傳使用者數量 ≥10 人 |
| P2.4 使用者認證 | Phase 4 | 系統需要對外開放 |

---

## 6. 待決策事項

請您針對以下技術疑慮做出決策，以便後續實作：

### 6.1 會話列表分頁效能方案

**問題**: 當會話數量 >1000 時可能出現效能瓶頸

**選項**:
- [ ] **方案 A**: 快取優化（TTL 60 秒）
  - 優點: 實作簡單，效能提升明顯
  - 缺點: 快取期間新會話不立即顯示
- [ ] **方案 B**: SQLite 索引
  - 優點: 支援大量會話，查詢高效
  - 缺點: 增加架構複雜度

**建議**: 方案 A（短期），當會話數 >1000 時再評估方案 B

---

### 6.2 會話標題長度計算方式

**問題**: 中文、英文、emoji 的字元計算方式不同

**選項**:
- [ ] **方案 A**: 視覺寬度計算（精確）
  - 優點: 精確控制顯示效果，支援多語言
  - 缺點: 邏輯稍複雜
- [ ] **方案 B**: 簡單限制 50 字
  - 優點: 實作簡單
  - 缺點: 英文使用者可能覺得限制過嚴

**建議**: 方案 B（簡單限制），除非需要精確控制多語言顯示

---

### 6.3 刪除確認對話框鎖定機制

**問題**: 快速連續點擊可能造成 Modal 狀態錯亂

**選項**:
- [ ] **啟用鎖定機制**: 防止重複觸發
- [ ] **不啟用鎖定機制**: 依賴使用者操作習慣

**建議**: 啟用鎖定機制，避免使用者困惑

---

### 6.4 群集名稱 Emoji 支援

**問題**: 簡單截斷可能切斷 emoji 導致亂碼

**選項**:
- [ ] **方案 A**: 使用 grapheme 庫（精確）
  - 優點: 不會產生亂碼，支援所有 Unicode
  - 缺點: 需要額外依賴
- [ ] **方案 B**: 簡單截斷 + 移除 emoji
  - 優點: 無需額外依賴
  - 缺點: 可能切斷字元

**建議**: 方案 B（簡單截斷），除非 AI 生成的摘要經常包含 emoji

---

## 7. 測試計畫

### 7.1 單元測試清單

#### Repository 層
```bash
# tests/unit/repositories/test_chat_repository.py
- test_list_sessions_pagination()
- test_list_sessions_title_filter()
- test_list_sessions_date_filter()
- test_list_sessions_combined_filters()
- test_list_sessions_empty_result()
```

#### Service 層
```bash
# tests/unit/services/test_rag_service.py
- test_validate_session_title_valid()
- test_validate_session_title_too_long()
- test_validate_session_title_invalid_chars()
- test_validate_session_title_edge_cases()
- test_rename_session_with_validation()

# tests/unit/services/test_cluster_service.py
- test_generate_cluster_summary_short()
- test_generate_cluster_summary_truncate()
- test_generate_cluster_summary_special_chars()
```

### 7.2 整合測試清單

```bash
# tests/integration/test_chat_api.py
- test_list_sessions_with_pagination()
- test_list_sessions_with_filters()
- test_rename_session_validation_error()

# tests/integration/test_config_api.py
- test_update_weight_config_invalid_sum()
- test_update_weight_config_valid()
```

### 7.3 手動測試清單

#### 會話列表分頁與搜尋
- [ ] 每頁顯示 20 筆會話
- [ ] 上一頁/下一頁按鈕正常運作
- [ ] 標題搜尋即時生效
- [ ] 日期範圍篩選準確
- [ ] 無結果時顯示提示訊息

#### 會話標題驗證
- [ ] 輸入 101 字標題被阻擋（前端）
- [ ] 輸入特殊字元顯示錯誤訊息（前端）
- [ ] 後端驗證與前端一致
- [ ] 錯誤訊息清楚易懂

#### 刪除確認對話框
- [ ] 點擊刪除按鈕顯示 Bootstrap Modal
- [ ] 點擊「取消」不執行刪除
- [ ] 點擊「刪除」正確刪除項目
- [ ] Modal 關閉後可再次開啟

#### 權重驗證
- [ ] 輸入總和 ≠ 1.0 禁用儲存按鈕
- [ ] 輸入總和 = 1.0 啟用儲存按鈕
- [ ] 即時顯示警告/成功訊息

#### 群集名稱截斷
- [ ] 超過 30 字的名稱被截斷
- [ ] 特殊字元被替換為 "_"
- [ ] 截斷後的名稱可正常顯示

---

## 8. 風險評估與緩解策略

### 8.1 高風險項目

| 項目 | 風險描述 | 機率 | 影響 | 緩解策略 |
|------|---------|------|------|---------|
| 會話列表分頁 | 效能瓶頸（會話數 >1000） | 中 | 高 | 採用快取方案，監控效能指標 |
| 前端 JS 錯誤 | 瀏覽器相容性問題 | 低 | 中 | 在多個瀏覽器測試（Chrome、Firefox、Safari） |

### 8.2 中風險項目

| 項目 | 風險描述 | 機率 | 影響 | 緩解策略 |
|------|---------|------|------|---------|
| 標題驗證 | 多語言字元計算不準確 | 中 | 低 | 採用簡單限制（50 字），避免複雜邏輯 |
| Modal 鎖定 | 鎖定邏輯影響使用者體驗 | 低 | 低 | 可選擇性啟用，根據實際使用情況調整 |

### 8.3 低風險項目

| 項目 | 風險描述 | 機率 | 影響 | 緩解策略 |
|------|---------|------|------|---------|
| 群集名稱截斷 | Emoji 切斷導致亂碼 | 低 | 極低 | AI 生成的摘要通常不含 emoji |
| 權重驗證前端 | 浮點數精度問題 | 極低 | 極低 | 使用固定容忍誤差（0.0001） |

---

## 9. 驗收標準（Definition of Done）

### 9.1 P0 功能驗收標準

#### 1.1 會話列表分頁與搜尋
- [ ] 後端 API 支援 `page`, `page_size`, `title`, `date_start`, `date_end` 參數
- [ ] Repository 正確實作篩選與分頁邏輯
- [ ] 前端顯示分頁控制項（上一頁、下一頁、頁碼）
- [ ] 標題搜尋即時生效
- [ ] 日期範圍篩選準確
- [ ] 單元測試覆蓋率 ≥80%
- [ ] 手動測試通過

#### 1.2 會話標題驗證
- [ ] 前端即時驗證（≤100 字，無特殊字元）
- [ ] 後端 API 驗證（`rename_session` 方法）
- [ ] 錯誤訊息清楚易懂
- [ ] 單元測試覆蓋率 ≥90%
- [ ] 手動測試通過

#### 1.3 刪除確認對話框
- [ ] `templates/base.html` 新增統一 Modal
- [ ] 實作 `showDeleteConfirm()` 工具函式
- [ ] 會話刪除使用統一 Modal
- [ ] 清空聊天使用統一 Modal
- [ ] 手動測試通過

### 9.2 P1 功能驗收標準

#### 1.4 權重總和雙重驗證
- [ ] 前端即時驗證（總和 = 1.0）
- [ ] 禁用/啟用儲存按鈕邏輯
- [ ] 顯示警告/成功訊息
- [ ] 手動測試通過

#### 1.5 群集名稱截斷邏輯
- [ ] 實作截斷邏輯（30 字 + "..."）
- [ ] 實作特殊字元替換
- [ ] 單元測試覆蓋率 ≥80%
- [ ] 手動測試通過

---

## 10. 後續追蹤

### 10.1 文件更新

完成所有 P0、P1 功能後，請更新以下文件：

- [ ] `docs/schedule-mustupdate/plan/unfinish/plan_phase3_enhanced_features.md` - 標記已完成項目
- [ ] `CLAUDE.md` - 更新功能清單與架構說明
- [ ] `README.md` - 更新使用者指南（如有新功能）
- [ ] `docs/schedule-mustupdate/report/` - 新增完成報告

### 10.2 效能監控

建議建立效能監控機制：

```python
# core/metrics.py
import time
from functools import wraps

def track_performance(metric_name: str):
    """效能追蹤裝飾器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            elapsed = time.time() - start
            log_info(f"[Performance] {metric_name}: {elapsed:.3f}s")
            return result
        return wrapper
    return decorator

# 使用範例
@track_performance("list_sessions")
def list_sessions(self, ...):
    # ...
```

監控指標：
- 會話列表載入時間（目標 <500ms）
- 標題驗證時間（目標 <10ms）
- 權重配置儲存時間（目標 <100ms）

### 10.3 使用者回饋收集

建議在 Phase 3 完成後收集使用者回饋：

- 會話列表分頁是否易用？
- 標題驗證限制是否合理？
- 刪除確認是否過於繁瑣？

根據回饋調整實作。

---

## 11. 總結

### 11.1 關鍵發現

1. **計畫文件與實際實作存在顯著落差**: 整體完成度僅 27.8%
2. **P0 功能嚴重不足**: 會話列表分頁、標題驗證、刪除確認均未按計畫完成
3. **P2.3 已提前完成**: 跨平台支援在 Phase 1-1 完成，但文件未同步
4. **技術債務清晰**: 效能瓶頸、字元計算、非同步競爭等問題已識別

### 11.2 建議行動

1. **立即補齊 P0 功能**: 預估 2 個工作日，無技術風險
2. **決策技術方案**: 針對 4 個技術疑慮選擇實作方案
3. **延後 P2 功能**: 等待實際需求明確後再實作
4. **同步更新文件**: 確保計畫文件反映真實進度

### 11.3 成功指標

- [ ] P0 功能 100% 完成
- [ ] P1 功能 100% 完成
- [ ] 單元測試覆蓋率 ≥80%
- [ ] 手動測試全數通過
- [ ] 使用者回饋正面（易用性、穩定性）

---

## 12. 附錄

### 12.1 相關文件連結

- 原始計畫: `docs/schedule-mustupdate/plan/unfinish/plan_phase3_enhanced_features.md`
- 專案架構: `CLAUDE.md`
- 測試指南: `tests/README.md`
- API 文件: (待補充)

### 12.2 聯絡資訊

如有問題或需要進一步說明，請聯絡：
- 專案負責人: (待補充)
- 技術支援: (待補充)

---

**文件版本**: 1.0
**最後更新**: 2025-11-19
**下次審查日期**: Phase 3 完成後
