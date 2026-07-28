# 2026-06-07 Phase 19 Manual Mapping Store TODO

## 目標
實作 Task 19 manual mapping store，讓使用者確認過的 mapping decision 可以被安全保存，並在下次 scan / normalize 時重現。

## 實作邏輯
- `ai_system_map.json` 是輸出結果，不是設定來源；API 不直接修改既有 artifact。
- Manual mapping 是 project-level decision，不是新的完整 canonical template。
- Confirmed mapping 先寫入 Systograph-managed storage / repository，再由下一次 scan 的 component detection 階段套用。
- Route 只呼叫 service；validation、digest、decision state、canonical map 影響都集中在 core service。
- 測試中使用 fake / in-memory repository，避免寫 developer 真實 DB 或 user home。

## 階段規劃
1. RED：新增 `ManualMappingService` 單元測試，鎖定 confirmed、invalid slot、reject / skip / not_applicable、digest、secret-like payload rejection。
2. RED：新增 `ComponentDetectionService` 整合測試，確認 confirmed existing slot mapping 會移除對應 unmapped 並產生 detected slot；未確認或 rejected decision 不改 canonical component result。
3. RED：新增 `/api/mappings` web route 測試，確認 create/list/patch 只寫 mapping store，不會直接 mutate latest map artifact。
4. GREEN：建立 mapping domain model、repository protocol / in-memory implementation、manual mapping service。
5. GREEN：將 service 以 `ManualMappingHook` 套進 component detection pipeline。
6. GREEN：建立 FastAPI mapping routes 與 app dependency wiring。
7. 文件：更新 Epic 1 local API guide 的 mapping route contract。
8. 驗證：跑 focused tests、ruff、mypy、全量 pytest；若有非本次相關失敗，記錄在 report。

## 驗收重點
- Confirmed mapping 不寫入 project root。
- Invalid mapping 不進 canonical JSON。
- Rerun scan / normalize 可重現 confirmed mapping。
- Reject / skip / not_applicable 不會產生 slot、extension 或 flow edge。
- Web route 不直接修改既有 `ai_system_map.json`。
- API response 足以支援前端 unmapped confirmation affordance。
