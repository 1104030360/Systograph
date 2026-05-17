# KAI-Mind Roadmap

這個資料夾保存目前的 roadmap 與 GitHub 工作流程規劃，用來把 Local AI Health Doctor 轉向成 KAI-Mind：AI Agent / RAG Release Readiness Gate。

## Parent Epic Issues

| Issue | Epic | 目的 |
| --- | --- | --- |
| [#1](https://github.com/1104030360/Local-AI-Health-Doctor/issues/1) | 專案基礎 | 決定跨平台 core、CLI、Local Web UI、repo workflow 與 report contracts。 |
| [#2](https://github.com/1104030360/Local-AI-Health-Doctor/issues/2) | System Map Builder | 掃描 project inputs 並產出 `ai_system_map.json`。 |
| [#3](https://github.com/1104030360/Local-AI-Health-Doctor/issues/3) | Runtime Readiness | 檢查 Ollama、Docker、native services、Qdrant 與 app/API health。 |
| [#4](https://github.com/1104030360/Local-AI-Health-Doctor/issues/4) | Privacy & Exposure Guard | 檢查 secrets、ports、cloud endpoints 與 Data Leaves Device 風險。 |
| [#5](https://github.com/1104030360/Local-AI-Health-Doctor/issues/5) | Agent Tool Risk Guard | 盤點 agent tools、permissions、approval、policy 與 audit logs。 |
| [#6](https://github.com/1104030360/Local-AI-Health-Doctor/issues/6) | RAG Knowledge Trust | 檢查 collections、metadata、citations 與 answer grounding。 |
| [#7](https://github.com/1104030360/Local-AI-Health-Doctor/issues/7) | Release Report & CI Gate | 產出 verdict、evidence、JSON report、exit code 與 CI gate 行為。 |
| [#8](https://github.com/1104030360/Local-AI-Health-Doctor/issues/8) | Distribution & Integrations | 規劃 launchers、GitHub Action、Codex review 與後續 integrations。 |

## 建議開發順序

1. 先讓所有 parent epics 作為 roadmap anchors。
2. 只拆 Epic 1 的 sub-issues。
3. 先完成 System Map Builder，讓它可以掃描 sample AI stack。
4. 將第一版 `ai_system_map.json` 當作後續模組的共同 input contract。
5. Epic 1 能 end-to-end 跑通後，再進入 Runtime Readiness。

## Epic 1 建議 Sub-Issues

- 定義 AI System Map schema。
- 建立 sample AI system project。
- 實作 project folder scanner。
- 實作 config / `.env` scanner。
- 實作 `docker-compose.yml` scanner。
- 匯出 `ai_system_map.json`。

## Branch 命名

Branch 名稱要能清楚對應 issue：

```text
feature/system-map-schema
feature/system-map-sample-project
feature/project-folder-scanner
feature/config-env-scanner
feature/docker-compose-scanner
feature/system-map-json-export
```

## Parent Epic 的 Definition of Done

一個 Epic 只有在以下條件成立時才算完成：

- 功能有產出 evidence，不只是 pass/fail label。
- 結果可以表示成 JSON。
- 報告能說明使用者最應該先修什麼。
- Risky checks 預設是 read-only。
- README 或相關文件已更新。
