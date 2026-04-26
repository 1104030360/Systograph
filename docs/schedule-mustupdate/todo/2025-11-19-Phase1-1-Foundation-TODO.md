# Phase 1-1: 基礎設施建立 - TODO

**建立日期**: 2025-11-19
**階段目標**: 建立 OpenPyXL-only Excel 操作抽象層，完全移除 COM 依賴
**預估時間**: 2.5 天
**參考文件**: `/Users/linjunting/Desktop/IT_Ticket_System備份/docs/error/Excel-COM-error/phase1-1-foundation.md`

---

## 當前狀態分析

### 已存在檔案
- ✅ `utils/excel_client.py` - 存在但仍包含 COM 支援（需修改）
- ✅ `utils/resource_manager.py` - 存在且符合需求
- ❌ `utils/excel_client_openpyxl.py` - **不存在，需建立**

### 測試狀況
- ❌ `tests/unit/utils/test_excel_client_factory.py` - 不存在
- ❌ `tests/unit/utils/test_excel_client_openpyxl.py` - 不存在
- ❌ `tests/unit/utils/test_resource_manager.py` - 不存在
- ⚠️ `tests/unit/utils/test_excel_utils.py` - 存在但測試舊版 excel_utils

---

## 工作項目清單

### Task A: 修改 excel_client.py（OpenPyXL-only）
**預估時間**: 0.5 天
**優先級**: 🔴 高

#### 子任務
- [ ] **A.1** 移除所有 COM 相關程式碼
  - 刪除 `client_type="com"` 分支
  - 刪除 `import win32com.client` 相關程式碼
  - 刪除 ComExcelClient 相關 import

- [ ] **A.2** 修改 `get_excel_client()` 工廠函式
  - 移除 `client_type` 參數（或將其標記為 deprecated）
  - 永遠返回 `OpenpyxlExcelClient()`
  - 加入 log: "✅ OpenPyXL-only mode (跨平台)"
  - 移除所有環境變數 `EXCEL_CLIENT_TYPE` 判斷

- [ ] **A.3** 更新 docstring
  - 明確標示「OpenPyXL 是唯一實作」
  - 加入註記：「COM 已於 Phase 1-1 完全淘汰」
  - 更新範例程式碼

- [ ] **A.4** 驗證修改
  - 確保檔案通過語法檢查
  - 確保沒有任何 Windows 特定程式碼

**驗收標準**:
- `get_excel_client()` 永遠返回 `OpenpyxlExcelClient`
- 檔案中沒有任何 COM/pywin32/taskkill 相關程式碼
- Docstring 清楚說明 OpenPyXL-only 策略

---

### Task B: 建立 excel_client_openpyxl.py
**預估時間**: 1.5 天
**優先級**: 🔴 高

#### 子任務
- [ ] **B.1** 建立基礎類別結構
  ```python
  class OpenpyxlExcelClient(ExcelClient):
      """OpenPyXL 實作的 Excel 客戶端（跨平台）"""
  ```

- [ ] **B.2** 實作 `read_excel()` 方法
  - 使用 `pandas.read_excel(engine='openpyxl')`
  - 支援單頁/多頁讀取
  - 返回統一格式: `{"success": bool, "data": DataFrame/dict, "error": str}`
  - 錯誤處理：檔案不存在、格式錯誤、權限問題

- [ ] **B.3** 實作 `write_excel()` 方法
  - 使用 `pandas.to_excel(engine='openpyxl')`
  - 支援三種模式:
    - `"overwrite"` - 覆寫整個檔案
    - `"append"` - 附加到現有工作表
    - `"new_sheet"` - 新增工作表
  - 錯誤處理：磁碟空間、權限、檔案鎖定

- [ ] **B.4** 實作 `apply_formatting()` 方法
  - **自動欄寬調整** (`auto_width: bool`)
    - 使用 OpenPyXL 的 column_dimensions
  - **凍結窗格** (`freeze_panes: str`)
    - 例如 "A2" 凍結第一列
  - **標題樣式** (`header_style: dict`)
    - 粗體字型 (`Font(bold=True)`)
    - 背景色 (`PatternFill`)
    - 字型色 (`Font(color=...)`)
  - **條件格式** (`conditional_format: dict`)
    - 使用 `CellIsRule` 或 `FormulaRule`
    - 支援顏色填充

