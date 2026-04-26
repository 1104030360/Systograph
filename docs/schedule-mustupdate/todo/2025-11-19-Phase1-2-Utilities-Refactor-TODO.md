# Phase 1-2: 工具層重構 (Utilities Refactor) - TODO

**建立日期**: 2025-11-19
**階段名稱**: Phase1-2-Utilities-Refactor
**目標**: 讓 `utils/excel_utils.py`、`build_kb.py` 全面使用 Phase 1-1 的 ExcelClient 與 ResourceManager，徹底移除 Win32/COM 程式碼

---

## 任務概覽

| 任務 | 預估工時 | 狀態 | 備註 |
|------|---------|------|------|
| Task 1: 讀取並分析現有程式碼 | 30min | ⏳ PENDING | 檢查 excel_utils.py, build_kb.py 現有實作 |
| Task 2: 重構 utils/excel_utils.py | 2hr | ⏳ PENDING | 移除 COM, 引入 ExcelClient |
| Task 3: 重構 build_kb.py | 1.5hr | ⏳ PENDING | 使用 safe_excel_operation() |
| Task 4: 全域搜尋並清理 COM 殘留 | 30min | ⏳ PENDING | 搜尋 win32com, taskkill, EXCEL.EXE |
| Task 5: 建立/更新單元測試 | 2hr | ⏳ PENDING | test_excel_utils.py, test_build_kb.py |
| Task 6: 執行測試並驗證覆蓋率 | 30min | ⏳ PENDING | 目標: excel_utils ≥90%, build_kb ≥85% |
| Task 7: 更新文件 | 30min | ⏳ PENDING | README, CLAUDE.md, AGENTS.md |
| Task 8: 最終驗收測試 | 30min | ⏳ PENDING | 跨平台測試 (macOS, Linux, Windows) |

**總預估工時**: ~8 小時

---

## Task 1: 讀取並分析現有程式碼 ⏳

### 目標
- 了解 `utils/excel_utils.py` 當前實作與 COM 依賴程度
- 了解 `build_kb.py` 的 Excel 操作流程
- 識別所有需要重構的函式

### 檢查清單
- [ ] 讀取 `utils/excel_utils.py` 完整內容
- [ ] 識別所有使用 win32com 的函式
- [ ] 讀取 `build_kb.py` 完整內容
- [ ] 列出所有需要修改的函式清單
- [ ] 搜尋專案中其他可能使用 COM 的檔案

### 預期輸出
- 需要重構的函式列表
- COM 依賴程度評估
- 風險點識別

---

## Task 2: 重構 utils/excel_utils.py ⏳

### 目標
- 移除所有 Win32/COM import
- 使用 Phase 1-1 的 ExcelClient 與 ResourceManager
- 保持函式簽名不變（向後相容）

### 檢查清單

#### 2.1 模組初始化
- [ ] 移除 `import win32com.client`
- [ ] 移除 `import pythoncom`
- [ ] 移除 `HAS_WIN32` capability flag
- [ ] 新增 `from utils.excel_client import get_excel_client`
- [ ] 新增 `from utils.resource_manager import safe_excel_operation, wait_for_file_unlock`
- [ ] 建立 `_excel_client = get_excel_client()`
- [ ] 新增 log: "Excel utils running in OpenPyXL-only mode"

#### 2.2 重構 `save_and_close_excel(filepath)`
- [ ] 檢查路徑存在性
- [ ] 若檔案被鎖定，呼叫 `wait_for_file_unlock()`
- [ ] 呼叫 `_excel_client.close_file_safely()`
- [ ] 根據回傳結果輸出適當 log
- [ ] 移除任何 COM Excel.Application 相關程式碼

#### 2.3 重構 `close_excel_if_open(filepath)`
- [ ] 重新定義為「檢查鎖檔 → 等待解鎖 → 回傳結果」
- [ ] 移除任何 Process 控制程式碼
- [ ] 移除 taskkill 相關邏輯
- [ ] 回傳 bool + 輸出 log

#### 2.4 重構 `ensure_excel_opened()`
- [ ] 新增 `@deprecated` 裝飾器與警告訊息
- [ ] 若 `refresh_all=True` 或 `update_links=True`，印出替代方案並回傳 False
- [ ] 若僅確認檔案存在，則檢查後回傳 True
- [ ] 新增明確的 deprecation 訊息："OpenPyXL 無法刷新外部連結，請改用資料來源 API 或手動流程"

