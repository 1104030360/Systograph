# AGENTS.md

## 專案背景

KAI-Mind / Local AI Health Doctor 是一個 AI Agent / RAG Release Readiness Gate。它會在 demo、交付、部署或 CI/CD 前，掃描既有的 local AI 系統並輸出 readiness report。

它不是 chatbot、RAG builder、完整 observability 平台，也不是企業級資安掃描器。

## Review 指南

- 優先檢查 release-readiness 相關 regression。
- 標記不安全的 filesystem scanning、secret exposure、network exposure 風險。
- Scanner code 預設必須 read-only，除非 task 明確要求修改檔案或系統狀態。
- 不可以在 logs、reports、test snapshots 或 PR comments 中印出完整 secret values。
- Scanner 行為缺少測試時，視為 P1。
- JSON report schema 破壞相容性時，視為 P1，除非已清楚記錄 migration。
- 檢查 CLI 行為是否同時適用 Windows 與 macOS。
- 檢查 packaging code 是否重複實作 core scanner logic。
- 優先要求 evidence-based findings，不要只有不透明的單一總分。

## 開發指南

- Core Engine 行為應獨立於 platform launchers。
- CLI 與 JSON report contract 要保持穩定。
- 跨平台假設必須寫清楚。
- Network exposure checks 要說明不確定性。
- Scanner tests 應使用 sample projects 與 fixtures。

## Codex 全域 MCP / Agent 使用規則

- Codex MCP 與 agent 設定使用全域目錄 `/Users/linjunting/.codex/`，不要在本 repo 建立或提交 repo-local `.codex/` 設定，除非任務明確要求且已先記錄原因。
- 全域 agent 放在 `/Users/linjunting/.codex/agents/`；使用說明在 `/Users/linjunting/.codex/AGENT_USAGE.md`。
- 全域 MCP 設定放在 `/Users/linjunting/.codex/config.toml`；使用說明在 `/Users/linjunting/.codex/MCP_USAGE.md`。
- 需要最新官方文件、API 用法、SDK 設定或版本差異時，優先使用全域 Context7；若 Context7 不足，再使用 Ref.tools 或一般 web research。
- 需要查 GitHub repo、issue、PR、Actions 或 release 狀態時，使用 GitHub MCP，且預設 read-only。
- 需要找開源專案、比較技術方案、查最新 best practices 時，使用 Exa / Tavily。
- 需要研究 public GitHub repo 架構時，使用 DeepWiki / GitHub MCP。
- 需要測試 Viewer、Dashboard、Mapping UI 或瀏覽器互動流程時，使用 Playwright MCP。
- 需要大型 codebase 的 symbol-level 搜尋、references、跨檔案語意導覽時，使用 Serena。
- Research 類 MCP 預設只查資料，不直接修改 code。
- 修改 code 前先提出 plan，並說明使用了哪些 MCP 來源與結論。
