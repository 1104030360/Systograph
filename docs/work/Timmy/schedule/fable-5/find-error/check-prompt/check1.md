# 前提
請先閱讀並遵守 `/Users/linjunting/Local_AI_Health_Doctor/AGENTS.md`。只有在專案結構真的改變、且需要成為長期開發規則時，才更新 AGENTS.md；一般實作紀錄請寫到 TODO / Report。

# 背景知識
1.目前專案的產品定位請先看：`/Users/linjunting/Local_AI_Health_Doctor/AGENTS.md`
這個專案是 KAI-Mind / Local AI Health Doctor，是 AI Agent / RAG Release Readiness Gate。它的主要目標是在 demo、交付、部署或 CI/CD 前，掃描既有 local AI / RAG 專案並輸出 readiness report。它不是 chatbot、不是 RAG builder、不是完整 observability 平台，也不是企業級資安掃描器。

2.目前還沒完成、後續可能會接續開發的 plan 放在：
`/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/schedule/plan/unfinish`
這裡的「前後端分法」請理解成 issue / plan 的交付拆分，不是把工作歸到既有 Epic 2。除非 roadmap 另外明確重定義，以下檔案只能當作目前 unfinish issue 候選與後續接續開發脈絡。
其中目前跟後端延伸、前端對接與 issue 拆分最相關的是：
`/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/schedule/plan/unfinish/20a-implement-ai-mapping-proposal-frontend-flow.md`
`/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/schedule/plan/unfinish/21a-implement-detail-scan-frontend-flow.md`
`/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/schedule/plan/unfinish/24a-implement-project-mapping-profile-page.md`
`/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/schedule/plan/unfinish/24b-implement-project-scan-and-boundary-decision-frontend-flow.md`
`/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/schedule/plan/unfinish/25-implement-project-upload-ingestion.md`
`/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/schedule/plan/unfinish/26-implement-persistent-session-store-and-scan-history.md`
`/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/schedule/plan/unfinish/27-introduce-database-backed-storage-layer.md`
`/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/schedule/plan/unfinish/28-introduce-openapi-generated-frontend-sdk.md`

3.目前過去已經完成的計劃放在：
`/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/schedule/plan/finish`
注意目前目錄名稱是 `finish`，不是 `finished`。這裡面有 Task 1 到 Task 25 的 backend 開發脈絡，可以用來理解目前專案狀態，不要只看單一 task。

4.目前專案的大方向設計文件如下：
`/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/design/epic1-backend-design.md`
`/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/design/epic1-local-api-guide.md`
`/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/design/epic1-scan-pipeline-research.md`

5.目前正式 API 文件如下：
`/Users/linjunting/Local_AI_Health_Doctor/docs/API-GUIDE.md`
如果新增、刪除、修改 API，或改變 request / response / error code / lifecycle，必須同步更新這份文件，這樣前端工程師才知道 API 怎麼用。

6.目前 API 相關 shell script 都放在：
`/Users/linjunting/Local_AI_Health_Doctor/scripts`
如果新增 API 或改 API 行為，記得新增或更新對應 `trace_*.sh`。完成後可以跑 `scripts/trace_all.sh` 來確認各 endpoint 的 input/output 行為是否仍然對齊文件。

7.目前後端主要程式碼在：
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind`
目前 schema contract 在：
`/Users/linjunting/Local_AI_Health_Doctor/schemas/ai-system-map.v1.schema.json`
目前前端程式碼在：
`/Users/linjunting/Local_AI_Health_Doctor/frontend`

8.目前 Python 後端技術棧定義在：
`/Users/linjunting/Local_AI_Health_Doctor/pyproject.toml`
目前是 Python 3.11+，主要 runtime dependency 是 `pydantic`、`fastapi`、`uvicorn`、`typer`、`jsonschema`、`httpx`、`packaging`、`pathspec`、`PyYAML`。品質檢查使用 `pytest`、`ruff`、`mypy`，而且 mypy 是 strict mode。

9.目前後端 package 大致分成這幾層：
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/core/models`
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/core/providers`
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/core/services`
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/web`
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/cli`
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/storage`

10.目前最重要的後端架構原則是：Web route 和 CLI 都只是 thin adapter，不能把 scanner / provider / normalize / validation 邏輯塞在 route 或 command 裡。真正的工作流要放在 `core/services`，低階掃描放在 `core/providers`，資料契約放在 `core/models`。

11.目前 L1 map build 的主流程如下：
使用者輸入 project path
-> `OutputArtifactProvider` 檢查 precondition / output run
-> `ProjectScanService` 建立 raw scan result
-> `FilesystemProvider` 建立 deterministic file inventory
-> `ConfigParseProvider` / `DockerComposeProvider` / `DependencyManifestProvider` / `CodePatternProvider` 收集 facts / evidence / issues
-> `RagTemplateService` 載入 `rag-core-v1`
-> `ComponentDetectionService` 將 raw facts 映射到 RAG slots / extensions / unmapped components
-> `EndpointDetectionService` 推導 endpoints
-> `RiskHintService` 產生 release-readiness risk hints
-> `FlowDerivationService` 產生 indexing / query_answer flows
-> `SystemMapNormalizeService` 組成 canonical `RagSystemMap`
-> `SystemMapValidationService` 做 schema + cross-reference + secret/path safety validation
-> `OutputArtifactProvider` 寫出 `ai_system_map.json` / `ai_system_map.md`
-> `ViewerSessionService` 產生 frontend 用的 `graph_view_model`

12.目前總指揮 service 是：
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/core/services/map_build_service.py`
`MapBuildService.build()` 是共用核心，不管 Web API 或 CLI 都應該走這條，不要再複製一套 map build pipeline。

13.目前 scanner 聚合 service 是：
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/core/services/project_scan_service.py`
`ProjectScanService` 負責把 provider-local output 合成 `ProjectScanResult`，同時做 provider failure isolation、dedupe、safe logging。單一 provider 壞掉時不應拖垮整個掃描，而是轉成 `ParseIssue` / warning。

14.目前 file inventory 的核心是：
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/core/providers/filesystem_provider.py`
它會優先用 git inventory，失敗或非 git repo 才 fallback recursive scan。它會跳過 `.git`、`node_modules`、`.venv`、build output、cache、coverage、generated file、binary、大檔、大 log、model weights、root 外 symlink、unreadable file。scanner 預設 read-only，不能修改使用者 repo。

15.目前 filesystem skip 是 scanner safety 的第一層。Task 24 的 scan boundary review 只會針對「原本可掃、但需要使用者確認」的 suspicious file 產生 proposal，例如 `.env`、secret-like config、vector persistence path。已經被 deterministic filesystem hard-skip 的 large/binary/generated/log、dependency/cache、model weight 不會再拿去問使用者。