#### 2.5 其他輔助函式
- [ ] 檢查所有格式化函式（欄寬、樣式等）
- [ ] 確保全部使用 `_excel_client` 而非 COM 物件
- [ ] 確保全部使用 `safe_excel_operation()` 包裝檔案操作

### 預期輸出
- 完全重構的 `utils/excel_utils.py`
- 無任何 COM/Win32 import
- 所有函式使用 Phase 1-1 API

---

## Task 3: 重構 build_kb.py ⏳

### 目標
- 刪除所有內部 Excel 相關函式
- 統一從 `excel_utils` 匯入
- 使用 `safe_excel_operation()` 包裝所有寫檔操作

### 檢查清單

#### 3.1 刪除遺留邏輯
- [ ] 刪除 `ensure_excel_opened()` 函式（如果有）
- [ ] 刪除 `close_excel_if_open()` 函式（如果有）
- [ ] 刪除 `kill_all_excel_processes()` 函式（如果有）
- [ ] 移除所有 Win32/COM import

#### 3.2 使用工具層 API
- [ ] 新增 `from utils.resource_manager import safe_excel_operation`
- [ ] 新增 `from utils.excel_utils import ...`（需要的函式）
- [ ] 將所有寫檔區塊包裝為 `with safe_excel_operation(...)`

#### 3.3 處理刷新外部連結需求
- [ ] 若流程需要同步 SharePoint，輸出提示訊息
- [ ] 移除任何嘗試刷新 Power Query 的程式碼
- [ ] 新增註解說明替代方案（Graph API / 手動刷新）

#### 3.4 清理註解
- [ ] 所有歷史 COM 流程註解標示為 "Legacy COM flow (已移除)"
- [ ] 刪除實作但保留必要的歷史說明

### 預期輸出
- 重構的 `build_kb.py`
- 無任何 Excel 相關函式定義
- 所有 Excel 操作透過工具層

---

## Task 4: 全域搜尋並清理 COM 殘留 ⏳

### 目標
- 確保專案中無任何 COM/Win32 殘留程式碼

### 檢查清單
- [ ] 執行 `grep -r "win32com" .` 並清理所有結果
- [ ] 執行 `grep -r "pythoncom" .` 並清理所有結果
- [ ] 執行 `grep -r "taskkill" .` 並清理所有結果
- [ ] 執行 `grep -r "EXCEL.EXE" .` 並清理所有結果
- [ ] 執行 `grep -r "Excel.Application" .` 並清理所有結果
- [ ] 檢查 `requirements.txt` 是否仍有 `pywin32`（如有則移除）

### 預期輸出
- 搜尋結果報告
- 所有 COM 相關字串已移除或標記為歷史

---

## Task 5: 建立/更新單元測試 ⏳

### 目標
- 為重構的函式建立完整測試
- 達成覆蓋率目標

### 檢查清單

#### 5.1 `tests/unit/utils/test_excel_utils.py`
- [ ] 測試 `save_and_close_excel()` 新行為
- [ ] 測試 `close_excel_if_open()` 檔案鎖偵測
- [ ] 測試 `ensure_excel_opened()` deprecation 行為
- [ ] 測試 `ensure_excel_opened()` 拋錯情境（refresh_all=True）
- [ ] 測試所有格式化函式使用 ExcelClient
- [ ] Mock `_excel_client` 與 `safe_excel_operation`
- [ ] 覆蓋率目標: ≥90%

#### 5.2 `tests/unit/scripts/test_build_kb.py` (新建)
- [ ] 測試 `safe_excel_operation()` 的使用
- [ ] 測試檔案寫入流程
- [ ] 測試錯誤處理（鎖檔、權限問題等）
- [ ] Mock FAISS 與 SQLite 操作
- [ ] 覆蓋率目標: ≥85%（Excel 互動區域）

#### 5.3 跨平台測試
- [ ] 在 macOS 上執行測試
- [ ] 在 Linux 上執行測試（如有環境）
- [ ] 在 Windows 上執行測試（如有環境）
- [ ] 確保檔案鎖定行為一致

### 預期輸出
- 完整的單元測試套件
- 覆蓋率報告顯示達標

---

## Task 6: 執行測試並驗證覆蓋率 ⏳

### 目標
- 確保所有測試通過
- 驗證覆蓋率達標

