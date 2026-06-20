# Task 7: Add Viewer Regression Tests

## 目標

補齊前端 Viewer 的 regression tests，保護 graph rendering、filter highlight、
detail modal、API loading 與 replay interaction。

## 為什麼要做這個

Viewer 的互動狀態多，容易因 UI 微調破壞 edge rendering、Follow focus 或
detail modal。需要 automated checks 降低回歸風險。

## 實作範圍

- Component tests 或 Playwright/E2E tests。
- Graph render smoke。
- Detail modal open/close。
- Filter highlight 不移除 graph。
- Replay controls。
- Follow focus toggle。
- API error state。

## 不包含範圍

- 不測 backend scanner providers。
- 不測 Python schema validation。
- 不測 local model 真實回答品質。

## 建議實作步驟

1. 評估加入 Playwright 或 Vitest + Testing Library。
2. 建立 sample map fixture test harness。
3. 測 graph 有 nodes/edges。
4. 測 click node 開 modal。
5. 測 replay step forward 改變 active step。
6. 測 API error 顯示但 app 不 crash。

## 驗收標準

- CI/local 能跑前端 tests。
- edge 消失、modal 失效、filter 隱藏 graph 這類問題會被測試抓到。
- test 不依賴真實 backend server。