16.目前 scan boundary review 的核心檔案如下：
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/core/models/scan_boundary.py`
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/core/services/scan_boundary_review_service.py`
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/web/routes/scan_routes.py`
它是 same-run gate，不是長期 policy store。

17.目前 `POST /api/scans` 的正式流程是：
先 `POST /api/projects/import` 建立 `project_id`
-> `POST /api/scans`
-> `FilesystemProvider().build_inventory()`
-> `ScanBoundaryReviewService.create_proposals()`
-> 如果還有 unresolved suspicious target，就回 `status="requires_boundary_decision"`，`build_result=null`，不寫 artifact，不更新 `/api/map`
-> 如果 decisions 完整，就用 `ScanBoundaryReviewService.for_decisions()` 產生 one-run inventory overlay
-> 再呼叫 `MapBuildService.build(...)`
-> 成功後存到 `InMemorySessionStore`

18.目前 scan boundary user decision 只支援：
`scan_this_run`
`skip_this_run`
不支援 `always_skip`、`metadata_only`、`masked_summary_only`、`scan_normally`。Decision 必須 match `target_path + fingerprint`，檔案內容或 metadata 改變時舊 decision 不套用。

19.目前 scan boundary decision 不會保存成歷史偏好，不會寫回被掃描 repo，不會 retroactively 修改既有 artifact，也不會被下一次 scan 記住。這個邊界很重要，後續不要把它改成第二套 scanner pipeline 或長期 suppression system。

20.目前 canonical JSON contract 是：
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/core/models/system_map.py`
`/Users/linjunting/Local_AI_Health_Doctor/schemas/ai-system-map.v1.schema.json`
正式 source of truth 是 `ai_system_map.json`，也就是 `RagSystemMap`。前端 projection、viewer payload、trace result、mapping proposal 都不能取代 canonical truth。

21.目前 `RagSystemMap` 的重要欄位包含：
`schema_version`
`system_type`
`classification`
`project`
`reference_architecture`
`scan_depth`
`scan_summary`
`components_by_slot`
`evidence`
`endpoints`
`flows`
`extensions`
`unmapped_components`
`detail_scans`
`risk_hints`
`recommended_next_checks`
`query_trace_events`

22.目前 canonical schema version 固定是：
`ai-system-map/v1`
目前 reference template 固定是：
`rag-core-v1`
目前 template 檔案在：
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/core/templates/rag-core-v1.json`

23.目前 `rag-core-v1` 的 baseline RAG slots 包含：
`data_sources`
`document_loader`
`chunking`
`embedding_model`
`vector_store`
`app_api_or_orchestrator`
`query_processing`
`retriever`
`prompt_builder`
`llm`
`citation_or_response_composer`
`guardrails`
`observability`

24.目前 `rag-core-v1` 的 baseline flows 是：
`indexing`
`query_answer`
注意 template 裡的 flow id 是 `indexing` / `query_answer`，但 canonical map 裡 `Flow.id` 會是 `flow:indexing` / `flow:query_answer`。

25.目前 component detection 的核心是：
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/core/services/component_detection_service.py`
它會保守地把 evidence-backed facts 映射到 component slots。沒有 evidence 的東西不能變成 detected component。無法安全分類的東西要留在 `unmapped_components`，讓 manual mapping / proposal flow 後續處理。

26.目前 rule catalog 已經外部化到 TOML：
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/core/rules/dependency_manifest_rules.toml`
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/core/rules/docker_image_rules.toml`
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/core/rules/code_pattern_rules.toml`
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/core/rules/risk_hint_rules.toml`
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/core/rules/recommended_next_check_rules.toml`
Rule id 是 evidence / component / risk 對應的重要 contract，不要隨便改名。

27.目前 provider 的責任是「讀 deterministic input，產生 facts/evidence/issues」，不是做最終真相判斷。Provider 包含：
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/core/providers/config_parse_provider.py`
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/core/providers/docker_compose_provider.py`
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/core/providers/dependency_manifest_provider.py`
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/core/providers/code_pattern_provider.py`
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/core/providers/output_artifact_provider.py`
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/core/providers/endpoint_call_provider.py`
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/core/providers/llm_proposal_provider.py`

28.目前 `ConfigParseProvider` 會讀 `.env`、JSON、TOML、YAML 類設定，並使用 `SecretMaskingService` 遮罩敏感值。壞 config 應該產生 parse issue，不應該讓整個 scanner crash。

29.目前 `DockerComposeProvider` 會讀 Compose services、image、ports、environment、env_file、volumes、depends_on。它只做 static parse，不啟動 container，也不連線 runtime。

30.目前 `DependencyManifestProvider` 會讀 `requirements.txt`、`requirements.in`、`requirements.pip`、`pyproject.toml`、`package.json`，用 dependency rule catalog 找 RAG 相關 dependency signal。

31.目前 `CodePatternProvider` 會掃 source file 並套用 deterministic regex rule catalog，產生 bounded masked snippet、line range、evidence id。它不是 AST/Semgrep 全功能引擎，也不是讓 AI 直接讀整個 repo。

32.目前 `EndpointDetectionService` 只從 static facts 推導 endpoint，例如 Docker published port、internal service URL、OpenAI base URL、Chroma HTTP client。它不做 runtime probing。

33.目前 `QueryTraceService` 才會真的呼叫 endpoint，而且必須由使用者明確 opt-in 走 `/api/trace` 或 CLI `kai-mind trace`。一般 map scan 不可以偷偷呼叫 target service。

34.目前 `RiskHintService` 會根據 endpoints、parse issues、secret-like config、missing required slots、Chroma HTTP/local persistence 等 evidence 產生 risk hints。Risk hint 是 release-readiness 提醒，不是完整資安掃描報告。

35.目前 `FlowDerivationService` 只在 flow 兩端 slot 都 detected 時才產生 edge。不要為了畫面完整而在 canonical map 裡硬塞沒有 evidence 的 edge。

36.目前 `SystemMapNormalizeService` 會把 raw scan、template、components、endpoints、flows、risk hints 組成 `RagSystemMap`，並補 `scan_summary`、`recommended_next_checks`、排序與空陣列。缺欄位代表產出端壞掉，不應該讓 validator 偷偷補。

37.目前 `SystemMapValidationService` 是 canonical contract 的 runtime 防線。它會拒絕：
`confidence` 欄位
未遮罩 secret-like value
不安全 evidence path
duplicate ids
壞掉的 component / endpoint / flow / risk / detail scan / query trace cross-reference

38.目前 path safety 的核心是：
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/core/services/path_safety_service.py`
對外輸出的 path 應該是 project-relative POSIX path，不應包含 Windows drive、UNC root、absolute path、backslash、parent traversal 或本機絕對路徑。

39.目前 secret masking 的核心是：
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/core/services/secret_masking_service.py`
不要在 provider、route、report、test snapshot、proposal 裡各自重做一套 masking rule。要共用這條 shared masking path。

