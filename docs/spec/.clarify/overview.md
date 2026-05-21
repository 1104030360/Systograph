# Epic 1 Decision Log

This file keeps the decisions that affect implementation. It replaces the previous one-question-per-file clarification records.

## D1. Source of Truth

`docs/design/epic1.md` is the implementation contract for Epic 1.

Supporting files:

- `docs/spec/draft/epic1.md` for product/spec overview.
- `docs/spec/erm.dbml` for data-model reference.
- `docs/spec/features/*.feature` for high-level behavior examples.

## D2. Scanner Boundary

The scanner is read-only against the target project folder. It may write only to its output directory.

## D3. Public Repo Usage

Public RAG/local-AI repos may inform fixture design, but scanner tests must use local synthetic fixtures. Do not vendor third-party repos into this repository.

## D4. Normalization Layer

Parsers emit raw scan signals. A normalization service converts those signals into system-map concepts such as component slots, endpoints, flows, evidence, and risk hints.

## D5. Evidence Paths

Evidence file paths use project-relative POSIX paths so outputs are stable across Windows and macOS.

## D6. Secret Handling

Full secret values must not appear in JSON, Markdown, logs, snapshots, or UI. Secret-like values should be masked or omitted before serialization.

Raw retrieved chunks are not part of the default Epic 1 map contract because they may contain private documents or PII.

## D7. Endpoints

Endpoints are modeled independently from components because multiple components can reference the same endpoint, and one component can expose or depend on multiple endpoints.

## D8. Risk Hint Targets

Risk hints may target:

- `component_instance`
- `endpoint`
- `component_slot`

Risk hints are not final security verdicts. They must include uncertainty.

## D9. Parse Failures

Malformed config or Docker Compose files should create parse-error evidence and allow a partial map. Missing or unreadable project root is fatal.

## D10. Output Directory

The map command must not overwrite existing artifacts. If an output directory already contains artifacts, create a timestamped run directory.

## D11. Viewer Filter Behavior

Viewer filters keep the full graph visible and highlight matching items. They should not hide unmatched components by default.

## D12. Query Trace

Query trace / replay is not part of the Epic 1 MVP. It can be revisited as an explicit opt-in workflow after privacy, endpoint, and side-effect boundaries are defined.
