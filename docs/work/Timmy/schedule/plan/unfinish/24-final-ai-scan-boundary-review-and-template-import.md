# Task 24: Final Epic 1 Scan Boundary Review

## 目標
完成 Epic 1 最後一段「高風險但不改 canonical truth」的能力：建立 pending-only 的 scan boundary review proposal flow。

白話說，Task 24 現在只做一件事：

```text
掃描結果 / inventory / skipped files / masked evidence
  -> 找出可疑或需要使用者決定的掃描邊界
  -> 未決 suspicious file 先 hold 在 pending_boundary_review
  -> 產生 pending proposal
  -> 使用者決定下次掃描策略
  -> 下一次 scan 才套用 policy overlay
```

例如：當 `.env`、log、cache、大型檔案、model weights、vector DB、本地 persistence 等敏感或不適合完整掃描的檔案出現在專案裡時，project session scan 不應第一次就把未決 suspicious file 交給 provider 深入讀取。系統要先把它標成 `pending_boundary_review`，再提出「下次是否跳過 / metadata-only / masked-summary-only / 正常掃描」的建議；proposal / decision 不能回頭修改既有 `ai_system_map.json` 或被掃描 repo。

## 重要決策：移除 Template Import 工項（2026-06-11）
`Local Template Import / Scan Profile Catalog` 已從 Task 24 移除，不再作為本任務實作項目。

移除原因：

- 一般使用者真正期待的是「匯入 GitHub repo / 本機資料夾 -> 掃描 -> confirm component」，不是自行準備 `kai-mind-template.yaml`。
- 目前已完成的 `ManualMappingService` / `MappingProposalService` 更符合一般使用者的客製化流程。
- Epic 1 目前 canonical template selection 仍固定 `rag-core-v1`，即使匯入 scan profile 也不能立即套用，容易讓使用者困惑。
- `Template Import` 容易被誤解成 project import、RAG framework import、GitHub template import，和實際產品主流程衝突。
- 若未來真的需要，應另開 P3/admin feature，例如 `Scan Profile Catalog`，並等到多個內建 scan profiles 與 template activation policy 清楚後再做。

因此 Task 24 不再做：

- `TemplateImportService`
- `POST /api/templates/import`
- `GET /api/templates`
- `kai-mind-template.yaml` import
- archive / folder template package validation
- template quarantine / digest / provenance catalog

## 外部查證結論（2026-06-11）
已依使用者研究結果補做外部查證，結論是「scan boundary decision 外部化、fingerprint、防止污染被掃描 repo」方向正確，但 TruffleHog 的互動式 triage 描述需要修正為較保守說法。

已查證來源：

- Gitleaks 官方 README：支援 `--baseline-path`，baseline 可以讓後續 report 只包含新問題；官方也有 `.gitleaksignore` 與 finding `Fingerprint` 機制。這支持 KAI-Mind 採用「決策外部化 + fingerprint match」避免同一路徑內容改變時無腦忽略。來源：https://github.com/gitleaks/gitleaks
- Semgrep 官方文件：`semgrep scan --config` 可使用 registry rules、local YAML-defined rules、multiple config。這支持「掃描引擎」與「規則/策略輸入」解耦。來源：https://docs.semgrep.dev/running-rules
- Trivy 官方文件：misconfiguration scan 支援以 Rego 撰寫 custom checks。這同樣支持 policy-as-data / policy-as-code 與核心 scanner 分離。來源：https://trivy.dev/docs/latest/tutorials/misconfiguration/custom-checks/
- TruffleHog 官方 README：確認其結果可區分 `verified` / `unknown` / `unverified`，並支援 JSON output；但官方文件沒有足夠證據支持「內建完整互動式逐項 triage UI」這個說法。因此 Task 24 文件只採用「可作為 triage 狀態與結果分類參考」，不寫成官方 interactive UI 對標。來源：https://github.com/trufflesecurity/trufflehog

對 Task 24 的落地影響：

- `ScanBoundaryDecision` 必須存於 KAI-Mind-managed repository，不寫回目標 repo。
- Overlay 必須依 `path + fingerprint` 套用；如果 `.env` 同路徑但內容/metadata 改變，舊 decision 失效並回到 `pending_boundary_review`，避免新內容被舊決策直接放行或跳過。
- Proposal / decision 是 policy overlay，不是 canonical scanner fact；本次 scan 產生 proposal 後，不回頭改當次 `FileInventory` 或 `ai_system_map.json`。
- Response 只提供 masked/bounded packet，不提供 raw file content、raw secret 或本機絕對路徑。