40.目前 human-readable Markdown report 由：
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/core/services/markdown_summary_service.py`
產生，輸出檔是 `ai_system_map.md`。它是 canonical map 的人類可讀投影，不是另一份 source of truth。

41.目前 frontend viewer projection 由：
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/core/services/viewer_session_service.py`
產生。`graph_view_model` 是前端渲染用 projection，不是 canonical truth。後端不輸出 node x/y/position，layout 由 frontend 處理。

42.目前 viewer payload 的 model 在：
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/core/models/viewer.py`
`ViewerLoadResult.loaded` / `error_reason` 位於 `viewer_load_result` 層，不在 `GraphViewModel` 裡。

43.目前 local web API factory 是：
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/web/app.py`
它會組裝 `ManualMappingService`、`MappingProposalService`、`ScanBoundaryReviewService`、`MapBuildService`、`DetailScanService`、`QueryTraceService`、`ViewerSessionService`、`InMemorySessionStore`，並掛上各 route。

44.目前 web request/response schema 集中在：
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/web/schemas.py`
所有寫入類 schema 預設 `extra="forbid"`，用來避免 API contract 悄悄漂移。

45.目前 web routes 分散在：
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/web/routes/project_routes.py`
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/web/routes/scan_routes.py`
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/web/routes/map_routes.py`
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/web/routes/viewer_routes.py`
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/web/routes/detail_scan_routes.py`
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/web/routes/mapping_routes.py`
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/web/routes/mapping_proposal_routes.py`
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/web/routes/trace_routes.py`

46.目前 local API 有兩種流程，不能混淆：
第一種是 Project session：`POST /api/projects/import` -> `POST /api/scans` -> 後續 `detail-scans` / `mapping-proposals` / `mappings` / `trace`
第二種是 Viewer demo：`POST /api/map/build` -> `GET /api/map`
`POST /api/map/build` 不建立 `project_id`，不能接 project-scoped API。

47.目前 session store 是：
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/web/session_store.py`
它是 `InMemorySessionStore`，只保存單一 backend process 裡的 project、latest build result、latest viewer payload。後端重啟後 `project_id` 和 scan state 會消失。

48.目前 persistent session / scan history 尚未完成，相關 plan 是：
`/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/schedule/plan/unfinish/26-implement-persistent-session-store-and-scan-history.md`
目前 database-backed storage 也尚未完成，相關 plan 是：
`/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/schedule/plan/unfinish/27-introduce-database-backed-storage-layer.md`
所以不要在目前文件或 API 說明中宣稱 PostgreSQL、scan history、restart reload、persistent manual mapping default 已經落地。

49.目前 storage package 只有 repository protocol / in-memory implementation re-export：
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/storage/repositories.py`
目前沒有 SQLAlchemy、Alembic、psycopg、pgvector、migrations 或 DB-backed repository。

50.目前 manual mapping 的核心檔案是：
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/core/models/mapping.py`
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/core/services/manual_mapping_service.py`
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/web/routes/mapping_routes.py`
它是 project-level 的 mapping decision，和 Task 24 scan boundary decision 是不同 domain，不要共用 model。

51.目前 manual mapping 的作用是：使用者確認某個 `unmapped_component` 應該套到既有 `rag-core-v1` slot，或變成 extension component。它會在後續 map build 的 component detection 後套用 overlay，但必須仍然有 live evidence，不能把不存在的 evidence 硬塞進 map。

52.目前 AI mapping proposal 的核心檔案是：
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/core/services/mapping_evidence_packet_builder.py`
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/core/services/mapping_proposal_service.py`
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/core/providers/llm_proposal_provider.py`
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/web/routes/mapping_proposal_routes.py`

53.目前 mapping proposal 是 pending-only 建議，不是 source of truth。它只能使用 masked / bounded `MappingEvidencePacket`，候選結果必須引用 packet 內既有 evidence ids，使用者 accept/edit 後才會建立 manual mapping。未確認的 proposal 不可以直接修改 `ai_system_map.json`。

54.目前 optional LLM provider 是 NVIDIA NIM，但必須用 env 明確開啟：
`KAI_MIND_ENABLE_NVIDIA_NIM_PROPOSALS`
`NVIDIA_API_KEY`
LLM provider 只是 proposal candidate generator，失敗時會 fallback deterministic candidates。不要讓 LLM 直接掃 repo、直接寫 canonical map 或輸出未驗證 schema。

55.目前 detail scan 的核心檔案是：
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/core/services/detail_scan_service.py`
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/core/services/component_detail_scan_service.py`
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/core/services/code_path_scan_service.py`
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/web/routes/detail_scan_routes.py`

56.目前 detail scan 分成 L2 component scan 和 L3 code_path scan。它是 target-scoped、bounded、best-effort static extraction。它只掃 target 相關 project-owned Python files，不執行 target project，不追完整 framework/runtime call graph。

57.目前 query trace 的核心檔案是：
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/core/models/trace.py`
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/core/services/query_trace_service.py`
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/core/providers/endpoint_call_provider.py`
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/web/routes/trace_routes.py`
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/cli/trace_command.py`

58.目前 query trace 是 explicit opt-in black-box endpoint probe。它會對 validated map 裡的 endpoint 送一次 bounded request，回傳 `TraceRunResult`，並遮罩 input/output。它不是 L1 scanner 預設流程，也不應該在 map build 時偷偷呼叫服務。

59.目前 CLI entrypoint 是：
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/cli/main.py`
目前 CLI commands 包含：
`kai-mind map`
`kai-mind validate-map`
`kai-mind trace`
CLI 必須維持 thin adapter，和 Web API 共用 core services。

60.目前 local API safety hardening 在：
`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/web/middleware.py`
目前有 request body size limit、safe unhandled exception middleware、CORS allowlist。Local API 預設應該只綁 `127.0.0.1`，不要開成任意 origin 或 public network API。

61.目前 API 文件記錄的基本 local-only 規則是：Base URL 預設 `http://127.0.0.1:8000`，Auth 無，CORS allowlist 是 `http://127.0.0.1:5173` 和 `http://localhost:5173`，request body 預設 1 MB，錯誤 response 不應包含 raw secret、Python exception string 或本機絕對路徑。

62.目前測試分層如下：
`/Users/linjunting/Local_AI_Health_Doctor/tests/unit`
`/Users/linjunting/Local_AI_Health_Doctor/tests/integration`
`/Users/linjunting/Local_AI_Health_Doctor/tests/web`
`/Users/linjunting/Local_AI_Health_Doctor/tests/cli`
`/Users/linjunting/Local_AI_Health_Doctor/tests/contracts`
`/Users/linjunting/Local_AI_Health_Doctor/tests/fixtures`

63.目前 scanner fixture 專案放在：
`/Users/linjunting/Local_AI_Health_Doctor/tests/fixtures/rag_projects`
目前 canonical schema fixture 放在：
`/Users/linjunting/Local_AI_Health_Doctor/tests/fixtures/ai_system_map`
不要把 provider fixture、contract fixture、frontend sample 混在一起。

