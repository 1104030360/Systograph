# KAI-Mind — Local AI Health Doctor 開發計劃

> 一個本機 AI 健檢與診斷平台，幫助使用者判斷自己的 local AI 環境是否能穩定、安全、有效地運行。

---

## 📋 Phase 總覽

| Phase | 名稱 | 預估時間 | 狀態 |
| :---: | --- | :---: | :---: |
| 0 | [從零建構專案基礎](./phase-0-codebase-audit.md) | 2.5–3 週 | `[ ]` |
| 1 | [重新定位與 UI 骨架](./phase-1-rebranding-ui.md) | 1 週 | `[ ]` |
| 2 | [Environment Scanner](./phase-2-environment-scanner.md) | 2 週 | `[ ]` |
| 3 | [Model Fit Advisor + Performance Benchmark](./phase-3-model-fit-benchmark.md) | 2 週 | `[ ]` |
| 4 | [Privacy / Security Guard](./phase-4-privacy-guard.md) | 1–2 週 | `[ ]` |
| 5 | [RAG Quality Inspector](./phase-5-rag-quality.md) | 2 週 | `[ ]` |
| 6 | [工程品質與履歷包裝](./phase-6-polish-resume.md) | 1–2 週 | `[ ]` |

**總預估時間：** 11.5–14 週（8 月前完成）

---

## 🎯 最終 Demo 流程

8 月前最終 demo 應該長這樣：

1. 使用者啟動 KAI-Mind
2. Dashboard 自動掃描本機環境
3. 顯示 Ollama / Qdrant / Docker 狀態
4. 顯示本機可跑的模型建議
5. 跑一次 local LLM benchmark
6. 顯示 tokens/sec、retrieval latency、generation latency
7. Privacy Guard 顯示 Data Leaves Device: No
8. 使用者上傳文件並問問題
9. RAG Quality Inspector 顯示 citation coverage 與 unsupported claims
10. 匯出 diagnosis report

---

## ⚠️ 8 月前最低可交付版本

如果時間不足，最低要完成：

- [ ] Environment Scanner
- [ ] Model Fit Advisor
- [ ] Performance Benchmark
- [ ] Privacy Guard
- [ ] RAG Quality Inspector 基礎版
- [ ] Docker Compose
- [ ] README
- [ ] Demo video
- [ ] GitHub Actions + pytest

---

## 🏗️ 技術棧

| 層級 | 技術 |
| --- | --- |
| 後端 | Python 3.12 + FastAPI |
| 前端 | Vite + React |
| AI 工作流 | LangGraph |
| Vector DB | Qdrant |
| 本機 LLM | Ollama |
| 容器化 | Docker Compose |
| CI/CD | GitHub Actions |
| Config 管理 | pydantic-settings |
