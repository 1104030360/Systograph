# System Map 資料模型決策脈絡

本文件整理原本分散在 `resolved/data/*` 的核心資料模型釐清結果。它保留決策背景，但不取代 `docs/design/epic1.md` 與 `docs/spec/erm.dbml`。

## ComponentSlot requiredness

原始問題：每個 RAG slot 是否都應該被視為必填？

決策：

- `required_for_rag` 不應是全域固定常數。
- Scanner 應根據 `rag-core-v1` template、project evidence 與 detected flows 推導 requiredness。
- 沒有 evidence 時，不得把 slot 標成 `detected`。

保留原因：

如果把所有 RAG slots 都硬設為必填，會讓小型或非典型 RAG project 被錯誤標示為缺失過多。Epic 1 應該建立 map，不應提前替後續 readiness checks 下結論。

## Endpoint model

原始問題：`endpoints` 是否需要獨立建模？

決策：

- Endpoints 應獨立於 components 建模。
- Endpoint 可以被多個 components 引用。
- Component 也可以暴露或依賴多個 endpoints。

保留原因：

Endpoint 是後續 Runtime Readiness 與 Privacy / Exposure Guard 的共用輸入。若只塞在 component 裡，後續很難做 endpoint-level checks、dedupe 或 exposure hints。

## Evidence path normalization

原始問題：Windows 與 macOS 路徑要如何穩定輸出？

決策：

- Evidence file path 使用 project-relative POSIX path。
- 不把本機絕對路徑作為主要 evidence identity。

保留原因：

同一個 fixture 或 project 在 Windows/macOS/CI 上執行時，輸出應盡量穩定，避免 snapshot tests 因路徑格式不同而失敗。

## Secret-like value masking

原始問題：secret-like value 應該如何保存與顯示？

決策：

- Full secret values 不得出現在 JSON、Markdown、logs、snapshots 或 UI。
- Secret-like values 應在 serialization 前遮罩或省略。
- 所有 output surface 應共用同一個 `SecretMaskingService`。

保留原因：

Epic 1 會掃 `.env`、config 與 Docker environment。若 masking policy 分散在不同輸出層，容易漏掉 snapshot、Markdown 或 UI。

## RiskHint target

原始問題：risk hint 只能指向 component instance，還是可以指向 slot / endpoint？

決策：

Risk hints 可以指向：

- `component_instance`
- `endpoint`
- `component_slot`

Risk hints 必須包含 `rule_id`、`evidence_id`、`rationale` 與 `uncertainty`。

保留原因：

有些風險是 endpoint-level，例如 external endpoint 或 published port；有些則是 slot-level，例如重要 slot missing。只允許 component target 會讓後續檢查不自然。
