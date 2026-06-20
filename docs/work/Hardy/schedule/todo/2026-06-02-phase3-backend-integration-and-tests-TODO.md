# Phase3 Backend Integration and Viewer Tests TODO

## 目標

在 Timmy 完成 viewer local API 後，將前端從 sample-first checkpoint 推進到
正式 API integration，並補 Viewer regression tests。

## 實作邏輯

- API mode 應以 `ViewerSessionService` response 為主。
- Frontend 繼續只渲染 `graph_view_model`。
- invalid map / API error 要有明確 error state。
- query trace request 必須等 endpoint contract，且 missing endpoint 不送出 query。
- tests 先保護現有 graph / modal / replay / follow focus 行為。

## 步驟

1. 跟 Timmy 確認 viewer load endpoint 與 response shape。
2. 更新 `frontend/API_CONTRACT.md`。
3. 更新 Zod schema。
4. 實作 invalid map error state。
5. 加入前端 test runner。
6. 補 graph render smoke test。
7. 補 detail modal open/close test。
8. 補 filter highlight 不隱藏 graph test。
9. 補 replay controls / follow focus test。
10. 補 API error state test。

## 驗收清單

- [ ] API mode 可載入正式 backend viewer response。
- [ ] invalid map 顯示 error state，不顯示半殘 graph。
- [ ] frontend 不讀 project folder。
- [ ] frontend 不推論 JSON 沒有的 component。
- [ ] graph render smoke test 通過。
- [ ] node click 會開 detail modal。
- [ ] filter 只高亮，不移除 graph。
- [ ] replay step 可前進 / 後退。
- [ ] Follow on/off 行為可測。
- [ ] API error 不讓 app crash。