## 已完成、必須承接但不要重做
- Task 16 已完成 local API shell，但 `POST /api/map/build` 仍是 viewer demo 捷徑，不建立 `project_id`。
- Task 18 已完成 `ViewerSessionService` / viewer payload 路線，web route 採獨立 `routes/*.py` + `web/schemas.py`。
- Task 19 已完成 `ManualMappingService`、repository protocol / in-memory implementation、`/api/mappings` routes。
- Task 20 已完成 pending-only `MappingProposalService`、`MappingEvidencePacketBuilder`、`/api/mapping-proposals` lifecycle。
- Task 21 已完成 target-scoped detail scan，並採 append-only evidence/update map session 的路線。
- Task 22 已完成 opt-in query trace，明確把 runtime side effect 與 baseline scan 分開。
- Task 23 已完成 local API hardening、path safety、snapshot safety、stable masked error 與 `docs/API-GUIDE.md` 更新。
- Task 25 已明確把 project upload ingestion 拆走；archive scan input 不屬於本任務。
- Task 27 已把「長期 persistence 方向」改成 shared PostgreSQL-backed repository abstraction；Task 24 不應再規劃獨立 file-based default store。

## 已完成的使用者客製化主流程
一般使用者若想修正掃描判斷，應走已完成的 manual mapping / mapping proposal flow：

```text
default rag-core-v1 scan
  -> detected / unmapped components
  -> user confirm / edit / reject / skip
  -> save mapping decision
  -> next scan applies confirmed mapping
```

這條路線比要求使用者新增 scan template 更合理，也更符合目前產品狀態。

## Task 24 最新實作狀態（2026-06-11）

目前 Task 24 的 scan boundary review 已完成 backend/core/API 落地。

已實作檔案：

- `src/kai_mind/core/models/scan_boundary.py`
- `src/kai_mind/core/services/scan_boundary_review_service.py`
- `src/kai_mind/core/services/project_scan_service.py`
- `src/kai_mind/core/services/map_build_service.py`
- `src/kai_mind/storage/repositories.py`
- `src/kai_mind/web/routes/scan_boundary_routes.py`
- `src/kai_mind/web/app.py`
- `src/kai_mind/web/dependencies.py`
- `src/kai_mind/web/schemas.py`
- `tests/unit/core/test_scan_boundary_review_service.py`
- `tests/unit/core/test_project_scan_service.py`
- `tests/web/test_scan_boundary_routes.py`
- `docs/API-GUIDE.md`
- `docs/work/Timmy/design/epic1-local-api-guide.md`

### A. Scan boundary review models
- 已完成：建立 `ScanBoundaryEvidencePacket`。
- 已完成：建立 `ScanBoundaryProposal`。
- 已完成：建立 `ScanBoundaryDecision`。
- 已完成：型別沒有重用 `mapping.py`；scan boundary decision 和 component mapping decision 是不同 domain。

### B. ScanBoundaryReviewService
- 已完成：建立 `ScanBoundaryReviewService`。
- 已完成：根據既有 `FileInventory`、`SkippedFile`、masked evidence 產生 bounded review packet。
- 已完成：suspicious target 類型至少涵蓋：
  - secret-like config
  - large / binary / generated
  - dependency / cache / log
  - model weight / vector DB / local persistence
- 已完成：proposal status 採 `pending_user_confirmation`。
- 已完成：proposal response masked / bounded / traceable，不包含 raw secret 或本機絕對路徑。
- 已完成：未決 suspicious file 會在 provider collection 前移到 `pending_boundary_review`，避免第一次掃描就完整深讀。

### C. User decisions
user decision 至少支援：

- `skip_this_run`
- `always_skip`
- `metadata_only`
- `masked_summary_only`
- `scan_normally`

- 已完成：上述 action 全部支援。
- 已完成：決策只能影響下一次 scan 的 controlled policy overlay，不 retroactively 修改已產生的 canonical map。
- 已完成：`skip_this_run` 套用一次後會記錄 `applied_at`，後續不再套用。
- 已完成：`scan_normally` 只有在 path + fingerprint 仍相同時放行，讓該 target 回到一般 scanner/provider 規則。

### D. Repository boundary
- 已完成：建立 `ScanBoundaryRepository` protocol。
- 已完成：已接到既有 repository/service boundary，並由 `src/kai_mind/storage/repositories.py` re-export。
- 已完成：提供 `InMemoryScanBoundaryRepository` 給 tests/dev/local API 使用。
- 已完成：沒有 repo-local default store。
- 已完成：decision 不會寫回被掃描 repo。

### E. Policy overlay
- 已完成：實作 apply-policy overlay 機制。
- 已完成：overlay 在 provider collection 前套用，未決 suspicious file 先 hold；proposal create 不改 latest map payload。
- 已完成：overlay 使用 path + fingerprint，並在 `skipped_files` summary 保留 deterministic audit trail。
- 已完成：不直接修改目前 `FileInventory`、既有 `ai_system_map.json` 或已產生 artifact。

### F. Local API / docs
採目前既有 route 拆分模式，建立：

- 已完成：`src/kai_mind/web/routes/scan_boundary_routes.py`

採目前既有 service + dependency injection pattern，更新：

- 已完成：`src/kai_mind/web/app.py`
- 已完成：`src/kai_mind/web/dependencies.py`
- 已完成：`src/kai_mind/web/schemas.py`

文件必須同步更新：

- 已完成：`docs/work/Timmy/design/epic1-local-api-guide.md`
- 已完成：`docs/API-GUIDE.md`

## API contract 建議

