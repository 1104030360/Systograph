# Task 17: Implement Markdown Summary Artifact

## 目標
實作 `MarkdownSummaryService`，從 validated `RagSystemMap` 產生 `ai_system_map.md`。Markdown 必須只讀 canonical map，不重新掃描檔案，也不得輸出 full secret。

## 為什麼要先做這個
Local web API 產生 JSON 後，使用者還需要可讀報告快速理解 system map。設計文件要求 Markdown 是 artifact output 的一部分，但它不能成為第二份 truth。

## Research 查證與採用結論（2026-06-06）

本段校正 researcher notes，避免把外部專案的做法誤套成本任務的必要需求。

### Source-backed observations

- Checkov 適合作為「scanner result 與 output rendering 解耦」的參考。上游 `checkov/common/output/` 目前有 `Report`、`Record` 與多種輸出支援，且 README 說明支援 CLI、CycloneDX、JSON、JUnit XML、CSV、SARIF、GitHub Markdown 等輸出。不過它不是一個單純的 `MarkdownFormatter` class 範例；GitHub Markdown 目前主要體現在 `Report.print_failed_github_md()` 這類 report method，會用 `tabulate(..., tablefmt="github")` 產生 GitHub table。
  - Source: https://github.com/bridgecrewio/checkov
  - Source: https://github.com/bridgecrewio/checkov/tree/main/checkov/common/output
  - Source: https://github.com/bridgecrewio/checkov/blob/main/checkov/common/output/report.py
- MultiQC 適合作為「複雜報告使用 templates 分離 presentation」的參考。上游仍有 `multiqc/templates/`，`pyproject.toml` 也列出 `jinja2>=3.0.0`。但 MultiQC 的主輸出是複雜 HTML / interactive report，不能直接推論本任務的 Markdown MVP 必須立刻引入 Jinja2。
  - Source: https://github.com/MultiQC/MultiQC
  - Source: https://github.com/MultiQC/MultiQC/tree/main/multiqc/templates
  - Source: https://github.com/MultiQC/MultiQC/blob/main/pyproject.toml
- Bandit 適合作為「formatter plugin 介面很薄」的 MVP 參考。官方文件說 formatter 是 plugin，內建 formatter 目前包含 csv、custom、html、json、sarif、screen、text、xml、yaml；沒有內建 Markdown formatter。因此它不應被寫成 Markdown 報告參考。
  - Source: https://bandit.readthedocs.io/en/latest/formatters/index.html
  - Source: https://github.com/PyCQA/bandit/tree/main/bandit/formatters
- GitHub task list `- [ ]` 可用在 issue / pull request comment 中形成 checkbox，適合作為 `recommended_next_checks` 的 Markdown 呈現格式。但這只是可讀報告的 GFM affordance，不是 machine contract。
  - Source: https://docs.github.com/get-started/writing-on-github/working-with-advanced-formatting/about-task-lists
- Jinja 官方建議使用 `Environment` 搭配 loader 載入 template，並明確設定 autoescape；但 Markdown 是 plain text artifact，本任務若未導入 HTML rendering，不應把 HTML autoescape 當成 secret masking 或 safety boundary。
  - Source: https://jinja.palletsprojects.com/en/stable/api/

### Decision for this task

- MVP 不新增 Jinja2 dependency。`pyproject.toml` 目前沒有 Jinja2，而 Task 17 的 report sections 固定、輸出格式可用 deterministic Python renderer 維護。先避免為單一 Markdown artifact 增加 runtime dependency 與 packaging surface。
- 可以設計 `MarkdownSummaryService` 的內部資料準備函式，例如 `_build_summary_view(system_map)`，讓未來若 sections 變得很複雜，可以低風險改成 template-backed renderer。
- `MarkdownSummaryService` 的 public API 只接收 validated `RagSystemMap`，回傳 `str`。它不接收 `project_path`、不讀 raw project files、不負責 open/write。
- Markdown 寫檔應留在 `OutputArtifactProvider` 或 `MapBuildService` 周邊的 artifact writer 邊界；service 本身維持 pure rendering。
- Secret safety 必須沿用既有 `SecretMaskingService` / validation policy。因為設計文件已要求 downstream consume already masked values，Task 17 仍要加 regression test：Markdown 不含 fake full secret；若 renderer 需要處理自由文字，應用既有 masking service，不另寫 secret detector。
- `recommended_next_checks` 建議輸出為 GFM task list，並測試輸出含 `- [ ]`。這是 PR/comment 友善格式，不代表使用者在 Markdown 勾選後會回寫 canonical JSON。
- Frontend 若要直接 view / download report，需要 local API 讀取受控 artifact。不要讓前端用任意 local filesystem path 讀檔；MVP 應由 session store / latest build result 找到最新 `map_markdown_path`，再回傳 plain Markdown。

