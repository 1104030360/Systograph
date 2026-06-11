# 2026-06-11 Phase24 Scan Boundary Review REP

## 實作邏輯
- Task 24 已移除 Template Import，實作重心改為 scan boundary review。
- 採 pending-only proposal lifecycle：本次 scan 只產生 review proposal，使用者 decision 只在下一次 `POST /api/scans` 透過 policy overlay 生效。
- Decision 使用 KAI-Mind-managed repository，不寫回被掃描 repo。
- Overlay 使用 `path + fingerprint`，避免同一路徑內容變更後仍無腦跳過造成漏掃。
- 追加修正：未決 suspicious file 會在 provider collection 前先 hold 在 `pending_boundary_review`，避免 `.env` 第一次就被 config parser 深入讀取。
- `scan_normally` 只在 path + fingerprint 仍相同時放行；fingerprint 變更、一次性 skip 用完或沒有 decision 時，都回到 pending review，不直接正常掃描。
- Response 僅包含 project-relative path、fingerprint、masked/bounded evidence packet，不包含 raw file contents、full secret 或本機絕對路徑。

## 步驟
1. 依 TDD 先新增 failing tests：unit tests 覆蓋 proposal/fingerprint/decision/overlay；web tests 覆蓋 create/list/decision、404、canonical map 不被 mutation。
2. 確認 RED：測試因缺少 `scan_boundary` model/service 模組失敗。
3. 新增 `scan_boundary.py` domain models 與 `ScanBoundaryReviewService`、`ScanBoundaryRepository`、`InMemoryScanBoundaryRepository`。
4. 擴充 `ProjectScanService.scan(..., inventory_policy=...)`，讓 policy overlay 在 provider collection 前套用。
5. 擴充 `MapBuildService`，只有 project session flow 且有 `project_id` 時才套用 scan boundary overlay；`POST /api/map/build` demo flow 不受影響。
6. 新增 `/api/scan-boundary-proposals` list/create/decision routes，並接入 FastAPI app/dependencies/schemas。
7. 新增 API trace scripts 並串入 `scripts/trace_all.sh`。
8. 依外部查證更新 Task24 plan、`docs/API-GUIDE.md`、`docs/work/Timmy/design/epic1-local-api-guide.md`。
9. 依後續安全語意修正補 TDD regression：`.env` 第一次 project scan 先 `pending_boundary_review`；使用者選 `scan_normally` 後，下次 fingerprint match 才交回一般 provider。

## 測試方式
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/unit/core/test_scan_boundary_review_service.py`
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/web/test_scan_boundary_routes.py`
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/unit/core/test_scan_boundary_review_service.py tests/unit/core/test_project_scan_service.py tests/web/test_scan_boundary_routes.py`
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/unit/core/test_scan_boundary_review_service.py tests/unit/core/test_project_scan_service.py tests/web/test_scan_boundary_routes.py tests/integration/test_map_build_service.py tests/web/test_project_scan_routes.py tests/web/test_mapping_proposal_routes.py`
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider`
- `.venv/bin/ruff check src tests`
- `.venv/bin/ruff format --check src tests`
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/mypy src tests`
- `scripts/trace_scan_boundary_proposals_create.sh --start-server`
- `scripts/trace_scan_boundary_proposals_list.sh --start-server`
- `scripts/trace_scan_boundary_proposals_decision.sh --start-server`
- `scripts/trace_scan_boundary_policy_overlay.sh --start-server`

## 遇到的問題與解法
- TruffleHog 外部研究修正：官方文件支持 verified/unknown/unverified 與 JSON output，但沒有足夠證據支持「官方內建完整互動式逐項 triage UI」。文件改成保守表述。
- 測試初版使用 mapping proposal 的 `reject` decision，但 scan boundary action 不包含 `reject`。修正為 `scan_normally`，保留 missing proposal 回 404 的驗收目的。
- `ProjectScanService.scan` 新增 keyword-only `inventory_policy` 後，既有 integration fake subclass signature 不相容。同步測試 fake signature，保持 LSP/type contract。
- 後續檢查發現 `.env` 若未被 `.gitignore` 擋住，第一次仍會被 config parser 讀取後再 masking。修正方式是把 boundary gate 放在 `ScanBoundaryReviewService` policy overlay，而不是硬塞進 `FilesystemProvider`，避免破壞使用者已選 `scan_normally` 的路徑。
- Ruff format/check 與 mypy 發現行長、格式、web test JSON helper 型別問題，已修正。

## 測試結果
- Targeted scan boundary/project scan tests：17 passed。
- Broader affected suite：36 passed。
- Full pytest：433 passed。
- Ruff lint：passed。
- Ruff format check：passed。
- Mypy：passed。
- 新增 scan boundary API trace scripts：create/list/decision 均已實際呼叫成功。
- 新增 policy overlay 行為 trace script：第一次 scan `files_scanned=1/files_skipped=1`，`scan_normally` 後第二次 scan `files_scanned=2/files_skipped=0`。
- 已確認 trace scripts 沒有殘留 uvicorn process。

## 最終狀態
- Task24 plan 內提出的 scan boundary review ideas 已全部實作並標註完成。
- Template Import 已明確從 Task24 移除，不再作為本任務工項。
- Project upload / GitHub URL ingestion 仍不屬於 Task24，維持 Task25 或後續獨立任務範圍。
