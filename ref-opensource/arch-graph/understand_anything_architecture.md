# Understand-Anything 架構總覽 (High-Level Architecture & Data Flow)

> Scope：`/understand` 主管線與唯讀 dashboard。
> 驗證基準：submodule pin `73559a1`（2026-07-06），plugin 版本 `2.8.2`。
> 來源：`understand-anything-plugin/skills/understand/SKILL.md`、`agents/*.md`、`packages/dashboard/`。
> 逐 Phase 細節見：`understand_anything_architecture_detailed.md`
> **Canonical 可視化總圖見：`understand_anything_pipeline_visual.md`**
> 使用者視角流程見：`understand_anything_flow.md`

本圖劃分五個職責邊界：**L0 編排層**、**L1 Agent 層（唯一有 LLM 的地方）**、
**L2 確定性腳本層**、**L3 解析核心**，以及 **JSON 產物管線 → 唯讀前端**。

```text
┌─ L0  Host Orchestrator - the main session itself, reading skills/understand/SKILL.md ────────┐
│  Owns directly (no subagent): Ph0 pre-flight, Ph0.5 ignore, Ph1.5 batch, Ph2 merge, Ph7      │
│  Dispatches agents for: Ph1 scan, Ph2 analyze, Ph3 assemble, Ph4 arch, Ph5 tour, Ph6         │
│  Ten phase sections; every progress string still reads "N/7" (incl. "[Phase 1.5/7]")         │
└────────────┬─────────────────────────────────────────────────┬───────────────────────────────┘
             │ Task dispatch (LLM)                             │ Bash: run bundled script
             ▼                                                 │
┌─ L1  Agent Layer - 5 pipeline agents + 1 optional ───────────┴───────────────────────────────┐
│  project-scanner        x1   Ph1  runs scan-project.mjs + extract-import-map.mjs itself;     │
│                                   LLM only names/describes the project                       │
│  file-analyzer          xN   Ph2  <=5 concurrent; runs extract-structure.mjs, then adds      │
│                                   semantic nodes/edges                                       │
│  assemble-reviewer      x1   Ph3  pure LLM, no script                                        │
│  architecture-analyzer  x1   Ph4  authors + runs tmp/ua-arch-analyze.js                      │
│  tour-builder           x1   Ph5  authors + runs tmp/ua-tour-analyze.js                      │
│  graph-reviewer         x1   Ph6  ┄┄▶ only with --review; default path is deterministic      │
│  Full run = 5 + N dispatches (N = batch count), +1 with --review                             │
└────────────┬─────────────────────────────────────────────────────────────────────────────────┘
             │ agents shell out to the same bundled scripts
             ▼
┌─ L2  Deterministic Script Layer - the 9 scripts bundled in skills/understand/ ───────────────┐
│  Ph0   merge-subdomain-graphs.py      Ph0.5 generate-ignore.mjs                              │
│  Ph1   scan-project.mjs               Ph1   extract-import-map.mjs                           │
│  Ph1.5 compute-batches.mjs            Ph2   extract-structure.mjs                            │
│  Ph2   merge-batch-graphs.py          Ph7   build-fingerprints.mjs                           │
│  9th file = extract-structure-result.mjs: pure imported module, NO CLI - not a step          │
│  NOT bundled: ua-inline-validate.cjs (Ph6 default), ua-arch-analyze.js, ua-tour-analyze.js,  │
│               ua-graph-validate.js - authored into tmp/ by the agent at runtime              │
└────────────┬─────────────────────────────────────────────────────────────────────────────────┘
             │ AST / parsing
             ▼
┌─ L3  @understand-anything/core ──────────────────────────────────────────────────────────────┐
│  web-tree-sitter WASM (native fails on darwin/arm64 + Node 24)                               │
│  14 language configs / 15 grammars + non-code parsers (Markdown, YAML, JSON, TOML, SQL, ...) │
│  Missing grammar = silent degradation (console.debug, empty result), never a throw           │
└──────────────────────────────────────────────────────────────────────────────────────────────┘

┌─ JSON Artifact Pipeline - everything under <project-root>/.understand-anything/ ─────────────┐
│  intermediate/scan-result.json        files[] + importMap (deliberately survives cleanup)    │
│        │  compute-batches.mjs                                                                │
│        ▼                                                                                     │
│  intermediate/batches.json            Louvain communities, file-count based                  │
│        │  extract-structure.mjs  (deterministic structure facts, no LLM)                     │
│        ▼                                                                                     │
│  tmp/ua-file-extract-results-<i>.json                                                        │
│        │  file-analyzer LLM  (semantic nodes/edges)                                          │
│        ▼                                                                                     │
│  intermediate/batch-<i>.json                                                                 │
│        │  merge-batch-graphs.py  (normalize ids, dedupe, import recovery)                    │
│        ▼                                                                                     │
│  intermediate/assembled-graph.json ──▶ assemble-review.json / layers.json / tour.json /      │
│        │                               review.json   (Ph3-6 also edit it in place)           │
│        ▼  Phase 7 SAVE - order is load-bearing                                               │
│  knowledge-graph.json ──▶ fingerprints.json ──▶ meta.json                                    │
└────────────┬─────────────────────────────────────────────────────────────────────────────────┘
             │ read-only HTTP, every route gated by ?token=<16-byte hex> (403 otherwise)
             ▼
┌─ Dashboard - a LIVE Vite dev server, not a static bundle ────────────────────────────────────┐
│  npx vite --host 127.0.0.1, port 5173 (next free port if taken), GRAPH_DIR=<project-dir>     │
│  GET /knowledge-graph.json, /meta.json, /config.json, /file-content.json                     │
│  /file-content.json: graph-derived path allowlist + 1 MB cap                                 │
│  React 19 + @xyflow/react + Zustand - renders only; never re-runs an agent or a script       │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 架構解說

1. **L0 Host Orchestrator = 主 session 本身**，不是一個 subagent。它讀 `SKILL.md` 當劇本，
   Phase 0 / 0.5 / 1.5 / Phase 2 尾端的 merge / Phase 7 全部由它直接跑腳本，不派 agent；
   只有 Phase 1～5（以及 `--review` 下的 Phase 6）才會派出 Task subagent。
2. **L1 Agent Layer 是全系統唯一有 LLM 的地方**。`project-scanner` 屬於 agent 層而非腳本層——
   它自己依序執行 `scan-project.mjs` 與 `extract-import-map.mjs`，LLM 只從 README / manifest
   歸納出專案名稱、描述與 frameworks。`file-analyzer` 同理：先跑 `extract-structure.mjs` 拿確定性
   結構事實，再由 LLM 疊上語意節點與邊。
3. **L2 只有 9 個腳本真的躺在 disk 上**。Phase 4 / 5 / 6 用到的 `ua-arch-analyze.js`、
   `ua-tour-analyze.js`、`ua-inline-validate.cjs`、`ua-graph-validate.js` 都是 agent 在 runtime
   當場寫進 `tmp/` 的一次性腳本，不隨 plugin 發佈；`extract-structure-result.mjs` 是被 import 的
   純模組、沒有 CLI 介面，畫成管線節點是錯的。
4. **產物演進是本圖的重點**：純結構（`ua-file-extract-results-*.json`）→ LLM 加語意的圖譜碎片
   （`batch-*.json`）→ 合併圖（`assembled-graph.json`）→ Phase 7 才落地成
   `knowledge-graph.json`。Phase 7 的順序是有意義的：`build-fingerprints.mjs` 必須成功
   （stdout 出現 `Fingerprints baseline:`）才准寫 `meta.json`。
5. **前端是唯讀且受 token 保護的**。Dashboard 是 `/understand-dashboard` 背景啟動的 Vite dev
   server，用自訂 Vite plugin 從 `GRAPH_DIR/.understand-anything/` 供檔；每個 route 都要
   `?token=`（per-process 16-byte 隨機 hex，可用 `UNDERSTAND_ACCESS_TOKEN` 覆寫），否則 403。
   `/file-content.json` 另有「只允許圖上出現過的路徑」白名單與 1 MB 上限。前端只畫圖，
   **絕對不會觸發或重跑任何 agent／腳本**。

### 容易讀錯的幾個點

- Plugin **沒有 `commands/` 目錄**：組成是 8 個 skills + 9 個 agents + hooks（git 事件與
  SessionStart 觸發的自動增量更新）。`/understand` 這個 slash command 來自
  `skills/understand/SKILL.md` 的 frontmatter `name`。
- **Phase 編號有十段，但進度字串一律寫 `N/7`**，包含字面上的 `[Phase 1.5/7]`。
- **節點／邊型別數量看 scope**：`/understand` 用 **13 node types / 26 edge types**；
  reviewer agents 的 prompt 是 16 / 29；`packages/core/src/schema.ts` 的 zod（權威超集）是 21 / 35。
- Phase 0 的 `merge-subdomain-graphs.py` 會在任何分析開始前就可能改寫既有的
  `knowledge-graph.json`（自動探索 `*knowledge-graph*.json`），別把它當成無副作用的前置動作。
- 語言／框架 prompt 只在 **Phase 4 architecture-analyzer** 注入，**沒有**注入 Phase 2 的
  file-analyzer（上游 `frameworks/*.md` 文件的敘述有誤）。
- 上游 `CLAUDE.md` 已過期（寫 5 agents / 4 skills）；disk 上實際是 9 agents / 8 skills，
  且 `SKILL.md` 確實有 dispatch `assemble-reviewer`。

### 與 Systograph 的邊界（一句話）

Systograph 只採用 L2 的三支腳本——`extract-import-map.mjs` → `compute-batches.mjs` →
`extract-structure.mjs`——在 UA Phase 1 之前進入、在 `file-analyzer` 之前就返回；
`scan-project.mjs` 與 Phase 3～7（含 dashboard）一律不採用。完整契約見
`ref-opensource/systograph-understand-anything-integration-boundary.md`。
