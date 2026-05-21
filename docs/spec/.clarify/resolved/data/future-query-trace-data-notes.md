# Future Query Trace 資料模型脈絡

本文件保留原本 Query Trace 相關資料模型討論，但它不是 Epic 1 MVP contract。

## 目前決策

Query trace / replay 不屬於 Epic 1 MVP。它應該等下列邊界清楚後，再作為 explicit opt-in workflow：

- 使用者如何明確指定 endpoint。
- 是否允許呼叫 running service。
- 如何避免觸發外部 LLM、side effects 或 API quota。
- Trace output 如何避免保存敏感資料。

## 原始資料模型問題

原本討論過 `QueryTraceEvent` 需要保存：

- replay order
- timestamp
- slot / edge mapping
- input / output
- error / timeout
- retrieved chunks

## 保留但延後的原則

若未來重新設計 query trace：

- Replay order 應使用明確的 `sequence_index`，不要依賴 timestamp 排序。
- Error / timeout 應保存為 trace step，不應丟棄整次 replay。
- Missing endpoint 時不得送出 query。
- Raw retrieved chunks 不應預設保存，因為可能包含私有文件或 PII。
- 若需要 chunk context，優先保存 source id、hash、count、metadata summary 或 redacted excerpt。

## 為什麼不放在 Epic 1 MVP

Epic 1 的 scanner 應該是 read-only map builder。Query trace 會主動呼叫被掃描 project 的 service，行為上已接近 runtime check / observability。把它放進 MVP 會讓 scanner scope 和 privacy boundary 變得不清楚。
