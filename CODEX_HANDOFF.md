# Codex 交接文件

當你在另一台電腦或另一個 Codex session 開啟這個 repo 時，請先讀這份文件。它是目前規劃 branch 的共享工作記憶。

## 目前 Branch

```text
kai-mind-roadmap-issues
```

## 目前目標

替 KAI-Mind roadmap 建立 repo 內的基礎文件：

- 在 GitHub 開好 Parent / Epic issues。
- 記錄跨平台架構決策。
- 保存 input layer 研究用的公開 repo。
- 記錄 GitHub Codex review 設定方式。
- 更新 README，讓後續貢獻者知道要從哪裡開始。

## 已建立的 GitHub Issues

- #1 `[Epic 0] 專案基礎：跨平台 Core、CLI 與 Local Web UI`
- #2 `[Epic 1] System Map Builder：探索 AI Stack Inputs 與 Data Flow`
- #3 `[Epic 2] Runtime Readiness：Ollama、Docker、Native Services 與 Qdrant`
- #4 `[Epic 3] Privacy & Exposure Guard：Secrets、Ports 與 Cloud Endpoints`
- #5 `[Epic 4] Agent Tool Risk Guard：Tool Inventory、Permissions 與 Auditability`
- #6 `[Epic 5] RAG Knowledge Trust：Collections、Metadata、Citations 與 Grounding`
- #7 `[Epic 6] Release Report & CI Gate：Verdict、Evidence、JSON 與 Exit Code`
- #8 `[Epic 7] Distribution & Integrations：Packaging、GitHub Action 與 Developer Workflow`

## 已新增或更新的文件

- `README.md`
- `AGENTS.md`
- `CODEX_HANDOFF.md`
- `docs/kai-mind/README.md`
- `docs/kai-mind/cross-platform-strategy.md`
- `docs/kai-mind/public-reference-repos.md`
- `docs/kai-mind/github-codex-review.md`

## 產品決策摘要

KAI-Mind 不應該做成 Windows-only `.exe`。

建議架構是：

```text
Core Engine + CLI + Local Backend + Local Web UI + thin platform launchers
```

CLI 是穩定 contract。Launchers 只是方便使用者啟動的外層包裝。

## 下一步建議

只從 Epic 1 開始：

1. 在 #2 底下建立 sub-issues。
2. 定義 `ai_system_map.json` schema。
3. 新增一個小型 sample AI stack fixture。
4. 實作 folder/config scanner。
5. 匯出第一版 system map。

目前不要把所有 Epic 都拆成細項 task，避免團隊一開始就分散。

## 重要限制

- Scanner 預設應該 read-only。
- 不要印出完整 secret values。
- Scanner logic 應放在 core，不要放在 launcher。
- Local Web UI 應呼叫 local backend / CLI，不要用純 browser code 掃描敏感檔案。
- Codex Cloud 尚未啟用，所以這份 handoff file 暫時作為跨設備同步機制。

## 另一個 Codex Session 應如何接手

1. 先讀 `README.md`。
2. 再讀本文件。
3. 再讀 `docs/kai-mind/README.md`。
4. 執行 `git status --short --branch`。
5. 如果要繼續實作，從 Epic 1 schema work 開始。
