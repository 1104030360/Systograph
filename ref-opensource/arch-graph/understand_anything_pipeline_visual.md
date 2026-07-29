# Understand-Anything `/understand` 可視化流程圖

> Canonical pipeline（已驗證版）
> 來源：`skills/understand/SKILL.md`、`agents/*.md`、`packages/dashboard/`
> 對照 upstream pin：`73559a1`（plugin 2.8.2，MIT）

本檔是 `/understand` 的**可視化總圖**，其他 `understand_anything_*.md` 都指向這裡。
所有圖已改為 ASCII（不再使用 Mermaid），框內一律英文，中文解說放在圖外。

## 圖例（四張圖共用）

| 標記 | 意義 |
|------|------|
| `[O]` | Orchestrator（主 session，依 `SKILL.md` 編排；不是 subagent） |
| `[A]` | LLM subagent（`agents/*.md`；`/understand` 用到 6 個） |
| `[S]` | 隨 skill 出貨的確定性腳本（`skills/understand/` 內，共 9 支） |
| `[R]` | runtime-authored 腳本（**不在磁碟上**，每次執行才寫進 `tmp/`） |
| `[J]` | JSON artifact |
| `[UI]` | Dashboard（Vite dev server + ReactFlow，無 AI） |
| `[!]` | 阻斷式使用者確認 gate（不確認就不往下走） |
| `┄┄▶` | 條件分支 / 可選路徑 |

---

## 圖 1：主管線總覽（Phase 0 → Dashboard）

