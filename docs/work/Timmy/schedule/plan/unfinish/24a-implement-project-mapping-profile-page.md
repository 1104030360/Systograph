# Task 24a: Implement Project Mapping Profile Page

## 最新狀態校正（2026-06-12）

本任務仍未完成，但不應作為 EPIC1 最小收尾阻塞項。

目前實作現況：

- 後端已具備 manual mapping、mapping proposal、scan-boundary review 的 core/API。
- 前端尚未接 `POST /api/projects/import`、`POST /api/scans`、boundary decision flow、manual mapping/proposal mutation。
- 本頁是 project-level mapping/profile 管理資訊架構，依賴前述互動流程成熟後才有完整價值。

因此本任務定位調整為：

```text
EPIC1 收尾前：不阻塞
EPIC1 後品質/UX 強化：可開始設計 view model
EPIC2：適合作為 workspace/profile/productization 功能
```

EPIC1 收尾優先順序應先做 `24b-implement-project-scan-and-boundary-decision-frontend-flow.md`、Task 20a、Task 21a，再回頭做本頁。

## 目標
建立 Project Mapping Profile / Template Overlay 管理頁，讓使用者看見目前可用的 scan profile 版本：

1. 系統預設版本：KAI-Mind built-in `rag-core-v1`。
2. 使用者確認後的 project 版本：基於 `rag-core-v1` 加上 user-confirmed mappings 的 derived profile。

使用者可以選擇下次 scan 要使用哪個版本作為 base/profile。頁面也要顯示每個 project profile 套用了哪些 confirmed mappings、哪些決策仍在 draft/pending 狀態，以及下次 scan 會如何套用。

這個頁面不是讓使用者直接重寫 `rag-core-v1`，而是把 Task 19 / Task 20 產生的 project-specific mapping overlay 包成「可選擇的 derived scan profile」。產品上可以讓使用者理解成「自己的版本」，但工程上仍應保存為 default template + confirmed mapping overlay，而不是複製並改寫內建 template。

## 為什麼要獨立做這個
Task 19 負責保存 confirmed manual mappings；Task 20 負責產生 pending mapping proposals；Task 24 負責 final scan boundary review 與 local template import。Project Mapping Profile Page 是前端資訊架構與 UX 層，應在 mapping/proposal/storage 能力穩定後再做，避免把「確認 unmapped」和「管理 template/profile」混成同一個 feature。

使用者完成多次 unmapped confirmation 後，需要一個地方理解：

- 目前使用的是 KAI-Mind default `rag-core-v1`。
- 這個 project 已有多少 confirmed mapping overlay。
- 是否已產生 project-specific derived profile。
- 目前 active scan profile 是 system default 還是 project custom。
- 哪些 mapping 是 active、draft、rejected、skipped。
- 下次 scan 會套用哪些 confirmed decisions。
- 未來若匯入 template，default template、project overlay、imported template 不能混在一起。

## 承接 Task 19 / 20 / 24
- 承接 Task 19 的 KAI-Mind-managed manual mapping store。
- 承接 Task 20 的 pending proposal lifecycle。
- 與 Task 24 的 template store / local template import UI 對齊，但不實作 import 主流程。
- 若 Task 26 已完成 scan history，本頁可顯示 last applied scan / last updated metadata；若尚未完成，只顯示目前 session 可取得的 profile state。

## 前置需求
- Task 19 已能保存、列出、驗證 confirmed manual mappings。
- Task 20 已能列出 pending/accepted/rejected mapping proposals。
- Task 18 已有 viewer graph projection，可從 unmapped / extension / slot 回到 source ids。
- Task 24 若已提供 template metadata API，本頁可顯示 imported template；否則只顯示 built-in `rag-core-v1`。

## 實作範圍
- 建立 frontend page / route：Project Mapping Profile 或 Template Overlay。
- 顯示 default template：`rag-core-v1`，標籤為 `System default`、`Read-only`。
- 顯示 project profile：例如 `<project name> mapping profile`，標籤為 `Project custom`、`Derived from rag-core-v1`、`Active` 或 `Draft`。
- 支援選擇 active scan profile：system default 或 project custom profile。
- 一開始沒有 user-confirmed mappings 時，只顯示 system default profile；project custom profile 可顯示為 empty/draft state，或在第一次 confirmed mapping 後才產生。
- 顯示 confirmed mappings 清單：source file、mapping type、target slot/extension、evidence count、last updated、source。
- 顯示 pending proposals 清單：proposal status、suggested mapping、actions：review / accept / edit / reject / skip。
- 顯示 skipped / not applicable decisions，避免使用者以為它們消失。
- 顯示「下次 scan 會套用」的說明與 last applied 狀態。
- 提供從 profile item 跳回 graph node / evidence detail 的入口。
- 更新 frontend API contract docs，記錄 profile page 需要的 mapping/profile response shape。