- [ ] **B.5** 實作 `is_file_locked()` 方法
  - 使用 `portalocker` 檢查檔案鎖
  - 跨平台一致行為
  - 非阻塞式檢查

- [ ] **B.6** 實作 `close_file_safely()` 方法
  - OpenPyXL 是即時寫入，返回 no-op 訊息
  - 返回格式: `{"success": True, "message": "OpenPyXL 即時寫入，無需關閉"}`

- [ ] **B.7** 錯誤處理與 logging
  - 所有方法都要有 try-except
  - 使用 `core.logger` 記錄操作
  - 錯誤訊息要清楚且可操作

**驗收標準**:
- 所有抽象方法都已實作
- 讀寫、格式化功能完整且可用
- 錯誤處理涵蓋主要異常情境
- 程式碼覆蓋率 ≥ 90%

---

### Task C: 驗證 resource_manager.py
**預估時間**: 0.5 天
**優先級**: 🟡 中

#### 子任務
- [ ] **C.1** 檢視現有實作
  - 確認 `safe_excel_operation()` 符合需求
  - 確認 `wait_for_file_unlock()` 符合需求

- [ ] **C.2** 改進（若需要）
  - 加強錯誤訊息
  - 改進 logging
  - 確保跨平台一致性

- [ ] **C.3** 與 excel_client 整合測試
  - 確保兩者配合良好

**驗收標準**:
- `safe_excel_operation()` 能正確處理檔案鎖
- `wait_for_file_unlock()` 能正確輪詢
- 覆蓋率 ≥ 85%

---

### Task D: 建立單元測試
**預估時間**: 1 天
**優先級**: 🔴 高

#### D.1 test_excel_client_factory.py
- [ ] 測試 `get_excel_client()` 永遠返回 `OpenpyxlExcelClient`
- [ ] 測試無法指定 COM 模式
- [ ] 測試 logging 輸出

#### D.2 test_excel_client_openpyxl.py
- [ ] **讀取測試**
  - 測試讀取單頁 Excel
  - 測試讀取多頁 Excel
  - 測試檔案不存在情況
  - 測試格式錯誤檔案

- [ ] **寫入測試**
  - 測試 overwrite 模式
  - 測試 append 模式
  - 測試 new_sheet 模式
  - 測試寫入失敗情況（權限、空間）

- [ ] **格式化測試**
  - 測試自動欄寬調整
  - 測試凍結窗格
  - 測試標題樣式（粗體、顏色）
  - 測試條件格式

- [ ] **檔案鎖測試**
  - 測試 `is_file_locked()` 正常情況
  - 測試檔案被鎖定情況

- [ ] **關閉檔案測試**
  - 測試 `close_file_safely()` no-op 行為

- [ ] **錯誤處理測試**
  - 測試各種異常情況
  - 測試錯誤訊息格式

#### D.3 test_resource_manager.py
- [ ] **safe_excel_operation 測試**
  - 測試正常操作
  - 測試檔案鎖定與重試
  - 測試重試失敗情況
  - 測試 Context Manager 清理

- [ ] **wait_for_file_unlock 測試**
  - 測試檔案未鎖定情況
  - 測試檔案鎖定情況
  - 測試逾時情況
  - 測試檔案不存在情況

- [ ] **FileLockedError 測試**
  - 測試異常拋出
  - 測試錯誤訊息

**驗收標準**:
- 所有測試通過
- 覆蓋率:
  - `excel_client_openpyxl.py` ≥ 90%
  - `resource_manager.py` ≥ 85%
  - `excel_client.py` (factory) ≥ 95%
- 測試涵蓋 happy path 與 edge cases

---

### Task E: 文件更新
**預估時間**: 0.5 天
**優先級**: 🟡 中

