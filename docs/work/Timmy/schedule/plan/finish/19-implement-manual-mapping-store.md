# Task 19: Implement Manual Mapping Store

## 目標
實作 Systograph-managed manual mapping store，讓使用者確認過的 mapping 可以在下次 scan 重現。此任務處理 manual selection，不處理 AI proposal。

## 最新狀態校正（2026-06-07）
Phase 19 已完成第一版 core / local API implementation：

- 已新增 `ManualMapping` model、`ManualMappingService`、repository protocol / in-memory test implementation。
- 已新增 `/api/mappings` list/create/patch routes。
- 已讓 `/api/scans` 在同一個 `project_id` 下次 scan / normalize 時套用 confirmed mapping。
- 已補 `tests/unit/core/test_manual_mapping_service.py`、`tests/integration/test_manual_mapping_component_detection.py`、`tests/web/test_mapping_routes.py`。
- 已更新 `docs/work/Timmy/design/epic1-local-api-guide.md`。

前端目前可顯示 `unmapped / needs_confirmation` 狀態，且 `frontend/src/types.ts` 已保留 graph edge `status`；但 `frontend/src/services/viewerApi.ts` 仍只呼叫 `/api/map`、`/map`、`/api/scan/events`，尚未有 `/api/mappings` client、confirm/edit/reject/save buttons 或 persistence flow。Task 19 目前提供 backend/API 落點，不包含 GUI form。

Storage 決策已被 Task 27 更新：default manual mapping persistence 目標是 shared PostgreSQL-backed storage layer。Phase 19 目前先建立 repository boundary，local app / tests 使用可注入的 in-memory repository；具體 PostgreSQL repository、Alembic migration、DB URL 設定仍由 Task 27 storage layer 落地。Import/export YAML 或 repo-local `systograph.mapping.yaml` 只保留為 future exchange format，不是 Task 19 的預設 source of truth。

## 為什麼要先做這個
unmapped components 不能永遠停在 needs_confirmation。設計文件要求 user-confirmed mapping 寫入 Systograph-managed store，而不是修改被掃描 repo 或只改 output JSON。

外部工具的 repo-local policy file pattern（例如 `.snyk`）只能作為未來 team sharing / import-export 的參考，不改變 Epic 1 預設決策：Task 19 不把 confirmed mapping 寫入被掃描 project root，也不讓 output artifact 變成下一次 scan 的設定來源。

## 產品與 UX 校正
使用者看到 `unmapped / needs_confirmation` 時，不能只看到空狀態或被迫自己翻 source code。合理 UX 是 evidence-driven confirmation：

- 顯示掃到的 source file / observed kind / 為什麼 scanner 不確定。
- 顯示 masked evidence list 與 evidence ids。
- 顯示可採取的操作，例如 confirm、edit、reject、skip、mark not applicable。
- 儲存後明確提示：confirmed decision 會在下次 scan / normalize 生效，不會直接改現有 `ai_system_map.json`。

Task 19 只負責「使用者已經做出決策後」的安全保存、驗證與套用。若使用者不知道該確認成哪個 slot 或 extension，候選 mapping 的產生屬於 Task 20 `MappingProposalService`，不得塞進 `unmapped_components.suggested_actions`。

若決策來源是 Task 20 AI / rule proposal，Task 19 只保存使用者 accept/edit 後通過 validation 的結果；pending proposal、AI rationale、rank、recommendation_level、uncertainty_reason 都不應被當成 canonical fact 寫入 `ai_system_map.json`。

## Project-level mapping 與 custom template 邊界
Task 19 的 manual mapping store 不是新的完整 canonical template，也不是修改版 `rag-core-v1`。它保存的是 project-level confirmed decision：

```text
這個 project 裡，某個 source / evidence 經使用者確認後，應映射到某個 slot 或 extension。
```

這種 decision 的目標是讓同一個 project 下次 scan / normalize 可以穩定重現，不是把一次 confirmation 直接推廣成可套用到其他 project 的 custom RAG template。

不直接在 Task 19 產生 custom RAG template 的原因：

- 使用者確認的是「這個 project 的特殊事實」，不一定是可泛化規則。
- `src/foo.py` 是 reranker，不能直接推論成「所有叫 foo.py 的檔案都是 reranker」或「所有類似 project 都套用同一個架構」。
- 真正的 template / profile 需要處理 provenance、版本、active profile、derived-from 關係、匯入/匯出、team sharing、conflict resolution。
- pending / rejected / skipped decisions 不能混進 template；只有 confirmed 且 validation 通過的 mapping 才能影響下次 canonical map。

