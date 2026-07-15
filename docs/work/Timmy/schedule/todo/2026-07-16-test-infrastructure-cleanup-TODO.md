# Test Infrastructure Cleanup TODO

## 目標

讓測試分類能由 pytest 直接選取，讓共用 fixture 有清楚 ownership，並使錯誤 marker、
非同步測試或 collection drift 能在本機與 CI 立即失敗。

## 實作邏輯

- 優先修改集中式 pytest config，不用重複 decorator 汙染每個測試檔。
- 共用 fixture 只提升到真正共用的最低目錄；單檔資料保留在單檔，避免全域 fixture 膨脹。
- 不改 production contract；每次配置變更都以 collection 與分層執行驗證相容性。

## 步驟

- [x] 依 baseline 補齊 pytest strict config 與正式 markers。
- [x] 建立自動分類或最小 marker 方案，讓 unit/integration/e2e/contracts/web 可獨立執行。
- [x] 檢查重複 fixture；只有 root `conftest.py` 共用 state isolation，沒有需要搬動的重複 fixture。
- [x] 執行各分層 collection 與 focused suite，確認沒有漏收或重複執行。
- [x] 寫入本階段 Report，記錄相容性與執行方式。