## 不包含範圍
- 不建立新的 canonical template schema；project custom profile 是 derived profile / overlay，不是新的完整 reference architecture template。
- 不讓使用者在本頁直接修改 `rag-core-v1`。
- 不做 remote template marketplace。
- 不做 team sharing/import/export。
- 不直接寫入被掃描 repo。
- 不在本頁產生 AI proposal；proposal 產生仍由 Task 20 API 負責。
- 不讓 profile overlay 直接 mutate 既有 `ai_system_map.json` artifact；切換 active scan profile 後仍需 rerun scan / normalize 產生新的 map artifact。

## 建議實作步驟
1. 定義 frontend view model：available scan profiles、active profile、default template、project profile、confirmed mappings、pending proposals、skipped decisions、last applied metadata。
2. 補 API contract doc：`GET /api/mapping-profile` 或等價 endpoint 的 response shape。
3. 建立 Project Mapping Profile page / tab。
4. 建立 Template/Profile summary header，清楚區分 `System default` 與 `Project custom`。
5. 建立 active profile selector，讓使用者選擇下次 scan 使用 system default 或 project custom profile。
6. 建立 confirmed mapping table/list。
7. 建立 pending proposal review section，連回 Task 20 decision flow。
8. 建立 skipped / not applicable section。
9. 建立空狀態：尚未確認任何 unmapped 時，只顯示 system default，並引導使用者回 viewer 掃描/檢查 needs confirmation。
10. 建立 graph/evidence deep link 或選取行為。
11. 加入 frontend tests 或 Playwright smoke test，確認標籤、空狀態、pending/confirmed/skipped sections 不混淆。

## 預期輸出
- frontend Project Mapping Profile page / route / tab。
- frontend mapping profile view model types。
- frontend mapping profile API client。
- active scan profile selector UI。
- 更新 `frontend/API_CONTRACT.md` 或 Epic 1 local API guide 的 profile section。
- focused frontend tests / smoke test。

## 驗收標準
- 使用者能清楚分辨 `rag-core-v1` 是 read-only default template，不是被 project decisions 改寫的檔案。
- 使用者能看到 project-specific mapping overlay / derived profile。
- 一開始沒有 confirmed mapping 時，頁面只顯示 system default 或清楚標示 project profile 尚未建立。
- 使用者能選擇下次 scan 使用 system default 或 project custom profile。
- confirmed mappings、pending proposals、skipped decisions 不混在同一種狀態裡。
- 使用者能理解哪些 decisions 會在下次 scan 生效。
- 頁面不暗示 pending proposal 已進入 canonical map。
- 頁面不暗示 output artifact `ai_system_map.json` 是可手動修改的設定來源。
- 若沒有任何 mapping，頁面提供清楚 empty state，而不是空白表格。

## 可能風險與注意事項
- 不要把 Project Mapping Profile 命名成 Custom RAG Template，除非 UI 同時清楚標示它是 derived from `rag-core-v1` 的 project version，而不是完整 reference architecture template。
- Profile/overlay 是 project-specific decisions，不等同 team shared template。
- active profile selection 影響下一次 scan，不應 retroactively 改寫既有 `ai_system_map.json`。
- 如果未來支援 import/export，必須清楚標示 provenance、source、version、digest。
- 若 profile 頁和 viewer detail 都能修改 mapping decision，必須共享同一套 Task 19/20 API，不要產生兩套狀態來源。

## 新手提示
這個頁面像「選擇掃描時要用哪張底圖」。一開始只有 KAI-Mind 的 default `rag-core-v1`。使用者確認 unmapped 後，系統會形成一個 project custom version；它看起來像自己的版本，但底層是 default template 加 confirmed mapping overlay。之後使用者可以選擇用 default 或自己的 project version 重新 scan。

## 視覺化說明
```text
┌──────────────────────────┐
│ Default template          │
│ rag-core-v1               │
│ System default / Read-only│
└──────────┬───────────────┘
           │
           ↓
┌──────────────────────────┐
│ Project Mapping Profile   │
│ Project custom / Active   │
│ Derived from rag-core-v1   │
└──────┬─────────┬─────────┘
       │         │
       ↓         ↓
┌──────────────┐ ┌──────────────────────┐
│ Confirmed    │ │ Pending proposals     │
│ mappings     │ │ accept/edit/reject    │
└──────┬───────┘ └──────────┬───────────┘
       │                    │
       ↓                    ↓
┌──────────────────────────────────────┐
│ Next scan applies confirmed overlay   │
│ and regenerates ai_system_map.json    │
└──────────────────────────────────────┘

Profile selector:

┌──────────────────────────┐
│ Scan using                │
│ ○ System default          │
│ ● Project custom version  │
└──────────────────────────┘
```