## 承接 Task 16 延後功能
- 承接 Task 16 「不產生 Markdown」的延後範圍。
- Task 16 只保證 `ai_system_map.json` 與 map build result；本任務補上同一 run directory 內的 `ai_system_map.md`。
- Markdown artifact 必須由 `MapBuildService` 在 validated map 通過後呼叫產生，不能另外開一條 scanner pipeline。
- Local web API / CLI 回傳 artifact list 時，應同時顯示 JSON 與 Markdown 路徑，但 canonical truth 仍只有 `ai_system_map.json`。

## 前置需求
- Task 15 已完成 normalized validated map。
- Task 16 已完成 `MapBuildService`、local web API map build 與 JSON output。
- Task 5 已完成 secret masking。

## 實作範圍
- 建立 `MarkdownSummaryService`。
- 產生 sections：系統總覽、slot coverage、detected/missing slots、indexing flow、query/answer flow、local endpoints、external endpoints、network exposure、recommended next checks。
- 串接 `MapBuildService` 寫出 `ai_system_map.md`。
- 更新 map build response artifact metadata，讓 local API 可以回傳 Markdown artifact path。
- 建立 local-only report read endpoint，讓 frontend 可以 view / download latest Markdown report。
- 更新 `docs/work/Timmy/design/epic1-local-api-guide.md`，說明 Markdown artifact 是 report view，不是 schema source。
- 確認 Markdown 不含 full secret。
- 不新增 Jinja2 dependency；除非實作中先提出明確理由、測試策略與 packaging 影響，並更新本 plan。

## 不包含範圍
- 不重新讀 project files。
- 不產生 final READY/RISKY/NOT_READY verdict。
- 不做 GUI layout。
- 不做 CLI 專屬輸出流程；CLI 後續只讀同一批 artifacts。
- 不做 AI summary。
- 不在本任務導入 template engine。
- 不提供任意 path-based file read / static file server。
- 不建立 public sharing URL；report endpoint 只服務 local frontend / desktop flow。

## 建議實作步驟
1. 建立 `src/kai_mind/core/services/markdown_summary_service.py`。
2. 設計 deterministic Markdown section order，固定 heading 文字，方便 tests assert。
3. 建立內部 view-model/helper，例如 `_build_summary_view(system_map)`；它只能讀 `RagSystemMap` 欄位，不可讀 project files。
4. 用純 Python renderer 產生 Markdown tables / lists；先保持小函式與 section-level helpers，不用 Jinja2。
5. 從 map object 渲染 slot coverage table。
6. 從 detected / missing slots 渲染元件摘要，missing slots 不要補推論。
7. 從 flows 渲染 indexing flow 與 query / answer flow；若 map 缺資料，要輸出 unknown / not detected，不可假裝存在。
8. 從 endpoints 渲染 local/external endpoint section。
9. 從 risk_hints 渲染 network exposure / risk section，保留 uncertainty。
10. 將 `recommended_next_checks` 渲染成 GFM task list `- [ ] ...`。
11. 在 `OutputArtifactProvider` 加入 Markdown write method，或在既有 artifact writer 邊界加入等價寫入方法；不要讓 `MarkdownSummaryService` 自己寫檔。
12. 在 `MapBuildService` 中 validated map / JSON artifact 寫出成功後產生 Markdown，並把 Markdown path 放入 `MapBuildResult` / API artifact metadata，例如 `map_markdown_path`。
13. 建立 `GET /api/map/report` 或等價 route，回傳目前 session 最新 `ai_system_map.md` 內容。
14. Endpoint 回傳 `text/markdown; charset=utf-8`；若支援下載，使用 `?download=true` 加 `Content-Disposition: attachment; filename="ai_system_map.md"`，不要另開任意 path download endpoint。
15. Endpoint 不接受 raw filesystem path。若尚未 build 或 Markdown artifact 不存在，回傳 typed 404 / error response，不回傳 stack trace。
16. 更新 `docs/work/Timmy/design/epic1-local-api-guide.md`，說明 Markdown artifact 是 report view，不是 schema source，並記錄 report view/download endpoint。
17. 寫測試：sections 存在、GFM task list 存在、secret masked、不讀 raw project file、precondition error 不產生 Markdown、report endpoint 不接受任意 path 且可讀 latest Markdown。

