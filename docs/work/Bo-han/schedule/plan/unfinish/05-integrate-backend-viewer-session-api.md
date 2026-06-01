# Task 5: Integrate Backend Viewer Session API

## 目標

將目前的 sample-first Viewer 改成可正式接 `ViewerSessionService` 的 local API，
讓前端能載入後端產生的 `viewer_load_result`。

## 依賴

- Timmy 完成 `ViewerSessionService.load_map()`。
- Timmy 提供 local API endpoint 與 response shape。
- Timmy 更新 API guide，說明 invalid map error state。

## 實作範圍

- 對接正式 viewer load endpoint。
- 處理 loaded/error_reason/map_json。
- invalid map 顯示 error state。
- graph_view_model 欄位變更時更新 Zod schema。
- 移除或降級暫時 fallback endpoint。

## 不包含範圍

- 不重新做 backend graph projection。
- 不在 frontend 推論 missing component。
- 不處理 query trace request。

## 建議實作步驟

1. 跟 Timmy 確認 endpoint path 與 response shape。
2. 更新 `frontend/API_CONTRACT.md`。
3. 更新 `viewerPayloadSchema`。
4. 補 invalid map UI。
5. 用 backend fixture map 做手動驗證。

## 驗收標準

- API mode 可載入正式 backend response。
- invalid map 不顯示半殘 graph。
- error_reason 對使用者可讀。
- frontend 不需要讀 project folder。
