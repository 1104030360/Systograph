# 前提
請先幫我更新最新專案結構到 `/Users/linjunting/Desktop/IT_Ticket_System備份/CLAUDE.md`，接下來繼續進行以下事項

# 背景知識
1.目前專案的計劃要做的事情如下： `/Users/linjunting/Desktop/IT_Ticket_System備份/docs/schedule-mustupdate/plan/unfinish/2025-11-07-Phase2-Core-Issues-Action-Plan.md`
2.目前後端程式碼如下：
   **核心應用層 (443 行)**:
   - `/Users/linjunting/Desktop/IT_Ticket_System備份/Analysis.py` (250 行)
   - `/Users/linjunting/Desktop/IT_Ticket_System備份/run_analysis.py` (193 行)

   **API 層 - Blueprints (1,199 行):
   - `/Users/linjunting/Desktop/IT_Ticket_System備份/api/__init__.py` (28 行)
   - `/Users/linjunting/Desktop/IT_Ticket_System備份/api/upload_routes.py` (143 行)
   - `/Users/linjunting/Desktop/IT_Ticket_System備份/api/chat_routes.py` (150 行)
   - `/Users/linjunting/Desktop/IT_Ticket_System備份/api/cluster_routes.py` (278 行)
   - `/Users/linjunting/Desktop/IT_Ticket_System備份/api/config_routes.py` (378 行)
   - `/Users/linjunting/Desktop/IT_Ticket_System備份/api/history_routes.py` (222 行)

   **Services 層 - 業務邏輯 (3,857 行) ✅ 已由 Blueprint 呼叫**:
   - `/Users/linjunting/Desktop/IT_Ticket_System備份/services/__init__.py` (31 行)
   - `/Users/linjunting/Desktop/IT_Ticket_System備份/services/ticket_service.py` (889 行)
   - `/Users/linjunting/Desktop/IT_Ticket_System備份/services/rag_service.py` (463 行)
   - `/Users/linjunting/Desktop/IT_Ticket_System備份/services/cluster_service.py` (806 行)
   - `/Users/linjunting/Desktop/IT_Ticket_System備份/services/risk_service.py` (350 行)
   - `/Users/linjunting/Desktop/IT_Ticket_System備份/services/kb_service.py` (397 行)
   - `/Users/linjunting/Desktop/IT_Ticket_System備份/services/config_service.py` (475 行)
   - `/Users/linjunting/Desktop/IT_Ticket_System備份/services/history_service.py` (446 行)

   **Repositories 層 - 數據訪問 (294 行)**:
   - `/Users/linjunting/Desktop/IT_Ticket_System備份/repositories/__init__.py` (20 行)
   - `/Users/linjunting/Desktop/IT_Ticket_System備份/repositories/base_repository.py` (101 行)
   - `/Users/linjunting/Desktop/IT_Ticket_System備份/repositories/config_repository.py` (173 行)

   **Core 層 - 基礎設施 (1,310 行)**:
   - `/Users/linjunting/Desktop/IT_Ticket_System備份/core/__init__.py` (103 行)
   - `/Users/linjunting/Desktop/IT_Ticket_System備份/core/config_loader.py` (368 行)
   - `/Users/linjunting/Desktop/IT_Ticket_System備份/core/database.py` (224 行)
   - `/Users/linjunting/Desktop/IT_Ticket_System備份/core/dependencies.py` (207 行)
   - `/Users/linjunting/Desktop/IT_Ticket_System備份/core/error_handler.py` (204 行)
   - `/Users/linjunting/Desktop/IT_Ticket_System備份/core/logger.py` (165 行)
   - `/Users/linjunting/Desktop/IT_Ticket_System備份/core/file_download.py` (39 行)

   **Utils 層 - 工具函數 (1,669 行)**:
   - `/Users/linjunting/Desktop/IT_Ticket_System備份/utils/excel_utils.py` (266 行)
   - `/Users/linjunting/Desktop/IT_Ticket_System備份/utils/prompt_utils.py` (191 行)
   - `/Users/linjunting/Desktop/IT_Ticket_System備份/utils/sentence_utils.py` (154 行)
   - `/Users/linjunting/Desktop/IT_Ticket_System備份/utils/cluster_utils.py` (153 行)
   - `/Users/linjunting/Desktop/IT_Ticket_System備份/utils/config_utils.py` (119 行)
   - `/Users/linjunting/Desktop/IT_Ticket_System備份/utils/data_utils.py` (96 行)
   - `/Users/linjunting/Desktop/IT_Ticket_System備份/utils/kb_loader.py` (105 行)
   - `/Users/linjunting/Desktop/IT_Ticket_System備份/utils/save_query_context.py` (63 行)
   - `/Users/linjunting/Desktop/IT_Ticket_System備份/utils/file_utils.py` (127 行)
   - `/Users/linjunting/Desktop/IT_Ticket_System備份/utils/validation_utils.py` (207 行)
   - `/Users/linjunting/Desktop/IT_Ticket_System備份/utils/ollama_client.py` (188 行)

   **Agents 層 - RAG 多代理系統 (1,898 行)**:
   - `/Users/linjunting/Desktop/IT_Ticket_System備份/agents/__init__.py`
   - `/Users/linjunting/Desktop/IT_Ticket_System備份/agents/sql_agent.py` (1,022 行)
   - `/Users/linjunting/Desktop/IT_Ticket_System備份/agents/semantic_agent.py` (522 行)
   - `/Users/linjunting/Desktop/IT_Ticket_System備份/agents/hybridquery_agent.py` (354 行)

   **獨立核心模組 (2,370 行)**:
   - `/Users/linjunting/Desktop/IT_Ticket_System備份/gptChat.py` (751 行)
   - `/Users/linjunting/Desktop/IT_Ticket_System備份/build_kb.py` (873 行)
   - `/Users/linjunting/Desktop/IT_Ticket_System備份/SmartScoring.py` (289 行)
   - `/Users/linjunting/Desktop/IT_Ticket_System備份/gpt_utils.py` (404 行)
   - `/Users/linjunting/Desktop/IT_Ticket_System備份/query_sqlite.py` (53 行)

   **總計**: 45 個 Python 文件，13,040 行代碼（不含第三方套件）