## 預期輸出
- `src/kai_mind/core/services/markdown_summary_service.py`
- `tests/unit/core/test_markdown_summary_service.py`
- 更新 `src/kai_mind/core/services/map_build_service.py`
- 更新 `src/kai_mind/core/providers/output_artifact_provider.py`
- 視需要更新 `src/kai_mind/core/models/map_build.py`
- 更新 `src/kai_mind/web/routes/map_routes.py`
- 更新 `tests/web/` 或既有 API route tests，覆蓋 Markdown report endpoint。
- 更新 `docs/work/Timmy/design/epic1-local-api-guide.md`

## 驗收標準
- Local web API map build result 同時指向 `ai_system_map.json` 與 `ai_system_map.md`。
- CLI 後續接上時應重用同一個 artifact generation service。
- Markdown 包含設計文件指定 sections。
- Markdown 不包含 full fake secret。
- Markdown content 只依賴 validated map。
- `MarkdownSummaryService.render(validated_map)` 或等價 public API 回傳 `str`，不得接收 `project_path`。
- `recommended_next_checks` 以 `- [ ]` 呈現，並在文件中明確標註這只是 GFM report view。
- `pyproject.toml` 不新增 Jinja2，除非 plan 先被更新並記錄理由。
- `MapBuildResult` / API artifact metadata 包含 Markdown path 或受控 artifact reference。
- Frontend 可透過 local API 取得 Markdown report content；route 不接受任意 local path。
- 下載模式若實作，必須只針對 latest / selected controlled artifact，加正確 `Content-Disposition`。

## 可能風險與注意事項
- 不要在 Markdown 重新開檔讀 snippet。
- risk hint 要寫 uncertainty，不要假裝完整 security verdict。
- Markdown 是報告，不是 schema source。
- 不要在 Markdown renderer 重新實作 secret detection；優先重用 `SecretMaskingService` 與 validated map 的既有 masked values。
- 不要讓 GitHub task list 勾選狀態成為任何 canonical state；canonical truth 仍是 `ai_system_map.json`。
- 若未來導入 Jinja2，template 只做 presentation，不可放 secret masking、path scanning、network probing 或 schema decision logic。
- Report view/download endpoint 不可把 query string 的任意 `path` 交給 `FileResponse`；必須從 session/latest build metadata 或受控 artifact id 解析。

## 新手提示
Markdown summary 是給人看的翻譯版。正式資料仍然是 `ai_system_map.json`。

## 視覺化說明
```text
┌──────────────────────┐
│ validated             │
│ RagSystemMap          │
└──────┬─────────┬─────┘
       │         │
       ↓         ↓
┌──────────────┐ ┌──────────────────────┐
│ JSON writer  │ │ MarkdownSummary       │
│              │ │ Service.render()      │
└──────┬───────┘ └──────────┬───────────┘
       │                    │
       │                    ↓
       │         ┌──────────────────────┐
       │         │ Markdown string       │
       │         │ no file I/O           │
       │         └──────────┬───────────┘
       │                    ↓
       │         ┌──────────────────────┐
       │         │ OutputArtifact        │
       │         │ Provider.write_md()   │
       │         └──────────┬───────────┘
       ↓                    ↓
┌──────────────┐ ┌──────────────────────┐
│ ai_system_   │ │ ai_system_map.md      │
│ map.json     │ │ report view only      │
└──────────────┘ └──────────┬───────────┘
                            ↓
                 ┌──────────────────────┐
                 │ GET /api/map/report  │
                 │ view / download      │
                 └──────────────────────┘
```