```text
/understand [path] [--full] [--review] [--language <code>] [--auto-update]
   │
   ▼
┌─ [O] Orchestrator   main session, executes skills/understand/SKILL.md ─────────┐
│ ten phase sections, but only eight progress strings, all worded "N/7":         │
│ 1/7, 1.5/7, 2/7, 3/7, 4/7, 5/7, 6/7, 7/7   (Phase 0 and 0.5 print none)        │
└────────────────────────────────────────────────────────────────────────────────┘
   │
   ▼
┌─ Phase 0   Pre-flight        [O] only, no agents ──────────────────────────────┐
│ git-worktree redirect -> main repo root      plugin build (pnpm + core)        │
│ git rev-parse HEAD    mkdir intermediate/ tmp/    purge .trash-* > 7 days      │
│ [S] merge-subdomain-graphs.py   *knowledge-graph*.json + existing graph        │
│         => [J] knowledge-graph.json   (may rewrite the graph before Ph 1)      │
│ decide: full | incremental (git diff) | review-only    => [J] config.json      │
│ [!] graph exists + commit unchanged -> ask (a) full (b) review (c) stop        │
└────────────────────────────────────────────────────────────────────────────────┘
   │
   ├┄┄▶ review-only path (--review + graph exists + commit unchanged):
   ┊      copy knowledge-graph.json -> intermediate/assembled-graph.json,
   ┊      then jump straight to Phase 6 step 3, skipping Phase 0.5 .. 5
   ▼
┌─ Phase 0.5 Ignore Configuration   [O] only ────────────────────────────────────┐
│ [S] generate-ignore.mjs  => .understand-anything/.understandignore (plain text)│
│ [!] two blocking user-confirmation gates (newly generated / already existed)   │
└────────────────────────────────────────────────────────────────────────────────┘
   │
   ▼
┌─ Phase 1/7   SCAN        (full analysis only) ─────────────────────────────────┐
│ [A] project-scanner x1  ->  [S] scan-project.mjs, [S] extract-import-map.mjs,  │
│ then LLM narrative from README/manifest   => [J] scan-result.json              │
│ soft gate: > 100 files -> warn and suggest scoping to a subdirectory           │
└────────────────────────────────────────────────────────────────────────────────┘
   │
   ▼
┌─ Phase 1.5/7 BATCH       100% deterministic, no agent ─────────────────────────┐
│ [S] compute-batches.mjs   Louvain communities over the import graph            │
│ => [J] batches.json       exit != 0 is a HARD failure (no retry)               │
└────────────────────────────────────────────────────────────────────────────────┘
   │
   ▼
┌─ Phase 2/7   ANALYZE ──────────────────────────────────────────────────────────┐
│ [A] file-analyzer x N batches, up to 5 concurrent  => [J] batch-<i>.json       │
│ [S] merge-batch-graphs.py (Python)                 => [J] assembled-graph.json │
└────────────────────────────────────────────────────────────────────────────────┘
   │
   ▼
┌─ Phase 3/7   ASSEMBLE REVIEW ──────────────────────────────────────────────────┐
│ [A] assemble-reviewer x1, LLM end to end, runs no script                       │
│ => [J] assemble-review.json  +  edits assembled-graph.json in place            │
└────────────────────────────────────────────────────────────────────────────────┘
   │
   ▼
┌─ Phase 4/7   ARCHITECTURE ─────────────────────────────────────────────────────┐
│ [A] architecture-analyzer x1 + [R] tmp/ua-arch-analyze.js  => [J] layers.json  │
└────────────────────────────────────────────────────────────────────────────────┘
   │
   ▼
┌─ Phase 5/7   TOUR ─────────────────────────────────────────────────────────────┐
│ [A] tour-builder x1 + [R] tmp/ua-tour-analyze.js  => [J] tour.json (5-15 steps)│
└────────────────────────────────────────────────────────────────────────────────┘
   │
   ▼
┌─ Phase 6/7   REVIEW        ◀┄┄ review-only path enters here ───────────────────┐
│ [O] inline assembles { version, project, nodes, edges, layers, tour }          │
│ fork:  default [R] tmp/ua-inline-validate.cjs   |   --review [A] graph-reviewer│
│ both => [J] review.json ; auto-fix + revalidate once                           │
│ critical issues remaining -> still save, but skip dashboard auto-launch        │
└────────────────────────────────────────────────────────────────────────────────┘
   │
   ▼
┌─ Phase 7/7   SAVE          [O] only, step order is load-bearing ───────────────┐
│ 1) write [J] knowledge-graph.json                                              │
│ 2) [S] build-fingerprints.mjs => [J] fingerprints.json                         │
│    gate: exit 0 AND stdout contains "Fingerprints baseline:"                   │
│    otherwise ABORT Phase 7 and do NOT write meta.json                          │
│ 3) write [J] meta.json   4) mv intermediate/ + tmp/ -> .trash-<epoch>/,        │
│    KEEPING intermediate/scan-result.json   5) summary report                   │
│ 6) invoke /understand-dashboard only if final validation passed                │
└────────────────────────────────────────────────────────────────────────────────┘
   │
   ▼
┌─ [UI] Dashboard   /understand-dashboard, conditional, read-only, no AI ────────┐
│ background `GRAPH_DIR=<project> npx vite --host 127.0.0.1` on port 5173        │
│ React 19 + @xyflow/react layout in the browser                                 │
└────────────────────────────────────────────────────────────────────────────────┘
```

**解說**

- 章節共有 **十段**（0、0.5、1、1.5、2、3、4、5、6、7），但對使用者印出的進度字串只有
  八條，而且分母一律是 `/7`——包含字面上的 `[Phase 1.5/7]`。Phase 0 與 0.5 不印進度。
- Phase 0 不只是解析參數：它會做 git-worktree 轉址、確保 plugin 已 build、建立
  `intermediate/`＋`tmp/`、清掉 7 天以上的 `.trash-*`，並且執行
  `merge-subdomain-graphs.py`——這支 Python 腳本會在任何掃描之前就可能**改寫**
  `knowledge-graph.json`。任何忽略 Phase 0 的流程圖都會漏掉這個副作用。
- `--review` ＋ 圖已存在 ＋ commit 未變時走 review-only：把既有 `knowledge-graph.json`
  複製成 `intermediate/assembled-graph.json`，直接跳到 Phase 6 step 3。
