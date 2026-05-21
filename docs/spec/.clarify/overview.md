# Epic 1 決策紀錄

本文件只保留會影響實作的決策，取代原本一題一檔的 clarification records。

## D1. Source of Truth

`docs/design/epic1.md` 是 Epic 1 的實作契約。

輔助文件：

- `docs/spec/draft/epic1.md`：產品與規格概述。
- `docs/spec/erm.dbml`：資料模型參考。
- `docs/spec/features/*.feature`：高層級行為範例。

## D2. Scanner Boundary

Scanner 對 target project folder 必須 read-only。它只能寫入自己的 output directory。

## D3. Public Repo Usage

公開 RAG / local-AI repos 可以作為 fixture design 的研究來源，但 scanner tests 必須使用本地 synthetic fixtures。不要把第三方 repo vendoring 到本 repository。

## D4. Normalization Layer

Parsers 只輸出 raw scan signals。Normalization service 負責把 signals 轉換成 system-map concepts，例如 component slots、endpoints、flows、evidence 與 risk hints。

## D5. Evidence Paths

Evidence file paths 使用 project-relative POSIX paths，讓 outputs 在 Windows 與 macOS 上保持穩定。

## D6. Secret Handling

Full secret values 不得出現在 JSON、Markdown、logs、snapshots 或 UI。Secret-like values 在 serialization 前應遮罩或省略。

Raw retrieved chunks 不屬於 default Epic 1 map contract，因為它們可能包含私有文件或 PII。

## D7. Endpoints

Endpoints 應獨立建模，因為多個 components 可能引用同一個 endpoint，而單一 component 也可能暴露或依賴多個 endpoints。

## D8. Risk Hint Targets

Risk hints 可以指向：

- `component_instance`
- `endpoint`
- `component_slot`

Risk hints 不是最終安全 verdict，必須包含 uncertainty。

## D9. Parse Failures

Malformed config 或 Docker Compose 檔案應產生 parse-error evidence，並允許 partial map。Project root 不存在或不可讀才是 fatal error。

## D10. Output Directory 行為

Map command 不得覆寫既有 artifacts。如果 output directory 已經有 artifacts，應建立 timestamped run directory。

## D11. Viewer Filter Behavior

Viewer filters 保留完整 graph，只高亮 matching items。預設不隱藏 unmatched components。

## D12. Query Trace

Query trace / replay 不屬於 Epic 1 MVP。等 privacy、endpoint 與 side-effect boundaries 定義清楚後，再作為 explicit opt-in workflow。