### 檢查清單
- [ ] 執行 `pytest tests/unit/utils/test_excel_utils.py -v`
- [ ] 執行 `pytest tests/unit/scripts/test_build_kb.py -v`
- [ ] 執行 `pytest tests/ --cov=utils.excel_utils --cov-report=term`
- [ ] 執行 `pytest tests/ --cov=build_kb --cov-report=term`
- [ ] 驗證 `excel_utils.py` 覆蓋率 ≥90%
- [ ] 驗證 `build_kb.py` Excel 區域覆蓋率 ≥85%
- [ ] 執行整合測試確保無迴歸: `pytest tests/integration/ -v`

### 預期輸出
- 所有測試通過
- 覆蓋率報告達標
- 無迴歸問題

---

## Task 7: 更新文件 ⏳

### 目標
- 同步更新所有相關文件

### 檢查清單
- [ ] 更新 CLAUDE.md - 標註 Phase 1-2 完成
- [ ] 更新 AGENTS.md - 新增 Phase 1-2 測試成果
- [ ] 更新 backend-arch.md - 更新 utils/ 與 scripts 說明
- [ ] 更新 README（如需要）- 說明手動刷新流程
- [ ] 新增/更新 utils/README.md - 說明 excel_utils 新 API

### 預期輸出
- 所有文件更新完成
- 準確反映 Phase 1-2 變更

---

## Task 8: 最終驗收測試 ⏳

### 目標
- 完整端到端驗證
- 確保跨平台相容性

### 檢查清單
- [ ] 執行完整測試套件: `pytest tests/ -v`
- [ ] 驗證 KB 重建流程: `python build_kb.py`
- [ ] 檢查無 COM 錯誤訊息
- [ ] 驗證檔案鎖定處理正確
- [ ] 確認 deprecation 警告正確顯示
- [ ] 執行 `pytest --collect-only -q` 確認測試數量
- [ ] 生成最終覆蓋率報告: `pytest tests/ --cov=. --cov-report=html`

### 預期輸出
- 所有驗收標準通過
- 完整測試報告
- 覆蓋率報告

---

## 驗收標準總覽

| 項目 | 驗收內容 | 狀態 |
|------|----------|------|
| **程式碼清潔** | 專案內不再有 `taskkill`、`win32com`、`pythoncom`、`Excel.Application`、`EXCEL.EXE` 等字串 | ⏳ |
| **工具層重構** | `utils/excel_utils.py` 全面使用 ExcelClient 與 ResourceManager | ⏳ |
| **腳本重構** | `build_kb.py` 所有 Excel 操作透過工具層進行 | ⏳ |
| **跨平台功能** | KB 重建流程在 macOS/Linux/Windows 均可執行 | ⏳ |
| **測試覆蓋率** | `excel_utils.py` ≥90%, `build_kb.py` ≥85% | ⏳ |
| **測試通過** | 所有單元測試與整合測試通過 | ⏳ |
| **文件更新** | CLAUDE.md, AGENTS.md, backend-arch.md 更新完成 | ⏳ |

---

## 風險與注意事項

### 1. Power Query / 外部連結需求
- **風險**: OpenPyXL 無法處理 Power Query 刷新
- **緩解**: 明確提示使用者手動刷新或使用 Graph API
- **影響**: `ensure_excel_opened()` 標記為 deprecated

### 2. 檔案鎖定行為差異
- **風險**: Linux/macOS 鎖定行為與 Windows 不同
- **緩解**: 使用 portalocker 統一行為，加強測試
- **影響**: 需要跨平台測試驗證

### 3. 現有呼叫點相容性
- **風險**: 其他模組可能仍依賴舊函式行為
- **緩解**: 保持函式簽名不變，只改內部實作
- **影響**: 需要全域搜尋並驗證所有呼叫點

### 4. 效能考量
- **風險**: OpenPyXL 可能比 COM 慢
- **緩解**: 使用 openpyxl 的 write_only mode（如需要）
- **影響**: 大檔案處理可能需要優化

---

## 完成標準

當以下條件全部滿足時，Phase 1-2 視為完成：

✅ 所有 Task 1-8 檢查清單項目完成
✅ 專案中無任何 COM/Win32 殘留程式碼
✅ 所有測試通過（單元 + 整合）
✅ 覆蓋率達標（excel_utils ≥90%, build_kb ≥85%）
✅ KB 重建流程在至少一個平台上驗證成功
✅ 所有文件更新完成
✅ Phase 1-2 完成報告撰寫完成

---

**預計完成日期**: 2025-11-19
**負責人**: Claude Code
**狀態**: 🔄 IN PROGRESS
