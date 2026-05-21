# Epic 1 Design Contract

> Status: Design contract
> Scope: Epic 1 - RAG System Map Builder  
> Source of truth for implementation: this file

## 1. Purpose

Epic 1 builds the first usable KAI-Mind capability: scan an existing RAG project folder and produce a stable, evidence-based `ai_system_map.json`.

The map is the shared fact layer for later runtime readiness, privacy/exposure, RAG trust, report, and CI gate work. Epic 1 should not decide whether a system is ready for release. It should explain what was detected, where the evidence came from, and what later checks should inspect.

## 2. MVP Scope

### In Scope

- Read-only project folder scan.
- Discovery of config, Docker Compose, dependency manifests, selected source files, and documentation hints.
- Deterministic extraction of raw scanner signals.
- Normalization into a RAG-oriented system map.
- `ai-system-map/v1` JSON contract.
- Human-readable Markdown summary.
- Secret-safe output across JSON, Markdown, logs, fixtures, and snapshots.
- Fixture-based tests that do not depend on live external repositories.

### Out of Scope

- Runtime health checks.
- Port security conclusions beyond initial hints.
- Deep secret scanning.
- Agent tool policy evaluation.
- RAG answer groundedness evaluation.
- `READY` / `RISKY` / `NOT_READY` verdicts.
- Query trace / replay by default.
- Full interactive dashboard.

Query trace can be designed later as an explicit opt-in workflow, for example `kai-mind trace --endpoint ...`. It should not be required for the first map builder because it calls a running user service and can trigger side effects, external LLM calls, quota usage, or data disclosure.

## 3. Architecture

```text
Project folder
  -> File discovery
  -> Format-specific parsers
  -> Raw scan signals
  -> Normalization service
  -> AI System Map validator
  -> JSON + Markdown artifacts
```

Core rule: parsers do not produce final product conclusions. They only produce raw signals with evidence. The normalization layer maps those signals into stable domain concepts.

Recommended future module boundaries:

```text
src/kai_mind/
  core/
    models/
    providers/
    services/
    templates/
  cli/
tests/
  fixtures/rag_projects/
  contracts/
  core/
  cli/
schemas/
```

## 4. Provider Responsibilities

Providers interact with files, parsers, or low-level sources. They must be read-only against the scanned project.

| Provider | Responsibility | Output |
|---|---|---|
| `FilesystemProvider` | Build bounded file inventory and read candidate files | file metadata, candidate contents |
| `ConfigParseProvider` | Parse `.env`, YAML, JSON, TOML-like config where supported | key/value signals, parse issues |
| `DockerComposeProvider` | Parse services, images, ports, env, volumes | service and endpoint signals |
| `DependencyManifestProvider` | Parse `requirements.txt`, `pyproject.toml`, `package.json` | dependency signals |
| `CodePatternProvider` | Bounded scan for explicit RAG patterns | code pattern signals |
| `OutputArtifactProvider` | Create output directory and write artifacts | artifact paths |

Provider failures should be structured. A malformed config file should not kill the full scan; it should create parse-error evidence and allow a partial map. A missing or unreadable project root is fatal.

## 5. Service Responsibilities

| Service | Responsibility |
|---|---|
| `MapBuildService` | Top-level orchestration for `kai-mind map` |
| `ProjectScanService` | Coordinate providers and collect raw signals |
| `RagTemplateService` | Load the `rag-core-v1` slot and flow template |
| `ComponentDetectionService` | Map raw signals to component slots and instances |
| `EndpointDetectionService` | Normalize local/external endpoint signals |
| `RiskHintService` | Create evidence-backed hints, not final security conclusions |
| `SystemMapNormalizeService` | Merge, dedupe, and assemble the map |
| `SystemMapValidationService` | Enforce schema invariants |
| `MarkdownSummaryService` | Render a human-readable summary from the validated map |
| `SecretMaskingService` | Apply one masking policy everywhere |

Service rules:

- Detected components must have evidence.
- The map must not include a `confidence` field.
- Missing evidence means the slot is `missing`, `not_configured`, or `not_applicable`, not guessed.
- Risk hints must include uncertainty when Epic 1 cannot prove real exposure.
- Report generation reads the normalized map. It must not rescan files.

## 6. `ai-system-map/v1` Contract

Required top-level fields:

- `schema_version`
- `system_type`
- `classification`
- `project`
- `reference_architecture`
- `components_by_slot`
- `endpoints`
- `flows`
- `risk_hints`
- `recommended_next_checks`