64.如果改 `RagSystemMap`、schema、path policy、secret validation、viewer payload，至少要檢查：
`/Users/linjunting/Local_AI_Health_Doctor/tests/contracts/test_ai_system_map_schema.py`
`/Users/linjunting/Local_AI_Health_Doctor/tests/unit/core/test_system_map_validation.py`
`/Users/linjunting/Local_AI_Health_Doctor/tests/unit/core/test_system_map_normalize_service.py`
`/Users/linjunting/Local_AI_Health_Doctor/tests/unit/core/test_viewer_session_service.py`

65.如果改 scan boundary / `POST /api/scans`，至少要檢查：
`/Users/linjunting/Local_AI_Health_Doctor/tests/unit/core/test_scan_boundary_review_service.py`
`/Users/linjunting/Local_AI_Health_Doctor/tests/web/test_scan_boundary_routes.py`
`/Users/linjunting/Local_AI_Health_Doctor/tests/web/test_project_scan_routes.py`
`/Users/linjunting/Local_AI_Health_Doctor/scripts/trace_scan_boundary_policy_overlay.sh`
`/Users/linjunting/Local_AI_Health_Doctor/scripts/trace_scan_boundary_multi_decision_gate.sh`

66.如果改 map build pipeline，至少要檢查：
`/Users/linjunting/Local_AI_Health_Doctor/tests/integration/test_map_build_service.py`
`/Users/linjunting/Local_AI_Health_Doctor/tests/web/test_map_routes.py`
`/Users/linjunting/Local_AI_Health_Doctor/tests/cli/test_map_command.py`
`/Users/linjunting/Local_AI_Health_Doctor/scripts/trace_map_build.sh`
`/Users/linjunting/Local_AI_Health_Doctor/scripts/trace_map_get.sh`
`/Users/linjunting/Local_AI_Health_Doctor/scripts/trace_map_report.sh`

67.如果改 manual mapping / mapping proposal，至少要檢查：
`/Users/linjunting/Local_AI_Health_Doctor/tests/unit/core/test_manual_mapping_service.py`
`/Users/linjunting/Local_AI_Health_Doctor/tests/unit/core/test_mapping_evidence_packet_builder.py`
`/Users/linjunting/Local_AI_Health_Doctor/tests/unit/core/test_mapping_proposal_service.py`
`/Users/linjunting/Local_AI_Health_Doctor/tests/web/test_mapping_routes.py`
`/Users/linjunting/Local_AI_Health_Doctor/tests/web/test_mapping_proposal_routes.py`

68.如果改 detail scan / query trace，至少要檢查：
`/Users/linjunting/Local_AI_Health_Doctor/tests/unit/core/test_detail_scan_service.py`
`/Users/linjunting/Local_AI_Health_Doctor/tests/unit/core/test_query_trace_service.py`
`/Users/linjunting/Local_AI_Health_Doctor/tests/unit/core/test_query_trace_boundaries.py`
`/Users/linjunting/Local_AI_Health_Doctor/tests/web/test_detail_scan_routes.py`
`/Users/linjunting/Local_AI_Health_Doctor/tests/web/test_trace_routes.py`
`/Users/linjunting/Local_AI_Health_Doctor/tests/cli/test_trace_command.py`

69.目前推薦的基本驗證指令是：
`.venv/bin/pytest`
`.venv/bin/ruff check src tests`
`.venv/bin/ruff format src tests`
`.venv/bin/mypy src tests`
如果只是文件修改，可以不用跑全部測試，但如果文件改到 API contract、schema 或行為描述，最好至少跑對應 shell trace 或相關測試。

70.目前要改 API contract 時，必須同時檢查三個地方：
實作：`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/web`
文件：`/Users/linjunting/Local_AI_Health_Doctor/docs/API-GUIDE.md`
可執行 trace：`/Users/linjunting/Local_AI_Health_Doctor/scripts/trace_*.sh`
不要只改其中一個。

71.目前要改 canonical map contract 時，必須同時檢查四個地方：
model：`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/core/models/system_map.py`
schema：`/Users/linjunting/Local_AI_Health_Doctor/schemas/ai-system-map.v1.schema.json`
validator：`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/core/services/system_map_validation_service.py`
fixtures/tests：`/Users/linjunting/Local_AI_Health_Doctor/tests/fixtures/ai_system_map` 和 `tests/contracts`

72.目前最容易出錯的邊界是：
不要把 `graph_view_model` 寫進 `ai_system_map.json`
不要讓 route handler 直接做 provider/detection/normalize
不要讓 LLM output 直接變 canonical truth
不要讓 query trace 變成預設 scanner 行為
不要把 scan boundary decision 和 manual mapping decision 混成同一個 model
不要在 response / report / logs / snapshots 印出 full secret 或本機絕對路徑
不要宣稱 persistent DB / scan history 已完成

73.目前 frontend 對接時要記得：`ai_system_map.json` 是事實來源，`viewer_load_result.graph_view_model` 是渲染投影，`detail_scan` / `trace` / `mapping_proposal` / `scan_boundary` 是互動 surface。前端不應自己推論 component 是否存在，也不應把 graph projection 當作 canonical truth 回寫。

74.過程中你可以使用 "context7" MCP（如果要查詢的資料適合用 context7 查詢的話）來查找最新 framework / library / SDK / CLI 文件；如果是專案實作、API contract、架構狀態，必須優先讀本 repo 的實際 code、tests、scripts、docs，再決定要不要查外部資料。

75.目前前端專案的主要來源在：
`/Users/linjunting/Local_AI_Health_Doctor/frontend`
Bo-han 的前端設計、plan、todo、report 在：
`/Users/linjunting/Local_AI_Health_Doctor/docs/work/Bo-han`
讀前端狀態時要同時看實作與 Bo-han 文件，不能只看其中一邊。Bo-han 文件記錄了 viewer 的 UX 邊界與 phase 進度，frontend code 則代表目前真正能跑的狀態。

76.目前前端 package 定義在：
`/Users/linjunting/Local_AI_Health_Doctor/frontend/package.json`
目前是 React + Vite + TypeScript + pnpm，主要 dependency 是 `react`、`react-dom`、`reactflow`、`elkjs`、`zustand`、`@tanstack/react-query`、`zod`、`lucide-react`。目前 scripts 是：
`pnpm run dev`
`pnpm run build`
`pnpm run lint`
目前沒有正式 frontend test runner script，所以若要做前端 issue，通常需要先補 Vitest / React Testing Library 或 Playwright 類型的 regression test setup。

77.目前前端 source code 大致分成：
`/Users/linjunting/Local_AI_Health_Doctor/frontend/src/components`
`/Users/linjunting/Local_AI_Health_Doctor/frontend/src/hooks`
`/Users/linjunting/Local_AI_Health_Doctor/frontend/src/services`
`/Users/linjunting/Local_AI_Health_Doctor/frontend/src/store`
`/Users/linjunting/Local_AI_Health_Doctor/frontend/src/utils`
`/Users/linjunting/Local_AI_Health_Doctor/frontend/src/data`
`/Users/linjunting/Local_AI_Health_Doctor/frontend/src/types.ts`
`frontend/dist` 是 build output，`frontend/node_modules` 是 dependency，不是架構判斷的 source of truth。