3.目前的專案結構下：`/Users/linjunting/Desktop/IT_Ticket_System備份/CLAUDE.md`
4.目前專案前端程式碼如下： `/Users/linjunting/Desktop/IT_Ticket_System備份/templates`, `/Users/linjunting/Desktop/IT_Ticket_System備份/static`
5.過程中你可以使用 "context7" MCP來查找最新資訊

# 任務
使用 linux torvald `/Users/linjunting/Desktop/IT_Ticket_System備份/.cursor/linus_torvalds.mdc` 的思考方式，
在專案的前後端部分幫我根據 `/Users/linjunting/Desktop/IT_Ticket_System備份/dev-prompts/phase2-1.md` 進行開發
請注意！改善完後要能夠通過所有測試，如果我的測試程式沒有寫完整，你也可以自己補測試程式再測試，測試程式可以寫在 `/Users/linjunting/Desktop/IT_Ticket_System備份/tests`,單元測試寫在 `/Users/linjunting/Desktop/IT_Ticket_System備份/tests/unit`, 整合測試寫在 `/Users/linjunting/Desktop/IT_Ticket_System備份/tests/integration`
你要直到 `/Users/linjunting/Desktop/IT_Ticket_System備份/docs/schedule-mustupdate/plan/unfinish/2025-11-07-Phase2-Core-Issues-Action-Plan.md` 這份文件提出的想法全部都實現了你才能停止！

 
# 定期紀錄TODO
先規劃分成幾個階段做事，把每個階段要做的事情放在 `/Users/linjunting/Desktop/IT_Ticket_System備份/docs/schedule-mustupdate/todo`，檔案名稱使用 “今天日期-階段名稱-TODO”

# 定期紀錄Report
每個階段完成後，你必須要把你做了什麼事情記錄在 `/Users/linjunting/Desktop/IT_Ticket_System備份/docs/schedule-mustupdate/report`，檔案名稱使用 “今天日期-完成的階段名稱-REP”

## 注意事項
請注意，你必須獨立完成此工作，過程中所有的決策都不必徵求任何我的同意，直接照你自己的意思任何該改啥
就直接下去改！！我相信你！！ 因為我人會出門一趟，不會在座位上，我完全信任你獨立工作的能力，因此，你
必須一直工作直到確認底下條件全部驗收通過，才能停止！！ 
