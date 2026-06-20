# Task 3: Wire Viewer API Source and Progress Events

## 目標

讓 Viewer 支援 Sample / API 兩種資料來源，並預留 scan progress SSE 事件
對應到 graph highlight 的能力。

## 為什麼要做這個

前端需要在後端 API 完成前先可用 sample 開發，但後續必須能切換到 local
Python API，不應重寫資料載入層。

## 實作範圍

- Sample / API segmented control。
- 可輸入 `VITE_API_BASE_URL` 或 UI base URL。
- `GET /api/map` 與暫時 fallback `/map`。
- SSE `/api/scan/events`。
- progress event target mapping。
- mock progress fallback。
- `frontend/API_CONTRACT.md`。

## 不包含範圍

- 不實作 backend API。
- 不定義 canonical schema。
- 不處理真正 query trace request。

## 建議實作步驟

1. 建立 `useViewerPayload()`。
2. 建立 `useScanProgress()`。
3. 將 API mode 的錯誤顯示到 toolbar。
4. 定義 progress target 解析順序：node、edge、component、source、slot。
5. 把 API contract 寫成 Markdown，供 Timmy 對接。

## 預期輸出

- `frontend/src/hooks/useViewerPayload.ts`
- `frontend/src/hooks/useScanProgress.ts`
- `frontend/src/components/DataSourceControl.tsx`
- `frontend/API_CONTRACT.md`

## 驗收標準

- Sample mode 可正常載入 committed JSON。
- API mode 可設定 base URL。
- API error 不會讓畫面空白。
- progress mock 可逐步 highlight node / edge。

## 可能風險與注意事項

- API response shape 必須和 sample 一致。
- SSE event ID 可能是 graph id 或 source id，前端需要 mapping。
- API 尚未完成時，前端不可把 fallback 行為寫成正式 contract。
