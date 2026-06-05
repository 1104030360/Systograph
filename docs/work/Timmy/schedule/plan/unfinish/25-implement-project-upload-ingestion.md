# Task 25: Implement Project Upload Ingestion

## 目標
實作 project archive upload / multipart upload ingestion，讓 local web API 可以接受使用者上傳的 project archive 作為 scan input。這不是 Task 24 的 template import；本任務處理「要被掃描的專案」輸入來源。

## 為什麼要獨立做這個
Task 16 的 MVP 只支援 `local_path`，因為 project upload 會引入 archive extraction、path traversal、zip bomb、large binary、model weights、dependency dirs、temporary workspace cleanup 等安全與資源風險。這些不應該混進第一個 end-to-end map build milestone。

## 承接 Task 16 延後功能
- 承接 Task 16 「不做 project zip upload / multipart upload」的延後範圍。
- 本任務處理的是 scan input ingestion，不是 Task 24 的 template import。
- 完成後應把 `POST /api/projects/import` 的 source type 從只支援 `local_path` 擴充到 `uploaded_archive`，但 scan 仍必須走 `MapBuildService`。
- 若需要保存 upload history，只能交給 Task 26；本任務只處理安全 ingestion 與 temporary scan workspace。

## 前置需求
- Task 16 已完成 local path import、map build API、local-only policy。
- Task 23 已完成 cross-platform path、snapshot safety、structured logging hardening。
- Task 24 已有 local archive/mock template import 的 archive safety pattern 可參考，但不可直接把 template import 當 project upload。

## 實作範圍
- 建立 `ProjectUploadIngestionService`。
- 支援 multipart upload project archive，例如 `.zip` / `.tar`。
- 將 archive 解到 KAI-Mind-managed temporary scan workspace。
- 驗證 archive entry path，拒絕 path traversal、absolute path、symlink escape。
- 設定 upload size、extracted size、file count、depth limit。
- 解壓後仍必須走 `FilesystemProvider` skip policy，不得掃 binary/model/dependency/generated/log 大檔。
- 建立 FastAPI upload route，例如 `POST /api/projects/upload`。
- 回傳 `project_id`、resolved temporary scan root、upload digest、limits result。
- 更新 `docs/work/Timmy/design/epic1-local-api-guide.md`，記錄 upload request/response、limits、error codes、cleanup policy。

## 不包含範圍
- 不做 remote URL / GitHub repo download。
- 不執行 archive 內任何 script、workflow、postinstall、notebook。
- 不把 uploaded project 永久保存成 history；長期保存交給 Task 26。
- 不做 frontend upload UI；本任務只提供 backend API。
- 不讓 upload route 繞過 Task 16 的 `MapBuildService`。

## 建議實作步驟
1. 建立 `src/kai_mind/core/models/project_upload.py`。
2. 建立 `src/kai_mind/core/services/project_upload_ingestion_service.py`。
3. 建立 safe archive extractor，所有 entry 先 normalize/validate 再寫入 temp workspace。
4. 加入 limits：max upload bytes、max extracted bytes、max file count、max depth。
5. 解壓後建立 project import record，輸出 `source_type="uploaded_archive"`。
6. 建立 `src/kai_mind/web/routes/upload_routes.py`。
7. 將 upload result 接到既有 `POST /api/scans` flow；scan 仍呼叫 `MapBuildService`。
8. 更新 API guide。
9. 寫測試：path traversal rejected、oversized archive rejected、binary/model/dependency skipped、temp cleanup、upload route 不直接呼叫 scanner internals。

## 預期輸出
- `src/kai_mind/core/models/project_upload.py`
- `src/kai_mind/core/services/project_upload_ingestion_service.py`
- `src/kai_mind/web/routes/upload_routes.py`
- 更新 `docs/work/Timmy/design/epic1-local-api-guide.md`
- `tests/unit/core/test_project_upload_ingestion_service.py`
- `tests/web/test_project_upload_routes.py`

## 驗收標準
- `POST /api/projects/upload` 接受合法 archive 並回傳可 scan 的 `project_id`。
- path traversal、absolute path、symlink escape 一律 rejected。
- oversized upload / extracted archive / file count 超限時回傳清楚 error。
- uploaded project scan 仍走 `MapBuildService`，不新增第二條 scanner pipeline。
- upload workspace cleanup 行為有測試。
- API guide 已同步記錄 limits、accepted formats、error format、local-only policy。

## 可能風險與注意事項
- Archive extraction 是高風險邊界，不可為了 demo 放寬限制。
- Uploaded archive 可能包含 secrets；logs、errors、snapshots 不得印出 raw secret。
- 不可讓 temporary workspace 留下未清理的大量檔案。
- 不要把 Task 24 template import 的 trust/provenance metadata 直接套到 project upload；被掃描專案不是 template。

## 新手提示
Local path import 是「我已經在這台機器上有資料夾」。Project upload 是「使用者丟一包壓縮檔給後端」。後者多了一整層解壓縮安全問題，所以要獨立計劃。

## 視覺化說明
```text
┌──────────────────────┐
│ multipart upload      │
│ project archive       │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ ProjectUpload         │
│ IngestionService      │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ safe archive validate │
│ limits / traversal    │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ temp scan workspace   │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ POST /api/scans       │
│ MapBuildService       │
└──────────────────────┘
```