78.目前前端 entrypoint 是：
`/Users/linjunting/Local_AI_Health_Doctor/frontend/src/main.tsx`
主要 application shell 是：
`/Users/linjunting/Local_AI_Health_Doctor/frontend/src/App.tsx`
`App.tsx` 負責把 data source、viewer payload、graph、sidebar、detail panel、progress strip、replay timeline、chat drawer 串在一起。真正 API 呼叫在 `services/viewerApi.ts`，UI state 在 `store/viewerStore.ts`，graph 轉換與 layout helper 在 `utils/graph.ts`。

79.目前 Bo-han 前端設計文件是：
`/Users/linjunting/Local_AI_Health_Doctor/docs/work/Bo-han/design/epic1-frontend-viewer-design.md`
它的核心原則是：前端把後端產生的 `viewer_load_result.graph_view_model` 渲染成可理解、可互動、可追溯的 RAG System Map。前端只做呈現與互動，不重新掃描 repo、不自行推論 JSON 裡不存在的 component、不顯示未遮罩 secret。

80.目前 Bo-han 總覽文件是：
`/Users/linjunting/Local_AI_Health_Doctor/docs/work/Bo-han/bo-han.md`
它把 Bo-han 的責任定義為 Viewer、graph UX、detail panel、filters、query trace replay。Bo-han 不負責 filesystem scanner、config parser、Docker compose parser、dependency parser、scanner evidence，也不負責產生 `ai_system_map.json` 的 source facts。

81.目前 Bo-han 已完成的前端 plan 在：
`/Users/linjunting/Local_AI_Health_Doctor/docs/work/Bo-han/schedule/plan/finish/01-setup-viewer-frontend-foundation.md`
`/Users/linjunting/Local_AI_Health_Doctor/docs/work/Bo-han/schedule/plan/finish/02-implement-system-map-graph-viewer.md`
`/Users/linjunting/Local_AI_Health_Doctor/docs/work/Bo-han/schedule/plan/finish/03-wire-viewer-api-source-and-progress.md`
`/Users/linjunting/Local_AI_Health_Doctor/docs/work/Bo-han/schedule/plan/finish/04-refine-graph-interaction-and-detail-modal.md`
這代表前端 viewer shell、graph rendering、Sample/API 模式、SSE progress 預留、detail modal、follow focus、edge readability 已有第一版。

82.目前 Bo-han 尚未完成的前端 plan 在：
`/Users/linjunting/Local_AI_Health_Doctor/docs/work/Bo-han/schedule/plan/unfinish/05-integrate-backend-viewer-session-api.md`
`/Users/linjunting/Local_AI_Health_Doctor/docs/work/Bo-han/schedule/plan/unfinish/06-implement-query-trace-and-local-chat-ui.md`
`/Users/linjunting/Local_AI_Health_Doctor/docs/work/Bo-han/schedule/plan/unfinish/07-add-viewer-regression-tests.md`
`/Users/linjunting/Local_AI_Health_Doctor/docs/work/Bo-han/schedule/plan/unfinish/08-hardening-responsive-accessibility-performance.md`
這些要看成後續 frontend issue 候選，不要跟後端已完成的 Task 24 混在一起。

83.目前 Bo-han 最新前端 TODO 是：
`/Users/linjunting/Local_AI_Health_Doctor/docs/work/Bo-han/schedule/todo/2026-06-02-phase3-backend-integration-and-tests-TODO.md`
它的核心是：等 Timmy 完成 viewer local API 後，前端從 sample-first checkpoint 推進到正式 API integration，補 invalid map error state 與 regression tests。這份 TODO 仍沒有全部落地，因為目前 frontend package 還沒有 test runner。

84.目前前端的資料來源模式有兩種：
Sample mode：讀 committed sample payload。
API mode：呼叫 local Python backend。
相關程式碼在：
`/Users/linjunting/Local_AI_Health_Doctor/frontend/src/hooks/useViewerPayload.ts`
`/Users/linjunting/Local_AI_Health_Doctor/frontend/src/services/viewerApi.ts`
Sample mode 透過 `loadSampleViewerPayload()` 使用 `frontend/src/data/sampleMap.ts`。API mode 目前透過 `loadApiViewerPayload(baseUrl)` 嘗試 `GET /api/map`，失敗再嘗試暫時 fallback `GET /map`。

85.目前前端 API contract 文件是：
`/Users/linjunting/Local_AI_Health_Doctor/frontend/API_CONTRACT.md`
它記錄的是 viewer-facing contract：`GET /api/map`、temporary fallback `GET /map`、`GET /api/scan/events` SSE、`viewer_load_result.graph_view_model`、query replay sample、future detail scan request shape。它尚未完整記錄 project import、`POST /api/scans`、scan boundary decision、mapping proposal、detail scan mutation 的正式前端 flow。

86.目前前端 Zod contract 在：
`/Users/linjunting/Local_AI_Health_Doctor/frontend/src/types.ts`
它定義 `viewerPayloadSchema`、`graphViewModelSchema`、`scanProgressEventSchema`、`traceEventSchema`。目前對 `ai_system_map` 採較寬鬆 `record/passthrough`，可以容忍後端多欄位，但也代表前端尚未 typed access `detail_scans[]`、mapping proposal lifecycle、project/scan lifecycle。

87.目前 `viewerPayloadSchema` 期待的主結構是：
`viewer_load_result.loaded`
`viewer_load_result.error_reason`
`viewer_load_result.map_json`
`viewer_load_result.ai_system_map`
`viewer_load_result.graph_view_model`
`trace_result_samples`
`detail_scan_result_sample`
`mapping_proposal_result_sample`
`invalid_map_error_sample`
其中 `detail_scan_result_sample` 與 `mapping_proposal_result_sample` 目前仍是 sample / placeholder 用途，不代表真實 API mutation 已完成。

88.目前前端 graph contract 是：
`graph_view_model.nodes`
`graph_view_model.edges`
`graph_view_model.details.evidence_by_id`
`graph_view_model.details.risk_hints_by_id`
`graph_view_model.filters.available`
前端只用這些資料畫圖與顯示 detail。前端不應從 `ai_system_map` 自己重新推 component，也不應自己根據 dependency 或檔案內容建立 node / edge。

89.目前前端 graph render 核心是：
`/Users/linjunting/Local_AI_Health_Doctor/frontend/src/components/SystemGraph.tsx`
`/Users/linjunting/Local_AI_Health_Doctor/frontend/src/components/SystemNode.tsx`
`/Users/linjunting/Local_AI_Health_Doctor/frontend/src/utils/graph.ts`
`SystemGraph` 使用 React Flow 畫 canvas、pan、zoom、minimap、自訂 edge。`utils/graph.ts` 會把 `graph_view_model` 轉成 React Flow nodes/edges，使用 ELK 做 deterministic layered layout，並處理 filter highlight、trace focus、progress target、edge lane offsets。