- Phase 7 的順序是有意義的：先寫 `knowledge-graph.json` → 跑 `build-fingerprints.mjs`
  → 才寫 `meta.json`。fingerprints 是 `meta.json` 的 gate，順序顛倒會讓後續 auto-update
  每次都升級成 `FULL_UPDATE`。

---

## 圖 2：Phase 展開（Agent · Script · 產物）

```text
┌─ Phase 0   Pre-flight            [O] orchestrator direct, no agents ─────────────────┐
│ 1.  resolve PROJECT_ROOT; git-worktree redirect -> main repo root (issue #133)       │
│ 1.5 ensure plugin built: pnpm install + build @understand-anything/core              │
│ 2-3 git rev-parse HEAD; mkdir .understand-anything/{intermediate,tmp}                │
│ 3.1 purge .trash-* older than 7 days                                                 │
│ 3.5 --auto-update / --language          => [J] config.json                           │
│ 4.  [S] merge-subdomain-graphs.py <PROJECT_ROOT>                                     │
│       auto-discovers *knowledge-graph*.json, merges into the base graph              │
│       output path HARDCODED         => [J] knowledge-graph.json (pre-merge)          │
│ 7.  decide: full | incremental (git diff --name-only) | review-only                  │
│       [!] HARD user gate when graph exists AND commit hash unchanged                 │
│ 8.  collect README / manifest / dir tree / entry point for later phases              │
└──────────────────────────────────────────────────────────────────────────────────────┘
   │
   ▼
┌─ Phase 0.5 Ignore Configuration  [O] orchestrator direct ────────────────────────────┐
│ [S] generate-ignore.mjs <PROJECT_ROOT>   (idempotent, output path HARDCODED)         │
│      => .understand-anything/.understandignore   (plain text, not JSON)              │
│ [!] gate A: file was just generated -> user reviews it, confirms to continue         │
│ [!] gate B: file already existed    -> user reviews it, confirms to continue         │
│ both gates BLOCK the pipeline; Phase 1 starts only after confirmation                │
└──────────────────────────────────────────────────────────────────────────────────────┘
   │
   ▼
┌─ Phase 1/7 SCAN                  [A] project-scanner x1 ─────────────────────────────┐
│ 1. [S] scan-project.mjs <projectRoot> <outputPath>    (paths configurable)           │
│      git ls-files (+ directory-walk fallback), applies .understandignore             │
│      -> files[]{path, language, sizeLines, fileCategory}, totalFiles,                │
│         estimatedComplexity, filteredByIgnore                                        │
│ 2. [S] extract-import-map.mjs <input.json> <output.json>  (tree-sitter)              │
│      per-language resolution: tsconfig paths, go.mod, composer.json,                 │
│      Package.swift ...  -> importMap{path: [resolved]}   no LLM fallback             │
│ 3. LLM ONLY here: project name / description / frameworks from README                │
│    and the package manifest                                                          │
│ => [J] intermediate/scan-result.json      soft gate: > 100 files -> warn             │
└──────────────────────────────────────────────────────────────────────────────────────┘
   │
   ▼
┌─ Phase 1.5/7 BATCH               [O] direct, 100% deterministic, no agent ───────────┐
│ [S] compute-batches.mjs <project-root> [--changed-files=...]                         │
│   Louvain community detection over the import graph (graphology)                     │
│   MAX_COMMUNITY_SIZE 35; count-based fallback batchSize 12; MIN_BATCH_SIZE 3         │
│   neighborMap = 1-hop neighbours, capped at 50 per batch                             │
│   file-count based, no token budget                                                  │
│   reads intermediate/scan-result.json, writes intermediate/batches.json              │
│   (both paths HARDCODED - no --input/--output/--work-dir flags upstream)             │
│   => [J] intermediate/batches.json                                                   │
│   exit != 0  ->  HARD failure: relay full stderr, no retry, pipeline stops           │
└──────────────────────────────────────────────────────────────────────────────────────┘
   │
   ▼
┌─ Phase 2/7 ANALYZE               [A] file-analyzer x N batches, <= 5 concurrent ─────┐
│ per agent:                                                                           │
│   1. [S] extract-structure.mjs <input.json> <output.json>                            │
│        => [J] tmp/ua-file-extract-results-<i>.json   (structural facts)              │
│   2. LLM semantic pass on top of those facts: summary, tags, semantic edges          │
│        NO language/framework prompt files injected here (Phase 4 only)               │
│   => [J] intermediate/batch-<i>.json  or  batch-<i>-part-<k>.json                    │
│      naming is per batchIndex, NO fusion: the merge regex                            │
│      batch-(\d+)(-part-(\d+))?.json silently DROPS any other name                    │
│ then [O] runs [S] merge-batch-graphs.py <project-root>   (Python)                    │
│   normalize node ids + complexity, dedupe, drop dangling edges,                      │
│   tested_by linker (2 passes), recover ~25% of edges from scan-result.json           │
│   => [J] intermediate/assembled-graph.json ; warnings -> $PHASE_WARNINGS             │
│ incremental path: compute-batches.mjs --changed-files + batch-existing.json          │
└──────────────────────────────────────────────────────────────────────────────────────┘
   │
   ▼
┌─ Phase 3/7 ASSEMBLE REVIEW       [A] assemble-reviewer x1 ───────────────────────────┐
│ LLM end to end - this agent runs no script                                           │
│ consumes: assembled-graph.json + batch-*.json + merge stderr + importMap             │
│ => [J] intermediate/assemble-review.json                                             │
│ => edits [J] intermediate/assembled-graph.json IN PLACE                              │
└──────────────────────────────────────────────────────────────────────────────────────┘
   │
   ▼
┌─ Phase 4/7 ARCHITECTURE          [A] architecture-analyzer x1 ───────────────────────┐
│ prompt = base agent template                                                         │
│        + languages/<language-id>.md   (per language detected in Phase 1)             │
│        + frameworks/<framework-id>.md (per framework detected in Phase 1)            │
│        + locales/<code>.md            (only when $OUTPUT_LANGUAGE != en)             │
│        missing file = silent skip. THIS IS THE ONLY PHASE THAT INJECTS THEM.         │
│ agent writes and runs [R] tmp/ua-arch-analyze.js  (authored per run, not             │
│   bundled): tmp/ua-arch-input.json -> tmp/ua-arch-results.json                       │
│ => [J] intermediate/layers.json   then [O] applies 5-step normalization              │
└──────────────────────────────────────────────────────────────────────────────────────┘
   │
   ▼
┌─ Phase 5/7 TOUR                  [A] tour-builder x1 ────────────────────────────────┐
│ input: file-level nodes + layers + all edges + README + $ENTRY_POINT                 │
│ agent writes and runs [R] tmp/ua-tour-analyze.js  (authored per run):                │
│   tmp/ua-tour-input.json -> tmp/ua-tour-results.json                                 │
│ => [J] intermediate/tour.json, 5-15 steps                                            │
│    then [O] applies 5-step normalization (unwrap envelope, rename legacy             │
│    fields, path -> file: prefix, drop dangling nodeIds, sort by order)               │
└──────────────────────────────────────────────────────────────────────────────────────┘
   │
   ▼
┌─ Phase 6/7 REVIEW                [O] assembles, then forks ──────────────────────────┐
│ [O] inline assembles the canonical KnowledgeGraph object:                            │
│     { version "1.0.0", project{...}, nodes[], edges[], layers[], tour[] }            │
│     => [J] intermediate/assembled-graph.json                                         │
│                                                                                      │
│ ┌────────────────────────────────────┐   ┌────────────────────────────────────┐      │
│ │ DEFAULT (no --review)              │   │ --review                           │      │
│ │ [R] tmp/ua-inline-validate.cjs     │   │ [A] graph-reviewer x1 (LLM)        │      │
│ │   written fresh from source        │   │   fed the scan-result file         │      │
│ │   embedded in SKILL.md, then run   │   │   inventory + $PHASE_WARNINGS      │      │
│ │   deterministic: required fields,  │   │   cross-validates every scanned    │      │
│ │   duplicate ids, edge integrity,   │   │   file against graph nodes and     │      │
│ │   layer coverage of the 9 file-    │   │   flags nodes whose filePath is    │      │
│ │   level types, tour refs;          │   │   not in the inventory             │      │
│ │   orphan node = warning only       │   │   (writes [R] ua-graph-validate.js)│      │
│ └────────────────────────────────────┘   └────────────────────────────────────┘      │
│                    └───────────────────┬────────────────────┘                        │
│                                        ▼                                             │
│                          [J] intermediate/review.json                                │
│                                                                                      │
│ auto-fixes: drop dangling edges, fill missing fields, drop invalid node types        │
│ -> revalidate ONCE. Critical issues still present: save the graph anyway,            │
│    report the warnings, and SKIP dashboard auto-launch.                              │
└──────────────────────────────────────────────────────────────────────────────────────┘
   │
   ▼
┌─ Phase 7/7 SAVE                  [O] only, step order is load-bearing ───────────────┐
│ 1) write [J] .understand-anything/knowledge-graph.json                               │
│ 2) [S] build-fingerprints.mjs <fingerprint-input.json>                               │
│      => [J] fingerprints.json  (output path HARDCODED)                               │
│      GATE: exit 0 AND stdout contains "Fingerprints baseline:"                       │
│      otherwise ABORT Phase 7 - meta.json must NOT be written (issue #152)            │
│ 3) write [J] meta.json {lastAnalyzedAt, gitCommitHash, version, analyzedFiles}       │
│ 4) cleanup: mv intermediate/* and tmp/ -> .trash-<epoch>/   (mv, not rm -rf)         │
│      PRESERVING intermediate/scan-result.json for the next incremental run           │
│ 5) summary: files, nodes by type, edges by type, layers, tour steps, warnings        │
│ 6) invoke /understand-dashboard ONLY if final validation passed                      │
└──────────────────────────────────────────────────────────────────────────────────────┘
   │
   ▼
┌─ [UI] Dashboard                  no AI, read-only ───────────────────────────────────┐
│ background: `GRAPH_DIR=<project-dir> npx vite --host 127.0.0.1`                      │
│   live Vite dev server, port 5173 (next free port if taken) - NOT a static           │
│   bundle, and never built in CI                                                      │
│ custom Vite plugin serves from GRAPH_DIR/.understand-anything/, each gated           │
│ by ?token=<per-process 16-byte hex ACCESS_TOKEN> (403 otherwise):                    │
│   /knowledge-graph.json  /domain-graph.json  /diff-overlay.json                      │
│   /meta.json  /config.json                                                           │
│ startup: parallel fetch of those endpoints -> React 19 + @xyflow/react +             │
│   Zustand layout computed in the browser                                             │
│ /file-content.json: lazy, fetched only when a node is clicked;                       │
│   graph-derived path allowlist + 1 MB cap                                            │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

**解說**

- **Phase 1 的 LLM 只做敘事**：檔案清單、語言、分類、行數來自 `scan-project.mjs`
  （`git ls-files` ＋ 走訪 fallback），import 關係來自 `extract-import-map.mjs`
  （tree-sitter ＋ 各語言解析規則，沒有 LLM fallback）；LLM 只從 README／manifest
  歸納出專案名稱、描述與 frameworks。
- **Phase 1.5 完全沒有 agent**。`compute-batches.mjs` 以 graphology 對 import graph 做
  Louvain 社群偵測，`MAX_COMMUNITY_SIZE 35`，退化時改用 count-based（`batchSize 12`、
  `MIN_BATCH_SIZE 3`），`neighborMap` 取 1-hop 且上限 50。非零 exit 是**硬失敗**，
  不重試。
- **Phase 2 的輸出檔名不能融合**：即使把多個小 batch 併成一次 dispatch，agent 仍必須
  依原本的 `batchIndex` 各寫一個 `batch-<i>.json`；merge 腳本的 regex 只認
  `batch-(\d+)(-part-(\d+))?.json`，其他名字（例如 `batch-fused-8-13.json`）會被**靜默
  丟棄**，整批節點與邊都會消失。
- **language / framework / locale 的 prompt 只在 Phase 4 注入** architecture-analyzer，
  Phase 2 的 file-analyzer 沒有拿到（upstream `frameworks/django.md` 的敘述與實際不符）。
- **Phase 6 的兩條路徑收斂在同一個 artifact**：預設路徑由 agent 依 SKILL.md 內嵌的原始碼
  寫出 `tmp/ua-inline-validate.cjs` 再執行（確定性檢查）；`--review` 則改派
  graph-reviewer，並額外餵入 scan inventory 與 `$PHASE_WARNINGS` 做交叉驗證。兩者都寫
  `review.json`。修完仍有 critical issue 時，圖照存，但不自動開 dashboard。
- **Dashboard 是 live dev server**，不是靜態產物；每個 JSON endpoint 都要帶
  per-process 的 `?token=`，否則 403。

---

## 圖 3：資料流（tmp/ 與 intermediate/ 的分界）

```text
┌─ .understand-anything/tmp/    per-agent scratch, never an input to a later phase ────────┐
│ ua-scan-files.json            ua-import-map-input.json / -output.json                    │
│ ua-file-analyzer-input-<i>.json                ua-file-extract-results-<i>.json          │
│ ua-arch-input.json / ua-arch-results.json      changed-files.txt                         │
│ ua-tour-input.json / ua-tour-results.json      ua-review-results.json                    │
│ [R] ua-inline-validate.cjs   [R] ua-arch-analyze.js   [R] ua-tour-analyze.js             │
│ [R] ua-graph-validate.js  (--review path)                                                │
│ the whole directory is moved into .trash-<epoch>/ at Phase 7 step 4                      │
└──────────────────────────────────────────────────────────────────────────────────────────┘

