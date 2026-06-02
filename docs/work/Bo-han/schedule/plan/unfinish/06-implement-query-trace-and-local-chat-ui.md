# Task 6: Implement Query Trace and Local Chat UI

## 目標

把目前的 replay sample 與 chat placeholder 擴充成可接後端 query trace API 與
local model chat 的互動介面。

## 依賴

- Timmy 定義 query trace request endpoint。
- Timmy 定義 missing endpoint / timeout / partial trace 行為。
- Timmy 定義 local model chat API 或明確延後該能力。

## 實作範圍

- Query input。
- Endpoint missing guard。
- Query trace request / running / timeout / error states。
- Trace event replay。
- Chat panel message list / composer。
- 將 selected node / edge context 帶入 chat request。

## 不包含範圍

- 不直接呼叫使用者專案 endpoint，除非 backend API 明確代理。
- 不繞過 backend secret masking。
- 不把 chat 回覆寫回 canonical map。

## 建議實作步驟

1. 先實作 endpoint missing guard。
2. 實作 trace request 狀態機。
3. 用 `sequence_index` 排序 trace events。
4. 將 replay active step 映射到 graph highlight。
5. 實作 chat panel skeleton 到可互動狀態。

## 驗收標準

- missing endpoint 時 `query_sent = false`。
- timeout 時保留 partial trace。
- error step 不讓 replay 消失。
- chat panel 不影響 graph 操作。
