# Task 24: Final Epic 1 AI Scan Boundary Review and Local Template Import

## 目標
實作 Epic 1 最後階段功能：AI-assisted scan boundary review 與 local archive/mock template import，並優先提供 GUI/local web UI 可使用的 review/import API。這兩項都必須在 baseline scanner、manual mapping、validation、secret masking、policy store 穩定後才開始。

## 為什麼要先做這個
設計文件明確標註這兩項是 Epic 1 最後才做。scan boundary review 依賴 inventory/skip reason/masking/user policy store；template import 依賴 schema/template validation/supply-chain guardrails。Remote template import 採已決策選項 B：Epic 1 先支援 local archive/mock import，GitHub API 留到下一階段。因為產品入口優先 GUI/local web UI，pending proposal 應先能被 local API 讀取與確認。

## 前置需求
- Task 23 已完成 baseline hardening。
- Task 7 已有 deterministic `FileInventory`。
- Task 19 已有 KAI-Mind-managed store pattern。
- Task 20 已有 pending proposal pattern。
- Task 3/15 已有 template/schema validation。

## 實作範圍
- 建立 `ScanBoundaryReviewService`。
- 建立 suspicious file classifier：secret-like config、large/binary/model/vector db/generated/dependency/log。
- 產生 pending scan boundary proposal，不直接改 canonical inventory。
- 支援 user decisions：skip_this_run、always_skip、metadata_only、masked_summary_only、scan_normally。
- 使用 FastAPI 建立 local web API：列出 pending proposals、提交 user decision、讀取 import result。
- 更新 Epic 1 local API guide，加入 scan boundary review API、decision API、local template import API。
- 建立 KAI-Mind-managed scan policy store。
- 建立 `TemplateImportService`。
- 支援 local `.zip` / `.tar` archive 或 local mock template folder import。
- 驗證 `kai-mind-template.yaml`。
- 記錄 local source path、digest、license、validation status；若 manifest 自帶 provenance，可保留為 metadata。

## 不包含範圍
- 不讓 AI 自動略過檔案。
- 不在 CLI/CI 彈窗。
- 不實作 frontend modal；本 task 只提供 backend API 給 GUI 使用。
- Epic 1 不直接接 GitHub API，不下載 remote repo URL，不處理 GitHub token/private repo/rate limit。
- 不執行 template archive 裡的 script/workflow/postinstall。
- 不讓 remote template 覆蓋內建 `rag-core-v1` contract。

## 建議實作步驟
1. 建立 `src/kai_mind/core/services/scan_boundary_review_service.py`。
2. 建立 suspicious file proposal model。
3. 建立 scan policy store，測試時可注入 temp path。
4. 將 policy decisions 套回下一次 FileInventory。
5. 建立 FastAPI route 顯示 pending decisions，並支援使用者提交 decision。
6. 建立 CLI/CI machine-readable pending decision output，但不得彈窗。
7. 建立 `src/kai_mind/core/services/template_import_service.py`。
8. 實作 local archive/mock folder loader，不做 network download。
9. 驗證 template manifest schema。
10. 更新 `docs/work/Timmy/design/epic1-local-api-guide.md`，補上 scan boundary proposal、user decision、local template import、remote URL rejected response。
11. 寫測試：proposal pending、不直接改 inventory、web decision API、template import 不執行 code、remote URL rejected with clear error。

## 預期輸出
- `src/kai_mind/core/services/scan_boundary_review_service.py`
- `src/kai_mind/config/scan_policy_store.py`
- `src/kai_mind/core/services/template_import_service.py`
- `src/kai_mind/core/models/scan_policy.py`
- `src/kai_mind/core/models/remote_template.py`
- `src/kai_mind/web/routes/mapping_routes.py`
- `src/kai_mind/web/routes/template_routes.py`
- 更新 `docs/work/Timmy/design/epic1-local-api-guide.md`
- `tests/core/test_scan_boundary_review_service.py`
- `tests/core/test_template_import_service.py`
- `tests/web/test_scan_boundary_review_routes.py`
- `tests/web/test_template_import_routes.py`

## 驗收標準
- AI-assisted scan boundary review 只產生 pending proposal。
- proposal 不顯示 full secret。
- GUI/local web UI 可透過 local API 讀取 proposal 並提交 decision。
- CLI/CI 只輸出 machine-readable pending decision，不彈窗。
- 使用者確認後的 policy 不寫入被掃描 repo。
- Template import 只接受 local archive/mock folder，並只把內容當 data。
- Remote GitHub URL 在 Epic 1 會被拒絕，錯誤訊息說明此能力留到下一階段。
- Template manifest validation 失敗進 rejected/quarantine state。
- imported template metadata 含 provenance 與 digest。
- API guide 已同步記錄 review/import endpoints、pending proposal response、user decision payload、remote URL rejected behavior。

## 可能風險與注意事項
- 這是 final milestone，不得阻塞 baseline Epic 1。
- 即使只支援 local archive/mock，template import 仍有 supply-chain 風險，絕不可執行外部 code。
- review/import API 會直接影響 GUI modal / review queue / template store UI；改 API contract 時必須同步更新 API guide。
- 參考依據：GitHub template repository 與 archive API docs 可作下一階段 remote import 依據；OpenSSF Scorecard 可作 trust signal；SLSA provenance 可作來源 metadata 設計參考。Epic 1 已決策先不接 GitHub API。

## 新手提示
這一步像加「進階安全確認」和「模板商店」。先把基本 scanner 做穩，再加這些方便但有風險的能力。

## 視覺化說明
```text
┌──────────────────────┐
│ FileInventory         │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ ScanBoundaryReview    │
│ Service               │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ pending skip/include  │
│ proposals             │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ user decision         │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ scan policy store     │
└──────────────────────┘

┌──────────────────────────┐
│ local archive/mock        │
│ template                  │
└──────────┬───────────────┘
           ↓
┌──────────────────────────┐
│ TemplateImportService     │
└──────────┬───────────────┘
           ↓
┌──────────────────────────┐
│ isolated archive cache    │
└──────────┬───────────────┘
           ↓
┌──────────────────────────┐
│ manifest validation       │
└──────────┬───────────────┘
           ↓
┌──────────────────────────┐
│ TemplateStore             │
└──────────────────────────┘
```