Task 24a 處理的是 Project Mapping Profile / Template Overlay：把 Task 19 confirmed mappings 和 Task 20 pending proposals 包成可視化、可選擇的 project-specific overlay。它仍不是新的完整 canonical template schema，也不直接改寫內建 `rag-core-v1`。產品上可呈現為「Project custom / Derived from rag-core-v1」，工程上仍是 default template + confirmed mapping overlay。

若未來要做真正可分享、可匯入、可套用到其他 project 的 custom RAG template，應另開 template generalization / import-export / versioning 任務，不應把 Task 19 的 project memory 當成通用 template。

## 承接 Task 16 延後功能
- 承接 Task 16 「不做 manual mapping」的延後範圍。
- Task 16 / Task 18 只會把 unmapped component 顯示為 `needs_confirmation`；本任務提供使用者確認後的持久化落點。
- 因為 Epic 1 優先 GUI/local web UI，本任務除了 core store，也要提供 local web API 讓前端提交 accept/edit/reject 後的 manual mapping。
- Manual mapping 生效方式是下次 scan / normalize 時套用，不是在現有 `ai_system_map.json` 上直接手改 canonical facts。

## 前置需求
- Task 13 已產生 unmapped components。
- Task 15 已有 validation。
- Task 18 已能讓 GUI/CLI 看到 unmapped。
- Task 27 的 database-backed storage layer / repository abstraction 已可提供 manual mapping decision persistence；若尚未完成，應先補齊該 storage foundation，不要回退成 file-based default store。

## 實作範圍
- 建立 `ManualMapping` model。
- 建立 DB-backed Systograph-managed mapping store，預設使用 Task 27 的 PostgreSQL-backed storage layer 與 repository abstraction。
- 以 project_id 分區儲存，project_id 由 resolved root path + git remote/git root hash 產生。
- 支援 existing slot mapping 與 new extension mapping。
- 支援 manual decisions：confirm existing slot、confirm extension、edit mapping draft、reject、skip_for_now、mark_not_applicable。
- 對 reject / skip / not_applicable 決策保留 audit metadata；只有 validation 通過的 confirmed slot / extension mapping 可以影響下一次 canonical map。
- 若 request 來自 proposal decision，必須保存 proposal id / decision source 作為 audit metadata，但不得保存 raw AI prompt、raw source code、unmasked evidence 或 `confidence`。
- 驗證 mapping references source file/evidence/slot。
- 將 confirmed mapping 套回 `ComponentDetectionService` 或 normalize flow。
- 使用 FastAPI 建立 local mapping routes，例如 `GET /api/mappings`、`POST /api/mappings`、`PATCH /api/mappings/{mapping_id}`。
- 更新 Epic 1 local API guide，加入 manual mapping request/response、validation error、rerun scan 生效規則，以及前端 confirmation UI 需要顯示的 evidence/action contract。
- 明確處理 Task 14 留下的 unmapped component 邊界：未確認前不得進 baseline `Flow.edges`；使用者確認後才可轉成 existing slot mapping 或 confirmed extension mapping。

## 不包含範圍
- 不寫入被掃描 repo。
- 不做 team sharing/import/export。
- 不做 AI proposal。
- 不做 GUI form；本任務只提供 local API 與 response contract，讓前端能做 unmapped detail / confirmation buttons。
- 不在本任務推論 unmapped component 應該放哪裡；若使用者不知道怎麼選，交給 Task 20 的 `MappingProposalService` 產生 pending proposal。
- 不做 runtime replay unknown step；trace/replay 呈現交給 Task 22。
- 不建立可選 scan profile / template version 頁面；project profile / derived version 管理交給 Task 24a。
- 不提供 repo-local `systograph.mapping.yaml` 作為 Epic 1 預設寫入路徑；該格式只保留給 future import/export 或 explicit `--mapping-file`。

