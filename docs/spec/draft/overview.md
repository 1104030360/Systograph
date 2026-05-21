# KAI-Mind 規格總覽

KAI-Mind 是 AI Agent / RAG 系統的 release-readiness 工具。它不負責建立 RAG app，而是檢查既有 project，產出人類與 CI 都能使用的 evidence-backed artifacts。

核心流程：

```text
Read -> Map -> Check -> Risk -> Recommend -> Gate
```

## 產品方向

KAI-Mind 應把 scanner behavior 放在 shared core：

```text
Core Engine + CLI
        |
        +-- Local Web UI
        +-- Windows launcher
        +-- macOS launcher
        +-- CI / GitHub Actions
```

Launcher 與 UI 都應呼叫同一份 core engine，不應重複實作 scanner logic。

## Epic 順序

| Epic | 目的 |
|---|---|
| Epic 1 | 從 project folder 建立 `ai_system_map.json` |
| Epic 2 | Runtime readiness checks |
| Epic 3 | Privacy and exposure guard |
| Epic 4 | Agent tool risk guard |
| Epic 5 | RAG knowledge trust |
| Epic 6 | Release report and CI gate |
| Epic 7 | Distribution and integrations |

## 目前焦點

先從 Epic 1 開始。第一版實作應穩定：

- schema
- scanner boundaries
- normalization layer
- evidence model
- fixture tests
- CLI output contract

不要一開始就做完整 dashboard 或 CI gate。
