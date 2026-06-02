# Phase3 Dev Prompt: API Mode and Scan Progress

請讓 Viewer 支援 local Python API 與 scan progress。

## 任務

- 建立 Sample / API source control。
- API base URL 預設 `http://127.0.0.1:8000`。
- 支援 `GET /api/map`。
- 支援 SSE `GET /api/scan/events`。
- Progress event 可解析 node / edge / component / source / slot。
- 更新 `frontend/API_CONTRACT.md`。

## 驗收

- Sample mode 不依賴 backend。
- API error 可顯示。
- Mock progress 可逐步 highlight graph。
- SSE event target 可映射到 graph element。
