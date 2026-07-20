# 前端同步總覽：目前 Backend-ready 工作（2026-07-15）

Status: backend implementation ready；frontend integration pending

Last updated: 2026-07-20（合併 7/3 穩定性紀錄、重查 current code 與 open PR）

## 先看結論

Frontend `main` 已完成專案匯入、基本 scan、boundary decision、SSE progress、基本 Viewer 與
test foundation。這些基線可以繼續使用，不需要重做。

目前還沒完成的是：Scan Inventory、v2 / legacy extension、project / build-scoped Viewer、Apply、
Detail Scan、Mapping Proposal、Query Trace、report，以及 rich profile / readiness 顯示。

7/3 文件中的已完成內容已整理成 baseline，未完成的四個 PR 也已依 current backend contract
改寫到本同步包。因此舊文件不再需要作為獨立入口。

## Frontend 目前做到哪裡

| 區域 | Current frontend `main` | 判定 |
| --- | --- | --- |
| Project import | 已呼叫 `POST /api/projects/import` | 已完成基本串接 |
| Basic scan | 已呼叫 `POST /api/scans` 並處理 sensitive boundary decision | 已完成舊 flow；Inventory preflight 待補 |
| Scan progress | 已接 `/api/scan/events`，保留 reconnect / reset | 已完成基線 |
| Viewer | 已用 Zod + React Query 載入 `/api/map` / `/map` | Demo 可用；project / build scope 待補 |
| Sample honesty | Viewer / Scan Template 有 Sample 標示 | 已完成基線 |
| Frontend tests | Vitest、RTL、jsdom 與 CI 已存在 | 已完成基線 |
| Detail / Mapping / Trace / Report | `main` 仍是 sample、mock 或未接線 | 未完成 |

## Backend-ready 工作總表

