# Timmy Work Scope - Epic 1 Fact Layer

> Owner: Core scanner, schema, CLI, evidence, artifacts

## Goal

Timmy owns the fact layer for Epic 1. The scanner must read a RAG project folder and produce valid, evidence-based `ai_system_map.json` and `ai_system_map.md`.

## Responsibilities

- Define `rag-core-v1` slots and flows.
- Define `ai-system-map/v1` schema and domain models.
- Implement read-only providers:
  - filesystem
  - config
  - Docker Compose
  - dependencies
  - bounded code patterns
- Implement raw-signal normalization.
- Detect components, endpoints, flows, evidence, and risk hints.
- Implement one canonical secret masking policy.
- Implement `kai-mind map <project_path>`.
- Create synthetic RAG fixtures.
- Add schema, scanner, CLI, fixture, and no-secret tests.

## Non-Responsibilities

- Viewer visual design.
- Graph interaction.
- Query trace replay UI.
- Release readiness verdicts.
- Runtime health checks.

## Must Deliver

| Deliverable | Notes |
|---|---|
| `rag-core-v1` template | Slots, flows, common evidence signals |
| `ai-system-map/v1` schema | Stable enough for viewer and later epics |
| Scanner providers | Read-only, bounded, structured errors |
| Normalization service | Raw signals to map concepts |
| `ai_system_map.json` | Validated before success output |
| `ai_system_map.md` | Rendered from the same map |
| Fixtures | No real secrets, no external repo dependency |
| Tests | Schema, masking, path normalization, partial failure |

## Contract With Bo-Han

Timmy provides:

- sample valid maps
- sample missing-slot maps
- sample risk-hint maps
- field definitions for nodes, edges, evidence, endpoints, and risk hints

Bo-Han should not need to rescan the project folder to build the viewer.

## Review Checklist

- Detected components have evidence.
- Output has no `confidence` field.
- No full secret appears in outputs.
- Evidence paths are project-relative POSIX paths.
- Parse failures produce partial map evidence.
- Existing output artifacts are not overwritten.