┌─ .understand-anything/intermediate/    pipeline state for one run ───────────────────────┐
│ [J] scan-result.json      files[] + importMap + project meta        (Phase 1)            │
│         │                                                                                │
│         ▼                                                                                │
│ [J] batches.json          Louvain batches + batchImportData         (Phase 1.5)          │
│         │                                                                                │
│         ▼                                                                                │
│ [J] batch-<i>.json        per-batch semantic nodes/edges            (Phase 2)            │
│     batch-<i>-part-<k>.json ; batch-existing.json on incremental runs                    │
│         │   (merge-batch-graphs.py also re-reads scan-result.json to                     │
│         │    recover ~25% of the import edges)                                           │
│         ▼                                                                                │
│ [J] assembled-graph.json  merged + normalized graph                 (Phase 2)            │
│         │                                                                                │
│         ├──▶ [J] assemble-review.json    and the reviewer edits     (Phase 3)            │
│         │        assembled-graph.json in place                                           │
│         ├──▶ [J] layers.json                                        (Phase 4)            │
│         ├──▶ [J] tour.json                                          (Phase 5)            │
│         ▼                                                                                │
│ [J] assembled-graph.json  rewritten as the canonical KnowledgeGraph (Phase 6)            │
│         │                 { version, project, nodes, edges, layers, tour }               │
│         ▼                                                                                │
│ [J] review.json           inline validator OR graph-reviewer output (Phase 6)            │
│ [J] fingerprint-input.json                                          (Phase 7)            │
└──────────────────────────────────────────────────────────────────────────────────────────┘
   │
   ▼