## 建議實作步驟
1. [x] 確認 Task 27 storage foundation 狀態；Phase 19 先建立 `src/systograph/storage/repositories.py` repository boundary，具體 PostgreSQL implementation 留 Task 27。
2. [x] 建立 `src/systograph/core/models/mapping.py`。
3. [x] 建立 `src/systograph/core/services/manual_mapping_service.py`。
4. [x] 透過 repository protocol 實作 mapping create/update/list；測試中可注入 in-memory repository。
5. [x] 實作 repository-backed persistence boundary，底層不依賴 output artifact 或 repo-local YAML 作為 source of truth。
6. [x] 實作 manual decision model，至少可表達 confirmed mapping、rejected、skip_for_now、not_applicable。
7. [x] 實作 mapping validation：slot exists、evidence exists、edge no dangling refs。
8. [x] 將 valid manual mapping 套用到 component detection。
9. [x] 對 existing slot mapping：確認後才讓原本的 unmapped evidence 進入對應 `components_by_slot.<slot>`，並保留 confirmed mapping source。
10. [x] 對 new extension mapping：確認後才產生 `ExtensionComponent`；若 mapping 帶 extension edge，必須確認所有 edge endpoint 都存在。
11. [x] 對 reject / skip / not_applicable：不得產生 component / extension / flow edge；只更新 mapping decision state。
12. [x] 建立 FastAPI mapping routes，route 只能呼叫 `ManualMappingService`。
13. [x] API response 可讓前端渲染 unmapped detail：source file、observed kind、reason、masked evidence refs、available manual actions、status。
14. [x] 更新 `docs/work/Timmy/design/epic1-local-api-guide.md`。
15. [x] 寫測試：confirmed mapping 下次 scan 穩定重現；invalid slot 被拒絕；未確認 / rejected unmapped 不會進 slot；confirmed extension edge 不可有 dangling refs；reject / skip 不改 canonical map；web route 不直接改 canonical JSON。

## 預期輸出
- `src/systograph/core/models/mapping.py`
- `src/systograph/core/services/manual_mapping_service.py`
- 更新 `src/systograph/storage/repositories.py` 或等價 repository module
- `src/systograph/web/routes/mapping_routes.py`
- 更新 `docs/work/Timmy/design/epic1-local-api-guide.md`
- `tests/unit/core/test_manual_mapping_service.py`
- `tests/integration/test_manual_mapping_component_detection.py`
- `tests/web/test_mapping_routes.py`

## 驗收標準
- confirmed mapping 不寫入 project root。
- 預設 persistence 使用 Task 27 shared DB storage layer，且可在測試中注入 isolated test DB / fake repository。
- mapping digest 可記錄到 report metadata。
- invalid mapping 不進 canonical JSON。
- rerun scan 可重現 confirmed mapping。
- reject / skip / not_applicable 不會產生 slot、extension 或 flow edge。
- Task 14 產生的 `unmapped_components` 在未確認前仍維持 `needs_confirmation`，不會被自動接進 baseline flow。
- confirmed existing slot mapping 可在重新 normalize 後參與 standard slot / baseline flow derivation。
- confirmed extension mapping 可在重新 normalize 後成為 `extensions[]`；若有 extension edge，必須通過 validation 後才進 canonical JSON。
- local web API 可提交 confirmed mapping，但不得直接 mutate 既有 artifact。
- local web API 可支援前端顯示 unmapped confirmation affordance：source/evidence/reason/actions。
- API guide 已同步記錄 mapping routes 與「下次 scan 生效」規則。
- 尚待 Task 27 接手：將 repository protocol 連到實際 PostgreSQL-backed storage、Alembic migration 與 DB URL 設定。

## 可能風險與注意事項
- mapping store / DB URL 在測試中要可注入，不能寫 developer 真實 DB 或 user home。
- 不要直接 hard-code `~/.systograph` 或 repo-local YAML 作為預設；可保留為 future explicit import/export override。
- 舊版 file-based 方案若使用 OS App Data Directory，性質上也是持久性儲存；但最新預設已改為 Task 27 PostgreSQL-backed storage，不應再把 OS App Data Directory 寫成 Task 19 default。
- mapping 不可覆蓋 secret masking。
- 手動 mapping 比 AI proposal 可信，但仍需 validation。
- proposal-derived mapping 只有在使用者 accept/edit 後才可進 store；AI 草稿本身不可被 Task 19 當成已確認 mapping。
- `suggested_actions` 只代表使用者可採取的操作，例如 confirm/skip/not_applicable；不得把它當成「此 component 位於 flow 哪裡」的結構化資料。
- 2-3 個候選 placement、rationale、confidence-like wording 應存在 Task 20 的 `MappingProposal`，不放在 `UnmappedComponent.suggested_actions`。
- repo-local mapping file 是 future sharing/import/export 能力，不是 Task 19 的預設儲存策略。
- 未確認的 unmapped component 不可為了畫圖方便被升級成 detected slot、confirmed extension 或 flow edge。
- 不要因為使用者在 UI 上看到「Project custom」就把它當成新的 canonical RAG template；Task 24a 的 project profile 是 overlay / derived profile 管理，不是重寫 template schema。

## 新手提示
Manual mapping 是使用者說「這個檔案其實是 reranker」後，系統記住這個決定。下次掃描才能穩定重現。

## 視覺化說明
```text
┌──────────────────────┐
│ unmapped component    │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ user confirms mapping │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ Systograph mapping      │
│ store                 │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ next scan             │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ confirmed slot or     │
│ extension             │
└──────────────────────┘
```