#### 子任務
- [ ] **E.1** 更新 CLAUDE.md
  - 加入 OpenPyXL-only 介面說明
  - 加入使用範例
  - 標記 COM 已淘汰

- [ ] **E.2** 更新 README.md
  - 更新技術棧說明
  - 移除 Windows 特定需求
  - 加入跨平台說明

- [ ] **E.3** 更新 backend-arch.md
  - 加入新的 Excel 客戶端架構說明
  - 更新模組責任說明

- [ ] **E.4** 建立使用範例（選配）
  - `examples/openpyxl_client_example.py`
  - 示範基本讀寫操作
  - 示範格式化功能

**驗收標準**:
- 所有文件都標示 OpenPyXL-only
- 文件中沒有 COM 相關敘述（除歷史註記）
- 範例程式碼可執行且正確

---

## 測試執行計畫

### 單元測試
```bash
# 啟動虛擬環境
source .venv/bin/activate

# 執行新建立的測試
pytest tests/unit/utils/test_excel_client_factory.py -v
pytest tests/unit/utils/test_excel_client_openpyxl.py -v
pytest tests/unit/utils/test_resource_manager.py -v

# 執行所有 utils 層測試
pytest tests/unit/utils/ -v

# 檢查覆蓋率
pytest tests/unit/utils/ --cov=utils --cov-report=html --cov-report=term
open htmlcov/index.html
```

### 覆蓋率目標
- `utils/excel_client.py`: ≥ 95%
- `utils/excel_client_openpyxl.py`: ≥ 90%
- `utils/resource_manager.py`: ≥ 85%

---

## 風險與注意事項

### 🔴 高風險
1. **Power Query/VBA 功能缺口**
   - OpenPyXL 無法刷新外部連結
   - 需在文件中明確標示
   - 建議後續使用 Microsoft Graph API

2. **現有程式碼尚未接軌**
   - Phase 1-1 只建立新檔案
   - 舊的 `excel_utils.py` 仍在使用中
   - Phase 1-2 才會進行遷移

### 🟡 中風險
3. **portalocker 平台差異**
   - 需在 macOS/Linux/Windows 測試
   - 檔案鎖行為可能不一致

4. **測試耗時**
   - 格式化測試需頻繁寫檔
   - 建議使用 `tmp_path` fixture
   - 測試後自動清理

### 🟢 低風險
5. **相依套件**
   - pandas, openpyxl, portalocker 已安裝
   - 無新增依賴

---

## 完成檢查清單

### 程式碼
- [ ] `utils/excel_client.py` - 已移除 COM 支援
- [ ] `utils/excel_client_openpyxl.py` - 已建立並實作所有方法
- [ ] `utils/resource_manager.py` - 已驗證符合需求

### 測試
- [ ] `tests/unit/utils/test_excel_client_factory.py` - 已建立
- [ ] `tests/unit/utils/test_excel_client_openpyxl.py` - 已建立
- [ ] `tests/unit/utils/test_resource_manager.py` - 已建立
- [ ] 所有測試通過（100%）
- [ ] 覆蓋率達標（≥85%）

### 文件
- [ ] CLAUDE.md - 已更新
- [ ] README.md - 已更新
- [ ] backend-arch.md - 已更新
- [ ] 使用範例 - 已建立（選配）

### 驗證
- [ ] 在 macOS 測試通過
- [ ] 在 Linux 測試通過（若可能）
- [ ] 在 Windows 測試通過（若可能）
- [ ] 無任何 COM/pywin32 相關程式碼
- [ ] Logging 輸出一致

---

## 下一階段預告

**Phase 1-2**: 工具層遷移（Utilities Migration）
- 更新 `excel_utils.py` 使用新的 `ExcelClient`
- 移除所有舊的 COM 相關函式
- 更新所有呼叫者

**預計開始日期**: Phase 1-1 完成後 1 天內
**參考文件**: `docs/error/Excel-COM-error/phase1-2-utilities.md`

---

**建立者**: Claude Code
**最後更新**: 2025-11-19
