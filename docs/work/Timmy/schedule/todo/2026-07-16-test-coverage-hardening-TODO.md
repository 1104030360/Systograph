# Test Coverage Hardening TODO

## 目標

依 production coverage 與 release-readiness 風險補齊真正缺少的 unit、integration 與 E2E
行為，且所有 production 修正都遵守 red-green-refactor。

## 實作邏輯

- 優先保護 scanner read-only、secret/path safety、JSON contract、artifact reload、CLI/API
  error contract 等 P1 邊界。
- 測試 observable behavior，不鎖 private implementation 或整份脆弱 snapshot。
- 能用 real service、temporary directory 或 FastAPI TestClient 就不用寬鬆 mock。

## 步驟

- [x] 依 coverage 與 call path 選出具體高風險缺口。
- [x] 每個缺口新增最小測試，並以實際 red 或 mutation red 保存失敗證據。
- [x] 兩個紅燈皆證明是測試 fixture/預期錯誤；沒有為了綠燈修改 production 行為。
- [x] 補 unit 邊界後，以 integration/Web/CLI 驗證真實 route、state 與 artifact lifecycle。
- [x] 寫入本階段 Report，列出 red/green 證據與剩餘風險。
