# KAI-Mind / Local AI Health Doctor

KAI-Mind 是一個 AI Agent / RAG 系統的 Release Readiness Gate。它協助團隊在 demo、交付、部署或進入 CI/CD 前，檢查一套 local AI 系統是否安全、可用、可信，並產出可追蹤的檢查報告。

這個專案不是 AI chatbot、RAG builder，也不是完整 observability 平台。它的定位是掃描一套已存在的 AI Agent / RAG 系統，建立 AI System Map，執行 readiness checks，最後輸出清楚的判斷：

- `READY`
- `RISKY`
- `NOT READY`

## 產品方向

KAI-Mind 應該先以跨平台核心為主：

```text
Core Engine + CLI
        |
        +-- Local Web UI
        +-- Windows launcher
        +-- macOS launcher
        +-- CI / GitHub Actions
```

這樣可以避免做成只能在 Windows 開啟的 `.exe`，並讓核心 scanner 可以同時支援 Windows、macOS、Linux、本機開發與 CI。

## MVP 模組

目前 roadmap 以 Parent / Epic issues 管理：

- [Epic 0：專案基礎](https://github.com/1104030360/Local-AI-Health-Doctor/issues/1)
- [Epic 1：System Map Builder](https://github.com/1104030360/Local-AI-Health-Doctor/issues/2)
- [Epic 2：Runtime Readiness](https://github.com/1104030360/Local-AI-Health-Doctor/issues/3)
- [Epic 3：Privacy & Exposure Guard](https://github.com/1104030360/Local-AI-Health-Doctor/issues/4)
- [Epic 4：Agent Tool Risk Guard](https://github.com/1104030360/Local-AI-Health-Doctor/issues/5)
- [Epic 5：RAG Knowledge Trust](https://github.com/1104030360/Local-AI-Health-Doctor/issues/6)
- [Epic 6：Release Report & CI Gate](https://github.com/1104030360/Local-AI-Health-Doctor/issues/7)
- [Epic 7：Distribution & Integrations](https://github.com/1104030360/Local-AI-Health-Doctor/issues/8)

建議從 Epic 1 開始開發。其他 Epic 先保留為 roadmap 層級的 Parent Issue，等 System Map Builder 能產出第一版可用的 `ai_system_map.json` 後，再往下一個模組推進。

## 重要文件

- [KAI-Mind roadmap](docs/kai-mind/README.md)
- [跨平台架構策略](docs/kai-mind/cross-platform-strategy.md)
- [公開參考 repo](docs/kai-mind/public-reference-repos.md)
- [GitHub Codex code review 設定](docs/kai-mind/github-codex-review.md)
- [Codex 交接文件](CODEX_HANDOFF.md)

## 建議的第一階段開發流程

1. 選定 Epic 1：System Map Builder。
2. 只拆 Epic 1 的 sub-issues。
3. 每個 sub-issue 開一條 branch。
4. 開 PR 合併回 `main`。
5. 合併前需要 human review 加上 Codex review。
6. Epic 1 可用後，再開始拆 Epic 2。

## 工作原則

- Scanner 預設必須是 read-only。
- 產品預設採 local-first privacy。
- 不顯示完整 secret value。
- 報告要提供 evidence，不只給分數。
- Packaging 要和 core scanner 分離。
- 先穩定 CLI 與 JSON report，再打磨 launcher。