90.目前 layout 責任在前端，不在後端。後端 `ViewerSessionService` 產生 graph nodes/edges/details/filter，但不輸出 x/y position。前端使用 ELK 計算位置，並且在 replay/progress 時避免每一步重新 layout，降低畫面閃動。

91.目前 node 視覺狀態由：
`/Users/linjunting/Local_AI_Health_Doctor/frontend/src/components/SystemNode.tsx`
處理。Risk hint 會優先顯示 risk 狀態，`needs_confirmation`、`not_configured`、`missing`、`confirmed`、`detected` 會用不同樣式。這是視覺標示，不是前端重新判斷 canonical truth。

92.目前 Sidebar 是：
`/Users/linjunting/Local_AI_Health_Doctor/frontend/src/components/Sidebar.tsx`
它顯示 scan summary、detected/missing/risk/unmapped counts、filter highlight、L1/L2/L3 scan depth indicator、legend。Filter 的語意是 highlight，不是隱藏 graph。這點很重要，因為 release-readiness viewer 需要保留完整脈絡，不應因 filter 讓風險或 missing slots 從畫面消失。

93.目前 DetailPanel 是：
`/Users/linjunting/Local_AI_Health_Doctor/frontend/src/components/DetailPanel.tsx`
它支援 `Overview`、`L2 Component`、`L3 Code Path` 三個 tab。Overview 會顯示 selected node/edge 的 id、status/type/slot 或 relationship/flow/from/to，以及 evidence / risk hints。L2/L3 目前只會讀 sample `detail_scan_result_sample`，還沒有接真實 `POST /api/detail-scans`。

94.目前 ReplayTimeline 是：
`/Users/linjunting/Local_AI_Health_Doctor/frontend/src/components/ReplayTimeline.tsx`
它從 `ai_system_map.query_trace_events` 讀 trace events，用 `sequence_index` 排序後做 replay UI。它支援 previous / play-pause / next，並把目前 step 轉成 graph highlight。這是 replay UI，不代表 query trace request API 已經從前端完成接線。

95.目前 ProgressStrip 與 SSE 相關檔案是：
`/Users/linjunting/Local_AI_Health_Doctor/frontend/src/components/ProgressStrip.tsx`
`/Users/linjunting/Local_AI_Health_Doctor/frontend/src/hooks/useScanProgress.ts`
`/Users/linjunting/Local_AI_Health_Doctor/frontend/src/services/viewerApi.ts`
API mode 且 progress running 時會開 `EventSource` 連到 `/api/scan/events`。若 SSE 失敗，前端會顯示 warning 並使用 mock progress。這個 mock progress 只是 UI fallback，不代表後端真的正在掃描。

96.目前 StateOverlay 是：
`/Users/linjunting/Local_AI_Health_Doctor/frontend/src/components/StateOverlay.tsx`
它處理 loading、error、pending 等非 loaded 狀態。重要邏輯是：API mode 失敗時不會偷偷顯示 sample data，使用者必須明確點 `Use sample data` 才會切回 sample。這可以避免 demo 時誤把 sample 看成實際掃描結果。

97.目前 ChatPanel 是：
`/Users/linjunting/Local_AI_Health_Doctor/frontend/src/components/ChatPanel.tsx`
它只是 local model chat placeholder。輸入框 disabled，沒有接 API。不要把它寫成已完成的 local model chat，也不要讓它繞過 backend masking 或直接讀 project context。

98.目前 DataSourceControl 是：
`/Users/linjunting/Local_AI_Health_Doctor/frontend/src/components/DataSourceControl.tsx`
它提供 Sample/API 切換、API base URL 輸入、reload。預設 API base URL 來自 `VITE_API_BASE_URL` 或 `http://127.0.0.1:8000`。這只是 viewer payload loader，不是完整 project import / scan workflow。

99.目前 viewer UI state 在：
`/Users/linjunting/Local_AI_Health_Doctor/frontend/src/store/viewerStore.ts`
它管理 `dataSourceMode`、`apiBaseUrl`、selected node/edge、filters、active trace step、replay running、progress running、follow focus、live progress event、detail mode。它目前沒有 `project_id`、`scan_id`、boundary proposals、boundary decisions、mapping proposal lifecycle、detail scan mutation state。

100.目前前端已完成的工作比較接近「viewer shell + graph interaction」，不是完整「project scan application」。換句話說，目前使用者可以看 sample 或既有 `/api/map` viewer payload，但還不能只靠前端 UI 完成：
輸入 project path
-> import project
-> create scan
-> 處理 `requires_boundary_decision`
-> scan completed 後 refresh graph
這個完整閉環。

101.目前正式 project-scoped scan flow 的前端未完成 issue 是：
`/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/schedule/plan/unfinish/24b-implement-project-scan-and-boundary-decision-frontend-flow.md`
這個 issue 要把前端 API mode 從「讀 `/api/map`」推進到：
`POST /api/projects/import`
-> `POST /api/scans`
-> `completed` 或 `requires_boundary_decision`
-> decision 後再次 `POST /api/scans`
-> `GET /api/map`
它不是 Project Mapping Profile Page，也不是 upload ingestion。

102.目前 scan boundary 前端 UI 尚未完成。後端 `POST /api/scans` 已可能回 `requires_boundary_decision`、`boundary_proposals`、`available_boundary_actions=["scan_this_run","skip_this_run"]`，但前端目前沒有 boundary decision modal/drawer、沒有 proposal state、沒有 decision submit flow。實作時要清楚寫 UI 文案：decision 只影響本次 scan，不是永久偏好。

103.目前 AI mapping proposal 的前端未完成 issue 是：
`/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/schedule/plan/unfinish/20a-implement-ai-mapping-proposal-frontend-flow.md`
後端 Task 20 已有 `/api/mapping-proposals` lifecycle，但前端目前沒有 `listMappingProposals()`、`createMappingProposal()`、`decideMappingProposal()`，也沒有 proposal query/mutation state。`DetailPanel` 裡的 proposal buttons 目前是 sample placeholder，沒有接真實 API。

104.目前 progressive detail scan 的前端未完成 issue 是：
`/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/schedule/plan/unfinish/21a-implement-detail-scan-frontend-flow.md`
後端 Task 21 已有 `POST /api/detail-scans` / `GET /api/detail-scans/{detail_scan_id}`，但前端目前沒有 `createDetailScan()`、`getDetailScan()`，也沒有 L2/L3 真實 running/error/completed state。`DetailPanel` 的 L2/L3 tab 目前還是 sample-only。

105.目前 Project Mapping Profile Page 的前端未完成 issue 是：
`/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/schedule/plan/unfinish/24a-implement-project-mapping-profile-page.md`
這個頁面是 project-level mapping/profile 管理資訊架構，應該在 `24b` scan flow、`20a` proposal flow、`21a` detail scan flow 更穩定後再做。它不應該搶在基本 project scan / decision / detail / proposal 之前。

