# IT Ticket Analysis System - 實作計劃

本目錄包含 IT Ticket Analysis System 架構重構與功能擴展的完整實作計劃。

---

## 📋 文件概覽

| 檔案 | 階段 | 時程 | 狀態 | 說明 |
|------|------|------|--------|------|
| [finish/phase1_architecture_refactor.md](finish/phase1_architecture_refactor.md) | Phase 1 | 2-3 週 | ⚠️ **部分完成** | 架構重構：已創建分層結構，但 Services 層未整合（實際完成度 35-40%） |
| **[unfinish/README.md](unfinish/README.md)** | **Phase 1 補完** | **9-13 小時** | 📋 **待開始** | **補完計劃總覽**：真正實現三層架構 (Services 整合 + Blueprints 瘦身 + Analysis 清理) |
| [unfinish/phase1-1-services-integration.md](unfinish/phase1-1-services-integration.md) | Phase 1-1 | 4-6 小時 | 📋 待開始 | Services 整合：建立 API → Services 調用關係 |
| [unfinish/phase1-2-blueprints-cleanup.md](unfinish/phase1-2-blueprints-cleanup.md) | Phase 1-2 | 3-4 小時 | 📋 待開始 | Blueprints 瘦身：移除業務邏輯，確保只負責路由 |
| [unfinish/phase1-3-analysis-final-cleanup.md](unfinish/phase1-3-analysis-final-cleanup.md) | Phase 1-3 | 2-3 小時 | 📋 待開始 | Analysis.py 最終清理：移除殘留業務邏輯和冗餘路由 |
| [phase2_testing_optimization.md](phase2_testing_optimization.md) | Phase 2 | 2-3 週 | ⏸️ **暫停** | 測試與優化：等待 Phase 1 補完後繼續 |
| [phase3_enhanced_features.md](phase3_enhanced_features.md) | Phase 3 | 1-2 週 | 📋 計畫中 | 增強功能：實作待規格化功能與進階功能 |
| [decisions_and_open_issues.md](decisions_and_open_issues.md) | 全階段 | - | 📖 參考 | 開放問題與決策點：需與團隊討論的關鍵決策 |

---

## 🚨 重要更新 (2025-11-05)

**Phase 1 實際完成度**: ~35-40% (非報告宣稱的 100%)

