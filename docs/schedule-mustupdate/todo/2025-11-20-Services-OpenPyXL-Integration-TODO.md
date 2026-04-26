# Phase 1-4: Services Layer OpenPyXL Integration - TODO

**建立日期**: 2025-11-20
**任務**: 服務層整合 OpenPyXL，完全移除 COM 依賴

---

## 目標

完全移除服務層對 COM 函式的依賴，改用 OpenPyXL + ManualSyncStrategy，實現真正的跨平台支援。

---

## 階段清單

### ✅ 階段 0: 更新專案文件 (30分鐘)
- [ ] 更新 CLAUDE.md 專案結構
- [ ] 更新 AGENTS.md
- [ ] 更新 backend-arch.md
- [ ] 更新 frontend-arch.md

### ⏳ 階段 1: 依賴注入 (1小時)
- [ ] TicketService 加入 excel_client, sync_strategy 參數
- [ ] ClusterService 加入 excel_client, sync_strategy 參數
- [ ] 更新 __init__ 方法，使用工廠函式
- [ ] 更新測試 fixtures

### ⏳ 階段 2: TicketService 重構 (2小時)
- [ ] 重寫 save_analysis_files() 使用 safe_excel_operation()
- [ ] 實作 _handle_sync_result() 方法
- [ ] 實作 _notify_manual_sync_required() 方法
- [ ] 移除所有 save_and_close_excel, ensure_excel_opened 呼叫
- [ ] 移除 is_file_locked 檢查

### ⏳ 階段 3: ClusterService 重構 (2.5小時)
- [ ] 重寫 _cluster_excel_export() 使用 safe_excel_operation()
- [ ] 重寫 _summarize_group_to_excel() 使用 safe_excel_operation()
- [ ] 實作 _handle_sync_result() 方法
- [ ] 移除 11處 COM 函式呼叫
- [ ] 統一使用 sync_strategy 處理同步

### ⏳ 階段 4: pending_sync.json 管理 (1小時)
- [ ] 確認 utils/pending_sync.py 可用
- [ ] 在服務層加入 _log_pending_sync() 方法
- [ ] 在服務層加入 _handle_sync_result() 方法
- [ ] 更新 log 訊息格式

### ⏳ 階段 5: 整合測試 (2小時)
- [ ] 建立 tests/integration/test_ticket_service_sync.py
- [ ] 建立 tests/integration/test_cluster_service_sync.py
- [ ] 測試 MANUAL_PENDING 狀態處理
- [ ] 測試 FAILED 狀態處理
- [ ] 測試 pending_sync.json 更新

### ⏳ 階段 6: 全平台測試驗證 (1小時)
- [ ] 執行 pytest tests/unit -v
- [ ] 執行 pytest tests/integration -v
- [ ] 驗證無 COM 函式呼叫 (grep 檢查)
- [ ] 驗證 pending_sync.json 正確產生
- [ ] 確認 950+ 測試通過

---

## 驗收標準

| 項目 | 標準 |
|------|------|
| **程式碼** | 無任何 save_and_close_excel, ensure_excel_opened, kill_all_excel_processes 呼叫 |
| **功能** | Ticket/Cluster 流程在 macOS/Linux/Windows 正常執行 |
| **測試** | 所有測試通過，無回歸 |
| **UX** | Log 中顯示明確的手動同步指引 |
| **資料** | pending_sync.json 符合規範 |

---

## Linus 品味檢查

- [ ] **簡潔**: 消除所有 `if is_file_locked` 特殊分支
- [ ] **實用**: 解決真實的跨平台問題
- [ ] **不破壞**: 保持所有公開 API 簽名
- [ ] **好品味**: 統一流程，無特殊情況

---

**預估總時間**: 10 小時