106.目前 OpenAPI generated frontend SDK 的後續 issue 是：
`/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/schedule/plan/unfinish/28-introduce-openapi-generated-frontend-sdk.md`
目前前端仍手寫 `fetch`、endpoint path、Zod schema。Task 28 的目標是等 local API route shape 穩定後，從 FastAPI 匯出 versioned OpenAPI schema，再產生 TypeScript types/client，降低前後端 contract drift。這是 contract hardening issue，不是 scanner canonical truth。

107.目前 project archive upload ingestion 的後續 issue 是：
`/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/schedule/plan/unfinish/25-implement-project-upload-ingestion.md`
它跟目前 `source_type="local_path"` 的 project import 不同。若做 upload，會碰到 zip-slip、archive size limit、extraction sandbox、secret/path masking、cleanup 等安全問題。不要把 upload 和目前 local-path scan flow 混成同一個前端 issue。

108.目前 persistent session / scan history / database-backed storage 仍是後續獨立 issue 候選：
`/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/schedule/plan/unfinish/26-implement-persistent-session-store-and-scan-history.md`
`/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/schedule/plan/unfinish/27-introduce-database-backed-storage-layer.md`
這兩個不應在 `check1.md` 裡被寫成已完成，也不應直接歸到既有 Epic 2。比較安全的說法是：目前保留在 `unfinish`，作為後續 storage/session issue 或 post-Epic1 品質/產品化議題，是否進入哪個 Epic 要看 roadmap 另行定義。

109.目前前端測試缺口很明確：`frontend/package.json` 沒有 `test` script，Bo-han Task 7 與 Timmy 20a / 21a / 24b 都要求補 frontend regression tests。若開始做任一前端互動 issue，建議先用 TDD/BDD 補測試框架與最小測試，例如：
graph render smoke
detail modal open/close
filter highlight 不隱藏 graph
API error 不 crash
boundary decision response schema
proposal decision mutation
detail scan L2/L3 state
再寫 UI/API helper。

110.目前前端 build/lint 驗證指令是：
`cd /Users/linjunting/Local_AI_Health_Doctor/frontend && pnpm run lint`
`cd /Users/linjunting/Local_AI_Health_Doctor/frontend && pnpm run build`
如果新增 frontend tests，應同步新增 `pnpm test` 或 `pnpm run test`，並把驗證方式寫進 Bo-han 或 Timmy 對應 TODO/Report。

111.目前前後端 contract 邊界要用這句話記住：
Backend owns truth and safety.
Frontend owns rendering and interaction.
也就是後端負責 scanner、provider、masking、validation、canonical `ai_system_map.json`、viewer projection；前端負責 graph layout、highlight、modal、replay controls、API mode state、使用者決策 UI。前端使用者決策要透過 backend API 生效，不可直接改 canonical map 或本機檔案。

112.目前前後端 issue 拆分應優先照「可獨立驗收的 user flow」拆，不要照檔案類型或 Epic 名稱硬拆。比較合理的前端 issue 順序是：
先做 `24b` project import + scan boundary decision flow，讓使用者能從 project path 走完整 scan。
再做 `21a` detail scan frontend flow，讓 L2/L3 tab 從 sample 變成真實 API。
再做 `20a` mapping proposal frontend flow，讓 needs_confirmation 可以產生/決策 proposal。
最後再做 `24a` profile page、Task 28 OpenAPI SDK、Bo-han Task 7/8 測試與 UX hardening。
如果後端 API shape 還會大改，Task 28 不要太早做，避免 generated SDK churn。

113.目前寫 TODO / Report 時要避免這些錯誤：
不要說前端已支援 project import + scan，因為目前還沒有。
不要說前端已支援 scan boundary decision UI，因為目前還沒有。
不要說前端已支援真實 mapping proposal decision，因為目前只有 sample placeholder。
不要說前端已支援真實 L2/L3 detail scan API，因為目前 L2/L3 tab 仍是 sample-only。
不要說 local model chat 已完成，因為目前只是 placeholder。
不要說 OpenAPI generated SDK 已完成，因為目前還是手寫 API helper。
不要把 storage/history/DB 寫成已完成，也不要自動放進既有 Epic 2。

114.目前前端 root render 在：
`/Users/linjunting/Local_AI_Health_Doctor/frontend/src/main.tsx`
它用 `React.StrictMode` 包住 App，外層有：
`ErrorBoundary`
`QueryClientProvider`
所以 data fetching 是 TanStack Query 的全域 query client，render crash 會先進 ErrorBoundary，不應直接變成空白頁。

115.目前 ErrorBoundary 在：
`/Users/linjunting/Local_AI_Health_Doctor/frontend/src/components/ErrorBoundary.tsx`
它會顯示 `Something went wrong`、錯誤訊息與 `Try again`。`componentDidCatch` 會把 render-time crash 印到 console 供 debug。注意這是前端 render crash 防線，不是 API error state；API error 主要由 `StateOverlay` / `DataSourceControl` 顯示。

116.目前 sample payload loader 在：
`/Users/linjunting/Local_AI_Health_Doctor/frontend/src/data/sampleMap.ts`
它會 import：
`/Users/linjunting/Local_AI_Health_Doctor/frontend/src/data/frontend-json-sample.json`
並先用 `viewerPayloadSchema.parse(rawSample)` 驗證 sample。Trace events 會用 `traceEventSchema.safeParse()` 過濾，再依 `sequence_index` 排序。這代表 sample 不是隨便 JSON，而是前端 Zod schema 的 contract fixture。

117.目前 sample JSON 的可視化規模是：
`graph_view_model.nodes = 14`
`graph_view_model.edges = 10`
`graph_view_model.filters.available = 4`
`ai_system_map.query_trace_events = 4`
並且包含 `detail_scan_result_sample`、`mapping_proposal_result_sample`、`invalid_map_error_sample`、`trace_result_samples`。這些 sample 區塊是前端開發與 demo 用，不代表後端 API mutation 都已完成。

118.目前前端 Vite 設定在：
`/Users/linjunting/Local_AI_Health_Doctor/frontend/vite.config.ts`
dev server port 是 `5173`。Build 已經設定 manual chunks：
`react` chunk：`react`、`react-dom`、`@tanstack/react-query`、`zustand`
`graph` chunk：`reactflow`、`elkjs`
`icons` chunk：`lucide-react`
所以若之後看到 build chunk warning，要先確認是否真的超過現有分包策略，不要直接把大型 graph dependency 當成 bug。

119.目前 TypeScript 設定在：
`/Users/linjunting/Local_AI_Health_Doctor/frontend/tsconfig.json`
`/Users/linjunting/Local_AI_Health_Doctor/frontend/tsconfig.node.json`
它使用 `strict: true`、`moduleResolution: "Bundler"`、`resolveJsonModule: true`、`jsx: "react-jsx"`。這代表前端改 types/schema/API helper 時，應以 TypeScript strict 為準，不要用 `any` 躲掉 contract drift。