**問題發現**:
- ✅ 分層結構已創建（api/, services/, utils/）
- ❌ Services 層完全未被使用（grep "from services" api/*.py 無結果）
- ❌ Blueprints 仍包含 1752 行業務邏輯
- ❌ 三層架構並未真正建立

**補救措施**:
- 已創建 Phase 1-1/1-2/1-3 補完計劃（見 [unfinish/README.md](unfinish/README.md)）
- 需額外 9-13 小時完成真正的三層架構整合
- Phase 2 測試計劃暫停，等待 Phase 1 補完

詳細調查報告: [PHASE1_REALITY_CHECK.md](../codex-review/PHASE1_REALITY_CHECK.md)

---

## 🎯 總體目標

**核心目標**:
- 建立清晰的分層架構 (API → Services → Repositories)
- 達成 70% 測試覆蓋率，確保重構安全
- 提升系統可維護性與可擴展性

**非目標** (避免過度工程):
- ❌ 微服務拆分
- ❌ 容器化部署 (K8s/Docker)
- ❌ 資料庫遷移至 PostgreSQL
- ❌ 前端框架重寫 (Vue/React)

---

## 📅 實作路線圖

```
┌─────────────────────────────────────────────────────────────────┐
│                    Phase 1 (2-3 週) - ⚠️ 部分完成                 │
│                       架構重構 - 必須執行                          │
├─────────────────────────────────────────────────────────────────┤
│  Week 1: 建立骨架 ✅ 完成                                         │
│    - 創建目錄結構 (api/, services/, repositories/, core/)        │
│    - 實作 5 個 Blueprints                                        │
│    - 統一錯誤處理器                                               │
├─────────────────────────────────────────────────────────────────┤
│  Week 2: 抽取業務邏輯 ⚠️ 部分完成                                 │
│    - 實作 5 個 Services ✅ 已創建（但未使用）                      │
│    - 整合現有邏輯 ❌ 未完成（Services 孤立存在）                   │
├─────────────────────────────────────────────────────────────────┤
│  Week 3: Repositories 層與依賴注入 ❌ 未開始                       │
│    - 實作 6 個 Repositories                                      │
│    - 重構 Analysis.py (<500 行)                                  │
│    - 驗證所有功能正常運作                                          │
└─────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────┐
│                  Phase 1 補完 (9-13 小時) - 📋 待開始              │
│                      真正實現三層架構                              │
├─────────────────────────────────────────────────────────────────┤
│  Phase 1-1: Services 整合 (4-6 小時)                             │
│    - 修改 Blueprints 以導入並使用 Services                        │
│    - 建立 API → Services 調用關係                                │
│    - 減少 Blueprints 代碼從 1752 到 <920 行                      │
├─────────────────────────────────────────────────────────────────┤
│  Phase 1-2: Blueprints 瘦身 (3-4 小時)                           │
│    - 移除輔助函數至 Utils                                         │
│    - 簡化路由函數至 <30 行                                        │
│    - 減少 Blueprints 代碼從 920 到 <800 行                       │
├─────────────────────────────────────────────────────────────────┤
│  Phase 1-3: Analysis.py 最終清理 (2-3 小時)                      │
│    - 移除業務邏輯函數至 Services/Utils                            │
│    - 移除冗餘路由至 Blueprints                                    │
│    - 減少 Analysis.py 從 463 到 <350 行                         │
└─────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────┐
│                         Phase 2 (2-3 週)                         │
│                      測試與優化 - 必須執行                         │
├─────────────────────────────────────────────────────────────────┤
│  Week 1: 建立測試框架                                             │
│    - 安裝 pytest, pytest-cov, pytest-mock                       │
│    - 建立測試目錄結構 (unit/, integration/, e2e/)               │
│    - 實作 conftest.py (共用 fixtures)                            │
├─────────────────────────────────────────────────────────────────┤
│  Week 2: 單元測試                                                 │
│    - Services 層測試 (5 個服務)                                   │
│    - Utilities 層測試 (4 個工具模組)                              │
│    - Agents 層測試 (4 個 Agent)                                  │
│    - 達成 50% 覆蓋率                                              │
├─────────────────────────────────────────────────────────────────┤
│  Week 3: 整合測試與優化                                           │
│    - API Endpoints 測試                                          │
│    - RAG 多代理協作測試                                           │
│    - 知識庫同步流程測試                                            │
│    - 達成 70% 覆蓋率                                              │
├─────────────────────────────────────────────────────────────────┤
│  Week 4 (可選): 效能優化                                          │
│    - cProfile 效能分析                                           │
│    - 識別並優化 Top 3 瓶頸                                        │
│    - LLM 快取、Embedding 批次處理、Excel 讀寫優化                  │
└─────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────┐
│                         Phase 3 (1-2 週)                         │
│                      增強功能 - 可選執行                           │
├─────────────────────────────────────────────────────────────────┤
│  Week 1: P0 高優先級功能                                          │
│    - 會話列表分頁與搜尋 (每頁 20 筆)                               │
│    - 會話標題驗證 (≤100 字，禁止特殊字元)                          │
│    - 刪除確認對話框 (統一 Bootstrap Modal)                        │
│    - 權重總和雙重驗證 (前端 + 後端)                                │
│    - 群集名稱截斷邏輯 (30 字 + 省略號)                             │
├─────────────────────────────────────────────────────────────────┤
│  Week 2: P1-P2 中低優先級功能 (視時間而定)                         │
│    - 召回率測試集建立 (100 組標註)                                 │
│    - 任務佇列 (RQ)                                               │
│    - 跨平台支援 (openpyxl)                                       │
│    - 使用者認證 (Flask-Login)                                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📂 專案結構 (重構後)

```
/
├── Analysis.py                     # Flask 主應用 (500 行，僅初始化與註冊)
├── run_analysis.py                 # 啟動腳本
├── api/                            # API 層 (Blueprints)
│   ├── upload_routes.py            # 工單上傳路由
│   ├── chat_routes.py              # RAG 對話路由
│   ├── cluster_routes.py           # 聚類分析路由
│   ├── config_routes.py            # 系統配置路由
│   └── history_routes.py           # 歷史記錄路由
├── services/                       # 業務邏輯層
│   ├── ticket_service.py           # 工單處理服務
│   ├── rag_service.py              # RAG 查詢服務
│   ├── risk_service.py             # 風險評分服務
│   ├── cluster_service.py          # 聚類分析服務
│   └── kb_service.py               # 知識庫同步服務
├── repositories/                   # 資料存取層
│   ├── ticket_repo.py              # 工單資料存取
│   ├── config_repo.py              # 配置資料存取
│   ├── chat_repo.py                # 對話記錄存取
│   ├── faiss_repo.py               # FAISS 索引操作
│   ├── category_repo.py            # 類別對照表存取
│   └── sentence_db_repo.py         # 高風險句子庫存取
├── core/                           # 核心基礎設施
│   ├── error_handler.py            # 統一錯誤處理
│   ├── config_loader.py            # 配置載入
│   ├── database.py                 # 資料庫連接管理
│   └── logger.py                   # 日誌管理
├── utils/                          # 工具函數
│   ├── ai_utils.py                 # AI 工具 (LLM, 快取)
│   ├── excel_utils.py              # Excel 處理
│   ├── vector_utils.py             # 向量化工具
│   └── validation_utils.py         # 輸入驗證
├── agents/                         # RAG 多代理系統 (保持現有)
│   ├── semantic_agent.py
│   ├── sql_agent.py
│   ├── hybrid_agent.py
│   └── followup_agent.py
├── tests/                          # 測試 (新增)
│   ├── conftest.py                 # 共用 fixtures
│   ├── unit/                       # 單元測試
│   │   ├── services/
│   │   ├── utils/
│   │   └── agents/
│   ├── integration/                # 整合測試
│   │   ├── test_api_endpoints.py
│   │   ├── test_rag_system.py
│   │   └── test_kb_sync.py
│   ├── e2e/                        # E2E 測試 (可選)
│   ├── performance/                # 效能測試
│   └── fixtures/                   # 測試資料
├── gptChat.py                      # RAG 編排核心 (保持)
├── build_kb.py                     # 知識庫建構 (保持)
├── SmartScoring.py                 # 風險評分引擎 (保持)
└── gpt_utils.py                    # AI 工具函數 (保持)
```

---

## 🎯 各階段目標與驗收標準

### Phase 1: 架構重構

**目標**:
- Analysis.py 從 2615 行降至 <500 行
- 建立清晰的三層架構
- 統一錯誤處理格式

**驗收標準**:
```bash
# 1. 程式碼行數檢查
wc -l Analysis.py  # 應 <500 行

# 2. 目錄結構檢查
ls -R api/ services/ repositories/ core/

# 3. 功能驗證 (手動測試)
python run_analysis.py
# 測試: 上傳 → 分析 → 聚類 → RAG 查詢 → 配置管理
```

### Phase 2: 測試與優化

**目標**:
- 測試覆蓋率達 70%
- Services 層 & Agents 層達 80%
- 建立 CI/CD 自動化測試

**驗收標準**:
```bash
# 1. 執行所有測試
pytest tests/ -v --cov=. --cov-report=html

# 2. 檢查覆蓋率
open htmlcov/index.html  # 應顯示 ≥70%

# 3. 效能測試
pytest tests/performance/ -v --durations=10
```

### Phase 3: 增強功能

**目標**:
- 實作 P0 高優先級功能 (5 項)
- 視時間實作 P1-P2 功能

**驗收標準**:
```bash
# 功能驗證 (手動測試)
# 1. 會話列表分頁 → 檢查每頁 20 筆
# 2. 會話標題驗證 → 嘗試輸入 101 字，應被阻擋
# 3. 刪除確認 → 點擊刪除，應顯示對話框
# 4. 權重驗證 → 輸入總和 ≠ 1.0，應禁用儲存
# 5. 群集名稱截斷 → 超過 30 字應截斷
```

---

## ⚠️ 風險與緩解

### 風險 1: 重構破壞現有功能
**緩解**: 增量遷移 + Git 頻繁提交 + 保留備份 (Analysis_backup.py)

### 風險 2: 時程延誤
**緩解**: Phase 1-2 必須，Phase 3 可選 + 每階段預留 1 週緩衝

### 風險 3: 測試撰寫耗時超出預期
**緩解**: 降低覆蓋率目標 (70% → 60%) + 優先核心模組 + 延後 E2E 測試

### 風險 4: 效能優化效果不明顯
**緩解**: Phase 2 實測驗證 + 聚焦高 ROI 優化 (LLM 快取、Excel 讀寫)

---

## 📌 關鍵決策點

以下決策點需與團隊討論並達成共識:

1. **技術債處理優先順序** (Phase 1-2 專注高優先級，低優先級延後)
2. **跨平台支援必要性** (Phase 3 遷移至 openpyxl?)
3. **任務佇列選型** (RQ vs 內建 threading vs 不實作)
4. **測試覆蓋率目標** (70% vs 60%?)
5. **依賴注入方案** (手動 DI vs Flask-Injector)

詳細決策分析請參考: [decisions_and_open_issues.md](decisions_and_open_issues.md)

---

## 📖 如何使用本計劃

### 開發團隊

1. **Phase 1 Week 1 開始前** (✅ 已完成):
   - 閱讀 [finish/phase1_architecture_refactor.md](finish/phase1_architecture_refactor.md)（已完成，參考用）
   - 閱讀 [finish/COMPLETION_STATUS.md](finish/COMPLETION_STATUS.md)（完成狀態報告）
   - 閱讀 [decisions_and_open_issues.md](decisions_and_open_issues.md)
   - 參加決策會議，確認關鍵決策

2. **Phase 1 實作期間**:
   - 按照 Week 1-3 任務清單逐步實作
   - 每完成一個模組，執行手動測試驗證
   - Git 頻繁提交，確保可回滾

3. **Phase 2 開始前**:
   - 閱讀 [phase2_testing_optimization.md](phase2_testing_optimization.md)
   - 確認測試覆蓋率目標 (70%)
   - 準備測試資料 (fixtures/)

4. **Phase 3 開始前**:
   - 閱讀 [phase3_enhanced_features.md](phase3_enhanced_features.md)
   - 確認功能優先順序 (P0 必須，P1-P2 視情況)
   - 與業務方確認需求

### 專案經理 / Tech Lead

1. **追蹤進度**:
   - 每週檢查任務完成狀態 (checkbox)
   - 識別延誤風險，調整計劃

2. **決策管理**:
   - 使用 [decisions_and_open_issues.md](decisions_and_open_issues.md) 追蹤決策狀態
   - 定期召開決策會議

3. **品質把關**:
   - Phase 1 結束: 驗證程式碼行數 (<500 行) 與功能完整性
   - Phase 2 結束: 驗證測試覆蓋率 (≥70%)
   - Phase 3 結束: 驗證新功能可用性

---

## 📞 聯絡資訊

如有問題或建議，請聯絡:
- Tech Lead: [待補充]
- QA Lead: [待補充]
- 專案文件: `/docs/spec/design/architecture_design.md`

---

## 📝 版本歷史

| 版本 | 日期 | 異動內容 | 負責人 |
|------|------|---------|--------|
| v1.2 | 2025-11-05 | **重大更新**: 發現 Phase 1 實際完成度僅 35-40%，新增 Phase 1 補完計劃 (1-1/1-2/1-3) | Claude Code |
| v1.1 | 2025-11-05 | Phase 1 已完成，文件移至 finish/ 目錄，更新狀態（後證實評估過於樂觀） | Claude Code |
| v1.0 | 2025-11-04 | 初版建立，包含 Phase 1-3 完整計劃 | Claude Code |

---

## 🎓 參考資料

- [Architecture Design Document](/docs/spec/design/architecture_design.md) - 完整架構設計
- [ERM Schema](/docs/spec/design/erm.dbml) - 資料庫結構
- [Feature Specifications](/docs/spec/features/) - 功能規格檔案 (Gherkin)
- [CLAUDE.md](/CLAUDE.md) - Claude Code 專案指引
