# Timmy 工作範圍 - Epic 1 事實層

> 負責範圍：Core scanner、schema、CLI、evidence、artifacts

## 目標

Timmy 負責 Epic 1 的事實層。Scanner 必須讀取 RAG project folder，並產出有效、evidence-based 的 `ai_system_map.json` 與 `ai_system_map.md`。

## 責任

- 定義 `rag-core-v1` slots and flows。
- 定義 `ai-system-map/v1` schema and domain models。
- 實作 read-only providers：
  - filesystem
  - config
  - Docker Compose
  - dependencies
  - bounded code patterns
- 實作 raw-signal normalization。
- 偵測 components、endpoints、flows、evidence 與 risk hints。
- 實作唯一 secret masking policy。
- 實作 `kai-mind map <project_path>`。
- 建立 synthetic RAG fixtures。
- 新增 schema、scanner、CLI、fixture 與 no-secret tests。

## 不負責

- Viewer visual design。
- Graph interaction。
- Query trace replay UI。
- Release readiness verdicts。
- Runtime health checks。

## 必須交付

| 交付物 | 說明 |
|---|---|
| `rag-core-v1` template | Slots、flows、common evidence signals |
| `ai-system-map/v1` schema | 足以支援 viewer 與後續 epics |
| Scanner providers | Read-only、bounded、structured errors |
| Normalization service | Raw signals 轉成 map concepts |
| `ai_system_map.json` | Success output 前必須 validate |
| `ai_system_map.md` | 由同一份 map 產生 |
| Fixtures | 無真實 secrets，不依賴 external repo |
| Tests | Schema、masking、path normalization、partial failure |

## 與 Bo-Han 的契約

Timmy 提供：

- sample valid maps
- sample missing-slot maps
- sample risk-hint maps
- nodes、edges、evidence、endpoints、risk hints 的欄位定義

Bo-Han 不應需要重新掃描 project folder 來建立 viewer。

## Review 檢查清單

- Detected components 有 evidence。
- 輸出沒有 `confidence` field。
- 輸出不含完整 secret。
- Evidence paths 是 project-relative POSIX paths。
- Parse failures 會產生 partial map evidence。
- Existing output artifacts 不會被覆寫。