120.目前 ESLint 設定在：
`/Users/linjunting/Local_AI_Health_Doctor/frontend/eslint.config.js`
它忽略 `dist`，使用 `@eslint/js`、`typescript-eslint`、`react-hooks`、`react-refresh`。如果新增 components/hooks，要維持 hooks rules，不要把 async/data loading 寫成違反 hook order 的條件式呼叫。

121.目前主要樣式與設計 token 在：
`/Users/linjunting/Local_AI_Health_Doctor/frontend/src/styles.css`
它不是隨機 CSS，而是 token-driven viewer design system：`[data-theme="light"]` / `[data-theme="dark"]`、`[data-density="comfortable"]` / `[data-density="compact"]`、sidebar、toolbar、graph canvas、progress strip、state overlay、replay timeline、floating inspector、chat drawer、responsive layout 都在同一份 stylesheet。

122.目前 frontend UX 已有 responsive 與 accessibility 基礎，但還不是完整 hardening。CSS 在 `max-width: 1180px` 會縮 sidebar / inspector / API input，在 `max-width: 880px` 會把 sidebar 改成 off-canvas、graph frame 給固定高度、inspector 改成底部 sheet、toolbar wrap、timeline 改成橫向 cards。Bo-han Task 8 仍要求補鍵盤、可讀性、performance 與 responsive hardening，所以不要把目前狀態寫成已完成產品化 UI。

123.目前 theme state 在：
`/Users/linjunting/Local_AI_Health_Doctor/frontend/src/hooks/useTheme.ts`
前端 HTML 入口在：
`/Users/linjunting/Local_AI_Health_Doctor/frontend/index.html`
`index.html` 預設 `<html data-theme="light" data-density="comfortable">`，並用 pre-paint inline script 讀 `localStorage.viewer-theme`，避免 theme flash。`App.tsx` 會用 toolbar button 切換 light/dark，`useTheme` 會同步到 `<html data-theme>` 並寫回 localStorage。若改 UI，不要把 theme token 寫死在 component inline style；應優先沿用 `styles.css` 裡的 CSS variables。

124.目前前端 helper formatting 在：
`/Users/linjunting/Local_AI_Health_Doctor/frontend/src/utils/format.ts`
`compactId()` 只做 UI 顯示用 id 簡化，`formatValue()` 只把值轉成人可讀字串，`titleCase()` 只做 label 顯示。這些 helper 不應用來改 canonical id，也不應用來判斷 backend truth。

125.目前開發階段檢查清單放在：
`/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/schedule/fable-5/check-list`

# 任務

使用 Linus Torvalds `/Users/linjunting/Local_AI_Health_Doctor/.cursor/rules/linus_torvalds.mdc` 的思考方式，
在專案的前端、後端、AI backend、AI infra、AI application 部分，根據目前系統架構與 `/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/schedule/fable-5/find-error/plan/unfinish/phase1-check.md`，檢查目前系統可能存在的漏洞、資安風險、過去實作上的缺陷，以及過去實作上不容易使用或不吸引使用者的地方。

本次任務只做檢查與紀錄，不直接修改功能程式碼、不直接修補問題。

你必須持續檢查到已覆蓋上述所有指定範圍，並找出目前可觀察到的所有漏洞或是可改善地方後，才能停下；不得只做抽樣檢查、只列幾個代表問題就提前結束。

如果檢查過程中發現需要修補的地方，請把問題、影響範圍、證據、重現方式、風險等級、建議修補方向、建議測試方式記錄下來，整理成 TODO:`/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/schedule/fable-5/find-error/todo` / Report:`/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/schedule/fable-5/find-error/report`，讓後續可以拆成獨立 issue 或下一階段修補任務。

你必須實際閱讀相關 code、docs、tests、scripts 後再下判斷，不可以只根據檔名或推測下結論。遇到不會或不確定的問題，必須使用 "context7" MCP 或直接上網查找相關最佳實踐，嚴禁自行猜測。

如果檢查內容涉及 AI backend、AI infra、AI application、RAG、Agent、LLM security、model serving、local inference、tool calling、retrieval quality、evals、observability、prompt injection 或資料外洩風險，你必須額外參考最新 AI 論文、最新 AI engineering / security 研究、以及最新 AI 相關開源專案 source / docs / issues / PR / release notes。引用外部資訊時，要記錄來源與查詢日期，並清楚區分「repo 實際觀察」與「外部最佳實踐建議」。

# 測試相關注意事項

如果需要驗證問題是否真的存在，你可以執行現有測試、lint、build、trace script，或撰寫臨時驗證腳本 / 測試案例。

但是要記得：

0. 可以使用 shell 腳本或測試程式輔助驗證問題
1. 本次任務只做檢查與紀錄，不直接修補功能程式碼
2. 如果錯誤跟本次檢查範圍相關，請記錄錯誤原因、影響範圍、重現方式、建議修補方式與建議測試方式
3. 如果錯誤不是本次檢查範圍造成的，也必須記錄下來並清楚標示為「非本次檢查主要問題」
4. 若新增臨時測試或驗證腳本，只用來輔助確認問題，不代表本次要完成正式修補
5. 遇到不會或不確定的問題，你必須使用 "context7" MCP 或直接上網查找相關軟體工程 / security / UX / AI engineering 最佳實踐資料

# 約束

1. 你必須先檢查實際 code / docs / tests / scripts，再判斷問題是否存在
2. 本次任務只做檢查與紀錄，不直接修改功能程式碼
3. 如果發現需要修補的問題，只能記錄問題與建議修補方向，不要直接修補
4. 你必須依照 `/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/schedule/fable-5/find-error/plan/unfinish/phase1-check.md` 的安全邊界與架構原則進行檢查
5. 全部做完後，你必須逐一整理本次發現的漏洞、資安風險、實作缺陷、UX / usability 問題、AI backend 問題、AI infra 問題、AI application 問題
6. 每個問題都必須包含：問題描述、影響範圍、證據、重現方式、風險等級、建議修補方向、建議測試方式
7. 沒有找到問題的區塊，也要明確記錄「已檢查，未發現明顯問題」
8. 涉及 AI backend / AI infra / AI application 的判斷，必須參考最新 AI 論文與最新 AI 相關開源 source，不可以只靠舊知識或主觀推測
9. 遇到不會的或不確定的問題，你必須使用 "context7" MCP（如果適合）或直接上網查找最新資訊

## 注意事項
請注意，你必須獨立完成此檢查工作。過程中不需要徵求我的同意，可以自行決定要檢查哪些 code path、docs、tests、scripts，也可以自行執行必要的驗證指令。

但是本次任務只做檢查與紀錄，不直接修改功能程式碼、不直接修補問題。
如果發現需要修補的地方，請完整記錄成 TODO / Report，讓後續可以拆成獨立 issue 或下一階段修補任務。