- `GET /api/scan-boundary-proposals?project_id=...`
- `POST /api/scan-boundary-proposals`
- `POST /api/scan-boundary-proposals/{proposal_id}/decision`

規則：

- 必須走 project session flow：`POST /api/projects/import` -> `POST /api/scans`。
- 不支援只靠 `POST /api/map/build` demo flow 建 proposal，因為那條路沒有 `project_id`。
- response 必須 masked / bounded / traceable。
- decision API 只保存決策與 audit trail，不直接改 canonical artifact。
- 第一次 project session scan 會先把 unresolved suspicious file hold 在 `pending_boundary_review`；`scan_normally` decision 後，下一次 fingerprint match 才交回一般 provider 掃描。

## 不包含範圍
- 不讓 AI / rule helper 自動修改 canonical inventory。
- 不在 `POST /api/map/build` 內偷偷自動跑 boundary review。
- 不把 boundary review decision 寫進被掃描 repo。
- 不做 project upload / multipart ingestion；那是 Task 25。
- 不做 GitHub URL project ingestion；那應另開 `github_url project ingestion` 任務。
- 不做 persistent session/history 的完整 DB 落地；那是 Task 26 / Task 27 路線。
- 不做 local template import / scan profile catalog。
- 不做 `kai-mind-template.yaml` 匯入。
- 不做 frontend modal / review queue UI；本任務只提供 backend/API 落點。

## 實作步驟對照
1. 已完成：建立 scan boundary core models，不重用 `mapping.py`。
2. 已完成：建立 scan boundary repository protocol 與 in-memory test/dev implementation。
3. 已完成：實作 `ScanBoundaryReviewService` deterministic proposal。
4. 已完成：目前沒有 AI/provider 接入；若未來接入，也只能吃 masked / bounded packet，不得拿 raw file read / shell / repo traversal 權限。
5. 已完成：實作 decision lifecycle：list、create、decision。
6. 已完成：實作 apply-policy overlay 機制，確認只影響未來 rerun。
7. 已完成：建立 FastAPI routes，route 只呼叫 service。
8. 已完成：更新 `docs/work/Timmy/design/epic1-local-api-guide.md` 與 `docs/API-GUIDE.md`。
9. 已完成：寫 unit / web tests，驗證 pending-only、masking、no absolute local path、no canonical mutation、project-session-only。

## 輸出狀態
- 已完成：`src/kai_mind/core/models/scan_boundary.py`
- 已完成：`src/kai_mind/core/services/scan_boundary_review_service.py`
- 已完成：更新 `src/kai_mind/storage/repositories.py`
- 已完成：`src/kai_mind/web/routes/scan_boundary_routes.py`
- 已完成：更新 `src/kai_mind/web/app.py`
- 已完成：更新 `src/kai_mind/web/dependencies.py`
- 已完成：更新 `src/kai_mind/web/schemas.py`
- 已完成：更新 `docs/work/Timmy/design/epic1-local-api-guide.md`
- 已完成：更新 `docs/API-GUIDE.md`
- 已完成：`tests/unit/core/test_scan_boundary_review_service.py`
- 已完成：`tests/web/test_scan_boundary_routes.py`

## 驗收標準狀態
- 已驗證：scan boundary review 只產生 pending proposal，不直接改 canonical inventory。
- 已驗證：decision payload / response 不顯示 full secret 或本機絕對路徑。
- 已驗證：proposal lifecycle 與 Task 20 proposal pattern 一致：可 list、create、decision，且可 audit。
- 已驗證：unresolved suspicious file 會先 hold 在 `pending_boundary_review`，不會第一次就交給 provider 完整深讀。
- 已驗證：`scan_normally` 後下一次 fingerprint match 才交回一般 scanner/provider 規則。
- 已驗證：policy overlay 不 retroactively mutate 已有 `ai_system_map.json`。
- 已驗證：`POST /api/map/build` 不會偷偷觸發 boundary review。
- 已驗證：unknown `project_id` 回 404 typed error。
- 已驗證：decision 不寫入被掃描 repo。
- 已完成：`docs/work/Timmy/design/epic1-local-api-guide.md` 與 `docs/API-GUIDE.md` 都有同步更新。

## 可能風險與注意事項
- 不要把 Task 24 做成第二套 scanner pipeline。
- 不要把 boundary review proposal 跟 manual mapping proposal 混成同一個 model；兩者生命週期相似，但目標與安全邊界不同。
- 若 Task 27 的 DB 落地尚未完成，Task 24 也不能回退成 repo-local default store；應先守住 repository boundary 與 in-memory fallback。
- 任何 AI/provider 輸出都只能是 proposal，不是 source of truth。
- 這個任務的價值是補 scan boundary safety，不是新增 project import，也不是新增 template system。

## 視覺化說明
```text
project session
  -> deterministic inventory
  -> unresolved suspicious files held as pending_boundary_review
  -> skipped files / masked evidence
  -> ScanBoundaryReviewService
  -> pending boundary proposal
  -> user decision
  -> policy overlay for next rerun

important:
  proposal does not mutate current FileInventory
  proposal does not mutate current ai_system_map.json
  decision does not write to scanned repo
```