| 優先 | Frontend 工作 | 為什麼現在要做 | 詳細文件 |
| ---: | --- | --- | --- |
| 1 | `ai-system-map/v2` + 移除 legacy extension | Normal backend 已切 v2，舊 request 會被拒絕 | [v2 cutover](./frontend-ai-system-map-v2-cutover.md) |
| 2 | Project / build-scoped Viewer | `/api/map` 是 process-wide demo，不足以識別專案與 child build | [Backend-ready integration](./frontend-backend-ready-integration.md#1-改用-project--build-scoped-viewer) |
| 3 | Scan Inventory Review | Backend preflight、typed errors 與 one-run selection 已完成 | [Inventory Review](./frontend-inventory-selection-review.md) |
| 4 | Detail Scan | Backend 可建立同 scan 的 child build | [Detail Scan](./frontend-backend-ready-integration.md#3-串接-detail-scan) |
| 5 | Proposal / Mapping / Apply | Backend proposal、audit mapping 與 Apply 已完成 | [Mapping / Apply](./frontend-backend-ready-integration.md#4-串接-mapping-proposalmanual-mapping-與-apply) |
| 6 | Query Trace | Backend opt-in trace 已完成，可綁 project / build | [Query Trace](./frontend-backend-ready-integration.md#5-串接-query-trace) |
| 7 | Report、Profile、Readiness | Backend 已提供 session report 與 inline rich result；project report 仍有邊界 | [Report / Rich result](./frontend-backend-ready-integration.md#6-report-與其他-artifacts) |

## 三份 Frontend 工作文件

### 1. Scan Inventory Review

[frontend-inventory-selection-review.md](./frontend-inventory-selection-review.md)

使用者在每次 scan 前查看 backend 準備好的安全範圍，只對這一次 scan 做調整。Frontend 不讀
filesystem、不解析 TOML，也不能繞過 hard safety。

### 2. ai-system-map/v2 Cutover

[frontend-ai-system-map-v2-cutover.md](./frontend-ai-system-map-v2-cutover.md)

把 active sample、type、proposal form 與 mock 從 v1 / `new_extension_component` 改成 current v2
contract。Historical v1 migration 由 backend 負責。

### 3. Backend-ready Integration

[frontend-backend-ready-integration.md](./frontend-backend-ready-integration.md)

承接 7/3 尚未完成的 Detail Scan、Mapping Proposal、Query Trace、Artifact Actions，並補上後來完成的
build-scoped Viewer、Apply、profile / readiness contract。

## 7/3 文件合併結果

### 已完成並保留為 baseline

| PR | 已完成行為 |
| --- | --- |
| #221 | Cancel / error 會停止 scan progress 與 SSE |
| #222 | Viewer request 可取消；cancel 與 timeout 分開 |
| #223 | Sample Viewer 有常駐 Sample data 標示 |
| #224 | Mock Scan Template 有標示，無作用按鈕停用 |
| #225 | 空 API base URL 有安全 fallback |
| #226 | SSE 單次瞬斷先重連，連續失敗才降級 |
| #232 | Frontend test runner 與 CI gate 已建立 |

### 尚未完成並已移入 current work item

| 舊 PR | 2026-07-20 狀態 | Current 處理 |
| --- | --- | --- |
| #198 Detail Scan | OPEN、與 `main` 衝突 | 依 current child-build response 重建 / rebase |
| #199 Mapping Proposal | OPEN draft、stacked on #198 | 拆成獨立 PR，更新 v2 candidate / Apply |
| #218 Query Trace | OPEN draft | 依 build-scoped v2 contract rebase |
| #227 Artifact Actions | OPEN | 保留 safe report；移除一般 UI 的 server-local path loader |
| #231 API tests | OPEN issue | Contract 更新後補 tests、mocks、fixtures |

詳細原因、endpoint、錯誤處理與驗收條件都在
[Backend-ready integration](./frontend-backend-ready-integration.md)。

## Backend / Frontend 邊界

| Backend 負責 | Frontend 負責 |
| --- | --- |
| Schema validation、v1 migration、v2 canonical truth | Parse current contract、render、typed UI state |
| Inventory enumeration、TOML policy、hard safety | 顯示 preflight、收集 one-run decisions |
| Build lineage、Apply、Detail child build、latest promotion | 保存 project / scan / build identity並切換 response |
| Proposal evidence、mapping audit、profile / readiness inference | 顯示候選、收集 decision，不自行推論 |
| Query Trace egress policy、timeout、masking | Explicit opt-in、safe replay、error / partial state |
| 10-artifact atomic publish | 只透過 public safe API 取資料，不讀 server-local path |

## 建議交付順序

1. 先更新 v2 types / samples、project / build-scoped Viewer 與 API-facing tests。
2. 接 Scan Inventory preflight / one-run selection。
3. 接 Detail Scan child-build flow。
4. 接 Mapping Proposal / Manual Mapping / Apply。
5. 接 Query Trace。
6. 接 safe report 與 rich profile / readiness panels。

每個步驟用獨立 PR。不要把 #198、#199、#218、#227 原樣疊回同一個大 branch。

## 完整交接驗收

- [ ] 三份工作文件都被 frontend owner 逐項確認。
- [ ] `frontend/API_CONTRACT.md` 與 current backend API 一致，不再把已完成 endpoint 寫成 future。
- [ ] API mode 使用 project / build-scoped Viewer，不把 process-wide `/api/map` 當唯一真相。
- [ ] Inventory、v2、Detail、Mapping / Apply、Trace 與可安全串接的 Report 各有獨立測試與 UI states。
- [ ] Rich graph、profile、readiness 只 render backend result，不在 browser 重算。
- [ ] Static execution / evidence / Mermaid 在 safe artifact API 出現前維持 deferred。
- [ ] Sample、mock、cancel、SSE reconnect、base URL fallback 等 7/3 baseline 沒有 regression。
- [ ] 每個 PR 通過 Vitest、RTL、lint、TypeScript build 與對應 API mode QA。

## Source of truth

- [API Guide](../../../API-GUIDE.md)
- [Model Contract](../../../MODEL-CONTRACT.md)
- [Plan 13](../../Timmy/schedule/plan/unfinish/phase2/static-trace-plan/s1-v2-cutover/13-retire-legacy-extension-contract.md)

文件衝突時，依序相信 current backend code、Pydantic schema、API Guide / Model Contract，最後才是
舊 PR 或舊 Meeting-Sync 文案。

## 不屬於目前 Frontend 工作

- 自行讀 backend filesystem、TOML、raw artifact path 或 secret。
- 在 browser 進行 v1-to-v2 / legacy persisted mapping migration。
- 自行推論 component、edge、profile、readiness 或 Mapping Completeness。
- 在 safe artifact API 尚未完成前自行拼 static execution / evidence / Mermaid URL。
- 修改 backend rollback、migration command 或 artifact publisher。
