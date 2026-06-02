# Phase5 Dev Prompt: Backend Integration and Regression Tests

請在 Timmy viewer API 完成後，完成正式整合與測試。

## 任務

- 對接 `ViewerSessionService` local API。
- 實作 invalid map error state。
- 補前端 regression tests。
- 測 graph render、detail modal、filter highlight、replay controls、Follow focus。
- Query trace request 必須等後端 contract。

## 驗收

- API mode 可載入正式 response。
- invalid map 不顯示 graph。
- tests 可在 local/CI 執行。
- frontend 仍不重新掃描 repo。