┌─ .understand-anything/    published output ──────────────────────────────────────────────┐
│ [J] knowledge-graph.json   the product; also the Dashboard's data source                 │
│ [J] fingerprints.json      written BEFORE meta.json and gates it                         │
│ [J] meta.json              {lastAnalyzedAt, gitCommitHash, version,                      │
│                             analyzedFiles} - only after fingerprints succeed             │
│ [J] config.json            autoUpdate, outputLanguage        (Phase 0)                   │
│     .understandignore      plain text                        (Phase 0.5)                 │
│     .trash-<epoch>/        old intermediate/ + tmp/, purged after 7 days                 │
│     intermediate/scan-result.json  DELIBERATELY SURVIVES cleanup so the                  │
│                                    next incremental run can skip Phase 1                 │
└──────────────────────────────────────────────────────────────────────────────────────────┘
   │
   ▼
┌─ [UI] Dashboard ─────────────────────────────────────────────────────────────────────────┐
│ parallel fetch of /knowledge-graph.json, /meta.json, /config.json, ...                   │
│ then /file-content.json lazily, one node click at a time                                 │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

**解說**

- `tmp/` 是**單一 phase 內部的 scratch**：由某個 agent 寫、同一個 agent 讀，不會成為下一
  個 phase 的輸入；runtime-authored 的 `[R]` 腳本也住在這裡。