Important invariants:

- `schema_version` is `ai-system-map/v1`.
- `system_type` is `rag` for Epic 1.
- `classification.selected_template` is `rag-core-v1`.
- Component slot status is one of `detected`, `missing`, `not_configured`, `not_applicable`.
- `required_for_rag` is derived from the scanned project and template rules, not treated as a universal constant.
- Endpoint type is `local` or `external`.
- Risk hint target type is `component_instance`, `endpoint`, or `component_slot`.
- Evidence file paths use project-relative POSIX paths.
- Secret-like values are masked before serialization.

The implementation should add `schemas/ai-system-map.v1.schema.json` and contract tests before treating the schema as stable.

## 7. Evidence Model

Every meaningful output should be traceable back to evidence.

Evidence should include:

- `id`
- `kind`
- `file`
- `path` when available
- `value` when safe and useful
- `line_start` / `line_end` when available
- `masked` flag
- `parser`

Do not store complete secret values. Do not store raw retrieved chunks by default. RAG chunks can contain private documents or PII and are not necessarily caught by secret masking. If future trace work needs chunk details, use source IDs, hashes, counts, metadata summaries, or explicit opt-in redacted excerpts.

## 8. CLI Contract

Initial command:

```bash
kai-mind map <project_path> [--output outputs] [--system-type rag]
```

Expected behavior:

- Validate that `project_path` exists and is readable.
- If invalid, write `map-error.md` and exit non-zero.
- Create an output directory without overwriting existing artifacts.
- Continue on parse errors and produce a partial map with parse-error evidence.
- Validate JSON before writing success artifacts.
- Write `ai_system_map.json`.
- Write `ai_system_map.md`.

`kai-mind viewer <map_json>` can be planned as a follow-up. The viewer should load only the map JSON and must not rescan the project folder or invent components.

## 9. Fixture Strategy

Public repositories should be research input only. Do not vendor third-party repos into this repo.

Create synthetic fixtures that combine patterns from multiple references:

- `basic_qdrant_ollama_rag`: Docker Compose with app, Ollama, Qdrant.
- `openai_external_provider_rag`: external provider and API key name signals.
- `malformed_config_rag`: invalid YAML or Docker Compose for partial-scan behavior.
- `missing_slots_rag`: minimal project that exercises missing slot status.

Fixtures must not include real secrets.

## 10. Test Strategy

Minimum tests before implementation is considered healthy:

- Schema validation for generated maps.
- Golden fixture output for at least one basic RAG project.
- Secret masking test across JSON, Markdown, logs, and snapshots.
- Windows/macOS path normalization test.
- Malformed config partial-map test.
- Missing project error artifact test.
- No `confidence` field test.
- Detected component requires evidence test.

## 11. Viewer Follow-up Scope

The viewer is useful, but it should not define the core contract. Treat it as a projection of `ai_system_map.json`.

Viewer rules when it is implemented:

- Load a validated `ai_system_map.json`.
- Do not scan the project folder.
- Do not create components that are not in the map.
- Show evidence and risk hints from the map.
- Filters should keep the full graph visible and highlight matched items.
- Invalid map input should show an error state instead of a blank graph.

## 12. Delivery Order

| Milestone | Deliverable | Notes |
|---|---|---|
| M1 | Schema and domain models | Lock `ai-system-map/v1` before UI work |
| M2 | Synthetic fixtures | No external repo dependency |
| M3 | File/config/compose/dependency providers | Read-only and bounded |
| M4 | Normalization and risk hints | Evidence-backed, no `confidence` |
| M5 | CLI and artifacts | JSON + Markdown |
| M6 | Contract and fixture tests | Required before next epic |
| M7 | Viewer prototype | Follow-up after contract is stable |

## 13. Work Split

Timmy owns the fact layer:

- schema
- scanner providers
- normalization
- evidence
- risk hints
- CLI map command
- fixture and contract tests

Bo-Han owns the presentation layer after schema is stable:

- viewer loading
- graph view model
- detail panel
- highlight-only filters
- invalid map state
- UI tests

Shared interface:

- `ai-system-map/v1`
- sample `ai_system_map.json` files
- evidence and risk hint shape

## 14. Open Questions

- Which implementation language should be used first: Python or TypeScript?
- What exact ignore rules should the file scanner use?
- Should `required_for_rag` be encoded in template rules or derived entirely from detected flows?
- What is the first stable JSON schema path and migration policy?
- When query trace is revisited, what opt-in UX and privacy boundaries are required?
