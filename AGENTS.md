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