- `intermediate/` 才是跨 phase 的管線狀態，`assembled-graph.json` 被寫過兩次
  （Phase 2 合併、Phase 6 改寫成 canonical KnowledgeGraph），Phase 3 還會就地編輯它。
- Phase 7 清理用 `mv` 而不是 `rm -rf`（避免觸發硬化主機的破壞性操作偵測），
  且**刻意保留** `intermediate/scan-result.json`，讓下一次增量更新可以跳過 Phase 1。
- `fingerprints.json` 不是可有可無的附屬品：它必須先寫成功，`meta.json` 才允許寫入。

---

## 圖 4：Subagent 與執行者對照

```text
┌─ [O] Orchestrator   main session running SKILL.md ───────────────────────────────────────┐
│ full run = 5 + N dispatches (N = number of batches), +1 with --review                    │
└──────────────────────────────────────────────────────────────────────────────────────────┘
   │
   ▼
┌─ [A] Subagents dispatched by [O]   (agents/*.md, LLM workers) ───────────────────────────┐
│ project-scanner         Phase 1        x1                                                │
│ file-analyzer           Phase 2        xN, up to 5 concurrent                            │
│ assemble-reviewer       Phase 3        x1                                                │
│ architecture-analyzer   Phase 4        x1                                                │
│ tour-builder            Phase 5        x1                                                │
│ graph-reviewer          Phase 6        x1, ONLY with --review                            │
└──────────────────────────────────────────────────────────────────────────────────────────┘

┌─ [S] Bundled scripts run directly by [O] ────────────────────────────────────────────────┐
│ merge-subdomain-graphs.py   Phase 0       Python                                         │
│ generate-ignore.mjs         Phase 0.5     Node                                           │
│ compute-batches.mjs         Phase 1.5     Node + graphology                              │
│                             (again on the incremental Phase 2 path)                      │
│ merge-batch-graphs.py       Phase 2 end   Python                                         │
│ build-fingerprints.mjs      Phase 7       Node + tree-sitter                             │
└──────────────────────────────────────────────────────────────────────────────────────────┘

┌─ [S] Bundled scripts run INSIDE an agent, not by [O] ────────────────────────────────────┐
│ scan-project.mjs        Phase 1   by project-scanner                                     │
│ extract-import-map.mjs  Phase 1   by project-scanner                                     │
│ extract-structure.mjs   Phase 2   by file-analyzer                                       │
│ extract-structure-result.mjs   imported module, NO CLI - not a pipeline step             │
│ (these 3 + the 5 above + the module = the 9 scripts that ship on disk)                   │
└──────────────────────────────────────────────────────────────────────────────────────────┘

┌─ [R] Runtime-authored scripts   written into tmp/ on every run, never on disk ───────────┐
│ ua-inline-validate.cjs  Phase 6 default   authored from source embedded in               │
│                                           SKILL.md, then run by [O]                      │
│ ua-arch-analyze.js      Phase 4           authored + run by architecture-analyzer        │
│ ua-tour-analyze.js      Phase 5           authored + run by tour-builder                 │
│ ua-graph-validate.js    Phase 6 --review  authored + run by graph-reviewer               │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

**解說**

- `/understand` 只用到 9 個 agent 中的 6 個；另外 3 個（`domain-analyzer`、
  `article-analyzer`、`knowledge-graph-guide`）屬於其他 skill 或由使用者直接呼叫。
- 磁碟上只有 **9 支腳本**隨 skill 出貨；其中 5 支由 `[O]` 直接執行、3 支由 agent 在自己
  的 dispatch 裡執行，另外 `extract-structure-result.mjs` 是被 import 的模組（沒有 CLI），
  不該畫成管線步驟。
- `[R]` 那一組**不存在於 repo**：每次執行才由 agent（或 `[O]`）現寫進 `tmp/`，跑完就被
  移進 `.trash-<epoch>/`。把它們畫成 bundled script 是常見的錯誤。

---

## 關鍵邊界

- **沒有 agent 產視覺圖**：`layers.json` 只是邏輯分層 metadata，實際 layout 由瀏覽器端的
  ReactFlow 計算。
- **Python 出現在兩個 phase**：Phase 0 的 `merge-subdomain-graphs.py`（合併 subdomain
  graph，會改寫 `knowledge-graph.json`）與 Phase 2 尾端的 `merge-batch-graphs.py`
  （合併 batch graph）。其餘腳本都是 Node；`layers` / `tour` 由 `[O]` 在 Phase 6 inline
  組進 KnowledgeGraph。
- **file-analyzer 內部**自己先跑 `extract-structure.mjs` 再做 LLM 語意分析；Orchestrator
  不跨管線餵結構 JSON。
- **只有 9 支腳本隨 skill 出貨**；`ua-inline-validate.cjs`、`ua-arch-analyze.js`、
  `ua-tour-analyze.js`、`ua-graph-validate.js` 都是 runtime-authored。
- **Dashboard read-only 且無 AI**：live Vite dev server（`127.0.0.1:5173`，被占用就往下找），
  每個 endpoint 以 per-process token 保護，`/file-content.json` 另有 graph-derived
  allowlist ＋ 1 MB 上限。
- **node / edge 型別數量隨 scope 不同**：`/understand` 的 SKILL.md 是 13 種 node ／ 26 種
  edge（本檔採用此組）；reviewer agent 為 16／29（各多 3 個 domain 型別）；
  `packages/core/src/schema.ts` 的 zod schema 是 21／35 的超集。
- **錯誤處理**：agent dispatch 失敗重試一次，警告累積在 `$PHASE_WARNINGS`；第二次失敗就
  跳過該 phase 帶著部分結果繼續，且一定存檔、一定回報。唯二的例外是 Phase 1.5 硬失敗與
  Phase 7 的 fingerprint abort。

## 相關檔案

- `understand_anything_flow.md` — 循序圖版
- `understand_anything_architecture_detailed.md` — 元件級架構圖
- `understand_anything_architecture.md` — 架構總覽
- `kai_mind_flow.md` — KAI-Mind 對照
- `../kai-mind-understand-anything-integration-boundary.md` — KAI-Mind 只採用其中
  `extract-import-map.mjs` → `compute-batches.mjs` → `extract-structure.mjs` 三支腳本，
  在 file-analyzer 之前就返回；本圖的 Phase 2 語意分析與 Phase 3～7 皆不採用。
