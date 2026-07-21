# 前端工作：接上 ai-system-map/v2 並移除舊 Extension

Status: backend ready；frontend implementation / integration pending

Last updated: 2026-07-20（Plan 13 backend cutover 已完成）

## 目的

Backend 的正常輸出已從 `ai-system-map/v1` 切成 `ai-system-map/v2`，而且不再接受
`new_extension_component`。Frontend 目前仍有舊的 type、表單分支、mock 與 sample；如果不調整，
畫面仍會教使用者走已停用的流程，送出後也只會收到
`legacy_mapping_type_read_only`。

這次前端的工作很單純：**讀取並顯示 backend 已提供的 v2 資料，只送 backend 目前接受的
mapping decision。** 舊 v1 資料的轉換由 backend 負責，frontend 不需要再做一套 migration。

## 這次改了什麼

| 以前 | 現在 | 為什麼 |
| --- | --- | --- |
| 正常 map 是 `ai-system-map/v1` | 正常 map 是 `ai-system-map/v2` | v2 可描述一般 AI system，不再綁死 RAG slot |
| map 可能有 top-level `extensions` | v2 使用 `components[]`、`edges[]` 等通用欄位 | 避免 extension 成為第二套 graph model |
| UI 可送 `new_extension_component` | 只能送 `existing_slot_mapping` 或 `non_baseline_capability_candidate` | Backend 已停用 legacy extension 寫入 |
| 找不到既有 slot 時建立 extension | 顯示 backend 給的 capability candidate、需要更多資訊或暫時略過 | Frontend 不應自己猜一個新 component |

## Frontend 要做什麼

目前共有 **4 個檔案、5 筆 legacy contract hit** 要處理：

| 檔案 | 要改什麼 | 為什麼 |
| --- | --- | --- |
| `frontend/src/types.ts` | 移除 legacy type；對齊目前 proposal 與 manual mapping union | 避免 TypeScript 認為 backend 已拒絕的值仍可送出 |
| `frontend/src/components/proposal/EditForm.tsx` | 移除 `ui_extension` 對應到 `new_extension_component` 的分支；依 backend candidate 類型顯示可用操作 | 避免使用者送出一定會得到 422 的 request |
| `frontend/src/data/scanTemplate.mock.ts` | 刪除 legacy extension fallback 與 `UI · New extension` 選項，改用目前 backend 支援的 candidate 範例 | Sample / mock 不應示範已退役流程 |
| `frontend/src/data/frontend-json-sample.json` | 把 canonical map sample 改成 `ai-system-map/v2`，移除 top-level `extensions` 與 legacy proposal sample | Sample mode 要和 API mode 使用同一份現行契約 |

### Proposal 畫面怎麼處理

- `existing_slot_mapping`：可接受或編輯既有 slot mapping。
- `non_baseline_capability_candidate`：顯示 backend 提供的 candidate 名稱、種類、理由與
  evidence；不要把它改名成 extension。
- `needs_more_information`：告訴使用者目前證據不足，不建立 component。
- `skip_for_now`：保留目前結果，讓使用者稍後再處理。

Frontend 不要從檔名、畫面文字或 graph 位置自行判斷 candidate type；直接使用 backend
payload。

### 遇到舊 request 時

如果舊分頁或舊 state 仍送出 `new_extension_component`，backend 會回
`legacy_mapping_type_read_only`。Frontend 應提示使用者重新整理或重新取得 proposal，不要用同一份
payload 一直重試，也不要在 browser 內把 legacy extension 自動轉成新 component。

## 建議實作順序

1. 先補 frontend 測試：v2 Viewer sample 可 parse、四種 proposal candidate 可 parse、legacy
   type 不可送出。
2. 更新 `types.ts`，讓型別先對齊 backend contract。
3. 更新 `EditForm.tsx`、mock 與 sample。
4. 跑 Vitest、TypeScript build、lint，再用 API mode 手動確認 proposal 與 Viewer。

## 驗收清單

- [ ] `frontend/src` 的 active code / sample 不再出現 `new_extension_component`。
- [ ] Frontend sample 的 canonical map 是 `ai-system-map/v2`，且沒有 top-level `extensions`。
- [ ] Zod 可 parse current v2 Viewer payload與四種 proposal candidate。
- [ ] Edit / accept 只會送 backend 支援的 manual mapping shape。
- [ ] 收到 `legacy_mapping_type_read_only` 時顯示可理解的更新提示，不重試舊 payload。
- [ ] Vitest、TypeScript build、lint 全部通過。
- [ ] API mode 完成 Viewer、proposal accept / edit / reject / skip 的手動測試。
- [ ] Frontend 交付後通知 backend owner 重跑 consumer census，確認 5 筆 `migrate` 降為 0。

## Source of truth

- [Plan 13：ai-system-map/v2 Active Cutover](../../Timmy/schedule/plan/unfinish/phase2/static-trace-plan/s1-v2-cutover/13-retire-legacy-extension-contract.md)
- [API Guide](../../../API-GUIDE.md)
- [Model Contract](../../../MODEL-CONTRACT.md)
- [v2 canonical map sample](../../Timmy/design/EPIC1/frontend-json-handoff/step-04-normalize-validate/frontend-ai-system-map-sample.json)
- [current proposal sample](../../Timmy/design/EPIC1/frontend-json-handoff/step-09-review-apply/frontend-mapping-proposal-sample.json)
- [current manual mapping sample](../../Timmy/design/EPIC1/frontend-json-handoff/step-09-review-apply/frontend-manual-mapping-create-capability-candidate-sample.json)

如果本文件與 API / Model Contract 衝突，以 `docs/API-GUIDE.md` 與
`docs/MODEL-CONTRACT.md` 為準。

## 不屬於這次工作

- 不在 frontend 實作 v1-to-v2 migration adapter。
- 不把 legacy extension 自動升格成 detected component、capability 或 edge。
- 不修改 backend 的 operator rollback、歷史 v1 read 或 migration command。
- 不重新設計 Viewer layout、Graph Studio 或整套 proposal UX。
